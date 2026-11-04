import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from community.catalog import write_catalog
from community.export_catalog_sql import export

BASE=Path(__file__).resolve().parents[1]/'community'
ROWS=json.loads((BASE/'fixtures/schools.json').read_text())


class CommunityImportTests(unittest.TestCase):
    def test_partial_csv_cannot_become_a_nationwide_catalog(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'Nationwide catalog appears partial'):
                write_catalog(ROWS,Path(d)/'bad.sqlite3','2026-11-04')
    def test_catalog_refresh_preserves_reports_and_retires_missing_ids(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'catalog.sqlite3';sql=Path(d)/'catalog.sql'
            write_catalog(ROWS,source,'2026-11-04',fixture=True)
            with self.assertRaises(ValueError):export(source,sql)
            export(source,sql,True)
            db=sqlite3.connect(':memory:');db.executescript('\n'.join(p.read_text() for p in sorted((BASE/'server/migrations').glob('*.sql'))));db.executescript(sql.read_text())
            db.execute("INSERT INTO reports(id,school_id,fingerprint,day,diagnosed_at,created_at,outcome,payload,payload_hash,public_key,signature,source) VALUES('r','TEST:H2','f','2026-11-04','2026-11-04T00:00:00Z',0,'success','{}','hash','key','sig','offline_review')")
            write_catalog([r for r in ROWS if r['SD_SCHUL_CODE']!='H2'],source,'2026-11-04',fixture=True)
            export(source,sql,True);db.executescript(sql.read_text())
            self.assertEqual(db.execute("SELECT active FROM schools WHERE id='TEST:H2'").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM reports').fetchone()[0],1)
            self.assertEqual(db.execute("SELECT value FROM settings WHERE key='catalog_ready'").fetchone()[0],1)
            interrupted=sql.read_text().split("UPDATE settings SET value=CASE")[0]
            db.executescript(interrupted)
            self.assertEqual(db.execute("SELECT value FROM settings WHERE key='catalog_ready'").fetchone()[0],0)
