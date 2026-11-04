import unittest
from macos.retry_release import decide, TAG, SOURCE_SHA


class ReleaseRetryTests(unittest.TestCase):
    def test_never_cancel_or_duplicate_assigned_or_queued_work(self):
        for status in ['queued', 'in_progress', 'waiting', 'requested']:
            run = {'display_title': f'MINER native {TAG} (macos-26)', 'status': status}
            self.assertEqual(decide({}, None, [run])['state'], 'waiting_active')
    def test_abandoned_runner_rotates_but_deterministic_failure_stops(self):
        run = {'display_title': f'MINER native {TAG} (macos-26)', 'status': 'completed', 'conclusion': 'cancelled', 'html_url':'run'}
        self.assertEqual(decide({}, None, [run])['runner'], 'macos-15')
        run['conclusion'] = 'failure'
        self.assertEqual(decide({}, None, [run])['state'], 'needs_fix')
    def test_only_verified_correct_source_dmg_stops_retries(self):
        receipt={'version':TAG[1:],'source_sha':SOURCE_SHA,'sha256':'a'*64,'dmg_to_disk_signature_verified':True,'native_ui_smoke':{'ok':True}}
        release={'assets':[{'name':f'MINER-{TAG}-macOS-AppleSilicon.dmg','digest':'sha256:'+'a'*64}]}
        self.assertEqual(decide(release, receipt, [])['state'], 'complete')
        for key in ['source_sha', 'version', 'sha256']:
            bad=dict(receipt); bad[key]='invalid'
            self.assertTrue(decide(release,bad,[])['dispatch'])

class ReleasePublicationTests(unittest.TestCase):
    def test_incomplete_or_fixture_beta2_cannot_be_published(self):
        from macos.publish_native import validate_receipt
        receipt={'version':'5.0.0-beta.2','sha256':'a'*64,'architecture':'arm64','dmg_to_disk_signature_verified':True,'finder_background_layout_verified':True,'native_ui_smoke':{'ok':True}}
        for catalog in [{},{'complete':False,'fixture':False},{'complete':True,'fixture':True}]:
            with self.assertRaises(ValueError):validate_receipt(dict(receipt,school_catalog=catalog),'v5.0.0-beta.2','a'*64)
        validate_receipt(dict(receipt,school_catalog={'complete':True,'fixture':False}),'v5.0.0-beta.2','a'*64)
        with self.assertRaises(ValueError):validate_receipt(dict(receipt,school_catalog={'complete':True,'fixture':False},development_only=True),'v5.0.0-beta.2','a'*64)
