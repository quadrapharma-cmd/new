# Drugbox — instructions for Claude Code

Drugbox is a B2B network for the Egyptian/Arab pharmaceutical industry: people, companies, deals, marketplace,
jobs (with a trust layer), groups, training, messages, uploads, moderation and payments.
Owner: Dr. Haytham Dweedar. **He writes in Egyptian Arabic — answer in Egyptian Arabic**, direct and action-first.

## The one architectural rule
**The approved demo is the interface.** The live app is the *same* HTML/JS with a data adapter that swaps where data
comes from. Never rewrite or restyle a page for the live app.

- Demo (standalone HTML, sample data in the browser): `web/base/app.html` + layers in `web/src/*.js|css`
  → `python3 web/build/build.py` → `web/dist/drugbox.html` (a single file the owner opens offline — he wants this file
  delivered whenever the interface changes).
- Live app: the same build + `web/src/live/adapter.js` (Supabase) → `python3 web/build/live.py` → `web/dist/live/`
  (`index.html` + `js/`). Needs `DRUGBOX_SUPABASE_URL` and `DRUGBOX_SUPABASE_ANON_KEY`.
- Parity: `python3 tools/parity_check.py web/reference/demo-approved.html web/dist/drugbox.html` must say PARITY OK.
  When an interface change is intended and tested, copy `web/dist/drugbox.html` over `web/reference/demo-approved.html`.

### How the adapter connects (keep using these patterns)
- Inert hooks in the demo code, e.g. `window.dxStoreHook(key, value)` (company hub stores), `window.dxKitHook(op, key, value)`
  (`DBK.store`: jobReviews, jobRefs, jobLists, jobInteractions, groupsJoined), `window.dxLiveHook('listing', d)`,
  `window.dxLiveTrust`, `window.dxJxPaint`. A hook does nothing in the demo — check with the demo suites.
- Swappable services with a demo implementation in the layer and a live one in the adapter:
  `window.dxMedia` (videos), `window.dxModeration` (Admin → Review), `window.dxPay` (checkout).
- **Pages that redefine their functions on render** (messages `mxComplete`, jobs `jxInit/jxComplete`, marketplace
  `openBoostModal`): wrap again *after each render* (`dxCore.onRender` or inside the render wrapper), guarded by a
  `__live`/`__pay` flag. Wrapping once at load silently stops working.
- Cards are filled from the approved page's own first card as a template (`el(tpl)`), never new markup.
  Some approved buttons are bound per element at init — live cards need a delegated capture handler (groups Join).
- People get small local numeric ids (1001+) mapped to UUIDs (`aid()`/`uuidOf()`), because the interface writes ids
  unquoted and `parseInt`s them. `gotoProfile` fetches unseen people first (otherwise `U()` falls back to "me").

## Database (supabase/migrations 0001–0024)
- Every migration ends with `notify pgrst, 'reload schema';`.
- After any migration run `psql -f supabase/tests/schema_sweep.sql` — it must print three "none" lines:
  **RLS on with no policy** (made five features unusable in production: group members, post media, company followers…),
  RLS off, and **two counter triggers on one table** (double counts).
- One counter trigger per table (+1/−1). Server-only functions are `security definer` and revoked from
  public/anon/authenticated (`confirm_payment`, `activate_order`, `set_order_provider_ref`).
- Never trust amounts, roles or statuses from the browser: prices come from `payment_products`; company
  verification/plan only via Drugbox admins (`companies_guard`); deals only via `deal_create`/`deal_act`.
- Storage buckets: `videos` (public; people/<uid>, companies/<id>), `post-media` (public), `message-media`
  (private, <sender>/<receiver>/…, signed links), `documents` (private: cv/, verification/, payments/),
  `reference-evidence` (private: author + moderators).

## Payments (supabase/functions, see PAYMENTS.md)
Card + Vodafone Cash/wallets via Paymob Unified Checkout (HMAC-SHA512 callback), Fawry reference numbers via FawryPay
(SHA-256 notification V2), InstaPay by transfer + receipt confirmed in Admin → Review → Payments (no public merchant API).
Secrets only as Supabase function secrets — never in the browser or in git.

## Running things locally
- Local stack (PostgreSQL 16 + PostgREST + `tools/local-supabase/gateway.mjs` emulating auth/REST/storage/functions on :54321):
  `tools/local-supabase/start.sh` (see the README for the database name and ports).
- Payment functions + Paymob/Fawry stand-in: `tools/local-supabase/start-payments.sh <env file>` (Deno; ports 54400/54500).
- Do not `pkill -f <pattern>` with a pattern that also appears in your own command line — it kills the command itself.
  Anchor patterns (`pgrep -f "^node gateway"`).

## Tests (run what you touched, then everything before handing over)
- Live end-to-end (Playwright, Python): `tests/e2e/*.py` — b1 auth, b2 feed, b2b profile posts, b3 network, b4 messages,
  c1 companies, c2 deals, c3 listings, d1 market, d2a jobs, d2b trust, d3 groups, video, e1a uploads + follow,
  e1b documents, e2 review, e3 training, e4 payments (server), e4b checkout (browser). Each prints `N / N`.
- Database security: `supabase/tests/{company_hub,deals,listings_groups}.rls.sql` on a fresh database built from
  `supabase/tests/_local_supabase_stub.sql` + all migrations, plus `schema_sweep.sql`.
- Demo: `tests/demo/*.py` and `tests/demo/legacy/*.py` (accessibility, links, dialogs, Arabic, speed, XSS…).
  The legacy suites read `/tmp/drugbox_brand.html` — copy `web/dist/drugbox.html` there first (or edit the path).
  Speed: `stress_base.py` vs `stress.py` side by side — a feature must not slow page switching.
- Test videos are WebM: the open-source Chromium used by Playwright cannot decode H.264.

## Non-negotiables from the owner
1. The interface stays exactly the approved demo (parity), in English and Arabic (RTL).
2. New features must never reduce speed or stability — measure before/after.
3. Deliver the standalone demo HTML (`web/dist/drugbox.html`) whenever the interface changes.
4. Test before saying something works; report failures plainly and fix the cause.

## Status (October 2026)
Done: A foundation · B auth/feed/network/notifications/messages · C companies/deals/listings/group buying ·
D marketplace/jobs/trust layer/groups · intro videos · E1 uploads and private documents · E2 Admin → Review ·
E3 training · E4 payments (server + checkout).
Code review (October 2026, `docs/CODE-REVIEW-2026-10.md`, F-01…F-178): fixed in migrations 0020 security core, 0021 trust/hub/deals,
0022 integrity/speed, 0023 payments/moderation/storage, 0024 round-2 follow-ups, plus the adapter, local stack, build and tests — run everything with
`python3 tests/run_all.py` (exits non-zero on any failure); the build is deterministic and parity compares the whole file.

**Next — E5 launch:** real Supabase project (apply 0001–0024, storage buckets, function secrets), Vercel deploy (web/dist/live + its vercel.json),
k6 load test at 100k users / 2,000 concurrent against staging, Sentry, backups, domain.

### Waiting on the owner
- Paymob keys + card and wallet integration ids, HMAC secret; Fawry merchant code + secure key; InstaPay address.
- Confirm boost / featured prices and durations (seeded EGP 1,450 / 7 days and EGP 3,950 / 30 days before 14% VAT).
- Known limits: videos the browser cannot read (iPhone HEVC on some Windows PCs) are refused — server transcoding would
  fix it; new reviews/references appear to others on their next visit to Jobs (not instantly).
