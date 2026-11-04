import importlib.util
from pathlib import Path
import tempfile
import unittest
import unicodedata

SPEC = importlib.util.spec_from_file_location("macos_build", Path(__file__).resolve().parents[1] / "macos/build.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)


class PackagingTests(unittest.TestCase):
    def test_ascii_resources_survive_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            app = Path(directory) / "SchoolNet v5 Alpha.app"
            resources = app / "Contents/Resources"
            resources.mkdir(parents=True)
            (resources / "UserGuide.txt").write_text("한국어 내용은 파일명과 별개입니다.")
            build.validate_resource_paths(app)
            for path in app.rglob("*"):
                self.assertEqual(unicodedata.normalize("NFC", str(path)), unicodedata.normalize("NFD", str(path)))

    def test_rejects_both_unicode_filename_normalizations_before_signing(self):
        for form in ["NFC", "NFD"]:
            with self.subTest(form=form), tempfile.TemporaryDirectory() as directory:
                app = Path(directory) / "App.app"
                app.mkdir()
                (app / unicodedata.normalize(form, "사용 안내.txt")).write_text("guide")
                with self.assertRaisesRegex(ValueError, "non-ASCII"):
                    build.validate_resource_paths(app)


if __name__ == "__main__":
    unittest.main()
