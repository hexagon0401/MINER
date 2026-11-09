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
from icon_assets import bundle_icon


def execute(*args, timeout=600):
    subprocess.run([str(a) for a in args],check=True,timeout=timeout)


def main():
    if sys.platform!='win32': raise ValueError('Windows runner required')
    os.chdir(BASE)
    if os.environ.get('GITHUB_REF_TYPE') == 'tag' and os.environ.get('GITHUB_REF_NAME') != TAG:
        raise ValueError('Git tag and packaged Windows version disagree')
    work=BASE/'windows/work'; work.mkdir(parents=True,exist_ok=True)
    art=work/'art'; art.mkdir(exist_ok=True)
    for name in ('AppIcon.png','developer-profile.json'):
        shutil.copyfile(BASE/'macos/design/assets'/name,art/name)
    profile=json.loads((art/'developer-profile.json').read_text())
    with urllib.request.urlopen(profile['avatarURL'],timeout=30) as response:
        image=response.read(4*1024*1024+1)
    if len(image)>4*1024*1024: raise ValueError('Avatar too large')
    (art/'avatar-source').write_bytes(image)
    with Image.open(art/'avatar-source') as avatar: avatar.convert('RGBA').save(art/'developer-avatar.png')
    app_icon=bundle_icon(art,VERSION)
    with Image.open(art/'AppIcon.png') as icon:
        icon.save(work/'MINER.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    shutil.copytree(BASE/'windows/pearl',art/'pearl',dirs_exist_ok=True)
    engine=install(work/'engine','windows-amd64')
    config=work/'check.json'; config.write_text(json.dumps(build_config(Profile(platform='windows'))))
    execute(engine,'check','-c',config)
    os.environ['SCHOOLNET_TEST_ENGINE']=str(engine)
    execute(sys.executable,'-m','unittest','discover','-s','tests','-v')
    # Real Windows adapter lifecycle, with auto_route disabled: do not reroute runner traffic.
    from windows.native_smoke import run as native_smoke
    native=native_smoke(engine,work)
    from selective_smoke import run as selective_smoke
    selective=selective_smoke(engine,work/"selective-native")
    execute(sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--uac-admin',
        '--name','MINER','--icon',work/'MINER.ico','--distpath',BASE/'dist-windows',
        '--workpath',work/'pyinstaller','--specpath',work,
        '--paths',BASE,'--hidden-import','windows.smoke',
        '--exclude-module','PySide6.QtWebEngineCore','--exclude-module','PySide6.QtWebEngineQuick',
        '--exclude-module','PySide6.QtWebEngineWidgets','--exclude-module','PySide6.QtQuick3D',
        '--exclude-module','PySide6.QtMultimedia','--exclude-module','PySide6.QtPdf',
        '--add-data',f'{BASE / "windows/qml"};qml',
        '--add-data',f'{art};art','--add-binary',f'{engine};engine',
        '--add-data',f'{__import__("certifi").where()};.',
        BASE/'windows/entry.py')
    # warp.verify_trace expects this exact bundle filename.
    import certifi
    shutil.copyfile(certifi.where(),BASE/'dist-windows/MINER/_internal/cacert.pem')
    from windows.package_size import prune
    size_report=prune(BASE/'dist-windows/MINER/_internal')
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
    # Upgrade the actual published v1.1.1 installer, with its identity preserved.
    old_setup=work/'MINER-ALPHA-v1.1.1-Windows-x64-Setup.exe'
    with urllib.request.urlopen('https://github.com/hexagon0401/MINER/releases/download/miner-alpha-v1.1.1/'+old_setup.name,timeout=60) as response:
        old_setup.write_bytes(response.read(100_000_001))
    assert hashlib.sha256(old_setup.read_bytes()).hexdigest()=='a10a319b74072b0012c7a7e5786e063de33537b9518f805a052349448c11d2d6','Published baseline installer checksum mismatch'
    execute(old_setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/DIR={work / "installed 한글 path"}')
    user_data=Path(os.environ['LOCALAPPDATA'])/'MINER/Beta1';user_data.mkdir(parents=True,exist_ok=True)
    sentinel=user_data/'upgrade-preservation-fixture.json'
    sentinel.write_text('{"fixture":"v1.1.1 user data must survive"}')
    sentinel_digest=hashlib.sha256(sentinel.read_bytes()).hexdigest()
    execute(setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/DIR={work / "installed 한글 path"}')
    assert hashlib.sha256(sentinel.read_bytes()).hexdigest()==sentinel_digest,'Upgrade changed user data'
    execute(work/'installed 한글 path/MINER.exe','--self-test',output/'installed',timeout=90)
    # Reinstall over the same installation to exercise upgrade safety.
    execute(setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/DIR={work / "installed 한글 path"}')
    execute(work/'installed 한글 path/unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART')
    import time
    for _ in range(50):
        if not (work/'installed 한글 path/MINER.exe').exists(): break
        time.sleep(.2)
    assert not (work/'installed 한글 path/MINER.exe').exists(),'Uninstall did not remove app'
    assert hashlib.sha256(sentinel.read_bytes()).hexdigest()==sentinel_digest,'Uninstall removed user data'
    sentinel.unlink()
    import platform
    report={'test_os':platform.platform(),'version':VERSION,'base':'MINER Beta 1.1','architecture':'x64',
      'authenticode_signed':False,'app_icon_sha256':app_icon['sha256'],'release_channel':app_icon['channel'],'ui':ui,'native_tun':native,'selective_network':selective,'upgrade_from':'1.1.1','upgrade_preserves_user_data':True,'installer_verified':True,'upgrade_verified':True,'unicode_path_verified':True,
      'ui_theme':'Pearl White','default_controls':'A rounded floating','alternative_controls':'B flush integrated',
      'supplied_asset_sha256':{name:hashlib.sha256((art/'pearl/mascot'/name).read_bytes()).hexdigest() for name in ('miner-transparent.png','MINER-wordmark-transparent.png')},'ui_engine':'Qt Quick RHI + Fluent controls and functional Pearl buttons','network_engine':'sing-box 1.12.0 Windows TUN',
      'ui_scale_factors':[1,1.25,1.5,2],'windows_11_live_tested':False,'vanguard_tested':False,
      'uninstaller_verified':True,'school_network_tested':False,'warp_live_tested':False,'source_commit':os.environ.get('GITHUB_SHA'),
      'package_optimization':size_report,'installer_bytes':setup.stat().st_size,'size_target_bytes':80_000_000,
      'size_target_met':setup.stat().st_size<=80_000_000}
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
