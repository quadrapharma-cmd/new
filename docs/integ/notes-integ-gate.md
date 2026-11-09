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
