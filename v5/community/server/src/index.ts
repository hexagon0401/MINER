import {Problem,requireValue,object,exact,decode,encode,digest,verifyReport,canonical} from './protocol';
export interface Env { DB:D1Database; COMMUNITY_ENABLED:string; SNAPSHOT_SIGNING_KEY?:string; ALLOW_FIXTURE_CATALOG?:string }
function json(value:unknown,status=200,headers:Record<string,string>={}) {return Response.json(value,{status,headers:{'Cache-Control':'no-store',...headers}});}
async function body(request:Request) {
  if(!request.headers.get('content-type')?.toLowerCase().startsWith('application/json')) throw new Problem(415,'json_required');
  if(Number(request.headers.get('content-length')??0)>16384) throw new Problem(413,'report_too_large');
  const reader=request.body?.getReader();if(!reader) throw new Problem(400,'invalid_json');
  const chunks:Uint8Array[]=[];let size=0;
  while(true) {
    const {done,value}=await reader.read();if(done)break;
    size+=value.byteLength;if(size>16384){await reader.cancel();throw new Problem(413,'report_too_large');}
    chunks.push(value);
  }
  const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
  try {return JSON.parse(new TextDecoder('utf-8',{fatal:true,ignoreBOM:false}).decode(bytes));}catch {throw new Problem(400,'invalid_json');}
}
async function catalog(env:Env) {
  const ready=await env.DB.prepare("SELECT value FROM settings WHERE key='catalog_ready'").first<{value:number}>();
  if(ready?.value!==1) throw new Problem(503,'catalog_import_incomplete');
  const result=await env.DB.prepare('SELECT key,value FROM catalog_meta').all<{key:string;value:string}>();
  const meta:Record<string,unknown>={};for(const row of result.results) meta[row.key]=JSON.parse(row.value);
  if(meta.complete!==true || (meta.fixture===true && env.ALLOW_FIXTURE_CATALOG!=='true')) throw new Problem(503,'catalog_not_ready');
  return meta;
}
async function challenge(request:Request,env:Env) {
  await catalog(env);
  const input=await body(request);object(input);exact(input,['publicKey']);
  const raw=decode(input.publicKey);requireValue(raw.length===65 && raw[0]===4,'invalid_public_key');
  try {await crypto.subtle.importKey('raw',raw,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);}catch {throw new Problem(400,'invalid_public_key');}
  const now=Math.floor(Date.now()/1000),fingerprint=await digest(raw);
  await env.DB.prepare('DELETE FROM challenges WHERE expires_at<?').bind(now-86400).run();
  const count=await env.DB.prepare('SELECT count(*) AS n FROM challenges WHERE fingerprint=? AND created_at>?').bind(fingerprint,now-86400).first<{n:number}>();
  if((count?.n??0)>=10) throw new Problem(429,'challenge_quota');
  const id=crypto.randomUUID(),nonce=encode(crypto.getRandomValues(new Uint8Array(32))),expiresAt=now+300;
  await env.DB.prepare('INSERT INTO challenges(id,nonce,fingerprint,expires_at,created_at) VALUES(?,?,?,?,?)').bind(id,nonce,fingerprint,expiresAt,now).run();
  return json({id,nonce,expiresAt},201);
}
async function submit(request:Request,env:Env) {
  const checked=await verifyReport(await body(request));const {envelope,fingerprint,payloadHash}=checked,p=envelope.payload;
  const existing=await env.DB.prepare('SELECT fingerprint,payload_hash,status FROM reports WHERE id=?').bind(p.id).first<{fingerprint:string;payload_hash:string;status:string}>();
  if(existing) {
    if(existing.fingerprint!==fingerprint || existing.payload_hash!==payloadHash) throw new Problem(409,'report_id_conflict');
    return json({id:p.id,status:existing.status});
  }
  const meta=await catalog(env);if(meta.catalog_version!==p.catalogVersion) throw new Problem(409,'catalog_version_mismatch');
  const school=await env.DB.prepare('SELECT id FROM schools WHERE id=? AND active=1').bind(p.schoolId).first();
  requireValue(school,'unknown_school');
  const now=Math.floor(Date.now()/1000),diagnosed=Date.parse(p.diagnosedAt)/1000;
  if(diagnosed<now-600 || diagnosed>now+30) throw new Problem(400,'diagnosis_not_fresh');
  if(!p.challenge) throw new Problem(400,'online_challenge_required');
  try {
    const insert=env.DB.prepare(`INSERT INTO reports(id,school_id,fingerprint,day,diagnosed_at,created_at,outcome,payload,payload_hash,public_key,signature,source)
      SELECT ?,?,?,?,?,?,?,?,?,?,?,'online' FROM challenges WHERE id=? AND nonce=? AND fingerprint=? AND used=0 AND expires_at>=?`)
      .bind(p.id,p.schoolId,fingerprint,new Date().toISOString().slice(0,10),p.diagnosedAt,now,p.outcome,canonical(p),payloadHash,envelope.publicKey,envelope.signature,p.challenge.id,p.challenge.nonce,fingerprint,now);
    const consume=env.DB.prepare('UPDATE challenges SET used=1 WHERE id=? AND EXISTS(SELECT 1 FROM reports WHERE id=?)').bind(p.challenge.id,p.id);
    const results=await env.DB.batch([insert,consume]);
    if(results[0].meta.changes!==1) throw new Problem(409,'challenge_expired_or_used');
  }catch(error) {
    if(error instanceof Problem) throw error;
    const message=String(error);
    if(message.includes('daily_quota') || message.includes('UNIQUE constraint')) throw new Problem(429,'report_quota');
    throw error;
  }
  return json({id:p.id,status:'pending'},201);
}
export async function snapshot(env:Env) {
  const meta=await catalog(env);
  if(!env.SNAPSHOT_SIGNING_KEY) throw new Problem(503,'snapshot_signer_not_configured');
  const rows=await env.DB.prepare(`SELECT s.id AS schoolId,s.level,c.last_success_day AS lastSuccessDay,c.last_failure_day AS lastFailureDay
    FROM schools s JOIN school_coverage c ON c.school_id=s.id WHERE s.active=1 ORDER BY s.id`).all<{schoolId:string;level:string;lastSuccessDay:string|null;lastFailureDay:string|null}>();
  const counts:Record<string,number>={high:0,middle:0,elementary:0};
  for(const row of rows.results) if(row.lastSuccessDay) counts[row.level]++;
  const seq=await env.DB.prepare("SELECT value FROM settings WHERE key='snapshot_sequence'").first<{value:number}>();
  const payload={schemaVersion:1,catalogVersion:meta.catalog_version,sequence:seq?.value??0,generatedAt:new Date().toISOString(),counts,
    schools:rows.results.map(({schoolId,lastSuccessDay,lastFailureDay})=>({schoolId,lastSuccessDay,lastFailureDay}))};
  const bytes=new TextEncoder().encode(canonical(payload));
  const key=await crypto.subtle.importKey('pkcs8',decode(env.SNAPSHOT_SIGNING_KEY),{name:'Ed25519'},false,['sign']);
  const signature=new Uint8Array(await crypto.subtle.sign('Ed25519',key,bytes));
  return json({payload:encode(bytes),signature:encode(signature)},200,{'Cache-Control':'public, max-age=600'});
}
export default {
  async fetch(request:Request,env:Env,context?:ExecutionContext):Promise<Response> {
    try {
      const path=new URL(request.url).pathname;
      if(path==='/healthz') return json({service:'miner-community',enabled:env.COMMUNITY_ENABLED==='true'});
      if(env.COMMUNITY_ENABLED!=='true') throw new Problem(503,'community_not_open');
      if(request.method==='GET' && path==='/v1/snapshot') {
        if(context) {
          const cache=await caches.open('miner-approved-schools-v1');
          const cached=await cache.match(request);if(cached)return cached;
          const response=await snapshot(env);context.waitUntil(cache.put(request,response.clone()));return response;
        }
        return await snapshot(env);
      }
      if(request.method==='POST' && path==='/v1/challenges') return await challenge(request,env);
      if(request.method==='POST' && path==='/v1/reports') return await submit(request,env);
      throw new Problem(404,'not_found');
    }catch(error) {
      if(error instanceof Problem) return json({error:error.code},error.status);
      // Do not log bodies, addresses, keys, or underlying database error strings.
      return json({error:'service_unavailable'},503);
    }
  }
};
