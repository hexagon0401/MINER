"""Read running macOS app identity; export categories and versions, never paths."""
import ctypes
import math
from pathlib import Path
import plistlib
import re
import sys

APP_ID='org.schoolnet.v5.alpha'


def bundle_metadata(bundle):
    result={'recognized':False,'version':'unavailable'}
    try:
        path=Path(bundle)/'Contents/Info.plist'
        if path.is_symlink() or path.stat().st_size>65536:return result
        data=plistlib.loads(path.read_bytes())
        if data.get('CFBundleIdentifier')!=APP_ID:return result
        result['recognized']=True
        for field,key,pattern in [('CFBundleShortVersionString','version',r'\d+(?:\.\d+){1,3}'),
                                  ('CFBundleVersion','build',r'\d+(?:\.\d+){0,3}'),
                                  ('SchoolNetReleaseVersion','backend_version',r'5\.0\.0-(?:alpha|strata)\.\d+\.\d+\.\d+(?:-preview\.\d+)?')]:
            value=data.get(field)
            if isinstance(value,str) and len(value)<=80 and re.fullmatch(pattern,value):result[key]=value
    except (OSError,ValueError,TypeError,AttributeError):pass
    return result


def process_path(pid):
    if sys.platform!='darwin' or type(pid) is not int or pid<=0:return None
    try:
        library=ctypes.CDLL('/usr/lib/libproc.dylib',use_errno=True)
        function=library.proc_pidpath;function.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_uint32];function.restype=ctypes.c_int
        buffer=ctypes.create_string_buffer(4096)
        if function(pid,buffer,len(buffer))<=0:return None
        return Path(buffer.value.decode('utf-8'))
    except (OSError,ValueError,UnicodeError):return None


def running_identity(pid,comm,installed=Path('/Applications/MINER.app')):
    executable=process_path(pid)
    if executable is None and isinstance(comm,str) and comm.startswith('/') and comm.endswith('.app/Contents/MacOS/MINER'):executable=Path(comm)
    if executable is None or not str(executable).endswith('.app/Contents/MacOS/MINER'):
        return {'identity_available':False,'location_kind':'unresolved','version':'unavailable'}
    bundle=executable.parents[2]
    try:matches=bundle.samefile(installed)
    except OSError:matches=False
    path=str(bundle)
    kind=('system_applications' if matches else 'translocated' if '/AppTranslocation/' in path else
          'mounted_volume' if path.startswith('/Volumes/') else
          'user_applications' if path.startswith(str(Path.home()/'Applications')+'/') else
          'other_system_applications_copy' if path.startswith('/Applications/') else 'other_copy')
    return {'identity_available':True,'location_kind':kind,'matches_system_install':matches,
            'version_source':'running_executable_bundle_plist','loaded_image_version_verified':False,**bundle_metadata(bundle)}


STAGES={'process_started','delegate_retained','did_finish_launching','window_presented','event_loop_ready','reopen_received','installation_check_rejected','installed_handoff_completed'}
KINDS={'system_applications','translocated','mounted_volume','user_applications','other_copy'}
def startup_events(path=None):
    import json
    path=Path(path) if path else Path.home()/'Library/Logs/MINER/startup.jsonl'
    if path.is_symlink():return []
    rows=[]
    try:
        with path.open('rb') as stream:
            size=path.stat().st_size;stream.seek(max(0,size-32768));text=stream.read(32768).decode('utf-8','replace')
        for line in text.splitlines():
            try:
                row=json.loads(line);at=row.get('at')
                if row.get('stage') in STAGES and row.get('installation_kind') in KINDS and type(at) in (float,int) and math.isfinite(at):
                    rows.append({'stage':row['stage'],'installation_kind':row['installation_kind'],'at':at})
            except (TypeError,ValueError,AttributeError):continue
    except OSError:pass
    return rows[-24:]
