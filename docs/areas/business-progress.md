# Area: business and payments — running log

Branch `claude/area-business` (from `claude/new-session-8nmyo7`). Migrations 0050–0059. Items: PRODUCT-GAPS 3.2
B-01…B-21 (except B-06 presets, B-07 demo rows, B-22 — the coordinator's). Journeys J-BUSINESS-01…49.

## Restart recipe
1. `bash tools/local-supabase/setup-session.sh` and export its last line.
2. `tools/local-supabase/start.sh`, then `start-payments.sh tools/local-supabase/payments.env.example`, then `python3 tests/fixtures/make_fixtures.py`.
3. Journeys: `DB_NAME=drugbox_live APP_URL=http://localhost:54321/ python3 tests/journeys/run_business.py --out /tmp/jb --configs demo:en:1440,live:en:1440 --jobs 2 --only J-BUSINESS-xx`.

## Log
- 2026-10-19: started; baseline run of all business journeys (demo EN 1440 + live EN 1440).
- Baseline (before any change): demo EN 1440 / live EN 1440 — live PASS only J-03, 06, 25, 27, 30, 31, 39, 45 (kept in docs/areas/baseline-business.json).
- 0050 company page (products+photos+price/currency, sites with capabilities + 'YYYY-MM' free months, certificates with documents, Drugbox check/reject with reason, logo/cover in company-media) and 0051 team (invites by e-mail, join requests, accept/decline, approve, routing follows roles); RLS suite company_page_team.rls.sql 61/61.
- Live PASS now: J-15, 16, 17, 18, 19, 22 (EN 1440). Journey changes: J-17 demo step 2 = skip (one demo account), J-17 step 3 strengthened (role change, invitation removed, routing follows role, survives reload), J-19 strengthened (a second certificate rejected with a reason: row gone, owner notified, not on page), J-16 ages updated_at with session_replication_role (the write trigger stamps now()), admin_decide fills the reason in the kit window, seed_site stores free months as YYYY-MM.
