"""Out-of-process Windows DNS recovery if the UI or its engine exits."""
import ctypes
import os
from pathlib import Path
import subprocess
import sys
import time

from .network_dns import Lease, journal_path


def spawn(directory, engine_pid):
    if os.name!='nt': return None
    args=[sys.executable]
    if getattr(sys,'frozen',False): args+=['--dns-guard']
    else: args+=['-m','schoolnet.dns_guard']
    args += [str(os.getpid()),str(engine_pid)]
    return subprocess.Popen(args,creationflags=subprocess.CREATE_NO_WINDOW)


def run(parent,engine):
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
        # Parent journals before applying DNS. Wait until it either writes the
        # journal or exits; never restore a healthy session's network settings.
        deadline=time.monotonic()+45
        while not path.exists() and time.monotonic()<deadline:
            if any(not h or kernel.WaitForSingleObject(h,0)==0 for h in handles):return 0
            time.sleep(.1)
        if not path.exists():return 0
        while path.exists():
            if any(not h or kernel.WaitForSingleObject(h,0)==0 for h in handles):
                Lease.recover(Path.home());return 0
            time.sleep(.5)
        return 0
    finally:
        for handle in [*handles,mutex]:
            if handle:kernel.CloseHandle(handle)


if __name__=='__main__':sys.exit(run(int(sys.argv[1]),int(sys.argv[2])))
