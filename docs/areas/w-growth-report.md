# Area report — w-growth (growth plan and the owner's pending decisions)

Branch `claude/w-growth` (from `claude/integ` f7dc703) · migrations **0100–0106** · running log `docs/areas/w-growth-progress.md`.
Interface: `web/src/growth.js` + `growth.css` (demo behaviour and all drawing), live services `web/src/live/growth.js`, one block
"AREA w-growth" at the end of `web/src/live/adapter.js`, three small hooks in `web/src/groups.js`.

## 1. Items

| Item | Status | Journeys (demo EN/AR × 1440/390 · live) | Where |
|---|---|---|---|
| W-41 official Drugbox channels + content scheduler | **closed** | J-COMMUNITY-W01, W02 — pass everywhere | 0100; growth.js §1; Admin → Channels |
| W-21 therapeutic areas: channel-post tags, Home and Marketplace filters | **closed** (hospitals: waiting on the owner) | J-COMMUNITY-W03, J-BUSINESS-W01 — pass everywhere | 0100 §3; growth.js §2 |
| W-42 founding members | **closed** | J-BUSINESS-W02 — pass everywhere | 0101; Admin → Founders; `#/founder/<code>` |
| W-43 Ask an expert | **closed** | J-COMMUNITY-W04 — pass everywhere (reminders live only: server runner) | 0102; Training → Ask an expert; Admin → Expert sessions |
| Directory import (B-01 extended) + claims | **closed** — the owner's real lists are **waiting on the owner** | J-BUSINESS-W03 — pass everywhere | Admin → Directory import (CSV, dry run first) over `admin_import_companies` (0052) |
| Decision 1: public company pages for visitors + SEO basics | **closed** (server-rendered meta for crawlers: see §6) | J-BUSINESS-W04 — pass everywhere; J-BUSINESS-02 / 04 / 10 visitor steps now pass live | 0103; the sign-in page's "Browse the company directory"; `#/companies/<slug>` |
| Decision 7: the six courses in Arabic (free) | **closed** (content and prices: waiting on the owner) | J-COMMUNITY-W05 — pass everywhere | 0104 |
| Decision 9: one-time specialty question | **closed** | J-SOCIAL-W01 — pass everywhere | 0104 |

Independent verification: see §3.

### What each does
- **Channels (W-41).** Four official groups — Drugbox News, Jobs, Regulatory, Market (`groups.official`, `channel_key`, Arabic name and
  description) — created by 0100 with **no members and no posts** (no fake members). Nobody posts into a channel from the browser, not
  even a Drugbox admin: posts come only from the scheduler (`channel_schedule` → `private.channel_publish`), written by the server as
  `posts.as_drugbox`, shown as **"Drugbox ✓ Official"** with the Drugbox logo, never a member's name or profile link; the members'
  notice names no person. Nobody can be a channel's admin; a group's own admins cannot make their group official or tag it.
  **Admin → Channels**: the W-41 content plan as ready templates (daily «مطلوب النهارده» 21:00; weekly: regulatory bulletin Sun, how to
  read a file ad Mon, agency market Tue, practical guide Wed, shortages Thu 21:30, jobs of the week Sun 20:00 — all Cairo time),
  "Use →" fills the channel, the text (Arabic in the Arabic interface) and the next slot; save a draft, schedule (date + time in
  **Africa/Cairo**), edit, cancel, publish now.
  **Runner:** `public.growth_tick()` (service role only, plain SQL) publishes what is due and sends the expert reminders; **pg_cron**
  `drugbox-growth-tick` every minute (0100 schedules it when pg_cron is on; `deploy/supabase_deploy.sh` schedules it too). Locally
  `tools/local-supabase/functions-local.js` calls it every `LOCAL_CRON_SECONDS`. No Edge Function needed.
- **Therapeutic areas (W-21).** biologics, veterinary, agriculture, GLP-1, oncology, growth hormone, fertility, insulin. A small
  dictionary (`private.thera_terms`, EN + AR words) tags posts and marketplace products by their own text (triggers — never the
  browser); a Drugbox channel post also carries the tags the admin chose. Home: "🧬 Therapeutic area" under the composer (live: the
  server finds every post about it, GIN index); Marketplace: a "Therapeutic area" section in the approved filter column (on phones in
  "⚙ Filters"), live through `market_search_thera()` (market_search's twin with one more condition — **keep the two in step at merge**).
- **Founding members (W-42).** Segments with quotas (manufacturers 8, toll / brand owners 10, agencies 15, distributors 15,
  registration-file owners 5, API suppliers 5, packaging 10, regulatory consultants 5 — **no pharmacy / "Rx traders" segment**).
  Admin → Founders: quotas, "+ New invitation" (segment, who it is for, days) → the code `DBX-XXXX-XXXX-XXXX-XXXX-XXXX` (100 bits)
  and its link are shown **once**; only the SHA-256 is stored; open / used / revoked / expired list, Revoke. The invitee opens
  `#/founder/<code>`, signs in or up, sees what it is for and **chooses** to join; the 3 VIP months go to a company page they run
  (owner/admin, once, within a year) — now or later from their profile. Founder badge "🏅 Founding member" on the profile. Ten wrong
  codes in an hour block further tries (per account).
- **Ask an expert (W-43).** Training → "🎤 Ask an expert": upcoming sessions (expert, Cairo time, seats left, Register / Cancel,
  "▶ Join the session"), topics to request (file purchase, NFSA, agency contracts, toll card, pricing, importing, cold chain, the
  authority's labs / track & trace, choosing a factory, other with a note) with how many asked, past sessions with their Q&A.
  Admin → Expert sessions: requests per topic with notes, schedule / edit / cancel / mark done, answer questions. The members who asked
  are told when a session is set; the registered get reminders a day and an hour before (`growth_tick`); the meeting link is given only
  to the registered, from an hour before until the end; questions only from the registered; answers by Drugbox or the expert.
- **Directory import.** Admin → Directory import: a CSV (UTF-8; name, sectors, source required) is read in the browser, **checked
  first** (nothing written: would add / duplicates / invalid with the reason per row), then imported as unclaimed `public_list` pages
  through 0052's `admin_import_companies` (same validation, dedupe by registry number or normalised EN/AR name). A sample CSV can be
  downloaded. The imported card shows the approved "Unclaimed" mark; the company claims it with its commercial registry document →
  Admin → Review → Claims (0052).
- **Visitors (decision 1).** The sign-in page offers "🏭 Browse the company directory without signing in"; a shared
  `#/companies/<slug>` link opens that page directly. A visitor sees the directory and company pages (name, about, sectors, products,
  sites with capacity, certificates as checked or not, verified badge, unclaimed mark) through `public_*` functions (0103) that return
  **no phone, e-mail, WhatsApp, registry number, team or documents**; Contact / Team / Follow / Message / quotes / any other page ask
  the visitor to sign in; a visitor bar offers All companies / Sign in / Join. The open company page sets the page title, description,
  canonical and Open Graph tags.
- **Courses (decision 7).** `training_courses.title_ar / description_ar` for the six courses; the Arabic interface shows them; they
  stay free.
- **Specialty (decision 9).** Accounts made **before 0104 ran** whose headline is exactly "Regulatory Affairs" are asked once:
  "Is this still your specialty?" (the sign-up list + "Other…"); Save records the answer (`member_prompts`), "Ask me later" does not.
  New accounts chose their specialty themselves and are not asked.

## 2. Migrations (0100–0106)
| Migration | Content | Test |
|---|---|---|
| 0100_official_channels | groups.official/channel_key/name_ar/description_ar/thera + guards; posts.as_drugbox/thera; products.thera; thera dictionary; channel_templates, channel_schedule + RPCs; feed_thera, market_search_thera; growth_tick + pg_cron | growth_channels.rls.sql |
| 0101_founding_members | founder_segments, founder_invites (hash), founder_members, attempts; create/revoke/quota/overview/list/peek/redeem/apply_vip/my_founder | growth_members.rls.sql §1 |
| 0102_expert_sessions | expert_topics/requests/sessions/registrations/questions + RPCs; reminders in growth_tick | growth_members.rls.sql §2 |
| 0103_public_company_pages | public_directory_page, public_company, public_company_sites/certs, public_sites_for, public_company_meta (anon, public fields only) | growth_members.rls.sql §3 |
| 0104_courses_ar_specialty | training_courses.title_ar/description_ar (6 courses); member_prompts; specialty_prompt_due/answer | growth_members.rls.sql §4 |
| 0105_growth_fixes | the second verifier round: channel posts without a member author (posts.user_id null + as_drugbox, channel_schedule.published_by), notices to nobody dropped, admin_delete/restore_post keep a Drugbox post Drugbox's with its tags, visitors' registry «•••», dictionary (ماشية), expert sessions (ended, expert member, answer limits) | growth_channels 75/75, growth_members 107/107 |
| 0106_growth_fixes_2 | the third verifier round: a Drugbox post is removed by Drugbox admins only (trigger, whatever the path), reports on channel posts go to Admin → Review, a restored post relinks to its plan, admin_posts names Drugbox posts, «العلاج الكيماوي» | growth_channels 80/80 |

Every table, sequence and function grants its own privileges; every table has RLS with policies; every migration ends with
`notify pgrst`; re-run safe (`tools/migration_check.py` OK); `schema_sweep.sql` six × none.

## 3. Independent verification
Two rounds by an independent verifier agent (it read the code and attacked the running stack through the API and the browser, EN/AR,
1440/390; it edited no code).
- **Round 1** — 1 critical (the meeting link was given to every member when a session had no expert member: a NULL in
  `expert_session_link`), 6 major (a restored channel post lost `as_drugbox`; channel posts showed the publishing admin on Saved and in
  notices and kept the former admin's own-post rights; a founder invitation reopened after the founder's account was deleted; visitors
  received the address / location / website; the SEO tags were set only by script; the founder dialog showed twice), 9 minor (Cairo time
  of "Publish now", registration after the start, moving a session into the past, dictionary false positives, the Home filter's paging,
  Arabic leftovers …). All fixed, each with a regression check.
- **Round 2** — the 14 round-1 items confirmed fixed except two partial ones, plus 3 major and 4 minor new findings:
  (1) deleting the publishing admin's account deleted Drugbox's channel posts (cascade); (2) the API embed of a channel post's author still
  named the admin, and the admin got "removed / restored your post" notices; (3) a verified company read "Not verified" to visitors
  (registry stripped); (4) the browser's dictionary still had `hmg` / `كيماوي`, and «الأمور ماشية» was tagged veterinary; (5) a session past
  its end stayed under Upcoming as "Happening now"; (6) an expert member could not be removed and could answer hidden questions for good;
  restore lost the tags; (7) Arabic leftovers (channel names and descriptions, the «انشر» column header, the import label, two banners for
  non-members). **All fixed in 0105 and the interface** — a Drugbox post now has no member author at all, so neither a deletion nor an
  embed can reach an admin; regression checks in `growth_channels.rls.sql` §6 and `growth_members.rls.sql` (marked 0105).
- **Round 3** (on 0105) — the 7 round-2 items: 5 fixed, 2 partly (the channel's About tab and the channel notice still English in Arabic;
  the Admin could not keep an expert member set through the API). New: 1 major (reposting a Drugbox post credited it to the member who
  reposted), 6 minor (Admin → Posts showed Drugbox posts as "Member"; reports on channel posts reached nobody; a moderator could remove a
  Drugbox post through `admin_delete_post`; a restored post lost its plan link; «العلاج الكيماوي» no longer tagged; the notices-to-nobody
  trigger — kept: it is not callable by members and only guards notices whose post has no author). Fixed in 0106 and the interface,
  checks added (`growth_channels` 80/80, W01 now reposts a Drugbox post and checks it is credited to Drugbox). It confirmed no security
  issue in the re-created functions and nothing broken by authorless posts (feed, saved, comments, likes, mentions, reposts, search,
  export, notifications). Its process note: 0100 was edited in place before any deployment (no ledger has it) — later changes went into
  0105 / 0106.
- **Verdict:** every item's journeys pass on the demo (EN/AR × 1440/390) and live (EN/AR 1440); the remaining verifier findings are fixed
  and covered by checks. A fourth round was not run (the shared limits) — the 0106 changes are small and each has its own check.

## 4. Interface changes for the owner's approval (EN + AR, 1440 + 390)
- **Groups:** four official channel cards with "✓ Drugbox official" (priority-badge slot) and an "OFFICIAL" tag; inside a channel the
  note "✓ Official Drugbox channel — only Drugbox posts here; you can comment and react", no composer; a Drugbox post shows the Drugbox
  logo, "Drugbox ✓ Official", "Official Drugbox channel" and its therapeutic tags (chips under the text).
- **Home:** "🧬 Therapeutic area" select under the composer; empty result line.
- **Marketplace:** a "Therapeutic area" section at the top of the filter column (phones: inside "⚙ Filters").
- **Admin:** four new tabs — 📣 Channels, 🏅 Founders, 🎤 Expert sessions, 📥 Directory import (admin-page-hdr / admin-section /
  admin-table look).
- **Training:** "🎤 Ask an expert" button next to "My courses", and its page (upcoming, request a topic, past Q&A).
- **Profile:** "🏅 Founding member" badge next to the name; for the founder, "🎁 You have 3 VIP months…" line with "Choose a company".
- **Invitation dialog** (after opening a founder link); **specialty question dialog** (old accounts).
- **Sign-in page:** "🏭 Browse the company directory without signing in" link; the **visitor bar** on top of the directory (All
  companies / Sign in / Join Drugbox); for visitors the member navigation is hidden.
- **Arabic:** new labels in the interface's own (formal) register with the trade's words for the new things — «مطلوب النهارده»،
  «نواقص الأسبوع»، سوق الوكالات، ملف تسجيل، التصنيع لدى الغير; the six course titles in Arabic; the channels' Arabic names and descriptions («Drugbox أخبار»، «Drugbox وظائف»، «Drugbox تسجيل ورقابة»، «Drugbox السوق»).

## 5. Suites (final head; the 150 journeys + crawler on the build before the last two interface commits, re-run where touched)
- SQL: **31 / 31** suites (each on a fresh database: stub + 0001–0106) incl. growth_channels 80/80, growth_members 107/107;
  schema sweep **6 × none**; `tools/migration_check.py` **OK (74 migrations)**.
- Build: deterministic (two builds, same sha256); `web/reference/demo-approved.html` refreshed — **PARITY OK**.
- Demo + legacy: **30 / 30** suites. Speed A/B against the base branch's build (f7dc703, 3 rounds): median page switch **7.0 ms vs 6.9 ms**
  (within noise) — PASS.
- e2e: **25 / 25** — `p1_no_sample_content_test` failed once (38/39: the Jobs "Reach N pharma professionals" count raced accounts other
  agents created at the same moment) and passes 39/39 re-run alone.
- Journeys, all **160** (150 + the 10 growth ones), demo EN 1440 / AR 1440 / EN 390 + live EN 1440 (report-only): **158 pass, 2 fail —
  both fail on the base branch too**:
  - J-SOCIAL-49 (demo): "impr differ between Home (16909) and Network (2840)" — same failure on the f7dc703 build.
  - J-COMMUNITY-30 (live): `NameError: name 'f' is not defined` — `tests/journeys/community_trust.py` line 24 has the statements that
    create `s` and `f` inside a `#` comment (file unchanged by this area).
  - Fixed here after the first run: J-COMMUNITY-35…39 in Arabic (the six courses now show their Arabic titles — the journeys look the
    card up by its shown title; the course search also matches the Arabic title). J-BUSINESS-01 live failed once (18 of 20 companies via
    Show more while another run was adding companies) and passes alone.
  - The 10 growth journeys also pass on AR 390 and live AR 1440.
- Dead-end crawler: CRAWL_RESULT

## 6. Open problems / waiting on the owner
- **Hospitals (W-21 "مستشفيات"):** left out — hospital tenders are not among the trading parties the owner listed; one line in
  `private.thera_terms` + the list in growth.js adds it if the owner says so.
- **Directory import:** the owner's official lists (CSV) — tested with a realistic sample written here.
- **Founders:** the quotas are a first proposal from the study minus the Rx segment — confirm.
- **Courses:** content, instructors and prices (they stay free).
- **SEO:** `/c/<slug>` is served by a small function (`deploy/share/company.js` → `api/company.js` in the live build, rewrite in
  `deploy/vercel.json`; the local gateway serves it the same way) with the title, description, canonical and Open Graph tags, then
  opens the app; live share links use it. **Check on the Vercel preview** that the function deploys (it could not be run on Vercel
  from here). A sitemap of all company pages is not built (waiting on the owner: whether every unclaimed page should be indexed).
- **Speed (100k seed, `tools/scale/timings.py`):** the new queries are 0.04–20 ms (Home filter 0.4 ms after a partial index;
  market_search_thera 7 ms; public_directory_page 12–20 ms). One existing query, `jobs_search_q` (Jobs area), measured 70 ms for
  member1 in one run while other tests ran on the machine (its own area reported 35 ms) — not changed here.
- Merge notes: `market_search_thera` mirrors `market_search` (w-trade may change it); `notify_group_post` (0061) was re-created
  with the Drugbox sender; `private.can_post_in_group` (0061) now refuses official channels; the schema sweep and
  `security_core.rls.sql` F-27 name the six `public_*` functions; `launch_readiness.rls.sql` re-applies 0100–0104;
  `tests/journeys/business_directory.py` J-02/J-04 visitor steps enter through the sign-in page's directory link.
  `web/src/i18n.js`: an official channel's card title and description are translated (the SKIP list skips only other groups' cards).
  `posts.user_id` is now nullable (only for `as_drugbox` posts — constraint `posts_author_or_drugbox`): code elsewhere that reads a post's
  author must allow none (all suites, the 150 journeys and the crawler were run on it).
