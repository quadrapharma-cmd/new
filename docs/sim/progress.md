# Activity simulator — progress (branch claude/sim-activity)

Crash log for this work: what is done, what is next. Newest at the bottom.

- Local stack up (setup-session, start.sh, start-payments.sh, fixtures). Playwright 1.56 expects chromium-1194; the container has 1243 → symlink shim in /opt/pw-browsers (outside the repo).
- tools/sim: safety guard (allowlist + /__drugbox/stack marker on the local gateway, staging marker, sim.drugbox.test only, payments only via the loopback stand-in), personas (name rule checked in the DB), API client, action catalog (social/business/community/admin), engine (registry, Poisson schedule in Cairo time, crash-resumable day log), report.
- Next: debug run with 20 accounts, UI driver, 100-account day, 1000-account day, timings, docs/SIM.md, workflow.
- Debug runs (20 and 100 accounts) found and fixed simulator bugs: intent values (`i-have`/`i-need`/`both`/`na`), reference authors (accepted owner/admin/HR of a verified company, candidate lists the company in experience), public-list imports are server-side, certificate guard checked in the DB, mutual connection requests, followers = followers ∪ connections, racy before+1 counters → invariants, company documents (insert without SELECT), duplicate course titles, payment functions restarted after a fresh stack (new JWT secret).
- App bug SIM-01 (docs/sim/bugs.md): Sign Out leaves e-mail + password in the login form (all configs).
- Fresh stack, 100 accounts, 2026-10-26 (speed 360): 1995 attempted, 1995 ok, 0 failed; UI 21/24 ok (2 = SIM-01). Report docs/sim/report-2026-10-26-n100.md.
- Next: 1000 accounts on the same stack, 2026-10-27 (speed 144, concurrency 16), then the coordinator message.
