# Drugbox — production code base (fresh start, identical to the approved demo)

## The one rule
**The app's interface is the approved demo — the same code, unchanged.**
Only the data layer changes: the demo keeps data in the browser; the app keeps it in a real database.
This is enforced, not hoped for: `tools/parity_check.py` fails the build if the interface differs from the demo by a single byte.

Why: the previous production code rewrote the demo pages in React. Every rewrite drifted a little and every new demo feature
had to be rewritten again, so the two versions drifted apart. Here the demo *is* the front end, so new demo features arrive in the app automatically.

## Layout
```
web/
  base/app.html          approved pages (from the demo)
  src/                   the 25 feature layers (build.py MODULES) + CSS + assets (current versions only);
                         snapshot.py / mobile_opt.py = the build's last step (phone optimisations + lite no-JS copy)
  build/build.py         builds web/dist/drugbox.html  (python3 web/build/build.py)
  build/live.py          live build → web/dist/live/ (index.html + cacheable js/ and media/)
  reference/demo-approved.html   the approved demo the build must match
  src/live/adapter.js    the data adapter (live build only)
supabase/
  migrations/0001_init.sql       fresh schema: core, feed, network, messages, notifications, marketplace,
                                 jobs + trust layer, groups, company hub (32 tables, RLS on all) — never re-run it (plain CREATE TABLE)
  migrations/0002_feed_paging.sql  keyset-paging indexes for the feed and comments
  migrations/0003_network.sql      suggest_people (bounded, by mutual connections), my_network_stats
  migrations/0004_messages.sql     read receipts (receiver-only, no editing), conversation functions, Realtime publication
  migrations/0005_messages_scale.sql  conversation_heads kept by triggers; index-friendly conversation and new-message reads
  migrations/0006_companies_live.sql  company guard (new companies start pending; verification/plan by Drugbox only), unclaimed pages,
                                   page profile, directory_companies(), company_sites_public(); guards trust server-side work only
  migrations/0007_deals.sql        deals + deal_events, deal_flow(), deal_create(), deal_act(), company_track_record(); changes only via the engine
  migrations/0008_company_listings.sql  listings, deal_members + deal_join, group confirmation → member orders, questionnaire → AVL
  migrations/0009_enquiries_id.sql  buy requests get an id automatically (inserts from the app failed); listing indexes
  migrations/0010_jobs_live.sql     job category, applicant count kept by the database, paging index
  migrations/0011_media.sql        videos bucket + folder rules (can_write_video), intro_video on profiles and companies
  migrations/0012_trust_live.sql   get_reviews_many (anonymity kept), open_candidates, my_interactions
  migrations/0013_groups_live.sql  group_members policies (were missing), member count, creator is admin, topic
  migrations/0014_uploads.sql      post-media (public) and message-media (private) buckets, post_media policies (were missing), message attachments
  migrations/0015_follows.sql      company_followers policies (were missing); one counter per table
  migrations/0016_documents.sql    private documents bucket, CV and verification read/write rules, cv_path, registry_path
  migrations/0017_moderation.sql   company_reports, notifications on verification decisions and published warnings
  migrations/0018_payments.sql     prices, orders, create/confirm/activate (confirm is server-only), InstaPay review, boost/featured
  migrations/0019_training.sql     training_courses (six seeded), course_enrollments, one counter
  migrations/0020_security_core.sql  code review 2026-10: profiles/products/connections guards, server-managed columns, grants & anon privacy
  migrations/0021_trust_hub_deals.sql  code review 2026-10: trust layer, company hub, deals engine, groups
  migrations/0022_integrity_perf.sql  code review 2026-10: FKs, notification dedupe, deals policy + indexes, lean directory RPC, counters, speed
  migrations/0023_payments_moderation_storage.sql  code review 2026-10: payments, moderation, storage buckets (+ Edge Functions)
  functions/                     payments-create, paymob-webhook, fawry-webhook (see functions/PAYMENTS.md)
  tests/_local_supabase_stub.sql the parts of Supabase the migrations need (auth.uid, storage.foldername… with Supabase's own definitions)
  tests/*.rls.sql, integrity_perf.sql   database security / integrity suites (each on a fresh database: stub + all migrations)
  tests/schema_sweep.sql         every line must say "none"
tools/parity_check.py            interface == demo, or the build fails
tools/migration_check.py         every migration can run twice and puts back every policy it creates
tools/local-supabase/            local stand-in for Supabase (PostgreSQL + PostgREST + auth/storage gateway, payment stand-ins) for tests
tests/run_all.py                 runs the suites and exits non-zero on any failure
tests/e2e/                       end-to-end tests against the local stack (settings in tests/e2e/_dx.py)
tests/demo/                      demo-build suites (legacy/ = older suites; legacy/retired/ = no longer run, see its README)
tests/fixtures/make_fixtures.py  makes the files the suites upload (WebM clips, photo, PDF)
tests/fixtures/make_demo_variants.py  the no-script viewer variants of the demo the lite suites open (csp_block, worst, sanitized)
docs/DATA-CONTRACT.md            every data list the interface reads → its table
vercel.json                      security and cache headers (template: live.py writes web/dist/live/vercel.json with the project's URL)
```

## Build and verify
```bash
python3 web/build/build.py                                    # → web/dist/drugbox.html (needs Pillow + Playwright/Chromium)
python3 tools/parity_check.py web/reference/demo-approved.html   # must print PARITY OK
python3 tests/run_all.py sql sweep                            # database suites + schema sweep, each on a fresh database
python3 tools/migration_check.py                              # migrations are re-runnable (lists the multi-policy blocks that are not)
```
The build is deterministic: two builds of the same sources give the same file. The lite snapshot (the read-only copy shown
by apps that block scripts) is rendered with a fixed date, a seeded random generator, reduced motion and no network, so the
parity check compares the whole file. `--ignore-snapshot` compares everything except it, if a different Chromium ever
renders it differently. The build writes `web/src/_static.html` only when the snapshot changed, and stops (writing nothing)
when Pillow or Playwright is missing or the snapshot fails.

Requirements: Python 3.11+ with `playwright` (+ `playwright install chromium`) and `pillow`; Node 20+; PostgreSQL 16;
PostgREST 12.2; Deno (payments); ffmpeg (test fixtures).

## Run the live app locally
```bash
tools/local-supabase/start.sh        # database drugbox_live on PostgreSQL :5433, PostgREST :3001, gateway → http://localhost:54321/
tools/local-supabase/start-payments.sh   # Edge Functions :54400 + Paymob/Fawry stand-in :54500 (local test values in payments.env.example)
python3 tests/fixtures/make_fixtures.py  # WebM clips, a photo and a PDF in /tmp/vids (DRUGBOX_FIXTURES)
python3 tests/run_all.py e2e         # every end-to-end suite; or one: python3 tests/e2e/b1_auth_test.py
```
Everything listens on 127.0.0.1 only and assumes a single-user machine. start.sh drops and recreates the database
(`DB_NAME`, default `drugbox_live`), builds the demo and the live app (without Realtime: `DRUGBOX_REALTIME=0`), and writes
its secret, logs and pid files to `RUN_DIR` (default /tmp, mode 600). Other settings: `PGHOST` `PGPORT` `GATEWAY_PORT`
`REST_PORT` `FN_PORT` `STORE_DIR` `SKIP_BUILD=1` `MIGRATIONS="file …"`. start-payments.sh signs the Supabase keys with the
running stack's secret and writes the effective settings to `$RUN_DIR/drugbox-fn.env`, which the e4 suites read.
The suites take `APP_URL`, `DB_NAME`, `PGHOST`/`PGPORT`, `DRUGBOX_FIXTURES`, `DRUGBOX_FN_ENV` from the environment.
```bash
python3 tests/e2e/b0_rtl_smoke_test.py # Arabic / right-to-left: every main page with live data, no console errors
python3 tests/e2e/b1_auth_test.py    # accounts, session, row-level security, no admin/verified self-promotion
python3 tests/e2e/b2_feed_test.py    # paging, post, react, comment, save, reload, delete + undo, row-level security, server-kept post columns
python3 tests/e2e/b3_network_test.py # two people — request, notify, accept, decline, suggestions, numbers, forged connections refused
python3 tests/e2e/b4_messages_test.py # two people — send, live delivery, badge, read receipts, live reply, second render, row-level security
python3 tests/e2e/b2b_profile_post_test.py # post from your own profile (saved, stay on profile), greeting for one-word names
python3 tests/demo/profile_composer_test.py [en|ar]  # demo build: composer on your own profile only
python3 tests/e2e/c1_companies_test.py # directory, unclaimed pages, Arabic search, sites, create wizard, edits, verification, guards
python3 tests/e2e/video_live_test.py   # upload, watch from Storage, personal video, Storage security, remove
python3 tests/demo/videos_test.py [en|ar]  # demo build
python3 tests/e2e/e3_training_test.py   # courses, enrollment kept after reload, one counter, rules
python3 tests/e2e/e4b_checkout_test.py  # the whole checkout in the browser (start-payments.sh first)
python3 tests/e2e/e4_payments_test.py   # through the real functions: forged / replayed / swapped / wrong-amount callbacks, InstaPay review
python3 tests/e2e/e2_review_test.py     # review queues, decisions + notifications, short-lived document links, non-admins blocked
python3 tests/e2e/e1b_documents_test.py # CV, verification documents, warning evidence (real dialog), who can read each
python3 tests/e2e/e1a_uploads_test.py   # post photo+PDF, private message files with signed links, storage rules
python3 tests/e2e/e1a_follow_test.py    # follow/unfollow, one counter
python3 tests/e2e/d3_groups_test.py     # create, join (card button), detail, leave, roles, private groups, delete
python3 tests/e2e/d2b_trust_test.py     # candidates, reviews (anonymous / interaction rule), references + reply, lists, warnings wait
python3 tests/e2e/d2a_jobs_test.py      # post as company, real cards, filters, apply once, save after a second render, row-level security
python3 tests/e2e/d1_market_test.py     # real supply/demand cards (newest first), contact routing, publish, no free boost, row-level security
python3 tests/e2e/c3_listings_test.py  # surplus, dossier, group buying → member orders, approved list, compare quotes
python3 tests/e2e/c2_deals_test.py     # two companies — RFQ → quote → accept → ship → receive → rate, refusals, expiry, track record
```
Demo suites open `DEMO_FILE` (default /tmp/drugbox_brand.html — copy web/dist/drugbox.html there, or set it); the lite suites
also need `python3 tests/fixtures/make_demo_variants.py` (`DEMO_VARIANTS`, default /tmp) and run on the browsers in
`DX_ENGINES` (default webkit,chromium; `tests/run_all.py legacy` sets both). Speed: `legacy/stress.py` (DEMO_FILE) vs
`legacy/stress_base.py` (BASE_FILE) side by side.
Every suite prints `N / N` and exits 1 when a check fails. Checks marked in the code with a finding number (F-01, F-03, F-08,
F-09, F-115) fail on a database without migrations 0020–0023 — they are the code review's exploits, kept as tests.

## Architecture for 100,000 users
- **Front end:** the demo interface, served as static files from a CDN (Vercel / Cloudflare) — no server work per page view.
- **Data adapter (`web/src/live/adapter.js`):** replaces the demo's in-browser lists with paged API reads (20 items per page, cursor-based),
  keeps the same shapes listed in `docs/DATA-CONTRACT.md`, and sends every write through the database's permission rules.
- **Database:** Supabase PostgreSQL with row-level security on every table, indexes on every foreign key and search column,
  counters maintained by triggers, connection pooling (Supavisor, port 6543).
- **Live features:** Supabase Realtime for messages and notifications; Storage (CDN) for avatars, post images and private documents.
- **Protection:** rate limiting per user (Upstash Redis), verification and document review only by Drugbox admins (enforced in the database).

## Roadmap
| Phase | Scope | Status |
|---|---|---|
| A | Repository; interface identical to the demo (proven); fresh database 0001 with security tests; data contract | ✅ done |
| B1 | Real accounts: sign up, sign in, sign out, session kept on reload; the signed-in person's profile from the database | ✅ done — 16/16 end-to-end |
| B2 | Feed: posts, reactions, comments, saved — 20 at a time (keyset paging); writes are instant and undone if the database refuses; delete keeps the interface's Undo | ✅ done — 16/16 end-to-end; page read < 1 ms at 200,000 posts |
| B3 | Network: requests, accept/decline, suggestions by mutual connections, real network numbers; notifications from the database (read, mark all, clear with Undo), badges. People get local numeric ids in the interface (it writes ids unquoted into buttons) — the adapter maps them to database UUIDs | ✅ done — 18/18 end-to-end with two people in two browsers; suggestions 48 ms at 100,000 members |
| B4 | Messages: real conversations in the approved page (its own thread row and bubbles are the templates), send, read receipts, unread badge, Message from any profile; no demo filler or simulated replies. Live updates: Supabase Realtime triggers the same tested code path as a safety-net timer (5 s on Messages, 20 s elsewhere, paused when the tab is hidden) | ✅ done — 19/19 end-to-end with two people; at 100,000 messages: list 1.7 ms, open 4.5 ms, new-message check 1.7 ms |
| C1 | Companies: directory from the database (incl. unclaimed pages from public lists), Arabic ingredient search, company page sites/certificates, the real create wizard, my companies, page edits, verification requests. Data hooks added to the demo sources (inert in the demo — its full test suite still passes) | ✅ done — 15/15 end-to-end |
| C2 | Deals engine in the database: the demo's 7 flows (quote, service, surplus, questionnaire, dossier, job, group) enforced by deal_create/deal_act — out-of-turn steps, wrong side, expired offers, self-dealing and direct edits are refused; the other side is notified; track record (orders, on-time, rating, response time) from the database | ✅ done — engine 18/18 in SQL, 16/16 end-to-end with two companies |
| C3 | Company listings (surplus, dossiers) through the real dialogs; group buying on the deals engine — join via deal_join, target reached and member orders created in the database; approved suppliers (incl. from an approved questionnaire); quote comparison across suppliers | ✅ done — 17/17 in SQL, 14/14 end-to-end with three companies |
| D1 | Marketplace: supply and demand cards from the database using the approved page's own cards as templates; Contact/Quote open a conversation with the real person; demo sponsors hidden; ticker from real listings; publishing from the listing wizard saves to the database (one inert hook in the approved page) | ✅ done — 14/14 end-to-end |
| D2a | Jobs: real job cards (the approved card as template, hiring cards only — candidate cards untouched), filters by category/level, apply (once only, with note; applicant count by the database), save, post a job as your company (the demo's fixed "Quadra Pharm" replaced) | ✅ done — 14/14 end-to-end with an employer and a candidate |
| Video | Intro videos — company video (owners/admins, ≤ 3 min, ≤ 100 MB) and a personal "about me" video (≤ 90 s, ≤ 50 MB) on the profile and candidate cards. Poster frame only until Play (pages stay light). Demo: IndexedDB; live: Supabase Storage bucket `videos` (anyone watches; uploads only into your own folder / your company's folder; size and type limits enforced by Storage). Also fixed: opening the profile of someone not seen yet showed your own profile | ✅ done — demo 15/15 (en+ar), live 14/14 |
| D2b | Jobs trust layer through the approved code's own store (6 inert hooks): real open-to-work candidate cards (Contact opens a conversation; intro-video chip), reviews (anonymous allowed for employers; only after a real interaction), honour references (only by a company the person lists in their experience) with right of reply, private white/black lists. Warning references wait for evidence uploads | ✅ done — 14/14 end-to-end with three people |
| D3 | Groups: real group cards (the approved card as template), the real group in the detail panel (admin tools for admins), join/leave (incl. the card button), create and delete through the windows. Fixed: group_members had RLS on and no policy — nobody could join | ✅ done — 17/17 end-to-end |
| E1a | Uploads: post photos and files (public bucket), message photos and files (private bucket, signed links valid 1 h, only the two people). Text-less photo posts allowed. Company Follow stored. Schema sweep fixed two more tables with RLS on and no policy (post_media, company_followers) and two double counters | ✅ done — 12/12 uploads, 5/5 follow |
| E1b | Private documents (bucket `documents`, signed links): CV with applications (applicant + that job's employer), verification documents from the real dialog (company + Drugbox; fixed: the dialog sent nothing for real companies), evidence for warning references (author + moderators) — warnings are submitted for review | ✅ done — 13/13 end-to-end with five people |
| E2 | Admin → Review (new section in the demo's admin panel, swappable data source): verification requests with documents (approve/reject with a reason; owner notified), warning references with evidence (publish/reject; the person notified with right of reply), site certificates (mark checked → level 3), company reports filed from the real dialog. Only the Drugbox team can decide | ✅ done — 14/14 end-to-end |
| E3 | Training: courses and enrollments from the database (approved course card as template), six courses seeded, Drugbox manages courses, enrollment stored and private, one counter | ✅ done — 10/10 |
| E4a | Payments server side: card + Vodafone Cash/wallets (Paymob Unified Checkout), Fawry reference numbers (FawryPay), InstaPay transfer + receipt reviewed by Drugbox; prices and VAT from the database; activation only after a verified signature and matching amount; see supabase/functions/PAYMENTS.md | ✅ done — 20/20 through the real functions |
| E4b | Checkout in the app: the VIP and boost windows offer card, Vodafone Cash & wallets, Fawry and InstaPay (demo shows the choice; the demo flow is unchanged). Live: Paymob page and back ("Payment received"), Fawry reference screen, InstaPay transfer number + receipt; Admin → Review → Payments to confirm transfers | ✅ done — 14/14 in the browser |
| Review | Code review October 2026 (docs/CODE-REVIEW-2026-10.md): fixes in migrations 0020–0023, the adapter, the local stack, the build and the test suites | ✅ done |
| E5 | Real Supabase project, load test at 100k users, launch checklist (below) | |


Every phase ends with: parity check, database security tests, the demo's own test suites, speed comparison.

## Live build switches
- `DRUGBOX_REALTIME=0` builds without Supabase Realtime (timer only) — start.sh uses it for the local stack, which has no Realtime server.
  On Supabase, leave it on; Realtime events and the timer run the same code (`tick`), which the tests exercise.
- live.py refuses a key whose JWT role is not `anon` (never the service key in the browser), a non-https URL (except
  localhost), and a demo build older than its sources (`DRUGBOX_ALLOW_STALE=1` to override). The splash video becomes a
  separate content-hashed file (`media/`), so the page itself is small and the video is cached.

## Known follow-ups
- Videos the browser cannot read (e.g. iPhone HEVC on some Windows PCs) are refused with "try MP4 (H.264)"; server-side transcoding would accept them — a launch-stage option.
- Local tests use WebM: the open-source Chromium used for testing cannot decode H.264 (Chrome, Safari and Edge can).
- Every migration ends with `notify pgrst, 'reload schema'` (PostgREST must see new tables/relationships at once).
- Migrations that create several policies in one `do … exception when duplicate_object` block do not put back a single missing
  policy when re-run (`python3 tools/migration_check.py` lists them). New migrations: one block per policy, or `drop policy if exists` + `create policy`.
- The Realtime subscription itself can only be exercised on Supabase (staging); locally the same update path runs on the timer.
- `suggest_people`: 48 ms at 100,000 members / 200 connections — fine for opening the network page; can be precomputed nightly if it grows.

## Launch notes (E5)
- **Auth (Supabase dashboard):** keep "Confirm email" on — sign-up for an address that already has an account then answers
  like a new one (the local gateway does the same), so sign-up cannot be used to find out who is registered; keep the Auth
  rate limits on (sign-up / token). The password minimum is 8 in the app; set the same in Auth settings.
- **API:** keep Max rows at 1000 (the local PostgREST uses the same `db-max-rows`); the role statement timeouts (anon 3 s,
  authenticated 8 s) are mirrored in the test stub.
- **Pooler:** nothing in the SQL needs a session (no session `SET`, advisory locks, temp tables, `LISTEN` or `PREPARE`), so
  transaction-mode pooling (Supavisor, port 6543) is safe for extra clients (k6, scripts) — with prepared statements off
  (`prepareThreshold=0` / PostgREST `db-prepared-statements = false`). PostgREST and Realtime stay on the direct connection
  (prepared statements, `notify pgrst` schema reloads, the replication slot). After the first production migration, check that
  the schema reload happened (a new column is visible through the API at once).
- **Headers:** `vercel.json` sends a Content-Security-Policy (scripts are inline in the approved page, so `'unsafe-inline'`
  is needed for scripts; no `eval`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, Referrer-Policy,
  Permissions-Policy and HSTS, plus caching: `index.html` no-cache, `js/` and `media/` (content-hashed) immutable.
  Replace `YOUR-PROJECT` in it with the Supabase project reference. The local gateway sends the same headers (without HSTS).
- **supabase-js:** the vendored `web/src/vendor/supabase-2.45.4.min.js` is byte-identical to the npm release; its bundled
  auth-js 2.65.0 has one low advisory (GHSA-8r88-6cj9-9fh5, `auth.admin.*` path building — service-role only, not used by the
  browser build). Upgrade to the current 2.x UMD build before launch and re-run b1, b4 and e4b.

## Data hooks in the demo sources (inert in the demo)
- `store()` in directory.js, hub-data.js, deals.js: `window.dxStoreHook(key, value)` answers reads/writes in the live app.
- `companies()` in directory.js: `window.dxLiveCompanies` replaces the demo's company list.
- `sitesOf()` in hub-data.js: `window.dxLiveSites[slug]` replaces a company's demo sites.
- `surplus()`, `dossiers()`, `groups()` in directory3.js: `window.dxLiveListings` hides the demo's fixed listings.
- Publish listing (approved marketplace page): `window.dxLiveHook('listing', d)` saves the listing in the live app.
- Kit store (`DBK.store`) get/set: `window.dxKitHook(op, key, value)` — jobs trust data in the live app; `window.dxLiveTrust` hides sample reviews/references and supplies the real company/name; `window.dxJxPaint` re-paints trust boxes.
- `track()` in hub-data.js: `window.dxLiveTrack(slug)` returns the track record from the database.
