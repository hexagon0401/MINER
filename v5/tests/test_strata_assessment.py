import json
import unittest
from diagnostics.strata_assessment import assess


class AssessmentTests(unittest.TestCase):
    def test_configured_components_do_not_hide_os_dns_selection_gap(self):
        row={'network':{'process_command':{'ok':True},'processes':{'engine':1},'default':{'interface':'physical'},'synthetic':{'interface':'tun','interface_class':'tunnel'},'dns':[{'kind':'miner_dns'}]},'warp':{'mode':'WarpProxy'},'socks':{'socks5_no_auth':True},'active_probes':{'auth.riotgames.com':{'dns':{'ok':True,'synthetic':False},'os_https':{'tls_verified':True,'http_status':403},'resolved_proxy_https':{'tls_verified':True,'http_status':404}}}}
        result=assess(row)
        self.assertEqual(result['hypotheses'][0]['status'],'NEEDS_INVESTIGATION')
        self.assertEqual(result['hypotheses'][0]['evidence'],'OS_QUERY_RETURNED_NON_SYNTHETIC_SELECTED_HOST')
        row['network']['processes']['engine']=0
        self.assertEqual(assess(row)['hypotheses'][0]['status'],'UNCONFIRMED')
    def test_post_game_failure_is_not_invented_endpoint_or_success(self):
        result=assess({'phase':'post_game','socks':{'socks5_no_auth':True},'statistics':{'result':'timeout_30s'}})
        self.assertFalse(result['statistics_success_verified'])
        self.assertEqual(result['actual_statistics_endpoint'],'NOT_IDENTIFIED')
        self.assertEqual(result['hypotheses'][4]['status'],'OBSERVED')
        self.assertEqual(result['hypotheses'][1]['status'],'UNCONFIRMED')
    def test_fixed_probe_path_difference_is_not_proof_of_statistics_cause(self):
        result=assess({'active_probes':{'auth.riotgames.com':{'proxy_https':{'tls_verified':True},'os_https':{'ok':False}}}})
        self.assertEqual(result['hypotheses'][0]['status'],'NEEDS_INVESTIGATION')
        self.assertNotIn('CONFIRMED',json.dumps(result['hypotheses'][0]))

    def test_full_warp_without_engine_is_not_a_failed_local_proxy_session(self):
        result=assess({'warp':{'mode':'Warp','connected':True},'network':{'process_command':{'ok':True},'processes':{'engine':0}},'socks':{'listening':False,'error':'ConnectionRefusedError'}})
        self.assertEqual(result['session']['state'],'SELECTIVE_NOT_OBSERVED')
        self.assertEqual(result['hypotheses'][2]['status'],'NOT_APPLICABLE')
    def test_proxy_mode_connection_refused_is_observed_failure_even_without_greeting_key(self):
        result=assess({'warp':{'mode':'WarpProxy'},'socks':{'listening':False,'error':'ConnectionRefusedError'}})
        self.assertEqual(result['hypotheses'][2]['status'],'OBSERVED')
    def test_historical_errors_and_failed_process_listing_do_not_prove_current_engine_failure(self):
        result=assess({'phase':'post_game','warp':{'mode':'Warp'},'network':{'process_command':{'ok':False},'processes':{'engine':0}},
            'app':{'locations':[{'files':{'engine.log':{'error_window':{'scope':'baseline_tail','patterns':[{'cause':'timeout'}]}}}}]}})
        self.assertEqual(result['session']['engine_observation'],'UNKNOWN');self.assertEqual(result['hypotheses'][3]['status'],'UNCONFIRMED')
    def test_proxy_alone_never_proves_selective_routing_or_statistics(self):
        result=assess({'warp':{'mode':'WarpProxy'},'socks':{'socks5_no_auth':True},'network':{'process_command':{'ok':True},'processes':{'engine':0}}})
        self.assertNotEqual(result['session']['state'],'SELECTIVE_COMPONENTS_OBSERVED');self.assertFalse(result['session']['game_or_statistics_success_verified'])
    def test_distinct_running_copy_and_versions_are_observations_not_assumed_from_fixed_path(self):
        result=assess({'app':{'version':'1.2.3'},'network':{'running_miner_apps':[{'recognized':True,'identity_available':True,'matches_system_install':False,'version':'2.0.0'}]}})
        self.assertTrue(result['session']['different_running_copy_observed']);self.assertTrue(result['session']['running_version_difference_observed'])
    def test_same_public_version_but_different_preview_build_is_detected(self):
        result=assess({'app':{'version':'2.0.0','installed_app':{'version':'2.0.0','build':'5020002'}},'network':{'running_miner_apps':[{'recognized':True,'identity_available':True,'version':'2.0.0','build':'5020001'}]}})
        self.assertTrue(result['session']['running_version_difference_observed'])
    def test_all_selective_components_are_observed_without_claiming_game_success(self):
        result=assess({'warp':{'mode':'WarpProxy'},'socks':{'socks5_no_auth':True},'network':{'process_command':{'ok':True},'processes':{'engine':1},'default':{'interface':'physical'},'synthetic':{'interface':'tunnel','interface_class':'tunnel'},'dns':[{'kind':'miner_dns'}]}})
        self.assertEqual(result['session']['state'],'SELECTIVE_COMPONENTS_OBSERVED');self.assertFalse(result['statistics_success_verified'])
    def test_windows_success_and_failed_parse_are_distinguished(self):
        row={'network':{'windows_command':{'ok':True},'processes':{'engine':1}}}
        self.assertEqual(assess(row)['session']['engine_observation'],'PRESENT')
        row['network']['parse_error']=True
        self.assertEqual(assess(row)['session']['engine_observation'],'UNKNOWN')
