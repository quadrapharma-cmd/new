# App bugs found by the activity simulator

Found by `tools/sim` on the local stack (see `docs/SIM.md`). App code is **not** changed on the simulator branch
(`claude/sim-activity`); each bug has a reproduction for whoever fixes it. Simulator bugs are fixed in `tools/sim` and are
not listed here.

| id | severity | area | summary | found |
|---|---|---|---|---|
| SIM-01 | high (privacy, shared devices) | auth (J-SOCIAL-04) | after **Sign Out** the login form still holds the e-mail **and the password** typed at sign-in | 2026-10-24, UI driver, every config (EN/AR × 1440/390) |

## SIM-01 — Sign Out leaves the e-mail and password in the login form

- **Where:** live app (`web/dist/live`, local stack), all four configurations: EN 1440, AR 1440, EN 390, AR 390.
- **Reproduce:**
  1. Open the live app, sign in **through the login form** (type e-mail and password, click Sign in).
  2. Profile → **Sign Out**. The login page shows again.
  3. `#loginEmail` still contains the e-mail and `#loginPw` the whole password (24 characters for the sim account), so on a
     shared computer the next person signs in as you by clicking **Sign in**. A reload clears them.
  ```
  python3 tools/sim/sim.py ui --accounts 100 --sample 8 --ui-actions ui.logout   # 8 / 8 fail: "the login fields are not empty after Sign Out"
  ```
- **Why the journey missed it:** `J-SOCIAL-04` signs the person **up** through the sign-up form, so the login fields were never
  filled; the demo had the same symptom (FEATURE-STATUS: "خانات الإيميل والباسورد بتفضل مليانة بعد الخروج").
- **Fix idea:** the sign-out path (the live adapter's sign-out, or the approved page's `doLogout`) clears `#loginEmail` and
  `#loginPw` (and any `#suPw`) before showing the login page — the same as the reload does.
