import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from schoolnet.config import Profile,build_config
from schoolnet.probe import socks_connect,SocksConnectError,recv_exact
from schoolnet.protocol_output import transport_detail
from resolution_fixture import Fixture,ORIGIN

class ProxyResolutionTests(unittest.TestCase):
    def test_reply_number_and_tls_errors_are_safe_and_distinct(self):
        import ssl
        self.assertEqual(transport_detail(SocksConnectError(5)),{'failure_stage':'SOCKS_CONNECT','failure_code':'SOCKS_REPLY_5'})
        detail=transport_detail(ssl.SSLCertVerificationError('SECRET'))
        self.assertEqual(detail['failure_code'],'CERTIFICATE_VERIFY_FAILED');self.assertNotIn('SECRET',json.dumps(detail))

    def test_pinned_engine_resolves_via_proxy_doh_and_sends_only_real_ip(self):
        engine=os.environ.get('SCHOOLNET_TEST_ENGINE')
        if not engine:self.skipTest('Set pinned SCHOOLNET_TEST_ENGINE')
        engine=str(Path(engine).resolve())
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td);fixture=Fixture(folder/'fixture')
            try:
                for mode in ('legacy','fixed','bad_tls'):
                    legacy=mode=='legacy'
                    with self.subTest(mode=mode),socket.socket() as reservation:
                        reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
                        reservation.close()
                        config=fixture.configure(build_config(Profile(proxy_port=fixture.port)))
                        config['inbounds']=[{'type':'socks','tag':'schoolnet-tun','listen':'127.0.0.1','listen_port':port}]
                        config['experimental']['cache_file']['path']=str(folder/('legacy.db' if legacy else 'fixed.db'))
                        if legacy:config['route']['rules']=[r for r in config['route']['rules'] if r['action']!='resolve']
                        if mode=='bad_tls':next(s for s in config['dns']['servers'] if s['tag']=='riot-real-dns')['tls']['server_name']='wrong.invalid'
                        path=folder/'config.json';path.write_text(json.dumps(config))
                        with (folder/'engine.log').open('w') as log:
                            child=subprocess.Popen([engine,'run','-c',str(path)],stdout=log,stderr=log)
                            try:
                                deadline=time.monotonic()+8
                                while True:
                                    try:client=socket.create_connection(('127.0.0.1',port),timeout=.3);break
                                    except OSError:
                                        if child.poll() is not None or time.monotonic()>deadline:self.fail((folder/'engine.log').read_text())
                                        time.sleep(.05)
                                with client:
                                    client.settimeout(8)
                                    if mode!='fixed':
                                        with self.assertRaises(SocksConnectError):socks_connect(client,'auth.riotgames.com',443)
                                    else:
                                        socks_connect(client,'auth.riotgames.com',443)
                                        for payload in [b'login',b'friends',b'ready-check',b'post-game']:
                                            client.sendall(payload);self.assertEqual(recv_exact(client,len(payload)),payload)
                            finally:child.terminate();child.wait(timeout=5)
                self.assertEqual(fixture.server.rejected_hostnames,['auth.riotgames.com'])
                self.assertEqual(fixture.server.destinations,[(ORIGIN,443)])
                self.assertIn(('auth.riotgames.com',1),fixture.server.dns_questions)
            finally:fixture.close()

    def test_health_probe_dns_uses_verified_tls_via_proxy_without_os_lookup(self):
        import ssl
        from schoolnet import proxy_dns
        with tempfile.TemporaryDirectory() as td:
            fixture=Fixture(td)
            try:
                context=ssl.create_default_context(cafile=str(fixture.cert))
                real_getaddrinfo=socket.getaddrinfo
                def local_only(host,*args,**kwargs):
                    self.assertEqual(host,'127.0.0.1')
                    return real_getaddrinfo(host,*args,**kwargs)
                with patch.object(proxy_dns.ssl,'create_default_context',return_value=context),patch('socket.getaddrinfo',side_effect=local_only):
                    origin=proxy_dns.resolve_origin('auth.riotgames.com',fixture.port,time.monotonic()+5,[None])
                self.assertEqual(origin,ORIGIN);self.assertFalse(fixture.server.rejected_hostnames)
                self.assertEqual(fixture.server.dns_questions,[('auth.riotgames.com',1)])
            finally:fixture.close()

    def test_dns_parser_refuses_fake_or_invalid_answers(self):
        import struct
        from schoolnet.proxy_dns import parse_answer
        query=b'\x01\x02\x01\x00\0\1\0\0\0\0\0\0\x01a\0\0\1\0\1'
        for address in ['198.18.0.28','127.0.0.1','172.30.255.2']:
            response=query[:2]+b'\x81\x80\0\1\0\1\0\0\0\0'+query[12:]+b'\xc0\x0c'+struct.pack('!HHIH',1,1,30,4)+socket.inet_aton(address)
            with self.assertRaises(ValueError):parse_answer(query,response)
        with self.assertRaises(ValueError):parse_answer(query,b'bad')
