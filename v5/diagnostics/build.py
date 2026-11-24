"""Build a standalone diagnostic recorder. Does not package or install MINER."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from diagnostics.collect import VERSION


def main():
    system=platform.system();arch=platform.machine()
    if system not in ('Darwin','Windows'):raise ValueError('Native Mac or Windows build required')
    output=ROOT/'dist-diagnostics';output.mkdir(exist_ok=True)
    import certifi
    with tempfile.TemporaryDirectory() as td:
        work=Path(td);name='MINER-Diagnostics'
        subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--console',
            '--name',name,'--paths',str(ROOT),'--distpath',str(work/'dist'),'--workpath',str(work/'work'),'--specpath',str(work),
            '--add-data',str(certifi.where())+(';' if system=='Windows' else ':')+'.',str(ROOT/'diagnostics/collect.py')],check=True,timeout=300)
        binary=work/'dist'/(name+('.exe' if system=='Windows' else ''))
        identity_fixture=False
        if system=='Darwin':
            subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(binary)],check=True,timeout=30)
            subprocess.run(['/usr/bin/codesign','--verify','--strict',str(binary)],check=True,timeout=30)
        # WARP absent / no installed MINER is a useful native scenario, not a skip.
        report=work/'한글 path'/'smoke.zip'
        subprocess.run([str(binary),'--phase','before','--output',str(report)],check=True,timeout=80)
        with zipfile.ZipFile(report) as z:
            data=json.loads(z.read('report.json'));assert data['read_only'] and not data['active_probes'] and not data['uploaded'];assert len(data['samples'])==1
        if system=='Darwin':
            # Long executable path reproduces the old ps truncation boundary.
            # This is a sleeping native fixture, not a GUI or a real MINER session.
            bundle=work/('fixture-'+('x'*110))/'MINER.app';executable=bundle/'Contents/MacOS/MINER';executable.parent.mkdir(parents=True)
            import plistlib
            (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'org.schoolnet.v5.alpha','CFBundleShortVersionString':'9.8.7','CFBundleVersion':'5020999','SchoolNetReleaseVersion':'5.0.0-strata.9.8.7-preview.1'}))
            source=work/'identity-fixture.c';source.write_text('#include <unistd.h>\nint main(void){sleep(90);return 0;}\n')
            subprocess.run(['/usr/bin/clang',str(source),'-o',str(executable)],check=True,timeout=30)
            subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(executable)],check=True,timeout=15)
            child=subprocess.Popen([str(executable)])
            try:
                identity_report=work/'identity.zip'
                subprocess.run([str(binary),'--phase','before','--output',str(identity_report)],check=True,timeout=80)
                with zipfile.ZipFile(identity_report) as z:row=json.loads(z.read('report.json'))['samples'][0]
                records=row['network']['running_miner_apps']
                assert any(item.get('version')=='9.8.7' and item.get('location_kind')=='other_copy' and item.get('identity_available') is True for item in records),'Packaged recorder failed to identify long-path native fixture'
                assert str(bundle) not in json.dumps(row),'Raw executable path leaked'
                identity_fixture=True
            finally:child.terminate();child.wait(timeout=5)
        client_flow_fixture=False
        if system=='Darwin':
            from diagnostics.client_flow_smoke import run as client_flow_smoke
            client_flow_fixture=client_flow_smoke(binary,work)
        # Ensure a frozen child can be invoked without recursively entering the UI.
        subprocess.run([str(binary),'--version'],check=True,timeout=15)
        kind='macOS-AppleSilicon' if system=='Darwin' and arch=='arm64' else 'macOS-Intel' if system=='Darwin' else 'Windows-x64'
        package=output/f'MINER-Diagnostics-v{VERSION}-{kind}.zip'
        with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(binary,binary.name);z.write(ROOT/'diagnostics/README_KO.md','README_KO.md')
            if system=='Darwin':
                info=zipfile.ZipInfo('시작.command');info.external_attr=0o100755<<16
                z.writestr(info,'#!/bin/bash\ncd -- "$(dirname -- "$0")" || exit 1\nexec ./MINER-Diagnostics --interactive\n')
        digest=hashlib.sha256(package.read_bytes()).hexdigest()
        package.with_suffix('.zip.sha256').write_text(digest+'  '+package.name+'\n')
        package.with_suffix('.zip.verification.json').write_text(json.dumps({'ok':True,'tool_version':VERSION,'system':system,'architecture':arch,'source_commit':os.environ.get('GITHUB_SHA'),'sha256':digest,'packaged_recorder_executed':True,'read_only_report_verified':True,'native_long_path_identity_fixture':identity_fixture,'native_client_socket_fixture':client_flow_fixture,'warp_live_tested':False,'game_live_tested':False,'signing':'adhoc' if system=='Darwin' else 'unsigned','notarized':False},indent=2)+'\n')
        print(package)

if __name__=='__main__':main()
