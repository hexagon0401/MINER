import unittest
from unittest.mock import patch
from schoolnet.network_scope import check
from schoolnet.config import DNS_V4,DNS_V6


class ScopeTests(unittest.TestCase):
    snapshot={'schema':1,'system':'Darwin','interface':'en0','service':'Wi-Fi','manual':[],'servers':['1.1.1.1']}
    def test_interface_switch_never_applies_or_restores_another_adapter(self):
        with patch('schoolnet.network_dns.command',return_value='interface: en9') as command,patch('schoolnet.network_dns.Backend.apply') as apply,patch('schoolnet.network_dns.Backend.restore') as restore:
            self.assertEqual(check(self.snapshot)['reason_code'],'DEFAULT_INTERFACE_CHANGED')
            self.assertEqual(command.call_count,1);apply.assert_not_called();restore.assert_not_called()
    def test_external_dns_change_is_reported_and_not_overwritten(self):
        with patch('schoolnet.network_dns.command',side_effect=['interface: en0','8.8.8.8']):self.assertEqual(check(self.snapshot)['reason_code'],'DNS_LEASE_CHANGED')
        with patch('schoolnet.network_dns.command',side_effect=['interface: en0',DNS_V4+'\n'+DNS_V6+'\n']):self.assertTrue(check(self.snapshot)['healthy'])
    def test_unavailable_check_is_unknown_not_success(self):
        with patch('schoolnet.network_dns.command',side_effect=OSError):self.assertIsNone(check(self.snapshot)['healthy'])
