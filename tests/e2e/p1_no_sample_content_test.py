"""Phase 1 (S-19, B-06, B-07, G-01…G-04): a brand-new account in the live app sees no sample content from the demo.
The demo's own sample words are read from the demo build itself (people, companies, groups, listings, services, jobs, the
sample conversation list), so the list never goes stale; then a fresh account walks Home, My Network, Messages, Groups (and the
inside of a group it creates), the Marketplace and My Listings, and the visible text is checked:
  - no element whose whole text is a sample name (sample data always matches exactly — names other suites create carry a tag);
  - none of the sample numbers and promises ("1.2K", "150,000+", "8×", "12K+", "top 12%", "27 unread", "412 real members"…);
  - the side menu / phone badges equal the real counts (0 for a new account), "Your shortcuts" and the Groups side list hold
    only real groups, the deal room's Listings tab lists only real listings (G-01, 0061), and the market counts equal the
    database's.
Phase 1b (S-19, J-05, B-06, J-SOCIAL-49): the top ticker never shows the demo's items (hidden while there is nothing real, then the
newest real listing); the sign-in page shows no invented totals and Home no stock faces and no empty TODAY card; the Jobs numbers
(strip, seniority counts, list headers) equal the database's and the 150,000+ reach claim is gone; My Intents starts empty, is kept
in profiles.intents and shows on the profile (to others too); another member's profile shows their real connection count, a visit
is counted in profile_views, and no "Post impressions" line (not recorded) is shown.
Settings: tests/e2e/_dx.py (APP_URL, DB_NAME…) and DEMO_FILE (default web/dist/drugbox.html)."""
import os, re
from playwright.sync_api import sync_playwright
from _dx import APP_URL as U, T, sql, ST, wait_for, done
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEMO = os.path.abspath(os.environ.get('DEMO_FILE', os.path.join(ROOT, 'web', 'dist', 'drugbox.html')))
SAMPLE_NUMBERS = [r'\b1\.2K\b', r'150,000\+', r'8×', r'12K\+', r'top 12%', r'\b27\b\s*unread', r'412 real members', r'Showing\s*\n?\s*853\b', r'\b3,800\b',
                  r'Online now', r'Unread \(2\)', r'\b76\b\s*open positions', r'\b54\b\s*providers', r'\b312\b\s*listings', r'Export Sales Director',
                  r'\b76 jobs\b', r'\b4 profiles\b', r'Post impressions', r'Search appearances', r'1,200\+']
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
        vocab = set(dp.evaluate(VOCAB_JS)); tick_demo = dp.evaluate("(window.TICKER_ITEMS||[]).map(t=>t.text)"); dc.close()
        T('the demo build gives the sample words to look for (people, groups, listings, services, jobs)', len(vocab) > 40 and 'API Sourcing & Supply' in vocab and 'Vivian Zhou' in vocab, len(vocab))
        T('the demo build gives its sample ticker items', len(tick_demo) >= 6, tick_demo)
        # 1b. the sign-in page (before sign-in): the anon key counts nothing (F-26/F-27), so no invented totals and no stock faces
        lc = b.new_context(viewport={'width': 1440, 'height': 900}); lp = lc.new_page(); lp.goto(U, wait_until='load'); lp.wait_for_timeout(400); lp.evaluate('endSplash()'); lp.wait_for_timeout(600)
        hero = lp.evaluate("""(()=>{const h=document.querySelector('.lg-hero'); if(!h) return null;
          return [...h.querySelectorAll('*')].filter(e=>e.getClientRects().length&&!e.closest('[style*="display: none"]')).map(e=>[...e.childNodes].filter(n=>n.nodeType===3).map(n=>n.nodeValue).join('')).join(' ').replace(/\\s+/g,' ')})()""")
        T('the sign-in page shows no invented totals (12K+ professionals, 1,200+ listings, 18 countries)', hero is not None and not re.search(r'12K\+|1,200\+|\b18\b|Professionals|Countries', hero) and
          lp.evaluate("(()=>{const s=document.querySelector('.lg-hero .lg-stats');return !s||getComputedStyle(s).display=='none'})()"), (hero or '')[-300:])
        T('the sign-in page shows no stock faces', lp.evaluate("document.querySelectorAll('.lg-hero .dg-faces-row img').length") == 0)
        lc.close()
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
            tick = pg.evaluate("[getComputedStyle(document.querySelector('.ticker')).display, document.getElementById('tickerInner').innerText]")
            bad = [t for t in tick_demo if t in tick[1]]
            if bad or (tick[0] != 'none' and not re.search(r'\S', tick[1].replace('● LIVE', ''))): found['ticker on ' + page] = bad or ['an empty ticker bar']
        badges = lambda: pg.evaluate("""()=>[...document.querySelectorAll('#sbNav .nl-badge, #mbnav .mb-badge, .tnb .nbadge')].filter(e=>getComputedStyle(e).display!='none'&&e.textContent.trim()).map(e=>e.closest('[id]').id+':'+e.textContent.trim())""")
        T('a new account has no message, request or alert badges (side menu, phone bar, top bar)', not badges(), badges())
        for page in ('feed', 'network', 'messages', 'notifs', 'profile', 'saved', 'training', 'companies', 'jobs'):
            go(page); scan(page)
            if page == 'jobs':
                pg.evaluate("document.querySelector('#jx .mode-opt[data-mode=hunting]').click()"); pg.wait_for_timeout(400); scan('jobs (job hunting)')
        # Home: no stock faces (members' own photos only), no empty TODAY card
        go('feed')
        faces = pg.evaluate("[...document.querySelectorAll('#content .dg-faces-row img')].map(e=>e.src)")
        T('Home shows no stock faces beside "N professionals" (only members\' own photos)', not [f for f in faces if f.startswith('data:')], [f[:40] for f in faces])
        T('Home shows no empty TODAY card', pg.evaluate("(()=>{const a=document.querySelector('#content .dg-today');return !a||a.querySelectorAll('li').length>0})()"))
        # Jobs (J-05): every number from the database
        go('jobs', 3000)
        js = dict(zip(('open', 'week', 'cand', 'exec', 'senior', 'mid', 'junior', 'entry'), map(int, sql(f"""select count(*), count(*) filter (where created_at >= now() - interval '7 days'),
            (select count(*) from public.profiles where open_to_work and id <> '{me}'),
            count(*) filter (where seniority in ('exec','executive')), count(*) filter (where seniority = 'senior'),
            count(*) filter (where coalesce(seniority,'') not in ('exec','executive','senior','junior','entry')), count(*) filter (where seniority = 'junior'), count(*) filter (where seniority = 'entry')
            from public.jobs where active""").split('|'))))
        num = lambda t: int(re.sub(r'[^\d]', '', t) or -1)
        strip = pg.evaluate("[...document.querySelectorAll('#jx .intel-strip .intel-item b')].map(e=>e.textContent)")
        T('Jobs: open positions, posted this week and candidates available come from the database', [num(x) for x in strip] == [js['open'], js['week'], js['cand']], (strip, js))
        sen = pg.evaluate("Object.fromEntries([...document.querySelectorAll('#jx .sen-opt[data-level] .sen-count')].map(e=>[e.parentElement.dataset.level, e.textContent]))")
        T('Jobs: the seniority counts come from the database', {k: num(v) for k, v in sen.items()} == {k: js[k] for k in ('exec', 'senior', 'mid', 'junior', 'entry')}, (sen, js))
        heads = pg.evaluate("[...document.querySelectorAll('#jx .sec-title')].map(e=>e.innerText.replace(/\\s+/g,' '))")
        hj = [h for h in heads if h.startswith('Open Positions')]; hc = [h for h in heads if h.startswith('Available Candidates')]
        T('Jobs: "Open Positions N jobs" and "Available Candidates N profiles" are the database counts', hj and num(hj[0]) == js['open'] and hc and num(hc[0]) == js['cand'], heads)
        cta = pg.evaluate("[...document.querySelectorAll('#jx .post-cta-sub')].map(e=>e.innerText).join(' | ')")
        members = int(sql("select count(*) from public.profiles"))
        T('Jobs: no "150,000+" reach claim — the real member count', '150,000' not in cta and ('Reach %s pharma professionals' % '{:,}'.format(members)) in cta, cta)
        shortcuts = pg.evaluate("[...document.querySelectorAll('#sidebar .sh-row')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim())")
        T('"Your shortcuts" holds no sample group for a new account', not shortcuts, shortcuts)
        go('groups', 3500); scan('groups')
        side = pg.evaluate("[...document.querySelectorAll('#gx .mygroup')].filter(e=>e.getClientRects().length).map(e=>e.textContent.trim())")
        T('the Groups side list shows no group for a new account (it holds my real groups only)', not side, side)
        demo_cards = pg.evaluate("[...document.querySelectorAll('#gx .gcard:not([data-gid])')].length")
        T('every group card on the Groups page is a group from the database', demo_cards == 0, demo_cards)
        chip = pg.evaluate("([...document.querySelectorAll('#gx .cf-tag')].find(e=>/My Groups/.test(e.textContent))||{}).textContent||''")
        T('"My Groups (N)" counts my real groups (0)', re.search(r'\(0\)', chip), chip)
        # a deal room I create: shortcuts, side list and My Groups follow; its Listings are the database's (none yet)
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
        # G-01 keeps deal-room listings in the database (0061): the tab is there, and a new deal room lists nothing invented
        T('the deal room has its Listings tab (G-01, kept in the database)', 'listings' in tabs and 'disc' in tabs, tabs)
        pg.evaluate("document.querySelector('#gpBox [data-gpt=listings]').click()"); pg.wait_for_timeout(1800)
        lt = pg.evaluate("(document.querySelector('#gpBox [data-pane=listings]')||{}).innerText||''")
        T('… and a new deal room shows no sample listing', 'No requests or offers yet' in lt and not pg.evaluate("document.querySelectorAll('#gpBox [data-pane=listings] .dcard, #gpBox [data-pane=listings] .lcard').length"), lt[:160])
        pg.evaluate("document.querySelector('#gpBox [data-gpt=disc]').click()"); pg.wait_for_timeout(300)
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
        # My Intents (B-06): nothing chosen for a new account; what I choose is kept in my profile and shows on it
        pg.evaluate("document.querySelector('#mkx .master-tab[data-tab=intents]').click()"); pg.wait_for_timeout(600)
        act = pg.evaluate("[...document.querySelectorAll('#tab-intents .it-opt.active')].length"); pv = pg.evaluate("document.getElementById('profilePreviewTags').innerText")
        T('My Intents: a new account has nothing chosen (no preset sample intents) and the profile preview says so', act == 0 and 'Nothing selected' in pv, (act, pv[:120]))
        pg.evaluate("document.querySelector('#tab-intents .cat-intent-row[data-cat=api] .it-opt.i-have').click()"); pg.evaluate("document.querySelector('#tab-intents .cat-intent-row[data-cat=equipment] .it-opt.i-need').click()")
        pg.evaluate("document.querySelector('#tab-intents .btn-save-intents').click()")
        T('My Intents: Save keeps my choices in the database (profiles.intents)', wait_for(lambda: sql(f"select intents->>'api', intents->>'equipment', (select count(*) from jsonb_object_keys(intents)) from public.profiles where id='{me}'") == 'i-have|i-need|2', 8),
          sql(f"select intents from public.profiles where id='{me}'"))
        T('My Intents: nothing is kept in this browser instead', pg.evaluate("localStorage.getItem('dbx_intents')") is None)
        # the ticker shows a real listing once there is one
        sql(f"insert into public.products (user_id, type, category, name, price, unit, active) values ('{me}', 'supply', 'api', 'Purge Ticker Item {ST}', '9 USD', 'kg', true)")
        pg.reload(wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); wait_for(lambda: pg.evaluate("window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(1500)
        tick = wait_for(lambda: (lambda t: t if f'Purge Ticker Item {ST}' in t[1] else None)(pg.evaluate("[getComputedStyle(document.querySelector('.ticker')).display, document.getElementById('tickerInner').innerText]")), 10)
        T('the ticker shows the newest real listing (and none of the demo items)', tick and tick[0] != 'none' and not [t for t in tick_demo if t in tick[1]], tick)
        go('market', 3000); pg.evaluate("document.querySelector('#mkx .master-tab[data-tab=intents]').click()"); pg.wait_for_timeout(600)
        act = pg.evaluate("[...document.querySelectorAll('#tab-intents .it-opt.active')].map(e=>e.closest('.cat-intent-row').dataset.cat+':'+[...e.classList].find(c=>/^i-|^both$|^na$/.test(c)))")
        T('My Intents: after a reload my choices are shown again', sorted(act) == ['api:i-have', 'equipment:i-need'], act)
        go('profile', 1800)
        pi = pg.evaluate("(document.querySelector('#content .dx-pintents')||{}).innerText||''")
        T('My Intents show on my profile', 'APIs' in pi and 'Equipment' in pi and 'I have this to sell' in pi, pi)
        # another member opens my profile: my real connection count and intents; the visit is counted
        others = sql(f"select id from public.profiles where id <> '{me}' order by created_at desc limit 2").split()
        for o in others: sql(f"insert into public.connections (requester, addressee, status) values ('{me}', '{o}', 'accepted') on conflict do nothing")
        conn = int(sql(f"select count(*) from public.connections where status='accepted' and '{me}' in (requester, addressee)"))
        c2 = b.new_context(viewport={'width': 1440, 'height': 900}); c2.add_init_script("try{localStorage.setItem('dx_tour_done','1')}catch(e){}")
        p2 = c2.new_page(); p2.on('pageerror', lambda e: errs.append(str(e)[:160])); p2.goto(U, wait_until='load'); p2.wait_for_timeout(400); p2.evaluate('endSplash()'); p2.wait_for_timeout(700)
        p2.evaluate('showSignup()'); p2.fill('#suName', 'Fresh Visitor'); p2.fill('#suEmail', f'purgev{ST}@x.test'); p2.fill('#suPw', 'Strong-pass-2026'); p2.click('#signupPage button.f-btn')
        wait_for(lambda: p2.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); p2.wait_for_timeout(1500)
        views0 = int(sql(f"select profile_views from public.profiles where id='{me}'"))
        p2.evaluate("u=>gotoProfile(dxLive.aid(u))", me); p2.wait_for_timeout(2500)
        stats = p2.evaluate("[...document.querySelectorAll('#content .profile-stats .pstat-n')].map(e=>e.textContent)")
        T("another member sees my real connection count on my profile", len(stats) > 1 and int(re.sub(r'\D', '', stats[1]) or -1) == conn, (stats, conn))
        pi2 = p2.evaluate("(document.querySelector('#content .dx-pintents')||{}).innerText||''")
        T('another member sees my intents on my profile', 'APIs' in pi2 and 'Equipment' in pi2, pi2)
        T('the visit is counted once in my profile views', wait_for(lambda: int(sql(f"select profile_views from public.profiles where id='{me}'")) == views0 + 1, 6), (views0, sql(f"select profile_views from public.profiles where id='{me}'")))
        c2.close()
        T('no page shows a sample name or number to a new account', not found, found)
        T('no script errors', not errs, errs[:4])
        sql(f"delete from public.groups where id={gid}")
        b.close()
    done()

main()
