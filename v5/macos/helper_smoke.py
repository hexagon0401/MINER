"""Exercise real root/user peer authentication without installing a daemon or TUN."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from schoolnet.macos_helper import SOCKET


def run(cli, output):
    if sys.platform!='darwin' or os.getuid()==0:raise ValueError('Run as the normal macOS CI user')
    if SOCKET.exists():raise ValueError('Preserving existing MINER helper; native smoke needs a clean runner')
    root_pid=None
    with (output/'helper-smoke.log').open('w') as log:
        process=subprocess.Popen(['sudo','-n',str(cli),'desktop','helper-serve','--owner',str(os.getuid())],stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+15
            while not SOCKET.exists():
                if process.poll() is not None or time.monotonic()>deadline:raise ValueError('Native helper did not start')
                time.sleep(.1)
            for _ in range(2):
                result=subprocess.run([str(cli),'desktop','helper-status'],capture_output=True,text=True,timeout=15,check=True)
                data=json.loads(result.stdout);root_pid=data['helper_pid']
                assert data['ok'] and not data['running']
            subprocess.run([str(cli),'desktop','helper-stop'],capture_output=True,text=True,timeout=20,check=True)
            report={'ok':True,'real_root_peer_authenticated':True,'repeated_user_requests':2,'engine_started':False,'launch_daemon_installed':False}
            (output/'helper-smoke.json').write_text(json.dumps(report,indent=2))
            return report
        except Exception:
            log.flush(); print((output/'helper-smoke.log').read_text(errors='replace'))
            raise
        finally:
            if root_pid:subprocess.run(['sudo','-n','/bin/kill','-TERM',str(root_pid)],capture_output=True,timeout=10)
            else:process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
            subprocess.run(['sudo','-n','/bin/rm','-f',str(SOCKET)],check=True,timeout=10)


if __name__=='__main__':
    run(Path(sys.argv[1]),Path(sys.argv[2]))
