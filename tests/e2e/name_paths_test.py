"""Every way a person's name can be written, against the running live stack (S-03, fourth and fifth versions of the name rule,
0039_names_rule_4, 0039_names_rule_5 and 0039_names_rule_6).
The ways a name reaches profiles.name (supabase/tests/privacy_names.rls.sql checks the same list in the catalog, so a new one fails
there): the sign-up trigger handle_new_user (the sign-up API's metadata), a member's own UPDATE (Edit Profile = PATCH /rest/v1/profiles),
anon (refused), INSERT / upsert of a profile (refused), another member's row (row security), a later change of the auth metadata (never
copied). No RPC writes or copies a name (checked here in the catalog too). For each: a name the rule refuses is refused, a look-alike
of an existing member is normalised the same way (the mark over an undotted Arabic letter removed: «حْالد» is stored «حالد»; an
accent that draws like another is keyed as its twin: «Josè» / «José»), and the stored name_key is exactly what the APP's skeleton
(the generated rule in the served adapter, nmSkel) makes of the same input. The sign-up form shows the refusals in English and
Arabic with the quoted letter isolated (U+2068 … U+2069), and the sign-in toast is in Arabic with the name isolated. Fifth version
(v-spoof-r1, v-real-r1): a bracket the bidi algorithm reorders is refused on every path («(MBA) Ali» drew as «Ali (MBA)» in Arabic),
bold look-alikes are keyed as twins («ئروت» / «ثروت», «Szổke» / «Szőke»), a zero-width non-joiner between Arabic letters is a space,
and the sign-in toast greets the first name (never a title, «الله» alone or a father's name). Sixth version (round 5): the skeleton
over-merges — «Alİ Kaya» (Turkish İ) is «Ali Kaya»'s twin, «عبد الله أحمد» is «عبدالله أحمد»'s (spaces are ignored), «حالد» is «خالد»'s
(one dot apart) — on every path, keyed as the app keys them; a space inside a bracket is tidied («Ali ( MBA )» → «Ali (MBA)»); a member
whose name breaks the rule only by the place of its brackets is told to move them (its own banner text, EN and AR); the greeting
skips honorifics and a leading article and says a Latin name in Latin in the Arabic interface.
  python3 tests/e2e/name_paths_test.py        (tools/local-supabase/start.sh; settings in tests/e2e/_dx.py)"""
import json
from playwright.sync_api import sync_playwright
from _dx import APP_URL as U, R, T, sql, ST, NT, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

FSI, PDI = '⁨', '⁩'
PW = 'Strong-pass-2026'
def q(s): return "'" + s.replace("'", "''") + "'"
def row(email): return sql(f"select p.id || '|' || p.name || '|' || p.name_key || '|' || p.name_needs_fix from public.profiles p join auth.users u on u.id = p.id where u.email = {q(email)}")
def make(email, name):   # a member made on the server (the person a look-alike would copy)
    return sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ({q(email)}, crypt('x-pass-123', gen_salt('bf')), jsonb_build_object('name', {q(name)})) returning id").split('\n')[0]

KHALID, JOSE, THARWAT, SZOKE = f'خالد {NT}', f'José {NT}', f'ثروت {NT}', f'Szőke {NT}'
ALI, ABDALLAH = f'Ali Kaya {NT}', f'عبدالله أحمد {NT}'
k_id, j_id = make(f'np-k{ST}@np.test', KHALID), make(f'np-j{ST}@np.test', JOSE)
t_id, s_id = make(f'np-t{ST}@np.test', THARWAT), make(f'np-s{ST}@np.test', SZOKE)
a_id, d_id = make(f'np-a{ST}@np.test', ALI), make(f'np-d{ST}@np.test', ABDALLAH)
T('setup: the members a look-alike would copy exist', sql(f"select count(*) from public.profiles where id in ('{k_id}', '{j_id}')") == '2')

# the catalog: no function other than the sign-up trigger writes a name, none stores a profile's name elsewhere, nothing copies metadata later
T('catalog: the functions that INSERT or UPDATE profiles are handle_new_user and three counters', sql(r"""select string_agg(p.proname, ',' order by p.proname) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
  where n.nspname in ('public', 'private', 'auth') and p.prosrc ~* '(insert\s+into\s+(public\.)?profiles|update\s+(public\.)?profiles\s+(as\s+\w+\s+)?set)'""")
  == 'handle_new_user,increment_profile_view,person_followers_count,profiles_followers_count')
T('catalog: no function reads a profile name into a variable to store it elsewhere', sql(r"""select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace
  where n.nspname in ('public', 'private') and p.prosrc ~* 'insert\s+into' and p.prosrc ~* 'select\s+[^;]*\mname\M[^;]*\minto\M[^;]*from\s+(public\.)?profiles'""") == '0')
T('catalog: the only trigger on auth.users is the sign-up one (INSERT)', sql("select string_agg(tgname, ',') from pg_trigger where tgrelid = 'auth.users'::regclass and not tgisinternal") == 'on_auth_user_created')

# the app's own rule: the generated region of the adapter the live app serves, run in a blank page (the app's CSP forbids eval)
ADAPTER_SRC = "() => [...document.scripts].map((s) => s.src).find((s) => /\\/adapter\\.[0-9a-f]+\\.js/.test(s))"
def load_rule(ctx, url):
    import urllib.request
    t = urllib.request.urlopen(url).read().decode('utf8'); a = t.index('/* >>> generated'); b = t.index('/* <<< generated */')
    nm = ctx.new_page(); nm.set_content('<p>rule</p>')
    nm.evaluate("(g) => { window.__NM = new Function(g + '\\nreturn {nmNorm, nmProblem, nmSkel, nmMessage};')(); }", t[t.index('\n', a) + 1:b]); return nm
def app_skel(nm, s): return nm.evaluate('(s) => window.__NM.nmSkel(s)', s)
def app_norm(nm, s): return nm.evaluate('(s) => window.__NM.nmNorm(s)', s)

with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox']); ctx = b.new_context(viewport={'width': 1440, 'height': 900}); pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:150]))
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(500); pg.evaluate('endSplash()'); pg.wait_for_timeout(900)
    src = pg.evaluate(ADAPTER_SRC); nm = load_rule(ctx, src)
    T("the app's generated rule is read from the served adapter", 'adapter.' in src and nm.evaluate("typeof window.__NM.nmSkel") == 'function', src)

    # ── 1. the sign-up API (metadata), without the app's own check in front of it ──
    def live_eval(expr, arg=None):   # a sign-up that opens a session can reload the page: wait for the adapter, retry once
        for i in range(3):
            try:
                wait_for(lambda: pg.evaluate("typeof window.dxLive === 'object' && !!window.dxLive.sb"), 15)
                return pg.evaluate(expr, arg)
            except Exception as e:
                if 'context was destroyed' not in str(e) and 'dxLive is not defined' not in str(e) or i == 2: raise
                pg.wait_for_timeout(1000)
    def signup(email, name):
        return live_eval("([e, pw, n]) => dxLive.sb.auth.signUp({ email: e, password: pw, options: { data: { name: n } } }).then((r) => r.error ? { code: r.error.code || r.error.status || '', message: r.error.message || '' } : null)", [email, PW, name])
    for name, why in [(f'Ɗanjuma {NT}', 'a letter not supported yet (Hausa Ɗ)'), (f'Ali {NT} - MBA', 'a spaced hyphen'), (f'Rаna {NT}', 'a Cyrillic а inside a Latin word'),
                      (f'Ahme̵d {NT}', 'a mark NFKC cannot join to its letter'), (f'Hala {NT} · Pharco', 'the picker separator'),
                      (f'(MBA) Ali {NT}', 'a bracket before the name (fifth version: drew as «Ali (MBA)» in Arabic)'),
                      (f'Ali {NT} (علي) محمد', 'an Arabic word in brackets between a Latin and an Arabic word (drew as «Ali محمد (علي)»)')]:
        e = f'np-bad{len(R)}{ST}@np.test'; r = signup(e, name)
        T(f'sign-up API: {why} is refused, nothing is created', r is not None and sql(f"select count(*) from auth.users where email = {q(e)}") == '0', r)
    LA = {f'حْالد {NT}': f'np-lak{ST}@np.test', f'Josè {NT}': f'np-laj{ST}@np.test', f'ئروت {NT}': f'np-lat{ST}@np.test', f'Szổke {NT}': f'np-las{ST}@np.test',
          f'Alİ Kaya {NT}': f'np-lai{ST}@np.test', f'عبد الله أحمد {NT}': f'np-lad{ST}@np.test'}
    for name, look, why in [(f'حْالد {NT}', KHALID, 'ح + sukun (looks like «خالد»)'), (f'Josè {NT}', JOSE, 'è (looks like «José»)'),
                            (f'ئروت {NT}', THARWAT, 'ئ (bold, looks like «ثروت»)'), (f'Szổke {NT}', SZOKE, 'ổ (bold, looks like «Szőke»)'),
                            (f'Alİ Kaya {NT}', ALI, 'the Turkish İ for i (bold, looks like «Ali Kaya», round 5)'), (f'عبد الله أحمد {NT}', ABDALLAH, 'a space after د (looks like «عبدالله أحمد», round 5)')]:
        e = LA[name]; r = signup(e, name); rw = row(e).split('|')
        T(f'sign-up API: {why} is stored as the rule writes it, keyed as the app keys it', r is None and len(rw) == 4 and rw[1] == app_norm(nm, name) and rw[2] == app_skel(nm, name)
          and rw[3] == 'false', [r, rw, app_norm(nm, name)])
    rw = row(f'np-lak{ST}@np.test').split('|')
    T('sign-up API: «حْالد» is stored «حالد» (no mark left to draw as the dot) — and is «خالد»\'s twin (sixth version: one dot apart)', rw[1] == f'حالد {NT}' and rw[2] == row(f'np-k{ST}@np.test').split('|')[2], rw)
    for e2, e1, what in [('lai', 'a', '«Alİ Kaya» has «Ali Kaya»\'s skeleton (İ is i — sixth version)'), ('lad', 'd', '«عبد الله أحمد» has «عبدالله أحمد»\'s skeleton (the skeleton ignores spaces — sixth version)')]:
        r2, r1 = row(f'np-{e2}{ST}@np.test').split('|'), row(f'np-{e1}{ST}@np.test').split('|')
        T('sign-up API: ' + what + ', both stored as typed', r2[2] == r1[2] and r2[1] != r1[1] and r2[3] == r1[3] == 'false', [r1, r2])
    e = f'np-br{ST}@np.test'; r = signup(e, f'Ali {NT} ( MBA )')
    T('sign-up API: «Ali ( MBA )» is stored «Ali (MBA)» (sixth version: the spaces inside the brackets tidied; it was refused)', r is None and row(e).split('|')[1] == f'Ali {NT} (MBA)' and row(e).split('|')[3] == 'false', [r, row(e)])
    T('sign-up API: «Josè» has «José»\'s skeleton (a twin, told apart in every list)', row(f'np-laj{ST}@np.test').split('|')[2] == row(f'np-j{ST}@np.test').split('|')[2])
    T('sign-up API: «ئروت» has «ثروت»\'s skeleton (bold initial ئ / ث, fifth version)', row(f'np-lat{ST}@np.test').split('|')[2] == row(f'np-t{ST}@np.test').split('|')[2])
    T('sign-up API: «Szổke» has «Szőke»\'s skeleton (bold ő / ổ, fifth version)', row(f'np-las{ST}@np.test').split('|')[2] == row(f'np-s{ST}@np.test').split('|')[2])
    e = f'np-sl{ST}@np.test'; r = signup(e, f'د / Sami {NT}')
    T('sign-up API: «د / Sami» is stored «د/ Sami» (the slash joined to the title)', r is None and row(e).split('|')[1] == f'د/ Sami {NT}', [r, row(e)])
    live_eval("dxLive.sb.auth.signOut().then(() => 0)"); pg.wait_for_timeout(300)

    # ── 2. the sign-up form: the refusal names the letter, isolated, in English and Arabic ──
    pg.reload(wait_until='load'); pg.wait_for_timeout(500); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate('showSignup()'); pg.wait_for_timeout(300)
    pg.fill('#suName', f'Ɗanjuma {NT}'); pg.fill('#suEmail', f'np-ui{ST}@np.test'); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(600)
    msg = pg.inner_text('#suErr')
    T('sign-up form (EN): «not supported yet», the letter isolated', msg == f'The letter “{FSI}Ɗ{PDI}” ({FSI}U+018A{PDI}) is not supported in names yet', repr(msg))
    pg.fill('#suName', f'Ali {NT} - MBA'); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(500)
    T('sign-up form (EN): a spaced hyphen → the parentheses suggested', f'write “{FSI}Ali {NT} (MBA){PDI}”' in pg.inner_text('#suErr'), repr(pg.inner_text('#suErr')))
    pg.fill('#suName', f'(MBA) Ali {NT}'); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(500)
    T('sign-up form (EN): a bracket before the name → the bracket after it suggested', pg.inner_text('#suErr') == f'Put the part in brackets after the name — write “{FSI}Ali {NT} (MBA){PDI}”', repr(pg.inner_text('#suErr')))
    ar = ctx.new_page(); ar.add_init_script("try{localStorage.setItem('dx_lang','ar')}catch(e){}"); ar.goto(U, wait_until='load'); ar.wait_for_timeout(500); ar.evaluate('endSplash()'); ar.wait_for_timeout(900)
    ar.evaluate('showSignup()'); ar.wait_for_timeout(300)
    ar.fill('#suName', f'Ɗanjuma {NT}'); ar.fill('#suEmail', f'np-uia{ST}@np.test'); ar.fill('#suPw', PW); ar.click('#signupPage button.f-btn'); ar.wait_for_timeout(600)
    msg = ar.inner_text('#suErr')
    T('sign-up form (AR): «الحرف … غير مدعوم في الأسماء بعد», the Latin letter and its code isolated', msg == f'الحرف «{FSI}Ɗ{PDI}» ({FSI}U+018A{PDI}) غير مدعوم في الأسماء بعد', repr(msg))
    ar.fill('#suName', f'Ahme̵d {NT}'); ar.click('#signupPage button.f-btn'); ar.wait_for_timeout(500)
    msg = ar.inner_text('#suErr')
    T('sign-up form (AR): a mark NFKC cannot join → the letter and the mark isolated in the Arabic sentence', msg.startswith(f'احذف العلامة المضافة إلى «{FSI}e̵{PDI}» ({FSI}U+0335{PDI})'), repr(msg))
    ar.fill('#suName', f'Ali {NT} - MBA'); ar.click('#signupPage button.f-btn'); ar.wait_for_timeout(500)
    T('sign-up form (AR): the parentheses suggested', ar.inner_text('#suErr') == f'ضع ما يلي الاسم بين قوسين — اكتب «{FSI}Ali {NT} (MBA){PDI}»', repr(ar.inner_text('#suErr')))
    ar.fill('#suName', f'(صيدلي) أحمد {NT}'); ar.click('#signupPage button.f-btn'); ar.wait_for_timeout(500)
    T('sign-up form (AR): a bracket before the name → «ضع الجزء الذي بين القوسين بعد الاسم», the name isolated', ar.inner_text('#suErr') == f'ضع الجزء الذي بين القوسين بعد الاسم — اكتب «{FSI}أحمد {NT} (صيدلي){PDI}»', repr(ar.inner_text('#suErr')))
    ar.fill('#suName', f'Hala {NT} – Head of QA – Pharco'); ar.click('#signupPage button.f-btn'); ar.wait_for_timeout(500)
    T('sign-up form (AR): several dashes → one pair the rule accepts', ar.inner_text('#suErr') == f'ضع ما يلي الاسم بين قوسين — اكتب «{FSI}Hala {NT} (Head of QA, Pharco){PDI}»', repr(ar.inner_text('#suErr')))
    T('sign-up form: nothing was created by the refused names', sql(f"select count(*) from auth.users where email in ('np-ui{ST}@np.test', 'np-uia{ST}@np.test')") == '0')
    # the form with a look-alike: what the app shows is what the database stored (no sukun)
    ar.fill('#suName', f'حْالد {NT}'); ar.click('#signupPage button.f-btn')
    wait_for(lambda: ar.is_visible('#app'), 15); ar.wait_for_timeout(800)
    me = ar.evaluate("({id: dxLive.uuidOf(ME.id), name: ME.name})")
    T('sign-up form (AR): «حْالد» opens the app as «حالد» — the stored name, nothing over the ح', me['name'] == f'حالد {NT}' and row(f'np-uia{ST}@np.test').split('|')[1] == f'حالد {NT}', me)

    # ── 3. a member's own UPDATE (Edit Profile = PATCH /rest/v1/profiles) ──
    def patch(page, uid, body):
        return page.evaluate("([id, b]) => dxLive.sb.from('profiles').update(b).eq('id', id).select('id,name,name_key,name_needs_fix').then((r) => ({ e: r.error ? { code: r.error.code || '', message: r.error.message || '' } : null, d: r.data || [] }))", [uid, body])
    uid = me['id']
    r = patch(ar, uid, {'name': f'Ɔpɔku {NT}'})
    T('member: a letter not supported yet is refused (23514) and the name stays', r['e'] and r['e']['code'] == '23514' and row(f'np-uia{ST}@np.test').split('|')[1] == f'حالد {NT}', r)
    T('member: …the refusal names the letter, isolated', r['e'] and r['e']['message'] == f'The letter “{FSI}Ɔ{PDI}” ({FSI}U+0186{PDI}) is not supported in names yet', r)
    r = patch(ar, uid, {'name': f'(صيدلي) أحمد {NT}'})
    T('member: a bracket before the name is refused (23514), suggesting it after the name', r['e'] and r['e']['code'] == '23514' and r['e']['message'] == f'Put the part in brackets after the name — write “{FSI}أحمد {NT} (صيدلي){PDI}”', r)
    r = patch(ar, uid, {'name': f'منى (Ali) {NT}'})
    T('member: a Latin word in brackets between an Arabic and a Latin word is refused (drew as «منى … (Ali)» in Arabic)', r['e'] and r['e']['code'] == '23514', r)
    for name in [f'عْادة {NT}', f'رْياد {NT}', f'Saʿīd {NT}', f'Hêlène {NT}', f'مُحَمَّد {NT}', f'ا.د / Sami {NT}', f'ئروت {NT}', f'Szổke {NT}', f'علی\u200cرضا {NT}', f'Ali {NT} محمد (علي)',
                 f'Alİ Kaya {NT}', f'أبو بكر {NT}', f'Ahmed ( Mido ) {NT}']:   # sixth version: İ, a space after a letter that never joins, spaces inside brackets
        r = patch(ar, uid, {'name': name}); rw = row(f'np-uia{ST}@np.test').split('|')
        T(f'member: «{name}» stored as the rule writes it and keyed as the app keys it', not r['e'] and rw[1] == app_norm(nm, name) and rw[2] == app_skel(nm, name) and rw[3] == 'false', [r, rw, app_norm(nm, name)])
    T('member: the Arabic diacritics are gone from what was stored («مُحَمَّد» → «محمد»)', row(f'np-uia{ST}@np.test').split('|')[1] != f'مُحَمَّد {NT}' and app_norm(nm, f'مُحَمَّد {NT}') == f'محمد {NT}')
    T('member: a zero-width non-joiner between Arabic letters is a space («علی‌رضا» → «علی رضا»)', app_norm(nm, f'علی\u200cرضا {NT}') == f'علی رضا {NT}')
    T('member: spaces inside brackets are tidied («Ahmed ( Mido )» → «Ahmed (Mido)», sixth version)', app_norm(nm, f'Ahmed ( Mido ) {NT}') == f'Ahmed (Mido) {NT}')
    T('member: «أبو بكر» and «أبوبكر» are one name to the app (no spaces in the skeleton)', app_skel(nm, f'أبو بكر {NT}') == app_skel(nm, f'أبوبكر {NT}'))
    r = patch(ar, uid, {'name': f'حْالد {NT}', 'name_key': row(f'np-j{ST}@np.test').split('|')[2], 'name_needs_fix': True})
    rw = row(f'np-uia{ST}@np.test').split('|')
    T("member: a forged key (José's) and flag are ignored — the database keys «حْالد» itself", not r['e'] and rw[2] == app_skel(nm, f'حْالد {NT}') and rw[2] != row(f'np-j{ST}@np.test').split('|')[2] and rw[3] == 'false', [r, rw])
    r = patch(ar, k_id, {'name': f'حْالد {NT}'})
    T("member: another member's row is not touched (row security)", not r['e'] and r['d'] == [] and row(f'np-k{ST}@np.test').split('|')[1] == KHALID, r)
    r = ar.evaluate("(id) => dxLive.sb.from('profiles').insert({ id: id, name: 'NP extra' })" + ERR, sql("select gen_random_uuid()"))
    T('member: cannot INSERT a profile', r and refused(r) and r.get('code') == '42501', r)
    r = ar.evaluate("(id) => dxLive.sb.from('profiles').upsert({ id: id, name: 'Ɗanjuma' }, { onConflict: 'id' })" + ERR, uid)
    T('member: an upsert of her own row with a refused name is refused', r and refused(r) and row(f'np-uia{ST}@np.test').split('|')[1] == f'حالد {NT}', [r, row(f'np-uia{ST}@np.test')])
    r = ar.evaluate("() => dxLive.sb.auth.updateUser({ data: { name: 'Ɗanjuma' } }).then((r) => r.error ? (r.error.status || r.error.message) : 'ok')")
    T('member: changing the auth metadata later never changes the name', row(f'np-uia{ST}@np.test').split('|')[1] == f'حالد {NT}', [r, row(f'np-uia{ST}@np.test')])

    # ── 4. the sign-in toast is in Arabic, the name isolated ──
    ar.evaluate('doLogout()'); ar.wait_for_timeout(800)
    sql(f"update public.profiles set name = 'Dr. Sami {NT}' where id = '{uid}'")
    ar.evaluate('showLogin()'); ar.fill('#loginEmail', f'np-uia{ST}@np.test'); ar.fill('#loginPw', PW)
    ar.evaluate("""() => { window.__toasts = []; const t = document.getElementById('toast');
      new MutationObserver(() => window.__toasts.push(t.textContent)).observe(t, { childList: true, subtree: true, characterData: true }); }""")
    ar.click('#loginPage button.f-btn'); wait_for(lambda: ar.is_visible('#app'), 15); ar.wait_for_timeout(1500)
    toasts = ar.evaluate('window.__toasts')
    T('sign-in toast (AR): «أهلًا بعودتك يا …!» with the name isolated', any(f'أهلًا بعودتك يا {FSI}Sami{PDI}!' in t for t in toasts), toasts[-5:])
    # the greeting uses the first name — after the title, with the word that completes it (v-real-r1: «عبد الله» was greeted «يا الله»)
    for stored, greet in [(f'عبد الله {NT}', 'عبد الله'), (f'د/ محمد أحمد {NT}', 'محمد'), (f'Ἀλέξανδρος', 'Ἀλέξανδρος'),
                          (f'الحاج أحمد {NT}', 'أحمد'), (f'El Sayed Mohamed {NT}', 'Sayed'), (f'Ali, Mohamed {NT}', 'Ali'), (f'Haytham {NT}', 'Haytham')]:   # sixth version
        ar.evaluate('doLogout()'); ar.wait_for_timeout(800); sql(f"update public.profiles set name = {q(stored)} where id = '{uid}'")
        ar.evaluate('showLogin()'); ar.fill('#loginEmail', f'np-uia{ST}@np.test'); ar.fill('#loginPw', PW); ar.evaluate('window.__toasts = []')
        ar.click('#loginPage button.f-btn'); wait_for(lambda: ar.is_visible('#app'), 15); ar.wait_for_timeout(1500)
        toasts = ar.evaluate('window.__toasts')
        T(f'sign-in toast (AR): «{stored}» is greeted «{greet}»', any(f'أهلًا بعودتك يا {FSI}{greet}{PDI}!' in t for t in toasts) and not any('undefined' in t for t in toasts), toasts[-3:])

    # ── 4b. a member whose name breaks the rule only by the place of its brackets (stored before the fifth version): the banner says
    #        to move them, in English and Arabic (round 5: it said «characters Drugbox no longer allows») ──
    ar.evaluate('doLogout()'); ar.wait_for_timeout(800); sql(f"update public.profiles set name = {q(f'(MBA) Ali {NT}')} where id = '{uid}'")
    T('banner: precondition — a server write keeps «(MBA) Ali» and flags it', row(f'np-uia{ST}@np.test').split('|')[1] == f'(MBA) Ali {NT}' and row(f'np-uia{ST}@np.test').split('|')[3] == 'true')
    for page, lang, want in [(ar, 'ar', 'انقل الجزء الذي بين القوسين'), (pg, 'en', 'move the part in brackets after the name')]:
        if page is pg: pg.reload(wait_until='load'); pg.wait_for_timeout(500); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
        page.evaluate('showLogin()'); page.fill('#loginEmail', f'np-uia{ST}@np.test'); page.fill('#loginPw', PW); page.click('#loginPage button.f-btn')
        wait_for(lambda: page.is_visible('#app'), 15); page.wait_for_timeout(1200); page.evaluate('gotoProfile(ME.id)'); page.wait_for_timeout(1500)
        ban = page.evaluate("(() => { const d = document.querySelector('.dx-name-fix'); return d ? d.innerText : ''; })()")
        T(f'banner ({lang}): a bracket-order name is asked to move the part in brackets — not told it has characters Drugbox does not allow', want in ban and 'Drugbox' not in ban.split('\n')[0], repr(ban))
        page.evaluate('doLogout()'); page.wait_for_timeout(800)

    # ── 5. anon ──
    ar.evaluate('doLogout()'); ar.wait_for_timeout(800)
    r = patch(ar, k_id, {'name': f'حْالد {NT}'})
    T('anon: cannot write a name (refused or no row), the name stays', (r['e'] is None and r['d'] == []) or refused(r['e']), r)
    T('anon: …the database row is unchanged', row(f'np-k{ST}@np.test').split('|')[1] == KHALID)
    r = ar.evaluate("(id) => dxLive.sb.from('profiles').insert({ id: id, name: 'NP extra' })" + ERR, sql("select gen_random_uuid()"))
    T('anon: cannot INSERT a profile', r and refused(r), r)
    T('no JavaScript errors', not errs, errs)
    b.close()
done()
