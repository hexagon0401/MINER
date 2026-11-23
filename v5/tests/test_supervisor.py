import tempfile
from pathlib import Path
import threading
import time
import unittest
from schoolnet.supervisor import Supervisor
from schoolnet.lease_owner import Ownership

class Backend:
    def __init__(self):self.calls=0;self.emergency=threading.Event();self.stopped=threading.Event()
    def preflight(self,p):pass
    def run(self,p,stop,phase,observe):
        self.calls+=1;phase('running',5);stop.wait(2);self.stopped.set()
    def recover(self):pass
    def probe(self,observe):raise TimeoutError()

def msg(op,rid='a'*32,g=0):return {'api_version':'strata-2','request_id':rid,'expected_generation':g,'operation':op}
def wait(s,target):
    end=time.monotonic()+3
    while s.snapshot()['state']!=target and time.monotonic()<end:time.sleep(.01)
    return s.snapshot()['state']
class SupervisorTests(unittest.TestCase):
    def test_duplicate_connect_never_starts_a_second_engine_and_gui_detach_changes_nothing(self):
        b=Backend();s=Supervisor('owner',b);m=msg('connect');s.request(m,'owner');s.request(m,'owner')
        self.assertEqual(wait(s,'READY'),'READY');self.assertEqual(b.calls,1)
        self.assertEqual(s.request(msg('status','b'*32),'owner')['state'],'READY')
        s.request(msg('stop','c'*32,1),'owner');self.assertEqual(wait(s,'STOPPED'),'STOPPED');self.assertTrue(b.stopped.is_set())
    def test_owner_generation_operation_and_reused_ids_are_checked(self):
        s=Supervisor('owner',Backend())
        for m,peer in [(msg('status'),'attacker'),(msg('shell'),'owner'),(msg('connect',g=2),'owner')]:
            with self.assertRaises(ValueError):s.request(m,peer)
        s.request(msg('prepare_update'),'owner')
        with self.assertRaises(ValueError):s.request(msg('stop'),'owner')
    def test_probe_failure_preserves_backend_session_and_stop_still_recovers(self):
        b=Backend();s=Supervisor('owner',b);s.request(msg('connect'),'owner');wait(s,'READY')
        s.request(msg('retry_probe','b'*32,1),'owner');self.assertEqual(wait(s,'DEGRADED'),'DEGRADED');self.assertFalse(b.stopped.is_set())
        s.request(msg('stop','c'*32,1),'owner');self.assertEqual(wait(s,'STOPPED'),'STOPPED')
    def test_ownership_rejects_wrong_owner_old_generation_corruption_and_links(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'owner.json';r=Ownership(p,'owner');r.save({'generation':1,'unfinished':True})
            with self.assertRaises(ValueError):Ownership(p,'other').read()
            with self.assertRaises(ValueError):r.save({'generation':0,'unfinished':False})
            p.write_text('{}')
            with self.assertRaises(ValueError):r.read()

    def test_failure_to_persist_owner_never_starts_backend(self):
        b=Backend()
        def broken(value):raise OSError('disk full')
        s=Supervisor('owner',b,broken)
        with self.assertRaises(OSError):s.request(msg('connect'),'owner')
        self.assertEqual(b.calls,0);self.assertEqual(s.snapshot()['state'],'RECOVERY_REQUIRED')

    def test_proxy_healthy_never_erases_riot_failure_and_retry_reuses_lease_correlation(self):
        from schoolnet.protocol_output import probe_event,ServiceProbeError
        b=Backend();s=Supervisor('owner',b);s.request(msg('connect'),'owner');wait(s,'READY')
        s.observe(probe_event('foreign',999,error=ServiceProbeError(TimeoutError())))
        s.phase('connection_warning',5);s.phase('running',5)
        self.assertEqual(s.snapshot()['state'],'DEGRADED')
        event=s.snapshot()['components']['riot_service']
        self.assertEqual(event['generation'],1);self.assertEqual(event['request_id'],'a'*32)
        b.probe=lambda observe:observe(probe_event('probe',0))
        s.request(msg('retry_probe','b'*32,1),'owner');self.assertEqual(wait(s,'READY'),'READY')
        s.request(msg('stop','c'*32,1),'owner');wait(s,'STOPPED')
        s.observe(probe_event('late',0),generation=0)
        self.assertEqual(s.snapshot()['components']['riot_service']['status'],'PASS')

    def test_recovery_failure_blocks_update_and_reconnect(self):
        b=Backend();s=Supervisor('owner',b);s.state='RECOVERY_REQUIRED'
        for op in ('prepare_update','connect'):
            with self.assertRaises(ValueError):s.request(msg(op),'owner')
        b.recover=lambda:(_ for _ in ()).throw(OSError())
        s.request(msg('stop'),'owner');self.assertEqual(wait(s,'RECOVERY_REQUIRED'),'RECOVERY_REQUIRED')
