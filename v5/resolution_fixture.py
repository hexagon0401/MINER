"""CI-only WARP-like proxy: reject hostnames, serve verified TLS DoH and IP echo."""
import http.server
from pathlib import Path
import shutil
import socket
import socketserver
import ssl
import struct
import subprocess
import threading
from schoolnet.probe import recv_exact

ORIGIN='8.8.4.4'

class DoH(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        size=int(self.headers.get('Content-Length','0'))
        if self.path!='/dns-query' or not 12<=size<=512:self.send_error(400);return
        query=self.rfile.read(size);offset=12;labels=[]
        while query[offset]:
            count=query[offset];offset+=1;labels.append(query[offset:offset+count].decode());offset+=count
        offset+=1;kind,cls=struct.unpack('!HH',query[offset:offset+4]);end=offset+4
        self.server.dns_questions.append(('.'.join(labels),kind))
        answer=(b'\xc0\x0c'+struct.pack('!HHIH',1,1,30,4)+socket.inet_aton(ORIGIN)) if kind==1 else b''
        body=query[:2]+b'\x81\x80\0\1'+struct.pack('!H',1 if answer else 0)+b'\0\0\0\0'+query[12:end]+answer
        self.send_response(200);self.send_header('Content-Type','application/dns-message');self.send_header('Content-Length',str(len(body)));self.send_header('Connection','close');self.end_headers();self.wfile.write(body)

class Origin(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_HEAD(self):
        self.send_response(404);self.send_header('Content-Length','0');self.send_header('Connection','close');self.end_headers()

class Proxy(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        try:
            if recv_exact(self.request,3)!=b'\5\1\0':raise ValueError('Invalid fixture greeting')
            self.request.sendall(b'\5\0');header=recv_exact(self.request,4)
            if header[:3]!=b'\5\1\0':raise ValueError('Invalid fixture command')
            kind=header[3]
            if kind==3:host=recv_exact(self.request,recv_exact(self.request,1)[0]).decode()
            elif kind in (1,4):host=socket.inet_ntop(socket.AF_INET if kind==1 else socket.AF_INET6,recv_exact(self.request,4 if kind==1 else 16))
            else:raise ValueError('Invalid fixture address')
            port=struct.unpack('!H',recv_exact(self.request,2))[0]
            if kind==3:
                self.server.rejected_hostnames.append(host)
                self.request.sendall(b'\5\5\0\1\0\0\0\0\0\0');return
            self.request.sendall(b'\5\0\0\1\x7f\0\0\1\0\0')
            if host=='1.1.1.1' and port==443:
                with self.server.tls.wrap_socket(self.request,server_side=True) as tls:DoH(tls,self.client_address,self.server)
                return
            if host!=ORIGIN:raise ValueError('Fixture received unresolved/synthetic origin')
            self.server.destinations.append((host,port))
            if self.server.origin_tls:
                with self.server.tls.wrap_socket(self.request,server_side=True) as tls:Origin(tls,self.client_address,self.server)
                return
            while True:
                data=self.request.recv(1024)
                if not data:return
                self.request.sendall(data)
        except (OSError,ValueError) as exc:self.server.errors.append(type(exc).__name__)

class Server(socketserver.ThreadingTCPServer):
    daemon_threads=True

class Fixture:
    def __init__(self,directory):
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        config=directory/'tls.cnf';cert=directory/'ca.pem';key=directory/'key.pem'
        config.write_text('[req]\ndistinguished_name=dn\nx509_extensions=v3\nprompt=no\n[dn]\nCN=MINER CI only\n[v3]\nsubjectAltName=DNS:cloudflare-dns.com,DNS:auth.riotgames.com\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\n')
        openssl=shutil.which('openssl') or r'C:\Program Files\Git\usr\bin\openssl.exe'
        subprocess.run([openssl,'req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-config',str(config)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
        self.cert=cert;self.server=Server(('127.0.0.1',0),Proxy)
        self.server.destinations=[];self.server.rejected_hostnames=[];self.server.dns_questions=[];self.server.errors=[]
        self.server.origin_tls=False
        self.server.tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);self.server.tls.load_cert_chain(cert,key)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
    @property
    def port(self):return self.server.server_address[1]
    def configure(self,config):
        resolver=next(s for s in config['dns']['servers'] if s['tag']=='riot-real-dns')
        resolver['tls']['certificate_path']=str(self.cert)
        return config
    def close(self):self.server.shutdown();self.server.server_close()
