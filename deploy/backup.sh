#!/usr/bin/env bash
# Drugbox — encrypted database backups and the restore drill.
#
#   deploy/backup.sh [--prod]                      take a backup of SUPABASE_DB_URL into BACKUP_DIR, keep the newest BACKUP_RETENTION
#   deploy/backup.sh --restore-drill [--file F]    restore the newest backup (or F) into the EMPTY database DRILL_DB_URL, then check it:
#                                                  schema_sweep.sql must print "none" on every line and every table's row count must
#                                                  equal the count recorded in the backup's manifest
#   deploy/backup.sh --list                        list the backups
#   deploy/backup.sh --gen-key FILE                write a new random key to FILE (mode 600) — keep a copy OFF this machine
#
# Settings (environment, or deploy/.env.supabase — .prod with --prod; the environment wins). See deploy/env.supabase.example.
#   SUPABASE_DB_URL (or SUPABASE_PROJECT_REF + SUPABASE_DB_PASSWORD)  the database to back up
#   DRUGBOX_BACKUP_KEY_FILE   file holding the encryption passphrase (preferred)   — or DRUGBOX_BACKUP_KEY in the environment
#   BACKUP_DIR                where backups go (default deploy/backups — git-ignored; copy them to storage you control)
#   BACKUP_RETENTION          how many backups of this database to keep (default 8: two months of weekly backups)
#   DRILL_DB_URL              --restore-drill only: an EMPTY scratch database (never the live one)
#
# Format: pg_dump custom format of the app's schemas (public, private, drugbox_deploy) + auth and storage (+ pgcrypto/pg_trgm/uuid-ossp),
# streamed through openssl AES-256-CBC (PBKDF2, 600k iterations, random salt) — the key is read from the file/environment, never
# from the command line. A manifest beside it holds the sha256 and an HMAC-SHA256 of the encrypted file and the row count of every
# table IN THE ARCHIVE (counted from the dump stream itself, so the drill compares like with like).
# Supabase's daily backups / Point-in-Time Recovery stay the first line of defence; this is the copy you control.
set -euo pipefail
# shellcheck source=deploy/lib.sh
source "$(dirname "$0")/lib.sh"

MODE=backup PROD=0 ENV_FILE='' FILE='' GENKEY=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod) PROD=1 ;;
    --restore-drill) MODE=drill ;;
    --list) MODE=list ;;
    --gen-key) MODE=genkey; GENKEY="${2:?--gen-key needs a file name}"; shift ;;
    --file) FILE="${2:?}"; shift ;;
    --env-file) ENV_FILE="${2:?}"; shift ;;
    -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option $1 (see --help)" ;;
  esac; shift
done
need openssl python3 sha256sum
umask 077
ITER=600000
ENC_OPTS=(-aes-256-cbc -pbkdf2 -iter "$ITER" -md sha256)

if [[ $MODE == genkey ]]; then
  [[ -e "$GENKEY" ]] && die "$GENKEY exists — not overwriting a key (backups made with it would become unreadable)"
  openssl rand -base64 48 > "$GENKEY"; chmod 600 "$GENKEY"
  ok "new key in $GENKEY (mode 600). Store a copy in a password manager / offline: without it the backups cannot be restored."; exit 0
fi

SUFFIX=''; [[ $PROD == 1 ]] && SUFFIX='.prod'
load_env_file "${ENV_FILE:-$DEPLOY_DIR/.env.supabase$SUFFIX}" >/dev/null || true   # (stderr stays: a malformed file must say so)
BACKUP_DIR="${BACKUP_DIR:-$DEPLOY_DIR/backups}"; BACKUP_RETENTION="${BACKUP_RETENTION:-8}"
[[ "$BACKUP_RETENTION" =~ ^[1-9][0-9]*$ ]] || die "BACKUP_RETENTION must be a positive number"
mkdir -p "$BACKUP_DIR"; BACKUP_DIR="$(cd "$BACKUP_DIR" && pwd)"

# the key: a file (preferred) or the environment; openssl reads it itself (-pass file:/env:), it never appears on a command line
key_setup() {
  if [[ -n "${DRUGBOX_BACKUP_KEY_FILE:-}" ]]; then
    [[ -r "$DRUGBOX_BACKUP_KEY_FILE" ]] || die "cannot read DRUGBOX_BACKUP_KEY_FILE ($DRUGBOX_BACKUP_KEY_FILE)"
    [[ "$(stat -c '%a' "$DRUGBOX_BACKUP_KEY_FILE")" =~ ^[0-7]00$ ]] || die "$DRUGBOX_BACKUP_KEY_FILE must be private: chmod 600 $DRUGBOX_BACKUP_KEY_FILE"
    PASS_ARG="file:$DRUGBOX_BACKUP_KEY_FILE"; KEYSRC="file $DRUGBOX_BACKUP_KEY_FILE"
  elif [[ -n "${DRUGBOX_BACKUP_KEY:-}" ]]; then export DRUGBOX_BACKUP_KEY; PASS_ARG="env:DRUGBOX_BACKUP_KEY"; KEYSRC="environment DRUGBOX_BACKUP_KEY"
  else die "no key: set DRUGBOX_BACKUP_KEY_FILE (create one with: deploy/backup.sh --gen-key ~/.drugbox-backup.key)"; fi
  python3 - <<'PY' || die "the backup key is too short (32+ characters; use --gen-key)"
import os, sys
k = open(os.environ['DRUGBOX_BACKUP_KEY_FILE']).readline().strip() if os.environ.get('DRUGBOX_BACKUP_KEY_FILE') else os.environ.get('DRUGBOX_BACKUP_KEY', '')
sys.exit(0 if len(k) >= 32 else 1)
PY
}
# hmac FILE — HMAC-SHA256 of a file with a key derived from the backup key (the key is read inside python, not passed)
hmac_of() {
  python3 - "$1" <<'PY'
import os, sys, hmac, hashlib
k = open(os.environ['DRUGBOX_BACKUP_KEY_FILE']).readline().strip() if os.environ.get('DRUGBOX_BACKUP_KEY_FILE') else os.environ['DRUGBOX_BACKUP_KEY']
h = hmac.new(hashlib.sha256(b'drugbox-backup-hmac\0' + k.encode()).digest(), digestmod=hashlib.sha256)
with open(sys.argv[1], 'rb') as f:
    for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
print(h.hexdigest())
PY
}
# the row count of every table in a custom-format archive read on stdin (from its COPY blocks)
count_copy_rows() { pg_restore -f - 2>/dev/null | awk '/^COPY /{t=$2; n=0; f=1; next} f && $0 == "\\." {print t "|" n; f=0; next} f {n++}'; }
mval() { sed -n "s/^$2=//p" "$1" | head -1; }

if [[ $MODE == list ]]; then
  step "Backups in ${BACKUP_DIR#"$REPO"/}"
  shopt -s nullglob; for f in "$BACKUP_DIR"/drugbox-*.dump.enc; do
    m="${f%.dump.enc}.manifest"
    info "$(basename "$f")  $(du -h "$f" | cut -f1)  $( [[ -f "$m" ]] && echo "$(mval "$m" environment) $(mval "$m" source) $(grep -c '|' "$m") tables" || echo 'NO MANIFEST')"
  done; exit 0
fi

if [[ $MODE == backup ]]; then
  need pg_dump pg_restore psql
  step "Backup"
  resolve_db; prod_guard "$DB_REF" "$PROD"; key_setup
  STAMP="$(q "select case when to_regclass('drugbox_deploy.environment') is null then '' else (select coalesce(max(name), '') from drugbox_deploy.environment) end")"
  [[ "$STAMP" == production && $PROD == 0 ]] && die "this database is stamped PRODUCTION — run with --prod (and deploy/.env.supabase.prod)"
  [[ $PROD == 1 && -n "$STAMP" && "$STAMP" != production ]] && die "--prod was given but this database is stamped '$STAMP'"
  SVN="$(q "select current_setting('server_version_num')::int / 10000")"; DVN="$(pg_dump --version | grep -oE '[0-9]+' | head -1)"
  (( DVN >= SVN )) || die "pg_dump $DVN is older than the server ($SVN): install the PostgreSQL $SVN client tools"
  LABEL="${DB_REF:-$DB_NAME}"; TS="$(date -u +%Y%m%dT%H%M%SZ)"; BASE="$BACKUP_DIR/drugbox-$LABEL-$TS"
  info "source: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME (${STAMP:-unstamped})   key: $KEYSRC   → ${BASE#"$REPO"/}.dump.enc"
  # the app's schemas (public, private, drugbox_deploy, …) + Supabase's auth and storage; not the platform's own schemas
  SCHEMAS=() NAMES=()
  while IFS= read -r s; do SCHEMAS+=(-n "$s"); NAMES+=("$s"); done < <(q "select nspname from pg_namespace where nspname !~ '^(pg_|_)' and nspname not in
    ('information_schema', 'extensions', 'graphql', 'graphql_public', 'realtime', 'supabase_functions', 'supabase_migrations', 'vault', 'pgsodium',
     'pgsodium_masks', 'net', 'cron', 'pgbouncer', 'pgtle', 'repack', 'topology', 'tiger', 'tiger_data') order by nspname")
  t0=$(date +%s); COUNTS="$BASE.counts.tmp"
  pg_dump -d "$DB_URL" -Fc -Z 6 "${SCHEMAS[@]}" --extension=pgcrypto --extension=pg_trgm --extension=uuid-ossp 2>"$BASE.err" \
    | tee >(count_copy_rows > "$COUNTS") \
    | openssl enc -e "${ENC_OPTS[@]}" -salt -pass "$PASS_ARG" -out "$BASE.dump.enc.tmp" \
    || { cat "$BASE.err" >&2; rm -f "$BASE".*; die "pg_dump / encryption failed"; }
  wait "$!" 2>/dev/null || true
  rm -f "$BASE.err"
  [[ -s "$COUNTS" ]] || { rm -f "$BASE".*; die "the dump has no tables — nothing was backed up"; }
  mv "$BASE.dump.enc.tmp" "$BASE.dump.enc"
  { echo "format=drugbox-backup-1"; echo "created_utc=$TS"; echo "source=$DB_HOST:$DB_PORT/$DB_NAME"; echo "project_ref=${DB_REF}"
    echo "environment=${STAMP:-unknown}"; echo "server_version=$(q "select current_setting('server_version')" | awk '{print $1}')"
    echo "pg_dump=$(pg_dump --version | awk '{print $3}')"; echo "schemas=${NAMES[*]}"
    echo "cipher=aes-256-cbc pbkdf2 sha256 iter=$ITER"; echo "bytes=$(stat -c %s "$BASE.dump.enc")"
    echo "sha256=$(sha256 "$BASE.dump.enc")"; echo "hmac_sha256=$(hmac_of "$BASE.dump.enc")"
    echo "# rows per table in the archive"; sort "$COUNTS"; } > "$BASE.manifest"
  rm -f "$COUNTS"
  ok "$(basename "$BASE").dump.enc — $(du -h "$BASE.dump.enc" | cut -f1), $(grep -c '|' "$BASE.manifest") tables, $(awk -F'|' '/\|/{s+=$2} END{print s+0}' "$BASE.manifest") rows, $(( $(date +%s) - t0 )) s"
  mapfile -t ALL < <(find "$BACKUP_DIR" -maxdepth 1 -name "drugbox-$LABEL-*.dump.enc" -printf '%f\n' | sort -r)
  if [[ ${#ALL[@]} -gt $BACKUP_RETENTION ]]; then
    for old in "${ALL[@]:$BACKUP_RETENTION}"; do rm -f "$BACKUP_DIR/$old" "$BACKUP_DIR/${old%.dump.enc}.manifest"; info "retention: removed $old"; done
  fi
  ok "kept ${BACKUP_RETENTION} newest of this database ($(( ${#ALL[@]} < BACKUP_RETENTION ? ${#ALL[@]} : BACKUP_RETENTION )) now). Copy ${BACKUP_DIR#"$REPO"/} to storage you control."
  exit 0
fi

# ── restore drill ─────────────────────────────────────────────────────────────────────────────────────────────────────────
need pg_restore psql
step "Restore drill"
key_setup
if [[ -z "$FILE" ]]; then FILE="$(find "$BACKUP_DIR" -maxdepth 1 -name 'drugbox-*.dump.enc' -printf '%f\n' | sort | tail -1)"; [[ -n "$FILE" ]] || die "no backups in $BACKUP_DIR"; FILE="$BACKUP_DIR/$FILE"; fi
[[ -f "$FILE" ]] || die "no such backup: $FILE"
MAN="${FILE%.dump.enc}.manifest"; [[ -f "$MAN" ]] || die "the manifest $(basename "$MAN") is missing"
info "backup: $(basename "$FILE") ($(mval "$MAN" environment), $(mval "$MAN" source), taken $(mval "$MAN" created_utc))"
[[ "$(mval "$MAN" environment)" == production && $PROD == 0 ]] && die "this is a PRODUCTION backup — restoring it (even into a scratch database) needs --prod"
[[ "$(sha256 "$FILE")" == "$(mval "$MAN" sha256)" ]] || die "sha256 mismatch: the file is damaged"
[[ "$(hmac_of "$FILE")" == "$(mval "$MAN" hmac_sha256)" ]] || die "HMAC mismatch: the file was changed, or this is not the key it was made with"
ok "integrity: sha256 + HMAC match the manifest"

[[ -n "${DRILL_DB_URL:-}" ]] || die "set DRILL_DB_URL to an EMPTY scratch database (e.g. createdb drugbox_drill on a spare server)"
SRC_URL="${SUPABASE_DB_URL:-}"
SUPABASE_DB_URL="$DRILL_DB_URL" SUPABASE_PROJECT_REF='' SUPABASE_DB_PASSWORD='' resolve_db   # never send the source's password to the drill server
if [[ -n "$SRC_URL" ]]; then mapfile -d '' SP < <(db_url_split "$SRC_URL"); [[ "${SP[2]}:${SP[3]}/${SP[5]}" != "$DB_HOST:$DB_PORT/$DB_NAME" ]] || die "DRILL_DB_URL is the backed-up database itself — use a scratch database"; fi
[[ -n "$DB_REF" && -n "${SUPABASE_PROD_REF:-}" && "$DB_REF" == "$SUPABASE_PROD_REF" ]] && die "DRILL_DB_URL is the PRODUCTION project — a drill restores into a scratch database only"
USED="$(q "select count(*) from pg_class c join pg_namespace n on n.oid = c.relnamespace where n.nspname not in ('pg_catalog', 'information_schema', 'pg_toast') and n.nspname not like 'pg_temp%' and n.nspname not like 'pg_toast_temp%'")"
EXTS="$(q "select count(*) from pg_extension where extname <> 'plpgsql'")"
[[ "$USED" == 0 && "$EXTS" == 0 ]] || die "DRILL_DB_URL ($DB_NAME on $DB_HOST) is not empty ($USED relations, $EXTS extensions) — the drill only restores into an EMPTY database"
ok "drill database $DB_NAME on $DB_HOST is empty"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
openssl enc -d "${ENC_OPTS[@]}" -pass "$PASS_ARG" -in "$FILE" -out "$TMP/db.dump" || die "decryption failed (wrong key?)"
pg_restore -l "$TMP/db.dump" >/dev/null || die "the decrypted file is not a pg_dump archive"
ok "decrypted ($(du -h "$TMP/db.dump" | cut -f1)) and readable by pg_restore"

# roles named by the archive's grants must exist (roles are per server): create the missing ones without login
mapfile -t ROLES < <(pg_restore -s -f - "$TMP/db.dump" | { grep -E '^(GRANT|REVOKE|ALTER DEFAULT PRIVILEGES) ' || true; } \
  | sed -nE 's/.* (TO|FROM) ([^;]+);$/\2/p; s/.*FOR ROLE ([a-z_"]+) .*/\1/p' | sed 's/ WITH GRANT OPTION//' | tr ',' '\n' | tr -d ' "' | { grep -vx 'PUBLIC' || true; } | sort -u)
MADE=()
for r in "${ROLES[@]}"; do
  [[ "$r" =~ ^[a-z_][a-z0-9_]*$ ]] || continue
  if [[ "$(q "select count(*) from pg_roles where rolname = '$r'")" == 0 ]]; then q "create role \"$r\" nologin" >/dev/null; MADE+=("$r"); fi
done
if [[ ${#MADE[@]} -eq 0 ]]; then ok "roles: the ${#ROLES[@]} roles the archive grants to exist"
else warn "created ${#MADE[@]} missing role(s) on the drill server (nologin): ${MADE[*]}"; fi

q "create schema if not exists extensions" >/dev/null   # where Supabase keeps pgcrypto (the archive creates the extension, not the schema)
# the empty database already has schema public (with PostgreSQL's default rights): restore everything but its CREATE SCHEMA
pg_restore -l "$TMP/db.dump" | grep -vE '^[0-9]+; [0-9]+ [0-9]+ SCHEMA - public ' > "$TMP/toc.list"
t0=$(date +%s)
pg_restore --no-owner -L "$TMP/toc.list" -d "$DB_URL" "$TMP/db.dump" 2>"$TMP/restore.err" || true
ERRS="$(grep -c '^pg_restore: error:' "$TMP/restore.err" || true)"
if [[ "$ERRS" != 0 ]]; then grep '^pg_restore: error:' "$TMP/restore.err" | head -10 | sed 's/^/      /' >&2; fi
FAILS=0
if [[ "$ERRS" == 0 ]]; then ok "restored in $(( $(date +%s) - t0 )) s, no errors"; else warn "pg_restore reported $ERRS error(s) (above)"; FAILS=$((FAILS + 1)); fi

SWEEP="$("${PSQL[@]}" -At -d "$DB_URL" -f "$REPO/supabase/tests/schema_sweep.sql" 2>&1)" || { echo "$SWEEP" >&2; die "schema_sweep.sql could not run on the restored database"; }
while IFS= read -r line; do [[ -z "$line" ]] && continue
  if [[ "$line" == *": none" ]]; then ok "sweep — $line"; else printf '    \033[31mFAIL\033[0m sweep — %s\n' "$line" >&2; FAILS=$((FAILS + 1)); fi
done <<<"$SWEEP"

N=0 BAD=0 ROWS=0
while IFS='|' read -r t want; do
  [[ "$t" =~ ^[A-Za-z0-9_.\"]+$ ]] || { warn "unexpected table name in the manifest: $t"; BAD=$((BAD + 1)); continue; }
  got="$(q "select count(*) from $t" 2>/dev/null || echo missing)"; N=$((N + 1)); ROWS=$((ROWS + ${got//missing/0}))
  [[ "$got" == "$want" ]] || { printf '    \033[31mFAIL\033[0m rows %s: backup %s, restored %s\n' "$t" "$want" "$got" >&2; BAD=$((BAD + 1)); }
done < <(grep '|' "$MAN")
if [[ $BAD == 0 ]]; then ok "row counts: all $N tables match the manifest ($ROWS rows)"; else FAILS=$((FAILS + 1)); fi
for t in public.profiles auth.users public.posts public.messages public.payment_orders drugbox_deploy.migrations; do
  info "$(printf '%-28s %s rows' "$t" "$(q "select count(*) from $t" 2>/dev/null || echo '-')")"
done
[[ $FAILS == 0 ]] || die "restore drill FAILED ($FAILS problem(s)) — the backup cannot be trusted until this is fixed"
step "Restore drill PASSED — $(basename "$FILE") restores completely into $DB_NAME"
info "drop the scratch database when done:  dropdb … $DB_NAME"
