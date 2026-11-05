import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import icon_assets


class IconAssetsTests(unittest.TestCase):
    def test_official_alpha_codename_can_explicitly_select_stable(self):
        self.assertEqual("stable", icon_assets.release_channel("5.0.0-alpha.1.0.1", "stable"))
        self.assertEqual("beta", icon_assets.release_channel("5.0.0-beta.2", "beta"))

    def test_default_distinguishes_numeric_release_and_legacy_betas(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("stable", icon_assets.release_channel("1.0.1"))
            self.assertEqual("beta", icon_assets.release_channel("5.0.0-beta.2"))

    def test_channel_copies_exact_asset_and_never_falls_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "beta").mkdir()
            (root / "beta/AppIcon.png").write_bytes(b"original beta icon")
            (root / "output").mkdir()
            with patch.object(icon_assets, "ICONS", root):
                result = icon_assets.bundle_icon(root / "output", "5-beta", "beta")
                self.assertEqual("beta", result["channel"])
                self.assertEqual(b"original beta icon", (root / "output/AppIcon.png").read_bytes())
                with self.assertRaisesRegex(ValueError, "never fall back"):
                    icon_assets.bundle_icon(root / "output", "1.0.1", "stable")

    def test_unknown_channel_is_rejected(self):
        with self.assertRaises(ValueError):
            icon_assets.release_channel("1.0.1", "betaa")

    def test_official_codename_tag_and_beta_tag_choose_different_icons(self):
        with patch.dict(os.environ, {"GITHUB_REF_TYPE": "tag", "GITHUB_REF_NAME": "miner-alpha-v2"}, clear=True):
            self.assertEqual("stable", icon_assets.release_channel("5.0.0-beta.2"))
        with patch.dict(os.environ, {"GITHUB_REF_TYPE": "tag", "GITHUB_REF_NAME": "v5.0.0-beta.2"}, clear=True):
            self.assertEqual("beta", icon_assets.release_channel("5.0.0-beta.2"))


if __name__ == "__main__":
    unittest.main()
