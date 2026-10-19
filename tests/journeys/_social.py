"""Helpers shared by the social journeys (tests/journeys/social_*.py): feed posts, profiles, network, messages.
Everything here acts through the interface; database helpers are for preconditions and acceptance checks in live."""
import re, time
from _j import StepFail

LONG_TEXT = ("Update on our QC lab expansion.\n\nWe added two HPLC lines and a dissolution bath. "
             "Our stability chamber now runs Zone IVb (30C/75%RH).\nسعداء بخدمة شركائنا في مصر 🇪🇬 "
             "Details: https://example.org/qc-lab #EDA2026")
SCRIPT = '<img src=x onerror="window.__xss=1">'

# ---- feed ------------------------------------------------------------------------------------------------------------
def posts(pg):
    """Posts currently on the page: [{dom id, text, author}] in display order."""
    return pg.evaluate("""()=>[...document.querySelectorAll('#content .post')].filter(e=>e.offsetParent!==null).map(e=>({id:e.id,
        author:(e.querySelector('.post-name')||{}).innerText||'',text:(e.querySelector('.post-body')||{}).innerText||''}))""")

def post_el(j, pg, needle):
    """The visible post whose text contains needle (Locator) — fails the step if it is not on the page."""
    loc = pg.locator('#content .post', has_text=needle)
    j.check(loc.count() > 0, 'post "%s" is not on the page' % needle[:40])
    return loc.first

def post_menu(j, pg, post, pattern, what):
    """Open the post's ⋯ menu as a person does (hover/tap) and choose the item matching pattern. The live feed may
    re-render a post while the menu is open: the whole gesture is retried then."""
    names = []
    for attempt in range(3):
        btn = post.locator('button.icon-action, [data-mpid], [aria-label*="menu" i], [aria-label*="More" i]').first
        j.check(btn.count(), 'not built: the post has no ⋯ menu')
        btn.hover(); pg.wait_for_timeout(250)
        items = post.locator('.ctx-item, [role=menuitem]')
        if not (items.count() and items.first.is_visible()): btn.click(); pg.wait_for_timeout(250)
        if not (items.count() and items.first.is_visible()): btn.hover(); pg.wait_for_timeout(250)
        names = [t.strip() for t in items.all_inner_texts()]
        hit = None
        for i in range(items.count()):
            if re.search(pattern, items.nth(i).inner_text(), re.I): hit = items.nth(i); break
        if hit is None: j.notbuilt('no "%s" in the post ⋯ menu (items: %s)' % (what, ', '.join(names) or 'none'))
        before = j.toast_mark(pg)
        try: hit.click(timeout=4000)
        except Exception:
            if attempt == 2: raise
            pg.mouse.move(1, 1); pg.wait_for_timeout(700); continue
        pg.wait_for_timeout(500)
        return j.dead_end(pg, before, what)

def compose(j, pg, body, category=None, submit=True):
    """Open the composer from Home ('What's on your mind') and write a post."""
    j.click(pg, r"What.s on your mind|تفكر|ماذا يدور|شارك|ما الذي", what="What's on your mind")
    pg.wait_for_selector('#postBody', state='visible', timeout=5000)
    pg.fill('#postBody', body)
    if category:
        pg.select_option('#postCat', value=category) if pg.locator('#postCat option[value="%s"]' % category).count() else pg.select_option('#postCat', label=re.compile(category, re.I).pattern)
    if submit:
        pg.locator('.modal-bg button:has-text("Post"), .modal-bg button:has-text("نشر"), .modal-bg [onclick^="submitPost"]').last.click()
        j.settle(pg, 900)

# ---- live preconditions (database) ------------------------------------------------------------------------------------
def connect_db(j, a, b, status='accepted'):
    j.sql("insert into public.connections (requester, addressee, status) values ('%s','%s','%s') on conflict do nothing" % (a, b, status))

def post_db(j, uid, body, category='general', ago_minutes=0):
    return j.sql1("insert into public.posts (user_id, body, category, created_at) values ('%s', $q$%s$q$, '%s', now() - interval '%d seconds') returning id" % (uid, body, category, ago_minutes))

def comment_db(j, uid, post_id, body, parent=None):
    return j.sql1("insert into public.comments (post_id, user_id, body%s) values ('%s','%s',$q$%s$q$%s) returning id" % (
        ', parent_id' if parent else '', post_id, uid, body, ", '%s'" % parent if parent else ''))

def make_admin(j, uid):
    j.sql("update public.profiles set role='admin' where id='%s'" % uid)

def goto_profile(j, pg, who):
    """Open a person's profile: demo → local id; live → database id (the app fetches unseen people first)."""
    if j.live and isinstance(who, dict) and who.get('id'):
        local = pg.evaluate("u=>dxLive.aid(u)", who['id'])
    else:
        local = who['local'] if isinstance(who, dict) else who
    pg.evaluate("id=>gotoProfile(id)", local); j.settle(pg, 1500)
    return local

def top_search(j, pg, q, enter=True):
    """Search from the top bar as a person does: type, press Enter; returns the results text. On a phone the top bar
    has a search button that opens the command palette instead — then the palette's results are used."""
    j.data.pop('_palette', None)
    if pg.locator('#dxCmd.on').count(): pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    s = pg.locator('#searchIn')
    if not (s.count() and s.is_visible()):
        icon = pg.locator('#dxSearchBtn:visible')
        j.check(icon.count(), 'no visible top-bar search at %dpx' % j.width); icon.click(); pg.wait_for_timeout(400)
        box = pg.locator('[role=dialog]:visible input').first
        j.check(box.count(), 'the search button opens no search box'); box.fill(q); pg.wait_for_timeout(1200)
        j.data['_palette'] = True
        return pg.evaluate("(document.querySelector('[role=dialog] [role=listbox]')||document.activeElement.closest('[role=dialog]')||{}).innerText||''")
    s.click(); s.fill(q)
    if enter: s.press('Enter')
    j.settle(pg, 1000)
    t = j.text(pg)
    j.check(re.search(r'Results for|نتائج', t[:300]), 'the top-bar search shows no results for "%s"' % q)
    return t

def open_result(j, pg, needle):
    """Click the search result that names needle (results page, or the palette on a phone)."""
    if j.data.get('_palette'):
        opt = pg.locator('[role=dialog] [role=option]').filter(has_text=needle)
        j.check(opt.count(), 'the search results do not include "%s"' % needle); opt.first.click(); j.settle(pg, 1200); return
    el = j.find(pg, re.escape(needle), scope='#content', kinds='[onclick],a,button,[role=option],li,[data-gp],[class*=result],[class*=card]')
    j.check(el, 'the search results do not include "%s"' % needle)
    el.click(); j.settle(pg, 1200)

# ---- e-mail (live: the local stack keeps what Supabase would send; GET /__mail?to=) ------------------------------------
def mails(j, to):
    import json as _json, urllib.request, urllib.parse
    import _dx
    base = _dx.APP_URL.rstrip('/')
    try:
        with urllib.request.urlopen(base + '/__mail?to=' + urllib.parse.quote(to.lower()), timeout=5) as r: return _json.loads(r.read().decode())
    except Exception as e: raise StepFail('the local mailbox cannot be read (%s)' % e)

def wait_mail(j, to, subject, n=1, timeout=10):
    """The n-th mail (1 = first) to `to` whose subject matches; fails the step when it does not arrive."""
    end = time.time() + timeout
    while True:
        got = [m for m in mails(j, to) if re.search(subject, m.get('subject', ''), re.I)]
        if len(got) >= n: return got[n - 1]
        if time.time() > end: raise StepFail('no e-mail "%s" #%d to %s (mailbox: %s)' % (subject, n, to, [m.get('subject') for m in mails(j, to)]))
        time.sleep(0.4)
