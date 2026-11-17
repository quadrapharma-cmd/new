"""eBOX stage 4 in the browser: station 8 «التحقق» builds the package in the formats chosen there and validates it the way the
authority does before anything is downloaded (each rule with its provenance, official or a draft, and the documents it names;
the assessor's review as the second door); station 9 «التصدير» downloads what was validated, as it was — not a build the dossier no
longer matches, and a build that did not pass only when the person says so; «ما بعد التقديم»: the sequences and their submission,
the authority's letters of the dossier with their questions, the answers and the reply letter, a response sequence.
Made-up data only."""
import io, json, shutil, socket, threading, time, zipfile
import pytest
from fixtures_pdf import make_pdf, make_pdf_lines

pw = pytest.importorskip('playwright.sync_api')
httpx = pytest.importorskip('httpx')
SOFFICE = pytest.mark.skipif(not shutil.which('soffice'), reason='LibreOffice missing (tracking table)')
PROFILE = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Exampletine', manufacturer='Example API Co.', option='CEP')])
PRODUCT = dict(name='Examplol 500 mg FCT', dosageform='film-coated tablet', manufacturer='Example Pharm Co.', indication='made-up indication')
ENV = dict(tracking='P-MAA-0001', applicant='Example Pharm Co.', invented_name='Examplol', inn=['exampletine'])


WS = {}


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine.app.api import create_app
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    WS['root'] = tmp_path_factory.mktemp('ws')
    srv = uvicorn.Server(uvicorn.Config(create_app(WS['root'], auth_enabled=False), host='127.0.0.1', port=port, log_level='error'))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True


def dossier(server):
    r = httpx.post(f'{server}/api/dossiers', json=dict(name='Examplol (made up)', profile=PROFILE, product=PRODUCT, envelope=ENV))
    assert r.status_code == 201, r.text
    return r.json()['id']


def up(server, did, slot, data, meta=None, name='d.pdf', replaces=None):
    r = httpx.post(f'{server}/api/dossiers/{did}/slots/{slot}/documents', files={'file': (name, data, 'application/pdf')},
                   data={'meta': json.dumps(meta or {}), **({'replaces': replaces} if replaces else {})}, timeout=60)
    assert r.status_code == 201, r.text
    return r.json()


def complete(server, tmp_path):
    did = dossier(server)
    pdf = make_pdf(tmp_path / 'd.pdf', 'made-up document').read_bytes()
    for s in httpx.get(f'{server}/api/dossiers/{did}/board').json()['slots']:
        if s['level'] in ('R', 'O') and s['status'] == 'not_started':
            meta = {'pi_type': 'spc', 'lang': 'en'} if s['req_id'] == 'M1-09' else ({'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'} if s['module'] == 5 else {})
            up(server, did, s['slot_id'], pdf, meta)
    assert httpx.get(f'{server}/api/dossiers/{did}/gate').json()['ok']
    return did


def page_of(b, lang='ar', width=1280):
    page = b.new_context(viewport={'width': width, 'height': 900}, accept_downloads=True).new_page()
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script(f"localStorage.setItem('db.lang','{lang}')")
    return page


def path_state(page, n):
    return page.get_attribute(f'#pathbar a[data-st="{n}"]', 'class')


@SOFFICE
def test_station_8_builds_and_validates_and_station_9_downloads_what_was_validated(server, tmp_path):
    did = complete(server, tmp_path)
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/checks')
        page.wait_for_selector('#valSign[data-state="v8SignTodo"]')
        assert page.locator('#view a[download]').count() == 0                     # nothing is downloaded at the validation
        assert page.locator('#valReview #valRevNone').count() == 1                  # the second door: the assessor's review (none yet)
        assert page.locator('#valDocs').count() == 1 and not page.evaluate("document.getElementById('valDocs').open")   # in a fold: nothing there stops the build
        assert 'مستندات عليها ملاحظات:' in page.inner_text('#valDocs summary')
        page.check('#ack')
        page.click('#go')
        page.wait_for_selector('#valSign[data-state="v8SignOk"]', timeout=240000)
        assert page.get_attribute('#valSub', 'data-state') == 'ok' and 'done' in path_state(page, 8)
        reps = page.eval_on_selector_all('#valSub [data-rep]', 'xs => xs.map(x => x.dataset.rep)')
        assert reps == ['eCTD 3.2.2', 'eCTD 4.0'], reps
        b32 = httpx.get(f'{server}/api/dossiers/{did}/builds').json()['submission']['rules']['eCTD 3.2.2']
        assert page.locator('[data-rep="eCTD 3.2.2"] [data-orule]').count() == len(b32['others']) == sum(b32['counts'].values())
        provs = set(page.eval_on_selector_all('#valSub [data-prov]', 'xs => xs.map(x => x.dataset.prov)'))
        assert {'eda_draft', 'eu_derived'} <= provs and 'ich' in provs, provs                      # EDA's drafts beside ICH's own rules
        assert 'رسمية — ICH' in page.text_content('#valSub') and 'من مسودة الهيئة' in page.text_content('#valSub')
        assert 'لا «معتمد من الهيئة»' in page.inner_text('#valNote')
        assert page.locator('#view a[download]').count() == 0
        page.click('#valNext')                                                       # «التالي: التصدير»
        page.wait_for_selector('#expSub[data-state="ok"]')
        built = httpx.get(f'{server}/api/dossiers/{did}/builds').json()['submission']
        links = page.eval_on_selector_all('#expSub .dl a[download]', 'xs => xs.map(x => x.getAttribute("href"))')
        assert sorted(links) == sorted(built['downloads'].values())                  # the very files that were validated
        with page.expect_download(timeout=60000) as dl:
            page.click('#expSub [data-dl="ectd32"]')
        out = tmp_path / 'e.zip'
        dl.value.save_as(out)
        assert '0000/index.xml' in zipfile.ZipFile(out).namelist()
        assert page.get_attribute('#expAfter', 'href').endswith(f'/d/{did}/after')
        # a new version of a document after the validation: not downloaded, and said
        old = next(s for s in httpx.get(f'{server}/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-31')['documents'][0]['id']
        up(server, did, 'M1-31', make_pdf(tmp_path / 'c2.pdf', 'made-up composition v2').read_bytes(), name='composition-v2.pdf', replaces=old)
        page.reload()
        page.wait_for_selector('#expSub[data-state="stale"]')
        assert page.locator('#expSub a[download], #expSub [data-gdl]').count() == 0
        assert 'composition-v2.pdf' in page.inner_text('#expSub [data-ch="replaced"]') and 'نسخة جديدة' in page.inner_text('#expSub')
        page.click('#expToVal')
        page.wait_for_selector('#valSign[data-state="v8SignStale"]')
        assert 'now' in path_state(page, 8)
        b.close()
    assert not errors, errors


def test_a_failed_rule_says_its_provenance_and_leads_to_its_document(server, tmp_path):
    """A working copy with a PDF that carries a security restriction (EG-PF-16.3, from an EDA draft): the rule did not pass, says
    whose rule it is, and the document it names is one press away (its item)."""
    from pypdf import PdfWriter
    did = dossier(server)
    w = PdfWriter(clone_from=str(make_pdf(tmp_path / 's.pdf', 'Restricted made-up letter')))
    w.encrypt(user_password='', owner_password='owner', permissions_flag=0)
    buf = io.BytesIO(); w.write(buf)
    doc = up(server, did, 'M1-11', buf.getvalue(), name='restricted.pdf')
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/checks')
        page.wait_for_selector('#wkGo')
        assert page.locator('#go').is_disabled() and page.get_attribute('#valSign', 'data-state') == 'v8SignBlocked'
        page.click('#wkGo')
        page.wait_for_selector('#valWork [data-rule="EG-PF-16.3"]', timeout=240000)
        row = page.locator('#valWork [data-rule="EG-PF-16.3"]')
        assert row.get_attribute('data-st') == 'fail' and row.locator('[data-prov="eda_draft"]').count() == 1
        btn = row.locator(f'[data-vdoc="{doc["id"]}"]')
        assert 'restricted.pdf' in btn.inner_text()
        btn.click()
        page.wait_for_selector('#drawer:not([hidden]) #dBody')
        assert 'restricted.pdf' in page.inner_text('#dBody')
        b.close()
    assert not errors, errors


@SOFFICE
def test_a_build_that_did_not_pass_is_downloaded_only_when_the_person_says_so(server, tmp_path):
    did = complete(server, tmp_path)
    r = httpx.post(f'{server}/api/dossiers/{did}/export', json={'acknowledge_provisional': True}, timeout=240)
    assert r.status_code == 201, r.text
    # its validation said «did not pass» (how a rule fails, and what it names, is the engine's: tests/test_stage4_engine.py)
    path = WS['root'] / 'exports' / did / r.json()['id'] / 'build.json'
    rec = json.loads(path.read_text(encoding='utf-8'))
    rec['validation']['eCTD 3.2.2']['ok'] = False
    rec['validation']['eCTD 3.2.2']['counts']['fail'] = 1
    path.write_text(json.dumps(rec, ensure_ascii=False), encoding='utf-8')
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/export')
        page.wait_for_selector('#expSub[data-state="fail"]')
        assert page.locator('#expSub a[download]').count() == 0 and page.locator('#expSub [data-gdl]').count() == 3
        assert 'القواعد التي لم تجتزها: 1' in page.inner_text('#expState')
        downloads = []
        page.on('download', lambda d: downloads.append(d.suggested_filename))
        page.click('#expSub [data-gdl][data-dl="ctd"]')
        page.wait_for_selector('#cfOk')
        assert 'قد ترفضها الجهة الرقابية' in page.inner_text('#dBody')
        page.click('#cfNo')                                                      # not this time: nothing downloaded
        page.wait_for_timeout(800)
        assert downloads == []
        page.click('#expSub [data-gdl][data-dl="ctd"]')
        with page.expect_download(timeout=60000) as dl:
            page.click('#cfOk')
        assert dl.value.suggested_filename == 'ctd.zip'
        b.close()
    assert not errors, errors


@SOFFICE
def test_after_submission_the_sequence_is_recorded_the_letter_answered_and_a_response_prepared(server, tmp_path):
    did = complete(server, tmp_path)
    assert httpx.post(f'{server}/api/dossiers/{did}/export', json={'acknowledge_provisional': True}, timeout=240).status_code == 201
    letter = make_pdf_lines(tmp_path / 'letter.pdf', ['Subject: Comments on the made-up file Examplol', 'Please respond within 30 days.',
                                                      '1. Provide the made-up stability data.', '2. Justify the made-up specification.'], title='Letter')
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/after')
        page.wait_for_selector('[data-frz="ectd32|0000"]')
        assert page.is_visible('#navAfter') and page.inner_text('#view h1').strip() == 'ما بعد التقديم'
        page.click('[data-frz="ectd32|0000"]')
        page.fill('#frzTrack', 'P-MAA-0001')
        page.click('#frzGo')
        page.wait_for_selector('#aftSeq >> text=P-MAA-0001')
        # the authority's letter: read, its two questions with the due date
        page.click('#aftAdd summary')
        page.set_input_files('#aftLetFile', str(letter))
        page.click('#aftLetGo')
        page.wait_for_selector('[data-let] [data-q]')
        card = page.locator('[data-let]')
        assert 'Comments on the made-up file Examplol' in card.inner_text() and card.locator('[data-q]').count() == 2
        assert card.locator('[data-days="30"]').count() == 1                        # «within 30 days» from the day it came
        assert card.locator('[data-reply]').count() == 0                            # the reply letter waits for every answer
        for i, q in enumerate(page.eval_on_selector_all('[data-qans]', 'xs => xs.map(x => x.dataset.qans)')):
            page.fill(f'[data-qans="{q}"]', f'Made-up answer {i + 1}.')
            page.click(f'[data-qsave="{q}"]')
            page.wait_for_selector(f'[data-q="{q}"][data-qst="answered"]')
        with page.expect_download(timeout=60000) as dl:
            page.click('[data-reply]')
        out = tmp_path / 'reply.docx'
        dl.value.save_as(out)
        import docx
        text = '\n'.join(c.text for t in docx.Document(str(out)).tables for r in t.rows for c in r.cells)
        assert 'Made-up answer 1.' in text and 'Provide the made-up stability data.' in text
        assert [x['dossier_id'] for x in httpx.get(f'{server}/api/suite/letters', params={'dossier': did}).json()] == [did]
        # a response sequence: the next sequence set as a response, at station 8
        page.click('[data-resp]')
        page.wait_for_selector('#nextSeqCard')
        assert page.input_value('#sqUnit') == 'response' and page.input_value('#sqDesc').startswith('Response to: Comments on the made-up file')
        assert 'eCTD 3.2.2 — التسلسل 0001' in page.inner_text('#valTech')
        b.close()
    assert not errors, errors


@SOFFICE
def test_the_three_pages_fit_a_phone(server, tmp_path):
    did = complete(server, tmp_path)
    assert httpx.post(f'{server}/api/dossiers/{did}/export', json={'acknowledge_provisional': True}, timeout=240).status_code == 201
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, width=390)
        for route, sel in (('checks', '#valSub'), ('export', '#expSub'), ('after', '#aftLetters')):
            page.goto(f'{server}/#/d/{did}/{route}')
            page.wait_for_selector(sel)
            sw = page.evaluate('document.documentElement.scrollWidth')
            assert sw <= 390, (route, sw)
        b.close()
