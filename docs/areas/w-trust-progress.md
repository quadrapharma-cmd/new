# w-trust — running log (branch claude/w-trust, from claude/integ f7dc703)

Slice: trust, safety and groups — W-08, W-10, W-16, W-17, W-19, W-20, W-25, W-44, SIM-01. Migrations 0090–0099.
Live code in delimited blocks `/* ===== AREA w-trust: <feature> ===== */`. Report: docs/areas/w-trust-report.md.

## Machine notes
- The container's pre-installed Chromium is build 1243; Python Playwright 1.56 (setup-session.sh) wants 1194 and fails to launch.
  `pip install playwright==1.63.0` matches it (tested). Re-running setup-session.sh downgrades it again — reinstall 1.63 after.

## Log
- 2026-10-25 start: read CLAUDE.md, area reports; stack started.
- Migrations 0090 trade identity · 0091 auto review · 0092 trader reports + buyer rating · 0093 phone verification · 0094 group tools + invite
  links + partner groups. supabase/tests/w_trust.rls.sql 133/133. Other suites adjusted for the new rule (trade profile first, company offers
  need the badge): groups, marketplace, payments_storage, security_core, social, listings_groups; launch_readiness replays 0090–0094;
  privacy_names lists phone_verify_confirm.
- Interface: web/src/wtrust.js (service + trade profile, profile card, phone, reports), wtrust2.js (offers, holds, groups, Admin → Review,
  messages, buyer rating), wtrust_ar.js (Arabic), wtrust.css; live: web/src/live/wtrust.js. Shared files touched (delimited): adapter.js
  (hooks block at the end + 4 one-line hooks), moderation.js (dxModX extension point), groups.js (current() fields), deals.js (data-dl marker),
  soc_account.js (SIM-01), build.py (layers).
- Journeys: business_wtrust.py (W10, W16, W25, W19), community_wtrust.py (W08, W44, W17, W19), social_wtrust.py (W20), J-SOCIAL-04 strengthened.
  All pass demo EN 1440 + live EN 1440 (first round). Next: all configs, other suites, verifier.
