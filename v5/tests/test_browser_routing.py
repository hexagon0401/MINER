"""Real engine traffic on loopback; never installs a TUN/default route."""
import http.server
import json
import os
from pathlib import Path
import socket
import socketserver
import ssl
import struct
import subprocess
import tempfile
import threading
import time
import unittest

from schoolnet.config import Profile,build_config
from schoolnet.probe import socks_connect


class DNS(socketserver.BaseRequestHandler):
    def handle(self):
        data,transport=self.request
        end=12;parts=[]
        while data[end]:
            size=data[end];parts.append(data[end+1:end+1+size].decode());end+=size+1
        end+=5;self.server.names.append('.'.join(parts))
        answer=data[:2]+b'\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00'+data[12:end]
        answer+=b'\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04\x7f\x00\x00\x01'
        transport.sendto(answer,self.client_address)


class Web(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'ordinary browser route healthy'
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass


def port(kind):
    with socket.socket(socket.AF_INET,kind) as reservation:
        reservation.bind(('127.0.0.1',0));return reservation.getsockname()[1]


@unittest.skipUnless(os.environ.get('SCHOOLNET_TEST_ENGINE'),'Requires the verified native engine')
class BrowserRoutingTests(unittest.TestCase):
    def test_dns_and_verified_https_work_when_warp_is_down_and_riot_dns_does_not_leak(self):
        resolver=socketserver.ThreadingUDPServer(('127.0.0.1',0),DNS);resolver.names=[]
        web=http.server.ThreadingHTTPServer(('127.0.0.1',0),Web)
        fixture=Path(__file__).parent/'fixtures'
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(fixture/'local-web.pem',fixture/'local-web.key')
        web.socket=context.wrap_socket(web.socket,server_side=True)
        for server in (resolver,web):threading.Thread(target=server.serve_forever,daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as temporary:
                proxy_port,dns_port=port(socket.SOCK_STREAM),port(socket.SOCK_DGRAM)
                config=build_config(Profile(proxy_port=port(socket.SOCK_STREAM)))
                # Loopback listeners exercise the generated routing/DNS rules,
                # replacing privileged TUN and physical-interface binding only.
                config['inbounds']=[{'type':'socks','tag':'browser-test','listen':'127.0.0.1','listen_port':proxy_port},
                    {'type':'direct','tag':'dns-test','listen':'127.0.0.1','listen_port':dns_port,'network':'udp','override_address':'127.0.0.1','override_port':53}]
                config['route'].pop('auto_detect_interface',None)
                config['dns']['servers'][1]={'type':'udp','tag':'direct-dns','server':'127.0.0.1','server_port':resolver.server_address[1]}
                path=Path(temporary)/'config.json';path.write_text(json.dumps(config))
                log_path=Path(temporary)/'engine.log'
                with log_path.open('w') as log:
                    process=subprocess.Popen([os.environ['SCHOOLNET_TEST_ENGINE'],'run','-c',str(path)],stdout=log,stderr=log)
                    try:
                        deadline=time.monotonic()+5
                        while True:
                            try:
                                sock=socket.create_connection(('127.0.0.1',proxy_port),timeout=2);break
                            except OSError:
                                if process.poll() is not None or time.monotonic()>deadline:self.fail(log_path.read_text())
                                time.sleep(.03)
                        with sock:
                            socks_connect(sock,'normal.example',web.server_address[1])
                            client=ssl.create_default_context(cafile=str(fixture/'local-web.pem'))
                            with client.wrap_socket(sock,server_hostname='normal.example') as secure:
                                secure.sendall(b'GET / HTTP/1.0\r\nHost: normal.example\r\n\r\n')
                                result=b''
                                while True:
                                    chunk=secure.recv(4096)
                                    if not chunk:break
                                    result+=chunk
                        self.assertIn(b'ordinary browser route healthy',result)
                        self.assertIn('normal.example',resolver.names)
                        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as query:
                            query.settimeout(1)
                            domain=b'\x05login\x09riotgames\x03com\x00'
                            query.sendto(b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'+domain+b'\x00\x01\x00\x01',('127.0.0.1',dns_port))
                            try:response=query.recv(512)
                            except socket.timeout:response=b''
                            self.assertFalse(response and response[3]&15==0,'Riot DNS must not succeed through the direct resolver')
                        self.assertNotIn('login.riotgames.com',resolver.names)
                    finally:
                        process.terminate();process.wait(timeout=10)
        finally:
            for server in (resolver,web):server.shutdown();server.server_close()


if __name__=='__main__':unittest.main()
