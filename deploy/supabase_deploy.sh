#!/usr/bin/env bash
# Drugbox — database + Edge Functions deploy to a Supabase project (staging by default; production only with --prod).
#
#   deploy/supabase_deploy.sh [options]
#
# Settings (environment, or deploy/.env.supabase — deploy/.env.supabase.prod with --prod; the environment wins):
#   SUPABASE_DB_URL         postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres   (Settings → Database → Connection string)
#     or SUPABASE_PROJECT_REF + SUPABASE_DB_PASSWORD  (direct host; SUPABASE_DB_HOST / _PORT / _USER for the session pooler)
#   SUPABASE_PROJECT_REF    the project ref (the <ref> in https://<ref>.supabase.co) — needed for the functions
#   SUPABASE_PROD_REF       the PRODUCTION project's ref: a run against it is refused without --prod, --prod against any other is refused
#   SUPABASE_ACCESS_TOKEN   a personal access token (supabase.com → Account → Access Tokens) — for secrets + functions only
# Function secrets: deploy/.env.functions (staging: TEST keys) or deploy/.env.functions.prod (--prod: LIVE keys) — see env.functions.example.
#
# Options:
#   --prod                 production (also requires SUPABASE_PROD_REF to match and the database to be stamped production or new)
#   --db-only              database steps only: no secrets, no functions (local rehearsal, or a database-only change)
#   --with-local-stub      a bare PostgreSQL (rehearsal): load supabase/tests/_local_supabase_stub.sql when auth/storage are missing
#   --dry-run              connect, check and show the plan; change nothing
#   --baseline-through N   the database already has migrations ≤ N (applied by hand): record them as applied without running them
#   --migrations-dir DIR   apply migrations from DIR instead of supabase/migrations (tests)
#   --env-file F / --functions-env F   other settings / secrets files
#   --skip-smoke           do not call the deployed functions afterwards
#
# What it does, in order (every step prints what it does; secret values are never printed):
#   1 preflight: psql reachable, server version, required extensions, Supabase's auth/storage/roles/realtime publication
#   2 the migration ledger drugbox_deploy.migrations (filename + sha256): applied files are skipped, a CHANGED applied file is refused
#   3 every pending supabase/migrations/NNNN_*.sql in order, each in ONE transaction with ON_ERROR_STOP (and its ledger row)
#   4 checks: schema_sweep.sql (every line "none"), the five storage buckets, realtime on messages + notifications, table/sequence
#     grants for the API roles, jit = off for the API login role, the pg_cron job, the prices
#   5 (unless --db-only) function secrets + the three Edge Functions, then a smoke call to each
set -euo pipefail
# shellcheck source=deploy/lib.sh
source "$(dirname "$0")/lib.sh"

PROD=0 DB_ONLY=0 STUB=0 DRY=0 BASELINE='' SKIP_SMOKE=0 ENV_FILE='' FN_ENV='' MIG_DIR="$REPO/supabase/migrations"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod) PROD=1 ;;
    --db-only) DB_ONLY=1 ;;
    --with-local-stub) STUB=1 ;;
    --dry-run) DRY=1 ;;
    --baseline-through) BASELINE="${2:?--baseline-through needs a number like 0025}"; shift ;;
    --migrations-dir) MIG_DIR="$(cd "${2:?}" && pwd)"; shift ;;
    --env-file) ENV_FILE="${2:?}"; shift ;;
    --functions-env) FN_ENV="${2:?}"; shift ;;
    --skip-smoke) SKIP_SMOKE=1 ;;
    -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option $1 (see --help)" ;;
  esac; shift
done
[[ -n "$BASELINE" && ! "$BASELINE" =~ ^[0-9]{4}$ ]] && die "--baseline-through takes a 4-digit migration number, e.g. 0025"
[[ $PROD == 1 && $STUB == 1 ]] && die "--with-local-stub is for a local rehearsal database, never with --prod"
need psql python3 sha256sum
SUFFIX=''; [[ $PROD == 1 ]] && SUFFIX='.prod'
TARGET=staging; [[ $PROD == 1 ]] && TARGET=production; [[ $STUB == 1 ]] && TARGET=rehearsal
mkdir -p "$DEPLOY_DIR/logs"; chmod 700 "$DEPLOY_DIR/logs"; LOG="$DEPLOY_DIR/logs/supabase-$(date -u +%Y%m%dT%H%M%SZ)-$TARGET.log"; : > "$LOG"; chmod 600 "$LOG"

step "Settings ($TARGET)"
load_env_file "${ENV_FILE:-$DEPLOY_DIR/.env.supabase$SUFFIX}" || info "no ${ENV_FILE:-deploy/.env.supabase$SUFFIX} — using the environment only"
resolve_db
info "database: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME   project: ${DB_REF:-"(none: not a Supabase host)"}   log: ${LOG#"$REPO"/}"
prod_guard "$DB_REF" "$PROD"
if [[ $STUB == 1 ]] && ! is_local_host "$DB_HOST"; then die "--with-local-stub only for a local database (127.0.0.1/localhost), not $DB_HOST"; fi
if [[ $DB_ONLY == 0 ]]; then
  [[ -n "${SUPABASE_PROJECT_REF:-$DB_REF}" ]] || die "the functions need SUPABASE_PROJECT_REF (or --db-only)"
  [[ -n "${SUPABASE_ACCESS_TOKEN:-}" ]] || die "the functions need SUPABASE_ACCESS_TOKEN (supabase.com → Account → Access Tokens), or use --db-only"
fi

# ── 1. preflight ───────────────────────────────────────────────────────────────────────────────────────────────────────────
step "1. Preflight"
info "psql client: $(psql --version | awk '{print $3}')"
q 'select 1' >/dev/null 2>>"$LOG" || die "cannot connect to $DB_HOST:$DB_PORT as $DB_USER (details in ${LOG#"$REPO"/}). Supabase's direct host is IPv6 — on an IPv4-only network use the Session pooler URL (port 5432) from Settings → Database"
IFS='|' read -r SV SVN WHO <<<"$(q "select current_setting('server_version'), current_setting('server_version_num'), current_user")"
ok "connected as $WHO — PostgreSQL $SV"
(( SVN >= 140000 )) || die "PostgreSQL $SV is too old (14 or newer; Supabase runs 15/17)"
MISSING_EXT="$(q "select coalesce(string_agg(n, ', '), '') from unnest(array['pgcrypto','pg_trgm']) n where not exists (select 1 from pg_available_extensions a where a.name = n)")"
[[ -z "$MISSING_EXT" ]] || die "extensions not available on this server: $MISSING_EXT"
ok "extensions available: pgcrypto, pg_trgm$( [[ "$(q "select count(*) from pg_available_extensions where name = 'pg_cron'")" == 1 ]] && echo ', pg_cron (optional)')"
SUPA_CHECK="select coalesce(string_agg(x, ', '), '') from (values
  ('schema auth', to_regnamespace('auth') is not null), ('auth.users', to_regclass('auth.users') is not null),
  ('auth.uid()', to_regprocedure('auth.uid()') is not null), ('storage.buckets', to_regclass('storage.buckets') is not null),
  ('storage.objects', to_regclass('storage.objects') is not null),
  ('role anon', exists (select 1 from pg_roles where rolname = 'anon')), ('role authenticated', exists (select 1 from pg_roles where rolname = 'authenticated')),
  ('role service_role', exists (select 1 from pg_roles where rolname = 'service_role')),
  ('publication supabase_realtime', exists (select 1 from pg_publication where pubname = 'supabase_realtime'))) v(x, present) where not present"
MISSING="$(q "$SUPA_CHECK")"
if [[ -n "$MISSING" ]]; then
  if [[ $STUB == 1 ]]; then
    info "not a Supabase database (missing: $MISSING) — loading the local stand-in supabase/tests/_local_supabase_stub.sql (--with-local-stub)"
    [[ $DRY == 1 ]] && die "--dry-run does not change the database: the stub is needed first (run without --dry-run)"
    "${PSQL[@]}" -d "$DB_URL" -f "$REPO/supabase/tests/_local_supabase_stub.sql" >>"$LOG" 2>&1 || die "the local stub failed (see ${LOG#"$REPO"/})"
    MISSING="$(q "$SUPA_CHECK")"; [[ -z "$MISSING" ]] || die "still missing after the stub: $MISSING"
    ok "local Supabase stand-in loaded (auth, storage, roles, realtime publication)"
  else
    die "this database lacks what Supabase provides: $MISSING.
    On a real Supabase project these always exist — check that SUPABASE_DB_URL points at the Supabase project (not another server).
    For a local rehearsal on a bare PostgreSQL, add --with-local-stub."
  fi
else
  ok "Supabase schemas present: auth, storage, roles anon/authenticated/service_role, publication supabase_realtime"
fi

# ── 2. ledger + environment stamp ──────────────────────────────────────────────────────────────────────────────────────────
step "2. Migration ledger (drugbox_deploy.migrations)"
LEDGER_DDL="set client_min_messages = warning;
create schema if not exists drugbox_deploy;
revoke all on schema drugbox_deploy from public;
create table if not exists drugbox_deploy.migrations (filename text primary key, sha256 text not null check (sha256 ~ '^[0-9a-f]{64}\$'),
  applied_at timestamptz not null default now(), applied_by text not null default current_user, duration_ms int, mode text not null default 'transaction');
create table if not exists drugbox_deploy.environment (only_row boolean primary key default true check (only_row),
  name text not null check (name in ('production', 'staging', 'rehearsal')), project_ref text, stamped_at timestamptz not null default now(), stamped_by text not null default current_user);
revoke all on all tables in schema drugbox_deploy from public;
do \$\$ declare r text; begin foreach r in array array['anon','authenticated','service_role'] loop
  if exists (select 1 from pg_roles where rolname = r) then execute format('revoke all on schema drugbox_deploy from %I', r); execute format('revoke all on all tables in schema drugbox_deploy from %I', r); end if;
end loop; end \$\$;
comment on schema drugbox_deploy is 'Drugbox deploy bookkeeping (deploy/supabase_deploy.sh): applied migrations + this database''s environment. Not exposed to the API.';"
HAVE_LEDGER="$(q "select to_regclass('drugbox_deploy.migrations') is not null")"
if [[ $DRY == 1 ]]; then [[ "$HAVE_LEDGER" == t ]] || info "(dry run) no ledger yet — it would be created"
else "${PSQL[@]}" -d "$DB_URL" -c "$LEDGER_DDL" >>"$LOG" 2>&1 || die "could not create the ledger (see ${LOG#"$REPO"/})"; HAVE_LEDGER=t; fi
STAMP=''; [[ "$HAVE_LEDGER" == t ]] && STAMP="$(q "select name from drugbox_deploy.environment")"
case "$STAMP:$TARGET" in
  production:production|staging:staging|staging:rehearsal|rehearsal:rehearsal|rehearsal:staging) ok "environment stamp: $STAMP" ;;
  production:*) die "this database is stamped PRODUCTION — re-run with --prod (and the .prod settings) if that is really what you want" ;;
  *:production) [[ -z "$STAMP" ]] || die "--prod was given but this database is stamped '$STAMP' — wrong database?" ;;
  :*) ;;
esac
if [[ -z "$STAMP" ]]; then
  if [[ $DRY == 1 ]]; then info "(dry run) would stamp this database '$TARGET'"
  else q "insert into drugbox_deploy.environment (name, project_ref) values ('$TARGET', nullif('${DB_REF}', '')) on conflict do nothing" >/dev/null; ok "stamped this database '$TARGET' (later runs check it)"; fi
fi

shopt -s nullglob; FILES=("$MIG_DIR"/[0-9][0-9][0-9][0-9]_*.sql); shopt -u nullglob
[[ ${#FILES[@]} -gt 0 ]] || die "no migrations in $MIG_DIR"
declare -A APPLIED=()
if [[ "$HAVE_LEDGER" == t ]]; then
  while IFS='|' read -r fn h; do [[ -n "$fn" ]] && APPLIED["$fn"]="$h"; done < <(q "select filename, sha256 from drugbox_deploy.migrations order by filename")
fi
info "${#FILES[@]} migration files in ${MIG_DIR#"$REPO"/}; ${#APPLIED[@]} recorded as applied"
if [[ ${#APPLIED[@]} -eq 0 && -z "$BASELINE" && "$(q "select to_regclass('public.profiles') is not null")" == t ]]; then
  die "the database already has Drugbox tables but no ledger — migrations were applied by hand.
    Find the last one applied and record the files up to it: --baseline-through NNNN (they are not run again)."
fi
CHANGED=() PENDING=() LAST_APPLIED=''
for f in "${FILES[@]}"; do
  b="$(basename "$f")"; [[ "$b" =~ ^[0-9]{4}_[A-Za-z0-9_.-]+\.sql$ ]] || die "unexpected migration file name: $b"
  h="$(sha256 "$f")"
  if [[ -n "${APPLIED[$b]:-}" ]]; then
    [[ "${APPLIED[$b]}" == "$h" ]] || CHANGED+=("$b (applied ${APPLIED[$b]:0:12}…, file now ${h:0:12}…)")
    LAST_APPLIED="$b"; unset 'APPLIED[$b]'
  else PENDING+=("$f"); fi
done
for b in "${!APPLIED[@]}"; do warn "recorded as applied but not in ${MIG_DIR#"$REPO"/}: $b"; done
if [[ ${#CHANGED[@]} -gt 0 ]]; then
  printf '      %s\n' "${CHANGED[@]}" >&2
  die "${#CHANGED[@]} migration file(s) changed AFTER they were applied to this database. Applied migrations are never edited:
    restore the file (git checkout -- supabase/migrations/…) and put the change in a NEW migration (the next number)."
fi
for f in "${PENDING[@]}"; do b="$(basename "$f")"
  if [[ -n "$LAST_APPLIED" && "$b" < "$LAST_APPLIED" && ( -z "$BASELINE" || "${b:0:4}" > "$BASELINE" ) ]]; then
    die "$b sorts before the already-applied $LAST_APPLIED — a migration was inserted into the past; give it the next number instead"
  fi
done
if [[ -n "$BASELINE" ]]; then
  KEEP=()
  for f in "${PENDING[@]}"; do b="$(basename "$f")"
    if [[ "${b:0:4}" > "$BASELINE" ]]; then KEEP+=("$f"); continue; fi
    if [[ $DRY == 1 ]]; then info "(dry run) would record $b as applied (baseline)"
    else q "insert into drugbox_deploy.migrations (filename, sha256, mode) values ('$b', '$(sha256 "$f")', 'baseline')" >/dev/null; warn "baseline: recorded $b as applied WITHOUT running it"; fi
  done
  PENDING=("${KEEP[@]+"${KEEP[@]}"}")
fi
ok "ledger checked: ${#PENDING[@]} to apply, no changed files"

# ── 3. apply ──────────────────────────────────────────────────────────────────────────────────────────────────────────────
step "3. Migrations"
TX_UNSAFE='^[[:space:]]*(begin|commit|rollback|start[[:space:]]+transaction)[[:space:]]*;|\bconcurrently\b|^[[:space:]]*vacuum\b|alter[[:space:]]+system|create[[:space:]]+database|alter[[:space:]]+type[[:space:]].*[[:space:]]add[[:space:]]+value'
if [[ ${#PENDING[@]} -eq 0 ]]; then ok "nothing to apply — the database is up to date"; fi
for f in "${PENDING[@]}"; do
  b="$(basename "$f")"; h="$(sha256 "$f")"; mode=transaction
  if sed 's/--.*$//' "$f" | grep -qiE "$TX_UNSAFE"; then mode=autocommit; fi
  if [[ $DRY == 1 ]]; then info "(dry run) would apply $b ($mode, sha256 ${h:0:12}…)"; continue; fi
  t0=$(date +%s%3N); esc="${f//\'/\'\'}"
  {
    echo "set lock_timeout = '${DEPLOY_LOCK_TIMEOUT:-60s}'; set statement_timeout = 0;"
    echo "select extract(epoch from clock_timestamp()) as dx_t0 \\gset"
    [[ $mode == transaction ]] && echo "begin;" && echo "do \$\$ begin perform pg_advisory_xact_lock(hashtext('drugbox_deploy')); end \$\$;"
    echo "\\i '$esc'"
    echo "insert into drugbox_deploy.migrations (filename, sha256, duration_ms, mode) values ('$b', '$h', ((extract(epoch from clock_timestamp()) - :dx_t0) * 1000)::int, '$mode');"
    [[ $mode == transaction ]] && echo "commit;"
  } > "$LOG.cur"
  echo "-- $b ($mode)" >>"$LOG"
  if ! "${PSQL[@]}" -d "$DB_URL" -f "$LOG.cur" >>"$LOG" 2>&1; then
    rm -f "$LOG.cur"; grep -E 'ERROR|FATAL' "$LOG" | tail -5 >&2
    die "$b failed — $( [[ $mode == transaction ]] && echo 'rolled back: nothing of it was applied' || echo 'NOT transactional: check what was applied' ). Full output: ${LOG#"$REPO"/}"
  fi
  rm -f "$LOG.cur"
  ok "$b  ($(( $(date +%s%3N) - t0 )) ms, $mode)"
done
grep -h 'DRUGBOX' "$LOG" | sed 's/^/    note: /' | sort -u || true
if [[ $DRY == 1 && ${#PENDING[@]} -gt 0 ]]; then step "Dry run — stopping before the checks (${#PENDING[@]} migration(s) not applied)"; exit 0; fi

# ── 4. checks ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
step "4. Checks"
FAILS=0
SWEEP="$("${PSQL[@]}" -At -d "$DB_URL" -f "$REPO/supabase/tests/schema_sweep.sql" 2>>"$LOG")" || die "schema_sweep.sql failed to run (see ${LOG#"$REPO"/})"
while IFS= read -r line; do [[ -z "$line" ]] && continue
  if [[ "$line" == *": none" ]]; then ok "sweep — $line"; else printf '    \033[31mFAIL\033[0m sweep — %s\n' "$line" >&2; FAILS=$((FAILS + 1)); fi
done <<<"$SWEEP"
[[ "$(grep -c ': none$' <<<"$SWEEP")" -ge 3 ]] || { warn "schema_sweep printed fewer lines than expected"; FAILS=$((FAILS + 1)); }

BUCKETS="$(q "select coalesce(string_agg(format('%s (%s)', e.id, case when e.pub then 'public' else 'private' end), ', '), '') from (values ('videos', true), ('post-media', true), ('message-media', false), ('documents', false), ('reference-evidence', false)) e(id, pub) where not exists (select 1 from storage.buckets b where b.id = e.id and b.public = e.pub)")"
if [[ -z "$BUCKETS" ]]; then ok "storage buckets: videos, post-media (public); message-media, documents, reference-evidence (private)"
else printf '    \033[31mFAIL\033[0m storage buckets missing or wrong visibility: %s\n' "$BUCKETS" >&2; FAILS=$((FAILS + 1)); fi

RT="$(q "select coalesce(string_agg(t, ', '), '') from unnest(array['messages','notifications']) t where not exists (select 1 from pg_publication_tables p where p.pubname = 'supabase_realtime' and p.schemaname = 'public' and p.tablename = t)")"
if [[ -z "$RT" ]]; then ok "realtime publication: public.messages, public.notifications"
else printf '    \033[31mFAIL\033[0m not in the supabase_realtime publication: %s\n' "$RT" >&2; FAILS=$((FAILS + 1)); fi

# The app reaches tables through the API roles. Supabase is moving new projects to NOT granting new public tables to the API roles
# automatically (api.auto_expose_new_tables, from 2026-10-30), and the migrations rely on those default grants — so check them.
GRANTS="$(q "select coalesce(string_agg(distinct r.role || ' cannot read ' || p.tablename, ', '), '') from pg_policies p
  cross join lateral unnest(case when 'public' = any(p.roles) then array['anon','authenticated']::name[] else p.roles end) r(role)
 where p.schemaname = 'public' and p.cmd in ('SELECT', 'ALL') and r.role in ('anon', 'authenticated')
   and not has_any_column_privilege(r.role, format('public.%I', p.tablename), 'SELECT')")"
SEQS="$(q "select coalesce(string_agg(distinct c.relname || ' (' || s.relname || ')', ', '), '') from pg_class c join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
  join pg_attrdef d on d.adrelid = c.oid join pg_depend dep on dep.classid = 'pg_attrdef'::regclass and dep.objid = d.oid and dep.refclassid = 'pg_class'::regclass
  join pg_class s on s.oid = dep.refobjid and s.relkind = 'S'
 where c.relkind = 'r' and has_table_privilege('authenticated', c.oid, 'INSERT')
   and case when s.relkind = 'S' then not has_sequence_privilege('authenticated', s.oid, 'USAGE') else false end")"
if [[ -z "$GRANTS" && -z "$SEQS" ]]; then ok "API grants: every table with a read policy is readable by its role; inserts can use their sequences"
else
  if [[ -n "$GRANTS" ]]; then
    IFS=',' read -ra GL <<<"$GRANTS"
    printf '    \033[31mFAIL\033[0m %d policies without the table grant, e.g. %s%s\n' "${#GL[@]}" "$(printf '%s,' "${GL[@]:0:8}" | sed 's/,$//')" "$( [[ ${#GL[@]} -gt 8 ]] && echo ' …')" >&2
  fi
  [[ -n "$SEQS" ]] && printf '    \033[31mFAIL\033[0m insert allowed but its sequence is not: %s\n' "$SEQS" >&2
  info "The project does not grant new tables to the API roles. Fix with a new migration that grants them explicitly"
  info "(grant select … to anon, authenticated; grant usage on sequences … to authenticated) — see docs/LAUNCH.md."
  FAILS=$((FAILS + 1))
fi

JIT_SQL="select coalesce(string_agg(distinct r.rolname, ','), '') from pg_db_role_setting s join pg_roles r on r.oid = s.setrole left join pg_database d on d.oid = s.setdatabase
 where 'jit=off' = any(s.setconfig) and (s.setdatabase = 0 or d.datname = current_database())"
JIT="$(q "$JIT_SQL")"
if [[ ",$JIT," != *,authenticator,* && $DRY == 0 ]]; then
  q "do \$\$ begin
    if exists (select 1 from pg_roles where rolname = 'authenticator') then execute format('alter role authenticator in database %I set jit = off', current_database()); end if;
  exception when insufficient_privilege then
    begin alter role anon set jit = off; alter role authenticated set jit = off; alter role service_role set jit = off;
    exception when insufficient_privilege then null; end;
  end \$\$" >/dev/null 2>>"$LOG" || true
  JIT="$(q "$JIT_SQL")"
fi
if [[ ",$JIT," == *,authenticator,* ]]; then ok "jit = off for authenticator (the API login role)"
elif [[ ",$JIT," == *,anon,* && ",$JIT," == *,authenticated,* ]]; then ok "jit = off for anon + authenticated (authenticator may not be altered here; PostgREST applies the request role's settings)"
else warn "jit is still on for API requests — in the SQL editor run: alter role authenticator in database postgres set jit = off;"; fi

if [[ "$(q "select count(*) from pg_extension where extname = 'pg_cron'")" == 1 ]]; then
  if [[ "$(q "select count(*) from cron.job where jobname = 'drugbox-expire-vip'")" == 0 && $DRY == 0 ]]; then
    q "select cron.schedule('drugbox-expire-vip', '17 1 * * *', 'select public.expire_vip_plans()')" >/dev/null && ok "pg_cron: scheduled drugbox-expire-vip (daily 01:17 UTC)"
  else ok "pg_cron: drugbox-expire-vip is scheduled"; fi
else info "pg_cron is not enabled: VIP plans are not expired automatically — enable it (Database → Extensions → pg_cron) and re-run this script"; fi

if [[ "$(q "select to_regclass('public.payment_products') is not null")" == t ]]; then
  info "prices (payment_products — confirm before launch, +VAT):"
  q "select format('%-10s EGP %s / %s days%s', code, to_char(amount_egp, 'FM999,990'), duration_days, case when active then '' else ' (inactive)' end) from public.payment_products order by kind, amount_egp" | sed 's/^/      /'
fi
[[ $FAILS -eq 0 ]] || die "$FAILS check(s) failed — the database is NOT ready (details above; full log ${LOG#"$REPO"/})"
ok "database ready"

# ── 5. Edge Functions ─────────────────────────────────────────────────────────────────────────────────────────────────────
if [[ $DB_ONLY == 1 ]]; then step "5. Edge Functions — skipped (--db-only)"; info "log: ${LOG#"$REPO"/}"; exit 0; fi
step "5. Edge Functions"
REF="${SUPABASE_PROJECT_REF:-$DB_REF}"
FN_FILE="${FN_ENV:-$DEPLOY_DIR/.env.functions$SUFFIX}"
[[ -f "$FN_FILE" ]] || die "no $FN_FILE — copy deploy/env.functions.example and fill it ($( [[ $PROD == 1 ]] && echo LIVE || echo TEST ) keys)"
python3 - "$FN_FILE" "$PROD" <<'PY' || die "fix $FN_FILE (nothing was sent)"
import re, sys
path, prod = sys.argv[1], sys.argv[2] == '1'; env = {}
for n, line in enumerate(open(path, encoding='utf-8'), 1):
    s = line.strip()
    if not s or s.startswith('#'): continue
    m = re.match(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$', s)
    if not m: sys.exit(f'{path} line {n} is not KEY=VALUE')
    v = m.group(2).strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'': v = v[1:-1]
    env[m.group(1)] = v
bad = []
required = ['APP_URL', 'ALLOWED_ORIGINS', 'PAYMOB_SECRET_KEY', 'PAYMOB_PUBLIC_KEY', 'PAYMOB_HMAC_SECRET', 'PAYMOB_CARD_INTEGRATION_ID',
            'PAYMOB_WALLET_INTEGRATION_ID', 'FAWRY_MERCHANT_CODE', 'FAWRY_SECURE_KEY', 'INSTAPAY_ADDRESS']
for k in required:
    v = env.get(k, '')
    if not v or '…' in v or 'CHANGE_ME' in v or v.startswith('<'): bad.append(f'{k} is empty or still a placeholder')
for k in env:
    if k.startswith('SUPABASE_'): bad.append(f'{k}: SUPABASE_* names are set by Supabase itself (remove it from the file)')
for k in ('PAYMOB_CARD_INTEGRATION_ID', 'PAYMOB_WALLET_INTEGRATION_ID'):
    if env.get(k) and not env[k].isdigit(): bad.append(f'{k} must be a number')
if not env.get('APP_URL', '').startswith('https://'): bad.append('APP_URL must be the https:// address of the web app')
for o in filter(None, (x.strip() for x in env.get('ALLOWED_ORIGINS', '').split(','))):
    if not re.fullmatch(r'https://[a-z0-9.-]+(:\d+)?', o): bad.append(f'ALLOWED_ORIGINS entry {o!r} must be an origin like https://app.example.com (no path)')
test_keys = any('_test_' in env.get(k, '') for k in ('PAYMOB_SECRET_KEY', 'PAYMOB_PUBLIC_KEY'))
live_keys = any('_live_' in env.get(k, '') for k in ('PAYMOB_SECRET_KEY', 'PAYMOB_PUBLIC_KEY'))
fawry_staging = 'fawrystaging' in env.get('FAWRY_BASE', '')
if prod and (test_keys or fawry_staging): bad.append('production with Paymob TEST keys or Fawry STAGING (FAWRY_BASE) — use the live values')
if not prod and live_keys: bad.append('staging with Paymob LIVE keys — staging must use test keys (real money otherwise)')
if not prod and env.get('FAWRY_BASE', 'https://www.atfawry.com').rstrip('/') == 'https://www.atfawry.com': bad.append('staging without FAWRY_BASE=https://atfawry.fawrystaging.com (Fawry production otherwise)')
if bad: print('\n'.join('    - ' + b for b in bad), file=sys.stderr); sys.exit(1)
print('    secrets file checked: ' + ', '.join(sorted(env)))
PY
# shellcheck disable=SC2206  # word-split on purpose: a command plus its arguments
SB=(${SUPABASE_CLI:-npx --yes supabase@2.120.0})
export SUPABASE_ACCESS_TOKEN
info "setting function secrets on project $REF (names above; values are not printed)"
sb() { local rc=0; "${SB[@]}" "$@" >"$LOG.cli" 2>&1 || rc=$?; cat "$LOG.cli" >>"$LOG"; [[ $rc == 0 ]] || tail -5 "$LOG.cli" | sed 's/^/      /' >&2; rm -f "$LOG.cli"; return $rc; }
sb secrets set --env-file "$FN_FILE" --project-ref "$REF" || die "supabase secrets set failed (is SUPABASE_ACCESS_TOKEN valid for project $REF?)"
ok "secrets set"
# The CLI expects index.ts; ours are index.js — deploy from a scratch copy with a config.toml naming each entrypoint and its JWT rule.
# payments-create: the browser calls it with the user's JWT (verify_jwt on; the function also acts AS the user in the database).
# paymob-webhook / fawry-webhook: called by Paymob / Fawry with no Supabase JWT (verify_jwt off) — they verify the provider's signature.
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/supabase"; cp -r "$REPO/supabase/functions" "$WORK/supabase/functions"
{ echo 'project_id = "drugbox"'
  for fn in payments-create:true paymob-webhook:false fawry-webhook:false; do
    printf '\n[functions.%s]\nverify_jwt = %s\nentrypoint = "./functions/%s/index.js"\n' "${fn%%:*}" "${fn##*:}" "${fn%%:*}"
  done; } > "$WORK/supabase/config.toml"
for fn in payments-create paymob-webhook fawry-webhook; do
  extra=(); [[ $fn != payments-create ]] && extra=(--no-verify-jwt)
  info "deploying $fn $( [[ ${#extra[@]} -gt 0 ]] && echo '(public: provider callback, signature-checked)' || echo '(user JWT required)')"
  sb functions deploy "$fn" --project-ref "$REF" --use-api --workdir "$WORK" "${extra[@]}" || die "deploy of $fn failed"
  ok "$fn deployed"
done
if [[ $SKIP_SMOKE == 0 ]]; then
  need curl
  FNURL="${SUPABASE_FUNCTIONS_URL:-https://$REF.supabase.co/functions/v1}"
  ORIGIN="$(python3 - "$FN_FILE" <<'PY'
import re, sys
env = dict(m.groups() for m in (re.match(r'^(?:export\s+)?([A-Za-z_]\w*)=["\']?(.*?)["\']?\s*$', l.strip()) for l in open(sys.argv[1])) if m)
print((env.get('ALLOWED_ORIGINS', '').split(',')[0] or env.get('APP_URL', '')).strip().rstrip('/'))
PY
)"
  for fn in paymob-webhook fawry-webhook; do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$FNURL/$fn" || echo 000)"
    if [[ "$code" == 405 ]]; then ok "smoke: GET $fn → 405 (the function itself answers: it is up, and POST-only)"
    else warn "smoke: GET $fn → $code (expected 405 from the function) — check Edge Functions → $fn → Logs"; FAILS=$((FAILS + 1)); fi
  done
  hdr="$(curl -s -D - -o /dev/null --max-time 20 -X OPTIONS -H "Origin: $ORIGIN" -H 'Access-Control-Request-Method: POST' "$FNURL/payments-create" || true)"
  code="$(awk 'NR==1{print $2}' <<<"$hdr")"
  if [[ "$code" =~ ^20[04]$ ]] && grep -qi "^access-control-allow-origin: $ORIGIN" <<<"$hdr"; then ok "smoke: browser preflight to payments-create from $ORIGIN → $code with CORS"
  else warn "smoke: preflight to payments-create from $ORIGIN → ${code:-no answer} without the CORS header — check ALLOWED_ORIGINS / the function logs"; FAILS=$((FAILS + 1)); fi
  [[ $FAILS -eq 0 ]] || die "$FAILS smoke check(s) failed"
fi
step "Done — $TARGET project $REF"
info "Provider callbacks: Paymob (card + wallet integrations, transaction processed) → https://$REF.supabase.co/functions/v1/paymob-webhook"
info "                    Fawry server notification V2                            → https://$REF.supabase.co/functions/v1/fawry-webhook"
info "Web build: DRUGBOX_SUPABASE_URL=https://$REF.supabase.co and the anon key (Settings → API) in deploy/.env.web$SUFFIX, then deploy/vercel_deploy.sh$( [[ $PROD == 1 ]] && echo ' --prod')"
info "log: ${LOG#"$REPO"/}"
