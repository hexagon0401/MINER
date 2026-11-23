"""CI-only separate executable. This entry point is never bundled in MINER."""
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


class FixtureBackend:
    def __init__(self):self.emergency=threading.Event()
    def preflight(self,profile):pass
    def run(self,profile,stop,phase,observe):
        from windows.process import Job
        from windows.strata_service import root
        from schoolnet.runtime import write_json
        job=Job();child=subprocess.Popen([sys.executable,'--fixture-child'],creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        try:
            job.assign(child)
            write_json(root()/'strata-fixture.json',{'child':child.pid,'service':os.getpid()})
            phase('running',5);stop.wait(120)
        finally:job.close();child.wait(timeout=5)
    def recover(self):pass
    def probe(self,observe):pass


if __name__=='__main__':
    if '--fixture-child' in sys.argv:time.sleep(120)
    else:
        from windows.strata_service import host
        host(FixtureBackend)
