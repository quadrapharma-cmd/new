#!/usr/bin/env bash
# Local runner: (optionally) a fresh local stack, the payment stand-in, fixtures, then one or more simulated days.
#   tools/sim/run_local.sh --fresh --accounts 100 --speed 720           # fresh database, 100 accounts, one compressed day
#   tools/sim/run_local.sh --accounts 1000 --speed 0 --tag n1000 --timings --ui 24
# Every option after --fresh is passed to `sim.py run`. The simulator refuses anything but the local stack (see docs/SIM.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRESH=0; [ "${1:-}" = "--fresh" ] && { FRESH=1; shift; }
python3 -c "import psycopg2" 2>/dev/null || pip install -q psycopg2-binary     # the database checks (falls back to psql without it)
python3 -c "import requests" 2>/dev/null || pip install -q requests
if [ "$FRESH" = 1 ]; then
  bash "$ROOT/tools/local-supabase/setup-session.sh" | tail -1 > /tmp/drugbox-sim-env.sh; . /tmp/drugbox-sim-env.sh
  SKIP_BUILD=${SKIP_BUILD:-0} bash "$ROOT/tools/local-supabase/start.sh"
  rm -rf "$ROOT/tools/sim/state/local-${DB_NAME:-drugbox_live}"           # a fresh database: the old registry is void
fi
pg_isready -q -h "${PGHOST:-/tmp}" -p "${PGPORT:-5433}" || { echo "PostgreSQL is not running: tools/sim/run_local.sh --fresh"; exit 1; }
# after start.sh the stack has a new JWT secret: the payment functions must be restarted with it (else "Invalid API key")
[ "$FRESH" = 0 ] && curl -sf -o /dev/null http://127.0.0.1:${FN_PORT:-54400}/ || DENO=${DENO:-/opt/drugbox-tools/deno-npm/node_modules/.bin/deno} bash "$ROOT/tools/local-supabase/start-payments.sh"
[ -f "${DRUGBOX_FIXTURES:-/tmp/vids}/photo.png" ] || python3 "$ROOT/tests/fixtures/make_fixtures.py"
exec python3 "$ROOT/tools/sim/sim.py" run "$@"
