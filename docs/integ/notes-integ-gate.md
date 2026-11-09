# integ-gate — running notes (head 5af9483 at start)

Gate run on claude/integ. Nothing is fixed here; this file records what was run and what failed.
Gate copy with ONLY the workaround below: scratchpad `gate/wt` (not in git).

## Blockers found so far
1. **0070_usernames.sql fails on the merged chain** (`start.sh`, `run_all.py sql`, `deploy/supabase_deploy.sh` all stop):
   section 8 does `create or replace function public.open_candidates(int) returns setof public.profiles`, but `0065_merge.sql`
   (earlier, area branch) already turned it into `RETURNS TABLE(...)` -> `ERROR: cannot change return type of existing function`
   (0070_usernames.sql:478). Consequences: the migration chain is not applicable end-to-end; the final `notify pgrst` of 0070
   does not run; `open_candidates()` stays the 0065 version (no `username`/`username_key` columns).
   Workaround used ONLY in the gate copy: delete section 8 (lines 465-480) of 0070. Everything below was measured with it.

## Machine / environment notes
- setup-session.sh already detects chromium-1243 -> playwright 1.63.0 (no change needed; pin is fine).
- Node here is 22.23.4 = Unicode 17.0; tools/names/*.mjs and supabase/tests/{name_rule,usernames}.sql need Unicode 16.0
  (exit 2 "use Node 22"). Gate used `npm i node@22.13.1` (Unicode 16.0) in /opt/drugbox-tools/node-u16 for those suites -> they PASS
  (name_rule 429/429, usernames 71/71). The check in name_rule.mjs/username_rule.mjs should pin an exact Node or load ICU data.
- run_all.py has NO `launch` group (groups: sql sweep demo legacy stress demo-full e2e migrations journeys crawl render).
- WebKit is not installed (legacy lite suites run on Chromium only).

## Results so far (gate copy = head + 0070 workaround; builds from the unpatched head)
- build x2 same sha: c112c5c4... (identical, deterministic). live build x2 identical (needs a JWT-shaped anon key).
- parity vs web/reference/demo-approved.html: FAILED at char 408983 (expected: the new layers; list of interface changes below).
- sql suites (36): FAIL account.rls 31/32 · growth_channels 58/88 · launch_readiness (error) · privacy_names (error) · security_core 95/96 · trade 35/143
  (name_rule + usernames fail only on Node/Unicode, pass with Node 22.13.1). schema_sweep 6/6 none. migration_check PASS.
- demo quick suites: groups_test ar INTERMITTENT (fail, fail, fail, pass 67/67 on re-runs).
- e2e (29): only name_paths_test 111/112.
