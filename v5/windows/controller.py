"""Windows lifecycle: pinned engine, one profile, explicit restore, no direct fallback."""
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import time

from schoolnet import warp
from schoolnet.config import Profile, build_config
from schoolnet.runtime import doctor, instance_lock, is_admin, write_json


def prepare(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    profile_path = directory / 'profile.json'
    if profile_path.exists():
        profile = Profile(**json.loads(profile_path.read_text(encoding='utf-8'))).validate()
        if profile.platform != 'windows':
            raise ValueError('This profile is not for Windows')
    else:
        profile = Profile(platform='windows')
        write_json(profile_path, profile.to_dict())
    write_json(directory / 'sing-box.json', build_config(profile))
    return profile


def stop_engine(child):
    if child is None or child.poll() is not None:
        return
    child.send_signal(signal.CTRL_BREAK_EVENT)
    try:
        child.wait(timeout=10)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)
        raise ValueError('Engine forced to stop. Check Windows routes and DNS before reconnecting.')


def session(directory, engine, stop, emit, restore_only=False):
    if not is_admin():
        raise ValueError('Administrator permission is required. Restart MINER as administrator.')
    child = None
    directory = Path(directory)
    profile = prepare(directory)
    with instance_lock(directory):
        try:
            if not restore_only:
                warp.activate(profile.proxy_port, notify=emit)
                if not stop.is_set():
                    emit('engine_check', 3)
                    result = doctor(directory, str(engine))
                    if not result['preflight_ok']:
                        raise ValueError('Windows preflight failed')
                    emit('engine_start', 4)
                    with (directory / 'engine.log').open('w', encoding='utf-8') as log:
                        child = subprocess.Popen([str(engine), 'run', '-c', str(directory / 'sing-box.json')],
                            stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                        deadline = time.monotonic() + 20
                        ready = False
                        while child.poll() is None and not stop.wait(.15):
                            if not ready:
                                text = (directory / 'engine.log').read_text(encoding='utf-8', errors='replace')
                                if 'sing-box started' in text and 'inbound/tun' in text:
                                    ready = True
                                    emit('running', 5)
                                elif time.monotonic() >= deadline:
                                    raise ValueError('TUN readiness timed out. See engine.log')
                        if not stop.is_set():
                            raise ValueError('Network engine exited unexpectedly. See engine.log')
            # Only an explicit Stop/Close (or restore-only retry) restores full WARP.
            emit('restoring', 0)
            stop_engine(child)
            child = None
            warp.restore()
            emit('restored', 0)
        finally:
            stop_engine(child)
