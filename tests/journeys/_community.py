"""Helpers shared by the community journeys (tests/journeys/community_*.py): groups and their interior, jobs and the trust
layer, training, Drugbox admin decisions. Everything a journey proves is done through the interface; the SQL helpers here only
set up preconditions another journey owns (people already in a group, posts colleagues wrote, a job another company posted)
and read the acceptance rows in live."""
import re, os, time, json
from _j import StepFail
import _dx
from _biz import (L, ar, ui_ok as _ui_ok, dlg_open, dlg_text, dlg_click, dlg_inputs, dlg_buttons, fill_by_label, close_dialogs, reopen as _reopen,
                  admin_review, admin_decide, seed_company, seed_member, make_admin, fn_env, paymob_callback, fawry_callback, money, TOP_DLG)

FIX = _dx.FIXTURES

# A person who has taken the first-visit tour once: the app clears its storage when an account signs in, and the tour then
# opens 1.5 s after the app shows — on top of whatever the journey is doing. Keep the "tour done" mark set in every page.
import _j as _jm
if not getattr(_jm.J, '_community_tour', False):
    _orig_ctx = _jm.J.new_ctx
    def _new_ctx(self, *a, **k):
        ctx = _orig_ctx(self, *a, **k)
        ctx.add_init_script("setInterval(function(){try{if(!localStorage.getItem('dx_tour_done'))localStorage.setItem('dx_tour_done','1')}catch(e){}},200)")
        return ctx
    _jm.J.new_ctx = _new_ctx; _jm.J._community_tour = True
PDF, PNG = os.path.join(FIX, 'spec.pdf'), os.path.join(FIX, 'photo.png')

def num(s):
    m = re.findall(r'[\d,٠-٩]+', s or '')
    return int(m[0].replace(',', '').translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))) if m and re.search(r'\d|[٠-٩]', m[0]) else None

def nums(s):
    return [int(x.replace(',', '').translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))) for x in re.findall(r'[\d٠-٩][\d,٠-٩]*', s or '')]

def R(*en, extra=''):
    """A regex for a label in English or Arabic (web/src/i18n.js), not anchored."""
    return L(*en, exact=False, extra=extra)

DUMP = "JSON.stringify(Object.keys(localStorage).sort().map(k=>[k,localStorage.getItem(k)]))"
def flush(j, pg, timeout=12):
    """Demo: wait until what the page wrote to localStorage is committed — a second page of the same browser (same
    file: origin) reads the same values. Chromium commits a file:// page's storage asynchronously; a reload before that
    loses the last writes, which would look like a missing feature."""
    if not j.demo: return
    blank = os.path.join(j.cfg['out'], '_blank.html')
    if not os.path.exists(blank):
        os.makedirs(j.cfg['out'], exist_ok=True); open(blank, 'w').write('<!doctype html><title>x</title>')
    want = pg.evaluate(DUMP); p2 = pg.context.new_page(); end = time.time() + timeout
    try:
        while time.time() < end:
            p2.goto('file://' + blank)
            if p2.evaluate(DUMP) == want: break
            time.sleep(0.5)
    finally: p2.close()

def reopen(j, pg):
    """Reload the app as a person does (demo: after its storage is committed, then signed in again)."""
    flush(j, pg)
    keep = pg.evaluate("Object.keys(localStorage).filter(k=>/^dbx?_/.test(k)).map(k=>[k,localStorage.getItem(k)])") if j.demo else []
    _reopen(j, pg)
    if j.demo:
        # Chromium may lose a file:// page's last storage writes across a fast reload (they were committed in the page but not
        # yet in the browser): put back exactly what the app had written before the reload, and load once more. The keys put
        # back are recorded in the result (data.storage_restored).
        lost = pg.evaluate("kv=>kv.filter(([k,v])=>localStorage.getItem(k)!==v).map(([k])=>k)", keep)
        if lost:
            j.note('storage_restored', lost)
            pg.evaluate("kv=>kv.forEach(([k,v])=>{try{localStorage.setItem(k,v)}catch(e){}})", [kv for kv in keep if kv[0] in lost])
            flush(j, pg); _reopen(j, pg)
    pg.wait_for_timeout(500); tour_off(j, pg); return pg

def bad_reason(err):
    return '%s %s' % ((err or {}).get('code', ''), (err or {}).get('message', ''))

# ---- live preconditions ----------------------------------------------------------------------------------------------------
def seed_user(j, name, headline=None, company=None, location=None):
    """Live precondition: a member another journey signed up (no browser — only for people who never act on screen)."""
    uid = j.sql1("insert into auth.users (email, raw_user_meta_data) values ('%s', jsonb_build_object('name', $q$%s$q$)) returning id" % (j.email(name), name))
    sets = []
    if headline: sets.append("headline=$q$%s$q$" % headline)
    if company: sets.append("company=$q$%s$q$" % company)
    if location: sets.append("location=$q$%s$q$" % location)
    if sets: j.sql("update public.profiles set %s where id='%s'" % (', '.join(sets), uid))
    return uid

def seed_group(j, name, by, private=False, deal=False, desc='', rules=None, emoji='👥', listed=True):
    gid = j.sql1("insert into public.groups (name, description, emoji, type, topic, rules, created_by, listed) values ($q$%s$q$, $q$%s$q$, '%s', '%s', '%s', %s, %s, %s) returning id" % (
        name, desc, emoji, 'private' if private else 'public', 'DEAL ROOM' if deal else 'DISCUSS', ("$q$%s$q$" % rules) if rules else 'null',
        ("'%s'" % by) if by else 'null', 'true' if listed else 'false'))
    return int(gid)

def add_member(j, gid, uid, role='member'):
    j.sql("insert into public.group_members (group_id, user_id, role) values (%s, '%s', '%s') on conflict (group_id, user_id) do update set role=excluded.role" % (gid, uid, role))

def seed_gpost(j, uid, gid, body, ago_s=0, category='regulatory'):
    return int(j.sql1("insert into public.posts (user_id, body, category, group_id, created_at) values ('%s', $q$%s$q$, '%s', %s, now() - interval '%d seconds') returning id" % (uid, body, category, gid, ago_s)))

def member_count_db(j, gid):
    return j.sql1("select member_count||'/'||(select count(*) from public.group_members where group_id=%s) from public.groups where id=%s" % (gid, gid))

# ---- the Groups page -------------------------------------------------------------------------------------------------------
def tour_off(j, pg):
    """The first-visit tour can open late (after the page settled); a person closes it before going on."""
    for _ in range(2):
        j.skip_tour(pg)
        if not pg.locator('.tour-skip:visible').count(): return
        pg.wait_for_timeout(300)

def groups_page(j, pg):
    tour_off(j, pg); close_dialogs(pg)
    if gd_open(pg): gd_close(pg)
    j.nav(pg, 'groups'); j.settle(pg, 900)
    j.check(pg.locator('#content .gcard, #content .gx-groups-grid').count(), 'the Groups page shows no groups grid')
    return pg

def cards(pg):
    """The visible group cards: [{title, btn, meta, text}] in page order."""
    return pg.evaluate("""()=>[...document.querySelectorAll('#content .gcard')].filter(e=>e.getClientRects().length&&getComputedStyle(e).display!='none').map(c=>({
        title:((c.querySelector('.gcard-title')||{}).innerText||'').trim(), btn:((c.querySelector('.gcard-btn')||{}).innerText||'').trim(),
        meta:((c.querySelector('.gcard-meta')||{}).innerText||'').replace(/\\s+/g,' ').trim(), text:c.innerText.replace(/\\s+/g,' ').trim()}))""")

def card_titles(pg): return [c['title'] for c in cards(pg)]

def sidebar(pg):
    """Your Groups side list: names."""
    return pg.evaluate("[...document.querySelectorAll('#content .mygroup')].filter(e=>e.getClientRects().length).map(e=>((e.querySelector('.mg-name')||e).innerText||'').trim())")

def chip(j, pg, pattern, what):
    loc = pg.locator('#content .cf-tag').filter(has_text=re.compile(pattern, re.I))
    if loc.count(): el = loc.first; el.scroll_into_view_if_needed()
    else: el = j.find(pg, pattern, scope='#content', kinds='.cf-tag,[role=tab],button,[onclick]')
    if not el: j.notbuilt('no "%s" filter on the Groups page' % what)
    mark = j.toast_mark(pg); el.click(); j.settle(pg, 700); j.dead_end(pg, mark, what)
    return el

def chip_text(pg, pattern):
    return pg.evaluate("p=>{const e=[...document.querySelectorAll('#content .cf-tag')].find(e=>new RegExp(p,'i').test(e.innerText));return e?e.innerText.trim():''}", pattern)

def open_card(j, pg, title, via='card'):
    """Open a group from its card (the card itself, not its button) and wait for the interior."""
    loc = pg.locator('#content .gcard').filter(has=pg.locator('.gcard-title', has_text=title))
    if not loc.count():
        j.fail('no card for the group "%s" on the Groups page (cards: %s)' % (title, ', '.join(card_titles(pg))[:200]))
    c = loc.first; c.scroll_into_view_if_needed()
    mark = j.toast_mark(pg)
    c.locator('.gcard-title').click(); j.settle(pg, 900)
    j.dead_end(pg, mark, 'the card of ' + title)
    j.check(gd_open(pg), 'clicking the card of "%s" opens nothing' % title)
    wait_inside(j, pg)
    return c

def open_side(j, pg, title):
    el = pg.locator('#content .mygroup').filter(has_text=title)
    j.check(el.count(), 'the Your Groups side list has no "%s"' % title)
    el.first.click(); j.settle(pg, 900)
    j.check(gd_open(pg), 'clicking "%s" in Your Groups opens nothing' % title)
    wait_inside(j, pg)

def wait_inside(j, pg):
    if j.live: j.wait(pg, "(()=>{const b=document.querySelector('#gpBox');return b&&!/Loading|جار/.test(b.innerText.slice(0,200))})()", 8)

def gd_open(pg):
    return pg.evaluate("(()=>{const g=document.getElementById('groupDetail');return !!g&&g.classList.contains('show')&&g.getClientRects().length>0})()")

def gd_close(pg):
    b = pg.locator('#groupDetail .detail-close')
    if b.count() and b.first.is_visible(): b.first.click(); pg.wait_for_timeout(500)

def gd_title(pg): return pg.evaluate("((document.getElementById('dt-title')||{}).innerText||'').trim()")

def gd_header(pg):
    """The group header: cover (name, type) + action bar (counts, privacy, membership buttons)."""
    return pg.evaluate("[...document.querySelectorAll('#groupDetail .group-cover, #groupDetail .group-actionbar')].map(e=>e.innerText).join('\\n')")

def gd_buttons(pg):
    return pg.evaluate("[...document.querySelectorAll('#groupDetail .group-actionbar button')].filter(b=>b.getClientRects().length).map(b=>b.innerText.replace(/\\s+/g,' ').trim())")

def gd_members_n(pg):
    return pg.evaluate("(()=>{const b=document.querySelector('#groupDetail .group-meta-stats b');return b?parseInt(b.innerText.replace(/[^0-9]/g,''))||0:null})()")

def gd_tabs(pg):
    return pg.evaluate("[...document.querySelectorAll('#gpBox .gp-tabs .gx-ptab')].filter(e=>e.getClientRects().length).map(e=>e.dataset.gpt)")

def gd_tab(j, pg, key, what=None):
    t = pg.locator('#gpBox .gp-tabs .gx-ptab[data-gpt="%s"]' % key)
    if not (t.count() and t.first.is_visible()): j.notbuilt('the group has no %s tab (tabs: %s)' % (what or key, ', '.join(gd_tabs(pg))))
    t.first.click(); pg.wait_for_timeout(500)
    if j.live: j.wait(pg, "k=>{const p=document.querySelector('#gpBox [data-pane=\"'+k+'\"]');return p&&!/Loading|جار التحميل/.test(p.innerText.slice(0,120))}", 8, key)
    return gd_pane(pg, key)

def gd_pane(pg, key):
    return pg.evaluate("k=>{const p=document.querySelector('#gpBox [data-pane=\"'+k+'\"]');return p&&!p.hidden?p.innerText:''}", key)

def gposts(pg):
    """Posts in the open group's Discussion: [{id, text, pinned}] in display order."""
    return pg.evaluate("""()=>[...document.querySelectorAll('#gpBox [data-pane=disc] .post')].filter(e=>e.getClientRects().length).map(e=>({id:e.id,
        text:((e.querySelector('.post-body')||{}).innerText||''), author:((e.querySelector('.post-name')||{}).innerText||'').trim(), all:e.innerText}))""")

def gpost(j, pg, needle):
    loc = pg.locator('#gpBox .post', has_text=needle)
    j.check(loc.count() > 0, 'the post "%s" is not in the group' % needle[:50])
    return loc.first

def has_composer(pg):
    return pg.evaluate("(()=>{const c=document.querySelector('#gpBox [data-pane=disc] .comp-btn');return !!c&&c.getClientRects().length>0})()")

def gcompose(j, pg, body, image=None, file=None, submit=True):
    c = pg.locator('#gpBox [data-pane=disc] .comp-btn')
    if not (c.count() and c.first.is_visible()): j.notbuilt('no composer in the group')
    c.first.click(); pg.wait_for_selector('#postBody', state='visible', timeout=5000)
    pg.fill('#postBody', body)
    if image: pg.locator('.modal-bg.show input[type=file]').first.set_input_files(image); pg.wait_for_timeout(700)
    if file: pg.locator('.modal-bg.show input[type=file]').nth(1).set_input_files(file); pg.wait_for_timeout(700)
    if submit:
        mark = j.toast_mark(pg)
        pg.locator('.modal-bg.show .btn-p').last.click(); j.settle(pg, 1300)
        return j.toasts_since(pg, mark)

def menu(j, pg, post, pattern, what):
    """The post's ⋯ menu (hover / tap) → the item matching pattern."""
    btn = post.locator('button.icon-action, [data-mpid]').first
    j.check(btn.count(), 'not built: the post has no ⋯ menu')
    btn.hover(); pg.wait_for_timeout(250)
    items = post.locator('.ctx-item, [role=menuitem]')
    if not (items.count() and items.first.is_visible()): btn.click(); pg.wait_for_timeout(300)
    names = [t.strip() for t in items.all_inner_texts()]
    for i in range(items.count()):
        if re.search(pattern, items.nth(i).inner_text(), re.I):
            mark = j.toast_mark(pg); items.nth(i).click(); pg.wait_for_timeout(600); j.dead_end(pg, mark, what); return names
    j.notbuilt('no "%s" in the post menu (items: %s)' % (what, ', '.join(names) or 'none'))

def menu_items(pg, post):
    btn = post.locator('button.icon-action, [data-mpid]').first
    if not btn.count(): return []
    btn.hover(); pg.wait_for_timeout(300)
    items = post.locator('.ctx-item, [role=menuitem]')
    if not (items.count() and items.first.is_visible()): btn.click(); pg.wait_for_timeout(300)
    names = [t.strip() for t in items.all_inner_texts()]
    pg.mouse.move(2, 2); pg.wait_for_timeout(400)
    return names

def confirm(j, pg, pattern=r'^\W*(Delete|Remove|Leave|Confirm|Yes|OK|Archive|حذف|إزالة|مغادرة|تأكيد|نعم|أرشفة)', what='the confirmation'):
    """Accept the in-app confirmation if one opened (native confirm() is accepted by the harness)."""
    if dlg_open(pg):
        b = j.find(pg, pattern, scope='body', kinds='button')
        if b: b.click(); pg.wait_for_timeout(700); return True
    return False

def like_count(post):
    el = post.locator('.post-stats [onclick*="showReactors"], .post-stats [data-sr], .post-stats [data-gpm=reactors]')
    return (num(el.first.inner_text()) or 0) if el.count() else 0

def comment_count(post):
    el = post.locator('.post-stats [onclick*="toggleComments"], .post-stats [data-tc]')
    return (num(el.first.inner_text()) or 0) if el.count() else 0

def pact(post, k): return post.locator('.post-acts > .pact:nth-child(%d)' % k)

def manage(j, pg, tab=None):
    """Manage group (admin) → the panel tab: members | reports | settings. Returns the tab's text."""
    b = pg.locator('#groupDetail .btn-manage')
    if not (b.count() and b.first.is_visible()): j.notbuilt('no Manage Group for the group admin')
    if not pg.locator('#managePanel').is_visible(): b.first.click(); pg.wait_for_timeout(600)
    j.check(pg.locator('#managePanel').is_visible(), 'Manage Group opens nothing')
    if tab:
        idx = {'members': 0, 'reports': 1, 'settings': 2}[tab]
        t = pg.locator('#managePanel .panel-tabs .gx-ptab').nth(idx)
        j.check(t.count(), 'Manage has no %s tab' % tab); t.click(); pg.wait_for_timeout(600)
        if j.live: j.wait(pg, "t=>{const p=document.getElementById('tab-'+t);return p&&!/Loading|جار/.test(p.innerText.slice(0,100))}", 6, tab)
        return pg.evaluate("t=>(document.getElementById('tab-'+t)||{}).innerText||''", tab)
    return pg.evaluate("(document.getElementById('managePanel')||{}).innerText||''")

# ---- notifications ------------------------------------------------------------------------------------------------------------
def notifs(j, pg):
    tour_off(j, pg); close_dialogs(pg)
    if gd_open(pg): gd_close(pg)
    j.nav(pg, 'notifs'); j.settle(pg, 1200); tour_off(j, pg)
    return j.text(pg)

def open_notif(j, pg, pattern, what):
    """Notifications page → click the notification whose text matches pattern; returns the page it led to."""
    notifs(j, pg)
    row = pg.locator('#content .notif-item').filter(has_text=re.compile(pattern, re.I))   # the rows themselves, never the filter tabs ("Comments")
    if not row.count(): row = pg.locator('#content .notif-list > *').filter(has_text=re.compile(pattern, re.I))
    j.check(row.count(), 'no notification "%s" (the list: %s)' % (what, j.text(pg)[:200].replace('\n', ' | ')))
    mark = j.toast_mark(pg); row.first.click(); j.settle(pg, 1500); j.dead_end(pg, mark, 'the notification ' + what)
    return pg.evaluate("document.body.getAttribute('data-page')")

def notif_rows(j, uid, type_=None, extra=''):
    return int(j.sql1("select count(*) from public.notifications where user_id='%s'%s%s" % (uid, (" and type='%s'" % type_) if type_ else '', extra)) or 0)

# ---- dialogs of the jobs / training pages (.modal-overlay) as well as the shared ones ---------------------------------------
ANY_DLG = "[...document.querySelectorAll('.modal-overlay.show,.dbk-ov,.modal-bg.show,[role=dialog][aria-modal=true],#boostModalOverlay')].filter(e=>{const r=e.getBoundingClientRect();return r.width>2&&r.height>2&&getComputedStyle(e).visibility!='hidden'&&getComputedStyle(e).display!='none'}).pop()"
def mopen(pg): return pg.evaluate("!!(%s)" % ANY_DLG)
def mtext(pg): return pg.evaluate("(()=>{const d=%s;return d?d.innerText:''})()" % ANY_DLG)
def mclick(j, pg, pattern, what=None, settle=700):
    j.check(mopen(pg), 'no dialog is open to choose "%s" in' % (what or pattern))
    h = pg.evaluate_handle("p=>{const d=%s;if(!d)return null;const re=new RegExp(p,'i');return [...d.querySelectorAll('button,[role=button],a,[onclick]')].filter(e=>e.getClientRects().length&&re.test((e.innerText||e.getAttribute('aria-label')||'').trim())).pop()||null}" % ANY_DLG, pattern)
    el = h.as_element()
    if not el: j.notbuilt('no "%s" in the dialog (buttons: %s)' % (what or pattern, ', '.join(mbuttons(pg))[:200]))
    mark = j.toast_mark(pg); el.click(); pg.wait_for_timeout(settle); j.dead_end(pg, mark, what or pattern)
    return el
def mbuttons(pg):
    return pg.evaluate("(()=>{const d=%s;return d?[...d.querySelectorAll('button')].filter(b=>b.getClientRects().length).map(b=>b.innerText.trim()).filter(Boolean):[]})()" % ANY_DLG)
def mfield(pg, pattern):
    """The visible input/select/textarea of the open dialog whose label (or placeholder / id) matches pattern."""
    return pg.evaluate_handle("""(p)=>{const re=new RegExp(p,'i');const d=%s;if(!d)return null;const vis=e=>e.getClientRects().length>0;
        const els=[...d.querySelectorAll('input,select,textarea')].filter(e=>vis(e)&&!['hidden','checkbox','radio'].includes(e.type));
        const lab=e=>{let l=(e.labels&&e.labels[0]&&e.labels[0].innerText)||'';if(!l){const c=e.closest('label');if(c)l=c.innerText}
          if(!l){let pr=e.previousElementSibling;while(pr&&!pr.innerText)pr=pr.previousElementSibling;if(pr)l=pr.innerText}
          if(!l){const f=e.closest('.field,.form-group,.fg,.field-group');if(f){const x=f.querySelector('label,.field-label');if(x)l=x.innerText}}return (l||'').trim()};
        return els.find(e=>lab(e)&&re.test(lab(e)))||els.find(e=>re.test((e.placeholder||'')+' '+(e.id||'')+' '+(e.name||'')+' '+(e.getAttribute('aria-label')||'')))||null}""" % ANY_DLG, pattern).as_element()
def mfill(j, pg, pattern, value, required=True):
    el = mfield(pg, pattern)
    if not el:
        if required: j.notbuilt('no field "%s" in the dialog' % pattern)
        return None
    if el.evaluate("e=>e.tagName") == 'SELECT':
        opts = el.evaluate("e=>[...e.options].map(o=>o.value+'|'+o.textContent.trim())")
        pick = next((o.split('|')[0] for o in opts if re.search(value, o, re.I)), None)
        if pick is None:
            if required: j.fail('the "%s" list has no option "%s" (options: %s)' % (pattern, value, ', '.join(o.split('|')[1] for o in opts)[:200]))
            return None
        el.select_option(pick)
    else: el.fill(value)
    return el
def mclose(pg):
    for _ in range(3):
        if not mopen(pg): return
        x = pg.evaluate_handle("(()=>{const d=%s;return d?[...d.querySelectorAll('button,[onclick]')].find(b=>b.getClientRects().length&&/^\\s*(×|✕|Close|Cancel|إغلاق|إلغاء)\\s*$/.test(b.innerText)):null})()" % ANY_DLG).as_element()
        if x: x.click()
        else: pg.keyboard.press('Escape')
        pg.wait_for_timeout(300)
    close_dialogs(pg)

def new_toasts(pg, before):
    """Toast texts shown since `before` (a set of texts already shown) — distinct, in order."""
    out = []
    for t in pg.evaluate('window.__jt||[]'):
        if t not in before and t not in out: out.append(t)
    return out
def toast_set(pg): return set(pg.evaluate('window.__jt||[]'))
def toast_cut(pg):
    """A cut in the toast log: a toast shown after it is logged even when its text repeats the previous one."""
    return pg.evaluate("(()=>{const l=window.__jt;if(!l)return 0;l.push('\u00a7');return l.length})()")
def toasts_after(pg, cut):
    return [t for t in pg.evaluate("c=>(window.__jt||[]).slice(c)", cut) if t != '\u00a7']

# ---- jobs --------------------------------------------------------------------------------------------------------------------
def jobs_page(j, pg, mode=None):
    tour_off(j, pg); close_dialogs(pg); mclose(pg)
    j.nav(pg, 'jobs'); j.settle(pg, 1000)
    if mode:
        pat = r"Job Hunting|أبحث عن عمل|باحث عن عمل|البحث عن وظيفة" if mode == 'hunt' else r"I.m Hiring|أوظ|توظيف"
        el = pg.locator('#content .mode-opt').filter(has_text=re.compile(pat, re.I))
        j.check(el.count(), 'no "%s" switch on Jobs' % mode); el.first.click(); j.settle(pg, 900)
    return pg

def jcards(pg):
    return pg.evaluate("""()=>[...document.querySelectorAll('#content .jcard')].filter(e=>e.getClientRects().length&&getComputedStyle(e).display!='none').map(c=>({
        title:((c.querySelector('.jc-title')||{}).innerText||'').replace(/\\s+/g,' ').trim(), company:((c.querySelector('.jc-company')||{}).innerText||'').replace(/\\s+/g,' ').trim(),
        cat:c.dataset.cat||'', level:c.dataset.level||'', text:c.innerText.replace(/\\s+/g,' ').trim()}))""")

def jcard(j, pg, needle):
    loc = pg.locator('#content .jcard:visible').filter(has_text=needle)
    j.check(loc.count(), 'no card for "%s" on Jobs' % needle)
    return loc.first

def jobs_header_n(pg):
    t = pg.evaluate("(()=>{const e=[...document.querySelectorAll('#content .sec-title')].find(e=>e.getClientRects().length&&/Open Positions|Available Candidates|الوظائف|المرشح/.test(e.innerText));return e?e.innerText:''})()")
    return num(re.sub(r'^[^\d٠-٩]*', '', t)) if t else None

def seed_job(j, uid, title, company='', location='Cairo', country='EG', type_='full-time', seniority='mid', category='other', desc='', tags=(), salary='', deadline=None, ago_s=0, active=True):
    return int(j.sql1("insert into public.jobs (user_id, title, company, location, country, type, seniority, category, description, tags, salary, deadline, created_at, active) values ('%s', $q$%s$q$, $q$%s$q$, $q$%s$q$, '%s', '%s', '%s', '%s', $q$%s$q$, '{%s}', $q$%s$q$, %s, now() - interval '%d seconds', %s) returning id" % (
        uid, title, company, location, country, type_, seniority, category, desc, ','.join('"%s"' % x for x in tags), salary, ("'%s'" % deadline) if deadline else 'null', ago_s, 'true' if active else 'false')))

HUNT, HIRE = 'hunt', 'hire'

def employer(j, name='Hana HR', company='Quadra Pharm', verified=True):
    """Live: an employer (signed up through the UI) who owns a company page."""
    e = j.person(name); co = seed_company(j, e['id'], '%s %s' % (company, j.tag[:4]), status='verified' if verified else 'pending')
    j.reload(e['page']); e['co'] = co; return e

def apply_dialog(j, pg, title):
    jobs_page(j, pg, HUNT); c = jcard(j, pg, title)
    b = c.locator('.apply-btn'); j.check(b.count(), 'no Apply on the job'); b.click(); pg.wait_for_timeout(800)
    j.check(mopen(pg), 'Apply opens nothing')
    return mtext(pg)


# ---- the trust layer (live preconditions) ---------------------------------------------------------------------------------------
def employment(j, author, cand, co=None, cname=None):
    """Live precondition: `author` is the owner of a verified company and `cand` lists that company in his work experience
    (the database lets only such an employer write a work reference). Returns the company."""
    if co is None: co = seed_company(j, author, cname or 'Former Employer %s %s' % (j.tag[:4], author[:4]))
    seed_member(j, co['id'], author, 'owner')
    j.sql("update public.profiles set experience = coalesce(experience,'[]'::jsonb) || jsonb_build_array(jsonb_build_object('company', $q$%s$q$, 'company_id', %s, 'title', 'QC Chemist', 'from', '2022-01', 'to', '2024-12')) where id='%s'" % (co['name'], co['id'], cand))
    return co

def evidence(j, author, name='ev.pdf'):
    path = '%s/%s' % (author, name)
    j.sql("insert into storage.objects (bucket_id, name, owner) values ('reference-evidence', '%s', '%s') on conflict do nothing" % (path, author))
    return path

FACTS = 'Worked as QC chemist on HPLC release testing for 3 years; reliable, accurate, trained two juniors.'
WARN = 'Left the QC lab during a validation campaign without any notice; two batches were delayed by a week.'
def seed_ref(j, author, cand, kind='honor', status=None, body=FACTS, category=None, expires=None, reply=None):
    """Live precondition: a work reference another journey wrote (the author must be employment()-linked to cand). The
    database decides the first status (honor → published, warn → pending); `status` / `expires` set a later state."""
    ev = evidence(j, author, 'ev%s.pdf' % j.tag[:4] + str(int(time.time() * 1000) % 100000)) if kind == 'warn' else None
    rid = int(j.sql1("insert into public.work_references (author, candidate, kind, role_title, from_month, to_month, category, body, evidence_path) values ('%s','%s','%s','QC Chemist','2022-01-01','2024-12-01',%s,$q$%s$q$,%s) returning id" % (
        author, cand, kind, ("'%s'" % category) if category else ('null' if kind == 'honor' else "'Left without notice'"), body, ("'%s'" % ev) if ev else 'null')))
    sets = []
    if status: sets.append("status='%s'" % status)
    if expires: sets.append("expires_at=%s" % expires)
    if reply: sets.append("reply=$q$%s$q$, disputed_at=now()" % reply)
    if sets: j.sql("update public.work_references set %s where id=%d" % (', '.join(sets), rid))
    return rid

def decide(j, pg, needle, ok=True, reason='The document is not readable'):
    """Admin → Review: approve / reject a row; a rejection's reason is typed into the app's prompt (the harness answers
    native dialogs itself, so the prompt is answered in the page)."""
    if not ok: pg.evaluate("r=>{window.__dxPrompt=window.prompt;window.prompt=function(){return r}}", reason)
    try: admin_decide(j, pg, needle, ok, reason)
    finally:
        if not ok: pg.evaluate("()=>{if(window.__dxPrompt)window.prompt=window.__dxPrompt}")

# the community screens' own labels: in Arabic none of them may stay English
COMMUNITY_LABELS = ['Open Positions', 'Available Candidates', 'Favourites only', 'Preferred only', 'Top rated', 'Honor list', 'Warning list', 'My lists',
    'Your Groups', 'Suggested for You', 'My Groups', 'All Groups', 'By Country', 'Deal Rooms', 'View all', 'Create Group', 'Create New Group',
    'Discussion', 'Members', 'About', 'Listings', 'Leave Group', 'Notifications', 'Invite', 'Manage Group', 'Join', 'Request',
    'Post a Job', 'Post My Profile', 'Apply Now', 'Contact Candidate', 'Save', 'Enroll Now', 'Enrolled', 'COURSES', 'Show more posts',
    'Review', 'Verification requests', 'Warning references', 'Site certificates', 'Company reports', 'Payments', 'Mark checked']
def ui_ok(j, pg, where=''):
    """Arabic: no interface label of this screen is left in English (the shared list plus the community screens' own);
    phone: the screen fits (no sideways scroll)."""
    if j.ar: j.wait(pg, "(document.documentElement.getAttribute('dir')||getComputedStyle(document.body).direction)=='rtl'", 5)
    _ui_ok(j, pg, where)
    if j.ar:
        left = pg.evaluate("""(labels)=>{const vis=e=>e.getClientRects().length&&getComputedStyle(e).visibility!='hidden';
            const root=(%s)||document.querySelector('#content')||document.body;const out=new Set();
            root.querySelectorAll('button,a,[role=tab],label,h1,h2,h3,.sec-title,.cf-tag,.jx-tool,.mode-opt,.gx-ptab,.sb-title,.hero-title,.sec-all,.gcard-btn,.apply-btn,.save-btn').forEach(e=>{
              if(!vis(e))return;const t=(e.innerText||'').replace(/[^A-Za-z ]+/g,' ').replace(/\\s+/g,' ').trim();
              for(const l of labels){if(t===l||t.startsWith(l+' ')){out.add(l);break}}});return [...out]}""" % ANY_DLG, COMMUNITY_LABELS)
        j.check(not left, 'not translated in Arabic%s: %s' % ((' (' + where + ')') if where else '', ', '.join('"%s"' % x for x in left[:6])))

def tick(pg, sel, on=True):
    """Tick / untick a checkbox as a click would (also when the approved style hides the native box)."""
    pg.evaluate("([s,on])=>{const e=[...document.querySelectorAll(s)].filter(x=>x.closest('.dbk-ov,.modal-overlay')).pop()||document.querySelector(s);if(e&&e.checked!==on){e.click();if(e.checked!==on){e.checked=on;e.dispatchEvent(new Event('change',{bubbles:true}))}}}", [sel, on])

def card_act(j, pg, name, act, what):
    c = jcard(j, pg, name); b = c.locator('.jx-ic[data-a=%s]' % act)
    j.check(b.count(), 'no "%s" on the card of %s' % (what, name))
    before = toast_set(pg); b.first.click(); pg.wait_for_timeout(800)
    return new_toasts(pg, before)

