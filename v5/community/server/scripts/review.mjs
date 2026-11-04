// Operator-only CLI. No public moderation route or bundled administrator token.
import {readFileSync,writeFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {webcrypto} from 'node:crypto';
const [action,...rest]=process.argv.slice(2);
const remote=rest.includes('--remote');
const args=rest.filter(v=>v!=='--remote');
const sqlValue=v=>"'"+String(v).replaceAll("'","''")+"'";
function run(sql) {
 const dir=mkdtempSync(join(tmpdir(),'miner-review-'));
 try {
  const file=join(dir,'operation.sql');writeFileSync(file,sql);
  const result=spawnSync(process.execPath,['node_modules/wrangler/bin/wrangler.js','d1','execute','miner-community',remote?'--remote':'--local','--file',file,'--json'],{stdio:'inherit',env:{...process.env,WRANGLER_SEND_METRICS:'false'}});
  if(result.status!==0)process.exitCode=result.status??1;
 }finally {rmSync(dir,{recursive:true});}
}
if(action==='list') {
 run("SELECT id,school_id,outcome,status,diagnosed_at,review_reason FROM reports ORDER BY created_at DESC LIMIT 100;");
}else if(['approve','reject','revoke'].includes(action)) {
 const [id,reason,actor='hexagon0401']=args;
 if(!/^[a-f0-9-]{36}$/.test(id??'') || (reason??'').trim().length<3 || reason.length>500 || !actor.trim())throw new Error('Usage: npm run review -- approve|reject|revoke REPORT_ID REASON [ACTOR] [--remote]');
 const status={approve:'approved',reject:'rejected',revoke:'revoked'}[action];
 // SQL triggers validate transition and write audit+snapshot sequence atomically.
 run(`UPDATE reports SET status=${sqlValue(status)},review_reason=${sqlValue(reason)},reviewed_by=${sqlValue(actor)} WHERE id=${sqlValue(id)}; SELECT id,status,review_reason FROM reports WHERE id=${sqlValue(id)};`);
}else if(action==='import') {
 const [file]=args;if(!file)throw new Error('Provide an exported report JSON file');
 const {verifyReport,canonical}=await import('../src/protocol.ts');
 const checked=await verifyReport(JSON.parse(readFileSync(file,'utf8')));
 const p=checked.envelope.payload;
 if(p.challenge!==null)throw new Error('This import is for offline reports only');
 if(Date.parse(p.diagnosedAt)>Date.now()+30000)throw new Error('Report is dated in the future');
 const row=[p.id,p.schoolId,checked.fingerprint,new Date().toISOString().slice(0,10),p.diagnosedAt,Math.floor(Date.now()/1000),p.outcome,canonical(p),checked.payloadHash,checked.envelope.publicKey,checked.envelope.signature];
 run(`INSERT INTO reports(id,school_id,fingerprint,day,diagnosed_at,created_at,outcome,payload,payload_hash,public_key,signature,source) SELECT ${row.map(sqlValue).join(',')},'offline_review' FROM schools s WHERE s.id=${sqlValue(p.schoolId)} AND s.active=1 AND EXISTS(SELECT 1 FROM catalog_meta WHERE key='catalog_version' AND value=${sqlValue(JSON.stringify(p.catalogVersion))}); SELECT id,status FROM reports WHERE id=${sqlValue(p.id)};`);
}else {
 throw new Error('Usage: npm run review -- list | approve|reject|revoke ID REASON [ACTOR] | import FILE [--remote]');
}
