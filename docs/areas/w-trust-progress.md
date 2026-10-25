# w-trust — running log (branch claude/w-trust, from claude/integ f7dc703)

Slice: trust, safety and groups — W-08, W-10, W-16, W-17, W-19, W-20, W-25, W-44, SIM-01. Migrations 0090–0099.
Live code in delimited blocks `/* ===== AREA w-trust: <feature> ===== */`. Report: docs/areas/w-trust-report.md.

## Machine notes
- The container's pre-installed Chromium is build 1243; Python Playwright 1.56 (setup-session.sh) wants 1194 and fails to launch.
  `pip install playwright==1.63.0` matches it (tested). Re-running setup-session.sh downgrades it again — reinstall 1.63 after.

## Log
- 2026-10-25 start: read CLAUDE.md, area reports; stack started.
