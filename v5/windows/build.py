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
from windows.version import VERSION, FILE_VERSION, LABEL, TAG, STEM


def execute(*args, timeout=600):
    subprocess.run([str(a) for a in args],check=True,timeout=timeout)


def main():
    if sys.platform!='win32': raise ValueError('Windows runner required')
    os.chdir(BASE)
    if os.environ.get('GITHUB_REF_TYPE') == 'tag' and os.environ.get('GITHUB_REF_NAME') != TAG:
        raise ValueError('Git tag and packaged Windows version disagree')
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
    shutil.copytree(BASE/'windows/pearl',art/'pearl',dirs_exist_ok=True)
    for asset in ('full-window-strata.png','skylight-beam.png'):
        shutil.copyfile(BASE/'macos/delta/assets'/asset,art/asset)
    engine=install(work/'engine','windows-amd64')
    config=work/'check.json'; config.write_text(json.dumps(build_config(Profile(platform='windows'))))
    execute(engine,'check','-c',config)
    os.environ['SCHOOLNET_TEST_ENGINE']=str(engine)
    execute(sys.executable,'-m','unittest','discover','-s','tests','-v')
    # Real Windows adapter lifecycle, with auto_route disabled: do not reroute runner traffic.
    from windows.native_smoke import run as native_smoke
    native=native_smoke(engine,work)
    execute(sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--uac-admin',
        '--name','MINER','--icon',work/'MINER.ico','--distpath',BASE/'dist-windows',
        '--workpath',work/'pyinstaller','--specpath',work,
        '--paths',BASE,'--hidden-import','windows.smoke',
        '--add-data',f'{BASE / "windows/qml"};qml',
        '--add-data',f'{art};art','--add-binary',f'{engine};engine',
        '--add-data',f'{__import__("certifi").where()};.',
        BASE/'windows/entry.py')
    # warp.verify_trace expects this exact bundle filename.
    import certifi
    shutil.copyfile(certifi.where(),BASE/'dist-windows/MINER/_internal/cacert.pem')
    output=Path(os.environ.get('RUNNER_TEMP',str(work)))/'miner-windows-diagnostics'
    output.mkdir(parents=True,exist_ok=True)
    exe=BASE/'dist-windows/MINER/MINER.exe'
    os.environ['QSG_INFO']='1'
    execute(exe,'--self-test',output,timeout=90)
    for scale in ('1.25','1.5','2'):
        os.environ['QT_SCALE_FACTOR']=scale
        execute(exe,'--self-test',output/('scale-'+scale),timeout=90)
    os.environ.pop('QT_SCALE_FACTOR',None)
    ui=json.loads((output/'windows-ui.json').read_text())
    assert ui['ok']
    iscc=shutil.which('ISCC.exe') or r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
    execute(iscc,f'/DAppBuildVersion={VERSION}',f'/DAppFileVersion={FILE_VERSION}',f'/DOutputStem={STEM}',BASE/'windows/installer.iss')
    setup=BASE/'dist-windows'/f'{STEM}-Setup.exe'
    execute(setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/DIR={work / "installed 한글 path"}')
    execute(work/'installed 한글 path/MINER.exe','--self-test',output/'installed',timeout=90)
    # Reinstall over the same installation to exercise upgrade safety.
    execute(setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/DIR={work / "installed 한글 path"}')
    execute(work/'installed 한글 path/unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    import time
    for _ in range(50):
        if not (work/'installed 한글 path/MINER.exe').exists(): break
        time.sleep(.2)
    assert not (work/'installed 한글 path/MINER.exe').exists(),'Uninstall did not remove app'
    import platform
    report={'test_os':platform.platform(),'version':VERSION,'base':'MINER Beta 1.1','architecture':'x64',
      'authenticode_signed':False,'ui':ui,'native_tun':native,'installer_verified':True,'upgrade_verified':True,'unicode_path_verified':True,
      'ui_theme':'Pearl White','default_controls':'A rounded floating','alternative_controls':'B flush integrated',
      'supplied_asset_sha256':{name:hashlib.sha256((art/'pearl/mascot'/name).read_bytes()).hexdigest() for name in ('miner-transparent.png','MINER-wordmark-transparent.png')},'ui_engine':'Qt Quick RHI + Fluent controls and functional Pearl buttons','network_engine':'sing-box 1.12.0 Windows TUN',
      'ui_scale_factors':[1,1.25,1.5,2],'windows_11_live_tested':False,'vanguard_tested':False,
      'uninstaller_verified':True,'school_network_tested':False,'warp_live_tested':False}
    for path in [setup]:
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        report['sha256']=digest
        path.with_suffix(path.suffix+'.sha256').write_text(f'{digest}  {path.name}\n')
        path.with_suffix(path.suffix+'.verification.json').write_text(json.dumps(report,indent=2))
    import zipfile
    archive=BASE/'dist-windows'/f'{STEM}-Screenshots.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(output.rglob('*')):
            if f.is_file() and f.suffix in ('.png','.gif','.json') and 'test-profile' not in f.parts:
                z.write(f,f.relative_to(output))
    shutil.copyfile(output/'windows-ui-motion.gif',BASE/'dist-windows'/f'{STEM}-Preview.gif')
    for filename in ('idle','proxy_connect','running','restored','disconnected','error','settings','rounded','flush'):
        shutil.copyfile(output/f'windows-ui-{filename}.png',BASE/'dist-windows'/f'{STEM}-{filename}.png')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
