import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest


DIRECTORY = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("homebrew_update", DIRECTORY / "update.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.cask = self.directory / "miner.rb"
        self.receipt = self.directory / "verified.json"
        # Keep the real cask's install/uninstall safeguards in this fixture while
        # making tests independent of whichever version the bot has published.
        text = (DIRECTORY.parents[1] / "Casks/miner.rb").read_text()
        text = re.sub(r'^  version "[^"]+"$', '  version "1"', text, flags=re.MULTILINE)
        self.cask.write_text(text)
        self.original = text
        self.calls = []

    def release(self, version="2"):
        tag = f"miner-alpha-v{version}"
        self.files = {}
        platforms = []
        assets = [{"name": "release-manifest.json", "id": 10, "state": "uploaded"}]
        for architecture, suffix in [("arm64", "AppleSilicon"), ("x86_64", "Intel")]:
            filename = f"MINER-ALPHA-v{version}-macOS-{suffix}.dmg"
            payload = f"verified native test payload {architecture} v{version}".encode()
            path = self.directory / filename
            path.write_bytes(payload)
            self.files[filename] = path
            digest = hashlib.sha256(payload).hexdigest()
            platforms.append({"filename": filename, "architecture": architecture, "sha256": digest})
            assets.append({"name": filename, "id": len(assets) + 10,
                           "state": "uploaded", "digest": f"sha256:{digest}"})
        self.manifest = {"tag": tag, "codename": "ALPHA", "release_version": version,
                         "prerelease": False, "platforms": platforms}
        self.manifest_path = self.directory / "release-manifest.json"
        self.save_manifest()
        self.files["release-manifest.json"] = self.manifest_path
        return {"id": 123, "tag_name": tag, "draft": False,
                "prerelease": False, "assets": assets}

    def save_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest))

    def download(self, name):
        self.calls.append(name)
        return self.files[name]

    def update(self, release):
        return updater.update(release, self.download, self.cask, self.receipt)

    def assert_unchanged(self):
        self.assertEqual(self.original, self.cask.read_text())
        self.assertFalse(self.receipt.exists())

    def test_new_release_downloads_both_architectures_and_preserves_safeguards(self):
        release = self.release()
        self.update(release)
        text = self.cask.read_text()
        version, hashes = updater.current_values(text)
        self.assertEqual("2", version)
        self.assertEqual(3, len(self.calls))
        self.assertEqual({p["architecture"]: p["sha256"] for p in self.manifest["platforms"]}, hashes)
        self.assertEqual(self.original.split('  name "MINER ALPHA"')[1],
                         text.split('  name "MINER ALPHA"')[1])
        self.assertTrue(json.loads(self.receipt.read_text())["downloads_verified"])

    def test_repeat_run_does_not_redownload_or_change_verified_files(self):
        release = self.release()
        self.update(release)
        before = (self.cask.read_bytes(), self.receipt.read_bytes())
        self.calls.clear()
        self.assertIn("Already verified", self.update(release))
        self.assertEqual([], self.calls)
        self.assertEqual(before, (self.cask.read_bytes(), self.receipt.read_bytes()))

    def test_missing_or_duplicate_intel_asset_cannot_publish_partial_update(self):
        release = self.release()
        for assets in [release["assets"][:-1], release["assets"] + [release["assets"][-1]]]:
            with self.subTest(assets=len(assets)):
                with self.assertRaises(ValueError):
                    self.update(dict(release, assets=assets))
                self.assert_unchanged()
        self.assertEqual([], self.calls)

    def test_corrupted_second_dmg_leaves_cask_and_receipt_untouched(self):
        release = self.release()
        self.files[release["assets"][-1]["name"]].write_bytes(b"truncated download")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.update(release)
        self.assert_unchanged()

    def test_download_failure_leaves_previous_cask_untouched(self):
        release = self.release()

        def failed_download(name):
            if name.endswith("Intel.dmg"):
                raise OSError("connection interrupted")
            return self.download(name)

        with self.assertRaises(OSError):
            updater.update(release, failed_download, self.cask, self.receipt)
        self.assert_unchanged()

    def test_github_checksum_must_also_match(self):
        release = self.release()
        release["assets"][-1]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "GitHub asset checksum mismatch"):
            self.update(release)
        self.assert_unchanged()

    def test_prereleases_drafts_and_other_codenames_do_not_update(self):
        release = self.release()
        for overrides in [{"prerelease": True}, {"draft": True},
                          {"tag_name": "miner-alpha-v2-beta.1"},
                          {"tag_name": "miner-delta-v2"}]:
            with self.subTest(overrides=overrides):
                self.assertIn("Skipped", self.update(dict(release, **overrides)))
                self.assert_unchanged()
        self.assertEqual([], self.calls)

    def test_older_latest_release_never_downgrades_cask(self):
        release = self.release("1")
        self.cask.write_text(self.original.replace('  version "1"', '  version "2"'))
        before = self.cask.read_bytes()
        self.assertIn("not downgraded", self.update(release))
        self.assertEqual(before, self.cask.read_bytes())
        self.assertFalse(self.receipt.exists())
        self.assertEqual([], self.calls)

    def test_replaced_same_version_payload_requires_new_version(self):
        release = self.release("1")
        with self.assertRaisesRegex(ValueError, "publish a new version"):
            self.update(release)
        self.assert_unchanged()

    def test_manifest_must_match_release_and_architecture(self):
        release = self.release()
        original = copy.deepcopy(self.manifest)
        for field, value in [("tag", "miner-alpha-v999"), ("prerelease", True),
                             ("release_version", "3"), ("codename", "DELTA")]:
            with self.subTest(field=field):
                self.manifest = dict(original, **{field: value})
                self.save_manifest()
                with self.assertRaises(ValueError):
                    self.update(release)
                self.assert_unchanged()
        self.manifest = original
        self.manifest["platforms"][-1]["architecture"] = "arm64"
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "platform"):
            self.update(release)
        self.assert_unchanged()

    def test_replaced_asset_id_forces_full_download_verification(self):
        release = self.release()
        self.update(release)
        before = (self.cask.read_bytes(), self.receipt.read_bytes())
        changed = copy.deepcopy(release)
        changed["assets"][-1]["id"] = 999
        self.files[changed["assets"][-1]["name"]].write_bytes(b"bad replacement")
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.update(changed)
        self.assertEqual(3, len(self.calls))
        self.assertEqual(before, (self.cask.read_bytes(), self.receipt.read_bytes()))

    def test_numeric_versions_order_correctly(self):
        self.assertLess(updater.version_key("2"), updater.version_key("10"))
        self.assertLess(updater.version_key("2.9"), updater.version_key("2.10"))
        self.assertEqual(updater.version_key("1"), updater.version_key("1.0"))

    def test_unknown_cask_layout_requires_review(self):
        release = self.release()
        self.cask.write_text(self.original.replace("miner-alpha-v#{version}", "unknown"))
        with self.assertRaisesRegex(ValueError, "format changed"):
            self.update(release)
        self.assertFalse(self.receipt.exists())
        self.assertEqual([], self.calls)


if __name__ == "__main__":
    unittest.main()
