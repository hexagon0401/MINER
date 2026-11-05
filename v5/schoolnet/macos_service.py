"""macOS engine session; optional persistent control helper never starts a tunnel at boot."""
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import time

from . import __version__
from .config import build_config
from .runtime import check_engine, doctor, instance_lock, load_profile, write_json

LABEL = "org.schoolnet.v5.alpha"
BASE = Path("/Library/Application Support/SchoolNet v5 Alpha")
MARKER = ".schoolnet-v5-managed.json"
APP_RESOURCES = Path("/Applications/MINER.app/Contents/Resources")


def owned_base(base=None):
    """Never delete a preexisting directory that is not our own managed tree."""
    base = base if base is not None else BASE
    if base.is_symlink():
        raise ValueError("managed service directory must not be a symlink")
    marker = base / MARKER
    if base.exists():
        if not marker.is_file() or marker.is_symlink():
            raise ValueError("existing service directory is not marked as SchoolNet v5; preserving it")
        data = json.loads(marker.read_text(encoding="utf-8"))
        if data.get("id") != LABEL:
            raise ValueError("service directory ownership marker differs; preserving it")
    return base


def status():
    result = subprocess.run(["/bin/launchctl", "print", f"system/{LABEL}"],
                            capture_output=True, text=True, timeout=5)
    match = re.search(r"^\s*pid = (\d+)\s*$", result.stdout, re.MULTILINE)
    return {"running": bool(result.returncode == 0 and match),
            "pid": int(match.group(1)) if match else None,
            "log": str(BASE / "engine.log")}


def stop():
    before = status()
    if before["running"]:
        subprocess.run(["/bin/launchctl", "remove", LABEL], check=True,
                       capture_output=True, text=True, timeout=10)
    else:
        # Remove an exited launchd job too, before the next submit.
        subprocess.run(["/bin/launchctl", "remove", LABEL], capture_output=True, timeout=10)
    profile = BASE / "profile"
    if profile.exists():
        deadline = time.monotonic() + 15
        while True:
            try:
                with instance_lock(profile):
                    break
            except ValueError:
                if time.monotonic() >= deadline:
                    raise ValueError("engine cleanup still active; keeping installed files and logs")
                time.sleep(.1)
    return {"running": False, "message": "Stopped. WARP remains installed and enabled as a local proxy."}


def install_runtime(base, resources, profile):
    """Stage an alpha upgrade before replacing only our managed runtime files."""
    stage = Path(tempfile.mkdtemp(prefix=".upgrade-", dir=base))
    replaced = []
    backups = {}
    try:
        shutil.copytree(resources / "runtime" / "schoolnet-cli", stage / "runtime", symlinks=False)
        (stage / "bin").mkdir()
        shutil.copy2(resources / "bin" / "sing-box", stage / "bin" / "sing-box")
        write_json(stage / "check.json", build_config(profile))
        check_engine(str(stage / "bin" / "sing-box"), stage / "check.json")
        for name in ["runtime", "bin"]:
            destination = base / name
            if destination.is_symlink():
                raise ValueError("managed runtime path must not be a symlink")
            if destination.exists():
                backup = stage / (name + ".previous")
                os.replace(destination, backup)
                backups[name] = backup
            os.replace(stage / name, destination)
            for path in [destination, *destination.rglob("*")]:
                path.chmod(0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644)
            replaced.append(name)
        write_json(base / MARKER, {"id": LABEL, "version": __version__})
    except Exception:
        for name in reversed(replaced):
            shutil.rmtree(base / name)
        for name, backup in backups.items():
            os.replace(backup, base / name)
        raise
    finally:
        shutil.rmtree(stage)


def prepare(resources, profile_dir):
    if resources is None or resources.resolve() != APP_RESOURCES:
        raise ValueError("Install MINER.app in /Applications before starting")
    if profile_dir is None:
        raise ValueError("missing user profile")
    profile = load_profile(profile_dir)
    if profile.platform != "macos":
        raise ValueError("the macOS app requires a macos profile")
    engine = resources / "bin" / "sing-box"
    doctor(profile_dir, str(engine))
    base = owned_base()
    if not base.exists():
        base.mkdir(mode=0o755)
        write_json(base / MARKER, {"id": LABEL, "version": __version__})
    marker = json.loads((base / MARKER).read_text(encoding="utf-8"))
    runtime = base / "runtime"
    # Copy bundled runtime to root-owned state. Never execute a user-selected binary.
    if marker["version"] != __version__ or not runtime.exists() or not (base / "bin" / "sing-box").exists():
        install_runtime(base, resources, profile)
    root_profile = base / "profile"
    root_profile.mkdir(exist_ok=True)
    write_json(root_profile / "profile.json", profile.to_dict())
    write_json(root_profile / "sing-box.json", build_config(profile))
    check_engine(str(base / "bin" / "sing-box"), root_profile / "sing-box.json")
    # Readable log for the desktop user; no Riot credentials/packet content is logged.
    log = base / "engine.log"
    if log.exists() and log.stat().st_size > 5 * 1024 * 1024:
        os.replace(log, base / "engine.previous.log")
    log.touch(exist_ok=True)
    log.chmod(0o644)
    return base


def start_installed(profile):
    """Persistent approval may execute only the installed root-owned runtime."""
    if platform.system() != "Darwin" or os.geteuid() != 0:
        raise ValueError("Installed engine requires the macOS root helper")
    base = owned_base()
    if status()["running"]: raise ValueError("MINER is already running")
    stop()
    directory = base / "profile"
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.is_symlink(): raise ValueError("Managed profile must not be a symlink")
    write_json(directory / "profile.json", profile.to_dict())
    write_json(directory / "sing-box.json", build_config(profile))
    engine = base / "bin/sing-box"
    check_engine(str(engine), directory / "sing-box.json")
    log = base / "engine.log"
    if log.exists() and log.stat().st_size > 5 * 1024 * 1024:
        os.replace(log, base / "engine.previous.log")
    offset = log.stat().st_size if log.exists() else 0
    command = ["/bin/launchctl", "submit", "-l", LABEL,
               "-o", str(base / "engine.log"), "-e", str(base / "engine.log"), "--",
               str(base / "runtime/schoolnet-cli"), "run", "--directory", str(directory),
               "--engine", str(engine), "--managed-helper"]
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        result = status()
        text = ""
        if log.exists():
            with log.open("rb") as stream:
                stream.seek(offset); text = stream.read().decode(errors="replace")
        if result["running"] and "sing-box started" in text and "inbound/tun" in text: return result
        if not result["running"] and text: raise ValueError("Installed engine exited during startup; inspect engine.log")
        time.sleep(.1)
    stop()
    raise ValueError("TUN readiness timed out; routing was stopped")


def manage(operation, resources=None, profile=None):
    if platform.system() != "Darwin":
        raise ValueError("desktop service commands are macOS-only")
    if operation == "status":
        print(json.dumps(status()))
        return 0
    if os.geteuid() != 0:
        raise ValueError("macOS administrator authorization is required")
    owned_base()
    if operation == "start":
        from .warp import progress
        progress("routing", 4)
        if status()["running"]:
            raise ValueError("MINER is already running")
        stop()
        base = prepare(resources, profile)
        command = ["/bin/launchctl", "submit", "-l", LABEL,
                   "-o", str(base / "engine.log"), "-e", str(base / "engine.log"), "--",
                   str(base / "runtime" / "schoolnet-cli"), "run",
                   "--directory", str(base / "profile"), "--engine", str(base / "bin" / "sing-box")]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
        # A PID is not functional readiness. Report only whether startup stayed alive.
        time.sleep(1)
        result = status()
        if not result["running"]:
            raise ValueError(f"engine exited during startup; inspect {base / 'engine.log'}")
        progress("running", 5)
        print(json.dumps(result))
    elif operation == "stop":
        print(json.dumps(stop()))
    elif operation == "uninstall":
        stop()
        from .macos_helper import remove
        remove()
        base = owned_base()
        if base.exists():
            shutil.rmtree(base)
        print(json.dumps({"removed": str(base), "warp_removed": False}))
    return 0
