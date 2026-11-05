"""Actual Windows TUN creation and graceful shutdown, without changing default routes."""
import ctypes
import json
from pathlib import Path
import subprocess
import time
from windows.controller import stop_engine
from windows.process import Job


def run(engine,work):
    ctypes.windll.kernel32.AllocConsole()
    path=Path(work)/'tun-smoke.json'
    config={'log':{'level':'info'},'inbounds':[{'type':'tun','tag':'native-smoke',
      'interface_name':'MINER-CI-Smoke','address':['172.30.254.1/30'],
      'auto_route':False,'strict_route':False,'stack':'system'}],
      'outbounds':[{'type':'direct','tag':'direct'}]}
    path.write_text(json.dumps(config))
    logfile=Path(work)/'tun-smoke.log'
    child=None
    job=Job()
    try:
        with logfile.open('w') as log:
            child=subprocess.Popen([str(engine),'run','-c',str(path)],stdout=log,stderr=log,
               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            job.assign(child)
            for _ in range(100):
                text=logfile.read_text(errors='replace')
                if 'sing-box started' in text and 'inbound/tun' in text: break
                if child.poll() is not None: raise ValueError(text)
                time.sleep(.1)
            else: raise ValueError('Native Windows TUN startup timed out')
            stop_engine(child)
            assert child.poll() is not None
    finally:
        try: stop_engine(child)
        finally: job.close()
    # Exercise KILL_ON_JOB_CLOSE with a real disposable child process.
    import sys
    orphan=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])
    ownership=Job()
    try:
        ownership.assign(orphan)
        ownership.close()
        orphan.wait(timeout=5)
    finally:
        ownership.close()
        if orphan.poll() is None: orphan.kill();orphan.wait(timeout=5)
    return {'adapter_created':True,'graceful_stop':True,'auto_route':False,'job_kills_remaining_child':True}
