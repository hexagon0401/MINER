import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from schoolnet.network_dns import Backend,Lease,DNS_V4,DNS_V6


class FakeBackend:
    def __init__(self):
        self.snapshot={'schema':1,'system':'Darwin','interface':'en0','service':'Wi-Fi','manual':[], 'servers':['192.0.2.53']}
        self.current=['192.0.2.53'];self.fail_apply=False;self.fail_restore=False
    def capture(self):return copy.deepcopy(self.snapshot)
    def validate(self,snapshot):Backend('Darwin').validate(snapshot)
    def apply(self,snapshot):
        self.current=[DNS_V4,DNS_V6]
        if self.fail_apply:raise ValueError('partial apply failed')
    def restore(self,snapshot):
        if self.fail_restore:raise ValueError('adapter unavailable')
        if set(self.current).issubset({DNS_V4,DNS_V6}):self.current=['192.0.2.53']


class DNSTransactionTests(unittest.TestCase):
    def test_journal_precedes_mutation_and_clean_stop_recovers(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'dns.json';backend=FakeBackend();lease=Lease(d,backend,path)
            self.assertEqual(['192.0.2.53'],lease.prepare())
            original=backend.apply
            def apply(snapshot):
                self.assertEqual(snapshot,json.loads(path.read_text()));original(snapshot)
            backend.apply=apply
            lease.activate();self.assertEqual([DNS_V4,DNS_V6],backend.current)
            lease.close();self.assertEqual(['192.0.2.53'],backend.current);self.assertFalse(path.exists())

    def test_failed_partial_install_rolls_back_and_failed_recovery_keeps_journal(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'dns.json';backend=FakeBackend();lease=Lease(d,backend,path)
            lease.prepare();backend.fail_apply=True
            with self.assertRaisesRegex(ValueError,'partial apply'):lease.activate()
            self.assertFalse(path.exists());self.assertEqual(['192.0.2.53'],backend.current)
            backend.fail_restore=True
            with self.assertRaisesRegex(ValueError,'adapter unavailable'):lease.activate()
            self.assertTrue(path.exists())
            backend.fail_restore=False;lease.close();self.assertFalse(path.exists())

    def test_crash_recovery_and_external_dns_edits_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'dns.json';backend=FakeBackend();lease=Lease(d,backend,path)
            lease.prepare();lease.activate()
            Lease.recover(d,backend,path);self.assertEqual(['192.0.2.53'],backend.current)
            lease.prepare();lease.activate();backend.current=['192.0.2.99']
            lease.close();self.assertEqual(['192.0.2.99'],backend.current)

    def test_macos_restores_automatic_dns_without_replacing_it_with_static_dns(self):
        backend=Backend('Darwin');snapshot=FakeBackend().snapshot
        with patch('schoolnet.network_dns.command',side_effect=[DNS_V4+'\n'+DNS_V6+'\n','','No DNS servers set\n']) as run,patch.object(backend,'flush'):
            backend.restore(snapshot)
        self.assertIn(['/usr/sbin/networksetup','-setdnsservers','Wi-Fi','Empty'],[c.args[0] for c in run.call_args_list])

    def test_windows_restores_each_family_and_original_dhcp_mode(self):
        snapshot={'schema':1,'system':'Windows','interface':'7','guid':'12345678-1234-1234-1234-123456789abc','servers':['192.0.2.53','2001:db8::53'],
            'families':[{'family':'IPv4','manual':False,'servers':['192.0.2.53']},{'family':'IPv6','manual':True,'servers':['2001:db8::53']}]}
        before=[{'AddressFamily':2,'ServerAddresses':[DNS_V4]},{'AddressFamily':23,'ServerAddresses':[DNS_V6]}]
        after=[{'AddressFamily':2,'ServerAddresses':['192.0.2.53']},{'AddressFamily':23,'ServerAddresses':['2001:db8::53']}]
        with patch('schoolnet.network_dns.powershell',side_effect=[json.dumps(before),'','',json.dumps(after)]) as run:
            Backend('Windows').restore(snapshot)
        script=run.call_args_list[1].args[0]
        self.assertIn('-ResetServerAddresses',script)
        self.assertIn("'2001:db8::53'",script)
        self.assertIn(snapshot['guid'],script)
        self.assertNotIn('-InterfaceAlias *',script)

    def test_corrupt_recovery_input_never_reaches_powershell(self):
        backend=Backend('Windows')
        with patch('schoolnet.network_dns.powershell') as run,self.assertRaises(ValueError):
            backend.restore({'schema':1,'system':'Windows','servers':['192.0.2.53'],'guid':"'; bad command"})
        run.assert_not_called()
