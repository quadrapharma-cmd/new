# shellcheck shell=bash
# Shared helpers for deploy/*.sh — sourced, never run. No secret value is ever printed: only names, hosts and checksums.
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$DEPLOY_DIR")"
export DEPLOY_DIR REPO

if [[ -t 1 ]]; then _B=$'\033[1m'; _G=$'\033[32m'; _Y=$'\033[33m'; _R=$'\033[31m'; _N=$'\033[0m'; else _B=''; _G=''; _Y=''; _R=''; _N=''; fi
step() { printf '\n%s==> %s%s\n' "$_B" "$*" "$_N"; }
info() { printf '    %s\n' "$*"; }
ok()   { printf '    %sOK%s  %s\n' "$_G" "$_N" "$*"; }
warn() { printf '    %sWARN%s %s\n' "$_Y" "$_N" "$*" >&2; }
die()  { printf '\n%sFAILED:%s %s\n' "$_R" "$_N" "$*" >&2; exit 1; }
need() { local c; for c in "$@"; do command -v "$c" >/dev/null 2>&1 || die "'$c' is not installed (needed by $(basename "$0"))"; done; }

# load_env_file FILE — KEY=VALUE lines (# comments, blank lines, optional "export ", optional quotes). The file is PARSED, never
# executed. A variable already set in the environment wins over the file. Prints the names it set, never the values.
load_env_file() {
  local f="$1" line key val n=0 names=()
  [[ -f "$f" ]] || return 1
  if [[ "$(stat -c '%a' "$f" 2>/dev/null || echo 600)" =~ [0-7][0-7][1-7]$ ]]; then warn "$f is readable by other users — chmod 600 $f"; fi
  while IFS= read -r line || [[ -n "$line" ]]; do
    n=$((n + 1)); line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*(#|$) ]] && continue
    line="${line#"${line%%[![:space:]]*}"}"; line="${line#export }"
    [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || die "$f line $n is not KEY=VALUE"
    key="${BASH_REMATCH[1]}"; val="${BASH_REMATCH[2]}"
    [[ "$key" =~ ^(LD_.*|DYLD_.*|BASH.*|PATH|IFS|PS4|ENV|SHELLOPTS|PROMPT_COMMAND|PYTHON.*|NODE_OPTIONS|PERL5.*|HOME)$ ]] && die "$f line $n sets $key — not a Drugbox setting (refused: it would change how the tools run)"
    if [[ "$val" =~ ^\"(.*)\"[[:space:]]*(#.*)?$ ]] || [[ "$val" =~ ^\'(.*)\'[[:space:]]*(#.*)?$ ]]; then val="${BASH_REMATCH[1]}"
    else val="${val%%[[:space:]]#*}"; val="${val%"${val##*[![:space:]]}"}"; fi
    if [[ -z "${!key+x}" ]]; then printf -v "$key" '%s' "$val"; export "${key?}"; names+=("$key"); fi
  done < "$f"
  info "read ${#names[@]} setting(s) from ${f#"$REPO"/}: ${names[*]:-(all already set in the environment)}"
}

# jwt_claim TOKEN CLAIM — a claim from a JWT's payload (no verification: used only to tell anon from service keys and to read "ref")
jwt_claim() {
  python3 - "$1" "$2" <<'PY'
import sys, json, base64
try:
    p = sys.argv[1].split('.')[1]; print(json.loads(base64.urlsafe_b64decode(p + '=' * (-len(p) % 4))).get(sys.argv[2], ''))
except Exception: print('')
PY
}

# db_url_split URL — prints (NUL-separated) the URL WITHOUT its password, the password, the host, the port, the user, the database.
# The URL goes to python in the environment, not as an argument: a command line (with the password in it) is visible to every user in `ps`.
db_url_split() {
  DX_SPLIT_URL="$1" python3 - <<'PY'
import os, sys
from urllib.parse import urlsplit, urlunsplit, unquote
u = urlsplit(os.environ['DX_SPLIT_URL'])
if u.scheme not in ('postgres', 'postgresql') or not u.hostname: sys.exit('not a postgres:// URL')
user = unquote(u.username or ''); pw = unquote(u.password or ''); host = u.hostname; port = str(u.port or 5432)
netloc = (u.netloc.rsplit('@', 1)[0].split(':', 1)[0] + '@' if u.username else '') + u.netloc.rsplit('@', 1)[-1]
sys.stdout.write('\0'.join([urlunsplit((u.scheme, netloc, u.path, u.query, '')), pw, host, port, user, unquote(u.path.lstrip('/')) or 'postgres']) + '\0')
PY
}

# ref_from_host HOST USER — the Supabase project ref of a db.<ref>.supabase.co host or a postgres.<ref> pooler user (empty otherwise)
ref_from_host() {
  if [[ "$1" =~ ^db\.([a-z0-9]{20})\.supabase\.co$ ]]; then echo "${BASH_REMATCH[1]}"
  elif [[ "$2" =~ ^postgres\.([a-z0-9]{20})$ ]]; then echo "${BASH_REMATCH[1]}"
  else echo ''; fi
}
is_local_host() { [[ "$1" == 127.* || "$1" == localhost || "$1" == ::1 || "$1" == /* ]]; }

# resolve_db — sets DB_URL (no password), exports PGPASSWORD, DB_HOST/DB_PORT/DB_USER/DB_NAME and DB_REF.
# Input: SUPABASE_DB_URL, or SUPABASE_PROJECT_REF + SUPABASE_DB_PASSWORD (direct host db.<ref>.supabase.co:5432; override
# SUPABASE_DB_HOST / SUPABASE_DB_PORT / SUPABASE_DB_USER for the session pooler when the direct host is IPv6-only for you).
resolve_db() {
  local raw="${SUPABASE_DB_URL:-}" parts=()
  [[ -z "${SUPABASE_PROJECT_REF:-}" || "$SUPABASE_PROJECT_REF" =~ ^[a-z0-9]{20}$ ]] || die "SUPABASE_PROJECT_REF must be the 20-letter project ref (the <ref> in https://<ref>.supabase.co)"
  [[ -z "${SUPABASE_PROD_REF:-}" || "$SUPABASE_PROD_REF" =~ ^[a-z0-9]{20}$ ]] || die "SUPABASE_PROD_REF must be a 20-letter project ref"
  if [[ -z "$raw" ]]; then
    [[ -n "${SUPABASE_PROJECT_REF:-}" && -n "${SUPABASE_DB_PASSWORD:-}" ]] || die "set SUPABASE_DB_URL, or SUPABASE_PROJECT_REF + SUPABASE_DB_PASSWORD (see deploy/env.supabase.example)"
    raw="postgresql://${SUPABASE_DB_USER:-postgres}@${SUPABASE_DB_HOST:-db.${SUPABASE_PROJECT_REF}.supabase.co}:${SUPABASE_DB_PORT:-5432}/postgres"
    export PGPASSWORD="$SUPABASE_DB_PASSWORD"
  fi
  mapfile -d '' parts < <(db_url_split "$raw") || true
  [[ ${#parts[@]} -eq 6 ]] || die "SUPABASE_DB_URL is not a postgres:// URL"
  DB_URL="${parts[0]}"; DB_HOST="${parts[2]}"; DB_PORT="${parts[3]}"; DB_USER="${parts[4]}"; DB_NAME="${parts[5]}"
  if [[ -n "${parts[1]}" ]]; then export PGPASSWORD="${parts[1]}"
  elif [[ -n "${SUPABASE_DB_URL:-}" && -n "${SUPABASE_DB_PASSWORD:-}" ]]; then export PGPASSWORD="$SUPABASE_DB_PASSWORD"; fi   # URL without its password + the password apart
  [[ "$DB_PORT" == 6543 ]] && die "port 6543 is Supabase's TRANSACTION pooler — migrations need a session: use port 5432 (direct host or session pooler)"
  if ! is_local_host "$DB_HOST" && [[ "$DB_URL" != *sslmode=* ]]; then export PGSSLMODE="${PGSSLMODE:-require}"; fi
  DB_REF="$(ref_from_host "$DB_HOST" "$DB_USER")"
  if [[ -n "${SUPABASE_PROJECT_REF:-}" && -n "$DB_REF" && "$DB_REF" != "$SUPABASE_PROJECT_REF" ]]; then
    die "SUPABASE_PROJECT_REF ($SUPABASE_PROJECT_REF) and the database URL (project $DB_REF) name different projects"
  fi
  DB_REF="${DB_REF:-${SUPABASE_PROJECT_REF:-}}"
  export DB_URL DB_HOST DB_PORT DB_USER DB_NAME DB_REF
}

# prod_guard REF IS_PROD — production only with --prod, and --prod only for the declared production project (SUPABASE_PROD_REF)
prod_guard() {
  local ref="$1" prod="$2" pr="${SUPABASE_PROD_REF:-}"
  if [[ "$prod" == 1 ]]; then
    [[ -n "$pr" ]] || die "--prod needs SUPABASE_PROD_REF (the production project ref) so the scripts can tell production apart"
    [[ "$ref" == "$pr" ]] || die "--prod was given but the target project is '${ref:-unknown}', not the production project '$pr'"
    warn "PRODUCTION target: project $pr"
  else
    [[ -n "$pr" && -n "$ref" && "$ref" == "$pr" ]] && die "project $ref is PRODUCTION (SUPABASE_PROD_REF) — re-run with --prod if that is really what you want"
    # a real Supabase project without SUPABASE_PROD_REF: a brand-new production project has no stamp yet, so without the ref a
    # staging run (test keys, rehearsal data) could land on production unnoticed — refuse instead of guessing
    [[ -z "$pr" && -n "$ref" ]] && die "set SUPABASE_PROD_REF (the PRODUCTION project's ref) in the settings file — also for staging: it is what tells the two apart"
    [[ -z "$pr" ]] && warn "SUPABASE_PROD_REF is not set: the production check relies on the database's own environment stamp only"
  fi
  return 0
}

PSQL=(psql -X -q -v ON_ERROR_STOP=1)
q()  { "${PSQL[@]}" -At -d "$DB_URL" -c "$1"; }                     # one query, unaligned, tuples only
sha256() { sha256sum "$1" | cut -d' ' -f1; }
