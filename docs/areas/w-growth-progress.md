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
- 0101–0104 done: growth_members.rls.sql 95/95, growth_channels 63/63, sweep 6× none, migration_check OK (72). founder_apply_vip steps out of the member identity for its one companies update (companies_guard 0006 has no server bypass while auth.uid() is set). Sweep allowlists the six public_* read-only definer functions (0103) by name.
- UI: web/src/growth.js/.css (demo + all drawing), web/src/live/growth.js (live services), adapter block "AREA w-growth" (end of adapter.js), groups.js extension points.
- tests/journeys/community_growth.py J-COMMUNITY-W01…W05: demo EN 1440 / AR 1440 / EN 390 pass; live EN 1440 pass (W04 after routing the meeting host).
- Arabic labels rewritten in the interface's formal register (the existing i18n is MSA) with the trade's terms kept.
- Journeys: community_growth W01–W05, business_growth W01–W04, social_growth W01 — demo EN/AR × 1440/390 all pass; live EN 1440 all pass.
- J-BUSINESS-02/04/10 visitor steps pass live (sign-in page → "Browse the company directory"); the journey takes that way in instead of failing "not built".
- tools/scale/timings.py: feed_thera, market_search_thera, channel_posts, expert_sessions_list, expert_topic_demand, founder_badge, public_directory_page.
