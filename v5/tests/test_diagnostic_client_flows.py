import json
import unittest
from unittest.mock import patch
from diagnostics import client_flows as c


class ClientFlowTests(unittest.TestCase):
    def test_lsof_groups_live_chat_and_https_without_exporting_addresses_or_pid(self):
        text='p123\nf15\ntIPv4\nn172.16.123.45:50200->198.18.77.8:5223\nTST=ESTABLISHED\nf16\nn172.16.123.45:50201->87.65.43.21:443\nTST=SYN_SENT\np999\nf1\nn127.0.0.1:99->1.2.3.4:5223\nTST=ESTABLISHED\n'
        result=c.summarize(c.parse_macos(text,{'123':'league_backend'}),query_ok=True)
        self.assertEqual(sum(f['count'] for f in result['flows']),2)
        self.assertIn({'role':'league_backend','port_class':'chat_tls_candidate','destination_class':'synthetic','tcp_state':'ESTABLISHED','count':1},result['flows'])
        for secret in ['123','999','87.65.43.21','198.18.77.8','172.16.123.45']:self.assertNotIn(secret,json.dumps(result))
        self.assertFalse(result['ready_check_delivery_verified']);self.assertFalse(result['chat_login_verified'])

    def test_ipv6_mapped_loopback_listen_and_unknown_owner(self):
        self.assertEqual(c.shape('::ffff:198.18.0.8',5223,'CloseWait','league_backend')[2:4],('synthetic','CLOSE_WAIT'))
        text='p10\nf4\nn[::1]:5000->[fdfe:dcba:9876:1000::7]:443\nTST=ESTABLISHED\nf5\nn*:5000\nTST=LISTEN\n'
        rows=c.parse_macos(text,{'10':'league_ui'})
        self.assertEqual(len(rows),1);self.assertEqual(rows[0][2],'synthetic')
        self.assertEqual(c.parse_macos(text,{}),[])

    def test_mac_selects_current_users_exact_client_processes_without_arguments(self):
        calls=[]
        def command(args,**kwargs):
            calls.append(args)
            if args[0]=='/bin/ps':return {'ok':True},'1 /Applications/LeagueClient\n2 /Applications/NotLeagueClient\n3 /Applications/League of Legends\n4 /Applications/RiotClientServices\n'
            return {'ok':True},'p1\nf1\nn127.0.0.1:1->127.0.0.1:40000\nTST=ESTABLISHED\n'
        with patch.object(c.os,'getuid',return_value=501,create=True):result=c.collect('Darwin',command)
        self.assertTrue(result['query_ok']);self.assertEqual(result['client_process_count'],2)
        self.assertEqual(calls[0],['/bin/ps','-ww','-U','501','-o','pid=,comm='])
        self.assertEqual(calls[1][calls[1].index('-p')+1],'1,4');self.assertNotIn('args=',str(calls))

    def test_socks_connect_reply_errors_are_preserved_as_categories(self):
        from diagnostics.log_events import classify
        result=classify('ERROR outbound/socks[warp]: SOCKS CONNECT failed (reply=2) secret=PRIVATE')
        self.assertEqual(result['patterns'][0]['cause'],'socks_server_failure')
        self.assertNotIn('PRIVATE',json.dumps(result))

    def test_symptoms_are_allowlisted_user_reports_not_delivery_proof(self):
        import tempfile
        from pathlib import Path
        from diagnostics import collect as d
        with patch('schoolnet.warp.resolve_cli',side_effect=ValueError),patch.object(d,'network_state',return_value={}),patch.object(d,'files_state',return_value={}),patch.object(d,'socket_check',return_value={}),patch.object(c,'collect',return_value=c.summarize([],query_ok=False)):
            recorder=d.Recorder()
            row=recorder.snapshot('error',client_event='ready_check_missing')
            self.assertEqual(row['client_event'],{'kind':'ready_check_missing','evidence':'USER_REPORT','delivery_verified_by_tool':False})
            with self.assertRaises(ValueError):recorder.snapshot('error',client_event='SECRET')

    def test_failed_socket_query_is_unknown_not_zero_connections(self):
        def command(args,**kwargs):return ({'ok':True},'10 /Applications/LeagueClient\n') if args[0]=='/bin/ps' else ({'ok':False},'private error')
        with patch.object(c.os,'getuid',return_value=501,create=True):result=c.collect('Darwin',command)
        self.assertFalse(result['query_ok']);self.assertEqual(result['flows'],[])

    def test_windows_metadata_is_aggregated_and_unknown_errors_are_not_exported(self):
        raw={'count':1,'rows':[{'name':'LeagueClient','address':'11.22.33.44','port':5223,'state':'Established','secret':'TOKEN'}]}
        result=c.collect('Windows',lambda *args,**kwargs:({'ok':True},json.dumps(raw)))
        self.assertTrue(result['query_ok']);self.assertEqual(result['flows'][0]['destination_class'],'real_address')
        for private in ['11.22.33.44','TOKEN','LeagueClient']:self.assertNotIn(private,json.dumps(result))
        self.assertFalse(c.collect('Windows',lambda *a,**k:({'ok':False},'TOKEN'))['query_ok'])

    def test_bound_and_invalid_data_do_not_invent_presence_success(self):
        self.assertIsNone(c.shape('bad-address',443,'Established','league_backend'))
        self.assertIsNone(c.shape('127.0.0.1',443,'Established','not_a_client'))
        self.assertIsNone(c.shape('127.0.0.1',True,'Established','league_backend'))
        self.assertEqual(c.shape('127.0.0.1',443,'SECRET','league_backend')[-1],'UNKNOWN')
        result=c.collect('Linux',lambda *a: self.fail('unsupported system must not query'))
        self.assertFalse(result['query_ok']);self.assertFalse(result['chat_login_verified'])
