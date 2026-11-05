"""Preflight and foreground lifecycle; never toggle WARP or rewrite OS DNS."""
from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import tempfile
import time

from .config import ENGINE_VERSION, Profile, build_config
from .probe import proxy_ready
from .warp import resolve_cli, verify_trace


def load_profile(directory):
    path = Path(directory).resolve() / "profile.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("profile.json must be an object")
    return Profile(**data).validate()


def write_json(path, data):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name+".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n"); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None: temporary.unlink(missing_ok=True)


def native_platform():
    return {"Darwin": "macos", "Windows": "windows"}.get(platform.system(), "unsupported")


def engine_path(value):
    resolved = shutil.which(value)
    if not resolved:
        raise ValueError("sing-box not found; install the pinned engine or pass --engine /absolute/path")
    return str(Path(resolved).resolve())


def check_engine(engine, config_path):
    version = subprocess.run([engine, "version"], capture_output=True, text=True, timeout=10, check=True)
    if not re.search(r"\bsing-box version " + re.escape(ENGINE_VERSION) + r"(?:\s|$)", version.stdout):
        raise ValueError(f"this alpha requires sing-box {ENGINE_VERSION}; engine upgrades need schema testing")
    subprocess.run([engine, "check", "-c", str(config_path)], capture_output=True,
                   text=True, timeout=10, check=True)


def warp_mode(warp_cli, expected_port=None):
    candidate = resolve_cli(warp_cli)
    result = subprocess.run([candidate, "settings"], capture_output=True, text=True, timeout=10, check=True)
    # Fail closed on unknown/localized CLI output; never infer mode from an open port.
    match = re.search(r"^\s*(?:\([^\n)]*\)\s*)?Mode:\s*([^\r\n]+)", result.stdout, re.MULTILINE)
    if not match or not re.match(r"WarpProxy(?:\s|$)", match.group(1)):
        raise ValueError("WARP Local proxy mode is not confirmed by warp-cli settings (expected Mode: WarpProxy)")
    port = re.search(r"\bport\s+(\d+)", match.group(1))
    if port and expected_port is not None and int(port.group(1)) != expected_port:
        raise ValueError("WARP proxy port differs from profile.json")
    return "WarpProxy"


def doctor(directory, engine="sing-box", warp_cli=None):
    directory = Path(directory).resolve()
    profile = load_profile(directory)
    checks = {}
    checks["native_platform"] = native_platform() == profile.platform
    # Re-render explicitly after profile edits. Do not run stale or arbitrary engine config.
    actual = json.loads((directory / "sing-box.json").read_text(encoding="utf-8"))
    if actual != build_config(profile):
        raise ValueError("sing-box.json does not match profile.json; run render first")
    resolved = engine_path(engine)
    check_engine(resolved, directory / "sing-box.json")
    checks["engine_schema"] = True
    warp_mode(warp_cli, profile.proxy_port)
    checks["warp_local_proxy_mode"] = True
    proxy_ready(profile.proxy_port)
    checks["socks5_greeting"] = True
    trace = verify_trace(profile.proxy_port)
    checks["warp_trace"] = trace["warp"] in {"on", "plus"}
    return {"preflight_ok": all(checks.values()), "checks": checks, "engine": resolved,
            "proxy": trace, "note": "WARP HTTPS was verified; this does not establish Riot media access, process matching, game RTT, or restoration."}


def is_admin():
    if os.name == "nt":
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    return os.geteuid() == 0


@contextmanager
def instance_lock(directory):
    # OS locks release on process exit, unlike PID files (no stale-PID killing).
    with (Path(directory) / "runtime.lock").open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            # Windows permits byte-range locks beyond EOF. Acquire before any
            # read/write: a second reader of the locked byte raises PermissionError.
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError("v5 is already running for this profile") from exc
        else:
            import fcntl
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ValueError("v5 is already running for this profile") from exc
        try:
            yield
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def run(directory, engine="sing-box", warp_cli=None):
    directory = Path(directory).resolve()
    with instance_lock(directory):
        result = doctor(directory, engine, warp_cli)
        if not result["preflight_ok"]:
            raise ValueError("this profile cannot run on this operating system")
        if not is_admin():
            raise ValueError("TUN startup requires root on macOS / Administrator on Windows")
        # Separate child group: controller forwards termination exactly once.
        options = {"start_new_session": True} if os.name != "nt" else {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        child = subprocess.Popen([result["engine"], "run", "-c", str(directory / "sing-box.json")], **options)
        previous = {}
        stop_deadline = None

        def stop(signum, frame):
            nonlocal stop_deadline
            if child.poll() is None and stop_deadline is None:
                stop_deadline = time.monotonic() + 10
                if os.name == "nt":
                    child.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    child.terminate()

        try:
            for signum in (signal.SIGINT, signal.SIGTERM):
                previous[signum] = signal.signal(signum, stop)
            print("Engine starting; verify client->warp and game->direct in its logs. Ctrl+C to stop.", flush=True)
            while True:
                try:
                    returncode = child.wait(timeout=0.5)
                    break
                except subprocess.TimeoutExpired:
                    if stop_deadline is not None and time.monotonic() >= stop_deadline:
                        child.kill()
                        child.wait()
                        print("Forced engine exit: check OS routes manually before continuing.", flush=True)
                        returncode = 1
                        break
        finally:
            if child.poll() is None:
                stop(None, None)
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                    print("Forced engine exit: check OS routes manually before continuing.", flush=True)
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        print("Engine exited; WARP proxy remains enabled. Verify restored routes/DNS on this OS.", flush=True)
        return returncode if returncode >= 0 else 128 - returncode
