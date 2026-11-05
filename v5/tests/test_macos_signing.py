import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from macos import signing
from macos import signing_credentials


@unittest.skipIf(os.name == "nt", "macOS service/signing contracts use POSIX permissions; tested on POSIX CI")
class SigningTests(unittest.TestCase):
    def test_requires_developer_id_not_apple_development(self):
        digest = "A" * 40
        for name, accepted in [("Apple Development: Fixture (ABCDE12345)", False),
                               ("Developer ID Application: Fixture (ABCDE12345)", True)]:
            with self.subTest(name=name), patch("subprocess.run", return_value=subprocess.CompletedProcess(
                    [], 0, stdout=f'1) {digest} "{name}"\n')):
                if accepted:
                    self.assertEqual(signing.developer_identity(digest), digest)
                else:
                    with self.assertRaises(ValueError):
                        signing.developer_identity(digest)

    def test_missing_signing_and_notary_credentials_fail_explicitly(self):
        with self.assertRaises(ValueError):
            signing.developer_identity(None)
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, "APPLE_NOTARY_KEY"):
            signing.validate_notary_credentials()

    def test_inside_out_signing_with_hardened_runtime_and_timestamp(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "App.app"
            framework = app / "Contents/Resources/Python.framework"
            framework.mkdir(parents=True)
            binary = framework / "Python"
            binary.write_bytes(bytes.fromhex("cffaedfe") + b"fixture")
            (framework / "UserGuide.txt").write_text("not code")
            calls = []
            signing.sign_app(app, "fixture-identity", lambda *args: calls.append(args))
            self.assertEqual(calls[0][-1], binary.resolve())
            self.assertEqual(calls[1][-1], framework.resolve())
            self.assertEqual(calls[2][-1], app)
            for call in calls[:-1]:
                self.assertIn("runtime", call)
                self.assertIn("--timestamp", call)
                self.assertNotIn("--deep", call)
            self.assertIn("--verify", calls[-1])

    def test_rejected_notarization_never_staples(self):
        with tempfile.TemporaryDirectory() as directory, patch("subprocess.run", return_value=subprocess.CompletedProcess(
                [], 0, stdout=json.dumps({"status": "Invalid", "id": "fixture"}))):
            calls = []
            receipt = Path(directory) / "receipt.json"
            with self.assertRaisesRegex(RuntimeError, "not Accepted"):
                signing.notarize(Path(directory) / "App.dmg", receipt, lambda *args: calls.append(args), "local-profile")
            self.assertFalse(calls)
            self.assertEqual(json.loads(receipt.read_text())["status"], "Invalid")

    def test_zip_submission_does_not_attempt_staple_zip(self):
        for suffix in [".zip", ".dmg"]:
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory, patch(
                "subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout='{"status":"Accepted"}')):
                calls = []
                signing.notarize(Path(directory) / ("App" + suffix), Path(directory) / "receipt.json",
                                 lambda *args: calls.append(args), "local-profile")
                self.assertEqual(len(calls), 0 if suffix == ".zip" else 2)

    def test_private_notary_file_is_temporary_and_not_an_argument_value(self):
        fixture = b"fixture-private-key"
        variables = {"APPLE_NOTARY_KEY_P8_BASE64": base64.b64encode(fixture).decode(),
                     "APPLE_NOTARY_KEY_ID": "fixture-id", "APPLE_NOTARY_ISSUER_ID": "fixture-issuer"}
        with patch.dict(os.environ, variables, clear=True):
            with signing.notary_arguments() as arguments:
                path = Path(arguments[1])
                self.assertEqual(path.read_bytes(), fixture)
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
                self.assertNotIn(fixture.decode(), arguments)
            self.assertFalse(path.exists())

    def test_keychain_cleanup_rejects_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"RUNNER_TEMP": directory}):
            with self.assertRaisesRegex(ValueError, "refusing cleanup"):
                signing_credentials.cleanup(str(Path(directory) / "unrelated.keychain-db"))


if __name__ == "__main__":
    unittest.main()
