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
- SQL: 31/31 suites (+ growth_channels 63, growth_members 96) after: explicit FK actions, anon empty reads, 0100–0104 in launch_readiness, the visitor functions named in security_core F-27, specialty_answer no longer writes profiles (the member's own row update does).
- Verifier round 1: 1 critical (meeting link leaked when no expert member: NULL in expert_session_link), 6 major (restored channel post lost as_drugbox;
  channel posts leaked as the admin (Saved, notices, former admin's own-post rights); a founder invitation reopened after the founder's account was
  deleted; visitors got address/location/website; SEO meta JS-only; founder dialog twice), 9 minor — all fixed, regression checks added
  (growth_channels 67/67, growth_members 101/101 on a fresh DB). SEO: /c/<slug> server page (deploy/share/company.js → live api/company.js,
  vercel.json rewrite, gateway route); live share links use /c/<slug>.
- Verifier round 2: 3 major (channel posts deleted with the publishing admin's account; the admin named by the API author embed and
  told of removals; visitors saw a verified company as "Not verified"), 4 minor (browser dictionary, ended sessions under Upcoming,
  expert member for good / answers on hidden questions / restore lost tags, Arabic leftovers). Fixed in 0105 (Drugbox posts have no
  member author: posts.user_id null + as_drugbox, constraint posts_author_or_drugbox, channel_schedule.published_by; notices to nobody
  dropped; registry «•••» for visitors; ماشية → الماشية/للماشية; expert_sessions_list.ended; expert member set per save; expert answers
  only visible questions until a week after) and the interface (SYS_UID author, Arabic channel names via i18n, «نص المنشور», import
  label, one banner for non-members). growth_channels 75/75, growth_members 107/107, SQL 31/31 + sweep, migration_check OK (73).
  Growth journeys: demo EN/AR × 1440/390 + live EN/AR all pass (two cross-run races in the journeys fixed: W04 counts this session's
  notice; W02 live runs one config at a time when two share a segment quota). Build deterministic 867c11d19241ddff, reference refreshed.
