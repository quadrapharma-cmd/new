#!/usr/bin/env bash
# One-time (and after-restart) setup of the local test machine for a cloud session: Python deps, PostgREST, Deno,
# the gateway's node modules, and a PostgreSQL 16 cluster on /tmp:5433 (trust auth, local only).
# Safe to re-run: each step is skipped when already done. After a container restart only the database needs starting,
# which this script also does. Prints the exports the other scripts need (POSTGREST, DENO).
# Settings (environment): TOOLS_DIR (/opt/drugbox-tools) PGDATA_DIR (/tmp/pgdata) PGPORT (5433)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TOOLS=${TOOLS_DIR:-/opt/drugbox-tools}; PGD=${PGDATA_DIR:-/tmp/pgdata}; PGP=${PGPORT:-5433}
PG=/usr/lib/postgresql/16/bin
mkdir -p "$TOOLS/bin"

python3 -c "import PIL" 2>/dev/null || pip install -q pillow
python3 -c "import playwright, importlib.metadata as m; assert m.version('playwright')=='1.56.0'" 2>/dev/null \
  || pip install -q playwright==1.56.0                # matches the pre-installed chromium-1194 (never 'playwright install')

if [ ! -x "$TOOLS/bin/postgrest" ]; then
  curl -sSL -m 120 -o "$TOOLS/pgrest.tar.xz" \
    https://github.com/PostgREST/postgrest/releases/download/v12.2.3/postgrest-v12.2.3-linux-static-x64.tar.xz
  tar -xJf "$TOOLS/pgrest.tar.xz" -C "$TOOLS/bin" && rm -f "$TOOLS/pgrest.tar.xz"
fi
[ -x "$TOOLS/deno-npm/node_modules/.bin/deno" ] || npm install --silent --no-audit --no-fund --prefix "$TOOLS/deno-npm" deno
[ -d "$ROOT/tools/local-supabase/node_modules" ] || ( cd "$ROOT/tools/local-supabase" && npm install --silent --no-audit --no-fund )

[ -x "$PG/initdb" ] || { echo "PostgreSQL 16 is not installed at $PG"; exit 1; }
if [ ! -f "$PGD/PG_VERSION" ]; then
  mkdir -p "$PGD" && chown postgres "$PGD"
  su postgres -s /bin/bash -c "$PG/initdb -D '$PGD' -A trust -U postgres" < /dev/null > /dev/null
fi
if ! pg_isready -q -h /tmp -p "$PGP"; then
  su postgres -s /bin/bash -c "$PG/pg_ctl -D '$PGD' -o '-p $PGP -k /tmp -c listen_addresses=127.0.0.1' -l '$PGD/pg.log' start" \
    < /dev/null > /dev/null
  for _ in $(seq 50); do pg_isready -q -h /tmp -p "$PGP" && break; sleep 0.2; done
fi
pg_isready -h /tmp -p "$PGP"
echo "export POSTGREST=$TOOLS/bin/postgrest DENO=$TOOLS/deno-npm/node_modules/.bin/deno PATH=$TOOLS/bin:\$PATH"
