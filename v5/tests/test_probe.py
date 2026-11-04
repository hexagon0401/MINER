import socket
import socketserver
import struct
import threading
import unittest
from contextlib import contextmanager

from schoolnet.probe import benchmark, negotiate, proxy_ready, recv_exact, socks_connect, summarize


class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        self.request.recv(1)


class SocksHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        if recv_exact(self.request, 3) != b"\x05\x01\x00":
            return
        # Fragment the negotiation reply to exercise stream reassembly.
        self.request.sendall(b"\x05")
        self.request.sendall(b"\x00")
        header = self.request.recv(4)
        if not header:
            return
        while len(header) < 4:
            header += recv_exact(self.request, 4 - len(header))
        _, command, _, kind = header
        if command != 1:
            return
        if kind == 1:
            target = socket.inet_ntop(socket.AF_INET, recv_exact(self.request, 4))
        elif kind == 4:
            target = socket.inet_ntop(socket.AF_INET6, recv_exact(self.request, 16))
        else:
            target = recv_exact(self.request, recv_exact(self.request, 1)[0]).decode()
        port = struct.unpack("!H", recv_exact(self.request, 2))[0]
        with socket.create_connection((target, port), timeout=2):
            self.server.connections.append((target, port))
            self.request.sendall(b"\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x00")


class Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


@contextmanager
def server(handler):
    with Server(("127.0.0.1", 0), handler) as instance:
        instance.connections = []
        thread = threading.Thread(target=instance.serve_forever, daemon=True)
        thread.start()
        try:
            yield instance.server_address[1]
        finally:
            instance.shutdown()
            thread.join(timeout=2)


class ProbeTests(unittest.TestCase):
    def test_real_socks_negotiation_and_tcp_comparison(self):
        with server(TCPHandler) as target, server(SocksHandler) as proxy:
            proxy_ready(proxy)
            result = benchmark("127.0.0.1", target, samples=3, proxy_port=proxy)
        for path in result["paths"].values():
            self.assertEqual(path["successes"], 3)
            self.assertEqual(path["failure_rate"], 0)
        self.assertFalse(result["direct_path_verified"])
        self.assertEqual(result["target_ip"], "127.0.0.1")

    def test_proxy_failure_is_not_success_or_udp_loss(self):
        with server(TCPHandler) as target:
            # Port has a listener but it does not speak SOCKS5.
            result = benchmark("127.0.0.1", target, samples=1, proxy_port=target, timeout=.3)
        self.assertEqual(result["paths"]["direct"]["successes"], 1)
        self.assertEqual(result["paths"]["warp_proxy"]["successes"], 0)
        self.assertIsNone(result["paths"]["warp_proxy"]["median_ms"])
        self.assertNotIn("packet_loss", result)

    def test_distribution_is_named_and_failure_aware(self):
        result = summarize([10, 50, 20], 4)
        self.assertEqual(result["median_ms"], 20)
        self.assertEqual(result["p95_ms"], 50)
        self.assertEqual(result["successive_difference_ms"], 35)
        self.assertEqual(result["failure_rate"], .25)
        self.assertIsNone(summarize([], 3)["median_ms"])

    def test_bounded_probe_inputs(self):
        for changes in [{"samples": 100}, {"samples": 0}, {"timeout": 0}, {"port": 0}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                benchmark("127.0.0.1", **{"port": 443, **changes})

    def test_eof_and_auth_rejection(self):
        left, right = socket.socketpair()
        try:
            right.sendall(b"\x05\xff")
            with self.assertRaises(OSError):
                negotiate(left)
            right.close()
            with self.assertRaises(OSError):
                recv_exact(left, 4)
        finally:
            left.close()
            right.close()


if __name__ == "__main__":
    unittest.main()
