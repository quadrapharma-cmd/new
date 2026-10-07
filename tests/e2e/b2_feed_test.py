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
    total = int(sql("select count(*) from public.posts")); want = min(40, total)
    T(f'scrolling loads the next page (expected {want} of {total}), no duplicates', n2 == want and len(set(ids)) == n2, n2)
    pg.evaluate("showPostModal()"); pg.wait_for_timeout(300); pg.fill('#postBody', f'My first real post {stamp}'); pg.select_option('#postCat', 'market'); pg.evaluate("submitPost()"); pg.wait_for_timeout(2500)
    T('new post saved in the database with its category', sql(f"select category from public.posts where body='My first real post {stamp}'") == 'market')
    top = pg.evaluate("POSTS[0].id"); T('new post shows first, with its real database id', isinstance(top, int) and 'My first real post' in pg.inner_text('#content .post'), top)
    target = pg.evaluate("POSTS[1].id"); pg.evaluate(f"likePost({target})"); pg.wait_for_timeout(1200)
    T('like saved (reaction row + counter updated by the database)', sql(f"select count(*) from public.reactions where post_id={target}") == '1' and sql(f"select like_count from public.posts where id={target}") == '1')
    pg.evaluate(f"toggleComments({target})"); pg.wait_for_timeout(1200); pg.fill(f'#ci-{target}', 'Very useful, thank you'); pg.evaluate(f"submitComment({target})"); pg.wait_for_timeout(1200)
    T('comment saved (and counted by the database)', sql(f"select count(*) from public.comments where post_id={target} and body='Very useful, thank you'") == '1' and sql(f"select comment_count from public.posts where id={target}") == '1')
    pg.evaluate(f"savePost({target})"); pg.wait_for_timeout(1000)
    T('save stored', sql(f"select count(*) from public.saved_posts where post_id={target}") == '1')
    pg.reload(wait_until='load'); pg.wait_for_timeout(500); pg.evaluate('endSplash()'); pg.wait_for_timeout(3500)
    st = pg.evaluate(f"(()=>{{var p=POSTS.find(x=>x.id=={target});return p?{{liked:p.liked,saved:p.saved,likes:p.likeCount}}:null}})()")
    T('after reload: my like and save are remembered', st and st['liked'] and st['saved'] and st['likes'] == 1, st)
    pg.evaluate(f"toggleComments({target})"); pg.wait_for_timeout(1500)
    txt = pg.inner_text(f'#post-{target}')
    T('after reload: the comment loads from the database, counted once', 'Very useful, thank you' in txt and pg.evaluate(f"(()=>{{var p=POSTS.find(x=>x.id=={target});return (p.commentCount||0)+((COMMENTS[{target}]||[]).length)}})()") == 1, txt[-200:])
    pg.evaluate(f"likePost({target})"); pg.wait_for_timeout(1000)
    T('un-like removes the reaction', sql(f"select count(*) from public.reactions where post_id={target}") == '0')
    mine = pg.evaluate(f"POSTS.find(p=>p.body==='My first real post {stamp}').id"); pg.evaluate(f"deletePost({mine})"); pg.wait_for_timeout(1500)
    T('during the Undo window the post is still in the database', sql(f"select count(*) from public.posts where id={mine}") == '1')
    T('after the Undo window, deleting my post removes it from the database', wait_for(lambda: sql(f"select count(*) from public.posts where id={mine}") == '0', 15))
    r = pg.evaluate(f"dxLive.sb.from('posts').delete().eq('id',{target}).select().then(r=>(r.data||[]).length)")
    T("cannot delete another member's post (row-level security)", r == 0 and sql(f"select count(*) from public.posts where id={target}") == '1')
    r = pg.evaluate(f"dxLive.sb.from('reactions').insert({{post_id:{target},user_id:'{other}',kind:'like'}})" + ERR)
    T('cannot react on behalf of someone else', r and refused(r) and sql(f"select count(*) from public.reactions where post_id={target} and user_id='{other}'") == '0', r)
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
