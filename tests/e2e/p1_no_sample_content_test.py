"""Phase 1 (S-19, B-06, B-07, G-01…G-04): a brand-new account in the live app sees no sample content from the demo.
The demo's own sample words are read from the demo build itself (people, companies, groups, listings, services, jobs, the
sample conversation list), so the list never goes stale; then a fresh account walks Home, My Network, Messages, Groups (and the
inside of a group it creates), the Marketplace and My Listings, and the visible text is checked:
  - no element whose whole text is a sample name (sample data always matches exactly — names other suites create carry a tag);
  - none of the sample numbers and promises ("1.2K", "150,000+", "8×", "12K+", "top 12%", "27 unread", "412 real members"…);
  - the side menu / phone badges equal the real counts (0 for a new account), "Your shortcuts" and the Groups side list hold
    only real groups, the deal room has no Listings tab (G-01 — not kept in the database yet), and the market counts equal the
    database's. The ticker is the admins' (ticker_items) and is not checked here.
Settings: tests/e2e/_dx.py (APP_URL, DB_NAME…) and DEMO_FILE (default web/dist/drugbox.html)."""
import os, re
from playwright.sync_api import sync_playwright
from _dx import APP_URL as U, T, sql, ST, wait_for, done
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEMO = os.path.abspath(os.environ.get('DEMO_FILE', os.path.join(ROOT, 'web', 'dist', 'drugbox.html')))
SAMPLE_NUMBERS = [r'\b1\.2K\b', r'150,000\+', r'8×', r'12K\+', r'top 12%', r'\b27\b\s*unread', r'412 real members', r'Showing\s*\n?\s*853\b', r'\b3,800\b',
                  r'Online now', r'Unread \(2\)', r'\b76\b\s*open positions', r'\b54\b\s*providers', r'\b312\b\s*listings', r'Export Sales Director']
# the demo's sample words, read from the demo page's own data and page markup (USERS, GROUPS, the groups / market / messages pages)
VOCAB_JS = r"""()=>{const out=new Set(), add=t=>{t=(t||'').replace(/\s+/g,' ').trim(); if(t.length>=4&&!/^[\d\W]+$/.test(t)&&!/:$/.test(t)) out.add(t)};
  (window.USERS||[]).filter(u=>u.id<=1000).forEach(u=>add(u.name)); (window.GROUPS||[]).forEach(g=>add(g.name));
  const own=(e)=>[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.nodeValue).join(' ');
  const P=new DOMParser(), pick=(html,sel,f)=>{ if(!html) return; const d=P.parseFromString(html,'text/html'); d.querySelectorAll(sel).forEach(e=>add(f?f(e):e.textContent)); };
  pick(window.GX_HTML,'.gcard-title,.mg-name'); pick(window.GX_HTML,'.member-name',own);
  pick(window.MKX_HTML,'.lc-title,.sc-title,.sm-title,.act-item b'); pick(window.MKX_HTML,'.dc-title',own);
  pick(window.MKX_HTML,'.sc-provider',e=>own(e).split('·')[0]); pick(window.MKX_HTML,'.jc-company span:first-child');
  pick(window.MX_HTML,'.t-name',own); pick(window.MX_HTML,'.online-avatar-name');
  document.querySelectorAll('#sidebar .sh-row').forEach(e=>add(own(e)));
  ['Dr. Haytham','Shandong Hexa','Quadra Pharm'].forEach(add);
  return [...out]}"""
# every element's own text in the app (not the ticker, which shows the admins' items, nor the course cards: training_courses rows
# whose titles can match a sample group's name, e.g. the course "GCC Market Access")
TEXTS_JS = r"""()=>{const out=[]; const vis=e=>e.getClientRects().length>0&&getComputedStyle(e).visibility!='hidden';
  document.querySelectorAll('#app *').forEach(e=>{ if(e.closest('#tickerInner,.ticker,.tr-card,script,style')||!vis(e)) return;
    const own=[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.nodeValue).join(' ').replace(/\s+/g,' ').trim(); if(own) out.push(own);
    const all=(e.innerText||'').replace(/\s+/g,' ').trim(); if(all&&all.length<120) out.push(all); });
  return out}"""

def main():
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--no-sandbox'])
        # 1. the sample words, from the demo build (offline)
        dc = b.new_context(); dc.route(lambda u: not u.startswith(('file:', 'data:', 'blob:')), lambda r: r.abort())
        dp = dc.new_page(); dp.goto('file://' + DEMO, wait_until='load'); dp.wait_for_timeout(600)
        vocab = set(dp.evaluate(VOCAB_JS)); dc.close()
        T('the demo build gives the sample words to look for (people, groups, listings, services, jobs)', len(vocab) > 40 and 'API Sourcing & Supply' in vocab and 'Vivian Zhou' in vocab, len(vocab))
        # 2. a brand-new account in the live app
        ctx = b.new_context(viewport={'width': 1440, 'height': 900}); ctx.add_init_script("try{localStorage.setItem('dx_tour_done','1')}catch(e){}")
        pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:160])); pg.on('dialog', lambda d: d.accept())
        pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
        pg.evaluate('showSignup()'); pg.fill('#suName', 'Fresh Purge'); pg.fill('#suEmail', f'purge{ST}@x.test'); pg.fill('#suPw', 'Strong-pass-2026'); pg.click('#signupPage button.f-btn')
        wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2500)
        me = pg.evaluate('dxLive.uuidOf(ME.id)')
        found = {}
        def scan(where):
            texts = pg.evaluate(TEXTS_JS); joined = '\n'.join(texts)
            hits = sorted(set(t for t in texts if t in vocab))
            nums = [rx for rx in SAMPLE_NUMBERS if re.search(rx, joined)]
            if hits or nums: found[where] = hits[:8] + nums
        def go(page, wait=2600):
            pg.evaluate("p=>goto(p)", page); pg.wait_for_timeout(wait)
        badges = lambda: pg.evaluate("""()=>[...document.querySelectorAll('#sbNav .nl-badge, #mbnav .mb-badge, .tnb .nbadge')].filter(e=>getComputedStyle(e).display!='none'&&e.textContent.trim()).map(e=>e.closest('[id]').id+':'+e.textContent.trim())""")
        T('a new account has no message, request or alert badges (side menu, phone bar, top bar)', not badges(), badges())
        for page in ('feed', 'network', 'messages', 'notifs', 'profile', 'saved', 'training', 'companies'):
            go(page); scan(page)
        shortcuts = pg.evaluate("[...document.querySelectorAll('#sidebar .sh-row')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim())")
        T('"Your shortcuts" holds no sample group for a new account', not shortcuts, shortcuts)
        go('groups', 3500); scan('groups')
        side = pg.evaluate("[...document.querySelectorAll('#gx .mygroup')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim())")
        T('the Groups side list shows no group for a new account (it holds my real groups only)', not side, side)
        demo_cards = pg.evaluate("[...document.querySelectorAll('#gx .gcard:not([data-gid])')].length")
        T('every group card on the Groups page is a group from the database', demo_cards == 0, demo_cards)
        chip = pg.evaluate("([...document.querySelectorAll('#gx .cf-tag')].find(e=>/My Groups/.test(e.textContent))||{}).textContent||''")
        T('"My Groups (N)" counts my real groups (0)', re.search(r'\(0\)', chip), chip)
        # a deal room I create: shortcuts, side list and My Groups follow; no Listings tab while listings are not in the database
        name = f'Purge Deal Room {ST[-6:]}'
        gid = int(sql(f"insert into public.groups (name, description, type, topic, created_by, listed) values ('{name}', 'test', 'public', 'DEAL ROOM', '{me}', true) returning id").split()[0])
        pg.reload(wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); wait_for(lambda: pg.evaluate("window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2500)
        T('my group is in "Your shortcuts" after sign-in', wait_for(lambda: name in pg.evaluate("[...document.querySelectorAll('#sidebar .sh-row')].map(e=>e.textContent).join('|')"), 8))
        pg.evaluate("[...document.querySelectorAll('#sidebar .sh-row')].find(e=>e.textContent.includes(%r)).click()" % name)
        opened = wait_for(lambda: pg.evaluate("(document.getElementById('dt-title')||{}).textContent") == name and pg.evaluate("document.getElementById('groupDetail').classList.contains('show')"), 10)
        pg.wait_for_timeout(800)   # and it stays that group (no other handler re-titles the window afterwards)
        head = pg.evaluate("[(document.getElementById('dt-title')||{}).textContent, (document.getElementById('dt-type')||{}).textContent]")
        T('a shortcut opens its own group (name and type)', opened and head[0] == name and 'Deal' in head[1], head)
        tabs = pg.evaluate("[...document.querySelectorAll('#gpBox .gp-tabs .gx-ptab')].map(e=>e.dataset.gpt)")
        T('the deal room shows no Listings tab in the live app (G-01: not in the database yet)', 'listings' not in tabs and 'disc' in tabs, tabs)
        pg.evaluate("document.querySelector('#groupDetail .btn-manage') && document.querySelector('#groupDetail .btn-manage').click()"); pg.wait_for_timeout(1500)
        scan('group manage')
        mt = pg.evaluate("(document.getElementById('tab-members')||{}).innerText||''")
        T('Manage → Members lists the real members only (no sample members or "412")', 'Fresh Purge' in mt and not re.search(r'412|Alia Mourad|Vivian', mt), mt[:200])
        pg.evaluate("closeGroup()"); pg.wait_for_timeout(500)
        side = pg.evaluate("[...document.querySelectorAll('#gx .mygroup')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim())")
        T('the Groups side list shows my group', len(side) == 1 and name in side[0], side)
        chip = pg.evaluate("([...document.querySelectorAll('#gx .cf-tag')].find(e=>/My Groups/.test(e.textContent))||{}).textContent||''")
        T('"My Groups (1)" after creating one', re.search(r'\(1\)', chip), chip)
        # the marketplace
        go('market', 4500); scan('market')
        db = dict(zip(('supply', 'demand', 'jobs'), sql("select (select count(*) from public.products where active and type='supply'), (select count(*) from public.enquiries where status='active' and type='demand'), (select count(*) from public.jobs where active)").split('|')))
        hero = pg.evaluate("[...document.querySelectorAll('#mkx .hero-stats .hstat-n')].map(e=>e.textContent.replace(/,/g,''))")
        T('the market hero counts listings and jobs from the database', hero and hero[0] == str(int(db['supply']) + int(db['demand'])) and hero[2] == db['jobs'], (hero, db))
        cats = pg.evaluate("[...document.querySelectorAll('#mkx .cat-grid .cat-count')].map(e=>e.textContent.replace(/,/g,''))")
        T('the category counts come from the database (Supply, Demand)', cats[:2] == [db['supply'], db['demand']], (cats, db))
        T('the sample services, jobs and comparison table are gone', pg.evaluate("!document.querySelector('#mkx .scard:not([data-live]), #mkx .jcard:not([data-live])') && getComputedStyle(document.querySelector('#mkx .compare-section')).display=='none'"))
        pg.evaluate("document.querySelector('#mkx .master-tab[data-tab=manage]').click()"); pg.wait_for_timeout(1800); scan('my listings')
        ml = pg.evaluate("(document.getElementById('tab-manage')||{}).innerText||''")
        T('My Listings shows no sample rows for a new account', not re.search(r'Metformin HCl BP/USP|Hyaluronic Acid|Contract Manufacturing — Tablets|247|Expiry notice', ml) and re.search(r'no listings yet', ml), ml[:300])
        T('no page shows a sample name or number to a new account', not found, found)
        T('no script errors', not errs, errs[:4])
        sql(f"delete from public.groups where id={gid}")
        b.close()
    done()

main()
