import json
from pathlib import Path
import tempfile
import unittest
from diagnostics.log_events import classify,LogWindows

class LogEventTests(unittest.TestCase):
    def test_export_contains_only_allowlisted_shapes_not_original_lines(self):
        result=classify('ERROR outbound/socks[warp]: dial tcp 127.0.0.1:40000: connection refused auth.riotgames.com token=SECRET user=PRIVATE\nERROR dns: query failed: SERVFAIL for 198.18.3.2 [password=SECRET]\nERROR outbound/socks[warp]: read: unexpected EOF')
        self.assertEqual(result['classified_error_lines'],3)
        self.assertTrue(any(p['cause']=='connection_refused' and 'local_proxy_40000' in p['endpoint_class'] for p in result['patterns']))
        self.assertTrue(any(p['cause']=='remote_closed' for p in result['patterns']))
        for value in ('SECRET','PRIVATE','127.0.0.1','auth.riotgames.com','198.18.3.2'):self.assertNotIn(value,json.dumps(result))

    def test_old_errors_are_not_recounted_as_new(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'engine.log';path.write_text('ERROR connection refused\n')
            reader=LogWindows();first=reader.read(path);second=reader.read(path)
            self.assertEqual(first['scope'],'baseline_tail');self.assertEqual(first['classified_error_lines'],1)
            self.assertEqual(second['scope'],'since_previous_sample');self.assertEqual(second['classified_error_lines'],0)
            with path.open('a') as f:f.write('ERROR connection reset\n')
            third=reader.read(path);self.assertEqual(third['classified_error_lines'],1);self.assertEqual(third['patterns'][0]['cause'],'connection_reset')

    def test_truncation_and_same_length_replacement_are_not_negative_deltas(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'engine.log';path.write_text('ERROR connection refused\n');reader=LogWindows();reader.read(path)
            path.write_text('ERROR network is unreachable\n');result=reader.read(path)
            self.assertEqual(result['scope'],'replaced_or_truncated_tail');self.assertEqual(result['patterns'][0]['cause'],'network_unreachable')
            path.write_text('EOF\n');self.assertEqual(reader.read(path)['scope'],'rotated_or_truncated_tail')

    def test_keyword_without_error_cause_is_not_counted_as_connection_failure(self):
        result=classify('INFO SOCKS proxy ready\nINFO DNS restored')
        self.assertEqual(result['classified_error_lines'],0);self.assertEqual(result['patterns'],[])

if __name__=='__main__':unittest.main()
