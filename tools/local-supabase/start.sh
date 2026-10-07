#!/usr/bin/env bash
# Local stand-in for Supabase (tests only): PostgreSQL 16 on :5433, PostgREST 12 on :3001, auth + app gateway on :54321.
# Requires: PostgreSQL 16, PostgREST 12.2 binary on PATH (or $POSTGREST), Node 20+, Python 3 with Pillow + Playwright.
# Everything listens on 127.0.0.1 only and assumes a single-user machine (the database uses `trust` for local connections).
# Settings (environment): DB_NAME (drugbox_live) PGHOST (/tmp) PGPORT (5433) GATEWAY_PORT (54321) REST_PORT (3001)
#   RUN_DIR (/tmp: drugbox-pgrst.conf, drugbox-*.log, drugbox-*.pid) STORE_DIR (/tmp/drugbox-storage) FN_PORT (54400: start-payments.sh)
#   SKIP_BUILD=1 (reuse web/dist/drugbox.html)
#   MIGRATIONS="file …" (default: every supabase/migrations/*.sql in order) JWT_SECRET (default: a new one per run)
set -euo pipefail
umask 077                                                    # the JWT secret and the logs are readable by this user only
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; DB=${DB_NAME:-drugbox_live}; PGH=${PGHOST:-/tmp}; PGP=${PGPORT:-5433}
GW=${GATEWAY_PORT:-54321}; RP=${REST_PORT:-3001}; RUN=${RUN_DIR:-/tmp}; STORE=${STORE_DIR:-/tmp/drugbox-storage}
case "$DB" in postgres|template0|template1|*[!a-z0-9_]*) echo "refusing to drop and recreate database '$DB'"; exit 1;; esac
stop() {                                                     # stop OUR previous process only (pid file + process name), never every postgrest on the host
  local f="$RUN/drugbox-$1.pid" p; [ -f "$f" ] || return 0; p=$(cat "$f")
  if [ -n "$p" ] && [ "$(ps -o comm= -p "$p" 2>/dev/null)" = "$2" ]; then kill "$p" 2>/dev/null || true
    for _ in $(seq 50); do kill -0 "$p" 2>/dev/null || break; sleep 0.1; done; fi
  rm -f "$f"
}
stop gateway node; stop postgrest postgrest
SECRET=${JWT_SECRET:-$(python3 -c "import secrets;print(secrets.token_hex(24))")}
echo "database $DB: drop and recreate"
psql -h "$PGH" -p "$PGP" -U postgres -q -c "drop database if exists $DB" -c "create database $DB"
psql -h "$PGH" -p "$PGP" -U postgres -d "$DB" -q -v ON_ERROR_STOP=1 -f "$ROOT/supabase/tests/_local_supabase_stub.sql"
for f in ${MIGRATIONS:-"$ROOT"/supabase/migrations/*.sql}; do psql -h "$PGH" -p "$PGP" -U postgres -d "$DB" -q -v ON_ERROR_STOP=1 -f "$f"; done
# PostgREST as on Supabase: at most 1000 rows per request (Dashboard → API → Max rows), a small pool
cat > "$RUN/drugbox-pgrst.conf" <<CONF
db-uri = "postgres://authenticator:local-only@127.0.0.1:$PGP/$DB"
db-schemas = "public"
db-anon-role = "anon"
db-max-rows = 1000
db-pool = 10
jwt-secret = "$SECRET"
server-port = $RP
server-host = "127.0.0.1"
CONF
nohup ${POSTGREST:-postgrest} "$RUN/drugbox-pgrst.conf" > "$RUN/drugbox-pgrst.log" 2>&1 < /dev/null & PGRST_PID=$!; echo $PGRST_PID > "$RUN/drugbox-postgrest.pid"
ANON=$(node -e "const c=require('crypto');const b=x=>Buffer.from(JSON.stringify(x)).toString('base64url');const h=b({alg:'HS256',typ:'JWT'}),p=b({role:'anon',iss:'local',iat:1700000000,exp:2000000000});console.log(h+'.'+p+'.'+c.createHmac('sha256','$SECRET').update(h+'.'+p).digest('base64url'))")
# the local stack has no Realtime server: build without it (the same code runs on the timer)
( cd "$ROOT/web" && { [ "${SKIP_BUILD:-0}" = 1 ] && [ -f dist/drugbox.html ] || python3 build/build.py >/dev/null; } \
  && DRUGBOX_SUPABASE_URL=http://localhost:$GW DRUGBOX_SUPABASE_ANON_KEY=$ANON DRUGBOX_REALTIME=0 DRUGBOX_ALLOW_STALE=${SKIP_BUILD:-0} python3 build/live.py )
( cd "$ROOT/tools/local-supabase" && npm install --silent --no-audit --no-fund )
cd "$ROOT/tools/local-supabase"
PORT=$GW REST_URL=http://127.0.0.1:$RP FN_PORT=${FN_PORT:-54400} JWT_SECRET=$SECRET DATABASE_URL=postgres://postgres@127.0.0.1:$PGP/$DB APP_DIR="$ROOT/web/dist/live" STORE_DIR="$STORE" \
  nohup node gateway.mjs > "$RUN/drugbox-gateway.log" 2>&1 < /dev/null & GW_PID=$!; echo $GW_PID > "$RUN/drugbox-gateway.pid"
# ready = both processes started here are alive (a port still held by an older stack makes them exit) and PostgREST accepts
# a token signed with THIS run's secret through the gateway
for _ in $(seq 100); do
  kill -0 $PGRST_PID 2>/dev/null && kill -0 $GW_PID 2>/dev/null || break
  if curl -sf -o /dev/null "http://127.0.0.1:$GW/rest/v1/" -H "apikey: $ANON" -H "Authorization: Bearer $ANON"; then echo "Drugbox (live, local) → http://localhost:$GW/"; exit 0; fi; sleep 0.2
done
echo "the stack did not start — see $RUN/drugbox-gateway.log and $RUN/drugbox-pgrst.log"; tail -5 "$RUN/drugbox-gateway.log" "$RUN/drugbox-pgrst.log"; exit 1
