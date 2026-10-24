"""The action catalog's framework: how an action is declared, run, checked in the database and reported.

An action is a function f(x) on a Ctx. It sends the same requests the live app sends (web/src/live/adapter.js) as the actor,
then checks the result IN THE DATABASE (x.expect / x.dbwait), not just the HTTP status. Outcomes:
  ok           done and verified
  fail         the app answered an error, or the database does not show what the app said it did  → a finding
  skip         nothing to do for this person now (no pending request to accept, no job to apply to…) — not counted
  not_built    the journey's feature has no live backend yet (docs/FEATURE-STATUS-2026-10.md) — counted apart
  limited      the app's own flood limit answered (expected when a day is compressed) — counted apart
  sim_error    the simulator itself broke (a bug to fix in tools/sim)
path: 'app' = the live interface sends exactly this; 'server' = Drugbox's own server-side work (an import job); 'api' = the database supports it but the live interface does not send it
yet (the journey is not built in the UI) — exercised to keep the backend honest, reported apart."""
import json, random, time, traceback

ACTIONS = {}


class Fail(Exception): pass
class Skip(Exception): pass
class NotBuilt(Exception): pass
class Limited(Exception): pass


class Action:
    def __init__(self, name, fn, area, journeys, weights, path, who, rare):
        self.name, self.fn, self.area, self.journeys, self.weights, self.path, self.who, self.rare = name, fn, area, journeys, weights, path, who, rare

    def weight(self, p):
        """How likely this person picks this action, from their archetype weights (social, trade, hire, seek, learn, group)."""
        if self.who == 'admin': return 1.0 if p.get('kind') == 'admin' else 0.0
        if p.get('kind') == 'admin': return 0.0
        if self.who == 'company' and not p.get('company'): return 0.0
        if self.who == 'owner' and p.get('company_role') != 'owner': return 0.0
        if self.who == 'employee' and (not p.get('company') or p.get('company_role') == 'owner'): return 0.0
        a = p.get('arch', {}); w = sum(a.get(k, 0) * v for k, v in self.weights.items()) if self.weights else 1.0
        return w * (0.08 if self.rare else 1.0)


def action(name, area, journeys, weights=None, path='app', who='any', rare=False):
    def deco(fn):
        ACTIONS[name] = Action(name, fn, area, journeys, weights or {}, path, who, rare); return fn
    return deco


class Ctx:
    """Everything an action needs: the actor (acc, p), the shared world, the database and a random generator."""
    def __init__(self, sim, acc, r):
        self.sim, self.acc, self.p, self.db, self.w, self.r = sim, acc, acc.p, sim.db, sim.world, r
        self.me = acc.uid; self.checks = []; self.target = ''

    # results ---------------------------------------------------------------------------------------------------------
    def ok(self, resp, what, allow=()):
        """The request must succeed; a flood-limit answer is Limited; anything else is a finding."""
        if resp.ok or resp.status in allow: return resp
        msg = (resp.err() or {}).get('message', '')
        if 'Too many' in msg or 'too many' in msg or resp.status == 429 or 'several requests to this company' in msg: raise Limited(msg[:160])
        raise Fail('%s: the app answered %s' % (what, (resp.text or '')[:240]))

    def rows(self, resp, what, min_rows=1):
        self.ok(resp, what); d = resp.data if isinstance(resp.data, list) else ([resp.data] if isinstance(resp.data, dict) else [])
        if len(d) < min_rows: raise Fail('%s: the app answered %s but changed nothing (%d rows)' % (what, resp.status, len(d)))
        return d

    def expect(self, sql, args, want, what):
        """A database check, once. want: a value, or a function of the value returning True."""
        v = self.db.val(sql, args); good = want(v) if callable(want) else (v == want)
        self.checks.append({'check': what, 'sql': _fmt(sql, args), 'got': _short(v), 'ok': bool(good)})
        if not good: raise Fail('database check failed: %s (got %s)' % (what, _short(v)))
        return v

    def dbwait(self, sql, args, want, what, timeout=3.0):
        """A database check that may take a moment (a trigger, a counter): polled until true or the time is up."""
        end = time.time() + timeout
        while True:
            v = self.db.val(sql, args); good = want(v) if callable(want) else (v == want)
            if good or time.time() > end: break
            time.sleep(0.15)
        self.checks.append({'check': what, 'sql': _fmt(sql, args), 'got': _short(v), 'ok': bool(good)})
        if not good: raise Fail('database check failed: %s (got %s)' % (what, _short(v)))
        return v

    def need(self, v, why='nothing to do'):
        if not v: raise Skip(why)
        return v

    # picking ---------------------------------------------------------------------------------------------------------
    def other(self, where=None):
        """Another simulated person (uid) — optionally one matching a predicate on the persona."""
        pool = [u for u, q in self.w.people.items() if u != self.me and q.get('kind') != 'admin' and (where is None or where(q))]
        return self.r.choice(pool) if pool else None

    def pick(self, sql, args=()):
        rows = self.db.q(sql, args); return self.r.choice(rows) if rows else None

    def lang(self): return self.p.get('lang', 'en')


def _fmt(sql, args):
    try: return ' '.join((sql % tuple(repr(a) for a in args)).split()) if args else ' '.join(sql.split())
    except Exception: return sql


def _short(v):
    s = v if isinstance(v, str) else json.dumps(v, default=str, ensure_ascii=False)
    return s if len(s) < 160 else s[:157] + '…'


def run(sim, acc, name, r):
    """Run one action as acc; returns an outcome record (never raises)."""
    a = ACTIONS[name]; x = Ctx(sim, acc, r); acc.calls = []; t0 = time.perf_counter(); status, detail = 'ok', ''
    try:
        if not acc.ensure(): raise Fail('sign-in failed: %s' % (acc.last.repro() if acc.last else ''))
        x.me = acc.uid; acc.calls = []
        a.fn(x)
    except Skip as e: status, detail = 'skip', str(e)
    except NotBuilt as e: status, detail = 'not_built', str(e)
    except Limited as e: status, detail = 'limited', str(e)
    except Fail as e: status, detail = 'fail', str(e)
    except Exception as e: status, detail = 'sim_error', '%s: %s | %s' % (type(e).__name__, e, traceback.format_exc(limit=3)[-600:])
    ms = (time.perf_counter() - t0) * 1000
    rec = {'action': name, 'area': a.area, 'journeys': a.journeys, 'path': a.path, 'status': status, 'detail': detail[:900], 'ms': round(ms, 1),
           'req_ms': [round(c.ms, 1) for c in acc.calls], 'actor': acc.email, 'target': x.target, 't': time.time()}
    if status in ('fail', 'sim_error'):
        rec['repro'] = {'actor': acc.email, 'uid': acc.uid, 'requests': [c.repro() for c in acc.calls][-6:], 'checks': x.checks[-4:]}
    return rec


# ── content ────────────────────────────────────────────────────────────────────────────────────────────────────────────
POSTS_EN = ['Just closed a {aud} audit at our {city} site with zero critical findings. Proud of the QA team! #GMP #{tag}',
            'Looking for a reliable supplier of {api} with DMF and CoA, delivery to {city}. Offers by message please. #sourcing',
            'EDA updated its guidance on {topic}. Three things that change for registration files this quarter — thread below. #EDA2026',
            'We are hiring a {role} in {city}. Two years of experience in {topic} preferred. #hiring #pharmajobs',
            'Free capacity on our {form} line from next month (min batch 50k units). Happy to quote. #CMO #tollmanufacturing',
            'Great discussion today about {topic} with colleagues from {city}. What is your biggest challenge with it?',
            'Reminder: stability samples for Zone IVb need 30°C/75% RH. Saw two files rejected for this last week. #stability',
            'Price update: {api} is up again this month. Anyone seeing better offers from India or China? #market']
POSTS_AR = ['الحمد لله خلصنا تفتيش {aud} في مصنع {city} من غير ملاحظات حرجة. شكراً لفريق الجودة #GMP',
            'محتاجين مورد {api} بشهادة تحليل وملف DMF، التوريد {city}. ابعتولي رسالة بالعرض #توريد',
            'هيئة الدواء حدّثت إرشادات {topic}. أهم ٣ تغييرات في ملفات التسجيل الربع ده #EDA2026',
            'مطلوب {role} في {city}، خبرة سنتين في {topic} ميزة #وظائف',
            'عندنا طاقة فاضية على خط {form} من الشهر الجاي، أقل باتش ٥٠ ألف وحدة. جاهزين نبعت عرض سعر #تصنيع_لدى_الغير',
            'نقاش ممتاز النهارده عن {topic} مع زملاء من {city}. إيه أكبر مشكلة بتقابلكم فيه؟',
            'تذكير: عينات الثبات لـ Zone IVb لازم ٣٠ درجة و٧٥٪ رطوبة. شفت ملفين اترفضوا بسبب كده الأسبوع اللي فات']
COMMENTS_EN = ['Congratulations, well deserved!', 'Very useful, thanks for sharing.', 'Can you share the reference for this?', 'We faced the same issue last year — happy to talk.',
               'Interested. Sent you a message.', 'Which batch size do you work with?', 'Agreed. The new timelines are tight.', 'Is the offer still valid?']
COMMENTS_AR = ['مبروك، تستاهلوا', 'معلومة مفيدة جداً، شكراً', 'ممكن المرجع لو سمحت؟', 'حصل معانا نفس الموضوع السنة اللي فاتت', 'مهتم، بعتلك رسالة', 'العرض لسه ساري؟']
MSGS_EN = ['Hi, saw your post — could you send me your price list?', 'Thanks for connecting! Are you at the exhibition next week?', 'Can we schedule a call tomorrow at 11?',
           'Please find the CoA attached.', 'Sure, I will check with our QA and come back to you.', 'What is your MOQ for this item?', 'Noted, thanks.']
MSGS_AR = ['أهلاً، شفت البوست بتاعك — ممكن قايمة الأسعار؟', 'شكراً على الإضافة! هتحضر المعرض الأسبوع الجاي؟', 'ممكن نعمل مكالمة بكرة الساعة ١١؟',
           'مرفق شهادة التحليل', 'تمام، هراجع مع الجودة وأرد عليك', 'إيه أقل كمية للطلب؟', 'تمام، شكراً']
TOPICS = ['GMP', 'pharmacovigilance', 'stability studies', 'bioequivalence', 'serialization', 'pricing', 'cold chain', 'variations', 'cosmetics notification']
TOPICS_AR = ['الـ GMP', 'اليقظة الدوائية', 'دراسات الثبات', 'التكافؤ الحيوي', 'التتبع الدوائي', 'التسعير', 'سلسلة التبريد']


def post_text(x):
    from .personas import APIS, FORMS
    r = x.r; ar = x.lang() == 'ar'
    t = r.choice(POSTS_AR if ar else POSTS_EN)
    return t.format(aud=r.choice(['EDA', 'WHO', 'SFDA', 'internal']), city=x.p.get('city') or 'Cairo', tag=r.choice(['QA', 'quality', 'pharma']),
                    api=r.choice(APIS), topic=r.choice(TOPICS_AR if ar else TOPICS), role=x.p.get('headline', 'pharmacist'), form=r.choice(FORMS))


def comment_text(x): return x.r.choice(COMMENTS_AR if x.lang() == 'ar' else COMMENTS_EN)
def message_text(x): return x.r.choice(MSGS_AR if x.lang() == 'ar' else MSGS_EN)
