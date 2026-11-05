"""Prepare a D1 import from a validated complete catalog. No cloud calls."""

from contextlib import closing
import argparse
import json
from pathlib import Path
import sqlite3


def literal(value):
    return str(value) if isinstance(value,int) else "'"+value.replace("'","''")+"'"


def export(source,output,allow_fixture=False):
    with closing(sqlite3.connect(f'file:{Path(source).resolve()}?mode=ro',uri=True)) as db:
        metadata={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM catalog_meta')}
        if not metadata['complete'] or (metadata['fixture'] and not allow_fixture): raise ValueError('Complete official catalog required')
        rows=list(db.execute('SELECT * FROM schools ORDER BY id'))
        if len(rows)!=metadata['record_count']:raise ValueError('Catalog row count mismatch')
        # Disable COMMUNITY_ENABLED during import; enable only after local checks.
        sql=['-- Maintenance import: keep COMMUNITY_ENABLED=false until verification.', "UPDATE settings SET value=0 WHERE key='catalog_ready';", 'UPDATE schools SET active=0;']
        columns=['id','name','level','province','district','address','search_name','search_region','active']
        for row in rows:
            sql.append('INSERT INTO schools('+','.join(columns)+') VALUES('+','.join(literal(v) for v in row)+') ON CONFLICT(id) DO UPDATE SET '+','.join(c+'=excluded.'+c for c in columns[1:])+';')
        for key,value in metadata.items():
            sql.append('INSERT INTO catalog_meta VALUES('+literal(key)+','+literal(json.dumps(value,ensure_ascii=False))+') ON CONFLICT(key) DO UPDATE SET value=excluded.value;')
        conditions=["(SELECT count(*) FROM schools WHERE active=1 AND level="+literal(level)+")="+str(metadata['counts'][level]) for level in ['high','middle','elementary']]
        sql.append("UPDATE settings SET value=CASE WHEN "+' AND '.join(conditions)+" THEN 1 ELSE 0 END WHERE key='catalog_ready';")
        # Previous public snapshots must not silently outlive a catalog change.
        sql.append("UPDATE settings SET value=value+1 WHERE key='snapshot_sequence';")
        Path(output).write_text('\n'.join(sql)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--allow-fixture',action='store_true')
    a=p.parse_args();export(a.source,a.output,a.allow_fixture)
