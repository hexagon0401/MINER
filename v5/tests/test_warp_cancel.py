import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

@unittest.skipIf(os.name=='nt','POSIX CLI cancellation')
class WarpCancellationTests(unittest.TestCase):
    def test_cancelling_the_cli_reaps_its_pending_warp_child(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pid=root/'pid';cli=root/'warp-fixture'
            cli.write_text('#!'+sys.executable+'\nimport os,time\nfrom pathlib import Path\nPath('+repr(str(pid))+').write_text(str(os.getpid()))\ntime.sleep(30)\n')
            cli.chmod(0o755)
            main=Path(__file__).resolve().parents[1]/'main.py'
            process=subprocess.Popen([sys.executable,str(main),'warp','connect','--warp-cli',str(cli)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            child=None
            try:
                deadline=time.monotonic()+5
                while not pid.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(pid.exists());child=int(pid.read_text())
                process.send_signal(signal.SIGTERM);process.communicate(timeout=3)
                with self.assertRaises(ProcessLookupError):os.kill(child,0)
            finally:
                if process.poll() is None:process.kill();process.wait()
                if child:
                    try:os.kill(child,signal.SIGKILL)
                    except ProcessLookupError:pass
