import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('homebrew_generate',ROOT/'packaging/homebrew/generate.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
RECEIPT=json.loads((ROOT/'packaging/homebrew/beta1.verification.json').read_text())


class HomebrewTests(unittest.TestCase):
    def test_actual_published_beta1_is_pinned_and_does_not_bypass_security(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'miner-beta.rb'
            module.generate(ROOT/'packaging/homebrew/beta1.verification.json',out)
            text=out.read_text()
            self.assertIn(RECEIPT['sha256'],text);self.assertIn('version "5.0.0-beta.1"',text)
            self.assertIn('app "MINER.app"',text);self.assertIn('uninstall_preflight',text)
            for forbidden in ['no_check','no-quarantine','spctl --master-disable','xattr -']:
                self.assertNotIn(forbidden,text)
    def test_no_unverified_or_fixture_beta2_cask(self):
        cases=[dict(RECEIPT,architecture='x86_64'),dict(RECEIPT,source_sha=''),dict(RECEIPT,native_ui_smoke={'ok':False}),dict(RECEIPT,version='5.0.0-beta.2',school_catalog={'complete':False,'fixture':False}),dict(RECEIPT,version='5.0.0-beta.2',school_catalog={'complete':True,'fixture':True})]
        with tempfile.TemporaryDirectory() as d:
            for receipt in cases:
                source=Path(d)/'receipt.json';source.write_text(json.dumps(receipt))
                with self.assertRaises(ValueError):module.generate(source,Path(d)/'out.rb')
