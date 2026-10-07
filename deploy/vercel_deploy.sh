#!/usr/bin/env bash
# Drugbox — build the web app and deploy it to Vercel (a PREVIEW by default; production only with --prod).
#
#   deploy/vercel_deploy.sh [--prod] [--dry-run] [--env-file F] [--out DIR]
#
# Settings (environment, or deploy/.env.web — deploy/.env.web.prod with --prod; the environment wins). See deploy/env.web.example.
#   DRUGBOX_SUPABASE_URL, DRUGBOX_SUPABASE_ANON_KEY   the project's URL and anon (public) key — Settings → API
#   DRUGBOX_SENTRY_LOADER                             optional: Sentry's loader script URL (the CSP allows Sentry only when set)
#   VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID    Vercel access (the token is passed in the environment, never on the command line)
#   SUPABASE_PROD_REF                                 the production project ref: building against it needs --prod, --prod needs it
#
# Steps: 1 demo build (web/build/build.py) into the output folder  2 parity with web/reference/demo-approved.html (must be PARITY OK)
#        3 live build (web/build/live.py) — headers/CSP from deploy/vercel.json, the one template  4 checks on what will be published
#        5 vercel deploy <out>/live (skipped with --dry-run)  6 a request to the new address
# It never writes web/dist (the offline demo and the local test build stay as they are): output goes to deploy/.out/<target>/.
set -euo pipefail
# shellcheck source=deploy/lib.sh
source "$(dirname "$0")/lib.sh"

PROD=0 DRY=0 ENV_FILE='' OUT=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prod) PROD=1 ;;
    --dry-run) DRY=1 ;;
    --env-file) ENV_FILE="${2:?}"; shift ;;
    --out) OUT="${2:?}"; shift ;;
    -h|--help) sed -n '2,/^set -euo/p' "$0" | sed '$d; s/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option $1 (see --help)" ;;
  esac; shift
done
need python3 node
SUFFIX=''; TARGET=preview; [[ $PROD == 1 ]] && SUFFIX='.prod' && TARGET=production
OUT="$(mkdir -p "${OUT:-$DEPLOY_DIR/.out/$TARGET}" && cd "${OUT:-$DEPLOY_DIR/.out/$TARGET}" && pwd)"
LOG="$OUT/build.log"; : > "$LOG"

step "Settings ($TARGET$( [[ $DRY == 1 ]] && echo ', dry run'))"
load_env_file "${ENV_FILE:-$DEPLOY_DIR/.env.web$SUFFIX}" || info "no ${ENV_FILE:-deploy/.env.web$SUFFIX} — using the environment only"
[[ -n "${DRUGBOX_SUPABASE_URL:-}" && -n "${DRUGBOX_SUPABASE_ANON_KEY:-}" ]] || die "set DRUGBOX_SUPABASE_URL and DRUGBOX_SUPABASE_ANON_KEY (deploy/env.web.example)"
[[ -z "${SUPABASE_PROD_REF:-}" || "$SUPABASE_PROD_REF" =~ ^[a-z0-9]{20}$ ]] || die "SUPABASE_PROD_REF must be a 20-letter project ref"
URL_REF=''; [[ "$DRUGBOX_SUPABASE_URL" =~ ^https://([a-z0-9]{20})\.supabase\.co/?$ ]] && URL_REF="${BASH_REMATCH[1]}"
KEY_ROLE="$(jwt_claim "$DRUGBOX_SUPABASE_ANON_KEY" role)"; KEY_REF="$(jwt_claim "$DRUGBOX_SUPABASE_ANON_KEY" ref)"
[[ "$KEY_ROLE" == anon ]] || die "DRUGBOX_SUPABASE_ANON_KEY is not an anon key (role '${KEY_ROLE:-?}') — only the anon public key belongs in the browser"
[[ -z "$URL_REF" || -z "$KEY_REF" || "$URL_REF" == "$KEY_REF" ]] || die "the anon key belongs to project $KEY_REF but DRUGBOX_SUPABASE_URL is project $URL_REF"
if [[ -z "$URL_REF" ]]; then
  [[ $PROD == 0 ]] || die "--prod needs DRUGBOX_SUPABASE_URL=https://<ref>.supabase.co"
  warn "DRUGBOX_SUPABASE_URL is not a <ref>.supabase.co address ($DRUGBOX_SUPABASE_URL) — fine for a rehearsal build only"
fi
info "Supabase: $DRUGBOX_SUPABASE_URL (anon key for ${KEY_REF:-?})   Sentry: $( [[ -n "${DRUGBOX_SENTRY_LOADER:-}" ]] && echo on || echo off)   output: ${OUT#"$REPO"/}"
prod_guard "$URL_REF" "$PROD"
if [[ $DRY == 0 ]]; then
  for v in VERCEL_TOKEN VERCEL_ORG_ID VERCEL_PROJECT_ID; do [[ -n "${!v:-}" ]] || die "set $v (deploy/env.web.example) — or use --dry-run to build only"; done
  export VERCEL_TOKEN VERCEL_ORG_ID VERCEL_PROJECT_ID
fi

step "1. Demo build (web/build/build.py → ${OUT#"$REPO"/}/drugbox.html)"
t0=$(date +%s)
DRUGBOX_OUT="$OUT/drugbox.html" python3 "$REPO/web/build/build.py" >>"$LOG" 2>&1 || { tail -15 "$LOG" >&2; die "demo build failed (log: ${LOG#"$REPO"/})"; }
ok "built in $(( $(date +%s) - t0 )) s — $(du -h "$OUT/drugbox.html" | cut -f1)"

step "2. Parity with the approved demo"
PAR="$(python3 "$REPO/tools/parity_check.py" "$REPO/web/reference/demo-approved.html" "$OUT/drugbox.html" 2>&1)" || { echo "$PAR" >&2; die "the interface differs from web/reference/demo-approved.html — approve the change first (CLAUDE.md), then deploy"; }
ok "$PAR"

step "3. Live build (web/build/live.py → ${OUT#"$REPO"/}/live)"
rm -rf "$OUT/live"
DRUGBOX_DEMO="$OUT/drugbox.html" DRUGBOX_LIVE_OUT="$OUT/live" python3 "$REPO/web/build/live.py" >>"$LOG" 2>&1 || { tail -5 "$LOG" >&2; die "live build failed"; }
ok "$(grep '^live build' "$LOG" | tail -1 | sed "s#$OUT/##")"

step "4. Checks on what will be published"
python3 - "$OUT/live" "$DRUGBOX_SUPABASE_URL" "${DRUGBOX_SENTRY_LOADER:-}" "$REPO/tools/local-supabase/gateway.mjs" <<'PY' || die "the build is not fit to publish (nothing was deployed)"
import sys, os, re, json, base64
out, url, sentry, gw = sys.argv[1], sys.argv[2].rstrip('/'), sys.argv[3], sys.argv[4]
bad = []; files = [os.path.join(d, f) for d, _, fs in os.walk(out) for f in fs]
idx = open(os.path.join(out, 'index.html'), encoding='utf-8').read()
vj = json.load(open(os.path.join(out, 'vercel.json'), encoding='utf-8'))
csp = [h['value'] for r in vj['headers'] for h in r['headers'] if h['key'] == 'Content-Security-Policy']
if not csp: bad.append('vercel.json has no Content-Security-Policy')
elif url not in csp[0]: bad.append('the CSP does not allow ' + url)
if 'YOUR-PROJECT' in json.dumps(vj): bad.append('vercel.json still has the YOUR-PROJECT placeholder')
for f in files:   # no key but the anon key may ship: decode every JWT-looking string
    if not f.endswith(('.js', '.html', '.json')): continue
    for tok in set(re.findall(r'eyJ[A-Za-z0-9_-]{8,}\.(eyJ[A-Za-z0-9_-]+)\.[A-Za-z0-9_-]*', open(f, encoding='utf-8', errors='ignore').read())):
        try: role = json.loads(base64.urlsafe_b64decode(tok + '=' * (-len(tok) % 4))).get('role')
        except Exception: continue
        if role != 'anon': bad.append(f'{os.path.relpath(f, out)} contains a {role!r} key — only the anon key may be published')
if 'service_role' in idx: bad.append('index.html mentions service_role')
loader = 'data-dx="sentry-loader"' in idx
if bool(sentry) != loader: bad.append('Sentry loader present=%s but DRUGBOX_SENTRY_LOADER set=%s' % (loader, bool(sentry)))
if bool(sentry) != ('sentry' in csp[0] if csp else False): bad.append('the CSP and DRUGBOX_SENTRY_LOADER disagree about Sentry')
refs = set(re.findall(r'(?:src|data-src)="((?:js|media)/[\w.-]+)"', idx))
missing = [r for r in refs if not os.path.exists(os.path.join(out, r))]
if missing: bad.append('index.html references missing files: ' + ', '.join(missing))
if bad: print('\n'.join('    FAIL ' + b for b in bad), file=sys.stderr); sys.exit(1)
# the e2e suites run behind the local gateway's copy of this policy: if the two drift apart, the tests no longer cover the published CSP
try:
    g = ''.join(re.findall(r'"([^"]*)"', re.search(r'const CSP = ((?:"[^"]*"\s*\+?\s*(?://[^\n]*)?\s*)+);', open(gw, encoding='utf-8').read()).group(1)))
    def norm(p, drop):
        return {d.split()[0]: sorted(t for t in d.split()[1:] if not drop(t)) for d in (x.strip() for x in p.split(';')) if d and d.split()[0] != 'upgrade-insecure-requests'}
    gt = set(re.split(r'[\s;]+', g))
    pub = norm(csp[0], lambda t: (t.startswith(('https://', 'wss://', 'http://')) and t not in gt) or 'sentry' in t)
    loc = norm(g, lambda t: re.match(r'(https?|wss?)://(localhost|127\.0\.0\.1)', t))
    if pub != loc:
        diff = sorted(k for k in set(pub) | set(loc) if pub.get(k) != loc.get(k))
        print('    WARN the published CSP and tools/local-supabase/gateway.mjs (what the e2e suites run under) differ in: ' + ', '.join(diff), file=sys.stderr)
except Exception as e: print('    WARN could not compare the CSP with tools/local-supabase/gateway.mjs: %s' % e, file=sys.stderr)
size = sum(os.path.getsize(f) for f in files)
print('    OK  %d files, %.1f MB; CSP allows %s%s; no key but the anon key; every referenced file present' % (len(files), size / 1e6, url, ' + Sentry' if sentry else ''))
PY

# shellcheck disable=SC2206  # word-split on purpose: a command plus its arguments
VC=(${VERCEL_CLI:-npx --yes vercel@62.7.0})
DEPLOY_CMD=(deploy --cwd "$OUT/live" --yes); [[ $PROD == 1 ]] && DEPLOY_CMD+=(--prod)
if [[ $DRY == 1 ]]; then
  step "Dry run — stopping before Vercel"
  info "would run: VERCEL_TOKEN=*** VERCEL_ORG_ID=… VERCEL_PROJECT_ID=… ${VC[*]} ${DEPLOY_CMD[*]#"$REPO"/}"
  info "the folder that would be published: ${OUT#"$REPO"/}/live"; exit 0
fi

step "5. Vercel deploy ($TARGET)"
# (run from the output folder: in the repo root the CLI mistakes the word "deploy" for the deploy/ folder)
DEPLOY_URL="$(cd "$OUT" && "${VC[@]}" "${DEPLOY_CMD[@]}" 2>>"$LOG" | tail -1)" || { tail -8 "$LOG" >&2; die "vercel deploy failed (log: ${LOG#"$REPO"/})"; }
[[ "$DEPLOY_URL" =~ ^https:// ]] || { tail -8 "$LOG" >&2; die "vercel deploy did not print a URL"; }
ok "deployed: $DEPLOY_URL"

step "6. First request"
HDR="$(curl -s -D - -o /dev/null --max-time 30 "$DEPLOY_URL/" || true)"; CODE="$(awk 'NR==1{print $2}' <<<"$HDR")"
if [[ "$CODE" == 200 ]] && grep -qi '^content-security-policy:' <<<"$HDR"; then ok "GET / → 200 with the Content-Security-Policy header"
elif [[ "$CODE" == 401 || "$CODE" == 403 ]]; then warn "GET / → $CODE: usually Vercel Deployment Protection on previews — open the link in a browser signed in to Vercel (or relax protection for previews)"
else warn "GET / → ${CODE:-no answer} — open $DEPLOY_URL and check"; fi
step "Done — $DEPLOY_URL"
[[ $PROD == 1 ]] || info "This is a preview. Production: deploy/vercel_deploy.sh --prod (with deploy/.env.web.prod). Roll back: Vercel → Deployments → previous → Promote."
