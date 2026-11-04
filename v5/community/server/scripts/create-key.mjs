// Local key preparation only. No account login, secret upload or deployment.
import {webcrypto} from 'node:crypto';
import {existsSync,mkdirSync,writeFileSync} from 'node:fs';
const production=process.argv.includes('--production');
if(existsSync('.local-keys/snapshot-private.txt') || (!production && existsSync('.dev.vars')))throw new Error('Existing local keys/config preserved; choose a separate working directory');
mkdirSync('.local-keys',{recursive:true,mode:0o700});
const key=await webcrypto.subtle.generateKey('Ed25519',true,['sign','verify']);
const privateKey=Buffer.from(await webcrypto.subtle.exportKey('pkcs8',key.privateKey)).toString('base64url');
const publicKey=Buffer.from(await webcrypto.subtle.exportKey('raw',key.publicKey)).toString('base64url');
writeFileSync('.local-keys/snapshot-private.txt',privateKey+'\n',{flag:'wx',mode:0o600});
writeFileSync('.local-keys/snapshot-public.json',JSON.stringify({developmentOnly:!production,snapshotPublicKey:publicKey},null,2)+'\n',{flag:'wx',mode:0o600});
if(!production)writeFileSync('.dev.vars',`COMMUNITY_ENABLED="true"\nALLOW_FIXTURE_CATALOG="true"\nSNAPSHOT_SIGNING_KEY="${privateKey}"\n`,{flag:'wx',mode:0o600});
console.log('Key files created under .local-keys; private material was not printed or uploaded.');
