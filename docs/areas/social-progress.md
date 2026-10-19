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
| 1 infra | gateway: recover / verify / PUT user / resend / confirm mode / test mailbox / Resend stand-in; notify-email local schedule | done |
| 2 account | S-05, S-16, X-01 (Settings, legal drafts, delete, export), J-03/04 fixes — 0040 | built; journeys live pass, demo J-03/04 to recheck |
| 3 feed | S-08, S-12, S-13, S-22, counts, end marker, preview remove — 0041 | built |
| 4 profile | S-06, S-14, S-25 — 0042 | built; J-22..27 pass demo + live |
| 5 search/nav | S-18 (search_all 0043, top bar + Ctrl+K + Network "find people"), S-21 router, S-20, S-09 (reports, block from profile, Reported members, suspension — 0044), saved searches per member, one Saved place, message + e-mail notices (0045, notify-email), S-24 connection phone (0046), S-23 composer Product/Job, S-28 pinned header 390 | built; journeys running |
| 6 verify + report | social.rls.sql 83/83, all rls suites green on a fresh DB, sweep 6× none, migration_check OK; verifiers; report | in progress |

## Log
- 0040 had dropped the "members only" restriction of the profiles read policy (anon could read profiles) — caught by security_core / launch_readiness on a fresh DB, fixed in 0040 before any deploy.
- Comment likes were never counted (the reply guard undid the counter's update) — caught by social.rls.sql, fixed in 0045.
- saved_searches insert policy counted its own table (infinite recursion) — moved to a trigger in 0045.
- The class name `dx-sr` collided with the approved screen-reader-only class (1 px results) — renamed `dx-sres`.
- The side menu's Settings item pushed "⚙️ Admin" below the fold at 1440×900 — Settings stays on the own profile and Ctrl+K only.
