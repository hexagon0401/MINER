"""Unprivileged, staged macOS app replacement with launch acknowledgement."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from . import __release_version__
from .runtime import write_json
from .updates import clean_cache,version

APP=Path('/Applications/MINER.app')
IDENTIFIER='org.schoolnet.v5.alpha'
DATA=Path.home()/'Library/Application Support/SchoolNet v5 Alpha'
CACHE=DATA/'Updates'
PENDING='mac-install.json'


def execute(*args):
    return subprocess.run([str(a) for a in args],check=True,capture_output=True,text=True,timeout=120)


def info(app):return plistlib.loads((app/'Contents/Info.plist').read_bytes())


def safe_cache():
    for path in (DATA,CACHE):
        if path.is_symlink():raise ValueError('Update directories must not be symlinks')
    CACHE.mkdir(parents=True,exist_ok=True,mode=0o700)
    return CACHE


def validate_app(app,target=None):
    if app.is_symlink() or not app.is_dir():raise ValueError('Expected a real MINER app bundle')
    values=info(app)
    if values.get('CFBundleIdentifier')!=IDENTIFIER or (target and values.get('CFBundleShortVersionString')!=target):
        raise ValueError('Update app identity/version mismatch')


def prepare(installer,sha,target,parent):
    import re
    version(target)
    if not re.fullmatch('[a-f0-9]{64}',sha) or parent<=1:raise ValueError('Invalid update request')
    cache=safe_cache();installer=Path(installer)
    if installer.parent!=cache or installer.is_symlink() or not re.fullmatch(r'MINER-ALPHA-v[0-9.]+-macOS-(AppleSilicon|Intel)\.dmg',installer.name):raise ValueError('Invalid update installer path')
    validate_app(APP)
    if (cache/PENDING).exists():raise ValueError('A previous app update needs recovery; keeping its backup')
    if not getattr(sys,'frozen',False):raise ValueError('Automatic app replacement requires the packaged runtime')
    for stale in cache.glob('.worker-*'):
        if stale.is_symlink() or not stale.is_dir() or not (stale/'.miner-worker-owned').is_file():continue
        try:
            pid=int((stale/'worker.pid').read_text())
            os.kill(pid,0)
            if time.time()-stale.stat().st_mtime<3600:raise ValueError('An update worker is still active')
            shutil.rmtree(stale)
        except (FileNotFoundError,ProcessLookupError):shutil.rmtree(stale)
    worker=cache/('.worker-'+uuid.uuid4().hex)
    child=None
    try:
        worker.mkdir(mode=0o700)
        (worker/'.miner-worker-owned').write_text(worker.name[8:])
        (worker/'worker.pid').write_text(str(os.getpid()))
        shutil.copytree(Path(sys.executable).parent,worker,symlinks=True,dirs_exist_ok=True)
        ticket=worker/'ticket.json'
        write_json(ticket,{'installer':str(installer),'sha256':sha,'target':target,'parent':parent,'token':worker.name[8:]})
        environment=os.environ.copy();environment['PYINSTALLER_RESET_ENVIRONMENT']='1'
        with (cache/'install.log').open('w') as log:
            child=subprocess.Popen([str(worker/'schoolnet-cli'),'update','apply','--platform','macos','--arch',platform.machine(),'--ticket',str(ticket)],env=environment,start_new_session=True,stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        deadline=time.monotonic()+15
        while not (worker/'worker-ready').exists():
            if child.poll() is not None or time.monotonic()>deadline:raise ValueError('Update worker did not become ready; app preserved')
            time.sleep(.1)
        return {'started':True}
    except Exception:
        if child and child.poll() is None:child.terminate();child.wait(timeout=5)
        shutil.rmtree(worker,ignore_errors=True);raise


def finish():
    cache=safe_cache();pending=cache/PENDING
    if not pending.exists():return clean_cache(cache,__release_version__)
    state=json.loads(pending.read_text())
    validate_app(APP,__release_version__)
    if state['target']!=__release_version__:return {'deferred':True}
    stage=Path(state['stage']);token=state['token']
    import re
    if not re.fullmatch('[a-f0-9]{32}',token) or stage.parent!=APP.parent or not stage.name.startswith('.MINER-update-') or stage.is_symlink():raise ValueError('Invalid app recovery record')
    if (stage/'.miner-update-owned').read_text()!=token:raise ValueError('App backup ownership differs')
    # Called only after the new window exists; acknowledge before removing backup.
    (cache/('ready-'+token)).write_text(__release_version__)
    shutil.rmtree(stage);pending.unlink()
    return clean_cache(cache,__release_version__)


def apply(ticket):
    cache=safe_cache();ticket=Path(ticket);worker=ticket.parent
    if worker.parent!=cache or not worker.name.startswith('.worker-') or worker.is_symlink() or ticket.is_symlink():raise ValueError('Invalid worker ticket')
    state=json.loads(ticket.read_text());installer=Path(state['installer']);target=state['target'];token=state['token']
    from re import fullmatch
    if not fullmatch('[a-f0-9]{32}',token) or worker.name!='.worker-'+token or installer.parent!=cache or installer.is_symlink():raise ValueError('Invalid update transaction')
    version(target)
    digest=hashlib.sha256()
    with installer.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    if digest.hexdigest()!=state['sha256']:raise ValueError('Installer checksum changed')
    (worker/'worker.pid').write_text(str(os.getpid()))
    (worker/'worker-ready').touch()
    deadline=time.monotonic()+120
    while True:
        try:os.kill(int(state['parent']),0)
        except ProcessLookupError:break
        if time.monotonic()>deadline:raise ValueError('MINER did not exit; update cancelled')
        time.sleep(.2)
    validate_app(APP)
    stage=None;mounted=False;replaced=False;launched=False
    mount=worker/'mount';mount.mkdir()
    try:
        execute('/usr/bin/hdiutil','attach','-readonly','-nobrowse','-mountpoint',mount,installer);mounted=True
        incoming=mount/'MINER.app';validate_app(incoming,target)
        execute('/usr/bin/codesign','--verify','--deep','--strict',incoming)
        stage=Path(tempfile.mkdtemp(prefix='.MINER-update-',dir=APP.parent))
        (stage/'.miner-update-owned').write_text(token)
        execute('/usr/bin/ditto',incoming,stage/'new.app')
        execute('/usr/bin/codesign','--verify','--deep','--strict',stage/'new.app')
        write_json(cache/PENDING,{'stage':str(stage),'target':target,'token':token})
        os.rename(APP,stage/'previous.app')
        try:os.rename(stage/'new.app',APP);replaced=True
        except Exception:os.rename(stage/'previous.app',APP);raise
        execute('/usr/bin/open','-n',APP);launched=True
        deadline=time.monotonic()+60
        ready=cache/('ready-'+token)
        while not ready.exists() or (cache/PENDING).exists() or stage.exists():
            if time.monotonic()>deadline:raise ValueError('New app did not confirm launch; previous app backup retained')
            time.sleep(.2)
        if ready.read_text()!=target:raise ValueError('Launch acknowledgement version mismatch')
        ready.unlink();return {'installed':True,'version':target,'backup_removed':not stage.exists()}
    except Exception as error:
        (cache/'install-error.txt').write_text(str(error))
        if stage and not launched:
            if replaced:shutil.rmtree(APP)
            if (stage/'previous.app').exists():os.rename(stage/'previous.app',APP)
            shutil.rmtree(stage,ignore_errors=True);(cache/PENDING).unlink(missing_ok=True)
        if not launched:
            try:execute('/usr/bin/open',APP)
            except Exception:pass
        raise
    finally:
        if mounted:
            subprocess.run(['/usr/bin/hdiutil','detach',str(mount)],capture_output=True,timeout=30)
        # Worker lives outside the replaced app. macOS permits unlinking its
        # already-loaded runtime; retain it only while an unresolved backup exists.
        if not (cache/PENDING).exists():shutil.rmtree(worker,ignore_errors=True)
