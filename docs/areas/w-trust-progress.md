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
- Round 2: all w-trust journeys pass demo EN/AR 1440/390 + live EN/AR 1440. run_all sql/sweep/demo/legacy/stress green after: demo groups_test fills the
  trade profile; deal-room chips in their own row. e2e green after c3/d1 preconditions and name_paths catalog. sms-dispatch + e2e w_sms_test 16/16.
  Company surplus / dossier ask for the badge + trade profile first. Independent verifier launched (brief: /tmp/claude-0/sc/verifier_brief.md —
  copy kept below if the container restarts). Scale DB drugbox_scale being seeded (tools/scale/seed_100k.sql) for timings.py.
- Coordinator's auth items: forgot password + Resend were already built by the social area (J-SOCIAL-05, J-SOCIAL-02). Added: the local gateway
  sends at most one auth e-mail (sign-up / reset / resend) per address per minute, as Supabase (429 over_email_send_rate_limit, the same for a
  registered address or not); every adapter / auth sentence has Arabic (wtrust_ar.js, delimited block); new journey J-SOCIAL-W04 (auth errors
  EN + AR, nothing reveals whether an e-mail is registered); J-SOCIAL-02's Resend now waits the minute honestly.
- Verifier round 1 (1 blocking, 9 major, 6 minor) → 0095 (held offers out of reach of the answer / contact / view functions; held offers stay off
  by the active flag too; W-17 rules v2: NFKC, more invisible characters, dots written apart, "squashed" spellings, the 11 false positives fixed;
  every product field checked; company surplus / dossiers held like the others; duplicates by letters and digits; one invite-link list;
  deleted posts still count toward the day) and 0096 (comments checked, a company that loses the badge has its company offers paused,
  phone check says nothing before the code + per-number limits, files in use cannot be deleted, removed members do not come back by a link,
  links of former admins stop, renaming drops the partner badge + Drugbox can withdraw it, group_activity counts visible posts only,
  accept_rules does not reveal private groups). Interface: "Your listing is live" / "Post published! ✅" only when true; SIM-01 on the
  "check your e-mail" screen; Admin → Review → Partner groups lists current partners with "Withdraw badge". w_trust.rls.sql 172/172.
- Verifier round 2 launched on the fresh stack (0001–0096).
