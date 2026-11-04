import {env as cloudEnv,applyD1Migrations} from 'cloudflare:test';
import {beforeAll,beforeEach,describe,it,expect} from 'vitest';
import worker,{type Env} from '../src/index';
import {CHECKS,canonical,encode,digest,verifyReport,type ReportBody,type SignedReport} from '../src/protocol';
import {review} from '../src/moderation';

const env=cloudEnv as unknown as Env & {TEST_MIGRATIONS:any};
const version='a'.repeat(64);
let signer:CryptoKeyPair;
let publicKey:string;
let snapshotKey:CryptoKeyPair;
let open:Env;
async function call(path:string,body?:unknown,custom:Env=open) {
 return worker.fetch(new Request('https://community.example'+path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),custom);
}
async function make(schoolId='TEST:H1',key=signer,pub=publicKey,changes:Partial<ReportBody>={}) {
 const challenge=await (await call('/v1/challenges',{publicKey:pub})).json() as {id:string;nonce:string};
 const payload:ReportBody={schemaVersion:1,id:crypto.randomUUID(),schoolId,catalogVersion:version,diagnosedAt:new Date().toISOString().replace(/\.\d{3}Z$/,'Z'),appVersion:'5.0.0-beta.2',osMajor:16,
  checks:Object.fromEntries(CHECKS.map(k=>[k,true])) as ReportBody['checks'],schoolNetworkConfirmed:true,clientConfirmed:true,game:'not_tested',video:'not_tested',clientReturn:'not_tested',outcome:'success',failureCode:null,
  challenge:{id:challenge.id,nonce:challenge.nonce},...changes};
 return resign(payload,key,pub);
}
async function resign(payload:ReportBody,key=signer,pub=publicKey):Promise<SignedReport> {
 return {payload,publicKey:pub,signature:encode(new Uint8Array(await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},key.privateKey,new TextEncoder().encode(canonical(payload)))))};
}
async function shared() {
 const response=await call('/v1/snapshot');expect(response.status).toBe(200);
 const signed=await response.json() as {payload:string;signature:string};
 const decode=(v:string)=>Uint8Array.from(atob(v.replaceAll('-','+').replaceAll('_','/')),c=>c.charCodeAt(0));
 expect(await crypto.subtle.verify('Ed25519',snapshotKey.publicKey,decode(signed.signature),decode(signed.payload))).toBe(true);
 return JSON.parse(new TextDecoder().decode(decode(signed.payload)));
}
beforeAll(async()=>{
 await applyD1Migrations(env.DB,env.TEST_MIGRATIONS);
 signer=await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},true,['sign','verify']) as CryptoKeyPair;
 publicKey=encode(new Uint8Array(await crypto.subtle.exportKey('raw',signer.publicKey)));
 snapshotKey=await crypto.subtle.generateKey({name:'Ed25519'},true,['sign','verify']) as CryptoKeyPair;
 open={...env,COMMUNITY_ENABLED:'true',ALLOW_FIXTURE_CATALOG:'true',SNAPSHOT_SIGNING_KEY:encode(new Uint8Array(await crypto.subtle.exportKey('pkcs8',snapshotKey.privateKey)))};
});
beforeEach(async()=>{
 await env.DB.batch(['DELETE FROM review_audit','DELETE FROM reports','DELETE FROM challenges','DELETE FROM schools','DELETE FROM catalog_meta',"UPDATE settings SET value=0 WHERE key='snapshot_sequence'"].map(s=>env.DB.prepare(s)));
 for(const [id,level] of [['TEST:H1','high'],['TEST:H2','high'],['TEST:M1','middle'],['TEST:E1','elementary']])
  await env.DB.prepare('INSERT INTO schools VALUES(?,?,?,?,?,?,?,?,1)').bind(id,'테스트학교',level,'테스트시','테스트구','예시로','테스트학교','테스트시').run();
 for(const [k,v] of Object.entries({complete:true,fixture:true,catalog_version:version,counts:{high:2,middle:1,elementary:1}}))
  await env.DB.prepare('INSERT INTO catalog_meta VALUES(?,?)').bind(k,JSON.stringify(v)).run();
});
describe('closed by default and privacy',()=>{
 it('does not open APIs or an admin endpoint by default',async()=>{
  expect((await call('/v1/snapshot',undefined,env)).status).toBe(503);
  expect((await call('/admin/reports',{})).status).toBe(404);
 });
 it('requires a production catalog and signer',async()=>{
  expect((await call('/v1/snapshot',undefined,{...open,ALLOW_FIXTURE_CATALOG:undefined})).status).toBe(503);
  expect((await call('/v1/snapshot',undefined,{...open,SNAPSHOT_SIGNING_KEY:undefined})).status).toBe(503);
 });
 it('rejects raw identifiers and oversized bodies',async()=>{
  const report=await make();(report.payload as any).ssid='do-not-store';
  expect((await call('/v1/reports',report)).status).toBe(400);
  expect((await call('/v1/reports',{text:'x'.repeat(17000)})).status).toBe(413);
  expect(await env.DB.prepare('SELECT count(*) AS n FROM reports').first('n')).toBe(0);
 });
});
describe('signed reports',()=>{
 it('pending submission is not public approval; identical retry is idempotent',async()=>{
  const report=await make();expect((await call('/v1/reports',report)).status).toBe(201);
  expect((await call('/v1/reports',report)).status).toBe(200);
  expect((await shared()).counts.high).toBe(0);
  const changed=await resign({...report.payload,video:'pass'});
  expect((await call('/v1/reports',changed)).status).toBe(409);
 });
 it('rejects forged signatures and success without actual confirmations',async()=>{
  const report=await make();report.payload.schoolId='TEST:H2';
  expect((await call('/v1/reports',report)).status).toBe(400);
  const wrong=await make('TEST:H1',signer,publicKey,{clientConfirmed:false});
  expect((await call('/v1/reports',wrong)).status).toBe(400);
 });
 it('rejects offline, expired, replayed and stale proofs',async()=>{
  const offline=await make('TEST:H1',signer,publicKey,{challenge:null});expect((await call('/v1/reports',offline)).status).toBe(400);
  const stale=await make('TEST:H1',signer,publicKey,{diagnosedAt:'2020-01-01T00:00:00Z'});expect((await call('/v1/reports',stale)).status).toBe(400);
  const expired=await make();await env.DB.prepare('UPDATE challenges SET expires_at=0 WHERE id=?').bind(expired.payload.challenge!.id).run();
  expect((await call('/v1/reports',expired)).status).toBe(409);
  const good=await make();expect((await call('/v1/reports',good)).status).toBe(201);
  const replay=await resign({...good.payload,id:crypto.randomUUID()});expect((await call('/v1/reports',replay)).status).toBe(409);
 });
 it('rejects unknown school and catalog versions',async()=>{
  expect((await call('/v1/reports',await make('TEST:unknown'))).status).toBe(400);
  expect((await call('/v1/reports',await make('TEST:H1',signer,publicKey,{catalogVersion:'b'.repeat(64)}))).status).toBe(409);
 });
 it('limits one school per key/day and three reports per key/day',async()=>{
  expect((await call('/v1/reports',await make())).status).toBe(201);
  expect((await call('/v1/reports',await make())).status).toBe(429);
  expect((await call('/v1/reports',await make('TEST:H2'))).status).toBe(201);
  expect((await call('/v1/reports',await make('TEST:M1'))).status).toBe(201);
  expect((await call('/v1/reports',await make('TEST:E1'))).status).toBe(429);
 });
});
describe('reviewed cumulative coverage',()=>{
 it('approves distinct schools, not report counts; withdrawal is audited',async()=>{
  const first=await make();await call('/v1/reports',first);
  await expect(review(env.DB,first.payload.id,'approve','','operator')).rejects.toThrow();
  await review(env.DB,first.payload.id,'approve','사용 결과 검토','operator');
  const secondKey=await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},true,['sign','verify']) as CryptoKeyPair;
  const secondPublic=encode(new Uint8Array(await crypto.subtle.exportKey('raw',secondKey.publicKey)));
  const second=await make('TEST:H1',secondKey,secondPublic);await call('/v1/reports',second);
  await review(env.DB,second.payload.id,'approve','별도 제보 검토','operator');
  expect((await shared()).counts.high).toBe(1);
  await review(env.DB,first.payload.id,'revoke','잘못된 학교 수정','operator');
  expect((await shared()).counts.high).toBe(1);
  await review(env.DB,second.payload.id,'revoke','승인 근거 재확인','operator');
  expect((await shared()).counts.high).toBe(0);
  expect(await env.DB.prepare('SELECT count(*) AS n FROM review_audit').first('n')).toBe(4);
 });
 it('rejection does not count; old approved successes remain cumulative',async()=>{
  const old=await make('TEST:H1',signer,publicKey,{diagnosedAt:'2020-01-01T00:00:00Z',challenge:null});
  const checked=await verifyReport(old);
  await env.DB.prepare(`INSERT INTO reports(id,school_id,fingerprint,day,diagnosed_at,created_at,outcome,payload,payload_hash,public_key,signature,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,'offline_review')`)
   .bind(old.payload.id,old.payload.schoolId,checked.fingerprint,'2020-01-01',old.payload.diagnosedAt,0,'success',canonical(old.payload),checked.payloadHash,old.publicKey,old.signature).run();
  await review(env.DB,old.payload.id,'approve','과거 제보 파일 수동 검토','operator');
  const pending=await make('TEST:M1');await call('/v1/reports',pending);await review(env.DB,pending.payload.id,'reject','근거 부족한 제보','operator');
  const snapshot=await shared();expect(snapshot.counts).toEqual({high:1,middle:0,elementary:0});
  expect(snapshot.schools[0].lastSuccessDay).toBe('2020-01-01');
  const text=JSON.stringify(snapshot);expect(text).not.toContain(publicKey);expect(text).not.toContain('fingerprint');
 });
});
