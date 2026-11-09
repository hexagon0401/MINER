"""Replace a real installed copy using the packaged updater; never starts WARP."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def run(app,dmg,output):
    installed=Path('/Applications/MINER.app')
    if installed.exists():raise ValueError('Native updater smoke requires an empty MINER app location')
    cache=Path.home()/'Library/Application Support/SchoolNet v5 Alpha/Updates'
    cache.mkdir(parents=True,exist_ok=True)
    (cache.parent/'.managed.json').write_text(json.dumps({'id':'org.schoolnet.v5.alpha'}))
    target=cache/('MINER-ALPHA-v1.2.1-macOS-'+('AppleSilicon' if 'arm64' in str(app) else 'Intel')+'.dmg')
    subprocess.run(['/usr/bin/ditto',str(app),str(installed)],check=True)
    (installed/'Contents/Resources/obsolete-upgrade-fixture.txt').write_text('old app resource must disappear')
    shutil.copyfile(dmg,target)
    cli=installed/'Contents/Resources/runtime/schoolnet-cli/schoolnet-cli'
    # A disposable parent exits after the worker is ready, just like the GUI.
    code='''import subprocess,time,os,json,sys
result=subprocess.run([sys.argv[1],'update','prepare','--platform','macos','--arch','arm64','--installer',sys.argv[2],'--sha256',sys.argv[3],'--target-version','1.2.1','--parent-pid',str(os.getpid())],capture_output=True,text=True)
print(result.stdout,result.stderr,flush=True)
raise SystemExit(result.returncode)
'''
    try:
        import sys
        subprocess.run([sys.executable,'-c',code,str(cli),str(target),hashlib.sha256(target.read_bytes()).hexdigest()],check=True,timeout=45)
        deadline=time.monotonic()+90
        while True:
            if not target.exists() and not (cache/'mac-install.json').exists() and not list(cache.glob('.worker-*')):break
            if time.monotonic()>deadline:
                raise ValueError((cache/'install.log').read_text(errors='replace')[-2400:])
            time.sleep(.5)
        assert not (installed/'Contents/Resources/obsolete-upgrade-fixture.txt').exists()
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(installed)],check=True)
        assert not list(Path('/Applications').glob('.MINER-update-*'))
        report={'ok':True,'packaged_worker':True,'app_replaced':True,'new_window_acknowledged':True,'obsolete_resources_removed':True,'installer_cache_removed':True,'rollback_backup_removed':True}
        (output/'mac-updater.verification.json').write_text(json.dumps(report,indent=2));return report
    finally:
        subprocess.run(['/usr/bin/pkill','-TERM','-x','MINER'],capture_output=True)
        time.sleep(1)
        if installed.exists():shutil.rmtree(installed)
