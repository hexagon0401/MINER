import json
import os
import socket
import unittest
from unittest.mock import patch

from schoolnet import macos_helper as helper


@unittest.skipIf(os.name=="nt","Unix helper protocol")
class HelperTests(unittest.TestCase):
    def test_only_installing_user_and_fixed_operations_are_authorized(self):
        with self.assertRaisesRegex(ValueError,"installing user"):
            helper.dispatch({"operation":"stop"},502,501)
        for operation in ["shell","uninstall","install","arbitrary"]:
            with self.subTest(operation=operation),self.assertRaisesRegex(ValueError,"Unsupported"):
                helper.dispatch({"operation":operation,"command":"touch /tmp/bad"},501,501)

    def test_status_does_not_start_engine_and_stop_requires_matching_owner(self):
        with patch.object(helper.service,"status",return_value={"running":False}),patch.object(helper.service,"manage") as manage:
            self.assertFalse(helper.dispatch({"operation":"status"},501,501)["running"])
            manage.assert_not_called()
        with patch.object(helper.service,"stop",return_value={"running":False}) as stop:
            self.assertTrue(helper.dispatch({"operation":"stop"},501,501)["ok"])
            stop.assert_called_once()

    def test_non_macos_profiles_never_reach_service(self):
        with patch.object(helper.service,"start_installed") as manage,self.assertRaises(ValueError):
            helper.dispatch({"operation":"start","profile":{"platform":"windows"}},501,501)
        manage.assert_not_called()

    def test_reused_approval_never_prepares_or_executes_the_mutable_app_bundle(self):
        with patch.object(helper.service,"status",return_value={"running":False}),patch.object(helper.service,"prepare") as prepare,patch.object(helper.service,"start_installed",return_value={"running":True}) as start:
            result=helper.dispatch({"operation":"start","profile":{"platform":"macos"}},501,501)
            self.assertTrue(result['running']);start.assert_called_once();prepare.assert_not_called()

    def test_kernel_peer_identity_matches_current_user(self):
        left,right=socket.socketpair()
        try:self.assertEqual(os.getuid(),helper.peer_uid(left))
        finally:left.close();right.close()

    def test_bounded_json_protocol_rejects_truncated_and_oversized_messages(self):
        # Darwin socketpair buffers may be smaller than the production limit;
        # keep boundary fixtures below that buffer instead of blocking sendall.
        for payload in [b"{}",b"x"*65+b"\n",b"[]\n"]:
            left,right=socket.socketpair()
            try:
                left.settimeout(2);right.settimeout(2)
                right.sendall(payload);right.shutdown(socket.SHUT_WR)
                with patch.object(helper,"LIMIT",64),self.assertRaises(ValueError):helper.receive(left)
            finally:left.close();right.close()


if __name__=="__main__":unittest.main()


class MacLeaseGateTests(unittest.TestCase):
    def test_repeated_request_is_idempotent_and_restart_rejects_old_generation(self):
        import tempfile
        from pathlib import Path
        from schoolnet.lease_owner import Ownership
        with tempfile.TemporaryDirectory() as d:
            record=Ownership(Path(d)/'owner.json','501');gate=helper.CommandGate(501,record)
            request={'operation':'start','version':helper.__version__,'request_id':'a'*32,'expected_generation':0,'profile':{'platform':'macos'}}
            with patch.object(helper.service,'status',return_value={'running':False}),patch.object(helper.service,'start_installed',return_value={'running':True}) as start:
                self.assertEqual(gate.execute(request,501)['generation'],1)
                gate.execute(request,501);start.assert_called_once()
                with self.assertRaises(ValueError):helper.CommandGate(501,record).execute(request,501)
                with self.assertRaises(ValueError):gate.execute(dict(request,request_id='b'*32),502)
                with self.assertRaises(ValueError):gate.execute(dict(request,command='shell'),501)
            self.assertTrue(record.read()['unfinished'])
            with patch.object(helper.service,'stop',return_value={'running':False}):
                gate.execute({'operation':'stop','version':helper.__version__,'request_id':'c'*32,'expected_generation':1},501)
            self.assertFalse(record.read()['unfinished'])
