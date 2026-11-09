"""Bounded DNS-only relay to the connection's original resolvers (never game data)."""
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import socket
import struct
import threading


def recv_exact(connection, count):
    data = bytearray()
    while len(data) < count:
        chunk = connection.recv(count-len(data))
        if not chunk: raise OSError("Incomplete DNS response")
        data.extend(chunk)
    return bytes(data)


class Forwarder:
    def __init__(self, servers):
        self.servers = list(dict.fromkeys(servers))
        if not self.servers: raise ValueError("No original DNS resolver is available")
        for server in self.servers: ipaddress.ip_address(server.split('%')[0])
        self.stop = threading.Event()
        self.slots = threading.BoundedSemaphore(16)
        self.pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="MINER DNS")
        self.sockets = []
        self.threads = []

    def __enter__(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(('127.0.0.1', 0))
        self.port = udp.getsockname()[1]
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try: tcp.bind(('127.0.0.1', self.port)); tcp.listen(8)
        except Exception: udp.close(); tcp.close(); self.pool.shutdown(); raise
        self.sockets = [udp, tcp]
        for sock, target in [(udp,self.udp_loop),(tcp,self.tcp_loop)]:
            sock.settimeout(.25)
            thread=threading.Thread(target=target,args=(sock,),daemon=True)
            self.threads.append(thread);thread.start()
        return self

    def exchange(self, query, tcp=False):
        if not 12 <= len(query) <= 65535: raise OSError("Invalid DNS request size")
        for server in self.servers:
            family = socket.AF_INET6 if ':' in server else socket.AF_INET
            try:
                address = socket.getaddrinfo(server, 53, family, socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM,0,socket.AI_NUMERICHOST)[0][4]
                with socket.socket(family, socket.SOCK_STREAM if tcp else socket.SOCK_DGRAM) as upstream:
                    upstream.settimeout(1.0); upstream.connect(address)
                    if tcp:
                        upstream.sendall(struct.pack('!H',len(query))+query)
                        response = recv_exact(upstream,struct.unpack('!H',recv_exact(upstream,2))[0])
                    else:
                        upstream.send(query); response = upstream.recv(65535)
                if len(response) >= 12 and response[:2] == query[:2] and response[2] & 0x80 and response[3]&15 not in (2,5):
                    return response
            except OSError: continue
        # Preserve the transaction/question; report failure without changing the
        # destination to a public resolver or sending ordinary DNS through WARP.
        return query[:2]+b'\x81\x82'+query[4:6]+b'\x00\x00\x00\x00\x00\x00'+query[12:]

    def udp_loop(self, listener):
        while not self.stop.is_set():
            try: query, address = listener.recvfrom(65535)
            except socket.timeout: continue
            except OSError: break
            if self.slots.acquire(False):
                self.pool.submit(self.udp_reply,listener,query,address)

    def udp_reply(self, listener, query, address):
        try: listener.sendto(self.exchange(query),address)
        except OSError: pass
        finally: self.slots.release()

    def tcp_loop(self, listener):
        while not self.stop.is_set():
            try: connection,_ = listener.accept()
            except socket.timeout: continue
            except OSError: break
            if self.slots.acquire(False): self.pool.submit(self.tcp_reply,connection)
            else: connection.close()

    def tcp_reply(self, connection):
        try:
            with connection:
                connection.settimeout(2)
                query = recv_exact(connection,struct.unpack('!H',recv_exact(connection,2))[0])
                answer = self.exchange(query,True)
                connection.sendall(struct.pack('!H',len(answer))+answer)
        except OSError: pass
        finally: self.slots.release()

    def __exit__(self,*args):
        self.stop.set()
        for sock in self.sockets: sock.close()
        for thread in self.threads: thread.join(timeout=1)
        self.pool.shutdown(wait=True)
