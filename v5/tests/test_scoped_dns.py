import copy
import os
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from schoolnet import scoped_dns as s
from schoolnet.network_dns import Backend,Lease

class ScopedDNSTests(unittest.TestCase):
    def snapshot(self,root):return {'schema':1,'system':'Darwin','interface':'en0','service':'Wi-Fi','manual':[],'servers':['192.0.2.53'],**s.plan(root)}
    def test_domain_files_are_owned_and_only_original_interface_dns_is_changed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'resolver';snapshot=self.snapshot(root);backend=Backend('Darwin',root)
            with patch.object(backend,'flush'),patch.object(backend,'current',side_effect=[['172.30.255.2','fdfe:dcba:9876::2'],[],[],[]]),patch('schoolnet.network_dns.command') as command:
                backend.apply(snapshot);self.assertTrue(s.active(snapshot,root))
                self.assertIn(b'nameserver 172.30.255.2', (root/'riotgames.com').read_bytes())
                backend.restore(snapshot);backend.restore(snapshot)
                self.assertFalse(list(root.iterdir()))
                self.assertEqual([c.args[0] for c in command.call_args_list],[['/usr/sbin/networksetup','-setdnsservers','Wi-Fi','172.30.255.2','fdfe:dcba:9876::2'],['/usr/sbin/networksetup','-setdnsservers','Wi-Fi','Empty']])
    def test_existing_domain_configuration_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'riotgames.com';path.write_text('administrator config')
            with self.assertRaises(ValueError):s.plan(root)
            self.assertEqual(path.read_text(),'administrator config')

    @unittest.skipUnless(os.name=='posix','macOS resolver permission semantics')
    def test_launchd_private_umask_does_not_hide_dns_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'resolver';snapshot=self.snapshot(root);previous=os.umask(0o077)
            try:s.install(snapshot,root)
            finally:os.umask(previous)
            self.assertEqual(root.stat().st_mode&0o777,0o755)
            self.assertTrue(all(path.stat().st_mode&0o777==0o644 for path in root.iterdir()))
            s.remove(snapshot,root)
    def test_partial_install_failure_recovers_only_owned_files_and_keeps_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'resolver';snapshot=self.snapshot(root);root.mkdir()
            conflict=root/snapshot['resolver_domains'][1];conflict.write_text('external config')
            with self.assertRaises(FileExistsError):s.install(snapshot,root)
            with self.assertRaises(ValueError):s.remove(snapshot,root)
            self.assertEqual(conflict.read_text(),'external config');self.assertEqual(len(list(root.iterdir())),1)
    def test_crash_recovery_journal_precedes_files_and_is_removed_after_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'resolver';snapshot=self.snapshot(root);backend=Backend('Darwin',root);journal=Path(d)/'journal.json'
            lease=Lease(d,backend,journal);lease.snapshot=snapshot
            with patch.object(backend,'flush'),patch('schoolnet.network_dns.command',return_value=''):
                original=backend.apply
                def apply(value):self.assertEqual(json.loads(journal.read_text()),snapshot);original(value)
                with patch.object(backend,'apply',side_effect=apply):lease.activate()
                Lease.recover(d,backend,journal)
            self.assertFalse(journal.exists());self.assertFalse(list(root.iterdir()))
    def test_modified_or_replaced_file_keeps_recovery_record(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'resolver';snapshot=self.snapshot(root);backend=Backend('Darwin',root);journal=Path(d)/'journal.json'
            lease=Lease(d,backend,journal);lease.snapshot=snapshot
            with patch.object(backend,'flush'),patch('schoolnet.network_dns.command',return_value=''):
                lease.activate();path=root/'riotgames.com';path.write_text('changed externally')
                with self.assertRaises(ValueError):lease.close()
            self.assertTrue(journal.exists());self.assertEqual(path.read_text(),'changed externally')
    def test_untrusted_journal_cannot_select_paths(self):
        with tempfile.TemporaryDirectory() as d:
            snapshot=self.snapshot(Path(d)/'resolver')
            for values in [{'resolver_domains':['../outside']},{'resolver_token':'bad'},{'dns_mode':'unknown'}]:
                invalid={**snapshot,**values}
                with self.subTest(values=values),self.assertRaises(ValueError):s.remove(invalid,Path(d))
