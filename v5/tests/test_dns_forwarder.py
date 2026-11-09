import socket
import socketserver
import struct
import threading
import unittest
from unittest.mock import patch

from schoolnet.dns_forwarder import Forwarder,recv_exact
from schoolnet.network_dns import addresses

QUERY=b'\x25\x36\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'
ANSWER=QUERY[:2]+b'\x81\x80'+QUERY[4:]

class UDP(socketserver.BaseRequestHandler):
    def handle(self):
        query,sock=self.request
        self.server.requests.append(query)
        sock.sendto(ANSWER,self.client_address)

class TCP(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        query=recv_exact(self.request,struct.unpack('!H',recv_exact(self.request,2))[0])
        self.server.requests.append(query)
        self.request.sendall(struct.pack('!H',len(ANSWER))+ANSWER)

class ForwarderTests(unittest.TestCase):
    def test_udp_tcp_and_fallback_use_only_original_resolvers(self):
        udp=socketserver.ThreadingUDPServer(('127.0.0.1',0),UDP)
        tcp=socketserver.ThreadingTCPServer(('127.0.0.1',udp.server_address[1]),TCP)
        for server in (udp,tcp):
            server.requests=[];threading.Thread(target=server.serve_forever,daemon=True).start()
        lookup=socket.getaddrinfo;attempts=[]
        def resolve(host,port,*args):
            if port!=53:return lookup(host,port,*args)
            attempts.append(host)
            if host=='127.0.0.2':raise socket.gaierror('original resolver unavailable')
            return lookup(host,udp.server_address[1],*args)
        try:
            with patch('schoolnet.dns_forwarder.socket.getaddrinfo',side_effect=resolve),Forwarder(['127.0.0.2','127.0.0.1']) as relay:
                with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                    sock.settimeout(2);sock.sendto(QUERY,('127.0.0.1',relay.port))
                    self.assertEqual(ANSWER,sock.recv(1024))
                with socket.create_connection(('127.0.0.1',relay.port),timeout=2) as sock:
                    sock.sendall(struct.pack('!H',len(QUERY))+QUERY)
                    self.assertEqual(ANSWER,recv_exact(sock,struct.unpack('!H',recv_exact(sock,2))[0]))
            self.assertEqual([QUERY],udp.requests);self.assertEqual([QUERY],tcp.requests)
            self.assertEqual({'127.0.0.1','127.0.0.2'},set(attempts))
        finally:
            for server in (udp,tcp):server.shutdown();server.server_close()

    def test_failure_returns_servfail_without_public_resolver_fallback(self):
        relay=Forwarder(['192.0.2.53'])
        try:
            with patch('schoolnet.dns_forwarder.socket.getaddrinfo',side_effect=socket.gaierror()) as call:
                answer=relay.exchange(QUERY)
                self.assertEqual(QUERY[:2],answer[:2]);self.assertEqual(2,answer[3]&15)
                self.assertEqual('192.0.2.53',call.call_args.args[0])
        finally:relay.__exit__()

    def test_dns_scope_cannot_become_powershell_code(self):
        self.assertEqual([],addresses(["fe80::1%';Write-Output bad;#",'1.2.3.4%en0','198.18.0.1','172.30.255.2']))
        self.assertEqual(['fe80::1%en0','fe80::1%12'],addresses(['fe80::1%en0','fe80::1%12']))
