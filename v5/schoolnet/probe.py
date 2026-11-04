"""Bounded SOCKS and TCP probes. TCP timings are not game ping or UDP loss."""
import ipaddress
import math
import socket
import statistics
import struct
import time


def recv_exact(sock, count):
    data = bytearray()
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise OSError("SOCKS server closed the connection")
        data.extend(part)
    return bytes(data)


def negotiate(sock):
    sock.sendall(b"\x05\x01\x00")
    if recv_exact(sock, 2) != b"\x05\x00":
        raise OSError("SOCKS5 unauthenticated mode was not accepted")


def proxy_ready(port, timeout=3.0):
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
        negotiate(sock)


def socks_connect(sock, host, port):
    negotiate(sock)
    try:
        address = ipaddress.ip_address(host)
        encoded = (b"\x01" if address.version == 4 else b"\x04") + address.packed
    except ValueError:
        encoded_host = host.encode("idna")
        if not 1 <= len(encoded_host) <= 255:
            raise ValueError("invalid SOCKS destination")
        encoded = b"\x03" + bytes([len(encoded_host)]) + encoded_host
    sock.sendall(b"\x05\x01\x00" + encoded + struct.pack("!H", port))
    version, reply, reserved, kind = recv_exact(sock, 4)
    if version != 5 or reserved != 0 or reply != 0:
        raise OSError(f"SOCKS CONNECT failed (reply={reply})")
    if kind == 1:
        size = 4
    elif kind == 4:
        size = 16
    elif kind == 3:
        size = recv_exact(sock, 1)[0]
    else:
        raise OSError("invalid SOCKS reply address type")
    recv_exact(sock, size + 2)


def summarize(values, attempts):
    if not values:
        return {"successes": 0, "attempts": attempts, "failure_rate": 1.0,
                "median_ms": None, "p95_ms": None, "successive_difference_ms": None}
    ordered = sorted(values)
    differences = [abs(a - b) for a, b in zip(values, values[1:])]
    return {"successes": len(values), "attempts": attempts,
            "failure_rate": (attempts - len(values)) / attempts,
            "median_ms": round(statistics.median(values), 3),
            "p95_ms": round(ordered[math.ceil(.95 * len(ordered)) - 1], 3),
            "successive_difference_ms": round(statistics.mean(differences), 3) if differences else None}


def benchmark(host, port, samples=5, proxy_port=40000, timeout=3.0):
    if not 1 <= samples <= 20 or not 1 <= port <= 65535 or not 0 < timeout <= 10:
        raise ValueError("samples=1..20, port=1..65535, timeout=(0,10]")
    # Same literal destination for both paths; exclude local DNS lookup from timings.
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    target_ip = addresses[0][4][0]
    values = {"direct": [], "warp_proxy": []}
    failures = {"direct": [], "warp_proxy": []}
    for i in range(samples):
        # Alternate order to reduce systematic warm-cache/order bias.
        for path in (["direct", "warp_proxy"] if i % 2 == 0 else ["warp_proxy", "direct"]):
            started = time.perf_counter()
            try:
                endpoint = (target_ip, port) if path == "direct" else ("127.0.0.1", proxy_port)
                with socket.create_connection(endpoint, timeout=timeout) as sock:
                    if path == "warp_proxy":
                        socks_connect(sock, target_ip, port)
                values[path].append((time.perf_counter() - started) * 1000)
            except OSError as exc:
                failures[path].append(type(exc).__name__)
    return {"measurement": "tcp_connect_including_socks_setup_not_game_rtt",
            "target_ip": target_ip, "port": port,
            "direct_path_verified": False,
            "note": "direct means an ordinary OS socket; turn off other full-tunnel VPNs. Failures are not UDP packet loss.",
            "paths": {p: {**summarize(values[p], samples), "errors": failures[p]} for p in values}}
