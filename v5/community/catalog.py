"""Import the complete official NEIS catalog into a read-only app database."""
import argparse
import csv
from datetime import date
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unicodedata
import urllib.parse
import urllib.request

SOURCE = 'https://open.neis.go.kr/hub/schoolInfo'
LEVELS = {'초등학교':'elementary','중학교':'middle','고등학교':'high'}
ALIASES = {
 'office':['ATPT_OFCDC_SC_CODE','시도교육청코드'],
 'code':['SD_SCHUL_CODE','행정표준코드','학교코드'],
 'name':['SCHUL_NM','학교명'],
 'level':['SCHUL_KND_SC_NM','학교종류명','학교급명'],
 'province':['LCTN_SC_NM','시도명'],
 'office_name':['ATPT_OFCDC_SC_NM','시도교육청명'],
 'address':['ORG_RDNMA','도로명주소','주소'],
 'state':['운영상태명','학교상태명'],
}
SCHEMA = '''
CREATE TABLE catalog_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE schools(id TEXT PRIMARY KEY,name TEXT NOT NULL,level TEXT NOT NULL CHECK(level IN ('high','middle','elementary')),province TEXT NOT NULL,district TEXT NOT NULL,address TEXT NOT NULL,search_name TEXT NOT NULL,search_region TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE INDEX schools_region ON schools(level,province,district);
PRAGMA user_version=1;
'''


def normalized(value):
    return unicodedata.normalize('NFC', str(value or '').strip())


def search_key(value):
    return ''.join(normalized(value).casefold().split())


def value(row, key):
    return next((normalized(row[n]) for n in ALIASES[key] if row.get(n)), '')


def normalize_rows(rows):
    schools = {}
    for row in rows:
        kind = value(row,'level')
        if kind not in LEVELS: continue
        office, code, name = (value(row,k) for k in ['office','code','name'])
        if not office or not code or not name: raise ValueError('Missing official school identifier/name')
        if any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-' for c in office+code): raise ValueError('Invalid official identifier')
        address = value(row,'address')
        province = value(row,'province') or value(row,'office_name').removesuffix('교육청')
        if not province: raise ValueError('Missing official province')
        parts = address.split()
        district = ' '.join(parts[1:3] if len(parts)>2 and parts[2].endswith('구') else parts[1:2])
        state = value(row,'state')
        item = {'id':office+':'+code,'name':name,'level':LEVELS[kind], 'province':province,'district':district,'address':address,
                'search_name':search_key(name),'search_region':search_key(province+' '+district+' '+address),
                'active':int(state not in ['폐교','폐지','휴교','폐교학교'])}
        previous = schools.get(item['id'])
        if previous and previous != item: raise ValueError('Conflicting duplicate school ID: '+item['id'])
        schools[item['id']] = item
    return sorted(schools.values(),key=lambda s:s['id'])


def write_catalog(rows, output, as_of, source=SOURCE, complete=True, fixture=False):
    date.fromisoformat(as_of)
    schools = normalize_rows(rows)
    if complete and not schools: raise ValueError('Empty complete school catalog')
    canonical = json.dumps(schools,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    meta = {'schema_version':1,'catalog_version':hashlib.sha256(canonical).hexdigest(),'as_of':as_of,'source_url':source,
            'complete':bool(complete),'fixture':bool(fixture),'record_count':len(schools),
            'counts':{k:sum(s['level']==k and s['active']==1 for s in schools) for k in ['high','middle','elementary']},
            'coverage':'Current official schoolInfo records; explicit closed/suspended records excluded',
            'attribution':'교육부·시도교육청 / 나이스 교육정보 개방 포털 학교기본정보. 출처와 기준일을 함께 표시합니다.'}
    output = Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent,suffix='.sqlite3',delete=False) as f: temporary=Path(f.name)
    try:
        with sqlite3.connect(temporary) as db:
            db.executescript(SCHEMA)
            db.executemany('INSERT INTO catalog_meta VALUES(?,?)',[(k,json.dumps(v,ensure_ascii=False)) for k,v in meta.items()])
            db.executemany('INSERT INTO schools VALUES(:id,:name,:level,:province,:district,:address,:search_name,:search_region,:active)',schools)
        os.replace(temporary,output)
    finally: temporary.unlink(missing_ok=True)
    output.with_suffix('.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    return meta


def fetch_neis(key=None):
    rows=[]; seen=set(); expected=None
    for page in range(1,101):
        params={'Type':'json','pIndex':page,'pSize':1000}
        if key: params['KEY']=key
        request=urllib.request.Request(SOURCE+'?'+urllib.parse.urlencode(params),headers={'User-Agent':'MINER-school-catalog/1'})
        try:
            with urllib.request.urlopen(request,timeout=30) as response: payload=json.load(response)
        except Exception as exc:
            # An API key must never appear in diagnostics or artifacts.
            raise ValueError('Official NEIS request failed: '+type(exc).__name__) from None
        if 'schoolInfo' not in payload: raise ValueError('NEIS schoolInfo unavailable; provide an official CSV or NEIS_API_KEY')
        head=payload['schoolInfo'][0]['head']; total=next(h['list_total_count'] for h in head if 'list_total_count' in h)
        if expected is None: expected=total
        if total!=expected: raise ValueError('Official catalog changed during pagination; retry import')
        batch=payload['schoolInfo'][1]['row']
        ids={(r['ATPT_OFCDC_SC_CODE'],r['SD_SCHUL_CODE']) for r in batch}
        if ids & seen or len(ids)!=len(batch): raise ValueError('NEIS pagination repeated rows; sample-only API response is not a complete catalog')
        remaining=expected-len(rows)
        if len(batch)!=min(1000,remaining): raise ValueError('NEIS returned a partial/sample page; use NEIS_API_KEY or official CSV')
        seen.update(ids);rows.extend(batch)
        if len(rows)==expected: return rows
    raise ValueError('Official catalog exceeded pagination bound')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv',type=Path);p.add_argument('--fetch-neis',action='store_true');p.add_argument('--empty',action='store_true')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--as-of',default=date.today().isoformat())
    args=p.parse_args()
    if sum(bool(v) for v in [args.csv,args.fetch_neis,args.empty])!=1: p.error('Choose exactly one input')
    if args.empty: rows=[]
    elif args.fetch_neis: rows=fetch_neis(os.environ.get('NEIS_API_KEY'))
    else:
        raw=args.csv.read_bytes()
        try: text=raw.decode('utf-8-sig')
        except UnicodeDecodeError: text=raw.decode('cp949')
        rows=list(csv.DictReader(io.StringIO(text)))
    meta=write_catalog(rows,args.output,args.as_of,complete=not args.empty)
    print(json.dumps(meta,ensure_ascii=False))


if __name__=='__main__': main()
