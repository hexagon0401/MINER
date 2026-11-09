"""Launch the verified installer after MINER releases its process and mutex."""
import os
from pathlib import Path
import subprocess
import sys


def installer_command(path, parent):
    literal = str(Path(path).resolve()).replace("'", "''")
    return f"$env:PSModulePath=$PSHOME+'\\Modules'; $minerParent=Get-Process -Id {int(parent)} -ErrorAction SilentlyContinue; if($minerParent){{$minerParent.WaitForExit()}}; Start-Process -FilePath '{literal}'"


def launch(path):
    if sys.platform != "win32": raise ValueError("Windows installer requires Windows")
    powershell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    return subprocess.Popen([str(powershell), "-NoProfile", "-NonInteractive", "-Command",
                             installer_command(path, os.getpid())], creationflags=subprocess.CREATE_NO_WINDOW)
