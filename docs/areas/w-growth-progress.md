# w-growth — running log (branch claude/w-growth, migrations 0100–0109)

Restart recipe: `bash tools/local-supabase/setup-session.sh` → eval its last line → `setsid nohup tools/local-supabase/start.sh &` →
`tools/local-supabase/start-payments.sh` → `python3 tests/fixtures/make_fixtures.py`. (setup-session now picks Playwright 1.63 when the
machine has chromium-1243 — the browsers changed under the old 1.56 pin.)

Baseline at f7dc703: parity vs web/reference/demo-approved.html already FAILS (the coordinator's integ CSS fix is not in the reference) — refreshed at the end.

## Design
- Channels = official groups (groups.official/channel_key, 4 seeded: news/jobs/regulatory/market). Posts only via the scheduler
  (channel_schedule → private.channel_publish), posts.as_drugbox shown as "Drugbox". Runner: public.growth_tick() — pg_cron
  'drugbox-growth-tick' every minute (migration + deploy script); locally functions-local.js calls the RPC every LOCAL_CRON_SECONDS.
- W-21 thera tags: private.thera_terms dictionary → posts.thera / products.thera by trigger; groups.thera set by Drugbox;
  feed_thera(), market_search_thera() (copy of market_search + one condition — keep in step with market_search at merge).
  'hospitals' left out: hospital tenders are not in the owner's list of trading parties → waiting on the owner.

## Log
- 0100 written; growth_channels.rls.sql 63/63; sweep 6× none; migration_check OK.
