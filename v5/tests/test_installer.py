import hashlib
import io
import tarfile
import unittest
from unittest.mock import patch
import zipfile

import install_engine


class InstallerTests(unittest.TestCase):
    def test_modified_download_rejected_before_unpacking(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            install_engine.unpack_verified(b"modified archive", "darwin-arm64")

    def test_verified_archive_extracts_only_named_binary(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w:gz") as archive:
            for name, content in [("sing-box-1.12.0-darwin-arm64/sing-box", b"fixture"),
                                  ("../../unexpected", b"never extract this")]:
                entry = tarfile.TarInfo(name)
                entry.size = len(content)
                archive.addfile(entry, io.BytesIO(content))
        raw = data.getvalue()
        with patch.dict(install_engine.DIGESTS, {"darwin-arm64": hashlib.sha256(raw).hexdigest()}):
            self.assertEqual(install_engine.unpack_verified(raw, "darwin-arm64"), ("sing-box", b"fixture"))

    def test_windows_zip_layout(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("sing-box-1.12.0-windows-amd64/sing-box.exe", b"fixture-exe")
        raw = data.getvalue()
        with patch.dict(install_engine.DIGESTS, {"windows-amd64": hashlib.sha256(raw).hexdigest()}):
            self.assertEqual(install_engine.unpack_verified(raw, "windows-amd64"), ("sing-box.exe", b"fixture-exe"))

    def test_architecture_mapping(self):
        for system, machine, expected in [("Darwin", "arm64", "darwin-arm64"),
                                          ("Darwin", "x86_64", "darwin-amd64"),
                                          ("Windows", "AMD64", "windows-amd64")]:
            with patch("platform.system", return_value=system), patch("platform.machine", return_value=machine):
                self.assertEqual(install_engine.target_key(), expected)


if __name__ == "__main__":
    unittest.main()
