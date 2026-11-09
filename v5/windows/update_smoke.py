"""Run the actual auto-install PowerShell handoff, then inspect installed files."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import time
from windows.updates import installer_command


def run(setup,installed):
    cache=Path(os.environ['LOCALAPPDATA'])/'MINER/Beta1/Updates';cache.mkdir(parents=True,exist_ok=True)
    payload=cache/setup.name;shutil.copyfile(setup,payload)
    old=cache/'MINER-ALPHA-v1.2.0-Windows-x64-Setup.exe';old.write_bytes(b'old download fixture')
    stale=installed/'_internal/obsolete-second-upgrade.dll';stale.write_bytes(b'old runtime')
    ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    command=installer_command(payload,2147483647,installed,hashlib.sha256(payload.read_bytes()).hexdigest())
    subprocess.run([str(ps),'-NoProfile','-NonInteractive','-Command',command],check=True,timeout=180)
    query="$env:PSModulePath=$PSHOME+'\\Modules'; Get-Process MINER -ErrorAction SilentlyContinue | Where-Object {$_.Path -eq '"+str(installed/'MINER.exe').replace("'","''")+"'} | Select-Object -ExpandProperty Id"
    pid=None
    try:
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            text=subprocess.check_output([str(ps),'-NoProfile','-Command',query],text=True).strip()
            if text and not old.exists():pid=int(text.splitlines()[0]);break
            time.sleep(.3)
        assert pid,'Updated app did not relaunch or clean old installer cache'
        assert not payload.exists() and not stale.exists()
        assert not (installed/'.MINER-upgrade-backup').exists()
        return {'ok':True,'same_location_install':True,'relaunch_verified':True,'installer_cache_removed':True,'obsolete_runtime_removed':True,'backup_removed':True}
    finally:
        subprocess.run([str(ps),'-NoProfile','-Command',query+' | ForEach-Object { Stop-Process -Id $_ -Force }'],capture_output=True)
        time.sleep(1)


def rollback(setup,installed):
    import ctypes
    from ctypes import wintypes as W
    target=installed/'MINER.exe';original=hashlib.sha256(target.read_bytes()).hexdigest()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,ctypes.c_void_p,W.DWORD,W.DWORD,W.HANDLE];kernel.CreateFileW.restype=W.HANDLE
    kernel.CloseHandle.argtypes=[W.HANDLE]
    handle=kernel.CreateFileW(str(target),0x80000000,1,None,3,0,None)
    if handle==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:
        result=subprocess.run([str(setup),'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/DIR='+str(installed)],timeout=120)
        assert result.returncode!=0,'A locked executable must abort the upgrade'
    finally:kernel.CloseHandle(handle)
    assert hashlib.sha256(target.read_bytes()).hexdigest()==original,'Failed upgrade changed previous executable'
    assert (installed/'_internal/obsolete-miner-fixture.dll').exists(),'Failed upgrade lost previous runtime'
    backup=installed/'.MINER-upgrade-backup/MINER.exe'
    if backup.exists():assert hashlib.sha256(backup.read_bytes()).hexdigest()==original,'Locked-file backup was not preserved'
    return True
