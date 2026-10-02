#!/usr/bin/env bash
# Local stand-in for Supabase (tests only): PostgreSQL 16 on :5433, PostgREST 12 on :3001, auth + app gateway on :54321.
# Requires: PostgreSQL 16, PostgREST 12.2 binary on PATH (or $POSTGREST), Node 20+, Python 3.
set -euo pipefail
pkill -x postgrest 2>/dev/null || true; [ -f /tmp/drugbox-gateway.pid ] && kill "$(cat /tmp/drugbox-gateway.pid)" 2>/dev/null || true
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; DB=${DB_NAME:-drugbox_live}; PGH=${PGHOST:-/tmp}; PGP=${PGPORT:-5433}
SECRET=${JWT_SECRET:-$(python3 -c "import secrets;print(secrets.token_hex(24))")}
psql -h "$PGH" -p "$PGP" -U postgres -q -c "drop database if exists $DB" -c "create database $DB"
psql -h "$PGH" -p "$PGP" -U postgres -d "$DB" -q -v ON_ERROR_STOP=1 -f "$ROOT/supabase/tests/_local_supabase_stub.sql"
for f in "$ROOT"/supabase/migrations/*.sql; do psql -h "$PGH" -p "$PGP" -U postgres -d "$DB" -q -v ON_ERROR_STOP=1 -f "$f"; done
cat > /tmp/drugbox-pgrst.conf <<CONF
db-uri = "postgres://authenticator:local-only@127.0.0.1:$PGP/$DB"
db-schemas = "public"
db-anon-role = "anon"
jwt-secret = "$SECRET"
server-port = 3001
server-host = "127.0.0.1"
CONF
( ${POSTGREST:-postgrest} /tmp/drugbox-pgrst.conf > /tmp/drugbox-pgrst.log 2>&1 & )
ANON=$(node -e "const c=require('crypto');const b=x=>Buffer.from(JSON.stringify(x)).toString('base64url');const h=b({alg:'HS256',typ:'JWT'}),p=b({role:'anon',iss:'local',iat:1700000000,exp:2000000000});console.log(h+'.'+p+'.'+c.createHmac('sha256','$SECRET').update(h+'.'+p).digest('base64url'))")
( cd "$ROOT/web" && { [ "${SKIP_BUILD:-0}" = 1 ] && [ -f dist/drugbox.html ] || python3 build/build.py >/dev/null; } && DRUGBOX_SUPABASE_URL=http://localhost:54321 DRUGBOX_SUPABASE_ANON_KEY=$ANON python3 build/live.py )
( cd "$ROOT/tools/local-supabase" && npm install --silent --no-audit --no-fund && PORT=54321 REST_URL=http://127.0.0.1:3001 JWT_SECRET=$SECRET \
  DATABASE_URL=postgres://postgres@127.0.0.1:$PGP/$DB APP_DIR="$ROOT/web/dist/live" node gateway.mjs > /tmp/drugbox-gateway.log 2>&1 & echo $! > /tmp/drugbox-gateway.pid )
sleep 3; echo "Drugbox (live, local) → http://localhost:54321/"
