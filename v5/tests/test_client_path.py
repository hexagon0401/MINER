import io
import socket
import unittest
from unittest.mock import patch,MagicMock
from schoolnet import client_path as p

class ClientPathTests(unittest.TestCase):
    def answer(self,ip):return (socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))
    def test_real_or_mixed_os_dns_is_not_allowed_as_selected_path(self):
        for ips in [['8.8.4.4'],['198.18.0.5','8.8.4.4']]:
            with self.subTest(ips=ips),patch.object(p.socket,'getaddrinfo',return_value=[self.answer(ip) for ip in ips]),self.assertRaisesRegex(p.ClientPathError,'OS_DNS_OUTSIDE_SELECTED_SPACE'):
                p.resolve_os('auth.riotgames.com',1)
    def test_synthetic_v4_v6_and_mapped_answers_are_accepted(self):
        with patch.object(p.socket,'getaddrinfo',return_value=[self.answer(ip) for ip in ['198.18.0.5','fdfe:dcba:9876:1000::5','::ffff:198.18.0.6']]):
            self.assertEqual(p.resolve_os('auth.riotgames.com',1),['198.18.0.5','198.18.0.6','fdfe:dcba:9876:1000::5'])
    def test_probe_dials_fake_ip_with_original_tls_host_without_raw_proxy_or_direct_fallback(self):
        sock=MagicMock();tls=MagicMock();tls.makefile.return_value=io.BytesIO(b'HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n')
        ctx=MagicMock();ctx.wrap_socket.return_value.__enter__.return_value=tls
        with patch.object(p,'resolve_os',return_value=['198.18.0.5']),patch.object(p.socket,'create_connection',return_value=sock) as connect,patch.object(p.ssl,'create_default_context',return_value=ctx):
            result=p.verify()
        self.assertEqual(connect.call_args.args[0],('198.18.0.5',443))
        ctx.wrap_socket.assert_called_once_with(sock.__enter__.return_value,server_hostname='auth.riotgames.com')
        self.assertTrue(result['os_dns_synthetic']);self.assertFalse(result['client_process_traffic_verified'])
    def test_bad_dns_never_opens_a_connection(self):
        with patch.object(p,'resolve_os',side_effect=p.ClientPathError('OS_DNS_OUTSIDE_SELECTED_SPACE')),patch.object(p.socket,'create_connection') as connect,self.assertRaises(p.ClientPathError):p.verify()
        connect.assert_not_called()

    def test_cli_cannot_emit_pass_when_upstream_works_but_os_path_bypasses(self):
        import contextlib,json,main
        out=io.StringIO();err=io.StringIO()
        with patch.object(main.sys,'platform','darwin'),patch.object(main.signal,'signal'),patch('schoolnet.warp.verify_client_service',return_value={'tls_verified':True}),patch.object(p,'verify',side_effect=p.ClientPathError('OS_DNS_OUTSIDE_SELECTED_SPACE')),contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            self.assertEqual(main.main(['warp','service-check','--request-id','r1','--generation','1']),1)
        event=json.loads(out.getvalue())
        self.assertEqual(event['status'],'FAIL');self.assertEqual(event['reason_code'],'CLIENT_OS_DNS_BYPASS')
        self.assertNotIn('"event"',err.getvalue())
