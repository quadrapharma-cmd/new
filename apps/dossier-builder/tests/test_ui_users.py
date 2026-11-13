"""The Users screen in the browser (Playwright): the owner turns sign-in on and becomes the first administrator, adds a user,
changes a role, resets a password; the user signs in on another browser as a viewer (note, dimmed writes, own password only);
the administrator deletes the user and turns sign-in off, then on again with the administrator's password."""
import os, socket, threading, time
import pytest

pw = pytest.importorskip('playwright.sync_api')
OUT = '/tmp/claude-0/-home-user-new/e6d1aa05-9cf9-5988-8d70-5db2feac2515/scratchpad/arabic'
ADMIN_PW, SARA_PW, SARA_PW2 = 'first admin password', 'editor password 1', 'reset by the admin'


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine.app.api import create_app
    for k in ('DB_MODE', 'DB_AUTH', 'DB_ADMIN_USER', 'DB_ADMIN_PASSWORD'):
        os.environ.pop(k, None)
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(create_app(tmp_path_factory.mktemp('ws')), host='127.0.0.1', port=port, log_level='error'))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True


def new_page(b, errors):
    ctx = b.new_context(viewport={'width': 1440, 'height': 960}, device_scale_factor=2)
    page = ctx.new_page()
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','ar')")
    return page


def users_json(page):
    return page.evaluate("fetch('/api/users').then(r=>r.json())")


def test_users_screen(server):
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        admin = new_page(b, errors)
        admin.goto(server + '/#/users')
        admin.wait_for_selector('#enUser')                                                   # off: the first-administrator form
        assert admin.locator('#nav a[data-r="users"]').count() == 1                          # the entry shows because it can be turned on
        assert admin.is_hidden('#who') and admin.get_attribute('body', 'data-role') == 'local'
        admin.fill('#enUser', 'haytham'); admin.fill('#enPw', ADMIN_PW); admin.fill('#enPw2', ADMIN_PW + 'x'); admin.click('#enGo')
        admin.wait_for_selector('#toast:not([hidden])')
        assert 'مش زي بعض' in admin.inner_text('#toast')                                     # the two passwords differ: caught in the page
        admin.fill('#enPw2', ADMIN_PW); admin.click('#enGo')
        admin.wait_for_selector('#usersTable')                                               # on, and signed in as administrator
        assert 'haytham' in admin.inner_text('#who') and 'مدير' in admin.inner_text('#who')
        assert admin.get_attribute('body', 'data-role') == 'admin' and admin.is_visible('#pwBtn') and admin.is_visible('#logout')
        assert admin.locator('tr[data-user="haytham"] .tag').inner_text() == 'إنت'
        assert admin.is_disabled('[data-role-of="haytham"]')                                 # not your own role
        assert admin.locator('[data-del="haytham"]').count() == 0                            # nor your own account

        # add sara (editor), make her a viewer, set her password
        admin.fill('#nuUser', 'sara'); admin.fill('#nuPw', SARA_PW); admin.select_option('#nuRole', 'editor'); admin.click('#nuAdd')
        admin.wait_for_selector('tr[data-user="sara"]')
        assert admin.inner_text('tr[data-user="sara"]').count('لسه') == 1                     # never signed in
        admin.select_option('[data-role-of="sara"]', 'viewer')
        admin.wait_for_function("() => document.querySelector('#toast').textContent.includes('الدور اتحفظ')")
        assert {u['username']: u['role'] for u in users_json(admin)} == {'haytham': 'admin', 'sara': 'viewer'}
        admin.click('[data-reset="sara"]'); admin.wait_for_selector('#rpNew')
        admin.fill('#rpNew', SARA_PW2); admin.fill('#rpNew2', SARA_PW2); admin.click('#rpGo')
        admin.wait_for_selector('#rpNew', state='hidden', timeout=60000)                                    # the drawer closed
        admin.locator('#view').screenshot(path=f'{OUT}/users_ar.png')

        # sara on another browser: the login page, then view-only
        sara = new_page(b, errors)
        sara.goto(server + '/#/dossiers')
        sara.wait_for_selector('form#f')                                                     # redirected to sign in
        sara.fill('input[name=username]', 'sara'); sara.fill('input[name=password]', SARA_PW); sara.click('form#f button')
        sara.wait_for_selector('#e:not(:empty)')                                             # the old password is gone
        sara.fill('input[name=password]', SARA_PW2); sara.click('form#f button')
        sara.wait_for_selector('#roleNote:not([hidden])')
        assert sara.get_attribute('body', 'data-role') == 'viewer' and 'مشاهدة بس' in sara.inner_text('#roleNote')
        assert sara.locator('#nav a[data-r="users"]').count() == 0                           # no Users entry for a viewer
        assert 'sara' in sara.inner_text('#who') and 'مشاهد' in sara.inner_text('#who')
        sara.goto(server + '/#/users'); sara.wait_for_selector('#mpOld')                     # own password only
        assert sara.locator('#usersTable').count() == 0 and sara.locator('#enUser').count() == 0
        sara.click('#pwBtn'); sara.wait_for_selector('#pwOld'); sara.click('#dClose')       # the header's change-password drawer
        r = sara.evaluate("fetch('/api/dossiers',{method:'POST',headers:{'X-DB':'1','content-type':'application/json'},body:'{}'}).then(r=>r.status)")
        assert r == 403                                                                      # a viewer's write is refused by the server
        admin.reload(); admin.wait_for_selector('#usersTable')
        assert 'لسه' not in admin.inner_text('tr[data-user="sara"]')                        # last sign-in recorded

        # delete sara, turn sign-in off, then on again
        admin.click('[data-del="sara"]'); admin.wait_for_selector('#delGo'); admin.click('#delGo')
        admin.wait_for_selector('tr[data-user="sara"]', state='detached')
        sara.reload(); sara.wait_for_selector('form#f')                                      # her session died with the account
        admin.click('#authOff'); admin.wait_for_selector('#offGo'); admin.click('#offGo')
        admin.wait_for_selector('#enUser')
        assert admin.is_hidden('#who') and admin.get_attribute('body', 'data-role') == 'local'
        assert 'الحسابات محفوظة' in admin.inner_text('#view') and admin.locator('#enPw2').count() == 0   # an existing administrator signs in
        sara.goto(server + '/#/dossiers'); sara.wait_for_selector('#btnNew')                 # open again for everyone at the computer
        admin.fill('#enUser', 'haytham'); admin.fill('#enPw', 'wrong wrong wrong'); admin.click('#enGo')
        admin.wait_for_function("() => document.querySelector('#toast').textContent.includes('مدير موجود')")
        admin.fill('#enPw', ADMIN_PW); admin.click('#enGo')
        admin.wait_for_selector('#usersTable')
        assert [u['username'] for u in users_json(admin)] == ['haytham']
        assert not errors, errors
        b.close()
