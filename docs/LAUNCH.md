# Drugbox — launch checklist (staging → production)

## الخلاصة بالمصري

- كل حاجة الإطلاق محتاجها بقت **سكربتات جاهزة** في `deploy/`: قاعدة البيانات + الـ Edge Functions (`supabase_deploy.sh`)،
  الموقع على Vercel (`vercel_deploy.sh`)، والنسخ الاحتياطي المشفّر + تجربة الاسترجاع (`backup.sh`).
- اللي ناقص منك **مفاتيح بس**: Supabase (رقم المشروع + باسورد قاعدة البيانات + access token)، Vercel (token + team/project id)،
  ومفاتيح الدفع **التجريبية** لـ Paymob وFawry للـ staging. تملا ملفات الـ `.example` وتشغّل أمر واحد لكل خطوة.
- اتجرّبت كلها هنا على نسخة محلية بدل الـ staging: الـ 25 migration اتطبقت، والتشغيل التاني ما طبّقش حاجة، وتعديل migration قديمة
  اترفض، والـ schema sweep طلع "none" في الستة، والـ 5 buckets والـ realtime موجودين، والموقع اتبنى وطلع PARITY OK،
  والباك أب اتشفّر واترجع في قاعدة فاضية بنفس عدد الصفوف بالظبط.
- **الإنتاج محمي**: أي سكربت يرفض يشتغل على مشروع الإنتاج من غير `--prod`، ويرفض `--prod` على أي مشروع تاني،
  ويرفض مفاتيح Paymob الحقيقية على الـ staging ومفاتيح التجربة على الإنتاج. وعشان كده `SUPABASE_PROD_REF` **إجباري** في كل ملف إعدادات
  (حتى بتاع الـ staging) — من غيره السكربت يوقف. وبيانات اختبار الضغط (100 ألف عضو) بترفض تتزرع على قاعدة الإنتاج.
- **تنبيه مهم من Supabase**: ابتداءً من 30 أكتوبر 2026 المشاريع الجديدة ممكن ما تدّيش صلاحيات تلقائية للجداول الجديدة.
  سكربت النشر بيكشف ده ويوقف (فحص "API grants") — لو حصل، محتاجين migration صغيرة فيها `grant` صريحة قبل الإطلاق.

---

Work top to bottom. **Staging first** (its own Supabase project + a Vercel preview); production only after staging passes.
Every script prints what it does, never prints a secret value, is safe to re-run, and refuses production without `--prod`.

| File | What it is |
|---|---|
| `deploy/env.supabase.example` → `deploy/.env.supabase` (`.prod`) | database URL/password, project ref, Supabase access token, `SUPABASE_PROD_REF`, backup key file |
| `deploy/env.functions.example` → `deploy/.env.functions` (`.prod`) | Edge Function secrets (Paymob, Fawry, InstaPay, `APP_URL`, `ALLOWED_ORIGINS`) |
| `deploy/env.web.example` → `deploy/.env.web` (`.prod`) | `DRUGBOX_SUPABASE_URL`, anon key, `DRUGBOX_SENTRY_LOADER`, Vercel token/ids |
| `deploy/supabase_deploy.sh` | migrations (ledger), checks, function secrets, the three functions, smoke calls |
| `deploy/vercel_deploy.sh` | demo build → parity → live build → checks → `vercel deploy` (preview; `--prod` for production) |
| `deploy/vercel.json` | the **one** template for the hosting headers (CSP etc.); `web/build/live.py` fills in the Supabase origin (and Sentry, only when set) |
| `deploy/backup.sh` | encrypted `pg_dump` with retention; `--restore-drill` restores into an empty database and verifies it |

The `.env*` copies, `deploy/logs/`, `deploy/.out/` and `deploy/backups/` are git-ignored. Keep the copies `chmod 600`.

**On the machine that runs them:** bash, `psql`/`pg_dump`/`pg_restore` of the **same major version as the Supabase server or newer**
(Supabase runs PostgreSQL 15/17: install the 17 client tools), Python 3.11+ with `pillow` and `playwright` (+ `playwright install chromium`
— the demo build needs it), Node 20+ (`npx` fetches the pinned Supabase and Vercel CLIs), `openssl`, `curl`. Passwords and tokens travel
in the environment only — never on a command line (where `ps` would show them); prefer the settings files to `psql "postgres://user:pass@…"`.

## 1. Accounts and decisions (owner)
- [ ] Supabase organisation; two projects: `drugbox-staging`, `drugbox-prod` (region close to Egypt/Gulf, e.g. Frankfurt). Note both refs;
      put the production ref in `SUPABASE_PROD_REF` in every settings file (staging ones too — that is what protects production).
- [ ] Vercel team + one project (Root Directory irrelevant: the script uploads the built folder) + the domain (e.g. `app.drugbox.app`); Sentry project (JavaScript – Browser).
- [ ] Paymob: secret/public keys, HMAC secret, card + wallet integration ids (**test** ones for staging). Fawry: merchant code + secure key (staging first). InstaPay address.
- [ ] Prices: confirm boost/featured (seeded EGP 1,450 / 7 days, EGP 3,950 / 30 days, before 14% VAT) — `payment_products`. `supabase_deploy.sh` prints the current prices at the end of every run.
- [ ] A backup key: `deploy/backup.sh --gen-key ~/.drugbox-backup.key` — keep a second copy offline (password manager). Without it no backup can be restored.

## 2. Staging
- [ ] Settings: `cp deploy/env.supabase.example deploy/.env.supabase` and `cp deploy/env.functions.example deploy/.env.functions` — fill in (staging ref,
      database password, access token; Paymob **test** keys, `FAWRY_BASE=https://atfawry.fawrystaging.com`; `APP_URL`/`ALLOWED_ORIGINS` = the staging web address).
- [ ] Optional first look, changes nothing: `deploy/supabase_deploy.sh --dry-run --db-only`
- [ ] Deploy: `deploy/supabase_deploy.sh`. It:
  1. checks the connection, the server version, the extensions (pgcrypto, pg_trgm) and that Supabase's `auth`/`storage`/roles/`supabase_realtime` exist;
  2. keeps a ledger `drugbox_deploy.migrations` (file + sha256; schema not exposed to the API) and stamps the database `staging`/`production`.
     Applied files are skipped; a **changed** applied file is refused (fix forward with a new migration); a file numbered into the past is refused;
  3. applies each pending `supabase/migrations/NNNN_*.sql` in order, each in **one transaction** with `ON_ERROR_STOP` (a failure rolls that file back completely);
  4. checks: `supabase/tests/schema_sweep.sql` (every line must end in "none"), the five buckets (`videos`, `post-media` public; `message-media`, `documents`,
     `reference-evidence` private), `messages` + `notifications` in the realtime publication, **API grants** (see below), `jit = off` for the API login role
     (migration 0022's note — done by the script; if the platform refuses `authenticator` it sets anon/authenticated/service_role instead), the pg_cron job;
  5. sets the function secrets (`supabase secrets set --env-file`) and deploys `payments-create` (user JWT required), `paymob-webhook` and `fawry-webhook`
     (`--no-verify-jwt`: Paymob/Fawry call them without a Supabase token; they verify the provider's signature), then calls each one:
     webhooks `GET` → 405 from the function itself, `payments-create` browser preflight from `ALLOWED_ORIGINS` → 200 with CORS.
  - The direct database host is IPv6-only; on an IPv4-only network use the **Session pooler** (port 5432) — see `env.supabase.example`. Port 6543 is refused.
  - If the database already has the migrations (applied by hand), the script stops; record them once with `--baseline-through 0025`.
- [ ] Supabase Auth (dashboard, manual): Site URL + redirect URLs = the staging web address; email confirmation on; **custom SMTP** (the built-in sender is for testing only — rate-limited).
- [ ] pg_cron (Database → Extensions) on, then re-run the deploy: it schedules `drugbox-expire-vip` (daily 01:17 UTC) — otherwise VIP plans never expire.
- [ ] Web: `cp deploy/env.web.example deploy/.env.web`, fill in (staging URL + **anon** key; Vercel token + ids), then `deploy/vercel_deploy.sh`
      (`--dry-run` builds and checks without calling Vercel). Output goes to `deploy/.out/preview/` (never `web/dist`). It refuses a non-anon key, a key of another
      project, a build that fails parity with `web/reference/demo-approved.html`, a CSP without the Supabase origin, or a missing file.
      Previews may sit behind Vercel Deployment Protection (401 when not signed in to Vercel).
- [ ] Open it, sign up, post, message, upload, pay with the Paymob test card / Fawry staging.
- [ ] Paymob test dashboard: transaction-processed callback (card **and** wallet integrations) → `https://<staging-ref>.supabase.co/functions/v1/paymob-webhook`.
      Fawry staging: server notification V2 → `…/functions/v1/fawry-webhook`. (`supabase_deploy.sh` prints both URLs.)
- [ ] Make your own account admin: `update public.profiles set role = 'admin' where email = '…';`
- [ ] First backup + drill on staging: `deploy/backup.sh`, then `DRILL_DB_URL=<empty scratch database> deploy/backup.sh --restore-drill`.

**API grants check.** Supabase is changing new projects (config `api.auto_expose_new_tables`, deprecated on 2026-10-30) to stop granting new
`public` tables to `anon`/`authenticated` automatically. The migrations rely on those automatic grants, so on such a project every API request
would fail with "permission denied". The deploy fails the check "policy without the table grant" in that case (rehearsed: 79 gaps found
on a database without the default grants). The fix is a new migration with explicit `grant select/insert/update/delete … to authenticated`,
`grant select … to anon` where the anon policies allow it, and `grant usage on sequences … to authenticated` — then re-run the deploy.

## 3. Load test on staging (decides the database size)
- [ ] Seed: `psql "$STAGING_DB_URL" -v ON_ERROR_STOP=1 -f tools/scale/seed_100k.sql` (100k members `member<N>@scale.test` / `Scale-pass-2026`).
      If signing in as a seeded member fails on your Supabase version, create the members with `tools/scale/seed_auth_admin.mjs` (Auth Admin API, slower) first.
      Remove the test data afterwards with `tools/scale/unseed.sql`. Never on production: the seed refuses a database that `supabase_deploy.sh` stamped
      `production` or that has more than 2,000 real accounts, and `seed_auth_admin.mjs` refuses the `SUPABASE_PROD_REF` project (both only with an explicit prod flag).
- [ ] Run from a separate machine or k6 Cloud (not a laptop on Wi-Fi):
      `k6 run -e BASE=https://<staging-ref>.supabase.co -e ANON=<anon key> -e VUS=2000 -e USERS=100000 tests/load/k6_drugbox.js`
      (raise Auth's sign-in rate limit on staging for the run — see the header of the k6 script).
- [ ] Pass = thresholds green (errors < 1 %, p95 feed/conversations/directory < 500 ms, post < 800 ms). If not: raise the compute size and repeat; watch Supabase → Reports (CPU, connections).
- [ ] Database timings with RLS: `STAGING_DB_URL=… python3 tools/scale/timings.py` (from the environment the password stays out of `ps`).

## 4. Production
- [ ] `deploy/.env.supabase.prod`, `deploy/.env.functions.prod` (**live** Paymob keys; no `FAWRY_BASE`), `deploy/.env.web.prod` — the scripts refuse test keys / Fawry staging here.
- [ ] `deploy/supabase_deploy.sh --prod` (compute size from step 3; **Point-in-Time Recovery** on; daily backups checked).
- [ ] `deploy/vercel_deploy.sh --prod`; the domain in Vercel (HTTPS automatic); headers come from `deploy/vercel.json` via the build.
- [ ] Sentry: the loader URL in `DRUGBOX_SENTRY_LOADER` (`deploy/.env.web.prod`), redeploy; alerts to your email/WhatsApp.
- [ ] Uptime checks: the site (200), and `GET https://<prod-ref>.supabase.co/functions/v1/paymob-webhook` → **405** (answered by the function itself).
      (`payments-create` requires a JWT at the gateway, so a plain GET there gets 401 from Supabase, not from the function.)
- [ ] `deploy/backup.sh --prod` weekly (cron) to storage you control + one `--restore-drill --prod` into an empty database; then monthly.
- [ ] Payment dashboards → production webhook URLs. One real small payment per method (card, Vodafone Cash, Fawry, InstaPay), then refund.
- [ ] Seed real content: training courses, the companies directory import, your admin team (`role = 'admin'`).

## 5. After go-live (first week)
- [ ] Daily: Sentry errors, Supabase CPU/slow queries, Review queues (verifications, warnings, payments).
- [ ] After every migration: `deploy/supabase_deploy.sh` on staging (it runs `schema_sweep.sql` and the other checks), `tools/scale/timings.py` against a staging copy, then `--prod`.

## Rollback
Web: Vercel → Deployments → the previous one → Promote (one click). Database: migrations only add; if one misbehaves, fix forward with a new
migration (the ledger refuses edits to applied files); for data loss use Point-in-Time Recovery, or `deploy/backup.sh --restore-drill` into a new
database to recover specific rows. Payments are activated only by signed callbacks — pausing the webhooks pauses activation safely.

## Rehearsed locally (October 2026, no network to Supabase/Vercel from the build machine)
- `supabase_deploy.sh --db-only --with-local-stub` on a bare PostgreSQL 16 (`--with-local-stub` loads `supabase/tests/_local_supabase_stub.sql`, a stand-in for
  Supabase's auth/storage; without it the script stops and explains that real Supabase has them): 25 migrations in 1.6 s, all checks OK; second run: nothing to apply.
- Refusals proven: changed applied file, migration numbered into the past, failing migration (rolled back, ledger unchanged), production ref/stamp without `--prod`,
  `--prod` against staging, transaction pooler port, stub against a remote host, live keys on staging, placeholders, `SUPABASE_*` secrets.
- Functions step with a recording stand-in for the Supabase CLI and the real function code served locally: secrets + 3 deploys with the right JWT setting,
  smoke 405/405/200. The real CLI 2.120 resolves the `index.js` entrypoints and the shared files from the generated `config.toml`, then stops at the network.
- `vercel_deploy.sh --dry-run`: demo build 48 s, PARITY OK, 37 files / 4.7 MB, CSP with the Supabase origin; with Sentry: loader first in `<head>`, CSP extended; real Vercel CLI stops at the network.
- `backup.sh`: 3 backups with retention 2; restore drill into an empty database: no errors, sweep "none" ×6, row counts equal for all 50 tables (1,573 rows),
  schema of the restored database identical to the source; tampered file and wrong key refused (HMAC), non-empty drill database and drill = source refused.
- Hostile review (L-review) re-ran every rehearsal on fresh databases: deploy + re-run + changed file + failing file (rolled back, ledger unchanged) + file numbered
  into the past; backup + restore drill PASSED; `vercel_deploy.sh --dry-run` with and without Sentry (Sentry hosts only in the Sentry build); seed (2,000 members,
  every counter consistent, no trigger left disabled), refusal on a database stamped `production`, k6 against the seed (0 % errors, all thresholds PASS), unseed back to zero.
