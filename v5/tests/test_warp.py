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
        def call(cli, *args, **kwargs):
            calls.append(args)
            return {("mode", "--help"): "warp warp+doh proxy", ("status",): "Connected", ("settings",): "Mode: Warp\n"}.get(args, "Success")
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call):
            self.assertTrue(warp.restore()["restored"])
        self.assertEqual(calls[1:4], [("disconnect",), ("mode", "warp"), ("connect",)])

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
        with patch.object(warp, "resolve_cli", return_value="warp-cli"), patch.object(warp, "command", side_effect=call), self.assertRaisesRegex(ValueError, "did not confirm UDP"):
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
