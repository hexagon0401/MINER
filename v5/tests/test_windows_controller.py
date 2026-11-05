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
