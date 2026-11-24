import io
from pathlib import Path
from unittest.mock import MagicMock, patch
import unittest

from schoolnet import warp


TRACE = {"warp": "on", "via": "socks5h", "direct_fallback": False}


class WarpTests(unittest.TestCase):
    def setUp(self):
        patcher = patch.object(warp, "proxy_ready")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_restore_explicit_udp_mode_and_validate(self):
        calls = []
        settings=iter(['Mode: WarpProxy','Mode: Warp'])
        def call(cli, *args, **kwargs):
            calls.append(args)
            if args==('settings',):return next(settings)
            return {("mode", "--help"): "warp warp+doh proxy", ("status",): "Connected"}.get(args, "Success")
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call):
            self.assertTrue(warp.restore()["restored"])
        self.assertEqual(calls[2:5], [("disconnect",), ("mode", "warp"), ("connect",)])

    def test_progress_follows_real_checks(self):
        calls, call = self.cli_fixture()
        events = []
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call), patch.object(warp, "verify_trace", return_value=TRACE):
            warp.activate(notify=lambda phase, count: events.append((phase, count)))
        self.assertEqual(events, [("cli_check", 0), ("proxy_connect", 1), ("tls_verify", 2), ("warp_ready", 3)])

    def test_restore_unsupported_mode_does_not_disconnect(self):
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", return_value="proxy warp+doh") as call, self.assertRaises(ValueError):
            warp.restore()
        self.assertEqual(call.call_count, 1)

    def test_restore_wrong_dns_mode_is_not_success(self):
        def call(cli, *args, **kwargs):
            return {("mode", "--help"): "warp proxy", ("status",): "Connected", ("settings",): "Mode: WarpWithDnsOverHttps\n"}.get(args, "Success")
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call), patch.object(warp.time,"monotonic",side_effect=[0,0,31]), patch.object(warp.time,"sleep"), self.assertRaisesRegex(ValueError, "restoration timed out"):
            warp.restore()
    def cli_fixture(self, mode="full", status="Disconnected", supported=True):
        calls = []
        def call(cli, *args, **kwargs):
            nonlocal mode, status
            calls.append(args)
            if args == ("--version",): return "warp-cli fixture"
            if args == ("mode", "--help"): return "proxy warp" if supported else "warp"
            if args == ("proxy", "--help"): return "port"
            if args == ("settings",): return "Mode: WarpProxy on port 40000\n" if mode == "proxy" else "Mode: WarpWithDnsOverHttps\n"
            if args == ("status",): return "Status update: " + status
            if args == ("mode", "proxy"): mode = "proxy"
            if args == ("connect",): status = "Connected"
            if args == ("disconnect",): status = "Disconnected"
            return "Success"
        return calls, call

    def test_button_sequence_disconnects_full_tunnel_before_proxy_connect(self):
        calls, call = self.cli_fixture()
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call), patch.object(warp, "verify_trace", return_value=TRACE):
            result = warp.activate()
        mutating = [c for c in calls if c in [("disconnect",), ("mode", "proxy"), ("proxy", "port", "40000"), ("connect",)]]
        self.assertEqual(mutating, [("disconnect",), ("mode", "proxy"), ("proxy", "port", "40000"), ("connect",)])
        self.assertTrue(result["reconfigured"])

    def test_healthy_proxy_is_idempotent_without_disconnect(self):
        calls, call = self.cli_fixture(mode="proxy", status="Connected")
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call), patch.object(warp, "verify_trace", return_value=TRACE):
            self.assertFalse(warp.activate()["reconfigured"])
        self.assertNotIn(("disconnect",), calls)
        self.assertNotIn(("connect",), calls)

    def test_unsupported_cli_fails_before_network_mutation(self):
        calls, call = self.cli_fixture(supported=False)
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call), self.assertRaisesRegex(ValueError, "no connection settings changed"):
            warp.activate()
        self.assertNotIn(("disconnect",), calls)

    def test_failed_trace_disconnects_new_proxy_and_never_selects_full_tunnel(self):
        calls, call = self.cli_fixture()
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call), patch.object(
            warp, "verify_trace", side_effect=ValueError("off")), patch("time.monotonic", side_effect=[0, 0, 100]), patch("time.sleep"), self.assertRaisesRegex(ValueError, "no direct fallback"):
            warp.activate()
        self.assertEqual(calls[-1], ("disconnect",))
        self.assertNotIn(("mode", "warp"), calls)

    def test_explicit_disconnect_does_not_change_to_full_tunnel(self):
        calls, call = self.cli_fixture(mode="proxy", status="Connected")
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call):
            self.assertFalse(warp.deactivate()["connected"])
        self.assertEqual(calls, [("disconnect",), ("status",)])

    def test_trace_uses_remote_hostname_tls_and_does_not_return_ip(self):
        for flag in ["on", "off"]:
            body = f"ip=fixture-private-value\nwarp={flag}\n".encode()
            tls = MagicMock()
            tls.makefile.return_value = io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(body)).encode() + b"\r\n\r\n" + body)
            context = MagicMock()
            context.wrap_socket.return_value.__enter__.return_value = tls
            sock = MagicMock()
            with self.subTest(flag=flag), patch("socket.create_connection", return_value=sock) as dial, patch.object(warp, "socks_connect") as connect, patch(
                "ssl.create_default_context", return_value=context), patch("socket.getaddrinfo", side_effect=AssertionError("local target DNS lookup")):
                if flag == "off":
                    with self.assertRaisesRegex(ValueError, "did not confirm WARP"):
                        warp.verify_trace()
                else:
                    result = warp.verify_trace()
                    self.assertTrue(result["tls_verified"])
                    self.assertNotIn("ip", result)
                connect.assert_called_once_with(sock.__enter__.return_value, "www.cloudflare.com", 443)
                context.wrap_socket.assert_called_once_with(sock.__enter__.return_value, server_hostname="www.cloudflare.com")
                dial.assert_called_once_with(("127.0.0.1", 40000), timeout=5.0)

    def test_health_check_preserves_healthy_client_and_only_reconnects_disconnected_proxy(self):
        for status, expected in [('Connected',False),('Disconnected',True)]:
            calls,call=self.cli_fixture(mode='proxy',status=status)
            with patch.object(warp,'resolve_cli',return_value='warp-cli'),patch.object(warp,'command',side_effect=call):
                self.assertEqual(expected,warp.maintain_proxy()['reconnecting'])
            self.assertNotIn(('disconnect',),calls)
            self.assertNotIn(('mode','proxy'),calls)
            self.assertEqual(expected,('connect',) in calls)

    def test_transient_cli_timeouts_preserve_session_and_retry_without_disconnect(self):
        import subprocess
        for failing in ('settings','status','connect'):
            calls,fixture=self.cli_fixture(mode='proxy',status='Disconnected')
            def command(cli,*args,**kwargs):
                if args==(failing,):raise subprocess.TimeoutExpired('warp-cli',2)
                return fixture(cli,*args,**kwargs)
            with patch.object(warp,'resolve_cli',return_value='warp-cli'),patch.object(warp,'command',side_effect=command):
                self.assertIn('warning',warp.maintain_proxy())
            self.assertNotIn(('disconnect',),calls)

    def test_external_full_tunnel_change_is_an_error_not_a_silent_toggle(self):
        calls,call=self.cli_fixture(mode='full',status='Connected')
        with patch.object(warp,'resolve_cli',return_value='warp-cli'),patch.object(warp,'command',side_effect=call),self.assertRaisesRegex(ValueError,'mode changed'):
            warp.maintain_proxy()
        self.assertEqual([('settings',)],calls)

    def test_status_does_not_treat_disconnected_as_connected(self):
        self.assertFalse(warp.connected("Status update: Disconnected"))
        self.assertTrue(warp.connected("Status update: Connected\n"))

    def test_packaged_app_adds_ca_trust_without_disabling_tls(self):
        body = b"warp=on\n"
        tls = MagicMock()
        tls.makefile.return_value = io.BytesIO(b"HTTP/1.1 200 OK\r\nContent-Length: 8\r\n\r\n" + body)
        context = MagicMock()
        context.wrap_socket.return_value.__enter__.return_value = tls
        with patch.object(warp.sys, "frozen", True, create=True), patch.object(warp.sys, "_MEIPASS", "/fixture/internal", create=True), patch(
            "socket.create_connection"), patch.object(warp, "socks_connect"), patch("ssl.create_default_context", return_value=context):
            warp.verify_trace()
        context.load_verify_locations.assert_called_once_with(cafile=str(Path("/fixture/internal") / "cacert.pem"))


if __name__ == "__main__":
    unittest.main()

class TraceDeadlineTests(unittest.TestCase):
    def test_slow_http_response_has_an_absolute_deadline(self):
        import threading,time
        stopped=threading.Event();tls=MagicMock();tls.shutdown.side_effect=lambda *a:stopped.set()
        context=MagicMock();context.wrap_socket.return_value.__enter__.return_value=tls
        response=MagicMock()
        def read(*args):
            stopped.wait(2);raise TimeoutError('slow response fixture')
        response.read.side_effect=read
        begin=time.monotonic()
        with patch('socket.create_connection'),patch.object(warp,'socks_connect'),patch('ssl.create_default_context',return_value=context),patch('http.client.HTTPResponse',return_value=response),self.assertRaises(TimeoutError):
            warp.verify_trace(timeout=.15)
        self.assertLess(time.monotonic()-begin,1)

class RestorationTests(unittest.TestCase):
    def test_connected_status_does_not_prematurely_fail_during_mode_transition(self):
        calls=[];settings=iter(['Mode: WarpProxy','Mode: WarpProxy','Mode: Warp'])
        def command(cli,*args,**kw):
            calls.append(args)
            if args==('mode','--help'):return 'warp proxy'
            if args==('settings',):return next(settings)
            if args==('status',):return 'Status update: Connected'
            return 'Success'
        with patch.object(warp,'resolve_cli',return_value='fixture'),patch.object(warp,'command',side_effect=command),patch.object(warp.time,'sleep'):
            self.assertTrue(warp.restore()['restored'])
        self.assertEqual(calls.count(('disconnect',)),1)

    def test_restoration_retry_preserves_already_restored_connection(self):
        calls=[]
        def command(cli,*args,**kw):
            calls.append(args)
            return 'warp proxy' if args==('mode','--help') else 'Mode: Warp' if args==('settings',) else 'Status update: Connected'
        with patch.object(warp,'resolve_cli',return_value='fixture'),patch.object(warp,'command',side_effect=command):
            self.assertFalse(warp.restore()['reconfigured'])
        self.assertNotIn(('disconnect',),calls);self.assertNotIn(('connect',),calls)

class ProxyHealthAndServiceTests(unittest.TestCase):
    def test_connected_without_socks_is_not_healthy_and_does_not_disconnect(self):
        def command(cli,*args,**kw):return 'Mode: WarpProxy on port 40000' if args==('settings',) else 'Status update: Connected'
        with patch.object(warp,'resolve_cli',return_value='fixture'),patch.object(warp,'command',side_effect=command) as call,patch.object(warp,'proxy_ready',side_effect=ConnectionRefusedError):
            self.assertFalse(warp.maintain_proxy()['healthy'])
        self.assertNotIn(('disconnect',),[c.args[1:] for c in call.call_args_list])

    def test_connecting_status_does_not_reissue_connect(self):
        def command(cli,*args,**kw):return 'Mode: WarpProxy on port 40000' if args==('settings',) else 'Status update: Connecting'
        with patch.object(warp,'resolve_cli',return_value='fixture'),patch.object(warp,'command',side_effect=command) as call:
            self.assertFalse(warp.maintain_proxy()['healthy'])
        self.assertEqual(call.call_count,2)

    def test_riot_check_uses_proxy_doh_ip_and_validates_original_tls_host(self):
        tls=MagicMock();tls.makefile.return_value=io.BytesIO(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n')
        context=MagicMock();context.wrap_socket.return_value.__enter__.return_value=tls
        sock=MagicMock()
        with patch('socket.create_connection',return_value=sock),patch.object(warp,'resolve_origin',return_value='8.8.4.4'),patch.object(warp,'socks_connect') as connect,patch('ssl.create_default_context',return_value=context):
            result=warp.verify_client_service()
        self.assertTrue(result['tls_verified']);self.assertFalse(result['game_or_statistics_verified']);self.assertEqual(result['http_status'],403)
        connect.assert_called_once_with(sock.__enter__.return_value,'8.8.4.4',443)
        context.wrap_socket.assert_called_once_with(sock.__enter__.return_value,server_hostname='auth.riotgames.com')

    def test_riot_failure_does_not_fall_back_to_direct(self):
        with patch('socket.create_connection',side_effect=ConnectionRefusedError) as connect,self.assertRaisesRegex(ValueError,'no direct fallback'):warp.verify_client_service()
        self.assertEqual(connect.call_args.args[0],('127.0.0.1',40000));self.assertLessEqual(connect.call_args.kwargs['timeout'],8)
