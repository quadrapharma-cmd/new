#!/bin/bash
# Local test services for payments: mock Paymob/Fawry (54500) and the Edge Functions (54400). Reads settings from $1.
set -a; . "${1:-/tmp/drugbox-fn.env}"; set +a
cd "$(dirname "$0")"
(MOCK_PORT=54500 setsid nohup node mock-providers.mjs > /tmp/mock.log 2>&1 &)
(FN_PORT=54400 setsid nohup ${DENO:-/tmp/denobin/deno} run --allow-net --allow-env --allow-read functions-local.js > /tmp/fn.log 2>&1 &)
