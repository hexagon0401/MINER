"""Out-of-process Windows DNS recovery if the UI or its engine exits."""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .network_dns import Lease, journal_path


def spawn(directory, engine_pid, executable=None):
    if os.name!='nt': return None
    args=[str(executable or sys.executable)]
    if executable or getattr(sys,'frozen',False): args+=['--dns-guard']
    else: args+=['-m','schoolnet.dns_guard']
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateEventW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_wchar_p];kernel.CreateEventW.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    name='Local\\MINER.DNSGuard.'+uuid.uuid4().hex
    ready=kernel.CreateEventW(None,True,False,name)
    if not ready:raise ctypes.WinError(ctypes.get_last_error())
    args += [str(os.getpid()),str(engine_pid),name]
    child=None
    try:
        child=subprocess.Popen(args,creationflags=subprocess.CREATE_NO_WINDOW)
        if kernel.WaitForSingleObject(ready,10000)!=0:raise ValueError('DNS recovery supervisor did not become ready; DNS was not changed')
        return child
    except Exception:
        if child and child.poll() is None:child.terminate();child.wait(timeout=5)
        raise
    finally:kernel.CloseHandle(ready)


def run(parent,engine,ready_name=None):
    if os.name!='nt' or min(parent,engine)<=0:raise ValueError('Invalid recovery supervisor')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.c_uint];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_wchar_p];kernel.CreateMutexW.restype=ctypes.c_void_p
    handles=[kernel.OpenProcess(0x00100000,False,pid) for pid in (parent,engine)]
    mutex=kernel.CreateMutexW(None,False,'Global\\MINER.Beta1.Windows')
    path=journal_path(Path.home())
    try:
        if not all(handles) or not mutex:raise ctypes.WinError(ctypes.get_last_error())
        if ready_name:
            import re
            if not re.fullmatch(r'Local\\MINER\.DNSGuard\.[a-f0-9]{32}',ready_name):raise ValueError('Invalid recovery supervisor event')
            kernel.OpenEventW.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.c_wchar_p];kernel.OpenEventW.restype=ctypes.c_void_p
            kernel.SetEvent.argtypes=[ctypes.c_void_p]
            ready=kernel.OpenEventW(0x0002,False,ready_name)
            if not ready:raise ctypes.WinError(ctypes.get_last_error())
            try:
                if not kernel.SetEvent(ready):raise ctypes.WinError(ctypes.get_last_error())
            finally:kernel.CloseHandle(ready)
        # Parent journals before applying DNS. Wait until it either writes the
        # journal or exits; never restore a healthy session's network settings.
        deadline=time.monotonic()+45
        while not path.exists() and time.monotonic()<deadline:
            if any(not h or kernel.WaitForSingleObject(h,0)==0 for h in handles):return 0
            time.sleep(.1)
        if not path.exists():return 0
        while path.exists():
            if any(not h or kernel.WaitForSingleObject(h,0)==0 for h in handles):
                deadline=time.monotonic()+45
                while True:
                    try:Lease.recover(Path.home());return 0
                    except (OSError,ValueError,subprocess.SubprocessError):
                        if time.monotonic()>=deadline:raise
                        time.sleep(1)
            time.sleep(.5)
        return 0
    finally:
        for handle in [*handles,mutex]:
            if handle:kernel.CloseHandle(handle)


if __name__=='__main__':sys.exit(run(int(sys.argv[1]),int(sys.argv[2]),sys.argv[3] if len(sys.argv)>3 else None))
