"""Build and exercise the actual Windows x64 executable before release."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
from PIL import Image

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from install_engine import install
from schoolnet.config import Profile, build_config


def execute(*args):
    subprocess.run([str(a) for a in args],check=True)


def main():
    if sys.platform!='win32': raise ValueError('Windows runner required')
    os.chdir(BASE)
    work=BASE/'windows/work'; work.mkdir(parents=True,exist_ok=True)
    art=work/'art'; shutil.copytree(BASE/'macos/design/assets',art,dirs_exist_ok=True)
    profile=json.loads((art/'developer-profile.json').read_text())
    with urllib.request.urlopen(profile['avatarURL'],timeout=30) as response:
        image=response.read(4*1024*1024+1)
    if len(image)>4*1024*1024: raise ValueError('Avatar too large')
    (art/'avatar-source').write_bytes(image)
    with Image.open(art/'avatar-source') as avatar: avatar.convert('RGBA').save(art/'developer-avatar.png')
    with Image.open(art/'AppIcon.png') as icon:
        icon.save(work/'MINER.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    engine=install(work/'engine','windows-amd64')
    config=work/'check.json'; config.write_text(json.dumps(build_config(Profile(platform='windows'))))
    execute(engine,'check','-c',config)
    # Real Windows adapter lifecycle, with auto_route disabled: do not reroute runner traffic.
    from windows.native_smoke import run as native_smoke
    native=native_smoke(engine,work)
    execute(sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--uac-admin',
        '--name','MINER','--icon',work/'MINER.ico','--distpath',BASE/'dist-windows',
        '--workpath',work/'pyinstaller','--specpath',work,
        '--paths',BASE,'--hidden-import','windows.smoke',
        '--add-data',f'{art};art','--add-binary',f'{engine};engine',
        '--add-data',f'{__import__("certifi").where()};.',
        BASE/'windows/app.py')
    # warp.verify_trace expects this exact bundle filename.
    import certifi
    shutil.copyfile(certifi.where(),BASE/'dist-windows/MINER/_internal/cacert.pem')
    output=Path(os.environ.get('RUNNER_TEMP',str(work)))/'miner-windows-diagnostics'
    output.mkdir(parents=True,exist_ok=True)
    exe=BASE/'dist-windows/MINER/MINER.exe'
    execute(exe,'--self-test',output)
    ui=json.loads((output/'windows-ui.json').read_text())
    assert ui['ok']
    iscc=shutil.which('ISCC.exe') or r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
    execute(iscc,BASE/'windows/installer.iss')
    setup=BASE/'dist-windows/MINER-v5.0.0-beta.1.1-windows.2-Windows-x64-Setup.exe'
    execute(setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/DIR={work / "installed"}')
    execute(work/'installed/MINER.exe','--self-test',output/'installed')
    execute(work/'installed/unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    import time
    for _ in range(50):
        if not (work/'installed/MINER.exe').exists(): break
        time.sleep(.2)
    assert not (work/'installed/MINER.exe').exists(),'Uninstall did not remove app'
    report={'version':'5.0.0-beta.1.1-windows.2','base':'MINER Beta 1.1','architecture':'x64',
      'authenticode_signed':False,'ui':ui,'native_tun':native,'installer_verified':True,
      'uninstaller_verified':True,'school_network_tested':False,'warp_live_tested':False}
    for path in [setup]:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        report['sha256']=digest
        path.with_suffix(path.suffix+'.sha256').write_text(f'{digest}  {path.name}\n')
        path.with_suffix(path.suffix+'.verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
