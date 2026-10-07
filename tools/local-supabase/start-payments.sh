#!/usr/bin/env bash
# Local test services for payments: mock Paymob/Fawry (54500) and the Edge Functions (54400), loopback only.
# Usage: start-payments.sh [env file]   (default: payments.env.example next to this script — local test values, no real keys)
# Run tools/local-supabase/start.sh first: the Supabase keys are signed with that stack's secret ($RUN_DIR/drugbox-pgrst.conf).
# Writes the effective settings to $RUN_DIR/drugbox-fn.env (mode 600), which tests/e2e/e4*.py read (DRUGBOX_FN_ENV).
set -euo pipefail
umask 077
HERE="$(cd "$(dirname "$0")" && pwd)"; RUN=${RUN_DIR:-/tmp}; GW=${GATEWAY_PORT:-54321}; MP=${MOCK_PORT:-54500}; FP=${FN_PORT:-54400}
ENV_FILE=${1:-$HERE/payments.env.example}
[ -f "$ENV_FILE" ] || { echo "env file $ENV_FILE not found"; exit 1; }
DENO=${DENO:-$(command -v deno || true)}; [ -n "$DENO" ] && [ -x "$DENO" ] || { echo "deno not found: put it on PATH or set DENO=/path/to/deno"; exit 1; }
CONF="$RUN/drugbox-pgrst.conf"; [ -f "$CONF" ] || { echo "$CONF not found — run tools/local-supabase/start.sh first"; exit 1; }
set -a; . "$ENV_FILE"; set +a
SECRET=$(sed -n 's/^jwt-secret = "\(.*\)"$/\1/p' "$CONF")
key() { node -e "const c=require('crypto');const b=x=>Buffer.from(JSON.stringify(x)).toString('base64url');const h=b({alg:'HS256',typ:'JWT'}),p=b({role:'$1',iss:'local',iat:1700000000,exp:2000000000});console.log(h+'.'+p+'.'+c.createHmac('sha256',process.argv[1]).update(h+'.'+p).digest('base64url'))" "$SECRET"; }
export SUPABASE_URL=${SUPABASE_URL:-http://127.0.0.1:$GW} FUNCTIONS_URL=${FUNCTIONS_URL:-http://localhost:$GW/functions/v1} APP_URL=${APP_URL:-http://localhost:$GW/}
export PAYMOB_BASE=${PAYMOB_BASE:-http://127.0.0.1:$MP} FAWRY_BASE=${FAWRY_BASE:-http://127.0.0.1:$MP}
export SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY:-$(key anon)} SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY:-$(key service_role)}
for v in PAYMOB_SECRET_KEY PAYMOB_HMAC_SECRET PAYMOB_CARD_INTEGRATION_ID PAYMOB_WALLET_INTEGRATION_ID FAWRY_MERCHANT_CODE FAWRY_SECURE_KEY; do
  [ -n "${!v:-}" ] || { echo "$v is missing in $ENV_FILE"; exit 1; }; done
python3 - "$RUN/drugbox-fn.env" <<'PY'
import os, re, sys   # KEY="value" lines a shell can source again; the tests read them too
keep = re.compile(r'(SUPABASE_|FUNCTIONS_URL|APP_URL|ALLOWED_ORIGINS|PAYMOB_|FAWRY_|INSTAPAY_)')
with open(sys.argv[1], 'w') as f:
    for k, v in sorted(os.environ.items()):
        if keep.match(k): f.write('%s="%s"\n' % (k, re.sub(r'(["\\$`])', r'\\\1', v)))
PY
stop() { local f="$RUN/drugbox-$1.pid" p; [ -f "$f" ] || return 0; p=$(cat "$f")
  if [ -n "$p" ] && [ "$(ps -o comm= -p "$p" 2>/dev/null)" = "$2" ]; then kill "$p" 2>/dev/null || true; for _ in $(seq 50); do kill -0 "$p" 2>/dev/null || break; sleep 0.1; done; fi; rm -f "$f"; }
stop mock node; stop functions deno
cd "$HERE"
MOCK_PORT=$MP setsid nohup node mock-providers.mjs > "$RUN/drugbox-mock.log" 2>&1 < /dev/null & echo $! > "$RUN/drugbox-mock.pid"
FN_PORT=$FP setsid nohup "$DENO" run --allow-net --allow-env --allow-read functions-local.js > "$RUN/drugbox-fn.log" 2>&1 < /dev/null & echo $! > "$RUN/drugbox-functions.pid"
for _ in $(seq 100); do
  if curl -s -o /dev/null "http://127.0.0.1:$MP/log" && curl -s -o /dev/null "http://127.0.0.1:$FP/"; then echo "payments: functions :$FP, Paymob/Fawry stand-in :$MP (settings in $RUN/drugbox-fn.env)"; exit 0; fi; sleep 0.2
done
echo "payment services did not start — see $RUN/drugbox-mock.log and $RUN/drugbox-fn.log"; tail -5 "$RUN/drugbox-mock.log" "$RUN/drugbox-fn.log"; exit 1
