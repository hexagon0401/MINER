export const CHECKS = ['engine_running','native_platform','engine_schema','warp_local_proxy_mode','socks5_greeting','warp_trace'] as const;
export type Outcome = 'pass'|'fail'|'not_tested';
export interface ReportBody {
  schemaVersion:1; id:string; schoolId:string; catalogVersion:string; diagnosedAt:string;
  appVersion:string; osMajor:number; checks:Record<typeof CHECKS[number],boolean>;
  schoolNetworkConfirmed:boolean; clientConfirmed:boolean; game:Outcome; video:Outcome; clientReturn:Outcome;
  outcome:'success'|'failure'; failureCode:null|'engine_not_running'|'diagnostic_failed'|'timeout'|'network_changed';
  challenge:null|{id:string;nonce:string};
}
export interface SignedReport { payload:ReportBody; publicKey:string; signature:string }
export class Problem extends Error { constructor(public status:number, public code:string) { super(code); } }
export function requireValue(value:unknown, code:string):asserts value { if(!value) throw new Problem(400,code); }
export function object(value:unknown):asserts value is Record<string,unknown> {
  requireValue(value!==null && typeof value==='object' && !Array.isArray(value),'object_required');
}
export function exact(value:Record<string,unknown>, keys:string[]) {
  requireValue(Object.keys(value).length===keys.length && keys.every(k=>Object.hasOwn(value,k)),'unknown_or_missing_fields');
}
export function canonical(value:unknown):string {
  if(value===null || typeof value==='string' || typeof value==='boolean') return JSON.stringify(value);
  if(typeof value==='number') { requireValue(Number.isSafeInteger(value),'integer_required'); return JSON.stringify(value); }
  if(Array.isArray(value)) return '['+value.map(canonical).join(',')+']';
  object(value);
  return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}';
}
export function encode(bytes:Uint8Array):string {
  return btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');
}
export function decode(value:unknown):Uint8Array {
  requireValue(typeof value==='string' && /^[A-Za-z0-9_-]+$/.test(value) && value.length<1000,'base64url_required');
  try { return Uint8Array.from(atob(value.replaceAll('-','+').replaceAll('_','/')),c=>c.charCodeAt(0)); }
  catch { throw new Problem(400,'base64url_required'); }
}
export async function digest(bytes:Uint8Array):Promise<string> {
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(v=>v.toString(16).padStart(2,'0')).join('');
}
const uuid=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
export function reportBody(value:unknown):asserts value is ReportBody {
  object(value);
  exact(value,['schemaVersion','id','schoolId','catalogVersion','diagnosedAt','appVersion','osMajor','checks','schoolNetworkConfirmed','clientConfirmed','game','video','clientReturn','outcome','failureCode','challenge']);
  requireValue(value.schemaVersion===1 && typeof value.id==='string' && uuid.test(value.id),'invalid_report_version_or_id');
  requireValue(typeof value.schoolId==='string' && /^[A-Za-z0-9_-]+:[A-Za-z0-9_-]+$/.test(value.schoolId) && value.schoolId.length<100,'invalid_school_id');
  requireValue(typeof value.catalogVersion==='string' && /^[a-f0-9]{64}$/.test(value.catalogVersion),'invalid_catalog_version');
  requireValue(typeof value.appVersion==='string' && /^5\.\d+\.\d+(?:-[A-Za-z0-9.]+)?$/.test(value.appVersion),'invalid_app_version');
  requireValue(typeof value.osMajor==='number' && Number.isInteger(value.osMajor) && value.osMajor>=13 && value.osMajor<100,'invalid_os_major');
  requireValue(typeof value.diagnosedAt==='string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$/.test(value.diagnosedAt) && Number.isFinite(Date.parse(value.diagnosedAt)),'invalid_diagnosis_time');
  object(value.checks);exact(value.checks,[...CHECKS]);
  requireValue(CHECKS.every(k=>typeof (value.checks as Record<string,unknown>)[k]==='boolean'),'invalid_checks');
  requireValue(typeof value.schoolNetworkConfirmed==='boolean' && typeof value.clientConfirmed==='boolean','confirmations_required');
  for(const k of ['game','video','clientReturn']) requireValue(['pass','fail','not_tested'].includes(String(value[k])),'invalid_optional_outcome');
  requireValue([null,'engine_not_running','diagnostic_failed','timeout','network_changed'].includes(value.failureCode as null|string),'invalid_failure_code');
  const success=CHECKS.every(k=>(value.checks as Record<string,unknown>)[k]===true) && value.schoolNetworkConfirmed && value.clientConfirmed && value.failureCode===null;
  requireValue(value.outcome===(success?'success':'failure'),'outcome_mismatch');
  if(value.challenge!==null) {
    object(value.challenge);exact(value.challenge,['id','nonce']);
    requireValue(typeof value.challenge.id==='string' && uuid.test(value.challenge.id),'invalid_challenge');
    requireValue(decode(value.challenge.nonce).length===32,'invalid_nonce');
  }
}
export async function verifyReport(input:unknown) {
  object(input);exact(input,['payload','publicKey','signature']);reportBody(input.payload);
  const raw=decode(input.publicKey), signature=decode(input.signature);
  requireValue(raw.length===65 && raw[0]===4 && signature.length===64,'invalid_p256_encoding');
  let key:CryptoKey;
  try { key=await crypto.subtle.importKey('raw',raw,{name:'ECDSA',namedCurve:'P-256'},false,['verify']); }
  catch { throw new Problem(400,'invalid_public_key'); }
  const bytes=new TextEncoder().encode(canonical(input.payload));
  requireValue(await crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},key,signature,bytes),'invalid_signature');
  return {envelope:input as unknown as SignedReport,fingerprint:await digest(raw),payloadHash:await digest(bytes)};
}
