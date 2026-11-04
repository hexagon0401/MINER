import {defineConfig} from 'vitest/config';
import {cloudflareTest,readD1Migrations} from '@cloudflare/vitest-pool-workers';
export default defineConfig(async()=>({
 plugins:[cloudflareTest({wrangler:{configPath:'./wrangler.jsonc'},miniflare:{bindings:{TEST_MIGRATIONS:await readD1Migrations('./migrations')}}})],
 test:{include:['test/**/*.test.ts'],fileParallelism:false,testTimeout:15000}
}));
