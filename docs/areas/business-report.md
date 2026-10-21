# Area report — business and payments

Branch `claude/area-business` · migrations 0050–0059 · journeys J-BUSINESS-01…49 · progress log: `docs/areas/business-progress.md`.
Final numbers (suites, 150 journeys, crawler, speed) are in the last section.

## Gap items (PRODUCT-GAPS 3.2)

| Id | What | Status | Where |
|---|---|---|---|
| B-01 | Directory filled from public lists; claim with proof | Done | `tools/import_companies.py` → `admin_import_companies` (validation, dedupe by registry / normalised EN+AR name, legal-form-only names refused, `unclaimed` / `public_list`, never invented); `claim_company` needs the commercial registry document, Admin → Review → Claims, the new owner never reads other claimants (0052, 0059) |
| B-02 | Products with photos, logo, cover | Done | 0050: `company_products` (category, pack, description, MOQ, price + currency, photo in `company-media`), logo/cover guard; directory rows carry the card fields only (a page of 100 stays < 300 KB), an opened page loads products in full |
| B-03 | Sites + GMP/ISO certificates with expiry | Done | 0050: sites with capabilities and free months (YYYY-MM), certificates with their document, Drugbox checks/rejects with a reason (`review_certificate`) |
| B-04 | Team: invites, join requests, roles, routing | Done | 0051: invites by e-mail (also to addresses without an account, claimed at sign-up), join requests, accept/decline/approve, role `management`; routing follows the team without undoing the owner's own choices; one invitation notice per person per week, 30 a day per company |
| B-06 | Real marketplace, intent matching | Done (marketplace fork) | 0054: `market_search`, `listing_match` notifications |
| B-07 | My Listings: edit, pause, delete, renew, views | Done (marketplace fork) | 0054: status / expiry / renew / counters |
| B-08 | Structured RFQ → priced quote → deal | Done (marketplace fork) | 0054 `listing_quote` + deals engine; "Quote →" uses the approved page's own "Submit a quote" form |
| B-09 | Trusted listings: photos, COA, verified certs, currency | Done (marketplace fork) | 0054: private COA (`documents/listings/<uid>/`), certificates verified by Drugbox only, currency |
| B-10 | Search the whole market | Done (marketplace fork) | 0054 `market_search` (total + rows, "Show more") |
| B-11 | Compliance documents (CEP, DMF, GDP…) | Done | 0059: `company_documents` with the file under `companydocs/<id>/` (team + Drugbox reviewers only), Admin → Review → Compliance documents (`document_review`), delete removes the file; nobody reviews their own company |
| B-12 | Deals with real paperwork | Done | 0056: `deal_files` + `deal_attach` (`deals/<deal>/`), both parties only, notified; a file behind a record can never be removed or swapped |
| B-13 | News outside the app (e-mail) | Done (provider waits for the owner) | 0059 outbox + `supabase/functions/notify-dispatch` (Resend / Postmark / SendGrid, `NOTIFY_DISPATCH_SECRET`, 10-minute claim lease, 5 tries), e-mail switch on Notifications; e-mails carry no member-written text |
| B-14 | My payments, receipts, invoices, Fawry reference again | Done | 0055 (payments fork + fixes): `my_payments`, invoices with 14 % VAT from the server, snapshot fixed at numbering, refunded invoices marked |
| B-15 | VIP in the create wizard, paid by checkout | Done | 0055; live prices from `payment_products` |
| B-16 | VIP perks | Done | 3 included boosts a month (`use_included_boost`), VIP verification requests first with a 48 h badge; the subdomain promise removed (waits for the owner) |
| B-17 | Supplier reviews: reply, dispute | Done | 0056: `review_reply`, `review_dispute`, `review_decide` (Drugbox), removed reviews count nowhere |
| B-18 | Chamber / export council membership badge | Done | 0059: a `Membership` document Drugbox confirms in Compliance documents |
| B-19 | Who in the team did what | Done | 0059 `company_activity` written from the store hook, team-only |
| B-20 | Who receives a quote request | Done | quote window + notice name the routed person ("Who answers"), unit from the product |
| B-21 | Business screens in Arabic | Done | Arabic for deals, certificates, units, MOQ, VIP sentences, payments, invoice (RTL); selects keep their English value in Arabic |
| B-06 presets, B-07 demo rows, B-22 | — | Coordinator's | not touched |

## Journeys (J-BUSINESS-01…49)
See the final section for the full run. Known, not from this area: **J-01 step 7** ("Back leaves the app") is the router (social area);
**J-02 / J-04 live** signed-out public company pages wait on the owner's decision.

## Independent verification (own model)
- **Payments** (money rules): round 1 FAIL (10 functional findings, money integrity held) → fixed; round 2 FAIL (4 new majors: a live Fawry
  reference offered as cancellable, rejected InstaPay hidden, promotions for expired listings, parity) → fixed; round 3 FAIL (Fawry reference lost → fixed by alerting Drugbox, F-115 kept) → **round 4 PASS** at 3dda8bd (95/95, 76/76, 68/68 SQL; e2e 48/48, 15/15; Fawry / payment-history journeys demo + live, EN + AR); its edge case (a second, different unmatched Fawry reference) fixed after: one alert per reference.
- **Business scope** (privacy / permissions / integrity): round 1 FAIL (CRITICAL file swap behind records, moderators blocked, decisions undoable,
  invitation e-mail abuse, Arabic role/filter) → fixed; round 2 FAIL (Arabic freeze from an i18n pattern, moderator shortcut too wide) → fixed;
  **round 3 PASS**; its last optional point (a reviewer reviewing their own company) closed.

## Migrations
0050 company page · 0051 team · 0052 claims + import · 0053 directory search (fuzzy only when nothing matches as written) · 0054 marketplace (fork) ·
0055 payments (fork + fixes) · 0056 deal files + reviews · 0057 group buying · 0058 follower notices + company jobs · 0059 company records + outbox.
All re-run safe (`tools/migration_check.py` OK), explicit grants (anon reads new tables empty — F-26), `schema_sweep.sql` six × none.
None is applied to staging/production yet, so they were corrected in place; once applied, changes go into new migrations.

## Interface changes for the owner's approval (EN + AR)
- **Company page / workspace:** product photos, price with currency, MOQ, pack; certificate chip "checked <date>" / "not yet checked"; compliance
  passport rows with file, "added by … · date", Open / Delete, statuses "Under review" / "Not accepted"; Add document takes a file; memberships
  "being checked by Drugbox"; followers line; "Still correct" for members; Directory health "Open reports"; Arabic name, tagline, logo preview in the wizard.
- **Team:** rows "Asked to join" / "Invited — waiting", Approve / Decline; "Ask to join" with "Role *"; invitation notices with Accept / Decline.
- **Claims:** claim window takes the commercial registry document; "Claim pending" banner/row; Admin → Review → Claims.
- **Deals:** documents section and file fields in share / deliver / answer; actor name in the timeline; group buying Change / Leave, "expired".
- **Admin → Review:** Claims, Compliance documents, Reviews queues; reject with a written reason.
- **Notifications:** "E-mail me about requests, deals, payments and my company" switch.
- **Directory:** "Request a proposal" on service companies; quote window names the routed person; misspelt names found.
- **Marketplace** (fork, see its list): status badges, edit box, ··· menu (pause / resume / renew / delete), COA chip, verified-certificate marks,
  Saved listings, products in top search, matching notices; real category counts.
- **Payments** (fork, see its list): My payments card, payment history with Continue / Cancel, printable tax invoice (Arabic RTL), VIP windows
  with the server's price, VIP requests first with "👑 VIP · answer within 48 h", demo notes on Fawry / InstaPay / wizard pay step; a live Fawry
  reference shows "Not paid by then, it simply expires — nothing is charged" instead of Cancel.

## Open problems / waiting on the owner
- Paymob keys + integration ids + HMAC, Fawry merchant code + secure key, InstaPay address; boost / featured prices (seeded 1,450 / 3,950 + 14 % VAT).
- E-mail provider (EMAIL_PROVIDER / EMAIL_API_KEY / EMAIL_FROM / NOTIFY_DISPATCH_SECRET) and the scheduler (cron → notify-dispatch).
- Signed-out public company pages (J-02 / J-04), VIP subdomain, billing legal details (tax registration), ETA e-invoice.
- Known limits: invitations to addresses without an account are not e-mailed (needs a decision on e-mailing non-members); a Fawry reference
  whose answer never reached the server cannot be matched automatically (F-115 forbids paying an order without a recorded reference) — reconcile
  from Fawry's dashboard; files of deleted records are removed with a direct `DELETE FROM storage.objects` (check on staging that hosted
  Supabase allows it; otherwise move to the Storage API); company-media is public (logos, product photos).
- J-01 "Back" (router, social area).

## Final sweep (2026-10-21)

**Build:** `web/build/build.py` twice → same sha256 `b9e233b34a0ab7bd…`; `web/reference/demo-approved.html` refreshed → `parity_check` PARITY OK.
`tools/migration_check.py`: OK (46 migrations). `schema_sweep.sql`: six × none.

**SQL suites** (fresh database from the stub + all migrations): company_contact 22/22, company_hub 35/35, company_page_team 67/67,
company_records 95/95, deals 23/23, followups 68/68, group_posts 120/120, integrity_perf 56/56, launch_readiness 32/32,
listings_groups 23/23, marketplace 34/34, messages_safety 25/25, network_followups 34/34, payments_area 96/96, payments_storage 76/76,
privacy_names 21/21, security_core 96/96, small_followups 33/33, trust_hub_deals 145/145.

**e2e (live):** all green, among them e4 payments 48/48, e4b checkout 15/15, e5 notify 23/23, c2 deals 16/16, d1 market 18/18, p1 36/36
(d3b and groups AR were flaky once in the full run and pass on their own).
**Demo suites:** tests/demo and legacy all green (legacy 30/30 suites after the approved quote form came back; mkx / p_mkx / b_p_mkx 22/22, hub_c 14/14).

**Journeys — business (49), after the fixes** (the full 150-run at 1b62280, then the fixed ones re-run on the setups where they had failed):

| Setup | Pass | Fail | N/A |
|---|---|---|---|
| Demo EN 1440 | 47 | 1 (J-01) | 1 |
| Demo AR 1440 | 47 | 1 (J-01) | 1 |
| Demo EN 390 | 47 | 1 (J-01) | 1 |
| Live EN 1440 | 46 | 3 (J-01, J-02, J-04) | 0 |

J-01 step 7 = "Back leaves the app" (router, social area); J-02 / J-04 live = signed-out public company pages (owner's decision).
J-03 and J-31 at 390 were flaky in the full run; 7 of 7 runs pass after the reload helper fix.

**Journeys — the other areas** (report only, same run): social 51 — demo EN 23 pass / AR 23 / 390 22 / live 20; community 50 — demo 9 / 9 / 9,
live 8. Most of their failures are features of those areas not built yet. Crossing my code: J-COMMUNITY-42 claims a company without the
commercial registry document that `claim_company` now requires (the journey needs the file step — for the coordinator), J-COMMUNITY-45
(Admin → Review tab order) and 49 (decided once) fixed here.

**Dead-end crawler:** demo 1707 clicks, **0 JS errors**, 61 new dead ends (mostly other areas); in market / companies / admin the approved
reference had 15, now 12, all 12 already present in the approved demo (admin tiles, Add Sponsor, Active toast, sample / sponsored cards,
AR contact-gold). Live 1197 clicks, **0 JS errors**, 32 new dead ends: market / companies ones are the expected guards for a member with no
company ("Create or claim your company page first", "Act as a company to make an offer") and a thin Quick view on a fixture listing with
no description; the rest are feed / jobs / profile / training (other areas).

**Speed:** 100k seed — every hot query < 50 ms; the area's queries 0.1–1.3 ms; `market_search` ≈ 40 ms (the heaviest, watch it in the
k6 run); directory page of 100 < 300 KB. Page switching: `stress.py` vs `stress_base.py` PASS (median switch 10.1 ms vs 9.8 ms base).

**Open (see above):** owner keys and decisions, J-01 router, J-02/J-04 signed-out pages, J-COMMUNITY-42 claim step, market_search at scale.
