import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from schoolnet import macos_service as service


class ServiceTests(unittest.TestCase):
    def test_preserves_unmanaged_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "user-file").write_text("preserve")
            with self.assertRaisesRegex(ValueError, "not marked"):
                service.owned_base(path)
            self.assertEqual((path / "user-file").read_text(), "preserve")

    def test_symlink_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "link").symlink_to(path / "actual", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                service.owned_base(path / "link")

    def test_uninstall_stops_before_removing_only_managed_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory) / "managed"
            base.mkdir()
            (base / service.MARKER).write_text(json.dumps({"id": service.LABEL}))
            unrelated = Path(directory) / "WARP"
            unrelated.write_text("untouched")
            with patch.object(service, "BASE", base), patch("platform.system", return_value="Darwin"), patch(
                "os.geteuid", return_value=0), patch.object(service, "stop") as stop:
                self.assertEqual(service.manage("uninstall"), 0)
                stop.assert_called_once()
            self.assertFalse(base.exists())
            self.assertEqual(unrelated.read_text(), "untouched")

    def test_failed_stop_prevents_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / service.MARKER).write_text(json.dumps({"id": service.LABEL}))
            with patch.object(service, "BASE", base), patch("platform.system", return_value="Darwin"), patch(
                "os.geteuid", return_value=0), patch.object(service, "stop", side_effect=ValueError("cleanup active")):
                with self.assertRaisesRegex(ValueError, "cleanup active"):
                    service.manage("uninstall")
            self.assertTrue((base / service.MARKER).exists())

    def test_mutations_require_admin_and_macos(self):
        with patch("platform.system", return_value="Linux"), self.assertRaisesRegex(ValueError, "macOS-only"):
            service.manage("start")
        with patch("platform.system", return_value="Darwin"), patch("os.geteuid", return_value=501), self.assertRaisesRegex(ValueError, "administrator"):
            service.manage("uninstall")

    def test_status_does_not_claim_functional_readiness(self):
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "state = running\n pid = 123\n")):
            result = service.status()
        self.assertTrue(result["running"])
        self.assertEqual(result["pid"], 123)
        self.assertNotIn("ready", result)
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "")):
            self.assertFalse(service.status()["running"])

    def test_refuses_app_from_disk_image_before_network_commands(self):
        with self.assertRaisesRegex(ValueError, "/Applications"):
            service.prepare(Path("/Volumes/SchoolNet/SchoolNet v5 Alpha.app/Contents/Resources"), Path("/tmp/profile"))


if __name__ == "__main__":
    unittest.main()
