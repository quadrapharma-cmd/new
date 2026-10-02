"""Follow / unfollow a company with the page's own button: stored in company_followers, counted by the database, private per person."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
U = os.environ.get('APP_URL', 'http://localhost:54321/'); DB = os.environ.get('DB_NAME', 'drugbox_live'); R = []
def T(n, ok, d=''): R.append(ok); print(('✅ ' if ok else '❌ ') + n + ('' if ok else '  → ' + str(d)[:200]))
def sql(q): return subprocess.run(['psql', '-h', '/tmp', '-p', '5433', '-U', 'postgres', '-d', DB, '-tA', '-c', q], capture_output=True, text=True).stdout.strip()
st = int(time.time())
own = sql("select id from public.profiles order by created_at limit 1")
cid = sql(f"insert into public.companies (owner_id, name, slug, type, status, sectors) values ('{own}','Followed Pharma {st}','followed-pharma-{st}','Manufacturer','verified','{{Manufacturer}}') returning id").split('\n')[0]
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); pg = b.new_page(viewport={'width': 1440, 'height': 900}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', 'Dr. Follower'); pg.fill('#suEmail', f'fol{st}@x.test'); pg.fill('#suPw', 'Strong-pass-2026'); pg.click('#signupPage button.f-btn'); pg.wait_for_timeout(4500)
    me = pg.evaluate("dxLive.uuidOf(ME.id)")
    pg.evaluate(f"dxHub.page('followed-pharma-{st}','overview')"); pg.wait_for_timeout(2500)
    btn = "[...document.querySelectorAll('#dxDir button, #dxDir .dr-btn')].find(b=>/Follow/.test(b.textContent))"
    pg.evaluate(f"({btn}).click()"); pg.wait_for_timeout(1800)
    T('Follow is stored', sql(f"select count(*) from public.company_followers where company_id={cid} and user_id='{me}'") == '1')
    fc = sql(f"select follower_count from public.companies where id={cid}"); rows = sql(f"select count(*) from public.company_followers where company_id={cid}")
    T('the database counts the follower', fc == '1', (fc, rows, cid))
    pg.evaluate(f"({btn}).click()"); pg.wait_for_timeout(1800)
    T('Unfollow removes it', sql(f"select count(*) from public.company_followers where company_id={cid} and user_id='{me}'") == '0' and sql(f"select follower_count from public.companies where id={cid}") == '0')
    r = pg.evaluate(f"dxLive.sb.from('company_followers').insert({{company_id:{cid},user_id:'{own}'}}).then(r=>!!r.error)")
    T('cannot make someone else follow a company', r)
    T('no errors in the page', not errs, errs)
    print(sum(R), '/', len(R)); b.close()
