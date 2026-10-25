"""Greeting toasts (demo build): the sign-in and sign-up toasts greet the person by the first name after any title, with the word
that completes it — never a title, a father's name, «الله» alone or "undefined" (v-real-r1: ME.name.split(' ')[1] greeted every
«عبد الله» «يا الله» and a one-word name "undefined"). Since S-03 fix 6 (v-real-r2): honorifics and a leading article are skipped
(«الحاج أحمد» → «أحمد», «El Sayed Mohamed» → «Sayed»), a particle stays with its word («ابن سينا», «van der Berg»), a trailing comma
is dropped («Ali, Mohamed» → «Ali», «العلي، محمد» → «العلي»), and a Latin name is greeted in Latin in the Arabic interface too — the
demo account is greeted «Haytham» in both («أهلًا بعودتك يا Haytham!»), no longer translated to «هيثم». S-03 fix 8 (v-real6-r2): a kunya or
family prefix stays with its word («أم كلثوم», «آل سعود», «بنت الشاطئ», «Umm Kulthum», «Ben Ali»), «Abdel- Rahman» is «Abdel-Rahman», a
zero-width space is a space, and a leading ’ / ʿ is not said («’Abd al-Rahman» → «Abd al-Rahman»); the sign-up avatar skips it too.
S-03 fix 9 (v-real8, kept under the owner's username decision): a name written «Family, Given» greets the given name («Ali, Mohamed» →
«Mohamed», «العلي، محمد» → «محمد»; «Ahmed Ali, PhD» stays «Ahmed»), and an article is greeted with its word («El Sayed Mohamed» → «El Sayed»).
  python3 tests/demo/greeting_test.py [en|ar]   (DEMO_FILE, default /tmp/drugbox_brand.html)"""
from playwright.sync_api import sync_playwright
import os, sys
F = os.environ.get('DEMO_FILE', '/tmp/drugbox_brand.html'); LANG = sys.argv[1] if len(sys.argv) > 1 else 'en'; R = []
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:200]))
CASES = [('Dr. Haytham Dweedar', 'Haytham'), ('عبد الله السيد', 'عبد الله'), ('عبد الرحمن محمد', 'عبد الرحمن'), ('Prof. Dr. Ahmed Zewail', 'Ahmed'),
         ('Mo’men Abd El-Raouf', 'Mo’men'), ('محمد أحمد عبد الرحمن', 'محمد'), ('Ἀλέξανδρος', 'Ἀλέξανδρος'), ('د/ محمد علي', 'محمد'),
         ('ا.د/ سامي فهمي', 'سامي'), ('م. أحمد', 'أحمد'), ('Dr.Hala Ali', 'Hala'), ('د.أحمد علي', 'أحمد'), ('Pharm. Mona', 'Mona'),
         ('Abd El Rahman Ali', 'Abd El Rahman'), ('أبو بكر الصديق', 'أبو بكر'), ('D/ Ahmed', 'Ahmed'), ('Dr.', 'Dr.'),
         # S-03 fix 6 (v-real-r2): honorifics, articles, particles, trailing punctuation
         ('El Sayed Mohamed', 'El Sayed'), ('Al Sayed Ali', 'Al Sayed'), ('Ali, Mohamed', 'Mohamed'), ('العلي، محمد', 'محمد'), ('Smith, John Paul', 'John'), ('Dr. El Sayed Ali', 'El Sayed'), ('Ahmed Ali, PhD', 'Ahmed'), ('الحاج أحمد علي', 'أحمد'),
         ('الحاجة فاطمة محمود', 'فاطمة'), ('الشيخ محمد', 'محمد'), ('المهندس محمود سامي', 'محمود'), ('الدكتور أحمد', 'أحمد'), ('الأستاذ الدكتور سامي فهمي', 'سامي'),
         ('Sheikh Zayed', 'Zayed'), ('Hajj Ali Hassan', 'Ali'), ('ابن سينا', 'ابن سينا'), ('van der Berg', 'van der Berg'), ('Abu Bakr Salem', 'Abu Bakr'),
         ('أ. منى', 'منى'), ('م. أحمد علي', 'أحمد'), ('Al', 'Al'), ('Haytham', 'Haytham'),
         # S-03 fix 8 (v-real6-r2): a kunya or family prefix stays with its word, a space beside a hyphen is no word break, a zero-width
         # space is one, a leading ’ ʿ is not said
         ('أم كلثوم إبراهيم', 'أم كلثوم'), ('ام كلثوم', 'ام كلثوم'), ('آل سعود', 'آل سعود'), ('بنت الشاطئ', 'بنت الشاطئ'), ('Umm Kulthum', 'Umm Kulthum'),
         ('Om Kalthoum Ibrahim', 'Om Kalthoum'), ('Ben Ali Mohamed', 'Ben Ali'), ('Bint Ahmed Ali', 'Bint Ahmed'), ('Dr. Umm El Kheir Ali', 'Umm El Kheir'),
         ('Abdel- Rahman Ali', 'Abdel-Rahman'), ('El- Sayed Ali', 'El-Sayed'), ('Ahmed Hassan -MBA', 'Ahmed'), ('Ahmed\u200bAli', 'Ahmed'),
         ('’Abd al-Rahman Ali', 'Abd al-Rahman'), ('ʿAbd al-ʿAziz', 'Abd al-ʿAziz'), ('’Αννα Νίκου', 'Αννα'), ('ʻAli Hassan', 'Ali'), ('’', '’')]
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); ctx = b.new_context(viewport={'width': 1440, 'height': 900}); ctx.add_init_script("try{localStorage.setItem('dx_lang','%s')}catch(e){}" % LANG)
    pg = ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    pg.goto('file://' + F, wait_until='load'); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    E = pg.evaluate
    for name, want in CASES:
        got = E('(n) => dxGreetName(n)', name)
        T(f'«{name}» is greeted «{want}»', got == want, got)
    E("""() => { window.__toasts = []; const t = document.getElementById('toast');
      new MutationObserver(() => window.__toasts.push(t.textContent)).observe(t, { childList: true, subtree: true, characterData: true }); }""")
    pg.click('.lg-demo'); pg.click('#loginPage button.f-btn'); pg.wait_for_timeout(2800)
    toasts = E('window.__toasts')
    want = 'أهلًا بعودتك يا \u2068Haytham\u2069!' if LANG == 'ar' else 'Welcome back, Haytham!'
    T('sign-in toast: the demo account is greeted «Haytham» — in Latin in the Arabic interface too', any(want in t for t in toasts), toasts[-3:])
    T('…never «هيثم» (a translation of one person\'s name)', not any('هيثم' in t for t in toasts), toasts[-3:])
    T('…never "undefined"', not any('undefined' in t for t in toasts), toasts[-3:])
    E("window.__toasts = []"); E("signupEnter('د/ عبد الله السيد', 'Pharco', 'Pharmacist')"); pg.wait_for_timeout(900)
    toasts = E('window.__toasts')
    want = 'أهلًا بك في Drugbox يا ⁨عبد الله⁩!' if LANG == 'ar' else 'Welcome to Drugbox, عبد الله!'
    T('sign-up toast: «د/ عبد الله السيد» is greeted «عبد الله» (not the title, not «الله»)', any(want in t for t in toasts), toasts[-3:])
    E("signupEnter('’Abd al-Rahman Ali', 'Pharco', 'Pharmacist')"); pg.wait_for_timeout(500)
    T('sign-up avatar: «’Abd al-Rahman Ali» has the letters «AA» (a leading ’ is skipped)', E('ME.initials') == 'AA', E('ME.initials'))
    T('no errors in the page', not errs, errs)
    print(LANG, sum(R), '/', len(R)); b.close()
sys.exit(0 if R and all(R) else 1)
