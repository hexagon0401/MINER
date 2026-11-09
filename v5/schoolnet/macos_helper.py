"""A root-owned launchd helper exposing only this user's MINER lifecycle."""
import json
import ctypes
import os
from pathlib import Path
import plistlib
import socket
import stat
import struct
import subprocess
import sys
import time

from . import __version__
from .config import Profile
from . import macos_service as service
from .runtime import write_json

LABEL = service.LABEL + ".helper"
PLIST = Path("/Library/LaunchDaemons") / (LABEL + ".plist")
SOCKET = Path("/var/run") / (LABEL + ".sock")
LIMIT = 16384


def peer_uid(connection):
    if sys.platform == "darwin":
        function = ctypes.CDLL(None, use_errno=True).getpeereid
        function.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]
        function.restype = ctypes.c_int
        uid, gid = ctypes.c_uint(), ctypes.c_uint()
        if function(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0:
            raise OSError(ctypes.get_errno(), "Unable to authenticate helper peer")
        return uid.value
    if hasattr(connection, "getpeereid"):
        return connection.getpeereid()[0]
    return struct.unpack("3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1]


def receive(connection):
    buffer = bytearray()
    while not buffer.endswith(b"\n"):
        chunk = connection.recv(4096)
        if not chunk or len(buffer) + len(chunk) > LIMIT:
            raise ValueError("Incomplete or oversized helper request")
        buffer.extend(chunk)
    value = json.loads(buffer)
    if not isinstance(value, dict):
        raise ValueError("Helper request must be an object")
    return value


def request(operation, profile=None):
    entry = SOCKET.lstat()
    if not stat.S_ISSOCK(entry.st_mode) or entry.st_uid != os.getuid():
        raise ValueError("Helper endpoint does not belong to this user")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(35)
        connection.connect(str(SOCKET))
        if peer_uid(connection) != 0:
            raise ValueError("Helper is not a root-owned process")
        message = {"operation": operation, "version": __version__}
        if profile is not None:
            message["profile"] = profile.to_dict()
        connection.sendall(json.dumps(message).encode() + b"\n")
        response = receive(connection)
    if not response.get("ok"):
        raise ValueError(response.get("error", "Helper request failed"))
    if response.get("version") != __version__:
        raise ValueError("Helper update needs one administrator approval")
    return response


def dispatch(message, uid, owner):
    if uid != owner:
        raise ValueError("Only the installing user can control MINER")
    operation = message.get("operation")
    if operation == "status":
        result = service.status()
    elif operation == "stop":
        result = service.stop()
    elif operation == "start":
        profile = Profile(**message.get("profile", {})).validate()
        if profile.platform != "macos":
            raise ValueError("Helper only accepts macOS profiles")
        if service.status()["running"]:
            raise ValueError("MINER is already running")
        result = service.start_installed(profile)
    else:
        raise ValueError("Unsupported helper command")
    return {"ok": True, "version": __version__, "helper_pid": os.getpid(), **result}


def serve(owner):
    if os.geteuid() != 0 or type(owner) is not int or owner <= 0:
        raise ValueError("Helper requires root and a non-root installing user")
    from .network_dns import Lease
    if not service.status()['running']:Lease.recover(service.BASE/'profile')
    SOCKET.unlink(missing_ok=True)
    last_recovery=time.monotonic()
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(SOCKET))
        os.chown(SOCKET, owner, -1)
        SOCKET.chmod(0o600)
        server.listen(4)
        server.settimeout(1)
        while True:
            try:connection, _ = server.accept()
            except socket.timeout:
                from .network_dns import JOURNAL
                if time.monotonic()-last_recovery>=5 and (service.BASE/'profile'/JOURNAL).exists():
                    if not service.status()['running']:Lease.recover(service.BASE/'profile')
                    last_recovery=time.monotonic()
                continue
            with connection:
                connection.settimeout(5)
                try:
                    message = receive(connection)
                    if message.get("version") != __version__: raise ValueError("Helper update needs administrator approval")
                    response = dispatch(message, peer_uid(connection), owner)
                except (ValueError, TypeError, OSError, subprocess.SubprocessError) as exc:
                    response = {"ok": False, "error": str(exc), "version": __version__}
                try:
                    connection.sendall(json.dumps(response).encode() + b"\n")
                except OSError:
                    pass


def remove():
    if os.geteuid() != 0:
        raise ValueError("Administrator approval required to remove helper")
    if PLIST.exists():
        if PLIST.is_symlink(): raise ValueError("Helper plist must not be a symlink")
        data = plistlib.loads(PLIST.read_bytes())
        expected = str(service.BASE / "runtime/schoolnet-cli")
        if data.get("Label") != LABEL or data.get("ProgramArguments", [None])[0] != expected:
            raise ValueError("Unrecognized helper plist; preserving it")
        subprocess.run(["/bin/launchctl", "bootout", f"system/{LABEL}"], capture_output=True, timeout=10)
        PLIST.unlink()
        SOCKET.unlink(missing_ok=True)


def install(resources, profile, owner):
    if os.geteuid() != 0 or owner is None or owner <= 0:
        raise ValueError("Administrator approval and installing user required")
    if service.status()["running"]:
        raise ValueError("Stop MINER before installing or upgrading the helper")
    remove()
    base = service.prepare(resources, profile)
    # No engine starts at login/boot: only the authenticated control socket does.
    data = {"Label": LABEL, "ProgramArguments": [str(base / "runtime/schoolnet-cli"),
            "desktop", "helper-serve", "--owner", str(owner)], "RunAtLoad": True,
            "KeepAlive": True, "UserName": "root", "Umask": 0o077,
            "EnvironmentVariables": {"PATH":"/usr/bin:/bin:/usr/sbin:/sbin"},
            "StandardOutPath": str(base / "helper.log"), "StandardErrorPath": str(base / "helper.log")}
    PLIST.write_bytes(plistlib.dumps(data))
    PLIST.chmod(0o600)
    subprocess.run(["/bin/launchctl", "bootstrap", "system", str(PLIST)], check=True, capture_output=True, timeout=10)
    deadline = time.monotonic() + 10
    while not SOCKET.exists():
        if time.monotonic() > deadline:
            raise ValueError("Helper did not become ready; retry installation")
        time.sleep(.1)
    return {"ok": True, "version": __version__, "owner": owner}
