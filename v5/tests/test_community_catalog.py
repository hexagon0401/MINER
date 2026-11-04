import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import unicodedata
from unittest.mock import patch
from community.catalog import write_catalog, normalize_rows, fetch_neis
from community.diagnostics import diagnose

ROWS=json.loads((Path(__file__).resolve().parents[1]/'community/fixtures/schools.json').read_text())


class CommunityCatalogTests(unittest.TestCase):
    def test_unique_ids_not_names_and_complete_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'schools.sqlite3'
            meta=write_catalog(ROWS+[ROWS[0]],path,'2026-11-04',fixture=True)
            self.assertEqual(meta['counts'],{'high':2,'middle':1,'elementary':1})
            with sqlite3.connect(path) as db:self.assertEqual(db.execute('select count(*) from schools').fetchone()[0],4)
    def test_conflicts_fail_without_replacing_previous_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'schools.sqlite3'
            write_catalog(ROWS,path,'2026-11-04',fixture=True); previous=path.read_bytes()
            bad=dict(ROWS[0],SCHUL_NM='다른 이름')
            with self.assertRaises(ValueError):write_catalog(ROWS+[bad],path,'2026-11-04')
            self.assertEqual(path.read_bytes(),previous)
    def test_unicode_and_closed_schools(self):
        row=dict(ROWS[0],SCHUL_NM=unicodedata.normalize('NFD',ROWS[0]['SCHUL_NM']),운영상태명='폐교')
        school=normalize_rows([row])[0]
        self.assertEqual(school['name'],ROWS[0]['SCHUL_NM']);self.assertEqual(school['active'],0)
    def test_empty_catalog_never_claims_nationwide_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'schools.sqlite3'
            with self.assertRaises(ValueError):write_catalog([],path,'2026-11-04')
            self.assertFalse(write_catalog([],path,'2026-11-04',complete=False)['complete'])
    @patch('community.diagnostics.status',return_value={'running':False})
    @patch('community.diagnostics.doctor')
    def test_diagnostics_do_not_start_or_touch_stopped_engine(self,doctor,status):
        result=diagnose('not-used','not-used')
        self.assertFalse(result['passed']);doctor.assert_not_called()
    @patch('community.diagnostics.status',side_effect=[{'running':True},{'running':False}])
    @patch('community.diagnostics.doctor',return_value={'checks':dict.fromkeys(['native_platform','engine_schema','warp_local_proxy_mode','socks5_greeting','warp_trace'],True),'engine':'/private/path','proxy':{'secret':'not-for-report'}})
    def test_stopping_engine_invalidates_pass_and_paths_are_not_exported(self,doctor,status):
        result=diagnose('unused','unused')
        self.assertFalse(result['passed']);self.assertNotIn('private',json.dumps(result));self.assertNotIn('secret',json.dumps(result))
