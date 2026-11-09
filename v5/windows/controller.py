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
from schoolnet.runtime import check_engine, instance_lock, is_admin, write_json


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


def session(directory, engine, stop, emit, restore_only=False, emergency=None):
    from dataclasses import replace
    from schoolnet.dns_forwarder import Forwarder
    from schoolnet.network_dns import Lease, probe_dns
    from schoolnet.dns_guard import spawn as spawn_guard
    emergency = emergency or threading.Event()
    if not is_admin(): raise ValueError('Administrator permission is required. Restart MINER as administrator.')
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    profile=None if restore_only else prepare(directory)
    marker=directory/'session.json'
    with instance_lock(directory):
        child=job=guardian=relay=lease=None
        failure=None;cleanup=[];disconnected=False
        write_json(marker,{'version':2,'unfinished':True})
        try:
            if not restore_only:
                warp.activate(profile.proxy_port,notify=emit)
                if not stop.is_set():
                    emit('engine_check',3)
                    lease=Lease(directory);servers=lease.prepare()
                    relay=Forwarder(servers);relay.__enter__()
                    profile=replace(profile,dns_forward_port=relay.port)
                    write_json(directory/'profile.json',profile.to_dict())
                    write_json(directory/'sing-box.json',build_config(profile))
                    check_engine(str(engine),directory/'sing-box.json')
                    emit('engine_start',4)
                    from windows.process import Job
                    job=Job()
                    with (directory/'engine.log').open('w',encoding='utf-8') as log:
                        child=subprocess.Popen([str(Path(engine).resolve()),'run','-c',str(directory/'sing-box.json')],cwd=directory,
                            stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                        job.assign(child)
                        deadline=time.monotonic()+20
                        while not stop.is_set() and child.poll() is None and not probe_dns():
                            if time.monotonic()>deadline:raise ValueError('Selective DNS/TUN readiness timed out')
                            stop.wait(.1)
                        if child.poll() is not None:raise ValueError('Network engine exited during startup; see engine.log')
                        if not stop.is_set():
                            guardian=spawn_guard(directory,child.pid)
                            lease.activate()
                            emit('running',5)
                        last_health=time.monotonic()
                        while child.poll() is None and not stop.wait(.25):
                            if time.monotonic()-last_health>=15:
                                warp.maintain_proxy(profile.proxy_port)
                                last_health=time.monotonic()
                        if not stop.is_set():raise ValueError('Network engine exited. Ordinary DNS is being recovered.')
        except Exception as exc:
            failure=exc
        finally:
            # Restore the original DNS before removing the interface or its
            # forwarder. Even startup/engine errors execute this cleanup path.
            try:
                if lease:lease.close()
                else:Lease.recover(directory)
            except Exception as exc:cleanup.append(str(exc))
            try:stop_engine(child)
            except Exception as exc:cleanup.append(str(exc))
            if job:job.close()
            if relay:relay.__exit__(None,None,None)
            if guardian:
                try:guardian.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # The independent guardian may still be restoring DNS; never
                    # kill it and strand the user's connection.
                    cleanup.append('DNS recovery supervisor is still active')
            if emergency.is_set():
                emit('disconnecting',0)
                try:warp.deactivate();disconnected=True
                except Exception as exc:cleanup.append(str(exc))
            elif restore_only or stop.is_set():
                emit('restoring',0)
                try:warp.restore()
                except Exception as exc:
                    if not emergency.is_set():cleanup.append(str(exc))
                if emergency.is_set():
                    try:warp.deactivate();disconnected=True
                    except Exception as exc:cleanup.append(str(exc))
            if cleanup:raise ValueError('Recovery needs retry: '+'; '.join(cleanup)) from failure
        if failure is not None and not emergency.is_set():raise failure
        marker.unlink(missing_ok=True)
        emit('disconnected' if disconnected else 'restored',0)
