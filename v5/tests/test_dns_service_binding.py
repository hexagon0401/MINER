"""Exercise actual sing-box DNS packets; no TUN, WARP or system DNS changes."""
import ipaddress
import json
import os
from pathlib import Path
import socket
import socketserver
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from schoolnet.config import Profile, build_config


class Upstream(socketserver.BaseRequestHandler):
    def handle(self):
        query, sock = self.request
        kind = struct.unpack('!H', query[-4:-2])[0]
        self.server.queries.append(kind)
        # ServiceMode records with both address hints. Only this loopback
        # fixture is queried; these addresses are never contacted.
        data = (b'\x00\x01\x00' + struct.pack('!HH', 4, 4) + socket.inet_aton('8.8.4.4') +
                struct.pack('!HH', 6, 16) + socket.inet_pton(socket.AF_INET6, '2606:4700::1111'))
        reply = (query[:2] + b'\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00' + query[12:] +
                 b'\xc0\x0c' + struct.pack('!HHIH', kind, 1, 60, len(data)) + data)
        sock.sendto(reply, self.client_address)


def ask(port, host, kind):
    query = (b'\x31\x32\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00' +
             b''.join(bytes([len(part)]) + part.encode('ascii') for part in host.split('.')) +
             b'\x00' + struct.pack('!HH', kind, 1))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(.4)
        sock.sendto(query, ('127.0.0.1', port))
        reply = sock.recv(4096)
    if reply[:2] != query[:2]: raise ValueError('DNS transaction mismatch')
    return reply


class ServiceBindingTests(unittest.TestCase):
    def test_native_engine_blocks_only_selected_service_binding_hints_and_preserves_address_dns(self):
        engine = os.environ.get('SCHOOLNET_TEST_ENGINE')
        if not engine: self.skipTest('Set SCHOOLNET_TEST_ENGINE to pinned sing-box 1.12.0')
        engine = str(Path(engine).resolve())
        for platform in ('macos', 'windows'):
            with self.subTest(platform=platform), socketserver.UDPServer(('127.0.0.1', 0), Upstream) as upstream, tempfile.TemporaryDirectory() as td:
                upstream.queries = []
                threading.Thread(target=upstream.serve_forever, daemon=True).start()
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
                    reservation.bind(('127.0.0.1', 0)); port = reservation.getsockname()[1]
                config = build_config(Profile(platform=platform, dns_forward_port=upstream.server_address[1]))
                config['inbounds'] = [{'type': 'direct', 'tag': 'fixture-dns', 'listen': '127.0.0.1', 'listen_port': port, 'network': 'udp'}]
                config['route']['rules'] = [{'inbound': ['fixture-dns'], 'action': 'hijack-dns'}]
                folder = Path(td); path = folder / 'fixture.json'; path.write_text(json.dumps(config))
                with (folder / 'engine.log').open('w') as log:
                    child = subprocess.Popen([engine, 'run', '-c', str(path)], cwd=folder, stdout=log, stderr=log)
                    try:
                        deadline = time.monotonic() + 8
                        while True:
                            if child.poll() is not None: self.fail('DNS fixture engine exited: ' + (folder / 'engine.log').read_text()[-2000:])
                            try: ask(port, 'example.test', 65); break
                            except (socket.timeout, ConnectionResetError, ConnectionRefusedError):
                                if time.monotonic() > deadline: self.fail('DNS fixture not ready')
                        upstream.queries.clear()
                        for host in ('riotgames.com', 'chat.riotgames.com', 'kr.pvp.net'):
                            for kind in (64, 65):
                                reply = ask(port, host, kind)
                                self.assertEqual(reply[3] & 15, 0, 'Use NODATA, not NXDOMAIN')
                                self.assertEqual(struct.unpack('!H', reply[6:8])[0], 0)
                                self.assertNotIn(socket.inet_aton('8.8.4.4'), reply)
                        self.assertEqual(upstream.queries, [], 'Selected hints must never reach ordinary upstream')
                        for host in ('example.test', 'notriotgames.com'):
                            for kind in (64, 65):
                                reply = ask(port, host, kind)
                                self.assertEqual(struct.unpack('!H', reply[6:8])[0], 1)
                                self.assertIn(socket.inet_aton('8.8.4.4'), reply)
                        self.assertIn(64, upstream.queries); self.assertIn(65, upstream.queries)
                        self.assertIn(ipaddress.ip_address(ask(port, 'chat.riotgames.com', 1)[-4:]), ipaddress.ip_network('198.18.0.0/15'))
                        self.assertIn(ipaddress.ip_address(ask(port, 'chat.riotgames.com', 28)[-16:]), ipaddress.ip_network('fdfe:dcba:9876:1000::/64'))
                    finally:
                        child.terminate(); child.wait(timeout=5); upstream.shutdown()
