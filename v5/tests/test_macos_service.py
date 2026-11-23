import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from schoolnet import macos_service as service
from schoolnet.config import Profile


@unittest.skipIf(os.name == "nt", "macOS service/signing contracts use POSIX permissions; tested on POSIX CI")
class ServiceTests(unittest.TestCase):
    def test_managed_upgrade_preserves_profile_and_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, resources = root / "managed", root / "resources"
            (base / "runtime").mkdir(parents=True)
            (base / "runtime/old").write_text("old")
            (base / "bin").mkdir()
            (base / "bin/sing-box").write_text("old-engine")
            (base / service.MARKER).write_text(json.dumps({"id": service.LABEL, "version": "old"}))
            (base / "engine.log").write_text("keep log")
            (resources / "runtime/schoolnet-cli").mkdir(parents=True)
            (resources / "runtime/schoolnet-cli/schoolnet-cli").write_text("new-runtime")
            (resources / "bin").mkdir()
            (resources / "bin/sing-box").write_text("new-engine")
            with patch.object(service, "check_engine"):
                service.install_runtime(base, resources, Profile())
            self.assertEqual((base / "runtime/schoolnet-cli").read_text(), "new-runtime")
            self.assertEqual((base / "engine.log").read_text(), "keep log")
            self.assertEqual(json.loads((base / service.MARKER).read_text())["version"], service.__version__)

    def test_bad_upgrade_does_not_replace_existing_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base, resources = root / "managed", root / "resources"
            (base / "runtime").mkdir(parents=True)
            (base / "runtime/old").write_text("preserve")
            (resources / "runtime/schoolnet-cli").mkdir(parents=True)
            (resources / "runtime/schoolnet-cli/schoolnet-cli").write_text("new")
            (resources / "bin").mkdir()
            (resources / "bin/sing-box").write_text("bad-engine")
            with patch.object(service, "check_engine", side_effect=ValueError("schema failed")), self.assertRaises(ValueError):
                service.install_runtime(base, resources, Profile())
            self.assertEqual((base / "runtime/old").read_text(), "preserve")

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
        self.assertFalse(result["ready"])
        with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "")):
            self.assertFalse(service.status()["running"])

    def test_refuses_app_from_disk_image_before_network_commands(self):
        with self.assertRaisesRegex(ValueError, "/Applications"):
            service.prepare(Path("/Volumes/SchoolNet/SchoolNet v5 Alpha.app/Contents/Resources"), Path("/tmp/profile"))

    def test_canonical_installed_alias_reaches_profile_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed=root/'Applications/MINER.app/Contents/Resources';installed.mkdir(parents=True)
            alias=root/'volume-alias';alias.symlink_to(installed,target_is_directory=True)
            with patch.object(service,'APP_RESOURCES',installed),patch.object(service,'load_profile',side_effect=ValueError('profile validation reached')) as profile,patch.object(service,'doctor') as doctor:
                with self.assertRaisesRegex(ValueError,'profile validation reached'):service.prepare(alias,root/'profile')
                profile.assert_called_once();doctor.assert_not_called()

    def test_different_copy_and_missing_install_never_reach_privileged_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed=root/'Applications/MINER.app/Contents/Resources';installed.mkdir(parents=True)
            duplicate=root/'Downloads/MINER.app/Contents/Resources';duplicate.mkdir(parents=True)
            with patch.object(service,'APP_RESOURCES',installed),patch.object(service,'load_profile') as profile,patch.object(service,'doctor') as doctor:
                for path in (duplicate,root/'AppTranslocation/missing',None):
                    with self.subTest(path=path),self.assertRaisesRegex(ValueError,'/Applications'):service.prepare(path,root/'profile')
                profile.assert_not_called();doctor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
