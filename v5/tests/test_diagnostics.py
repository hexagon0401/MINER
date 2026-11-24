import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from diagnostics import collect as d

class DiagnosticsTests(unittest.TestCase):
    def test_dns_probe_normalizes_mapped_synthetic_and_reports_mixed_answers(self):
        import socket
        def row(ip):return (socket.AF_INET6,socket.SOCK_STREAM,6,'',(ip,443,0,0))
        with patch.object(d.socket,'getaddrinfo',return_value=[row('::ffff:198.18.0.28')]):result=d.probe('dns','auth.riotgames.com',40000)
        self.assertTrue(result['all_synthetic']);self.assertEqual(result['synthetic_ipv4_mapped_count'],1)
        with patch.object(d.socket,'getaddrinfo',return_value=[row('::ffff:198.18.0.28'),row('2606:4700::1111')]):result=d.probe('dns','auth.riotgames.com',40000)
        self.assertTrue(result['synthetic']);self.assertFalse(result['all_synthetic']);self.assertEqual(result['real_address_count'],1)
        self.assertNotIn('2606:4700::1111',json.dumps(result))
    def test_addresses_are_session_scoped_and_private_values_do_not_escape(self):
        a,b=d.Privacy(),d.Privacy()
        self.assertEqual(a.address('172.30.255.2')['kind'],'miner_dns')
        self.assertEqual(a.address('198.18.1.2')['kind'],'synthetic')
        self.assertEqual(a.address('fdfe:dcba:9876:1000::3')['kind'],'synthetic')
        self.assertEqual(a.address('192.168.77.1'),a.address('192.168.77.1'))
        self.assertNotEqual(a.address('192.168.77.1'),b.address('192.168.77.1'))
        self.assertNotIn('192.168',json.dumps(a.address('192.168.77.1')))

    def test_warp_parses_allowed_fields_without_exporting_accounts_or_raw_errors(self):
        def command(args):
            text={'--version':'warp-cli 2026.8.2100.0','status':'Status update: Connected','settings':'Mode: WarpProxy on port 40000\nTunnel protocol: MASQUE\nAccount: SECRET\nDevice: PRIVATE','mode':'warp proxy'}
            return {'ok':True},text[args[1]]
        with patch.object(d,'command',side_effect=command):result=d.warp_state('warp-cli')
        self.assertEqual(result['version'],'2026.8.2100.0');self.assertEqual(result['mode'],'WarpProxy');self.assertEqual(result['port'],40000)
        self.assertTrue(result['connected']);self.assertEqual(result['transport'],'MASQUE')
        self.assertNotIn('SECRET',json.dumps(result));self.assertNotIn('PRIVATE',json.dumps(result))

    def test_findings_do_not_label_proxy_mode_as_error_during_a_match(self):
        row={'system':'Darwin','phase':'in_game','warp':{'mode':'WarpProxy','connected':True},'network':{},'socks':{'socks5_no_auth':True}}
        self.assertEqual(d.findings(row),['actual_game_udp_and_anticheat_result_not_proven'])
        row['phase']='after_stop';row['network']={'dns':[{'kind':'miner_dns'}]}
        self.assertIn('proxy_mode_remains_after_stop',d.findings(row));self.assertIn('miner_dns_remains_after_stop',d.findings(row))

    def test_logs_export_categories_and_codes_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'engine.log').write_text('timeout for https://SECRET/?token=PASSWORD from 192.168.77.8 user PRIVATE\nVAN 1067\nconnection reset')
            (root/'profile.json').write_text(json.dumps({'platform':'macos','proxy_port':40000,'mtu':1500,'password':'PASSWORD','physical_interface':'PRIVATE'}))
            with patch.object(d,'app_paths',return_value=[root]):result=d.files_state('Windows')
            text=json.dumps(result)
            for value in ('SECRET','PASSWORD','192.168.77.8','PRIVATE'):self.assertNotIn(value,text)
            self.assertEqual(result['locations'][0]['files']['engine.log']['events']['reset'],1)
            self.assertEqual(result['locations'][0]['files']['engine.log']['van_codes'],['VAN 1067'])

    def test_probe_is_bounded_and_uses_no_shell(self):
        import subprocess
        with patch.object(d.subprocess,'run',side_effect=subprocess.TimeoutExpired('fixture',1)) as call:
            result,text=d.command(['fixture'],timeout=1)
        self.assertEqual(result['error'],'timeout');self.assertEqual(text,'');self.assertNotIn('shell',call.call_args.kwargs)

    def test_local_recording_does_not_activate_warp_or_send_active_probes(self):
        with tempfile.TemporaryDirectory() as td,patch('schoolnet.warp.resolve_cli',side_effect=ValueError),patch.object(d,'network_state',return_value={}),patch.object(d,'files_state',return_value={}),patch.object(d,'socket_check',return_value={'listening':False}),patch.object(d,'child_probe') as active,patch('schoolnet.warp.activate') as activate:
            recorder=d.Recorder();recorder.snapshot('before');recorder.snapshot('after_stop')
            path=recorder.save(Path(td)/'report.zip')
            with zipfile.ZipFile(path) as z:
                self.assertEqual(set(z.namelist()),{'report.json','SUMMARY.txt'});report=json.loads(z.read('report.json'))
            self.assertTrue(report['read_only']);self.assertFalse(report['uploaded']);self.assertEqual(len(report['samples']),2)
            active.assert_not_called();activate.assert_not_called()

    def test_probe_cannot_target_arbitrary_hosts(self):
        with self.assertRaises(ValueError):d.probe('https','user-input.invalid',40000)

if __name__=='__main__':unittest.main()
