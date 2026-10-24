# Activity simulator — progress (branch claude/sim-activity)

Crash log for this work: what is done, what is next. Newest at the bottom.

- Local stack up (setup-session, start.sh, start-payments.sh, fixtures). Playwright 1.56 expects chromium-1194; the container has 1243 → symlink shim in /opt/pw-browsers (outside the repo).
- tools/sim: safety guard (allowlist + /__drugbox/stack marker on the local gateway, staging marker, sim.drugbox.test only, payments only via the loopback stand-in), personas (name rule checked in the DB), API client, action catalog (social/business/community/admin), engine (registry, Poisson schedule in Cairo time, crash-resumable day log), report.
- Next: debug run with 20 accounts, UI driver, 100-account day, 1000-account day, timings, docs/SIM.md, workflow.
