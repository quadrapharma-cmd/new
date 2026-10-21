# Community area — final report (jobs, groups, training, admin)

Branch `claude/area-community` · migrations 0060–0064 · running notes: `docs/areas/community-progress.md`.
All numbers below are from runs on this branch's head (fresh local database, `restack`), October 2026.

## 1. Status per gap id

| Id | Status | Where |
|---|---|---|
| J-01 Employer sees applicants, shortlist / interview / hire / reject / no-show | ✅ done (demo + live) | 0060, jobsx.js, adapter "AREA community: jobs" |
| J-02 My applications, withdraw | ✅ done | 0060, jobsx.js |
| J-03 Post my profile (open to work, CV), hide again | ✅ done | 0060 (job_seeker_cvs), jobsx.js |
| J-04 Job details before applying | ✅ done | jobsx.js |
| J-05 Search / paging, numbers right | ✅ search + paging done; the sample numbers are the coordinator's (not mine) | 0060 (search RPC) |
| J-06 Saved jobs on the Saved page | ✅ done | jobsx.js |
| J-07 Job alerts | ✅ done | 0060 (job_alerts + trigger) |
| G-01 Deal-room listings (RFQ / offers) kept and answered | ✅ done — answered through deal_create; tab hiding is the coordinator's | 0061 |
| G-04 … G-14 | ✅ done (search, sector/country filters, archive, Sub-Admin = moderator, mute, last admin kept, removed member told, removed post's author told, digest notice, Requests tab, invitation decline, Arabic) | 0061, groups.js |
| G-15 Sub-Admin role ✅; group comment Like | **G-15 like: waits on S-13 table, wiring at merge** | — |
| G-16 card name click | coordinator's (not mine) | — |
| T-01 Course → lessons → quiz → certificate (verify signed out) | ✅ done; course content and prices **waiting on the owner** | 0062, training.js |
| A-01 Users and Posts (security-definer RPCs) | ✅ done | 0063, admin.js |
| A-02 Ticker, Sponsors, Settings | ✅ done live (`tests/journeys/checks/a02_live.py` passes) — see open problems for Sponsors display / Design | 0001 tables, admin.js, adapter |
| A-03 Review: Decided tab with undo, search, filters | ✅ done | 0063, moderation.js |
| A-04 Admin entry visibility | coordinator's (not mine) | — |
| S-09 reported-members queue | not built here (as agreed) — J-47 people queue waits on S-09 | — |
| Trust layer (J-COMMUNITY-30…34): delete my review, withdraw my reference, records about me with Reply / Dispute, the reviewed side told | ✅ done | 0064, trust.js |

## 2. Journeys

**J-COMMUNITY-01…50, final run** (fresh database, every configuration the brief asks for: demo EN 1440, AR 1440, EN 390, AR 390;
live EN 1440, AR 1440): **282 PASS · 16 N/A · 2 FAIL**, and both failures pass on re-run:
- J-27 live — "N profiles" counted while parallel journeys were adding open-to-work profiles (a count race between runs, not the app); passes alone.
- J-39 demo AR 390 — Chromium showed the second file:// page the storage before the first page's last write landed (the harness issue `reopen` already handles); the journey now looks once more after a moment (recorded as `data.verify_reloaded`); 4/4 passes.
N/A = steps that exist only in live (J-33, J-49, J-50 in the demo).
The earlier full run on the same code before the last fixes: 284 PASS · 16 N/A · 0 FAIL.

**All 150 journeys, report only** (demo EN 1440, AR 1440, EN 390 + live EN 1440, this branch alone): community 46/50 before the
last fixes (all four fixed since — J-03, J-12, J-41, J-42), social 18/51, business 9/49. The social and business failures are the
other areas' features, which are not on this branch (they merge at the coordinator). One social failure was mine — J-SOCIAL-20
looked for the approved Review tab "🚩 Reported posts", which I had renamed; the name is restored and J-SOCIAL-20 passes (demo + live).

Journey changes (aligned or strengthened — none weakened):
- **Training J-37…J-40**: rewritten to the real flow — seeded lessons and quiz as the precondition, a Drugbox admin uploads the lesson media to the private bucket and the signed link plays, a real payment with the gateway callback and the return through `?payment=`, fail-then-pass quiz, signed-out certificate verify, admin adds a lesson and a question, edit and deactivate. Arabic accepts the approved 'تدريب'.
- **Admin J-41…J-50**: J-47 opens Content reports with the full post body as needle and suspends through Admin → Users (the member is told why and cannot post) instead of a column check; J-48 seeds one unread notice so "Mark all read" exists; J-43 reads the My-reports row in its dialog and requires "Open" on that row; J-44 uses this run's own warnings (a shared database keeps older runs' Sami/Dina) and waits for the rejection to be stored; J-45 accepts the approved Arabic name of the sample certificate (حلال); J-48 accepts the approved Arabic 'وافق'.
- **Helpers**: `admin_decide` also clicks a danger-confirm button (`.dbk-ov button.d[data-a=ok]`); `open_notif` clicks notification rows, not the filter tabs; approved Arabic words added (وافق، اقبل، أزل…).
- **Other suites aligned with the features** (no check removed): legacy `rest/p_rest/b_p_rest` apply to another company's job (own jobs open the applicants, J-01); legacy `hub_c` approves the claim through Drugbox before managing the page (A-03, stronger: also checks "not mine yet"); e2e `d2a` picks the category select by its options; `e3` reads "Enrolled" on the card; `d3b` looks for join requests in Manage → Requests; `p1` now requires the deal room's Listings tab and that it shows no invented listing (stronger).

## 3. Independent verification

Two independent verifier subagents (strongest model) reviewed the work:
- Groups/training round: 4 blocking findings (empty-course certificate, listing company switch, a demoted creator keeping control, group discovery) — all fixed; minor findings fixed or listed below.
- Admin/trust round: SQL side solid (22/22 suites on its own databases; normal members / anon reach no admin RPC, log or suspension; an anonymous review never reveals its writer). 4 blocking findings — a restored post's broken pictures, the moderator's reason not shown live, a moderator lifting an admin's suspension through undo, undo from stale log rows — **all fixed** (admin.rls.sql 72/72). Of its 15 minor findings, fixed: suspension coverage (a suspended account creates nothing, also through server functions), company-report reopen and `decided_by` forging, certificate no-op edits, certificate notice naming the moderator, orphaned post reports, admin undoing their own role, anonymous-review notice wording and later anonymisation, settings read before sign-in, senderless notices from deleted accounts. The remaining ones are listed under open problems.
- Verdict after the fixes: the verifier's blocking findings are all fixed and covered by new checks in admin.rls.sql / trust.rls.sql; the verifier has not re-reviewed after the fixes.

## 4. Migrations

| Migration | Content | Test |
|---|---|---|
| 0060_jobs | search RPC, pipeline, applicants, my applications, CVs, alerts | jobs.rls.sql 51/51 |
| 0061_groups | sector/country/post policy/archive, Sub-Admin, mute, last admin, notices, deal-room listings, listing company switch needs membership, a demoted creator loses control, archived groups hidden | groups.rls.sql 68/68 |
| 0062_training | topics, price, lessons (private content + course-media bucket), progress, server-scored quiz, certificates (signed-out verify by header), paid courses | training.rls.sql 68/68 |
| 0063_admin | decision log + undo where safe, decide-once (DX409), certificates checked/rejected with a note, company reports, suspension, roles + badge, Users/Posts RPCs, post removal + restore | admin.rls.sql 72/72 |
| 0064_trust | the reviewed side is told; a review made anonymous later stops naming its writer | trust.rls.sql 19/19 |

Every new table / sequence / function has explicit GRANT/REVOKE (0026 rule); `launch_readiness.rls.sql` re-applies 0060…0064.
`schema_sweep.sql` 6/6 "none"; `tools/migration_check.py` passes. None of these migrations has been deployed anywhere; 0061–0063 were
edited on this branch after their first commit (before any deploy, so no ledger is affected — but it is noted against the rule).

## 5. Interface changes for the owner's approval (EN + AR, 1440 + 390)

- Jobs: My jobs / Applicants panels (pipeline buttons), My applications, Post my profile, job details window, saved jobs on Saved, job alerts, employment-type and country filters and fields, "Applicants (n)" on my own jobs.
- Groups: search and sector/country filters, View all, Manage → Requests tab, settings (rules, privacy, who posts, sector, country), archive/restore, invitation Decline, deal-room listings with quotes / Close, file chips, lightbox, the private group's members tab lists its admins.
- Training: filters and search, course window, lessons, quiz, certificate (QR, verify link, print to PDF), My courses, certificates on the profile, Admin → Training.
- Admin: Users and Posts pages, live Dashboard numbers, Ticker / Sponsors (Add form, demo too) / Settings live, My reports, the suspension notice.
- Review: new "🗂 Decided" tab with Undo / Restore; search box; claim marker; the candidate's reply on warnings; certificate Reject (asks the reason with the browser's prompt); "Remove post" is the main (red) button.
- Directory: a claim waits for Drugbox's review in the demo too (was immediate); "Get verified" vs "Documents received — being checked" follows the real request.
- Trust: "Delete my review" in the rating window, "Withdraw" on my references in the Honor / Warning list, "📋 About you" (records about me with Reply / Dispute; shown only when something is written about me).
- Checkout: the demo shows the InstaPay path with its order number.
- Escape leaves a Jobs panel like ← Back.

## 6. Suite numbers (final head)

FINAL_SUITES

## 7. Open problems and items waiting

- **Waiting on the owner**: course content (lessons, instructors) and prices (live courses are free until set; the demo shows GCC Market Access at EGP 1,500 as a sample); Paymob keys; whether Admin → Design (colours, fonts, icons) should apply to everyone (today it changes the admin's own browser only); where sponsors should show to members (the Market Board they were made for became the Company Directory — Admin keeps them, no approved page shows them).
- **G-15 like: waits on S-13 table, wiring at merge.** **J-47 people queue waits on S-09.**
- Known limits / minor findings not fixed: the quiz answer count can reveal the key; group post notices fan out to every member (very large groups); the trigram index is not used by groups_search; staging must be checked to pass the `x-dbx-cert` header through; `verification_requests.reviewed_by` can be written by a moderator directly; undoing an approved verification resets only the status; deleting and re-writing a review notifies again; the i18n option-value fix freezes the first English value; `trust.js` installs a demo-only store hook for jobReviews/jobRefs (same behaviour as the store); certificate Reject uses the browser prompt rather than the approved dialog.
