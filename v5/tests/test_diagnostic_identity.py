import json
from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch
from diagnostics.app_identity import bundle_metadata,running_identity,startup_events,APP_ID


def bundle(root,version='2.0.0'):
    content=root/'Contents';content.mkdir(parents=True)
    (content/'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':APP_ID,'CFBundleShortVersionString':version,
        'CFBundleVersion':'5020002','SchoolNetReleaseVersion':'5.0.0-strata.2.0.0-preview.2','password':'SECRET','path':'/Users/PRIVATE'}))
    executable=content/'MacOS/MINER';executable.parent.mkdir();executable.touch();return executable


class IdentityTests(unittest.TestCase):
    def test_translocated_running_copy_is_distinguished_from_old_system_install_without_exporting_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);installed=root/'Applications/MINER.app';bundle(installed,'1.2.3')
            executable=bundle(root/'AppTranslocation/PRIVATE/d/MINER.app')
            with patch('diagnostics.app_identity.process_path',return_value=executable):value=running_identity(123,'MINER',installed)
            self.assertEqual(value['version'],'2.0.0');self.assertEqual(value['location_kind'],'translocated')
            self.assertFalse(value['matches_system_install']);self.assertFalse(value['loaded_image_version_verified'])
            for token in ('SECRET','PRIVATE',str(root)):self.assertNotIn(token,json.dumps(value))
    def test_alias_of_installed_copy_matches_file_identity_and_other_copy_does_not(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);installed=root/'MINER.app';bundle(installed)
            alias=root/'alias.app'
            try:alias.symlink_to(installed,target_is_directory=True)
            except OSError:self.skipTest('Directory symlink privilege unavailable')
            with patch('diagnostics.app_identity.process_path',return_value=alias/'Contents/MacOS/MINER'):value=running_identity(123,'MINER',installed)
            self.assertTrue(value['matches_system_install']);self.assertEqual(value['location_kind'],'system_applications')
    def test_unresolved_process_does_not_invent_installed_version(self):
        with patch('diagnostics.app_identity.process_path',return_value=None):value=running_identity(123,'MINER')
        self.assertFalse(value['identity_available']);self.assertEqual(value['version'],'unavailable')
    def test_startup_export_is_bounded_and_allowlisted(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'startup.jsonl'
            row={'stage':'event_loop_ready','installation_kind':'translocated','at':1234,'pid':123,'path':'SECRET','password':'PRIVATE'}
            path.write_text('\n'.join([json.dumps(row)]*40+[json.dumps(dict(row,stage='SECRET'))]))
            result=startup_events(path);self.assertEqual(len(result),24)
            self.assertEqual(set(result[0]),{'stage','at','installation_kind'})
            self.assertNotIn('SECRET',json.dumps(result));self.assertNotIn('PRIVATE',json.dumps(result))
    def test_malformed_or_unrecognized_bundle_does_not_export_untrusted_version_text(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bundle(root,'2.0.0 SECRET')
            self.assertEqual(bundle_metadata(root)['version'],'unavailable')
