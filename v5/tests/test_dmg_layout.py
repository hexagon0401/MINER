from pathlib import Path
import tempfile
import unittest
from macos.dmg_layout import settings, APP_POSITION, APPLICATIONS_POSITION, WINDOW_SIZE, ICON_SIZE


class DmgLayoutTests(unittest.TestCase):
    def test_real_app_and_applications_have_fixed_cavern_positions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "SchoolNet v5 Alpha.app"
            app.mkdir()
            background = root / "background.png"
            background.write_bytes(b"fixture-path-only")
            config = settings(app, background)
            self.assertEqual(config["files"], [str(app)])
            self.assertEqual(config["symlinks"], {"Applications": "/Applications"})
            self.assertEqual(config["icon_locations"][app.name], APP_POSITION)
            self.assertEqual(config["icon_locations"]["Applications"], APPLICATIONS_POSITION)
            self.assertLess(APP_POSITION[0], APPLICATIONS_POSITION[0])
            self.assertIsNone(config["arrange_by"])
            self.assertFalse(config["show_toolbar"])
            self.assertEqual(config["background"], str(background))
            for x, y in [APP_POSITION, APPLICATIONS_POSITION]:
                self.assertTrue(ICON_SIZE/2 < x < WINDOW_SIZE[0]-ICON_SIZE/2)
                self.assertTrue(ICON_SIZE/2 < y < WINDOW_SIZE[1]-ICON_SIZE/2)

    def test_missing_original_background_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "App.app"
            app.mkdir()
            with self.assertRaisesRegex(ValueError, "background image is missing"):
                settings(app, Path(directory) / "missing.png")


if __name__ == "__main__":
    unittest.main()
