// Public, test-only signatures. These keys are never production credentials.
import {webcrypto} from 'node:crypto';
import {readFileSync,writeFileSync} from 'node:fs';
const encode=b=>Buffer.from(b).toString('base64url');
const canonical=v=>v===null || typeof v!=='object'?JSON.stringify(v):Array.isArray(v)?'['+v.map(canonical).join(',')+']':'{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+canonical(v[k])).join(',')+'}';
const meta=JSON.parse(readFileSync(new URL('../../fixtures/test-catalog.json',import.meta.url)));
const key=await webcrypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},true,['sign','verify']);
const payload={schemaVersion:1,id:'11111111-1111-4111-8111-111111111111',schoolId:'TEST:H1',catalogVersion:meta.catalog_version,diagnosedAt:'2020-01-01T00:00:00Z',appVersion:'5.0.0-beta.2',osMajor:16,
checks:{engine_running:true,native_platform:true,engine_schema:true,warp_local_proxy_mode:true,socks5_greeting:true,warp_trace:true},schoolNetworkConfirmed:true,clientConfirmed:true,game:'not_tested',video:'not_tested',clientReturn:'not_tested',outcome:'success',failureCode:null,challenge:null};
const canonicalReport=canonical(payload);
const report={payload,publicKey:encode(await webcrypto.subtle.exportKey('raw',key.publicKey)),signature:encode(await webcrypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},key.privateKey,new TextEncoder().encode(canonicalReport)))};
const ed=await webcrypto.subtle.generateKey('Ed25519',true,['sign','verify']);
const snapshot=async sequence=>{
 const payload={schemaVersion:1,catalogVersion:meta.catalog_version,sequence,generatedAt:'2020-01-01T00:00:00.000Z',counts:{high:1,middle:0,elementary:0},schools:[{schoolId:'TEST:H1',lastSuccessDay:'2020-01-01',lastFailureDay:null}]};
 const bytes=new TextEncoder().encode(canonical(payload));
 return {payload:encode(bytes),signature:encode(await webcrypto.subtle.sign('Ed25519',ed.privateKey,bytes))};
};
writeFileSync(new URL('../../fixtures/protocol-vectors.json',import.meta.url),JSON.stringify({testOnly:true,canonicalReport,report,snapshotPublicKey:encode(await webcrypto.subtle.exportKey('raw',ed.publicKey)),snapshot:await snapshot(2),olderSnapshot:await snapshot(1)},null,2)+'\n');
