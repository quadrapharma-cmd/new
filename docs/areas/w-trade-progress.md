# W-trade — running log

Branch `claude/w-trade` (from `origin/claude/integ` f7dc703). Migrations 0071–0089. Items W-01…W-07, W-09, W-13…W-15, W-18.
Design: `docs/areas/w-trade-design.md`. Report (at the end): `docs/areas/w-trade-report.md`.

## Restart recipe
1. `bash tools/local-supabase/setup-session.sh`, then export its last line.
   This image ships Chromium 1243 while Python Playwright 1.56 looks for 1194: the compat links
   `/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell` and `/opt/pw-browsers/chromium-1194/chrome-linux/*`
   point at the 1243 binaries (made once per container; `ls /opt/pw-browsers` to check).
2. `setsid nohup tools/local-supabase/start.sh > /tmp/start.log 2>&1 &` → wait for :54321, then
   `tools/local-supabase/start-payments.sh tools/local-supabase/payments.env.example` and `python3 tests/fixtures/make_fixtures.py`.
3. Journeys: `DB_NAME=drugbox_live APP_URL=http://localhost:54321/ python3 tests/journeys/run_business.py --out /tmp/jt --configs demo:en:1440,live:en:1440 --jobs 2 --files business_trade.py`.

## Log
- 2026-10-25: started; read the area reports and the marketplace code (0054, market.js, adapter AREA business: marketplace);
  design written (one model on `products` + `listing_lines`); baseline run of the market / payments / deals journeys.
