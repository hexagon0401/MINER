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
        for payload in [b"{}",b"x"*(helper.LIMIT+1)+b"\n",b"[]\n"]:
            left,right=socket.socketpair()
            try:
                right.sendall(payload);right.shutdown(socket.SHUT_WR)
                with self.assertRaises(ValueError):helper.receive(left)
            finally:left.close();right.close()


if __name__=="__main__":unittest.main()
