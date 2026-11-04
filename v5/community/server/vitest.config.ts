import {defineConfig} from 'vitest/config';
import {cloudflareTest,readD1Migrations} from '@cloudflare/vitest-pool-workers';
export default defineConfig(async()=>({
 plugins:[cloudflareTest({wrangler:{configPath:'./wrangler.jsonc'},miniflare:{bindings:{COMMUNITY_ENABLED:'false',ALLOW_FIXTURE_CATALOG:'false',SNAPSHOT_SIGNING_KEY:'',TEST_MIGRATIONS:await readD1Migrations('./migrations')}}})],
 test:{include:['test/**/*.test.ts'],fileParallelism:false,testTimeout:15000}
}));
