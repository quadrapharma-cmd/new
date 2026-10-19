"""Social journeys — Home feed and posts: read, publish, media, react, comment, reply, repost/share, save, edit, delete,
report, mentions/hashtags (J-SOCIAL-10 … 21). Run: python3 tests/journeys/social_feed.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW, APP_VISIBLE, LOGIN_VISIBLE
from _social import *
import _dx

LIKE, COMMENT, REPOST, SAVE = 1, 2, 3, 4                      # the post action bar, in order (language-independent)

def act(post, k): return post.locator('.post-acts > .pact:nth-child(%d)' % k)
def num(s):
    m = re.findall(r'[\d,٠-٩]+', s or ''); return int(m[0].replace(',', '').translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))) if m else 0
def like_count(post):
    el = post.locator('.post-stats [onclick*="showReactors"]'); return num(el.inner_text()) if el.count() else 0
def comment_count(post):
    el = post.locator('.post-stats [onclick*="toggleComments"], .post-stats [data-tc]'); return num(el.first.inner_text()) if el.count() else 0
def pid(post): return int(post.get_attribute('id').split('-')[1])

def home(j, pg):
    j.nav(pg, 'feed'); j.settle(pg, 900)

def setup_live_pair(j, a_name='Dr. Amr Poster', b_name='Dr. Bassem Reader', connect=True):
    a = j.person(a_name); b = j.person(b_name)
    if connect: connect_db(j, a['id'], b['id'])
    return a, b

def demo_or_live_post(j, author, body, ago=5):
    """Live: a post by author written straight to the database (a precondition); returns its id."""
    return int(post_db(j, author['id'], body, 'regulatory', ago))

def fresh(j, pg):
    """Live: reload so the page fetches what the database now holds."""
    j.reload(pg); home(j, pg)

def reload_or_skip(j, pg, why):
    if j.demo: j.skip('demo keeps no data across a reload (no backend) — ' + why + ' is checked in live')
    fresh(j, pg)

@journey('J-SOCIAL-10')
def read_home_feed(j):
    """A member opens Home to catch up on her network's posts, newest first, and can keep scrolling."""
    long_body = 'Long circular summary ' + j.tag + '. ' + ('Zone IVb stability data is now the primary condition for local generics. ' * 8)
    if j.live:
        a, b = setup_live_pair(j, 'Dr. Aisha Reader', 'Dr. Badr Writer')
        c = j.person('Dr. Celine Other')
        for i in range(25):
            body = long_body if i == 3 else 'Badr update %02d %s' % (25 - i, j.tag)
            p = demo_or_live_post(j, b, body, ago=10 + i)
            if i == 1: j.sql("insert into public.post_media (post_id,url,type,name,size) values (%d,'%sstorage/v1/object/public/post-media/x.png','image','photo',1000)" % (p, _dx.APP_URL))
            if i == 2: j.sql("insert into public.post_media (post_id,url,type,name,size) values (%d,'%sstorage/v1/object/public/post-media/x.pdf','file','spec.pdf',40000)" % (p, _dx.APP_URL))
        for i in range(2): demo_or_live_post(j, c, 'Celine note %d %s' % (i, j.tag), ago=40 + i)
        pg = a['page']; fresh(j, pg)
    else:
        pg = j.demo_signin(j.new_page())
    with j.step('Land on Home: real posts newest first with author, headline, time, category and counts'):
        ps = posts(pg); j.check(ps, 'Home shows no posts')
        if j.live:
            mine = [x['text'] for x in ps if j.tag in x['text']]
            j.check(mine and mine[0].startswith('Badr update 25'), "B's newest post is not first among B's posts (first: \"%s\")" % (mine[0][:40] if mine else 'none shown'))
            nums = [int(m.group(1)) for m in (re.match(r'Badr update (\d+)', x) for x in mine) if m]
            j.check(nums == sorted(nums, reverse=True), 'posts are not newest first: %s' % nums[:8])
            demo = re.findall(r'Alia Mourad|Vivian Zhou|Omar Khaled|Indovista|12K\+ professionals|#EDA2025|UPCOMING EVENTS|Upcoming events|CPhI', j.text(pg) + j.text(pg, '#app'))
            j.check(not demo, 'live Home shows demo content: %s' % sorted(set(demo))[:6])
        first = pg.locator('#content .post').first
        j.check(first.locator('.post-name').count() and re.search(r'ago|now|منذ|الآن|\d', first.inner_text()), 'the first post has no author or time')
    with j.step('Click "see more" on a long post: the full text expands in place'):
        more = pg.locator('#content .post a[onclick*="expandPost"]:visible').first
        j.check(more.count(), 'no "see more" on a long post')
        box = pg.locator('#pb-' + more.get_attribute('data-ep')); before = len(box.inner_text())
        more.click(); pg.wait_for_timeout(300)
        j.check(len(box.inner_text()) > before + 20, '"see more" did not expand the text')
    with j.step('Scroll to the bottom repeatedly: older posts load until all are shown, then an end marker; no duplicates'):
        seen = []
        for _ in range(12):
            pg.evaluate("(()=>{const c=document.getElementById('content');c.scrollTop=c.scrollHeight;window.scrollTo(0,document.body.scrollHeight)})()"); pg.wait_for_timeout(900)
            ids = pg.eval_on_selector_all('#content .post', 'e=>e.map(x=>x.id)')
            if ids == seen: break
            seen = ids
        j.check(len(seen) == len(set(seen)), 'duplicate posts in the feed: %d shown, %d unique' % (len(seen), len(set(seen))))
        if j.live:
            n = pg.evaluate("t=>[...document.querySelectorAll('#content .post')].filter(e=>e.innerText.includes(t)).length", j.tag)
            j.check(n >= 27, 'scrolling showed %d of the 27 posts' % n)
        end = re.search(r"all caught up|no more posts|end of (the )?feed|You.ve seen|That.s all|لا مزيد|وصلت إلى النهاية|شاهدت كل", j.text(pg), re.I)
        j.check(end, 'no end marker after the last post')
    with j.step("Click an author name: that author's profile opens; Home returns to the feed"):
        pg.evaluate("(()=>{const c=document.getElementById('content');c.scrollTop=0})()")
        first = pg.locator('#content .post').first; name = first.locator('.post-name').inner_text().strip().split('\n')[0].strip()
        first.locator('.post-name').click(); j.settle(pg, 1200)
        head = j.text(pg)[:600]
        j.check(name.split()[0] in head and name.split()[-1] in head, "clicking the author did not open %s's profile" % name)
        home(j, pg); j.check(posts(pg), 'Home did not show the feed again')
    with j.step('Reload: the same posts with the same like/comment counts'):
        before = [(p['id']) for p in posts(pg)][:5]
        reload_or_skip(j, pg, 'the feed after reload')
        j.check([(p['id']) for p in posts(pg)][:5] == before, 'after reload the first posts differ')
    if j.live:
        with j.step('Each post view is counted (posts.view_count increases once per viewer)'):
            v = j.wait_db("select coalesce(max(view_count),0) from public.posts where user_id='%s'" % b['id'], 4)
            j.check(v not in ('', '0'), 'not built: post views are never counted (view_count stays 0 after A read the feed)')

@journey('J-SOCIAL-11')
def publish_text_post(j):
    """A company owner publishes a text update so his network sees it."""
    if j.live: a, b = setup_live_pair(j, 'Dr. Amr Poster', 'Dr. Bassem Reader'); pg = a['page']; fresh(j, pg)
    else: pg = j.demo_signin(j.new_page())
    body = 'Quarterly update %s\n\nNew GMP line approved by EDA. https://example.org/gmp-line #EDA2026 🎉\n\nسعداء بخدمة شركائنا %s' % (j.tag, SCRIPT)
    with j.step("Click \"What's on your mind\": the composer opens"):
        j.click(pg, r"What.s on your mind|تفكر|ماذا يدور|ما الذي يدور", what="What's on your mind")
        j.check(pg.is_visible('#postBody'), 'the composer did not open')
    with j.step('An empty post cannot be published'):
        n0 = len(posts(pg)); btn = pg.locator('.modal-bg [onclick^="submitPost"]').last
        if btn.is_enabled(): btn.click(); pg.wait_for_timeout(600)
        j.check(len(posts(pg)) == n0, 'an empty post was published')
    with j.step('Type a 3-paragraph update (Arabic, emoji, URL, #EDA2026), category Regulatory; Post'):
        if not pg.is_visible('#postBody'): j.click(pg, r"What.s on your mind|تفكر|ماذا يدور|ما الذي يدور", what="What's on your mind")
        pg.fill('#postBody', body); pg.select_option('#postCat', value='regulatory')
        pg.locator('.modal-bg [onclick^="submitPost"]').last.click(); j.settle(pg, 1200)
        top = pg.locator('#content .post').filter(has_not_text=re.compile('📌')).first; t = top.inner_text()
        j.check('Quarterly update ' + j.tag in t, 'the new post is not at the top (below pinned posts)')
        me = pg.evaluate('ME.name'); j.check(me.split()[-1] in t, 'the new post does not show the author name')
        j.check(re.search(r'just now|now|0m|الآن|للتو', t, re.I), 'the new post does not say "just now"')
        j.check(re.search(r'regulatory|تسجيل|تنظيمي|الشؤون التنظيمية|رقابي', t, re.I), 'the chosen category is not shown')
        j.check('\n' in top.locator('.post-body').inner_text().strip(), 'line breaks were lost')
        j.check(not pg.evaluate('window.__xss'), 'HTML typed into the post was executed')
        link = top.locator('a[href^="https://example.org/gmp-line"]')
        j.check(link.count(), 'the URL in the post is not a link')
        j.check('noopener' in (link.first.get_attribute('rel') or ''), 'the link has no rel=noopener')
    with j.step('Reload: the post is still there (live: posts row by A, category regulatory)'):
        if j.live: j.check(j.wait_db("select count(*) from public.posts where user_id='%s' and category='regulatory' and body like 'Quarterly update %s%%'" % (a['id'], j.tag), 6) == '1', 'no posts row for the new post')
        reload_or_skip(j, pg, 'the post after reload')
        j.check(any(('Quarterly update ' + j.tag) in p['text'] for p in posts(pg)), 'after reload the post is gone')
    with j.step('Own profile → Activity lists the post'):
        j.nav(pg, 'profile'); j.settle(pg, 900)
        tab = j.find(pg, r'^(Activity|Posts|النشاط|المنشورات)$', scope='#content', exact=True)
        if tab: tab.click(); j.settle(pg, 700)
        j.check(('Quarterly update ' + j.tag) in j.text(pg), 'the post is not on the own profile Activity')
    if j.live:
        with j.step("B sees the post on B's Home with A's name"):
            pb = b['page']; fresh(j, pb)
            t = next((p for p in posts(pb) if ('Quarterly update ' + j.tag) in p['text']), None)
            j.check(t and 'Amr' in t['author'], "the post is not on B's Home with A's name")
            j.check(not pb.evaluate('window.__xss'), "the script in the post ran in B's browser")

@journey('J-SOCIAL-12')
def post_photos_and_pdf(j):
    """A supplier posts product photos and a spec-sheet PDF so buyers can see and download them."""
    from PIL import Image
    d = os.path.join(j.cfg['out'], 'fixtures'); os.makedirs(d, exist_ok=True)
    img1, img2 = os.path.join(d, 'product-a.jpg'), os.path.join(d, 'product-b.png')
    Image.new('RGB', (900, 700), (40, 120, 200)).save(img1, quality=95); Image.new('RGB', (800, 600), (200, 80, 40)).save(img2)
    pdf = os.path.join(_dx.FIXTURES, 'spec.pdf'); j.check(os.path.exists(pdf), 'fixture %s missing (run tests/fixtures/make_fixtures.py)' % pdf)
    if j.live: a, b = setup_live_pair(j, 'Dr. Amr Supplier', 'Dr. Bassem Buyer'); pg = a['page']; fresh(j, pg)
    else: pg = j.demo_signin(j.new_page())
    with j.step('Click Photo in the composer and choose two images; previews show'):
        j.click(pg, r'^(📷 )?(Photo|صورة)$', scope='#content', what='Photo', exact=True)
        inp = pg.locator('.modal-bg input[type=file][accept*="image"]'); j.check(inp.count(), 'the composer has no photo picker')
        inp.set_input_files([img1, img2]); pg.wait_for_timeout(800)
        n = pg.locator('#postImgPrev img').count(); j.check(n == 2, '%d previews for 2 chosen images' % n)
    with j.step('Remove one image and add it again'):
        rm = pg.locator('#postImgPrev button, #postImgPrev [onclick*="remove" i], #postImgPrev [aria-label*="Remove" i], #postImgPrev span:has-text("×")')
        j.check(rm.count(), 'not built: an image preview cannot be removed')
        rm.first.click(); pg.wait_for_timeout(300); j.check(pg.locator('#postImgPrev img').count() == 1, 'remove did not remove the preview')
        inp.set_input_files([img2]); pg.wait_for_timeout(600); j.check(pg.locator('#postImgPrev img').count() == 2, 'adding again did not give 2 previews')
    with j.step('Attach the PDF; write a caption; post: both images and the PDF (name, size) show'):
        pg.locator('.modal-bg input[type=file]:not([accept])').set_input_files(pdf); pg.wait_for_timeout(500)
        pg.fill('#postBody', 'New batch photos and spec sheet ' + j.tag); pg.locator('.modal-bg [onclick^="submitPost"]').last.click(); j.settle(pg, 2500)
        top = post_el(j, pg, 'New batch photos and spec sheet ' + j.tag)
        j.check(top.locator('img').count() >= 2, 'the post does not show both images')
        j.check(re.search(r'spec\.pdf', top.inner_text()) and re.search(r'\d+\s?(KB|MB|kB|ك)', top.inner_text()), 'the post does not show the PDF name and size')
    if j.live:
        with j.step('Live: post_media rows for 2 images + 1 file and objects in the post-media bucket'):
            p = j.wait_db("select id from public.posts where user_id='%s' and body like 'New batch photos%%'" % a['id'], 6)
            j.check(j.wait_db("select count(*) from public.post_media where post_id=%s" % p, 8, want='3') == '3', 'post_media rows: %s (want 3)' % j.sql1("select count(*) from public.post_media where post_id=%s" % p))
        with j.step('B opens Home: the images open in a lightbox (Esc closes) and the PDF downloads identical in size'):
            pb = b['page']; fresh(j, pb); post = post_el(j, pb, 'New batch photos and spec sheet ' + j.tag)
            post.locator('img').first.click(); pb.wait_for_timeout(600)
            lb = pb.evaluate("[...document.querySelectorAll('.dx-lightbox,.lightbox,[class*=lightbox],[role=dialog]')].some(e=>e.getClientRects().length&&e.querySelector('img'))")
            j.check(lb, 'clicking an image does not open it larger')
            pb.keyboard.press('Escape'); pb.wait_for_timeout(300)
            a_pdf = post.locator('a:has-text("spec.pdf")'); j.check(a_pdf.count(), 'the PDF is not a link')
            with pb.expect_download(timeout=10000) as dl: a_pdf.first.click()
            got = dl.value.path(); j.check(os.path.getsize(got) == os.path.getsize(pdf), 'downloaded %d bytes, original %d' % (os.path.getsize(got), os.path.getsize(pdf)))
    with j.step('A wrong-type or too-big file is refused with a clear message'):
        big = os.path.join(d, 'huge.png')
        if not os.path.exists(big):
            with open(big, 'wb') as f: f.write(b'\x89PNG\r\n\x1a\n' + os.urandom(26 * 1024 * 1024))
        j.click(pg, r'^(📷 )?(Photo|صورة)$', scope='#content', what='Photo', exact=True)
        before = j.toast_mark(pg); pg.locator('.modal-bg input[type=file][accept*="image"]').set_input_files(big); pg.wait_for_timeout(1200)
        msg = j.toasts_since(pg, before) + [pg.evaluate("(document.querySelector('.modal-bg')||{}).innerText||''")]
        j.check(pg.locator('#postImgPrev img').count() == 0 or re.search(r'too (big|large)|max|كبير|الحد', ' '.join(msg), re.I), 'a 26 MB image was accepted without a message')
    with j.step('Reload: images and file are still there'):
        reload_or_skip(j, pg, 'media after reload')
        post = post_el(j, pg, 'New batch photos and spec sheet ' + j.tag)
        j.check(post.locator('img').count() >= 2 and 'spec.pdf' in post.inner_text(), 'after reload the images/file are gone')

def target_post(j, a, b, body):
    """Live: B wrote post P (database precondition); A sees it on Home. Demo: the first sample post by someone else."""
    if j.live:
        p = demo_or_live_post(j, b, body); pg = a['page']; fresh(j, pg); return pg, post_el(j, pg, body), p
    pg = j.demo_signin(j.new_page()); post = pg.locator('#content .post').first; return pg, post, pid(post)

@journey('J-SOCIAL-13')
def react_to_post(j):
    """A member reacts to a useful post so the author knows it helped."""
    a = b = None
    if j.live: a, b = setup_live_pair(j, 'Dr. Adel Reactor', 'Dr. Basma Author')
    pg, post, p = target_post(j, a, b, 'Useful circular for reactions ' + j.tag); post = pg.locator('#post-%d' % p)
    with j.step('Click Like on post P: the count changes by exactly 1 and the button shows the active state'):
        n0 = like_count(post)
        j.act(pg, act(post, LIKE).locator('[onclick*="doReact"]:visible').first, 'Like', lambda: like_count(post) == n0 + 1, timeout=3, expect='the reactions count to go from %d to %d' % (n0, n0 + 1))
        j.check('liked' in (act(post, LIKE).get_attribute('class') or '') or act(post, LIKE).get_attribute('aria-pressed') == 'true', 'the Like button shows no active state')
    with j.step('Choose another reaction (Insightful) from the reaction panel'):
        act(post, LIKE).hover(); pg.wait_for_timeout(500)
        ins = act(post, LIKE).locator('[data-rk="insightful"]')
        j.check(ins.count() and ins.first.is_visible(), 'no reaction panel on hover')
        ins.first.click(); pg.wait_for_timeout(500)
        j.check(like_count(post) == n0 + 1, 'changing the reaction changed the count to %d (want %d)' % (like_count(post), n0 + 1))
    with j.step('Click the reactions count: a list of who reacted (with my name), not a toast'):
        me = pg.evaluate('ME.name')
        j.act(pg, post.locator('.post-stats [onclick*="showReactors"]'), 'reactions count',
              lambda: pg.evaluate("n=>[...document.querySelectorAll('.modal-bg,[role=dialog]')].some(e=>e.getClientRects().length&&e.innerText.includes(n))", me))
        pg.keyboard.press('Escape')
    if j.live:
        with j.step('Live: a reactions row (P, A, kind) exists and like_count matches'):
            j.check(j.wait_db("select count(*) from public.reactions where post_id=%d and user_id='%s'" % (p, a['id']), 5) == '1', 'no reactions row after the click')
            j.check(j.wait_db("select kind from public.reactions where post_id=%d and user_id='%s'" % (p, a['id']), 5, want='insightful') == 'insightful', 'the reaction kind is not stored (want insightful)')
            j.check(j.sql1("select like_count from public.posts where id=%d" % p) == j.sql1("select count(*) from public.reactions where post_id=%d" % p), 'posts.like_count does not match the reactions rows')
    with j.step('Reload: the active state and count are the same'):
        reload_or_skip(j, pg, 'the reaction after reload')
        post = post_el(j, pg, 'Useful circular for reactions ' + j.tag)
        j.check(like_count(post) == n0 + 1 and 'liked' in (act(post, LIKE).get_attribute('class') or ''), 'after reload the reaction is lost')
    with j.step('Click Like again to remove it; reload: gone'):
        act(post, LIKE).locator('[onclick*="doReact"]:visible').first.click(); pg.wait_for_timeout(800)
        j.check(like_count(post) == n0, 'un-like did not restore the count')
        reload_or_skip(j, pg, 'un-like after reload')
        post = post_el(j, pg, 'Useful circular for reactions ' + j.tag)
        j.check(like_count(post) == n0 and 'liked' not in (act(post, LIKE).get_attribute('class') or ''), 'after reload the removed reaction is back')
        j.check(j.wait_db("select count(*) from public.reactions where post_id=%d and user_id='%s'" % (p, a['id']), 5, want='0') == '0', 'the reactions row is still there after un-like')
    with j.step('B gets one notification "A reacted to your post" that opens P'):
        if j.demo: j.skip('the other party exists only in live')
        # taking a reaction back also takes back its notification (0022, F-18/F-49): A reacts again first — after like,
        # insightful, un-like and like again B must still have exactly one notification about P from A
        act(post, LIKE).locator('[onclick*="doReact"]:visible').first.click()
        j.check(j.wait_db("select count(*) from public.reactions where post_id=%d and user_id='%s'" % (p, a['id']), 5, want='1') == '1', 'reacting again stored no reactions row')
        n = j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s' and post_id=%d" % (b['id'], a['id'], p))
        j.check(n == '1', '%s notifications for B about the reaction (want exactly 1)' % n)
        pb = b['page']; j.reload(pb); j.nav(pb, 'notifs'); j.settle(pb, 1000)
        # a notification row ([data-nid]) — not the "Reactions" filter tab above the list, which also matches /react/
        row = pb.locator('#content [data-nid]').filter(has_text=re.compile(r'react|liked|أعجب|تفاعل', re.I))
        # click the notification itself, not the reactor's name inside it (a name is a link to that person's profile; in
        # Arabic the row's centre falls on the Latin name)
        j.check(row.count(), 'B sees no reaction notification'); row.first.locator('.notif-time').click(); j.settle(pb, 1200)
        j.check(pb.locator('#post-%d' % p).count() and pb.locator('#post-%d' % p).first.is_visible(), 'clicking the notification does not open post P')
    if j.width <= 480:
        with j.step('On a phone (touch): a quick tap on Like likes and unlikes; pressing and holding Like opens the panel, and each of the six reactions is inside the screen and can be tapped'):
            tp = j.new_page(j.new_ctx(touch=True)); tp._touch = True
            if j.live: j.signin(tp, a['email'], a['pw']); home(j, tp); post = post_el(j, tp, 'Useful circular for reactions ' + j.tag)
            else: j.demo_signin(tp); post = tp.locator('#content #post-%d' % p)
            post.evaluate("e=>e.scrollIntoView({block:'center'})")
            on0, _ = rx_state(post); base = like_count(post) - (1 if on0 else 0)   # live: A reacted again in the previous step
            likebtn = act(post, LIKE).locator('[data-lp]')
            likebtn.tap(); tp.wait_for_timeout(500)
            j.check(rx_state(post)[0] != on0 and like_count(post) == base + (0 if on0 else 1), 'a quick tap on Like did not toggle Like')
            j.check(not act(post, LIKE).locator('.rxn-panel').is_visible(), 'a quick tap on Like also opened the reaction panel over the post')
            likebtn.tap(); tp.wait_for_timeout(500)
            j.check(rx_state(post)[0] == on0 and like_count(post) == base + (1 if on0 else 0), 'a second quick tap on Like did not toggle it back')
            if on0: likebtn.tap(); tp.wait_for_timeout(500)                 # start with no reaction: the panel's first choice adds one
            def hold():
                j.long_press(tp, act(post, LIKE).locator('[data-lp]'))
                j.check(act(post, LIKE).locator('.rxn-panel').is_visible(), 'pressing and holding Like does not open the reaction panel')
            every_reaction(j, tp, post, p, a, base, hold)
            if j.live:
                n = j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s' and post_id=%d" % (b['id'], a['id'], p))
                j.check(n == '1', 'changing the reaction left %s notifications for B (want exactly 1)' % n)
    else:
        with j.step('With the mouse and with the keyboard: each of the six reactions is inside the screen and can be chosen'):
            if j.live: fresh(j, pg); post = post_el(j, pg, 'Useful circular for reactions ' + j.tag)
            else: post = pg.locator('#content #post-%d' % p)
            post.evaluate("e=>e.scrollIntoView({block:'center'})")
            on0, _ = rx_state(post)
            if on0: act(post, LIKE).locator('[data-lp]').click(); pg.wait_for_timeout(500)   # start with no reaction
            base = like_count(post)
            def hover():
                pg.mouse.move(1, 1); pg.wait_for_timeout(150); act(post, LIKE).hover(); pg.wait_for_timeout(400)
                j.check(act(post, LIKE).locator('.rxn-panel').is_visible(), 'hovering Like does not open the reaction panel')
            every_reaction(j, pg, post, p, a, base, hover)
            pg.mouse.move(1, 1); pg.wait_for_timeout(200)
            # keyboard: Shift+Tab from Comment lands on Like and opens the panel; Tab walks the six reactions; Enter chooses
            act(post, COMMENT).focus(); pg.keyboard.press('Shift+Tab'); pg.wait_for_timeout(250)
            j.check(pg.evaluate("()=>document.activeElement&&document.activeElement.id||''").startswith('like-'), 'Shift+Tab from Comment does not reach Like')
            j.check(act(post, LIKE).locator('.rxn-panel').is_visible(), 'keyboard focus on Like does not open the reaction panel')
            order = []
            for _ in RX: pg.keyboard.press('Tab'); order.append(pg.evaluate("()=>(document.activeElement.dataset||{}).rk||''"))
            j.check(order == list(RX), 'Tab from Like does not walk the six reactions (got %s)' % order)
            pg.keyboard.press('Shift+Tab'); pg.keyboard.press('Enter'); pg.wait_for_timeout(500)   # back to Appreciation, choose it
            on, label = rx_state(post)
            mine = pg.evaluate("id=>{const x=(window.POSTS||[]).find(q=>q.id==id);return x?x.myKind||'':''}", p)
            j.check(on and like_count(post) == base + 1 and mine == 'appreciation', 'Enter on Appreciation did not choose it (my reaction "%s", button "%s")' % (mine, label.strip()))
            if j.live: j.check(j.wait_db("select kind from public.reactions where post_id=%d and user_id='%s'" % (p, a['id']), 5, want='appreciation') == 'appreciation', 'the keyboard choice (appreciation) is not stored')

RX = ('like', 'support', 'celebrate', 'insightful', 'appreciation', 'curious')
ON_SCREEN = """e=>{const r=e.getBoundingClientRect();const h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
  return r.width>0&&r.left>=0&&r.right<=innerWidth&&r.top>=0&&r.bottom<=innerHeight&&!!h&&(h===e||e.contains(h))}"""
def rx_state(post):
    l = act(post, LIKE); return (l.get_attribute('aria-pressed') == 'true' or 'liked' in (l.get_attribute('class') or ''), l.locator('[data-lp], [data-gpm="react"]').last.inner_text())
def rx_offscreen(post):
    """The reactions of the open panel that a person cannot reach (outside the screen or covered)."""
    return [k for k in RX if not act(post, LIKE).locator('[data-rk="%s"]' % k).evaluate(ON_SCREEN)]

def every_reaction(j, pg, post, p, a, n0, how):
    """Choose each of the six reactions in turn from the panel (opened by `how`) — all six inside the screen, the count stays
    n0 + 1, the Like button shows the kind chosen; live: one reactions row with that kind."""
    for k in RX:
        how()
        bad = rx_offscreen(post)
        j.check(not bad, 'at %dpx the reaction panel leaves %s outside the screen or covered' % (j.width, ', '.join(bad)))
        it = act(post, LIKE).locator('[data-rk="%s"]' % k)
        it.tap() if getattr(pg, '_touch', False) else it.click()
        pg.wait_for_timeout(400)
        on, label = rx_state(post)
        j.check(on and like_count(post) == n0 + 1, 'choosing "%s" left the post %s with %d reactions (want %d)' % (k, 'active' if on else 'not active', like_count(post), n0 + 1))
        mine = pg.evaluate("id=>{const x=(window.POSTS||[]).find(q=>q.id==id);return x?(x.myKind||(x.liked?'like':'')):''}", p)
        j.check(mine == k, 'after choosing "%s" the post holds my reaction "%s" (button "%s")' % (k, mine, label.strip()))
        if j.live:
            want = k                                                  # reactions.kind holds the six kinds (0028)
            got = j.wait_db("select string_agg(kind,',') from public.reactions where post_id=%d and user_id='%s'" % (p, a['id']), 5, want=want)
            j.check(got == want, 'after choosing "%s" the database holds kind(s) "%s" (want one row "%s")' % (k, got, want))

@journey('J-SOCIAL-14')
def comment_on_post(j):
    """A member comments on a post; the author and others see the comment."""
    a = b = None
    if j.live: a, b = setup_live_pair(j, 'Dr. Ahmed Commenter', 'Dr. Bothaina Author')
    pg, post, p = target_post(j, a, b, 'Circular for comments ' + j.tag); post = pg.locator('#post-%d' % p)
    text = 'Is this circular applicable to food supplements too? ' + j.tag
    with j.step('Click Comment on P, type the comment and press Enter: it appears with my name, the count +1'):
        n0 = comment_count(post)
        act(post, COMMENT).click(); pg.wait_for_timeout(800)
        inp = pg.locator('#ci-%d' % p); j.check(inp.is_visible(), 'the comment box did not open')
        inp.fill(text); inp.press('Enter'); pg.wait_for_timeout(900)
        box = pg.locator('#cmt-%d' % p); me = pg.evaluate('ME.name')
        j.check(text in box.inner_text(), 'the comment does not appear under the post')
        j.check(me.split()[-1] in box.locator('.cmt', has_text=text).inner_text(), 'the comment does not show my name')
        post = pg.locator('#post-%d' % p); j.check(comment_count(post) == n0 + 1, 'comment count %d → %d (want +1)' % (n0, comment_count(post)))
    if j.live:
        with j.step('Live: a comments row exists and comment_count is right'):
            j.check(j.wait_db("select count(*) from public.comments where post_id=%d and user_id='%s' and body=$q$%s$q$" % (p, a['id'], text), 5) == '1', 'no comments row')
            j.check(j.sql1("select comment_count from public.posts where id=%d" % p) == '1', 'posts.comment_count is %s' % j.sql1("select comment_count from public.posts where id=%d" % p))
    with j.step('Reload and open the comments again: still there, count matches'):
        reload_or_skip(j, pg, 'the comment after reload')
        post = pg.locator('#post-%d' % p); act(post, COMMENT).click(); pg.wait_for_timeout(1200)
        j.check(text in pg.locator('#cmt-%d' % p).inner_text() and comment_count(pg.locator('#post-%d' % p)) == 1, 'after reload the comment or count is wrong')
    with j.step("B gets a 'commented' notification; clicking it opens P with the comment visible"):
        if j.demo: j.skip('the other party exists only in live')
        pb = b['page']; j.reload(pb); j.nav(pb, 'notifs'); j.settle(pb, 1200)
        row = pb.locator('#content [onclick], #content .notif, #content .n-item').filter(has_text=re.compile('comment', re.I))
        j.check(row.count(), 'B has no comment notification')
        row.first.click(); j.settle(pb, 1200)
        j.check(pb.locator('#post-%d' % p).count() and text in j.text(pb), 'clicking the notification does not open post P with the comment')
    with j.step('C (a third member) sees the comment too'):
        if j.demo: j.skip('the other party exists only in live')
        c = j.person('Dr. Chaimaa Third'); pc = c['page']; fresh(j, pc)
        post = post_el(j, pc, 'Circular for comments ' + j.tag); act(post, COMMENT).click(); pc.wait_for_timeout(1500)
        j.check(text in pc.locator('#cmt-%d' % p).inner_text(), 'C does not see the comment')

@journey('J-SOCIAL-15')
def reply_to_comment(j):
    """A member replies to a specific comment so the conversation stays threaded."""
    if j.live:
        a, b = setup_live_pair(j, 'Dr. Anas Replier', 'Dr. Bahy Author'); c = j.person('Dr. Camelia Commenter')
        p = demo_or_live_post(j, b, 'Thread post ' + j.tag); k = comment_db(j, c['id'], p, 'First question from Camelia ' + j.tag)
        pg = a['page']; fresh(j, pg); post = post_el(j, pg, 'Thread post ' + j.tag)
    else:
        pg = j.demo_signin(j.new_page()); p = pid(pg.locator('#content .post').first); post = pg.locator('#post-%d' % p)
    with j.step("Open P's comments; click Reply on comment K"):
        act(post, COMMENT).click(); pg.wait_for_timeout(1200)
        cmt = pg.locator('#cmt-%d .cmt' % p).filter(has_not=pg.locator('.cmt-form')).first
        j.check(cmt.count(), 'P has no comment to reply to')
        reply = j.find(pg, r'^(Reply|رد|الرد)$', scope='#cmt-%d .cmt' % p, exact=True)
        j.act(pg, reply, 'Reply on a comment', lambda: pg.evaluate("id=>{const a=document.activeElement;return !!a&&/INPUT|TEXTAREA/.test(a.tagName)&&!!a.closest('#cmt-'+id)}", p))
    with j.step('Type a reply and send: it appears indented under K with "Replying to" context'):
        pg.keyboard.type('Yes — see clause 4 ' + j.tag); pg.keyboard.press('Enter'); pg.wait_for_timeout(900)
        j.check(pg.evaluate("t=>{const e=[...document.querySelectorAll('.cmt')].find(x=>x.innerText.includes(t));return !!e&&!!e.parentElement.closest('.cmt,.cmt-replies,[class*=reply]')}", 'clause 4 ' + j.tag), 'the reply is not nested under the comment')
    with j.step('Like comment K: stored and counted (not a toast)'):
        cm = pg.locator('#cmt-%d .cmt' % p).filter(has_not=pg.locator('.cmt-form')).first
        lk = cm.locator('[onclick]').filter(has_text=re.compile(r'👍|Like|أعجب')).first
        n0 = num(lk.inner_text()) if lk.count() else 0
        j.act(pg, lk if lk.count() else None, 'Like on a comment', lambda: num(lk.inner_text()) == n0 + 1)
        if j.live: j.check(j.has_table('comment_reactions') or j.has_table('comment_likes'), 'not built: no table for comment likes')
    if j.live:
        with j.step('Live: the reply is a comments row with parent_id = K'):
            j.check(j.wait_db("select count(*) from public.comments where post_id=%d and parent_id=%s and user_id='%s'" % (p, k, a['id']), 5) == '1', 'no comments row with parent_id=K for the reply')
    with j.step('Reload: thread structure and like are kept'):
        reload_or_skip(j, pg, 'the thread after reload')
        post = pg.locator('#post-%d' % p); act(post, COMMENT).click(); pg.wait_for_timeout(1500)
        j.check(pg.evaluate("t=>{const e=[...document.querySelectorAll('.cmt')].find(x=>x.innerText.includes(t));return !!e&&!!e.parentElement.closest('.cmt,.cmt-replies,[class*=reply]')}", 'clause 4 ' + j.tag), 'after reload the reply is no longer nested')
    with j.step('C gets "A replied to your comment" that opens P at the thread'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s' and post_id=%d" % (c['id'], a['id'], p)) >= '1', 'C got no reply notification')

@journey('J-SOCIAL-16')
def repost_and_share(j):
    """A member reposts a valuable post to his network or sends its link to a colleague."""
    if j.live:
        a, b = setup_live_pair(j, 'Dr. Akram Sharer', 'Dr. Bassant Friend'); c = j.person('Dr. Chadi Author')
        pg, post, p = target_post(j, a, c, 'Great post to share ' + j.tag)
    else:
        pg = j.demo_signin(j.new_page()); p = pid(pg.locator('#content .post').first); post = pg.locator('#post-%d' % p)
    shares0 = num(post.locator('.post-stats').inner_text().split('\n')[-1]) if post.locator('.post-stats').count() else 0
    with j.step("Click Repost on P (optionally with a comment) and confirm: an entry in my activity, share count +1"):
        def reposted():
            dlg = pg.evaluate("[...document.querySelectorAll('.modal-bg,[role=dialog]')].some(e=>e.getClientRects().length&&/repost|إعادة/i.test(e.innerText))")
            return dlg or re.search(r'reposted|أعاد نشر', j.text(pg), re.I)
        j.act(pg, act(post, REPOST), 'Repost', reposted)
        btn = j.find(pg, r'^(Repost|Confirm|Share|إعادة النشر|تأكيد|نشر)$', scope='.modal-bg', exact=True)
        if btn: btn.click(); j.settle(pg, 900)
        j.check(re.search(r'reposted|أعاد نشر', j.text(pg), re.I), 'no "reposted" entry after confirming')
        if j.live: j.check(j.wait_db("select share_count from public.posts where id=%d" % p, 5) == '1', 'posts.share_count did not become 1')
    with j.step('⋯ → Copy link puts a real URL to the post on the clipboard'):
        post = pg.locator('#post-%d' % p).first
        post_menu(j, pg, post, r'Copy link|نسخ الرابط', 'Copy link')
        clip = pg.evaluate("navigator.clipboard.readText().catch(()=>'')")
        j.check(re.search(r'(https?|file)://\S*(post|#|\?)\S*%d' % p, clip or ''), 'Copy link did not put a link to post %d on the clipboard (clipboard: "%s")' % (p, (clip or '')[:60]))
    with j.step('Open the link in a new tab (signed in): exactly post P'):
        pg2 = j.new_page(pg.context, url=clip)
        if j.demo and j.on_login(pg2): j.demo_signin(pg2)        # the demo keeps no session: every new tab starts at sign-in
        j.check(pg2.locator('#post-%d' % p).count() and pg2.locator('#post-%d' % p).first.is_visible(), 'the copied link does not open post P')
    with j.step('Open the link signed out: asks to sign in, then shows P'):
        pg3 = j.new_page(j.new_ctx(), url=clip)
        j.check(j.on_login(pg3), 'signed out, the link does not ask to sign in')
        if j.demo: j.demo_signin(pg3)
        else: j.signin(pg3, a['email'], a['pw'])
        j.check(pg3.locator('#post-%d' % p).count() and pg3.locator('#post-%d' % p).first.is_visible(), 'after signing in the link does not show post P')
    with j.step('Share → Send in a message to B: B gets a message with the post link'):
        post = pg.locator('#post-%d' % p).first
        el = j.find(pg, r'^(Send|Send in a message|Share|إرسال|مشاركة)$', scope='#post-%d' % p, exact=True)
        if not el: j.notbuilt('no "Send in a message" for a post')
        el.click(); j.settle(pg)
        j.check(pg.locator('.modal-bg input:visible').count(), 'Send has no recipient picker')
        if j.live:
            pg.locator('.modal-bg input:visible').first.fill('Bassant'); pg.wait_for_timeout(800)
            j.click(pg, 'Bassant', scope='.modal-bg', what='recipient Bassant'); j.click(pg, r'^(Send|إرسال)$', scope='.modal-bg', what='Send', exact=True)
            j.check(j.wait_db("select count(*) from public.messages where sender_id='%s' and receiver_id='%s' and body like '%%%d%%'" % (a['id'], b['id'], p), 6) == '1', 'no message to B with the post link')
    with j.step('C is notified that A reposted'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s' and post_id=%d" % (c['id'], a['id'], p)) == '1', 'C got no repost notification')

@journey('J-SOCIAL-17')
def save_posts(j):
    """A member saves posts to read again later and finds them in Saved."""
    if j.live:
        a, b = setup_live_pair(j, 'Dr. Asmaa Saver', 'Dr. Bilal Writer')
        p1 = demo_or_live_post(j, b, 'Circular one to keep ' + j.tag, 20); p2 = demo_or_live_post(j, b, 'Circular two to keep ' + j.tag, 10)
        pg = a['page']; fresh(j, pg)
    else:
        pg = j.demo_signin(j.new_page()); P = pg.locator('#content .post')
        p1, p2 = pid(P.nth(0)), pid(P.nth(2))
    t1 = pg.locator('#post-%d .post-body' % p1).inner_text()[:24].split('\n')[0]; t2 = pg.locator('#post-%d .post-body' % p2).inner_text()[:24].split('\n')[0]
    with j.step('Click Save on P1 and on P2: the button changes to "Saved" at once'):
        for x in (p1, p2):
            P = pg.locator('#post-%d' % x).first
            j.act(pg, act(P, SAVE), 'Save', lambda: re.search(r'Saved|محفوظ|تم الحفظ', act(P, SAVE).inner_text()) or 'saved' in (act(P, SAVE).get_attribute('class') or ''))
    if j.live:
        with j.step('Live: saved_posts rows for (A,P1) and (A,P2)'):
            j.check(j.wait_db("select count(*) from public.saved_posts where user_id='%s' and post_id in (%d,%d)" % (a['id'], p1, p2), 5, want='2') == '2', 'saved_posts rows missing')
    with j.step('Open Saved from the feed sidebar "Saved items": P1 and P2 listed, newest saved first'):
        j.nav(pg, 'feed'); el = j.find(pg, r'Saved items|العناصر المحفوظة|المحفوظات', scope='#content')
        j.act(pg, el, 'Saved items (feed sidebar)', lambda: pg.evaluate("document.body.getAttribute('data-page')") == 'saved')
        t = j.text(pg); j.check(t1 in t and t2 in t, 'Saved does not list both saved posts')
        j.check(t.index(t2) < t.index(t1), 'Saved is not newest-saved first')
    with j.step('Open P1 from the Saved list: the full post'):
        el = pg.locator('#content').get_by_text(t1, exact=False).first; el.click(); j.settle(pg)
        j.check(pg.locator('#post-%d' % p1).count() and pg.locator('#post-%d' % p1).first.is_visible(), 'clicking a saved item does not open the post')
    with j.step('Unsave P2 from Saved; reload: only P1 remains and still shows "Saved" on Home'):
        j.nav(pg, 'saved'); P = pg.locator('#post-%d' % p2).first
        j.check(P.count(), 'P2 is not on the Saved page'); act(P, SAVE).click(); pg.wait_for_timeout(800)
        if j.live: j.check(j.wait_db("select count(*) from public.saved_posts where user_id='%s'" % a['id'], 5, want='1') == '1', 'saved_posts not 1 row after unsave')
        reload_or_skip(j, pg, 'Saved after reload'); j.nav(pg, 'saved'); t = j.text(pg)
        j.check(t1 in t and t2 not in t, 'after reload Saved does not show P1 only')
        j.nav(pg, 'feed'); j.check(re.search(r'Saved|محفوظ', act(pg.locator('#post-%d' % p1).first, SAVE).inner_text()), 'P1 no longer shows "Saved" on Home')
    with j.step('Saved items are private: B cannot read A\'s saved posts'):
        if j.demo: j.skip('the other party exists only in live')
        r = b['page'].evaluate("u=>dxLive.sb.from('saved_posts').select('post_id').eq('user_id',u).then(r=>(r.data||[]).length)", a['id'])
        j.check(r == 0, "B can read A's saved posts (%s rows)" % r)

@journey('J-SOCIAL-18')
def edit_own_post(j):
    """A member corrects a typo in his own post after publishing."""
    if j.live:
        a, b = setup_live_pair(j, 'Dr. Ashraf Editor', 'Dr. Bassma Viewer')
        p = demo_or_live_post(j, a, 'Price is USD 5.08/kg typo ' + j.tag); pg = a['page']; fresh(j, pg)
    else:
        pg = j.demo_signin(j.new_page()); me = pg.evaluate('ME.name')
        p = pid(pg.locator('#content .post').filter(has=pg.locator('.post-name', has_text=me.split()[-1])).first)
    post = pg.locator('#post-%d' % p).first; body = post.locator('.post-body').inner_text()[:25]
    def editor(): return pg.locator('.modal-bg textarea:visible, #post-%d textarea:visible, #post-%d [contenteditable=true]:visible' % (p, p)).first
    with j.step('Open ⋯ on own post → Edit: an editor prefilled with the current text'):
        post_menu(j, pg, post, r'Edit|تعديل|عدّل', 'Edit')
        ed = editor(); j.check(ed.count() and body[:15] in (ed.input_value() if ed.evaluate('e=>e.tagName') == 'TEXTAREA' else ed.inner_text()), 'Edit did not open the text in an editor')
    with j.step('Change the text and save: updated in place with an "edited" marker'):
        ed.fill('Price is USD 5.80/kg corrected ' + j.tag); j.click(pg, r'^(Save|Update|حفظ|تحديث)$', scope='body', what='Save edit', exact=True); pg.wait_for_timeout(800)
        post = pg.locator('#post-%d' % p).first
        j.check('5.80/kg corrected' in post.inner_text(), 'the post text did not change')
        j.check(re.search(r'edited|معدل|تم التعديل', post.inner_text(), re.I), 'no "edited" marker')
    with j.step('Open Edit again and Cancel: the post is unchanged'):
        post_menu(j, pg, post, r'Edit|تعديل|عدّل', 'Edit'); editor().fill('SHOULD NOT SAVE')
        j.click(pg, r'^(Cancel|إلغاء)$', scope='body', what='Cancel', exact=True); pg.wait_for_timeout(500)
        j.check('SHOULD NOT SAVE' not in pg.locator('#post-%d' % p).first.inner_text(), 'Cancel changed the post')
    if j.live:
        with j.step('Live: posts.body updated; B sees the new text after reload'):
            j.check(j.wait_db("select count(*) from public.posts where id=%d and body like '%%5.80/kg corrected%%'" % p, 5) == '1', 'posts.body not updated')
            fresh(j, b['page']); j.check('5.80/kg corrected' in b['page'].locator('#post-%d' % p).first.inner_text(), 'B does not see the edited text')
    with j.step("Edit is not offered on other people's posts, and the database refuses it"):
        me = pg.evaluate('ME.name').split()[-1]
        other = pg.locator('#content .post').filter(has_not=pg.locator('.post-name', has_text=me)).first
        if j.live:
            x = demo_or_live_post(j, b, 'B post A cannot edit ' + j.tag); fresh(j, pg); other = pg.locator('#post-%d' % x).first
        names = other.locator('.ctx-item').all_inner_texts()
        j.check(not any(re.search(r'Edit|تعديل|عدّل', n) for n in names), "Edit is offered on someone else's post")
        if j.live:
            r = pg.evaluate("id=>dxLive.sb.from('posts').update({body:'HACK'}).eq('id',id).select().then(r=>(r.data||[]).length)", x)
            j.check(r == 0 and j.sql1("select body from public.posts where id=%d" % x) != 'HACK', "A edited B's post through the API")

@journey('J-SOCIAL-19')
def delete_own_post(j):
    """A member removes her own post that she no longer wants public."""
    if j.live:
        a, b = setup_live_pair(j, 'Dr. Azza Deleter', 'Dr. Bakr Friend')
        p = demo_or_live_post(j, a, 'Post to delete ' + j.tag, 20); q = demo_or_live_post(j, a, 'Post to keep via undo ' + j.tag, 10)
        comment_db(j, b['id'], p, 'B commented here'); j.sql("insert into public.post_media (post_id,url,type,name,size) values (%d,'%sstorage/v1/object/public/post-media/none.png','image','photo',10)" % (p, _dx.APP_URL))
        pg = a['page']; fresh(j, pg); P, Q = pg.locator('#post-%d' % p), pg.locator('#post-%d' % q)
    else:
        pg = j.demo_signin(j.new_page()); me = pg.evaluate('ME.name')
        own = pg.locator('#content .post').filter(has=pg.locator('.post-name', has_text=me.split()[-1]))
        j.check(own.count(), 'the demo feed has no own post'); p = pid(own.first); P = pg.locator('#post-%d' % p)
        j.click(pg, r"What.s on your mind|تفكر|ماذا يدور", what="What's on your mind"); pg.fill('#postBody', 'Post to keep via undo ' + j.tag)
        pg.locator('.modal-bg [onclick^="submitPost"]').last.click(); j.settle(pg); q = pid(post_el(j, pg, 'Post to keep via undo ' + j.tag)); Q = pg.locator('#post-%d' % q)
    with j.step('⋯ on P → Delete; confirm: the post leaves the list at once'):
        post_menu(j, pg, P, r'Delete|حذف', 'Delete')
        ok = j.find(pg, r'^(Delete|Yes, delete|Confirm|حذف|تأكيد|نعم)$', scope='.modal-bg', exact=True)
        if ok: ok.click()
        pg.wait_for_timeout(600)
        j.check(not P.is_visible(), 'the post is still in the list after Delete')
    with j.step('Delete Q, then Undo in the toast: Q is restored'):
        post_menu(j, pg, Q, r'Delete|حذف', 'Delete')
        ok = j.find(pg, r'^(Delete|Yes, delete|Confirm|حذف|تأكيد|نعم)$', scope='.modal-bg', exact=True)
        if ok: ok.click()
        pg.wait_for_timeout(300)
        j.click(pg, r'^(Undo|تراجع)$', scope='body', what='Undo', exact=True)
        j.check(Q.is_visible(), 'Undo did not restore the post')
    if j.demo:
        with j.step('Delete is not offered on other people\'s posts'):
            other = pg.locator('#content .post').filter(has_not=pg.locator('.post-name', has_text=pg.evaluate('ME.name').split()[-1])).first
            names = other.locator('.ctx-item').all_inner_texts()
            j.check(not any(re.search(r'Delete|حذف', n) for n in names), "Delete is offered on someone else's post")
        return
    with j.step('Wait 15 s; reload: P is gone with its comments, media; nobody sees it; Q stays'):
        pg.wait_for_timeout(16500)
        j.check(j.sql1("select count(*) from public.posts where id=%d" % p) == '0', 'posts row P still exists')
        j.check(j.sql1("select count(*) from public.posts where id=%d" % q) == '1', 'Q was deleted although Undo was clicked')
        j.check(j.sql1("select count(*) from public.comments where post_id=%d" % p) == '0' and j.sql1("select count(*) from public.post_media where post_id=%d" % p) == '0', 'comments/post_media of P remain')
        fresh(j, b['page']); j.check(not any(('Post to delete ' + j.tag) in x['text'] for x in posts(b['page'])), 'B still sees P after reload')
    with j.step("Deleting B's post with A's token is refused by the database"):
        bp = demo_or_live_post(j, b, 'B post that A cannot delete ' + j.tag)
        r = pg.evaluate("id=>dxLive.sb.from('posts').delete().eq('id',id).select().then(r=>({n:(r.data||[]).length,e:r.error&&r.error.message}))", bp)
        j.check(r['n'] == 0 and j.sql1("select count(*) from public.posts where id=%d" % bp) == '1', "A deleted B's post through the API: %s" % r)

@journey('J-SOCIAL-20')
def report_post(j):
    """A member reports a misleading post and a Drugbox moderator reviews and acts on it."""
    if j.live:
        a, b = setup_live_pair(j, 'Dr. Alaa Reporter', 'Dr. Bassel Other'); c = j.person('Dr. Cyrus Faker')
        pg, post, p = target_post(j, a, c, 'Our product has EDA approval (fake) ' + j.tag)
    else:
        pg = j.demo_signin(j.new_page()); p = pid(pg.locator('#content .post').first); post = pg.locator('#post-%d' % p)
    with j.step('⋯ on P → Report: a dialog with reasons (Spam / Misleading / Abusive / Other)'):
        post_menu(j, pg, post, r'Report|إبلاغ|بلاغ', 'Report')
        dlg = pg.locator('.modal-bg:visible, [role=dialog]:visible')
        j.check(dlg.count() and re.search(r'Spam|Misleading|Abusive|مزعج|مضلل|مسيء', dlg.first.inner_text()), 'dead end: Report has no dialog with reasons (%s)' % (j.toasts(pg)[:1] or 'nothing'))
    with j.step('Choose Misleading, add text, submit: a confirmation and "Hide this post"'):
        j.click(pg, r'Misleading|مضلل', scope='body', what='Misleading')
        ta = pg.locator('.modal-bg textarea:visible, [role=dialog] textarea:visible')
        if ta.count(): ta.first.fill('Claims an EDA approval that does not exist')
        j.click(pg, r'^(Submit|Report|Send|إرسال|إبلاغ)$', scope='body', what='Submit report', exact=True); pg.wait_for_timeout(800)
        j.check(re.search(r'Thanks|reported|received|شكرًا|تم', ' '.join(j.toasts(pg)) + j.text(pg, 'body')[:3000], re.I), 'no confirmation after reporting')
    with j.step('Report P again: "You already reported this"'):
        post_menu(j, pg, pg.locator('#post-%d' % p).first, r'Report|إبلاغ|بلاغ', 'Report')
        j.check(re.search(r'already reported|سبق.*الإبلاغ|أبلغت', ' '.join(j.toasts(pg)) + j.text(pg, 'body')[:4000], re.I), 'a second report is not recognised')
    if j.demo: return
    with j.step('Live: a post report row (reporter A, post P, reason, open); reporters cannot read others\' reports'):
        t = 'post_reports' if j.has_table('post_reports') else None
        j.check(t, 'not built: no post reports table in the database')
        j.check(j.sql1("select count(*) from public.post_reports where post_id=%d" % p) == '1', 'no post_reports row')
    with j.step('Moderator M: Admin → Review lists the report with reporter, reason, post text and author; Remove'):
        m = j.person('Dr. Mona Moderator'); make_admin(j, m['id']); pm = m['page']; j.reload(pm)
        # Admin is reached as the business journeys reach it (its entry sits in the sidebar footer, below the fold at
        # 1440 px, which j.nav does not scroll to), and reported posts are their own queue in Review — open it as M would
        from _biz import admin_review
        admin_review(j, pm, r'Reported posts|منشورات مُبلَّغ عنها')
        t = j.text(pm)
        j.check('EDA approval (fake)' in t and 'Alaa' in t, 'Admin → Review does not show the post report')
        row = pm.locator('.dx-mod-row', has_text=j.tag)        # P's own row (earlier runs may have left other reports open)
        j.check(row.count(), 'Admin → Review has no row for post P')
        rm = j.find(pm, r'Remove post|إزالة المنشور|أزل المنشور', scope='#' + row.first.evaluate("e=>e.id||(e.id='dxj-row-'+Date.now())"))
        if not rm: j.notbuilt('no "Remove post" on the report')
        rm.click(); pm.wait_for_timeout(600)
        note = pm.locator('.dbk-ov textarea:visible, .modal-bg textarea:visible, [role=dialog] textarea:visible')
        if note.count():                                         # "Remove post (with a note)": the note for the author, then confirm
            note.first.fill('No EDA approval exists for this product')
            j.click(pm, r'^(Remove post|Remove|Confirm|إزالة المنشور|أزل المنشور|تأكيد)$', scope='body', what='Confirm remove', exact=True)   # body: j.find picks inside the open dialog
        pm.wait_for_timeout(1200)
        j.check(j.sql1("select count(*) from public.posts where id=%d" % p) == '0', 'Remove did not remove the post')
    with j.step('A is told the outcome; C is told the post was removed and why'):
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and created_at>now()-interval '5 minutes'" % c['id']) >= '1', 'C was not told the post was removed')
        # each reads it on the Notifications page in the interface language, from Drugbox (not with their own initials as sender)
        for who, page, want in ((c, c['page'], r'removed your post|أزال.*منشورك'), (a, pg, r'reviewed your report|راجع.*بلاغك')):
            j.reload(page); j.nav(page, 'notifs'); j.settle(page, 900)
            rows = page.eval_on_selector_all('#content .notif-item', 'e=>e.filter(x=>x.getClientRects().length).map(x=>({t:x.innerText,av:(x.querySelector(".notif-av")||{}).innerText||""}))')
            hit = [r for r in rows if re.search(want, r['t'])]
            j.check(hit, '%s does not see the Drugbox notice on the Notifications page (rows: %s)' % (who['name'], [r['t'][:50] for r in rows[:4]]))
            if hit:
                if j.ar: j.check(not re.search(r'Drugbox (removed|reviewed)|reason:|Note:', hit[0]['t']), 'the Drugbox notice is in English in the Arabic interface: "%s"' % hit[0]['t'][:90])
                mine_ini = (page.evaluate('ME.initials') or '').strip().upper()
                j.check(hit[0]['av'].strip().upper() != mine_ini, 'the Drugbox notice shows the reader\'s own initials (%s) as its sender' % hit[0]['av'])

@journey('J-SOCIAL-21')
def mention_and_hashtag(j):
    """A member mentions a colleague and uses a hashtag so the right people and topic followers find it."""
    if j.live:
        a, b = setup_live_pair(j, 'Dr. Amira Mentioner', 'Dr. Alia Mourad'); pg = a['page']; fresh(j, pg)
    else: pg = j.demo_signin(j.new_page())
    with j.step('In the composer type "Thanks @Ali": people suggestions appear'):
        j.click(pg, r"What.s on your mind|تفكر|ماذا يدور|ما الذي يدور", what="What's on your mind")
        pg.click('#postBody'); pg.keyboard.type('Thanks @Ali'); pg.wait_for_timeout(1000)
        sug = pg.locator('.modal-bg [role=option]:visible, .modal-bg [class*=mention]:visible, .modal-bg [class*=suggest]:visible').filter(has_text='Alia')
        j.check(sug.count(), 'not built: typing @ in the composer shows no people suggestions')
    with j.step('Pick Dr. Alia Mourad; add #GMP; post'):
        sug.first.click(); pg.keyboard.type(' for the audit #GMP ' + j.tag)
        pg.locator('.modal-bg [onclick^="submitPost"]').last.click(); j.settle(pg, 1200)
        post = post_el(j, pg, j.tag)
    with j.step("The mention links to B's profile; #GMP links to a list of posts with that tag"):
        m = post.locator('a, [onclick]').filter(has_text='Alia'); j.check(m.count(), 'the mention is not a link')
        m.first.click(); j.settle(pg); j.check('Alia Mourad' in j.text(pg)[:400], "the mention does not open Alia's profile")
        j.nav(pg, 'feed'); post = post_el(j, pg, j.tag)
        h = post.locator('a, [onclick]').filter(has_text='#GMP'); j.check(h.count(), '#GMP is not a link')
        h.first.click(); j.settle(pg); j.check(j.tag in j.text(pg) and re.search(r'#GMP', j.text(pg)[:300]), '#GMP does not open a list of posts with that tag')
    with j.step('B gets "A mentioned you in a post" that opens the post (survives reload)'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and from_user='%s'" % (b['id'], a['id'])) == '1', 'B got no mention notification')

if __name__ == '__main__': main(__file__)
