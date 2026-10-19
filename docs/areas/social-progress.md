# Area social & account — running log (branch claude/area-social)

Restart recipe: `bash tools/local-supabase/setup-session.sh` → eval its last line → `setsid nohup tools/local-supabase/start.sh &`
(wait for :54321) → `tools/local-supabase/start-payments.sh` → `python3 tests/fixtures/make_fixtures.py`.

## Layout decisions
- Demo behaviour for this area: new layer `web/src/social.js` + `web/src/social.css` (added to build.py MODULES).
- Live code: `web/src/live/social.js` (loaded by live.py right after adapter.js) — keeps the shared adapter.js nearly untouched;
  adapter.js only gets one delimited block `AREA social: internals` that exposes what social.js needs.
- Migrations 0040–0049 (this area only).

## Baseline (start, demo EN 1440 + live EN 1440)
Failing: J-SOCIAL-02..08, 10..12, 14..16, 18, 21, 23, 25..28, 41..51 (see docs/FEATURE-STATUS-2026-10.md).

## Plan / status
| Step | Items | Status |
|---|---|---|
| 1 infra | gateway: recover / verify / PUT user / resend / confirm mode / test mailbox | todo |
| 2 account | S-05, S-16, X-01 (Settings, legal drafts, delete, export), J-03/04 fixes | todo |
| 3 feed | S-08, S-12, S-13, S-22, counts, end marker, preview remove | todo |
| 4 profile | S-06, S-14, S-25 | todo |
| 5 search/nav | S-18, S-20, S-21, S-09 rest, J-47/48/51 | todo |
| 6 verify + report | verifiers, suites, report | todo |
