// Runs every *.test.js under tests/ and dev/tests/ with node --test; passes when there are none.
import { readdirSync, statSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
function find(dir, out = []) {
  if (!existsSync(dir)) return out;
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) {
      if (f !== 'node_modules') find(p, out);
    } else if (f.endsWith('.test.js')) out.push(p);
  }
  return out;
}
const files = [...find(join(ROOT, 'tests')), ...find(join(ROOT, 'dev/tests'))].sort();
if (!files.length) {
  console.log('No test files found (tests/**/*.test.js, dev/tests/**/*.test.js): nothing to run.');
  process.exit(0);
}
const extra = process.argv.slice(2);
const r = spawnSync(process.execPath, ['--test', ...extra, ...files], { stdio: 'inherit', cwd: ROOT, env: process.env });
process.exit(r.status ?? 1);
