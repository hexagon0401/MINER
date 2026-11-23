import unittest
from unittest.mock import patch
from schoolnet.health_model import Observation,HealthState
from schoolnet.protocol_output import ServiceProbeError,probe_event
from schoolnet.warp import configuration_snapshot

class HealthTests(unittest.TestCase):
    def obs(self,**kw):
        data=dict(component='riot_service',status='FAIL',request_id='r1',generation=1,observed_at=100,ttl_seconds=30,evidence='CODE_TEST',reason_code='RIOT_PROBE_FAILED');data.update(kw);return Observation(**data)
    def test_enums_and_metadata_are_validated(self):
        for kw in [dict(status='HEALTHY'),dict(component='shell'),dict(generation=True),dict(ttl_seconds=-1),dict(observed_at=float('nan')),dict(request_id='../secret'),dict(evidence='guess')]:
            with self.subTest(kw=kw),self.assertRaises(ValueError):self.obs(**kw)
    def test_ttl_and_future_evidence_never_read_as_ready(self):
        self.assertEqual(self.obs(status='PASS').effective(130),'UNKNOWN');self.assertEqual(self.obs().effective(99),'UNKNOWN')
    def test_old_generation_wrong_request_and_duplicate_cannot_override(self):
        state=HealthState();state.begin('riot_service','r1',1)
        self.assertTrue(state.accept(self.obs(),100));self.assertFalse(state.accept(self.obs(),100))
        self.assertFalse(state.accept(self.obs(request_id='other'),100))
        state.begin('riot_service','r2',2);self.assertFalse(state.accept(self.obs(),100));self.assertEqual(state.status('riot_service',100),'UNKNOWN')
    def test_probe_failure_does_not_mutate_engine_observation(self):
        state=HealthState();state.begin('engine','r1',1);state.begin('riot_service','r1',1)
        state.accept(self.obs(component='engine',status='READY',reason_code='ENGINE_READY'),100);state.accept(self.obs(),100)
        self.assertEqual(state.status('engine',100),'READY');self.assertEqual(state.status('riot_service',100),'FAIL')
    def test_error_payload_is_allowlisted_and_not_statistics_success(self):
        error=ServiceProbeError(TimeoutError('token=SECRET 192.168.1.1'))
        event=probe_event('r1',1,error=error)
        self.assertEqual(event['status'],'TIMEOUT');self.assertFalse(event['statistics_verified']);self.assertNotIn('SECRET',str(event)+str(error))
    def test_restore_policy_is_fixed_for_all_starting_states(self):
        for mode,status in [('Warp','Connected'),('WarpProxy','Disconnected'),('DnsOverHttps','Disconnected'),('WarpWithDnsOverHttps','Connected')]:
            result=configuration_snapshot('Mode: '+mode,status)
            self.assertEqual(result['mode'],mode);self.assertEqual(result['restore_policy'],'FIXED_WARP_CONNECTED');self.assertFalse(result['exclusive_ownership'])

class ProtocolTests(unittest.TestCase):
    def test_cli_progress_and_machine_status_not_emitted_as_human_error(self):
        import io,json,contextlib,main
        error=ServiceProbeError(TimeoutError('private details'))
        stdout=io.StringIO();stderr=io.StringIO()
        with patch('schoolnet.warp.verify_client_service',side_effect=error),contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            code=main.main(['warp','service-check','--progress','--request-id','r1','--generation','1'])
        self.assertEqual(code,1);self.assertNotIn('"event"',stderr.getvalue())
        events=[json.loads(line) for line in stdout.getvalue().splitlines()]
        self.assertEqual(events[-1]['status'],'TIMEOUT');self.assertEqual(events[-1]['request_id'],'r1')
        self.assertFalse(events[-1]['statistics_verified'])
