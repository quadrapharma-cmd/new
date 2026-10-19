# Community area (jobs, groups, training, admin) — running log

Branch `claude/area-community`, migrations 0060–0069. Report: `docs/areas/community-report.md` (at the end).

## Setup after a restart
`bash tools/local-supabase/setup-session.sh`, then the stack: `start.sh` → `start-payments.sh tools/local-supabase/payments.env.example` → `python3 tests/fixtures/make_fixtures.py`,
then rebuild demo + live with the stack's JWT secret.

## Baseline (before any change, 19 Oct): demo EN 1440 8 pass, live 6 pass of J-COMMUNITY-01…50

## Done
- **Jobs (J-01…J-07)** — 0060_jobs.sql (search RPC, pipeline, applicants, my applications, CV table job_seeker_cvs, alerts), jobsx.js/css,
  adapter block "AREA community: jobs"; jobs.rls.sql 51/51; J-19…J-29 pass demo (EN/AR 1440, EN/AR 390) and live (EN/AR 1440).
- **Groups (G-01, G-04…G-15)** — 0061_groups.sql (sector/country/post policy/archive, Sub-Admin = moderator, mute, last admin kept unless the account
  is erased, removed member told, removed post's author told, digest notice for new posts, deal-room listings answered through deal_create with a worded
  notice), groups.js + adapter "AREA community: groups"; groups.rls.sql 65/65; J-01…J-18 pass demo + live (all configs as above).
  Older suites aligned with the journeys: group_posts (the post's author removes comments on it — J-05; a declined requester is told — J-10).
- **Training (T-01)** — 0062_training.sql (topics, instructor, price, lessons with private content + course-media bucket, progress, quiz scored on the
  server, certificates + signed-out verify by the x-dbx-cert header, paid courses via payment products course_<id> / create_order / activate_order);
  training.rls.sql 63/63; all 20 SQL suites pass. training.js/css (filters, search, course window, lessons, quiz, certificate + QR + verify link + print
  to PDF, My courses, profile certificates, Admin → Training) + adapter "AREA community: training". Journeys J-37…J-40 strengthened (real payment in
  live, seeded lessons/quiz as the precondition, fail-then-pass, signed-out verify, admin adds lessons and a question, edit and deactivate).
- Journey helper fixes (no assertion weakened): open_notif clicks notification rows, not the filter tabs; approved Arabic words added (وافق، اقبل، أزل…).

## Waiting
- G-15 group comment Like: waits on S-13 table (comment_reactions), wiring at merge.
- J-47: the reported-members queue (social S-09).
- Owner: course content (lessons, instructors), course prices (live courses are free until set; the demo shows GCC Market Access at EGP 1,500 as a sample).

## Next
- Training: build + run J-35…J-40 demo + live; fix.
- Admin A-01/A-02/A-03 (migration 0063), journeys 41–50; trust journeys 30–34.
- Finish list (build ×2, parity, run_all, e2e, 150 journeys, crawler, report, message the coordinator).
