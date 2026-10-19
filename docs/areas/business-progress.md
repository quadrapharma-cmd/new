# Area: business and payments — running log

Branch `claude/area-business` (from `claude/new-session-8nmyo7`). Migrations 0050–0059. Items: PRODUCT-GAPS 3.2
B-01…B-21 (except B-06 presets, B-07 demo rows, B-22 — the coordinator's). Journeys J-BUSINESS-01…49.

## Restart recipe
1. `bash tools/local-supabase/setup-session.sh` and export its last line.
2. `tools/local-supabase/start.sh`, then `start-payments.sh tools/local-supabase/payments.env.example`, then `python3 tests/fixtures/make_fixtures.py`.
3. Journeys: `DB_NAME=drugbox_live APP_URL=http://localhost:54321/ python3 tests/journeys/run_business.py --out /tmp/jb --configs demo:en:1440,live:en:1440 --jobs 2 --only J-BUSINESS-xx`.

## Log
- 2026-10-19: started; baseline run of all business journeys (demo EN 1440 + live EN 1440).
