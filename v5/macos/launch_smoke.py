"""Launch installed app through LaunchServices, with the normal startup path."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def run(app,output):
    app=Path(app);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    inspector=output/'launch-inspector';log=output/'finder-startup.jsonl'
    subprocess.run(['xcrun','swiftc','-swift-version','5','-parse-as-library','-framework','AppKit','-framework','CoreGraphics',str(Path(__file__).with_name('LaunchSmoke.swift')),'-o',str(inspector)],check=True,timeout=45)
    pid=None
    def events():
        if not log.exists():return []
        result=[]
        for line in log.read_text().splitlines():
            try:result.append(json.loads(line))
            except ValueError:pass
        return result
    def state():
        return json.loads(subprocess.check_output([str(inspector),str(pid)],text=True,timeout=4))
    try:
        subprocess.run(['/usr/bin/open','-n',str(app),'--args','--startup-log',str(log)],check=True,timeout=15)
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            rows=events()
            if rows:pid=rows[0]['pid']
            if pid and any(row['stage']=='event_loop_ready' for row in rows):
                status=state()
                if status.get('finished_launching') and status.get('visible_main_window'):break
            time.sleep(.15)
        else:raise TimeoutError('Normal Finder launch did not produce a responsive visible main window')
        assert all(row['installation_kind']=='system_applications' for row in rows),'Installed copy classified incorrectly'
        subprocess.run(['/usr/bin/open','-a',str(app)],check=True,timeout=10)
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            if any(row['stage']=='reopen_received' for row in events()) and state().get('visible_main_window'):break
            time.sleep(.15)
        else:raise TimeoutError('LaunchServices reopen did not reach the delegate')
        subprocess.run([str(inspector),str(pid),'--quit'],check=True,timeout=5)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if not state().get('running'):break
            time.sleep(.15)
        else:raise TimeoutError('Normal app Quit did not exit')
        report={'ok':True,'launch_services_normal_startup':True,'ui_smoke_mode':False,'event_loop_ready':True,
                'finished_launching':True,'visible_main_window':True,'reopen_received':True,'normal_quit':True,
                'installation_identity':'system_applications','start_button_invoked':False,'warp_or_tun_activation_requested':False}
        (output/'finder-launch.verification.json').write_text(json.dumps(report,indent=2)+'\n');return report
    except Exception:
        if log.exists():print(log.read_text()[-5000:],flush=True)
        if pid:subprocess.run(['/usr/bin/sample',str(pid),'2','1','-file',str(output/'finder-launch-sample.txt')],capture_output=True,timeout=8)
        raise
    finally:
        if pid:
            try:os.kill(pid,signal.SIGTERM)
            except ProcessLookupError:pass
