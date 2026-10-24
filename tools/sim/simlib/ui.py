"""The UI driver: a random sample of the day's actions done through the real interface (Playwright, real clicks), in English
and Arabic at 1440 and 390 px, by simulated accounts signing in through the login form. Every action checks the database,
like the journeys (tests/journeys/_j.py — the same helpers and selectors). At most 4 browsers: one per worker process."""
import json, os, random, re, sys, time, traceback
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ROOT = os.path.dirname(os.path.dirname(HERE))
JDIR = os.path.join(ROOT, 'tests', 'journeys')

UI_ACTIONS = {  # name: (journeys, weight)
    'ui.pages': (['J-SOCIAL-08', 'J-SOCIAL-10'], 2), 'ui.back': (['J-SOCIAL-50'], 0.5), 'ui.post': (['J-SOCIAL-11'], 2), 'ui.react': (['J-SOCIAL-13'], 2),
    'ui.comment': (['J-SOCIAL-14'], 1.5), 'ui.message': (['J-SOCIAL-36', 'J-SOCIAL-38'], 1.5), 'ui.enroll': (['J-COMMUNITY-36'], 1),
    'ui.group_join': (['J-COMMUNITY-09'], 1), 'ui.job_save': (['J-COMMUNITY-20'], 1), 'ui.market': (['J-BUSINESS-34'], 1),
    'ui.companies': (['J-BUSINESS-01', 'J-BUSINESS-04'], 1), 'ui.network': (['J-SOCIAL-29', 'J-SOCIAL-30'], 1),
    'ui.logout': (['J-SOCIAL-03', 'J-SOCIAL-04'], 0.7), 'ui.theme': (['J-SOCIAL-09'], 0.5), 'ui.cmdk': (['J-SOCIAL-46'], 0.5), 'ui.share': (['J-BUSINESS-10'], 0.5)}


def plan(people, n, configs, seed, only=None):
    r = random.Random('%s:ui' % seed); names = [k for k in UI_ACTIONS if not only or k in only]; w = [UI_ACTIONS[k][1] for k in names]
    out = []
    for i in range(n):
        cfg = configs[i % len(configs)]
        lang, width = cfg.split('-')
        pool = [p for p in people if p.get('uid') and (p.get('lang') == lang or r.random() < 0.3)] or people
        p = r.choice(pool)
        out.append({'i': i, 'config': cfg, 'lang': lang, 'width': int(width), 'action': r.choices(names, w)[0],
                    'who': {k: p.get(k) for k in ('email', 'password', 'uid', 'name', 'lang')}})
    return out


def run(sim, db, n, browsers, configs, seed, log=print, only=None):
    people = [p for p in sim.people if p.get('uid')]
    jobs = plan(people, n, configs, seed, only)
    out = os.path.join(sim.state, 'ui'); os.makedirs(out, exist_ok=True)
    groups = {}
    for j in jobs: groups.setdefault(j['config'], []).append(j)
    batches = list(groups.values())
    env = {'APP_URL': sim.base + '/', 'DB_NAME': os.environ.get('DB_NAME', 'drugbox_live')}
    t0 = time.time(); recs = []
    with ProcessPoolExecutor(max_workers=max(1, min(4, browsers, len(batches)))) as ex:   # never more than 4 browsers
        for res in ex.map(_worker, [(b, out, env) for b in batches]): recs.extend(res)
    ok = sum(1 for r in recs if r['status'] == 'ok'); fail = [r for r in recs if r['status'] == 'fail']; skip = sum(1 for r in recs if r['status'] == 'skip')
    js_err = sum(len(r.get('errors') or []) for r in recs)
    log('UI driver: %d actions in %.0f s — ok %d, failed %d, skipped %d, JavaScript errors %d' % (len(recs), time.time() - t0, ok, len(fail), skip, js_err))
    with open(os.path.join(out, 'ui-%s.jsonl' % time.strftime('%Y%m%d-%H%M%S')), 'w') as f:
        for r in recs: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return {'total': len(recs), 'ok': ok, 'fail': len(fail), 'skip': skip, 'js_errors': js_err, 'configs': sorted(groups), 'wall_s': round(time.time() - t0, 1),
            'failures': [{'action': r['action'], 'config': r['config'], 'actor': r['actor'], 'detail': r['detail'], 'shots': r.get('shots')} for r in fail] +
                        [{'action': r['action'], 'config': r['config'], 'actor': r['actor'], 'detail': 'JavaScript error: ' + '; '.join(r['errors'])[:300]} for r in recs if r.get('errors') and r['status'] != 'fail'],
            'by_action': _by(recs), 'records': recs}


def _by(recs):
    d = {}
    for r in recs:
        s = d.setdefault(r['action'], {'ok': 0, 'fail': 0, 'skip': 0, 'not_built': 0, 'ms': []}); s[r['status']] += 1; s['ms'].append(r['ms'])
    for s in d.values(): v = sorted(s.pop('ms')); s['p50_ms'] = v[len(v) // 2] if v else None
    return d


def _worker(arg):
    batch, out, env = arg
    os.environ.update(env); sys.path.insert(0, JDIR); sys.path.insert(0, os.path.join(ROOT, 'tests', 'e2e'))
    import _j
    from playwright.sync_api import sync_playwright
    res = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for job in batch: res.append(_one(_j, browser, job, out))
        finally: browser.close()
    return res


def _one(_j, browser, job, out):
    cfg = {'target': 'live', 'lang': job['lang'], 'width': job['width'], 'out': out}
    j = _j.J(cfg, browser, 'SIM-%s-%d' % (job['action'], job['i'])); t0 = time.time(); status, detail = 'ok', ''
    who = job['who']
    try:
        with j.step('sign in through the login form'):
            pg = j.new_page(j.new_ctx(touch=job['width'] <= 480)); j.signin(pg, who['email'], who['password'])
        with j.step(job['action']):
            ACT[job['action']](j, pg, who)
    except _j._Skip as e: status, detail = 'skip', str(e)
    except _j._Stop:
        if j.steps and 'known gap' in str(j.steps[-1].get('reason', '')): status, detail, j.failed = 'not_built', j.steps[-1]['reason'], None
    except Exception as e: status, detail = 'fail', 'driver: %s: %s' % (type(e).__name__, str(e)[:300])
    if j.failed: status, detail = 'fail', 'step %d (%s): %s' % j.failed
    if any(s.get('skipped') for s in j.steps) and status == 'ok': status, detail = 'skip', next(s['skipped'] for s in j.steps if s.get('skipped'))
    errors = [e for e in j.errors if not e.startswith('native dialog')]
    rec = {'action': job['action'], 'journeys': UI_ACTIONS[job['action']][0], 'config': job['config'], 'actor': who['email'], 'status': status, 'detail': detail[:600],
           'ms': round((time.time() - t0) * 1000), 'errors': errors[:5], 'shots': j.shots[:3]}
    try: j.close()
    except Exception: pass
    return rec


# ── the actions (selectors as in tests/journeys) ─────────────────────────────────────────────────────────────────────
def _home(j, pg): j.nav(pg, 'feed'); j.settle(pg, 900)


def ui_pages(j, pg, who):
    for page in ('feed', 'network', 'messages', 'notifs', 'companies', 'market', 'jobs', 'groups', 'training', 'saved', 'profile'):
        try: j.nav(pg, page)
        except _jfail() as e:
            if page in ('notifs', 'saved') and 'no visible navigation' in str(e): continue   # some entries live in a menu on a phone
            raise
        j.settle(pg, 500)
        j.check(j.in_app(pg), 'the app closed on %s' % page)
    if j.ar: j.check(pg.evaluate("document.documentElement.dir || document.body.dir") == 'rtl', 'Arabic is not right-to-left')


class KnownGap(Exception): pass


def ui_back(j, pg, who):
    j.nav(pg, 'network'); j.settle(pg, 500); j.nav(pg, 'jobs'); j.settle(pg, 500)
    pg.go_back(); j.settle(pg, 700)
    if not j.in_app(pg): raise KnownGap('the browser Back button leaves the app (no URL routing) — known gap J-SOCIAL-50 in docs/FEATURE-STATUS-2026-10.md')


def _jfail():
    import _j; return _j.StepFail


def _posts(pg): return pg.locator('#content .post[id^="post-"]')


def ui_post(j, pg, who):
    _home(j, pg)
    j.click(pg, r"What.s on your mind|تفكر|ماذا يدور|ما الذي يدور", what="What's on your mind")
    j.check(pg.is_visible('#postBody'), 'the composer did not open')
    body = 'UI sim %s — %s' % (j.tag, 'تحديث من المحاكي' if j.ar else 'update from the simulator')
    pg.fill('#postBody', body)
    try: pg.select_option('#postCat', value='general')
    except Exception: pass
    pg.locator('.modal-bg [onclick^="submitPost"]').last.click(); j.settle(pg, 1200)
    j.check(j.wait_db("select count(*) from public.posts where user_id='%s' and body='%s'" % (who['uid'], body.replace("'", "''")), 8) == '1', 'no posts row for the new post')
    j.check(body in j.text(pg), 'the new post is not on Home')


def _first_other_post(j, pg, who):
    _home(j, pg)
    ids = pg.evaluate("[...document.querySelectorAll('#content .post[id^=post-]')].filter(e=>e.getClientRects().length).map(e=>+e.id.slice(5))")
    for pid in ids[:15]:
        if j.sql1("select count(*) from public.posts where id=%d and user_id<>'%s'" % (pid, who['uid'])) == '1': return pid
    j.skip('no post by someone else on Home')


def ui_react(j, pg, who):
    pid = _first_other_post(j, pg, who); post = pg.locator('#post-%d' % pid)
    had = j.sql1("select count(*) from public.reactions where post_id=%d and user_id='%s'" % (pid, who['uid']))
    btn = post.locator('.post-acts > .pact:nth-child(1)').locator('[onclick*="doReact"]:visible').first
    if not btn.count(): btn = post.locator('.post-acts > .pact:nth-child(1)').first
    btn.click(); pg.wait_for_timeout(1200)
    want = '0' if had == '1' else '1'
    j.check(j.wait_db("select count(*) from public.reactions where post_id=%d and user_id='%s'" % (pid, who['uid']), 6, want=want) == want, 'the Like click did not %s the reaction' % ('remove' if had == '1' else 'store'))


def ui_comment(j, pg, who):
    pid = _first_other_post(j, pg, who); post = pg.locator('#post-%d' % pid)
    post.locator('.post-acts > .pact:nth-child(2)').click(); pg.wait_for_timeout(800)
    inp = pg.locator('#ci-%d' % pid); j.check(inp.is_visible(), 'the comment box did not open')
    text = 'UI sim comment %s' % j.tag; inp.fill(text); inp.press('Enter'); pg.wait_for_timeout(1000)
    j.check(j.wait_db("select count(*) from public.comments where post_id=%d and user_id='%s' and body='%s'" % (pid, who['uid'], text), 6) == '1', 'no comments row')


def ui_message(j, pg, who):
    j.nav(pg, 'messages'); j.settle(pg, 1200)
    t = pg.locator('#threadList .mx-thread:visible')
    if not t.count(): j.skip('no conversations yet')
    t.first.click(); j.settle(pg, 900)
    text = 'UI sim message %s' % j.tag
    pg.fill('#composeInput', text); pg.press('#composeInput', 'Enter'); pg.wait_for_timeout(1200)
    j.check(j.wait_db("select count(*) from public.messages where sender_id='%s' and body='%s'" % (who['uid'], text), 6) == '1', 'no messages row for the sent message')
    j.check(text in j.text(pg), 'the sent message is not in the conversation')


def ui_enroll(j, pg, who):
    j.nav(pg, 'training'); j.settle(pg, 1200)
    j.wait(pg, "document.querySelectorAll('#content .tr-card').length>0", 8)
    cards = pg.locator('#content .tr-card:visible')
    for i in range(cards.count()):
        c = cards.nth(i); b = c.locator('button').filter(has_text=re.compile(r'^\s*(Enroll|Enrol|سجّ?ل|التسجيل)'))
        if b.count() and b.first.is_enabled():
            title = (c.locator('.tr-title').inner_text() or '').strip()
            n0 = j.sql1("select count(*) from public.course_enrollments where user_id='%s'" % who['uid'])
            b.first.click(); pg.wait_for_timeout(1200)
            j.check(j.wait_db("select count(*) from public.course_enrollments where user_id='%s'" % who['uid'], 6, want=str(int(n0) + 1)) == str(int(n0) + 1), 'Enroll on "%s" stored nothing' % title)
            return
    j.skip('enrolled in every course')


def ui_group_join(j, pg, who):
    j.nav(pg, 'groups'); j.settle(pg, 1200)
    btn = j.find(pg, r'^\W*(\+ ?Join|Join|Join Group|انضم|انضمام)\W*$', scope='#content', exact=False)
    if not btn: j.skip('no group to join')
    n0 = j.sql1("select count(*) from public.group_members where user_id='%s'" % who['uid'])
    r0 = j.sql1("select count(*) from public.group_join_requests where user_id='%s'" % who['uid'])
    btn.click(); pg.wait_for_timeout(1500)
    ok = j.wait_db("select (select count(*) from public.group_members where user_id='%s') + (select count(*) from public.group_join_requests where user_id='%s')" % (who['uid'], who['uid']), 6, want=str(int(n0) + int(r0) + 1))
    j.check(ok == str(int(n0) + int(r0) + 1), 'Join stored no membership or request')


def ui_job_save(j, pg, who):
    import _community
    _community.jobs_page(j, pg, 'hunt'); j.settle(pg, 900)
    b = pg.locator('#content .jcard:visible .save-btn')
    if not b.count(): j.skip('no job card with Save')
    n0 = j.sql1("select count(*) from public.saved_jobs where user_id='%s'" % who['uid'])
    b.first.click(); pg.wait_for_timeout(1200)
    end = time.time() + 6
    while j.sql1("select count(*) from public.saved_jobs where user_id='%s'" % who['uid']) == n0 and time.time() < end: time.sleep(0.3)
    j.check(j.sql1("select count(*) from public.saved_jobs where user_id='%s'" % who['uid']) != n0, 'Save / Unsave changed nothing in saved_jobs')


def ui_market(j, pg, who):
    j.nav(pg, 'market'); j.settle(pg, 1500)
    n = int(j.sql1("select count(*) from public.products where active and type='supply'") or 0)
    if n: j.check(re.search(r'\w', j.text(pg)) and pg.evaluate("document.querySelectorAll('#content [class*=card]').length") > 0, 'the market shows no cards while %d listings are live' % n)


def ui_companies(j, pg, who):
    j.nav(pg, 'companies'); j.settle(pg, 1500)
    name = j.sql1("select name from public.companies where owner_id is not null and slug like 'sim-%%' order by id limit 1".replace('%%', '%'))
    if not name: j.skip('no companies yet')
    j.check(len(j.text(pg)) > 50, 'the directory is empty')


def ui_network(j, pg, who):
    j.nav(pg, 'network'); j.settle(pg, 1400)
    pend = j.sql1("select count(*) from public.connections where addressee='%s' and status='pending'" % who['uid'])
    btn = j.find(pg, r'^\W*(Accept|قبول|اقبل)\W*$', scope='#content', exact=False) if pend != '0' else None
    if btn:
        btn.click(); pg.wait_for_timeout(1200)
        j.check(j.wait_db("select count(*) from public.connections where addressee='%s' and status='pending'" % who['uid'], 6, want=str(int(pend) - 1)) == str(int(pend) - 1), 'Accept changed nothing')
        return
    btn = j.find(pg, r'^\W*(\+ ?Connect|Connect|تواصل|اتصال|إضافة)\W*$', scope='#content', exact=False)
    if not btn: j.skip('nobody to connect with')
    n0 = j.sql1("select count(*) from public.connections where requester='%s'" % who['uid'])
    btn.click(); pg.wait_for_timeout(1200)
    j.check(j.wait_db("select count(*) from public.connections where requester='%s'" % who['uid'], 6, want=str(int(n0) + 1)) == str(int(n0) + 1), 'Connect stored no request')


def ui_logout(j, pg, who):
    import _j
    j.nav(pg, 'profile')
    j.click(pg, r'^(Sign Out|Sign out|Log out|تسجيل الخروج|خروج)$', what='Sign Out', exact=True)
    j.check(j.wait(pg, _j.LOGIN_VISIBLE, 6), 'Sign Out did not show the login page')
    j.check(pg.input_value('#loginEmail') == '' and pg.input_value('#loginPw') == '', 'the login fields are not empty after Sign Out')
    j.reload(pg); j.check(not j.in_app(pg), 'a reload after Sign Out shows the app again')
    j.signin(pg, who['email'], who['password']); j.check(j.in_app(pg), 'signing in again does not open the app')


def ui_theme(j, pg, who):
    btn = pg.locator('#dxThemeBtn')
    el = btn if (btn.count() and btn.is_visible()) else j.find(pg, r'Theme|Appearance|المظهر')
    if not el: j.notbuilt('no visible Appearance button at %dpx' % j.width)
    el.click(); j.settle(pg, 400)
    j.click(pg, r'^(Dark|داكن|ليلي)$', scope='body', what='Dark', exact=True)
    dark = pg.evaluate("document.documentElement.dataset.theme||document.body.dataset.theme||document.documentElement.className+' '+document.body.className")
    j.check(re.search('dark', dark), 'Dark did not switch the theme (%s)' % dark)
    j.reload(pg)
    dark2 = pg.evaluate("document.documentElement.dataset.theme||document.body.dataset.theme||document.documentElement.className+' '+document.body.className")
    j.check(re.search('dark', dark2), 'the Dark choice is not remembered after a reload')


def ui_cmdk(j, pg, who):
    if j.width <= 480: j.skip('no keyboard on a phone')
    _home(j, pg); pg.keyboard.press('Control+k'); pg.wait_for_timeout(500)
    j.check(pg.evaluate("(()=>{const a=document.activeElement;const d=a&&a.closest('[role=dialog]');return !!(d&&d.getClientRects().length)})()"), 'Ctrl+K opened no palette')
    pg.keyboard.type('mess'); pg.wait_for_timeout(300); pg.keyboard.press('Enter'); j.settle(pg)
    j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'messages', 'Ctrl+K "mess" Enter did not open Messages')


def ui_share(j, pg, who):
    import _biz
    name = j.sql1("select name from public.companies where owner_id is not null and slug like 'sim-%' order by random() limit 1")
    if not name: j.skip('no companies yet')
    _biz.directory(j, pg); _biz.open_card(j, pg, name)
    j.click(pg, _biz.L('Share card'), scope='#content', what='Share card'); pg.wait_for_timeout(800)
    t = _biz.dlg_text(pg) + ' ' + pg.evaluate("(()=>{const d=%s;return d?[...d.querySelectorAll('input,textarea,a')].map(e=>e.value||e.getAttribute('href')||'').join(' '):''})()" % _biz.TOP_DLG)
    j.check(re.search(r'https?://', t), 'the share card gives no link')


ACT = {'ui.logout': ui_logout, 'ui.theme': ui_theme, 'ui.cmdk': ui_cmdk, 'ui.share': ui_share, 'ui.pages': ui_pages, 'ui.back': ui_back, 'ui.post': ui_post, 'ui.react': ui_react, 'ui.comment': ui_comment, 'ui.message': ui_message, 'ui.enroll': ui_enroll,
       'ui.group_join': ui_group_join, 'ui.job_save': ui_job_save, 'ui.market': ui_market, 'ui.companies': ui_companies, 'ui.network': ui_network}
