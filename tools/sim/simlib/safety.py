"""The simulator's hard boundary: it runs only against the local test stack or a staging project that says so — never production.

Fail closed: every check must pass, and any error while checking is a refusal.
  1. the target URL's host is in DRUGBOX_SIM_ALLOWED_HOSTS (default: localhost,127.0.0.1) and on no production list
     (DRUGBOX_PRODUCTION_HOSTS, *.drugbox.app and the domains in PRODUCTION_PATTERNS);
  2. the target answers that it is a non-production stack:
       local   (DRUGBOX_SIM_TARGET unset or 'local'): a loopback host whose gateway answers GET /__drugbox/stack with
               {"stack": "local-supabase", "production": false} (tools/local-supabase/gateway.mjs) for the database we check;
       staging (DRUGBOX_SIM_TARGET=staging): https://<ref>.supabase.co with DRUGBOX_SIM_STAGING_REF=<ref>, the ref different
               from DRUGBOX_PRODUCTION_REF, a marker file the operator put on staging only
               (public bucket 'sim-marker', object staging.json = {"drugbox_env": "staging", "ref": "<ref>"}) and a database URL
               (STAGING_DB_URL) for the same project;
  3. every simulated account's e-mail is at SIM_DOMAIN (not configurable);
  4. payments go only to the local Paymob/Fawry stand-in (tools/local-supabase/start-payments.sh): the function settings must
     point both providers at a loopback address, the stand-in must answer, and every checkout link must stay on the stand-in.
"""
import json, os, re, urllib.parse, urllib.request

SIM_DOMAIN = 'sim.drugbox.test'
LOOPBACK = {'localhost', '127.0.0.1', '::1'}
PRODUCTION_PATTERNS = [r'(^|\.)drugbox\.app$', r'(^|\.)drugbox\.com$', r'(^|\.)drugbox\.eg$', r'(^|\.)drugbox\.net$', r'(^|\.)vercel\.app$']


class Refused(SystemExit):
    def __init__(self, why):
        super().__init__('SIMULATOR REFUSED TO START: ' + why)
        self.why = why


def _host(url):
    p = urllib.parse.urlparse(url)
    if p.scheme not in ('http', 'https') or not p.hostname: raise Refused('target %r is not an http(s) URL' % url)
    return p.hostname.lower(), p


def _get_json(url, timeout=5):
    req = urllib.request.Request(url, headers={'accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status != 200: raise ValueError('HTTP %s' % r.status)
        return json.loads(r.read().decode() or 'null')


def allowed_hosts():
    raw = os.environ.get('DRUGBOX_SIM_ALLOWED_HOSTS', 'localhost,127.0.0.1')
    return {h.strip().lower() for h in raw.split(',') if h.strip()}


def is_production_host(host):
    extra = {h.strip().lower() for h in os.environ.get('DRUGBOX_PRODUCTION_HOSTS', '').split(',') if h.strip()}
    ref = os.environ.get('DRUGBOX_PRODUCTION_REF', '').strip().lower()
    if host in extra or (ref and host.startswith(ref + '.')): return True
    return any(re.search(p, host) for p in PRODUCTION_PATTERNS)


def check_target(url, db_name=None, db_url=None):
    """Return a description of the target, or raise Refused. db_name/db_url: the database the simulator verifies against."""
    host, p = _host(url)
    if is_production_host(host): raise Refused('%s is a production host' % host)
    if host not in allowed_hosts(): raise Refused('host %s is not in DRUGBOX_SIM_ALLOWED_HOSTS (%s)' % (host, ','.join(sorted(allowed_hosts()))))
    kind = os.environ.get('DRUGBOX_SIM_TARGET', 'local').strip().lower()
    base = url.rstrip('/')
    if kind == 'local':
        if host not in LOOPBACK: raise Refused('a local target must be a loopback address, not %s (staging: set DRUGBOX_SIM_TARGET=staging)' % host)
        try: m = _get_json(base + '/__drugbox/stack')
        except Exception as e: raise Refused('%s did not answer /__drugbox/stack (%s) — only the local gateway (tools/local-supabase/start.sh) is accepted' % (base, e))
        if not isinstance(m, dict) or m.get('stack') != 'local-supabase' or m.get('production') is not False:
            raise Refused('%s does not say it is the local test stack: %r' % (base, m))
        if db_name and m.get('database') and m['database'] != db_name:
            raise Refused('the gateway serves database %r but the simulator would check %r' % (m['database'], db_name))
        if db_url and not re.search(r'@(localhost|127\.0\.0\.1|\[::1\])[:/]|host=/tmp|^postgres(ql)?:///', db_url):
            raise Refused('a local target must be checked against a local database')
        return {'kind': 'local', 'url': base, 'host': host, 'marker': m}
    if kind == 'staging':
        ref = os.environ.get('DRUGBOX_SIM_STAGING_REF', '').strip().lower()
        if not ref: raise Refused('DRUGBOX_SIM_TARGET=staging needs DRUGBOX_SIM_STAGING_REF (the staging project ref)')
        if p.scheme != 'https' or host != ref + '.supabase.co': raise Refused('the staging URL must be https://%s.supabase.co' % ref)
        if ref == os.environ.get('DRUGBOX_PRODUCTION_REF', '').strip().lower(): raise Refused('the staging ref is the production ref')
        try: m = _get_json(base + '/storage/v1/object/public/sim-marker/staging.json')
        except Exception as e: raise Refused('no staging marker at %s/storage/v1/object/public/sim-marker/staging.json (%s) — see docs/SIM.md' % (base, e))
        if not isinstance(m, dict) or m.get('drugbox_env') != 'staging' or str(m.get('ref', '')).lower() != ref:
            raise Refused('the staging marker does not match: %r' % (m,))
        if not db_url or ref not in db_url: raise Refused('STAGING_DB_URL must be set and point at the same project (%s)' % ref)
        return {'kind': 'staging', 'url': base, 'host': host, 'marker': m}
    raise Refused('DRUGBOX_SIM_TARGET must be local or staging, not %r' % kind)


def check_email(email):
    if not str(email).lower().endswith('@' + SIM_DOMAIN): raise Refused('account %s is not a simulated account (@%s)' % (email, SIM_DOMAIN))
    return email


def check_payments(fn_env, target):
    """Payments are allowed only through the local stand-in. Returns (ok, why)."""
    if target['kind'] != 'local':
        sb = os.environ.get('DRUGBOX_SIM_PAYMENT_STANDIN_URL', '')
        if not sb: return False, 'payments are off on staging unless DRUGBOX_SIM_PAYMENT_STANDIN_URL names the stand-in the staging functions use'
        h, _ = _host(sb)
        if h not in allowed_hosts() or is_production_host(h): return False, 'the payment stand-in %s is not an allowed host' % h
        return True, sb
    if not fn_env: return False, 'no payment settings (run tools/local-supabase/start-payments.sh)'
    for k in ('PAYMOB_BASE', 'FAWRY_BASE'):
        v = fn_env.get(k, '')
        try: h, _ = _host(v)
        except Refused: return False, '%s is not set to the stand-in' % k
        if h not in LOOPBACK: return False, '%s points at %s, not the local stand-in' % (k, h)
    try: _get_json(fn_env['PAYMOB_BASE'].rstrip('/') + '/log', timeout=3)
    except Exception as e: return False, 'the Paymob/Fawry stand-in does not answer (%s)' % e
    return True, fn_env['PAYMOB_BASE']


def checkout_link_ok(link, standin):
    """A checkout link from payments-create must stay on the stand-in (or be empty for Fawry/InstaPay)."""
    if not link: return True
    try: h, _ = _host(link)
    except Refused: return False
    sh, _ = _host(standin)
    return h == sh or h in LOOPBACK
