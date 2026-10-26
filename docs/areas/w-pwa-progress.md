# Slice w-pwa — installable web app + web push (branch claude/w-pwa) — running log

Restart recipe: `bash tools/local-supabase/setup-session.sh` → eval its last line → `setsid nohup tools/local-supabase/start.sh &`
→ `tools/local-supabase/start-payments.sh` → `python3 tests/fixtures/make_fixtures.py`.
Container note (26 Oct): the pre-installed browser is now chromium-1243 while setup installs Python Playwright 1.56 (expects 1194):
link it once — `cd /opt/pw-browsers && mkdir -p chromium_headless_shell-1194/chrome-linux chromium-1194/chrome-linux &&
ln -sf $PWD/chromium_headless_shell-1243/chrome-headless-shell-linux64/* chromium_headless_shell-1194/chrome-linux/ &&
ln -sf chrome-headless-shell chromium_headless_shell-1194/chrome-linux/headless_shell && ln -sf $PWD/chromium-1243/chrome-linux64/* chromium-1194/chrome-linux/ &&
touch chromium-1194/INSTALLATION_COMPLETE chromium_headless_shell-1194/INSTALLATION_COMPLETE`.

Baseline (integ f7dc703): demo sha 36d98b86…, parity vs web/reference/demo-approved.html already NOT OK at the start
(integ changed `#content.dx-enter` CSS without refreshing the reference) — my interface diff is measured against the integ build.

## Plan / status
| Step | What | Status |
|---|---|---|
| 1 | icons from LOGO_ICON (tools/pwa/make_icons.py → web/src/pwa/*.png), live.py: manifest, sw.js, offline.html, head tags, VAPID public key in config; vercel.json + gateway headers | |
| 2 | demo layer pwa.js/pwa.css (install offer, iOS guide, Settings card, device notifications) + live block AREA w-pwa in adapter.js | |
| 3 | migration 0110 push subscriptions + push outbox, supabase/tests/push.rls.sql | |
| 4 | _shared/webpush.js (RFC 8291/8292, WebCrypto), notify-email sends pushes, local push receiver | |
| 5 | journeys J-SOCIAL-PWA-1..3, measurements (cold load, stress A/B) | |
| 6 | independent verifier, full suites, report | |
