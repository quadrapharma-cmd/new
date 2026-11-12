"""In the page (Playwright): a project that was started and left stays as a draft in the projects list (continue it, start another,
delete it); a project is deleted to the trash, brought back, or deleted for good with its name typed; the delete buttons of the home
page work; a compressed file gives the documents inside it, an archive with many documents asks which ones, and one that cannot be
opened says why. Fictional products «Dermacure» / «Cardiolol»."""
import io, json, zipfile
import httpx
import pytest
from fixtures_pdf import make_pdf, make_pdf_lines
from test_ui_e2e import server, browser          # noqa: F401  (the module's live server and Chromium)
from test_ui_intake_fixes import CPP, _upload
from test_reading_cases import PROFILE, PRODUCT, ENV
from dossier_engine import archives

H = {'X-DB': '1'}


@pytest.fixture()
def clean(server):
    """The shared workspace starts empty: no drafts, no projects, nothing in the trash."""
    for d in httpx.get(f'{server}/api/intake/drafts').json():
        httpx.delete(f"{server}/api/intake/drafts/{d['id']}?free=1", headers=H)
    for d in httpx.get(f'{server}/api/dossiers').json():
        httpx.delete(f"{server}/api/dossiers/{d['id']}", headers=H)
    for d in httpx.get(f'{server}/api/dossiers?deleted=1').json():
        httpx.delete(f"{server}/api/dossiers/{d['id']}?permanent=1", headers=H)
    return server


def _open(browser, server, hash_='#/new', wait='#intakeBtn', width=1440):
    page = browser.new_page(viewport={'width': width, 'height': 900})
    page.errors = []
    page.on('pageerror', lambda e: page.errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(server + '/' + hash_)
    page.wait_for_selector(wait)
    return page


def _drafts(server):
    return httpx.get(f'{server}/api/intake/drafts').json()


def _dossier(server, name='Dermacure'):
    return httpx.post(f'{server}/api/dossiers', json=dict(name=name, profile=PROFILE, product=PRODUCT, envelope=ENV), headers=H).json()['id']


def _wiz_files(page):
    return page.evaluate("() => (S.wiz.allFiles || []).map(f => f.name).sort()")


# ---------------- leaving the wizard
def test_leaving_the_wizard_keeps_a_draft_that_is_continued_from_the_list(clean, browser, tmp_path):
    server = clean
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    page = _open(browser, server)
    assert page.inner_text('#wizCancel') == 'Cancel'                                    # nothing to keep yet
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    assert 'draft is kept' in page.inner_text('#wizCancel')
    page.click('#wizCancel')                                                            # before: «Cancel» deleted the work
    page.wait_for_selector('#draftBox')
    assert page.evaluate('location.hash') == '#/dossiers'
    box = page.inner_text('#draftBox')
    assert 'Draft' in box and 'cpp.pdf' in box and page.locator('[data-draft]').count() == 1
    d = _drafts(server)
    assert len(d) == 1 and d[0]['files'] == 1 and not d[0]['state'].get('created')
    page.goto(server + '/#/')                                                           # the home page says it too
    page.wait_for_selector('#homeDrafts')
    page.click('#homeDrafts')                                                           # one draft: straight back into it
    page.wait_for_selector('#intakeReview', timeout=60000)
    assert 'cpp.pdf' in page.inner_text('#wizBody')
    page.click('#wizNext')
    assert page.input_value('[data-in=trade]') == 'Cardiolol 10 mg'                     # what was read came back with it
    assert page.errors == [], page.errors
    page.close()


def test_leaving_by_the_menu_keeps_what_was_just_typed(clean, browser):
    server = clean
    page = _open(browser, server)
    page.click('#wizNext')
    page.fill('[data-in=name]', 'Dermacure 2 % cream')
    page.evaluate("location.hash = '#/dossiers'")                                       # away at once, before the autosave has fired
    page.wait_for_selector('#draftBox')
    assert 'Dermacure 2 % cream' in page.inner_text('#draftBox')
    assert [x['state']['d']['name'] for x in _drafts(server)] == ['Dermacure 2 % cream']
    page.reload()                                                                       # and it is there after a reload
    page.wait_for_selector('#draftBox')
    assert 'Dermacure 2 % cream' in page.inner_text('#draftBox')
    assert page.errors == [], page.errors
    page.close()


def test_new_project_starts_a_new_one_and_the_draft_stays(clean, browser):
    server = clean
    first = httpx.post(f'{server}/api/intake/drafts', json={'state': {'step': 1, 'd': {'name': 'Dermacure first'}, 'typed': {'name': 1}}}, headers=H).json()['id']
    page = _open(browser, server, '#/dossiers', '#draftBox')
    page.click('#btnNew')
    page.wait_for_selector('#intakeBtn')                                                # a new wizard, at its first step, empty
    assert page.evaluate("() => !S.wiz.draftId && !S.wiz.d.name")
    page.click('#wizNext')
    page.fill('[data-in=name]', 'Dermacure second')
    page.click('#wizCancel')
    page.wait_for_selector('#draftBox')
    assert page.locator('[data-draft]').count() == 2
    assert sorted(x['state']['d']['name'] for x in _drafts(server)) == ['Dermacure first', 'Dermacure second']
    page.click(f'[data-draft="{first}"]')                                               # «continue» opens the one that was asked for
    page.wait_for_selector('[data-in=name]')
    assert page.input_value('[data-in=name]') == 'Dermacure first'
    assert page.errors == [], page.errors
    page.close()


def test_a_draft_is_deleted_in_two_presses_and_start_over_asks_first(clean, browser, tmp_path):
    server = clean
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    page = _open(browser, server)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    page.click('#wizRestart')                                                           # one press only asks
    assert 'Sure' in page.inner_text('#wizRestart') and len(_drafts(server)) == 1
    page.click('#wizCancel')
    page.wait_for_selector('[data-deldraft]')
    page.click('[data-deldraft]')
    assert 'Sure' in page.inner_text('[data-deldraft]') and len(_drafts(server)) == 1
    page.click('[data-deldraft]')
    page.wait_for_function("() => !document.querySelector('#draftBox')")
    assert _drafts(server) == []
    page.click('#btnNew')
    page.wait_for_selector('#intakeBtn')
    assert _wiz_files(page) == []                                                       # nothing of the deleted draft comes back
    page.click('#wizNext'); page.fill('[data-in=name]', 'Dermacure'); page.click('#wizBack')
    page.wait_for_function("() => S.wiz.draftId")
    page.click('#wizRestart'); page.click('#wizRestart')                                # the second press starts over
    page.wait_for_function("() => !S.wiz || !S.wiz.draftId")
    page.wait_for_timeout(300)
    assert _drafts(server) == []
    assert page.errors == [], page.errors
    page.close()


# ---------------- deleting a project
def _show_trash(page):
    """The trash opens by itself when the list is empty; with projects in the list it waits for a press."""
    if not page.evaluate("document.querySelector('#trashBox').open"):
        page.click('#trashBox summary')
    assert page.evaluate("document.querySelector('#trashBox').open")


def test_a_project_goes_to_the_trash_comes_back_and_is_deleted_for_good(clean, browser, tmp_path):
    server = clean
    did = _dossier(server, 'Dermacure 2 % cream')
    pdf = make_pdf(tmp_path / 'pricing.pdf', 'Pricing Certificate').read_bytes()
    httpx.post(f'{server}/api/dossiers/{did}/slots/M1-05/documents', files={'file': ('pricing.pdf', pdf, 'application/pdf')}, data={'meta': '{}'}, headers=H)
    page = _open(browser, server, '#/dossiers', f'[data-deld="{did}"]')
    page.click(f'[data-deld="{did}"]')
    page.wait_for_selector('#cfOk')
    assert 'Dermacure 2 % cream' in page.inner_text('#dBody') and 'Trash' in page.inner_text('#dBody')
    page.click('#cfNo')                                                                 # «Cancel» changes nothing
    assert [d['id'] for d in httpx.get(f'{server}/api/dossiers').json()] == [did]
    page.click(f'[data-deld="{did}"]'); page.click('#cfOk')
    page.wait_for_selector('#trashBox')
    assert httpx.get(f'{server}/api/dossiers').json() == [] and page.locator(f'[data-deld="{did}"]').count() == 0
    _show_trash(page)
    page.click(f'[data-undel="{did}"]')                                                 # back, with its document
    page.wait_for_selector(f'[data-deld="{did}"]')
    board = httpx.get(f'{server}/api/dossiers/{did}/board').json()
    assert sum(len(s['documents']) for s in board['slots']) == 1
    page.click(f'[data-deld="{did}"]'); page.click('#cfOk')
    page.wait_for_selector('#trashBox')
    _show_trash(page)
    page.click(f'[data-purge="{did}"]')
    page.wait_for_selector('#cfType')
    assert page.is_disabled('#cfOk') and '1 document' in page.inner_text('#dBody')      # for good: the name is typed first
    page.fill('#cfType', 'Dermacure')
    assert page.is_disabled('#cfOk')
    page.fill('#cfType', 'Dermacure 2 % cream')
    page.click('#cfOk')
    page.wait_for_function("() => !document.querySelector('#trashBox')")
    assert httpx.get(f'{server}/api/dossiers/{did}').status_code == 404 and httpx.get(f'{server}/api/dossiers?deleted=1').json() == []
    assert page.errors == [], page.errors
    page.close()


@pytest.mark.parametrize('width', [1440, 390])
def test_the_home_page_delete_button_works_and_the_lists_fit(clean, browser, width):
    server = clean
    did = _dossier(server)
    httpx.post(f'{server}/api/intake/drafts', json={'state': {'step': 0, 'd': {'name': 'Dermacure draft with a rather long name to wrap'}}}, headers=H)
    page = _open(browser, server, '#/', f'[data-deld="{did}"]', width)
    assert page.locator('#homeDrafts').count() == 1
    page.click(f'[data-deld="{did}"]')                                                  # before: the button was drawn on the home page and did nothing
    page.wait_for_selector('#cfOk'); page.click('#cfOk')
    page.wait_for_function(f"() => !document.querySelector('[data-deld=\"{did}\"]')")
    assert [d['id'] for d in httpx.get(f'{server}/api/dossiers?deleted=1').json()] == [did]
    page.goto(server + '/#/dossiers')
    page.wait_for_selector('#trashBox'); page.wait_for_selector('#draftBox')
    _show_trash(page)
    assert page.evaluate('document.documentElement.scrollWidth') <= width + 1          # nothing runs off a phone screen
    page.evaluate("setLang('ar')")
    page.wait_for_function("() => /مسودة/.test((document.querySelector('#draftBox') || {}).textContent || '')")
    _show_trash(page)
    assert 'مسودة' in page.inner_text('#draftBox') and 'المحذوفات' in page.inner_text('#trashBox')
    assert page.evaluate('document.documentElement.scrollWidth') <= width + 1
    assert page.errors == [], page.errors
    page.close()


# ---------------- compressed files
def _zip(path, entries):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in entries:
            z.writestr(name, data)
    return path


def test_a_zip_given_to_the_wizard_gives_the_documents_inside_it(clean, browser, tmp_path):
    server = clean
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme').read_bytes()
    z = _zip(tmp_path / 'Cardiolol documents.zip', [('Module 1/cpp.pdf', cpp), ('Module 1/ملاحظات.txt', 'Cardiolol 10 mg tablets\nApplicant: Medis S.A.'.encode()),
                                                 ('__MACOSX/Module 1/._cpp.pdf', b'x'), ('setup.exe', b'MZ' + b'\0' * 64)])
    page = _open(browser, server)
    _upload(page, '#intakeBtn', [z])
    page.wait_for_selector('#intakeReview', timeout=120000)
    assert _wiz_files(page) == ['cpp.pdf', 'ملاحظات.txt']                                 # the documents, not the archive, the system file or the program
    page.click('#wizNext')
    assert page.input_value('[data-in=trade]') == 'Cardiolol 10 mg'                     # and they were read
    assert _drafts(server)[0]['files'] == 2
    assert page.errors == [], page.errors
    page.close()


def test_an_archive_with_many_documents_asks_which_ones(clean, browser, tmp_path):
    server = clean
    z = _zip(tmp_path / 'everything.zip', [(f'batch records/record {i:02d}.txt', f'Batch record {i}\nProduct: Dermacure'.encode()) for i in range(45)])
    page = _open(browser, server)
    _upload(page, '#intakeBtn', [z])
    page.wait_for_selector('#psGo')
    assert page.is_disabled('#psGo') and '0 of 45' in page.inner_text('#psCount')        # nothing is taken without a choice
    page.check('[data-ps="3"]'); page.check('[data-ps="7"]')
    assert '2 of 45' in page.inner_text('#psCount')
    page.click('#psGo')
    page.wait_for_function("() => S.wiz.allFiles && S.wiz.allFiles.length === 2")
    assert _wiz_files(page) == ['record 03.txt', 'record 07.txt']
    assert page.errors == [], page.errors
    page.close()


def test_an_archive_that_cannot_be_opened_says_why(clean, browser, tmp_path, monkeypatch):
    server = clean
    monkeypatch.setattr(archives, 'tools', lambda: [])                                  # as in the browser edition: no unpacker for 7z
    z7 = tmp_path / 'backup.7z'
    z7.write_bytes(b"7z\xbc\xaf'\x1c" + b'\0' * 200)
    page = _open(browser, server)
    _upload(page, '#intakeBtn', [z7])
    page.wait_for_function("() => /ZIP/.test(document.querySelector('#toast').textContent)")
    said = page.inner_text('#toast')
    assert 'backup.7z' in said and '7z archive' in said                                 # why, and what to do about it
    page.wait_for_timeout(4500)
    assert page.is_visible('#toast') and '7z' in page.inner_text('#toast')              # still there to be read; not replaced by «choose documents»
    assert _wiz_files(page) == []
    assert page.errors == [], page.errors
    page.close()


# ---------------- RAR: opened inside the page by the program's own reader where the machine has no unpacker
RAR = __import__('pathlib').Path(__file__).parent / 'data' / 'archives' / 'rar'
RAR_DOCS = ['licence.pdf', 'notes.txt', 'pricing certificate.txt', 'تقرير الثبات.txt']       # scan.bin is not a document: left out


def test_a_rar_is_opened_inside_the_page(clean, browser, monkeypatch):
    server = clean
    monkeypatch.setattr(archives, 'tools', lambda: [])
    page = _open(browser, server)
    _upload(page, '#intakeBtn', [RAR / 'dermacure.rar'])
    page.wait_for_function("() => S.wiz.allFiles && S.wiz.allFiles.length === 4 && Object.values(S.wiz.docs).every(d => d.status !== 'reading')", timeout=120000)
    assert _wiz_files(page) == RAR_DOCS
    assert page.evaluate("() => S.wiz.kinds['licence.pdf']") == 'licence'               # and what is inside them was read
    assert _drafts(server)[0]['files'] == 4
    assert page.errors == [], page.errors
    page.close()


def test_a_rar_split_in_parts_and_a_part_given_alone(clean, browser, monkeypatch):
    server = clean
    monkeypatch.setattr(archives, 'tools', lambda: [])
    parts = sorted(RAR.glob('dermacure-parts.part*.rar'))
    page = _open(browser, server)
    _upload(page, '#intakeBtn', [parts[2]])                                             # the third part alone
    page.wait_for_function("() => /first part/.test(document.querySelector('#toast').textContent)")
    assert _wiz_files(page) == []
    _upload(page, '#intakeBtn', parts)                                                  # the four parts together: one archive
    page.wait_for_function("() => S.wiz.allFiles && S.wiz.allFiles.length === 4", timeout=120000)
    assert _wiz_files(page) == RAR_DOCS
    assert page.errors == [], page.errors
    page.close()


def test_a_rar_under_a_password_says_so(clean, browser, monkeypatch):
    server = clean
    monkeypatch.setattr(archives, 'tools', lambda: [])
    page = _open(browser, server)
    for name in ('dermacure-password.rar', 'dermacure-locked-names.rar'):               # the files locked; the names locked too
        _upload(page, '#intakeBtn', [RAR / name])
        page.wait_for_function("(n) => document.querySelector('#toast').textContent.includes(n) && /password/.test(document.querySelector('#toast').textContent)", arg=name)
    assert _wiz_files(page) == []
    assert page.errors == [], page.errors
    page.close()


@pytest.mark.skipif(not archives.tools(), reason='no RAR/7z unpacker on this machine')
def test_a_7z_given_to_the_wizard(clean, browser):
    import pathlib
    server = clean
    page = _open(browser, server)
    _upload(page, '#intakeBtn', [pathlib.Path(__file__).parent / 'data' / 'archives' / 'dermacure.7z'])
    page.wait_for_function("() => S.wiz.allFiles && S.wiz.allFiles.length === 2", timeout=60000)
    assert _wiz_files(page) == ['pricing certificate.txt', 'ثبات.txt']
    assert page.errors == [], page.errors
    page.close()


def test_a_reading_that_ends_after_leaving_goes_to_its_draft_and_not_over_the_page(clean, browser, tmp_path):
    """Before: the reading ended with the wizard redrawn over whatever page the person had gone to."""
    server = clean
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    page = _open(browser, server)

    def slow(route):                                                                    # the reading takes its time
        page.wait_for_timeout(1500)
        route.continue_()
    page.route('**/api/extract**', slow)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_function("() => S.wiz && S.wiz.draftId")
    page.evaluate("location.hash = '#/dossiers'")                                       # gone before the reading ends
    page.wait_for_selector('#draftBox')
    page.click('#btnNew')                                                               # and a new project is started meanwhile
    page.wait_for_selector('#intakeBtn')
    end, state = __import__('time').time() + 60, {}
    while __import__('time').time() < end and 'cpp.pdf' not in (state.get('texts') or {}):
        state = _drafts(server)[0]['state'] if _drafts(server) else {}
        page.wait_for_timeout(200)
    assert 'cpp.pdf' in state['texts'] and state['docs']['cpp.pdf']['status'] == 'ok'   # the reading reached its own draft
    page.wait_for_timeout(800)
    assert _wiz_files(page) == [] and page.evaluate("() => !S.wiz.draftId && !Object.keys(S.wiz.texts || {}).length")     # the new wizard got nothing of it
    assert 'cpp.pdf' not in page.inner_text('#wizBody')
    page.evaluate("location.hash = '#/dossiers'")
    page.wait_for_selector('#draftBox')
    assert page.locator('[data-draft]').count() == 1 and 'cpp.pdf' in page.inner_text('#draftBox')
    assert page.errors == [], page.errors
    page.close()


def test_the_wizard_is_not_painted_over_the_page_the_person_went_to(clean, browser, tmp_path):
    server = clean
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    page = _open(browser, server)

    def slow(route):
        page.wait_for_timeout(1500)
        route.continue_()
    page.route('**/api/extract**', slow)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_function("() => S.wiz && S.wiz.draftId")
    page.evaluate("location.hash = '#/dossiers'")
    page.wait_for_selector('#draftBox')
    end, state = __import__('time').time() + 60, {}
    while __import__('time').time() < end and 'cpp.pdf' not in (state.get('texts') or {}):
        state = _drafts(server)[0]['state'] if _drafts(server) else {}
        page.wait_for_timeout(200)
    assert 'cpp.pdf' in state['texts']                                                  # the reading ended, in the background
    page.wait_for_timeout(800)
    assert page.locator('#intakeBtn').count() == 0 and page.locator('#draftBox').count() == 1 and page.evaluate('location.hash') == '#/dossiers'
    page.click('[data-draft]')                                                          # continued: nothing is read twice
    page.wait_for_selector('#intakeReview', timeout=60000)
    assert 'cpp.pdf' in page.inner_text('#wizBody')
    assert page.errors == [], page.errors
    page.close()
