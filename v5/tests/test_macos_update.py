import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from schoolnet import macos_update as update

class AppUpdateTests(unittest.TestCase):
    def fixture(self,root):
        app=root/'Applications/MINER.app';app.mkdir(parents=True)
        incoming=root/'incoming';incoming.mkdir()
        for bundle,version in [(app,'1.2.0'),(incoming,'1.2.1')]:
            (bundle/'Contents').mkdir()
            (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':update.IDENTIFIER,'CFBundleShortVersionString':version}))
        (app/'old-resource').write_text('obsolete')
        cache=root/'cache';cache.mkdir()
        token='a'*32;worker=cache/('.worker-'+token);worker.mkdir()
        installer=cache/'MINER-ALPHA-v1.2.1-macOS-Intel.dmg';installer.write_bytes(b'verified fixture')
        ticket=worker/'ticket.json';ticket.write_text(json.dumps({'installer':str(installer),'sha256':hashlib.sha256(installer.read_bytes()).hexdigest(),'target':'1.2.1','parent':123,'token':token}))
        return app,incoming,cache,ticket

    def test_verified_replacement_removes_old_resources_only_after_new_launch(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            app,incoming,cache,ticket=self.fixture(Path(d))
            def execute(*args):
                args=list(map(str,args))
                if args[0].endswith('hdiutil'):
                    shutil.copytree(incoming,Path(args[-2])/'MINER.app')
                elif args[0].endswith('ditto'):shutil.copytree(args[1],args[2])
                elif args[0].endswith('open'):
                    self.assertTrue(list(app.parent.glob('.MINER-update-*/previous.app/old-resource')))
                    update.finish()
            with patch.object(update,'APP',app),patch.object(update,'CACHE',cache),patch.object(update,'DATA',cache.parent),patch.object(update,'execute',side_effect=execute),patch.object(update.os,'kill',side_effect=ProcessLookupError),patch.object(update.subprocess,'run'):
                result=update.apply(ticket)
            self.assertTrue(result['installed']);self.assertFalse((app/'old-resource').exists())
            self.assertFalse(list(app.parent.glob('.MINER-update-*')));self.assertFalse(ticket.parent.exists())

    def test_launch_failure_restores_previous_app_and_retains_installer(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            app,incoming,cache,ticket=self.fixture(Path(d))
            def execute(*args):
                args=list(map(str,args))
                if args[0].endswith('hdiutil'):shutil.copytree(incoming,Path(args[-2])/'MINER.app')
                elif args[0].endswith('ditto'):shutil.copytree(args[1],args[2])
                elif args[0].endswith('open'):raise subprocess.CalledProcessError(1,args)
            with patch.object(update,'APP',app),patch.object(update,'CACHE',cache),patch.object(update,'DATA',cache.parent),patch.object(update,'execute',side_effect=execute),patch.object(update.os,'kill',side_effect=ProcessLookupError),patch.object(update.subprocess,'run'),self.assertRaises(subprocess.CalledProcessError):update.apply(ticket)
            self.assertTrue((app/'old-resource').exists());self.assertTrue(list(cache.glob('*.dmg')))
            self.assertFalse(list(app.parent.glob('.MINER-update-*')))
