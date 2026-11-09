"""Install after MINER exits, relaunch only on success, clean the managed cache."""
import os
import ctypes
from pathlib import Path
import re
import subprocess
import sys


def literal(value):return "'"+str(value).replace("'","''")+"'"


def installer_command(path,parent,install_dir=None,sha=None):
    command="$ErrorActionPreference='Stop'; $env:PSModulePath=$PSHOME+'\\Modules'; "
    command+=f"$minerParent=Get-Process -Id {int(parent)} -ErrorAction SilentlyContinue; if($minerParent){{$minerParent.WaitForExit()}}; "
    if install_dir is None:return command+f"Start-Process -FilePath {literal(Path(path).resolve())}"
    if not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):raise ValueError('Expected a verified installer checksum')
    command+="try { "
    command+=f"if((Get-FileHash -Algorithm SHA256 -LiteralPath {literal(path)}).Hash.ToLower() -ne '{sha}'){{throw 'Installer checksum changed'}}; "
    arguments='/SILENT /SUPPRESSMSGBOXES /NORESTART /DIR="'+str(install_dir)+'"'
    command+=f"$setup=Start-Process -FilePath {literal(path)} -ArgumentList {literal(arguments)} -PassThru -Wait; "
    command+=f"if($setup.ExitCode -notin @(0,3010)){{throw 'MINER update failed; installer retained'}}; Remove-Item -LiteralPath {literal(path)} -ErrorAction SilentlyContinue; "
    command+=f"Start-Process -FilePath {literal(Path(install_dir)/'MINER.exe')}"
    command+=f" }} catch {{ Set-Content -LiteralPath {literal(Path(path).parent/'install-error.txt')} -Value 'Update failed; previous app files were preserved. Retry in Settings.'; Start-Process -FilePath {literal(Path(install_dir)/'MINER.exe')}; exit 1 }}"
    return command


def launch(path,sha):
    if sys.platform!='win32' or not getattr(sys,'frozen',False):raise ValueError('Use the installed Windows app to apply updates')
    powershell=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/WindowsPowerShell/v1.0/powershell.exe'
    # PyInstaller's DLL search directory is inherited by children. An updater
    # must not load/lock DLLs from the runtime it is about to replace.
    kernel=ctypes.windll.kernel32
    kernel.SetDllDirectoryW.argtypes=[ctypes.c_wchar_p]
    kernel.SetDllDirectoryW(None)
    try:
        return subprocess.Popen([str(powershell),'-NoProfile','-NonInteractive','-Command',installer_command(path,os.getpid(),Path(sys.executable).parent,sha)],creationflags=subprocess.CREATE_NO_WINDOW)
    finally:kernel.SetDllDirectoryW(str(sys._MEIPASS))
