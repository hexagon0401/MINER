import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from windows import controller


class WindowsLifecycleTests(unittest.TestCase):
    def test_profile_preserves_edits_and_rejects_other_platform(self):
        with tempfile.TemporaryDirectory() as d:
            p=controller.prepare(d)
            self.assertEqual(p.platform,'windows')
            path=Path(d)/'profile.json'
            values=json.loads(path.read_text()); values['proxy_port']=41000
            path.write_text(json.dumps(values))
            self.assertEqual(controller.prepare(d).proxy_port,41000)
            values['platform']='macos'; path.write_text(json.dumps(values))
            with self.assertRaises(ValueError): controller.prepare(d)

    def test_cancel_during_warp_setup_restores_without_starting_tun(self):
        with tempfile.TemporaryDirectory() as d:
            stop=threading.Event(); calls=[]
            def activate(*args,**kwargs): calls.append('activate');stop.set()
            with patch.object(controller,'is_admin',return_value=True), patch.object(controller.warp,'activate',side_effect=activate), patch.object(controller.warp,'restore',side_effect=lambda:calls.append('restore')), patch.object(controller.subprocess,'Popen') as popen:
                controller.session(d,'engine',stop,lambda *args:None)
                popen.assert_not_called()
            self.assertEqual(calls,['activate','restore'])

    def test_proxy_failure_never_starts_engine_or_restores_full_tunnel(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(controller,'is_admin',return_value=True), patch.object(controller.warp,'activate',side_effect=ValueError('proxy failed')), patch.object(controller.warp,'restore') as restore, patch.object(controller.subprocess,'Popen') as popen:
                with self.assertRaisesRegex(ValueError,'proxy failed'):
                    controller.session(d,'engine',threading.Event(),lambda *args:None)
                restore.assert_not_called(); popen.assert_not_called()

    def test_explicit_restore_retry_does_not_activate_proxy(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(controller,'is_admin',return_value=True), patch.object(controller.warp,'activate') as activate, patch.object(controller.warp,'restore') as restore:
                controller.session(d,'engine',threading.Event(),lambda *args:None,True)
                restore.assert_called_once(); activate.assert_not_called()

    def test_forced_stop_is_reported_as_failure(self):
        child=MagicMock();child.poll.return_value=None
        child.wait.side_effect=[controller.subprocess.TimeoutExpired('engine',10),0]
        with patch.object(controller.signal,'CTRL_BREAK_EVENT',1,create=True):
            with self.assertRaisesRegex(ValueError,'forced'):
                controller.stop_engine(child)
        child.kill.assert_called_once()

    def test_non_admin_cannot_change_warp(self):
        with patch.object(controller,'is_admin',return_value=False),patch.object(controller.warp,'activate') as activate:
            with self.assertRaisesRegex(ValueError,'Administrator'):
                controller.session('unused','engine',threading.Event(),lambda *args:None)
            activate.assert_not_called()

    def test_restore_failure_keeps_recovery_marker(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(controller,'is_admin',return_value=True), patch.object(controller.warp,'restore',side_effect=ValueError('restore failed')):
                with self.assertRaisesRegex(ValueError,'restore failed'):
                    controller.session(d,'engine',threading.Event(),lambda *a:None,True)
            self.assertTrue((Path(d)/'session.json').exists())

    def test_successful_restore_clears_recovery_marker_and_ignores_bad_profile(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'profile.json').write_text('invalid JSON')
            (Path(d)/'session.json').write_text('{}')
            events=[]
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'restore'):
                controller.session(d,'engine',threading.Event(),lambda *a:events.append(a),True)
            self.assertFalse((Path(d)/'session.json').exists())
            self.assertEqual(events[-1],('restored',0))

    def test_engine_schema_failure_never_spawns_or_restores_implicitly(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'activate'),patch.object(controller,'doctor',side_effect=ValueError('bad engine')),patch.object(controller.subprocess,'Popen') as spawn,patch.object(controller.warp,'restore') as restore:
                with self.assertRaisesRegex(ValueError,'bad engine'):
                    controller.session(d,'engine',threading.Event(),lambda *a:None)
                spawn.assert_not_called();restore.assert_not_called()
            self.assertTrue((Path(d)/'session.json').exists())

    def test_engine_early_exit_keeps_recovery_state_and_closes_job(self):
        child=MagicMock();child.poll.return_value=1
        job=MagicMock()
        with tempfile.TemporaryDirectory() as d:
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'activate'),patch.object(controller,'doctor',return_value={'preflight_ok':True}),patch.object(controller.subprocess,'Popen',return_value=child),patch.object(controller.subprocess,'CREATE_NEW_PROCESS_GROUP',512,create=True),patch('windows.process.Job',return_value=job),patch.object(controller.warp,'restore') as restore:
                with self.assertRaisesRegex(ValueError,'unexpectedly'):
                    controller.session(d,'engine',threading.Event(),lambda *a:None)
                job.assign.assert_called_once_with(child);job.close.assert_called_once();restore.assert_not_called()
            self.assertTrue((Path(d)/'session.json').exists())

    def test_emergency_disconnects_warp_without_restoring_full_tunnel(self):
        with tempfile.TemporaryDirectory() as d:
            kill=threading.Event();kill.set();events=[]
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'restore') as restore,patch.object(controller.warp,'deactivate') as disconnect:
                controller.session(d,'engine',threading.Event(),lambda *a:events.append(a),True,kill)
                disconnect.assert_called_once();restore.assert_not_called()
            self.assertEqual(events[-1],('disconnected',0));self.assertFalse((Path(d)/'session.json').exists())

    def test_emergency_during_activation_does_not_start_engine(self):
        with tempfile.TemporaryDirectory() as d:
            stop=threading.Event();kill=threading.Event()
            def activate(*a,**k):stop.set();kill.set()
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'activate',side_effect=activate),patch.object(controller.warp,'deactivate') as disconnect,patch.object(controller.warp,'restore') as restore,patch.object(controller.subprocess,'Popen') as spawn:
                controller.session(d,'engine',stop,lambda *a:None,False,kill)
                disconnect.assert_called_once();restore.assert_not_called();spawn.assert_not_called()

    def test_emergency_cleans_up_after_activation_error(self):
        with tempfile.TemporaryDirectory() as d:
            kill=threading.Event();kill.set()
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'activate',side_effect=ValueError('proxy failed')),patch.object(controller.warp,'deactivate') as disconnect:
                controller.session(d,'engine',threading.Event(),lambda *a:None,False,kill)
                disconnect.assert_called_once()

    def test_emergency_requested_during_restore_wins_serially(self):
        with tempfile.TemporaryDirectory() as d:
            kill=threading.Event();calls=[]
            def restore():calls.append('restore');kill.set();raise ValueError('restore interrupted')
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'restore',side_effect=restore),patch.object(controller.warp,'deactivate',side_effect=lambda:calls.append('disconnect')):
                controller.session(d,'engine',threading.Event(),lambda *a:None,True,kill)
            self.assertEqual(calls,['restore','disconnect'])

    def test_failed_emergency_disconnect_never_claims_success(self):
        with tempfile.TemporaryDirectory() as d:
            kill=threading.Event();kill.set();events=[]
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'deactivate',side_effect=ValueError('disconnect failed')):
                with self.assertRaisesRegex(ValueError,'disconnect failed'):
                    controller.session(d,'engine',threading.Event(),lambda *a:events.append(a),True,kill)
            self.assertTrue((Path(d)/'session.json').exists());self.assertNotIn(('disconnected',0),events)

    def test_late_emergency_never_labels_restore_as_disconnection(self):
        with tempfile.TemporaryDirectory() as d:
            kill=threading.Event();events=[];original=Path.unlink
            def unlink(path,*a,**k):
                result=original(path,*a,**k)
                if path.name=='session.json':kill.set()
                return result
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'restore'),patch.object(controller.warp,'deactivate') as disconnect,patch.object(Path,'unlink',unlink):
                controller.session(d,'engine',threading.Event(),lambda *a:events.append(a),True,kill)
                disconnect.assert_not_called()
            self.assertEqual(events[-1],('restored',0))

    def test_emergency_stops_engine_before_disconnect(self):
        with tempfile.TemporaryDirectory() as d:
            stop=threading.Event();kill=threading.Event();calls=[]
            child=MagicMock();child.poll.return_value=None
            def emit(phase,count):
                if phase=='engine_start':stop.set();kill.set()
            def stopped(proc):
                if proc is child:calls.append('engine stopped');child.poll.return_value=0
            with patch.object(controller,'is_admin',return_value=True),patch.object(controller.warp,'activate'),patch.object(controller,'doctor',return_value={'preflight_ok':True}),patch.object(controller.subprocess,'Popen',return_value=child),patch.object(controller.subprocess,'CREATE_NEW_PROCESS_GROUP',512,create=True),patch('windows.process.Job'),patch.object(controller,'stop_engine',side_effect=stopped),patch.object(controller.warp,'deactivate',side_effect=lambda:calls.append('warp disconnected')):
                controller.session(d,'engine',stop,emit,False,kill)
            self.assertEqual(calls,['engine stopped','warp disconnected'])
