"""The simulator engine: the registry of accounts, sign-up (bootstrap), the day's schedule and the dispatcher.

Schedule: each person has active hours in Cairo time and an intensity (actions per active day). A day's actions for a person
are a Poisson number of events, placed at uniform random times inside the active window (a Poisson process), with a few
outside it (late-night checks), fewer on Friday and Saturday (the Egyptian weekend). Every action that someone may do is
scheduled at least once a day. Wall time = sim time / speed (speed 0: as fast as the concurrency allows).

Crash resilience: every finished action is appended to <state>/days/<date>.jsonl with its event number; a restarted day skips
the events already done. The registry (accounts, passwords, uids) is written after every sign-up batch."""
import datetime, hashlib, json, math, os, random, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from zoneinfo import ZoneInfo

from . import catalog, personas, safety
from .client import Account, Bucket, Client
from . import act_social, act_business, act_community  # noqa: F401  (register the actions)

CAIRO = ZoneInfo('Africa/Cairo')
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(HERE))


class World:
    def __init__(self): self.people = {}   # uid → persona


class Sim:
    def __init__(self, args, target, db, anon, fn_env=None, log=print):
        self.args, self.target, self.db, self.log = args, target, db, log
        self.base = target['url']; self.fn_env = fn_env or {}
        self.bucket = Bucket(args.rps, burst=max(4, args.rps // 4))
        self.client = Client(self.base, anon, self.bucket)
        self.world = World(); self.accs = {}; self.admin = None; self._flow = None; self.stopped = None
        self.state = args.state or os.path.join(HERE, 'state', '%s-%s' % (target['kind'], (target.get('marker') or {}).get('database') or (target.get('marker') or {}).get('ref') or 'x'))
        os.makedirs(os.path.join(self.state, 'days'), exist_ok=True)
        self.payments = safety.check_payments(fn_env, target)
        self.companies = {}

    # ── registry ──────────────────────────────────────────────────────────────────────────────────────────────────────
    @property
    def reg_path(self): return os.path.join(self.state, 'registry.json')

    def load_registry(self):
        if not os.path.exists(self.reg_path): return {}
        with open(self.reg_path) as f: return json.load(f)

    def save_registry(self, people, companies):
        reg = {'seed': self.args.seed, 'target': self.target['url'], 'domain': safety.SIM_DOMAIN, 'updated': datetime.datetime.now(CAIRO).isoformat(),
               'admin': {k: self.admin.p.get(k) for k in ('email', 'password', 'uid', 'name')} if self.admin else None,
               'people': [{k: p.get(k) for k in ('i', 'email', 'password', 'uid', 'name', 'kind', 'company', 'company_role', 'lang')} for p in people],
               'companies': [{k: c.get(k) for k in ('i', 'name', 'slug', 'db_slug', 'id', 'type', 'owner')} for c in companies]}
        tmp = self.reg_path + '.tmp'
        with open(tmp, 'w') as f: json.dump(reg, f, ensure_ascii=False, indent=1)
        os.chmod(tmp, 0o600); os.replace(tmp, self.reg_path)

    def acc_of(self, uid): return self.accs.get(uid) or (self.admin if self.admin and self.admin.uid == uid else None)
    def company_of(self, p): return next((c for c in self.companies.values() if c['slug'] == p.get('company')), None)

    def flow(self):
        if self._flow is None: self._flow = self.db.val('select public.deal_flow()')
        return self._flow

    def stop(self, why):
        self.stopped = why; self.log('STOP: ' + why)

    # ── accounts ──────────────────────────────────────────────────────────────────────────────────────────────────────
    def bootstrap(self, n):
        """Make sure the n personas (and the sim admin) have accounts; sign up the missing ones through /auth/v1/signup."""
        people, companies, refused = personas.build(self.args.seed, n, self.db)
        if refused: self.log('name rule refused %d generated names (regenerated): %s' % (len(refused), refused[:5]))
        reg = self.load_registry(); known = {p['email']: p for p in reg.get('people', [])}
        self.companies = {c['slug']: c for c in companies}
        for c in reg.get('companies', []):
            if c['slug'] in self.companies: self.companies[c['slug']].update({k: c.get(k) for k in ('id', 'db_slug') if c.get(k)})
        for p in people:
            safety.check_email(p['email'])
            k = known.get(p['email'])
            if k and k.get('uid'): p['uid'] = k['uid']; p['name'] = k.get('name') or p['name']
        a = dict(personas.ADMIN); a['password'] = 'Sim-' + hashlib.sha256(('%s:admin' % self.args.seed).encode()).hexdigest()[:20]
        if reg.get('admin', {}) and reg['admin'].get('uid'): a['uid'] = reg['admin']['uid']
        self.admin = Account(self.client, a)
        todo = [p for p in people if not p.get('uid')]
        stats = {'signed_up': 0, 'signed_in': 0, 'failed': []}

        def one(p):
            acc = Account(self.client, p)
            r = acc.signup({'name': p['name'], 'company': p.get('company_name') or '', 'specialty': p['headline']})
            if not acc.token:   # the address already has an account (e.g. a lost registry): sign in
                s = acc.signin()
                if not acc.token: return p, acc, 'sign-up %s; sign-in %s' % (r.repro(), s.repro())
                return p, acc, 'in'
            return p, acc, 'up'
        with ThreadPoolExecutor(self.args.concurrency) as ex:
            for i, (p, acc, how) in enumerate(ex.map(one, todo)):
                if how == 'up': stats['signed_up'] += 1
                elif how == 'in': stats['signed_in'] += 1
                else: stats['failed'].append({'email': p['email'], 'name': p['name'], 'why': how}); continue
                self.accs[acc.uid] = acc
                if (i + 1) % 200 == 0: self.save_registry(people, companies); self.log('  signed up %d / %d' % (i + 1, len(todo)))
        for p in people:
            if p.get('uid') and p['uid'] not in self.accs: self.accs[p['uid']] = Account(self.client, p)
        if not self.admin.uid or not self.admin.ensure():
            r = self.admin.signup({'name': a['name']})
            if not self.admin.token: self.admin.signin()
        if not self.admin.uid: raise SystemExit('the sim admin account could not be created: %s' % (self.admin.last.repro() if self.admin.last else ''))
        # Drugbox staff are made on the server (never from the browser): the sim admin is promoted in the database
        self.db.q("update public.profiles set role='admin', account_type='admin' where id=%s and exists (select 1 from auth.users u where u.id=%s and u.email=%s)", (self.admin.uid, self.admin.uid, safety.check_email(a['email'])))
        self.admin.token = None   # the next action signs in again
        self.world.people = {p['uid']: p for p in people if p.get('uid')}
        self.world.people[self.admin.uid] = self.admin.p
        # every account's name is the rule's normalised form, keyed, and not flagged
        bad = self.db.q("select p.id, p.name from public.profiles p where p.id = any(%s::uuid[]) and (p.name_key is null or p.name_needs_fix or p.name = 'Member')", ([p['uid'] for p in people if p.get('uid')],))
        stats['name_problems'] = [list(b) for b in bad]
        self.save_registry(people, companies); self.people = people
        return stats

    # ── one day ───────────────────────────────────────────────────────────────────────────────────────────────────────
    def plan(self, date, first_day):
        r = random.Random('%s:%s:plan' % (self.args.seed, date)); wd = date.weekday()   # Mon=0 … Fri=4, Sat=5
        day_factor = 0.45 if wd in (4, 5) else 1.0
        events = []
        people = [p for p in self.people if p.get('uid')] + [self.admin.p]
        names = list(catalog.ACTIONS)
        for p in people:
            ws = [catalog.ACTIONS[n].weight(p) for n in names]
            if not sum(ws): continue
            lam = p['intensity'] * day_factor * self.args.scale
            k = _poisson(r, lam)
            h0, h1 = p['hours']
            for _ in range(k):
                if r.random() < 0.05: t = r.uniform(0, 24 * 3600)
                else: t = r.uniform(h0 * 3600, h1 * 3600)
                events.append((t, p['uid'], r.choices(names, ws)[0]))
        # first day: everybody sets up (profile, a few connections, a group); owners create their company, invite their team, hire
        if first_day:
            for p in people:
                h0 = p['hours'][0] * 3600; seq = []
                if p.get('kind') == 'admin': seq = ['admin.directory', 'admin.directory', 'admin.directory', 'training.admin']
                else:
                    seq = ['profile.edit', 'profile.experience', 'net.connect', 'net.connect', 'post.text']
                    if p.get('company_role') == 'owner': seq += ['co.create', 'co.update', 'co.invite', 'co.invite', 'co.invite', 'co.site', 'co.product', 'job.post', 'market.supply', 'co.invite']
                    elif p.get('company'): seq += ['co.join']
                    if p['arch'].get('group', 0) >= 3 and r.random() < 0.3: seq += ['group.create']
                    seq += ['group.join', 'training.enroll']
                for j, n in enumerate(seq): events.append((h0 + 20 * j + r.uniform(0, 10), p['uid'], n))
        # coverage: every action someone may do happens at least once today
        have = {e[2] for e in events}
        for n in names:
            if n in have: continue
            elig = [p for p in people if catalog.ACTIONS[n].weight(p) > 0]
            if elig:
                p = r.choice(elig); events.append((r.uniform(p['hours'][0] * 3600, p['hours'][1] * 3600), p['uid'], n))
        events.sort(key=lambda e: e[0])
        return events

    def run_day(self, date, first_day=False, label=''):
        events = self.plan(date, first_day)
        path = os.path.join(self.state, 'days', '%s%s.jsonl' % (date.isoformat(), label))
        done = set()
        if os.path.exists(path):
            with open(path) as f:
                for l in f:
                    try: done.add(json.loads(l)['ev'])
                    except Exception: pass
        self.log('day %s: %d events (%d already done), %d accounts, speed %s, concurrency %d' % (date, len(events), len(done), len(self.people), self.args.speed, self.args.concurrency))
        lock = threading.Lock(); out = open(path, 'a'); counts = {}
        plocks = {}
        t_start = time.time(); speed = self.args.speed

        def work(ev, t, uid, name):
            if self.stopped: return
            acc = self.acc_of(uid)
            if acc is None: return
            pl = plocks.setdefault(uid, threading.Lock())
            with pl:   # one person does one thing at a time
                rr = random.Random('%s:%s:%d' % (self.args.seed, date, ev))
                rec = catalog.run(self, acc, name, rr)
            rec.update(ev=ev, sim_t=round(t, 1), lag_s=round(time.time() - (t_start + (t - events[0][0]) / speed if speed else time.time()), 2))
            with lock:
                out.write(json.dumps(rec, ensure_ascii=False, default=str) + '\n'); out.flush()
                counts[rec['status']] = counts.get(rec['status'], 0) + 1
        sem = threading.BoundedSemaphore(self.args.concurrency * 2)
        last_log = time.time()
        with ThreadPoolExecutor(self.args.concurrency) as ex:
            t0 = events[0][0] if events else 0
            for ev, (t, uid, name) in enumerate(events):
                if self.stopped: break
                if ev in done: continue
                if speed:
                    due = t_start + (t - t0) / speed; d = due - time.time()
                    if d > 0: time.sleep(min(d, 30))
                sem.acquire()
                f = ex.submit(work, ev, t, uid, name); f.add_done_callback(lambda _f: sem.release())
                if time.time() - last_log > 15:
                    last_log = time.time(); self.log('  %s %d/%d %s' % (_clock(t), ev + 1, len(events), json.dumps(counts)))
        out.close()
        self.log('day %s finished in %.0f s: %s' % (date, time.time() - t_start, json.dumps(counts)))
        return path, len(events), time.time() - t_start


def _poisson(r, lam):
    if lam <= 0: return 0
    if lam > 30: return max(0, int(round(r.gauss(lam, math.sqrt(lam)))))
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= r.random()
        if p <= L: return k
        k += 1


def _clock(t): return '%02d:%02d' % (int(t // 3600) % 24, int(t % 3600 // 60))
