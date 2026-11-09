import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,MagicMock

from schoolnet import updates
from windows.updates import installer_command


class UpdateTests(unittest.TestCase):
    def fixture(self, value="1.2.0"):
        name=f"MINER-ALPHA-v{value}-macOS-AppleSilicon.dmg"
        digest=hashlib.sha256(b"installer fixture").hexdigest()
        release={"tag_name":f"miner-alpha-v{value}","draft":False,"prerelease":False,
                 "assets":[{"name":name,"state":"uploaded","digest":"sha256:"+digest}]}
        manifest={"tag":release["tag_name"],"release_version":value,"codename":"ALPHA","prerelease":False,
                  "platforms":[{"filename":name,"architecture":"arm64","sha256":digest}]}
        return release,manifest

    def test_newer_version_only_and_no_downgrades(self):
        r,m=self.fixture()
        self.assertTrue(updates.select(r,m,"macos","arm64","1.1.1")["available"])
        self.assertFalse(updates.select(r,m,"macos","arm64","2")["available"])
        self.assertFalse(updates.select(r,m,"macos","arm64","1.2")["available"])

    def test_prerelease_missing_installer_and_wrong_architecture_fail(self):
        r,m=self.fixture()
        with self.assertRaises(ValueError):updates.select(dict(r,prerelease=True),m,"macos","arm64")
        with self.assertRaises(ValueError):updates.select(dict(r,assets=[]),m,"macos","arm64")
        with self.assertRaises(ValueError):updates.select(r,m,"macos","x86_64")
        with self.assertRaises(ValueError):updates.select(r,dict(m,tag="miner-alpha-v9"),"macos","arm64")

    def test_download_checks_sha_and_does_not_replace_good_installer_on_failure(self):
        r,m=self.fixture();info=updates.select(r,m,"macos","arm64")
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/info["filename"];path.write_bytes(b"existing file")
            with patch.object(updates,"open_url",return_value=io.BytesIO(b"truncated")),self.assertRaisesRegex(ValueError,"checksum"):
                updates.download(info,d)
            self.assertEqual(b"existing file",path.read_bytes())
            self.assertFalse(list(Path(d).glob("*.download")))
            with patch.object(updates,"open_url",return_value=io.BytesIO(b"installer fixture")):
                result=updates.download(info,d)
            self.assertTrue(result["verified"]);self.assertEqual(b"installer fixture",path.read_bytes())

    def test_traversal_and_unexpected_github_digest_fail(self):
        r,m=self.fixture();r["assets"][0]["digest"]="sha256:"+"0"*64
        with self.assertRaises(ValueError):updates.select(r,m,"macos","arm64")
        info={"filename":"../bad.exe","url":updates.BASE+"bad","sha256":"a"*64}
        with self.assertRaises(ValueError):updates.download(info,"unused")

    def test_redirect_cannot_downgrade_tls_or_send_request_to_other_hosts(self):
        for url in ["http://github.com/asset", "https://example.com/asset"]:
            with self.subTest(url=url),self.assertRaises(ValueError):
                updates.HTTPSRedirect().redirect_request(None,None,302,"",{},url)

    def test_check_uses_official_static_manifest_without_rest_api_quota(self):
        r,m=self.fixture('3.0.0');m['payloads_rebuilt']=True
        for suffix,arch in [('macOS-Intel.dmg','x86_64'),('Windows-x64-Setup.exe','x64')]:
            m['platforms'].append({'filename':'MINER-ALPHA-v3.0.0-'+suffix,'architecture':arch,'sha256':'a'*64})
        with patch.object(updates,'get_json',return_value=m) as get,patch.object(updates,'homebrew',return_value=None):
            self.assertTrue(updates.check('windows','x64')['available'])
        get.assert_called_once_with('https://github.com/hexagon0401/MINER/releases/latest/download/release-manifest.json')

    def test_cache_cleanup_preserves_future_installers_user_files_and_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            old=root/'MINER-ALPHA-v1.2.0-Windows-x64-Setup.exe';old.write_bytes(b'old')
            future=root/'MINER-ALPHA-v1.3.0-macOS-Intel.dmg';future.write_bytes(b'future')
            personal=root/'notes.txt';personal.write_text('preserve')
            updates.clean_cache(root,'1.2.1')
            self.assertFalse(old.exists());self.assertTrue(future.exists());self.assertTrue(personal.exists())

    def test_windows_verified_update_waits_and_relaunches_only_after_success(self):
        command=installer_command('Setup.exe',123,'C:/Program Files/MINER','a'*64)
        self.assertIn('Get-FileHash',command);self.assertIn('-PassThru -Wait',command)
        self.assertLess(command.index('ExitCode'),command.index('Remove-Item'))
        self.assertIn('/DIR="C:/Program Files/MINER"',command)

    def test_windows_installer_does_not_inherit_the_runtime_dll_directory(self):
        import windows.updates as windows
        dll=MagicMock()
        with patch.object(windows.sys,'platform','win32'),patch.object(windows.sys,'frozen',True,create=True),patch.object(windows.sys,'_MEIPASS','fixture-runtime',create=True),patch.object(windows.ctypes,'windll',dll,create=True),patch.object(windows.subprocess,'CREATE_NO_WINDOW',0,create=True),patch.object(windows.subprocess,'Popen'):
            windows.launch('fixture.exe','a'*64)
        self.assertEqual([None,'fixture-runtime'],[call.args[0] for call in dll.kernel32.SetDllDirectoryW.call_args_list])

    def test_windows_installer_waits_for_parent_and_quotes_paths(self):
        command=installer_command("folder with ' quote/Setup.exe",123)
        self.assertIn("WaitForExit()",command)
        self.assertIn("-Id 123",command)
        self.assertIn("'' quote",command)


if __name__=="__main__":unittest.main()
