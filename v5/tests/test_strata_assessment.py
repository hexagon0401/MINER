import json
import unittest
from diagnostics.strata_assessment import assess


class AssessmentTests(unittest.TestCase):
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
