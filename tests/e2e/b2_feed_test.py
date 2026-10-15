"""B2 end-to-end: feed paging, posting, reactions, comments, saved, delete — against the local Supabase stack."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py
DB = os.environ.get('DB_NAME', 'drugbox_live')

stamp = ST; EMAIL = f'feed{stamp}@quadra.test'
# another member with 25 posts, one minute apart
other = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('author{stamp}@x.test', crypt('x-pass-123', gen_salt('bf')), '{{\"name\":\"Dr. Alia Author\"}}') returning id").split('\n')[0]
sql(f"insert into public.posts (user_id, body, category, created_at) select '{other}', 'Seed post #' || g || ' — EDA stability update', 'regulatory', now() - (g || ' minutes')::interval from generate_series(1,25) g")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); ctx = b.new_context(viewport={'width': 1440, 'height': 900}); pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(500); pg.evaluate('endSplash()'); pg.wait_for_timeout(800)
    pg.evaluate("showSignup()"); pg.fill('#suName', 'Dr. Feed Tester'); pg.fill('#suEmail', EMAIL); pg.fill('#suPw', 'Strong-pass-2026'); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    n1 = pg.evaluate("document.querySelectorAll('#content .post').length")
    T('first page: 20 real posts from the database (not demo posts)', n1 == 20 and pg.evaluate("POSTS.every(p=>typeof p.id==='number'&&p.uid>1000&&String(dxLive.uuidOf(p.uid)).length===36)"), n1)
    T('author name comes from the database', 'Dr. Alia Author' in pg.inner_text('#content'))
    pg.evaluate("document.querySelectorAll('#content .post')[19].scrollIntoView()"); pg.wait_for_timeout(2500)
    n2 = pg.evaluate("document.querySelectorAll('#content .post').length"); ids = pg.evaluate("[...document.querySelectorAll('#content .post')].map(e=>e.id)")
    total = int(sql("select count(*) from public.posts where group_id is null")); want = min(40, total)   # group posts (0027) live in their group, not in the feed
    T(f'scrolling loads the next page (expected {want} of {total}), no duplicates', n2 == want and len(set(ids)) == n2, n2)
    pg.evaluate("showPostModal()"); pg.wait_for_timeout(300); pg.fill('#postBody', f'My first real post {stamp}'); pg.select_option('#postCat', 'market'); pg.evaluate("submitPost()"); pg.wait_for_timeout(2500)
    T('new post saved in the database with its category', sql(f"select category from public.posts where body='My first real post {stamp}'") == 'market')
    top = pg.evaluate("POSTS[0].id"); T('new post shows first, with its real database id', isinstance(top, int) and 'My first real post' in pg.inner_text('#content .post'), top)
    # reactions through the real controls: the Like button ([data-lp]) and the reaction panel ([data-rk]) — S-02
    target = pg.evaluate("POSTS[1].id"); pg.click(f'#post-{target} [data-lp]'); pg.wait_for_timeout(1200)
    T('like saved (reaction row + counter updated by the database)', sql(f"select count(*) from public.reactions where post_id={target}") == '1' and sql(f"select like_count from public.posts where id={target}") == '1')
    pg.hover(f'#like-{target}'); pg.wait_for_timeout(500); pg.click(f'#like-{target} [data-rk="insightful"]'); pg.wait_for_timeout(1200)
    T('changing the reaction stores its kind (one row, counted once)', sql(f"select string_agg(kind, ',') from public.reactions where post_id={target}") == 'insightful' and sql(f"select like_count from public.posts where id={target}") == '1')
    pg.evaluate(f"toggleComments({target})"); pg.wait_for_timeout(1200); pg.fill(f'#ci-{target}', 'Very useful, thank you'); pg.evaluate(f"submitComment({target})"); pg.wait_for_timeout(1200)
    T('comment saved (and counted by the database)', sql(f"select count(*) from public.comments where post_id={target} and body='Very useful, thank you'") == '1' and sql(f"select comment_count from public.posts where id={target}") == '1')
    pg.click(f'#post-{target} .post-acts > .pact:nth-child(4)'); pg.wait_for_timeout(1000)   # the card's own 🔖 Save
    T('save stored', sql(f"select count(*) from public.saved_posts where post_id={target}") == '1')
    pg.reload(wait_until='load'); pg.wait_for_timeout(500); pg.evaluate('endSplash()'); pg.wait_for_timeout(3500)
    st = pg.evaluate(f"(()=>{{var p=POSTS.find(x=>x.id=={target});return p?{{liked:p.liked,kind:p.myKind,saved:p.saved,likes:p.likeCount}}:null}})()")
    T('after reload: my reaction (its kind) and save are remembered', st and st['liked'] and st['kind'] == 'insightful' and st['saved'] and st['likes'] == 1, st)
    pg.evaluate(f"toggleComments({target})"); pg.wait_for_timeout(1500)
    txt = pg.inner_text(f'#post-{target}')
    T('after reload: the comment loads from the database, counted once', 'Very useful, thank you' in txt and pg.evaluate(f"(()=>{{var p=POSTS.find(x=>x.id=={target});return (p.commentCount||0)+((COMMENTS[{target}]||[]).length)}})()") == 1, txt[-200:])
    pg.click(f'#post-{target} [data-lp]'); pg.wait_for_timeout(1000)
    T('un-like removes the reaction', sql(f"select count(*) from public.reactions where post_id={target}") == '0')
    mine = pg.evaluate(f"POSTS.find(p=>p.body==='My first real post {stamp}').id"); pg.evaluate(f"deletePost({mine})"); pg.wait_for_timeout(1500)
    T('during the Undo window the post is still in the database', sql(f"select count(*) from public.posts where id={mine}") == '1')
    T('after the Undo window, deleting my post removes it from the database', wait_for(lambda: sql(f"select count(*) from public.posts where id={mine}") == '0', 15))
    r = pg.evaluate(f"dxLive.sb.from('posts').delete().eq('id',{target}).select().then(r=>(r.data||[]).length)")
    T("cannot delete another member's post (row-level security)", r == 0 and sql(f"select count(*) from public.posts where id={target}") == '1')
    r = pg.evaluate(f"dxLive.sb.from('reactions').insert({{post_id:{target},user_id:'{other}',kind:'like'}})" + ERR)
    T('cannot react on behalf of someone else', r and refused(r) and sql(f"select count(*) from public.reactions where post_id={target} and user_id='{other}'") == '0', r)
    # 0028: reaction kinds are the interface's six; reports on Home posts are filed as yourself, once, and decided only by Drugbox
    r = pg.evaluate(f"dxLive.sb.from('reactions').upsert({{post_id:{target},user_id:dxLive.uuidOf(ME.id),kind:'angry'}},{{onConflict:'post_id,user_id'}})" + ERR)
    T('a reaction kind the interface does not offer is refused', r and r['code'] == '23514' and sql(f"select count(*) from public.reactions where post_id={target} and kind='angry'") == '0', r)
    third = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('third{stamp}@x.test', crypt('x-pass-123', gen_salt('bf')), '{{\"name\":\"Dr. Third Reader\"}}') returning id").split('\n')[0]
    sql(f"insert into public.post_reports (post_id, reporter, reason) values ({target}, '{third}', 'spam')")   # someone else's report on the same post
    # the card's own ⋯ → 🚩 Report item (clicked in place: the live feed may repaint a card while its menu is open)
    pg.evaluate(f"document.querySelector('#post-{target} .ctx-item[onclick*=\\'Reported\\']').click()"); pg.wait_for_timeout(800)
    pg.locator('.dbk-ov input[value=misleading]').check(); pg.fill('#dxRepN', 'Claims an approval it does not have'); pg.locator('.dbk-ov button', has_text='Report').last.click(); pg.wait_for_timeout(1200)
    T('Report on a post files a post_reports row (reason, note, author and text filled by the database)', sql(f"select reason||'|'||note||'|'||(post_author='{other}')::text||'|'||(post_excerpt<>'')::text from public.post_reports where post_id={target} and reporter=(select id from public.profiles where name='Dr. Feed Tester' order by created_at desc limit 1)") == 'misleading|Claims an approval it does not have|true|true')
    n = pg.evaluate(f"dxLive.sb.from('post_reports').select('id').eq('post_id',{target}).then(r=>(r.data||[]).length)")
    T("a member reads only their own reports (not who else reported)", n == 1, n)
    r = pg.evaluate(f"dxLive.sb.from('post_reports').insert({{post_id:{target},reporter:dxLive.uuidOf(ME.id),reason:'spam'}})" + ERR)
    T('the same member cannot report a post twice', r and r['code'] == '23505', r)
    r = pg.evaluate(f"dxLive.sb.from('post_reports').update({{status:'dismissed'}}).eq('post_id',{target}).select().then(r=>r.error?{{code:r.error.code,message:r.error.message}}:(r.data||[]).length)")
    T('a member cannot close a report', (r == 0 or (isinstance(r, dict) and refused(r))) and sql(f"select count(*) from public.post_reports where post_id={target} and status='open'") == '2', r)
    rid = sql(f"select id from public.post_reports where post_id={target} order by id limit 1")
    r = pg.evaluate(f"dxLive.sb.rpc('post_report_decide',{{p_report:{rid},p_remove:true}})" + ERR)
    T('only Drugbox moderators can decide a report (the post stays)', r and refused(r) and sql(f"select count(*) from public.posts where id={target}") == '1', r)
    # F-09: server-kept columns of a post (time, pin, counters) are not the browser's to choose
    # (FAILS before migration 0020_security_core.sql — a post dated 2099 stayed pinned on top of everyone's feed)
    me_uuid = pg.evaluate("dxLive.uuidOf(ME.id)")
    r = pg.evaluate(f"dxLive.sb.from('posts').insert({{user_id:'{me_uuid}',body:'Forged time {stamp}',category:'market',created_at:'2099-01-01T00:00:00Z',pinned:true,like_count:5000}})" + ERR)
    T('a new post cannot choose its own date, pin or like count', refused(r) and sql(f"select count(*) from public.posts where body='Forged time {stamp}' and (created_at > now() + interval '1 minute' or coalesce(pinned,false) or like_count > 0)") == '0', (r, sql(f"select created_at, pinned, like_count from public.posts where body='Forged time {stamp}'")))
    r = pg.evaluate(f"dxLive.sb.from('posts').update({{created_at:'2099-01-01T00:00:00Z',pinned:true,view_count:99999}}).eq('id',{target})" + ERR)
    T("cannot re-date, pin or inflate someone else's post", refused(r) and sql(f"select created_at < now() + interval '1 minute' and not coalesce(pinned,false) and coalesce(view_count,0) < 99999 from public.posts where id={target}") == 't', r)
    T('no errors in the page', not errs, errs)
    b.close()
done()
