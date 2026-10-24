# Drugbox activity simulator (`tools/sim`)

Synthetic accounts — 100, or 1000 — that use every function of the app every day, at random times, and check every result
in the database. It is a **daily soak / regression / load test** for the local stack and a future **staging** project: it
finds bugs (a failed action is reported with a reproduction) and slowdowns (latency per action, database growth, the hot
queries at that size).

## The hard boundary

It never runs against production, and its accounts never appear to real members as real people:

| rule | how it is enforced (`tools/sim/simlib/safety.py`, fail closed) |
|---|---|
| only allowed hosts | the target URL's host must be in `DRUGBOX_SIM_ALLOWED_HOSTS` (default `localhost,127.0.0.1`) and on no production list (`DRUGBOX_PRODUCTION_HOSTS`, `DRUGBOX_PRODUCTION_REF`, `*.drugbox.app/.com/.eg/.net`, `*.vercel.app`) |
| the target must say it is not production | **local:** a loopback host whose gateway answers `GET /__drugbox/stack` with `{"stack":"local-supabase","production":false,"database":…}` (added to `tools/local-supabase/gateway.mjs`), for the same database the simulator checks. **staging:** `DRUGBOX_SIM_TARGET=staging`, `https://<ref>.supabase.co` with `DRUGBOX_SIM_STAGING_REF=<ref>` (≠ `DRUGBOX_PRODUCTION_REF`), a marker file the operator puts on staging only, and `STAGING_DB_URL` for the same project |
| the checked database is the target's | after sign-up the sim admin's row must be readable through the API **and** in the database (`same_stack`) |
| simulated accounts only | every e-mail is `…@sim.drugbox.test` (a reserved `.test` domain; not configurable); every bio starts "Simulated account"; every account is in the registry; `sim.py cleanup` deletes them all |
| no real payment gateway | payments run only when the function settings point Paymob **and** Fawry at a loopback address and the stand-in answers (`tools/local-supabase/start-payments.sh`); every checkout link must stay on the stand-in, else the run stops. On staging payments are off unless `DRUGBOX_SIM_PAYMENT_STANDIN_URL` names an allowed stand-in |
| polite | a global token bucket (`--rps`, default 150 requests/s), a bounded API pool (`--concurrency`, default 12, at most 64), one action at a time per person, the app's own flood limits respected (deal requests: < 30/person/hour, < 10/company/hour; claims < 5/day), at most **4 browsers** for the UI driver |

`python3 tools/sim/sim.py check` prints the decision. Refusals exit with code 3 and say why, e.g.
`SIMULATOR REFUSED TO START: app.drugbox.app is a production host`.

## Quick start (local)

```bash
bash tools/local-supabase/setup-session.sh      # once per container (then export the POSTGREST/DENO line it prints)
tools/sim/run_local.sh --fresh --accounts 100 --speed 360 --tag n100 --timings --ui 24
tools/sim/run_local.sh --accounts 1000 --speed 0 --tag n1000 --timings --ui 24 --concurrency 16
python3 tools/sim/sim.py cleanup                 # delete every simulated account and all its data
```
`run_local.sh --fresh` recreates the database (start.sh), restarts the payment functions with the new secret, makes the
fixtures and runs `sim.py run` with the other options. Reports land in `docs/sim/report-<date>[-<tag>].md` and `.json`.

Other commands: `sim.py daemon` (day after day; `--speed 1` is real time and waits for the next Cairo midnight),
`sim.py ui --sample 24` (only the browser driver), `sim.py report --day <date> --tag <tag>` (rebuild a report from a day's
log), `sim.py catalog` (the action table below). Needs `requests` and `psycopg2-binary` (run_local.sh installs them;
without psycopg2 the database checks run through `psql`, slower).

## How it works

- **Personas** (`simlib/personas.py`): deterministic from `--seed` — person *i* depends only on (seed, *i*), so the first 100
  of a 1000 run are the 100 run's people. Egyptian and Gulf/Levant pharma professionals in Arabic or Latin script with
  titles (د. / Dr. / Eng. / Ph/), 16 roles (QA, QC, regulatory, production, medical rep, sales, procurement, BD, community
  and hospital pharmacists, R&D, supply chain, HR, PV, students, consultants) with archetype weights (social, trade, hire,
  seek, learn, group), 14 Egyptian cities + 6 Arab capitals, interests, skills, experience and education. About 1 in 8
  owns a company (manufacturer, distributor, CMO, pharmacy, API/packaging supplier, consultancy) and creates it on the
  first day; most others work for an earlier owner's company and join its team by invitation. **Every name is checked with
  the database's own rule** (`person_name_problem(person_name_norm(…))`, 0038–0039) before use, and after sign-up every
  profile must be keyed (`name_key`) and not flagged.
- **API driver** (`simlib/client.py`, `act_*.py`): each account signs in through `/auth/v1/token` and sends **the same
  REST / RPC / Storage / Functions requests the live app sends** (`web/src/live/adapter.js`) with its own JWT, so row-level
  security applies exactly as in the app. Each action then checks the result **in the database** (the row exists, the
  counter equals the rows, the status moved, the notification arrived, the private file is not readable by a stranger…).
- **UI driver** (`simlib/ui.py`): a random sample of actions done with real clicks in the live app by sim accounts signing
  in through the login form, spread over EN/AR × 1440/390 (touch on 390), with the journeys' own helpers and selectors
  (`tests/journeys/_j.py`), each checked in the database; JavaScript errors are counted. One browser per worker process,
  at most 4.
- **Schedule** (`simlib/engine.py`): each person has active hours in Cairo time and an intensity (actions per active day,
  log-normal: a few heavy users, a long tail of light ones). A day's actions are a Poisson number of events at uniform
  random times inside the window (a Poisson process), 5 % outside it, 45 % on Friday/Saturday. Actions are chosen by the
  persona's archetype weights; every action anyone may do is scheduled at least once a day; the first day adds the set-up
  (profile, experience, connections, a first post, company + team + site + product + job for owners, groups, a course).
  Wall time = simulated time / `--speed` (0 = as fast as the pool allows). Schedule lag is reported.
- **Crash resilience:** every finished action is appended to `tools/sim/state/<target>/days/<date>[-tag].jsonl` with its
  event number; re-running the same day skips what is done. The registry (`registry.json`, mode 600: e-mails, passwords,
  uids) is rewritten after each sign-up batch. Passwords are derived from the seed, so a lost registry is rebuilt by
  signing in again. `tools/sim/state/` is git-ignored.
- **Outcomes:** `ok` (done and verified) · `fail` (the app answered an error or the database does not show what it said it
  did → a finding with a reproduction) · `not_built` (the journey's feature has no live backend yet, as in
  `docs/FEATURE-STATUS-2026-10.md`) · `limited` (the app's own flood limit answered) · `skip` (nothing to do for this person
  now) · `sim_error` (a simulator bug — fix it in `tools/sim`). `path` says whether the live interface sends this request
  (`app`), the database supports it but no screen sends it yet (`api`), or it is Drugbox's server-side work (`server`).
- **Report** (`simlib/report.py`): per action attempted / ok / failed / not built / limited / skipped and latency p50/p95
  (per action and per request), every distinct failure with the actor, the requests and the database check, the journeys
  exercised, the UI driver's results, database growth per table, storage objects and database size, and the hot queries at
  that size (`tools/scale/timings.py --uuid <busiest sim member>`, row-level security on) with `--timings`.

## The action catalog

`python3 tools/sim/sim.py catalog` prints it (it is generated from the code). Every journey in `docs/JOURNEYS.md` has an
action (J-SOCIAL-01 sign-up is the bootstrap). Admin actions are done by the sim admin (`sim-admin@sim.drugbox.test`,
promoted to `role='admin'` in the database, as Drugbox staff are made on the server).

| area | actions |
|---|---|
| social | feed paging + views + reaction summary · text post (mentions, hashtags) · post with photo + PDF (Storage read-back) · react (all six kinds) / un-react · comment · reply (`api`) · comment like (`not built`) · repost + share count · save / unsave · edit · delete · report · profile edit (private phone via `my_profile()`), rename (name rule), experience/education/skills (`api`), intro video, photo (`not built`) · visit a profile (view log, counts, `select=*` refused) · people search (name + skeleton) · connect / accept / decline / withdraw / remove · follow / unfollow · dismiss a suggestion · message (text, attachment with signed link), read + search, mute, block (a blocked person cannot write), report · notifications read / read all / clear · ticker, market and jobs numbers · settings, saved searches, notification preferences, suspending a person (`not built` locally) |
| business | directory pages + filtered search · company page (products, sites, track record, ratings, contacts, jobs) · follow a company · message a company · create a company (forged verify/VIP refused) · update the page · team invite + accept (`api`), routing (`api`) · sites, certificates (a company cannot mark its own as checked), private documents, products (`api`) · verification with documents (strangers cannot open them) · claim an imported page · report wrong data · RFQ to 1–3 suppliers · service request · supplier questionnaire → approved list · dossier licensing · near-expiry surplus · buying groups (create, join, target reached, supplier confirms → one order per member) · every deal step on either side (quote, counter, accept, confirm, ship, receive, rate, decline, cancel…) · shared inbox and deal privacy probes · market browse / search / featured · supply listing, demand (RFQ), hide sold, intents · boost (card, Fawry), featured (wallet, InstaPay), VIP (card, wallet, Fawry) through the stand-in with signed callbacks · payment history |
| community | groups list/activity/discussion/members (private posts hidden) · create a group / deal room · join a public group, ask to join a private one (no direct join) · leave · post, comment, like · invite · admin: decide requests, pin, promote, settings · report a group post, admins dismiss/remove · jobs list + filters · save · apply with a CV (once; the poster can open it, a stranger cannot) · apply from a company page (job deal) · withdraw · post a job · move applicants to hired (`api`) · job alerts (`not built`) · trust: candidates, reviews, lists, honour references, warnings with evidence (wait for moderation), replies/disputes · training: enroll (+ count) · progress/exam/certificate (`not built`) |
| admin | post reports (a second decision does not overwrite) · verification and claim requests (documents opened by signed link, the requester notified) · wrong-data reports · warnings with evidence · certificates · InstaPay transfers · message reports · courses (`api`) · public-list imports (`server`) · a member is not staff (decisions refused) |
| ui | every main page in EN/AR (RTL) · Back (known gap J-SOCIAL-50) · post · react · comment · message · enroll · join a group · save a job · market · directory · connect/accept · sign out and in · dark theme remembered · Ctrl+K · company share card |

## Staging

The workflow `.github/workflows/sim-staging.yml` runs the simulator every day on staging. It is **disabled** until staging
exists: only `workflow_dispatch`, the `schedule:` block is commented out, and the job runs only when the repository variable
`DRUGBOX_SIM_STAGING_ENABLED` is `true`. To enable it:

1. Create the staging project (`docs/LAUNCH.md`, staging first) — never point this at production.
2. On staging only, create a public Storage bucket `sim-marker` and upload `staging.json`:
   `{"drugbox_env": "staging", "ref": "<staging ref>"}`. Production must never have this bucket.
3. Repository variables: `DRUGBOX_SIM_STAGING_URL` (`https://<ref>.supabase.co`), `DRUGBOX_SIM_STAGING_REF`,
   `DRUGBOX_PRODUCTION_REF` (so it is refused by name too), `DRUGBOX_SIM_STAGING_ENABLED=true`.
   Secrets: `DRUGBOX_SIM_STAGING_ANON_KEY`, `DRUGBOX_SIM_STAGING_DB_URL` (the staging database URL, for the checks, the
   sim admin and clean-up), `DRUGBOX_SIM_SEED` (the passwords derive from it).
4. Run it once by hand (Actions → sim-staging → Run workflow), read the report artifact, then uncomment `schedule:`.
5. Payments stay off on staging unless its function secrets point Paymob/Fawry at a stand-in and
   `DRUGBOX_SIM_PAYMENT_STANDIN_URL` names it.

Locally the same run is `tools/sim/run_local.sh` (or `sim.py daemon` for a continuous soak).

## Clean-up

`python3 tools/sim/sim.py cleanup` deletes every account whose e-mail is at `sim.drugbox.test` (the registry is not needed),
the companies they own, the imported `sim-dir-*` pages, the simulated courses and their Storage objects (and, locally, the
files). Everything else they made goes with the account through the foreign keys. It prints what is left (must be 0).

## Results and findings

Proof runs on a fresh local stack (2026-10-24, head of `claude/sim-activity`; seed `drugbox-sim-1`):

| run | accounts | events | attempted | ok | failed | not built | wall | action p50 / p95 | request p50 / p95 | lag p95 | UI driver |
|---|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| `report-2026-10-26-n100` (Mon, first day) | 100 + admin | 2,440 | 1,995 | 1,995 | **0** | 39 | 233 s (speed 360) | 13.4 / 146 ms | 3.7 / 7.1 ms | 0.7 s | 21 ok, 2 failed (SIM-01), 1 skipped |
| `report-2026-10-27-n1000` (Tue, 900 new members' first day) | 1000 + admin | 21,386 | 18,118 | 18,118 | **0** | 328 | 600 s (speed 144) | 54 / 546 ms¹ | 3.5 / 5.4 ms | 13.8 s¹ | 21 ok, 3 skipped |
| `report-2026-10-28-n1000-day2` (Wed, `--rps 600`) | 1000 + admin | 13,304 | 10,862 | 10,862 | **0** | 364 | 600 s (speed 144) | 9.9 / 59.8 ms | 3.5 / 5.9 ms | 0.1 s | 22 ok, 2 failed (SIM-01) |

¹ the simulator's own limiter (`--rps 150`) was the bottleneck at the first 1000-account day's peak (2,149 thread-seconds of
waiting); with `--rps 600` the next day's actions took p95 60 ms and started on time. The stack itself stayed fast:
single requests p95 ≤ 6 ms, no database statement over 100 ms in the PostgreSQL log during the run (log_min_duration_statement
= 100), and `tools/scale/timings.py` as the busiest sim member (RLS on) at 1000 members: every hot query within its limit,
the slowest `my_interactions` 2.3 ms, `directory_page` 1.6 ms, `deals_list` 1.6 ms, `connections_page` 1.0 ms. Database
18.8 → 32.6 → 39.1 MB. Every database error logged during the 1000 run was one of the simulator's deliberate negative probes
(`select=*` on profiles, a direct join of a private group, a second application, a forged verification, non-staff decisions,
a review without interaction, a message across a block), each refused as it should be. 96–99 actions were verified per day;
127 of 150 journeys were exercised with a verified result; the other journeys' features have no live backend yet (`not built`,
as in FEATURE-STATUS) or had no target that day.

- Reports: `docs/sim/report-<date>-<tag>.md` / `.json`.
- App bugs found by the simulator, with reproductions: `docs/sim/bugs.md` (app code is not changed on the simulator branch).
- Progress log of this work: `docs/sim/progress.md`.
