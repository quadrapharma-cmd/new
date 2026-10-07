#!/usr/bin/env node
// Drugbox — create the load-test members through the Supabase Auth Admin API (fallback for tools/scale/seed_100k.sql).
//
//   SUPABASE_URL=https://<staging-ref>.supabase.co SUPABASE_SERVICE_ROLE_KEY=… node tools/scale/seed_auth_admin.mjs
//   then: psql "$STAGING_DB_URL" -v ON_ERROR_STOP=1 -f tools/scale/seed_100k.sql
//
// Use it when a member that seed_100k.sql inserted straight into auth.users cannot sign in on your Supabase version
// (GoTrue changes its tables now and then). It creates member<N>@scale.test / Scale-pass-2026, e-mail confirmed,
// with the SAME id the SQL seed uses (md5('drugbox-scale-' || N) as a uuid), so the SQL seed then finds them,
// skips them and adds profiles and everything else. Slower: ~100k accounts take 20-60 minutes (bcrypt on the server).
// Idempotent and resumable: an existing member (422) is skipped; FROM=<N> starts later.
// Settings: USERS (100000), FROM (1), CONCURRENCY (16), PASSWORD (Scale-pass-2026).
// The service key is read from the environment only and never printed. Refuses a project that already has many
// accounts (a production project) unless --prod is given.
import crypto from 'node:crypto';

const URL_ = (process.env.SUPABASE_URL || '').replace(/\/+$/, '');
const KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || '';
const USERS = +(process.env.USERS || 100000), FROM = +(process.env.FROM || 1), CONC = +(process.env.CONCURRENCY || 16);
const PASSWORD = process.env.PASSWORD || 'Scale-pass-2026';
const PROD = process.argv.includes('--prod');
if (!URL_ || !KEY) { console.error('set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (staging)'); process.exit(2); }

const uuidOf = (n) => { const h = crypto.createHash('md5').update('drugbox-scale-' + n).digest('hex');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`; };
const FIRST = ['Ahmed', 'Mohamed', 'Mona', 'Sara', 'Khaled', 'Yasmin', 'Amr', 'Noha', 'Mariam', 'Youssef', 'Omar', 'Heba', 'Karim', 'Dina', 'Tarek', 'Rania', 'Hossam', 'Salma', 'Mahmoud', 'Nour'];
const LAST = ['Abdallah', 'Hassan', 'Ibrahim', 'Mostafa', 'Soliman', 'El-Sherif', 'Mansour', 'Fawzy', 'Gaber', 'Hamdy', 'Kamel', 'Lotfy', 'Nasser', 'Ragab', 'Saleh', 'Tawfik', 'Zaki', 'Farouk', 'Galal', 'Morsy', 'Shawky', 'Yassin', 'Ashour', 'Badawy', 'Darwish'];
const H = { apikey: KEY, Authorization: 'Bearer ' + KEY, 'Content-Type': 'application/json' };

async function total() {
  const r = await fetch(URL_ + '/auth/v1/admin/users?page=1&per_page=1', { headers: H });
  if (!r.ok) throw new Error('admin API refused (' + r.status + ') — is this the service_role key?');
  return +(r.headers.get('x-total-count') || 0);
}
async function create(n, tries = 0) {
  const r = await fetch(URL_ + '/auth/v1/admin/users', { method: 'POST', headers: H, body: JSON.stringify({
    id: uuidOf(n), email: `member${n}@scale.test`, password: PASSWORD, email_confirm: true,
    user_metadata: { name: FIRST[n % 20] + ' ' + LAST[Math.floor(n / 20) % 25] } }) });
  if (r.ok) return 'created';
  const b = await r.text();
  if (r.status === 422 && /already|exists|registered/i.test(b)) return 'existing';
  if ((r.status === 429 || r.status >= 500) && tries < 6) { await new Promise((s) => setTimeout(s, 500 * 2 ** tries)); return create(n, tries + 1); }
  throw new Error(`member${n}: ${r.status} ${b.slice(0, 200)}`);
}

// the production project's ref (SUPABASE_PROD_REF, as in deploy/.env.*): refused without --prod even while it is still empty
const PROD_REF = process.env.SUPABASE_PROD_REF || '';
if (PROD_REF && new URL(URL_).hostname.split('.')[0] === PROD_REF && !PROD) { console.error('SUPABASE_URL is the PRODUCTION project (SUPABASE_PROD_REF) — refusing; the load seed is for staging'); process.exit(3); }
const before = await total();
console.log(`target ${URL_} — ${before} accounts now; creating member${FROM} … member${USERS} (${CONC} at a time)`);
if (before > USERS + 500 && !PROD) { console.error('this project already has many accounts (production?) — refusing; pass --prod only if you really mean it'); process.exit(3); }
let next = FROM, done = 0, made = 0, had = 0; const t0 = Date.now();
async function worker() {
  while (next <= USERS) {
    const n = next++, res = await create(n);
    if (res === 'created') made++; else had++;
    if (++done % 1000 === 0) console.log(`  ${done} done (${made} created, ${had} existing) — ${Math.round((Date.now() - t0) / 1000)} s, at member${n}`);
  }
}
try { await Promise.all(Array.from({ length: CONC }, worker)); }
catch (e) { console.error('stopped: ' + e.message + `\nresume with FROM=${Math.max(FROM, next - CONC)}`); process.exit(1); }
console.log(`finished: ${made} created, ${had} existing in ${Math.round((Date.now() - t0) / 1000)} s — now run tools/scale/seed_100k.sql`);
