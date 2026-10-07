"""Live: post from your own profile — saved to the database, you stay on the profile, the post shows at the top; one-word names greet correctly."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); pg = b.new_page(viewport={'width': 1440, 'height': 900}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)[:150]))
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', 'Nour'); pg.fill('#suEmail', f'nour{st}@x.test'); pg.fill('#suPw', 'Strong-pass-2026'); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    T('one-word name: Home composer greets "Nour", not "undefined"', 'Nour' in pg.evaluate("document.querySelector('.comp-btn').textContent") and 'undefined' not in pg.evaluate("document.querySelector('.comp-btn').textContent"))
    pg.evaluate("goto('profile')"); pg.wait_for_timeout(1500)
    T('a new member sees the composer and a first-post prompt on their profile', pg.evaluate("!!document.querySelector('#profileTabContent .dx-pp-comp')") and pg.evaluate("!!document.querySelector('#profileTabContent .dx-pp-empty')"))
    pg.evaluate("document.querySelector('#profileTabContent .comp-btn').click()"); pg.wait_for_timeout(400)
    pg.fill('#postBody', f'My first post, from my profile {st}'); pg.evaluate("submitPost()"); pg.wait_for_timeout(2500)
    T('the post is saved in the database', sql(f"select count(*) from public.posts where body='My first post, from my profile {st}'") == '1')
    T('you stay on your profile (not sent to Home)', pg.evaluate("document.body.getAttribute('data-page')") == 'profile')
    T('the post shows at the top of your profile, with its database id', f'My first post, from my profile {st}' in pg.evaluate("document.querySelector('#profileTabContent .post').innerText") and pg.evaluate("typeof POSTS[0].id==='number'&&POSTS[0].id<1e12"))
    T('no errors in the page', not errs, errs)
    b.close()
done()
