"""Control the separately installed WARP client; never implement its tunnel."""
import http.client
import json
from pathlib import Path
import platform
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time

from .probe import socks_connect, proxy_ready


def progress(phase, completed):
    print(json.dumps({"event": "progress", "phase": phase, "completed": completed}), flush=True)


def resolve_cli(value=None):
    candidate = value or shutil.which("warp-cli")
    if not candidate and platform.system() == "Darwin":
        candidate = "/Applications/Cloudflare WARP.app/Contents/Resources/warp-cli"
    if not candidate or not Path(candidate).is_file():
        raise ValueError("warp-cli unavailable; install WARP or pass --warp-cli with its installed path")
    return str(candidate)


def command(cli, *arguments, timeout=10):
    result = subprocess.run([cli, *arguments], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # WARP output can include account metadata. Record the failing command,
        # not raw settings/account data or a silently selected direct path.
        raise ValueError(f"WARP command failed: {' '.join(arguments)} (exit {result.returncode}); check warp-cli mode --help / proxy --help")
    return result.stdout


def proxy_mode(settings, port):
    match = re.search(r"^\s*(?:\([^\n)]*\)\s*)?Mode:\s*(WarpProxy)(?:\s+on\s+port\s+(\d+))?\s*$", settings, re.MULTILINE)
    return bool(match and (match.group(2) is None or int(match.group(2)) == port))


def connected(output):
    return bool(re.search(r"^\s*(?:Status(?: update)?:\s*)?Connected\s*$", output, re.MULTILINE | re.IGNORECASE))


def verify_trace(port=40000, timeout=5.0):
    """TLS-verified HTTPS through SOCKS with remote hostname resolution.

    Only return the WARP flag. The trace's public IP/location are not logged.
    There is intentionally no direct-network retry.
    """
    host = "www.cloudflare.com"
    with socket.create_connection(("127.0.0.1", port), timeout=timeout) as sock:
        socks_connect(sock, host, 443)
        context = ssl.create_default_context()
        if getattr(sys, "frozen", False):
            # The standalone Mac may have no Python/OpenSSL CA installation.
            # Add the build's pinned public CA bundle, never disable TLS checks.
            context.load_verify_locations(cafile=str(Path(sys._MEIPASS) / "cacert.pem"))
        with context.wrap_socket(sock, server_hostname=host) as tls:
            tls.sendall(f"GET /cdn-cgi/trace HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\nAccept-Encoding: identity\r\n\r\n".encode("ascii"))
            response = http.client.HTTPResponse(tls)
            response.begin()
            body = response.read(8193)
            if response.status != 200 or len(body) > 8192:
                raise ValueError("WARP trace HTTPS request failed")
    values = dict(line.split("=", 1) for line in body.decode("utf-8", "strict").splitlines() if "=" in line)
    if values.get("warp") not in {"on", "plus"}:
        raise ValueError("SOCKS endpoint did not confirm WARP (warp=on/plus required)")
    return {"via": "socks5h", "proxy": f"127.0.0.1:{port}", "warp": values["warp"],
            "tls_verified": True, "direct_fallback": False}


def activate(port=40000, warp_cli=None, wait_seconds=30, notify=None):
    emit = notify or (lambda *args: None)
    emit("cli_check", 0)
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("proxy port must be 1024..65535")
    if not 1 <= wait_seconds <= 60:
        raise ValueError("wait_seconds must be 1..60")
    cli = resolve_cli(warp_cli)
    command(cli, "--version")
    mode_help = command(cli, "mode", "--help")
    proxy_help = command(cli, "proxy", "--help")
    if not re.search(r"\bproxy\b", mode_help) or not re.search(r"\bport\b", proxy_help):
        raise ValueError("installed WARP CLI does not advertise mode proxy / proxy port; no connection settings changed")
    emit("proxy_connect", 1)
    settings = command(cli, "settings")
    current_status = command(cli, "status")
    changed = not proxy_mode(settings, port)
    if not changed and connected(current_status):
        # Repeated clicks must not tear down healthy client TCP sessions.
        proxy_ready(port)
        emit("tls_verify", 2)
        result = verify_trace(port)
        emit("warp_ready", 3)
        return {**result, "mode": "WarpProxy", "reconfigured": False}
    try:
        if changed:
            command(cli, "disconnect")
            command(cli, "mode", "proxy")
            command(cli, "proxy", "port", str(port))
        command(cli, "connect")
        deadline = time.monotonic() + wait_seconds
        last_error = "WARP has not connected"
        while time.monotonic() < deadline:
            if connected(command(cli, "status", timeout=5)):
                if not proxy_mode(command(cli, "settings", timeout=5), port):
                    raise ValueError("WARP did not apply the requested Local Proxy mode/port")
                try:
                    proxy_ready(port)
                    emit("tls_verify", 2)
                    result = verify_trace(port)
                    emit("warp_ready", 3)
                    return {**result, "mode": "WarpProxy", "reconfigured": changed}
                except (OSError, ValueError, http.client.HTTPException) as exc:
                    last_error = type(exc).__name__ + ": WARP trace verification failed"
            time.sleep(.5)
        raise ValueError(f"WARP proxy readiness timed out: {last_error}; no direct fallback")
    except Exception:
        if changed:
            try:
                command(cli, "disconnect")
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
        # Never restore a full tunnel behind the user's back after a failure.
        raise


def inspect(port=40000, warp_cli=None):
    cli = resolve_cli(warp_cli)
    if not proxy_mode(command(cli, "settings"), port):
        raise ValueError("WARP is not configured for the requested Local Proxy endpoint")
    if not connected(command(cli, "status")):
        raise ValueError("WARP is not Connected")
    return {**verify_trace(port), "mode": "WarpProxy"}


def deactivate(warp_cli=None):
    cli = resolve_cli(warp_cli)
    command(cli, "disconnect")
    output = command(cli, "status")
    if not re.search(r"^\s*(?:Status(?: update)?:\s*)?Disconnected(?:[.:\s].*)?$", output, re.MULTILINE | re.IGNORECASE):
        raise ValueError("WARP did not confirm Disconnected after disconnect")
    return {"connected": False, "mode_restored_to_full_tunnel": False,
            "note": "WARP disconnected; Local Proxy mode is retained. No direct fallback was configured."}


def restore(warp_cli=None, wait_seconds=30):
    """Explicit user-requested return to Traffic and DNS (UDP), never a failure fallback."""
    cli = resolve_cli(warp_cli)
    help_text = command(cli, "mode", "--help")
    if not re.search(r"(?<![\w+\-])warp(?![\w+\-])", help_text):
        raise ValueError("installed WARP CLI does not advertise UDP mode warp; restoration was not attempted")
    command(cli, "disconnect")
    command(cli, "mode", "warp")
    command(cli, "connect")
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if connected(command(cli, "status", timeout=5)):
            settings = command(cli, "settings", timeout=5)
            if re.search(r"^\s*(?:\([^\n)]*\)\s*)?Mode:\s*Warp\s*$", settings, re.MULTILINE):
                return {"connected": True, "mode": "Warp", "dns_transport": "UDP", "restored": True}
            raise ValueError("WARP did not confirm UDP Traffic and DNS mode; inspect warp-cli settings")
        time.sleep(.5)
    raise ValueError("WARP UDP restoration timed out; inspect warp-cli status/settings")
