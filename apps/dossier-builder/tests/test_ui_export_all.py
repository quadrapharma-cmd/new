"""The real export from the page, for every authority (the owner, 15/11/2026: «انا عايز برنامج كامل لكل الدول و مصر بالتلات صيغ اللي
اتفقنا عليهم»): a complete dossier, the export page, its own button («تصدير المخرجات المختارة») clicked as a person clicks it — Egypt
gives its three formats (CTD One Submission, eCTD 3.2.2, eCTD 4.0), the EU its CTD and eCTD 3.2.2 on EU Module 1, the Gulf its CTD,
eCTD 3.2.2 on GCC Module 1 and NeeS, the others what the countries table says — each recorded as a submission where it is an
eCTD. The button sent `submission: null` for a first sequence and the server refused it (422) until 15/11/2026. Made-up files."""
import io, json, socket, threading, time, urllib.parse, urllib.request, zipfile
import pytest
from fixtures_pdf import make_pdf

pw = pytest.importorskip('playwright.sync_api')
GENERIC = dict(dossier_kind='generic', origin='imported', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])
LOCAL = dict(dossier_kind='generic', origin='local', licence='own', activity='new', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='FULL')])
PRODUCT = dict(name='Dermacure', dosageform='Cutaneous powder', manufacturer='Example Pharm Co.', indication='skin-infections')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Dermacure', inn=['neomycin'])


@pytest.fixture(scope='module')
def server(tmp_path_factory):
    import uvicorn
    from dossier_engine.app.api import create_app
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    srv = uvicorn.Server(uvicorn.Config(create_app(tmp_path_factory.mktemp('ws'), auth_enabled=False), host='127.0.0.1', port=port, log_level='error'))
    threading.Thread(target=srv.run, daemon=True).start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f'http://127.0.0.1:{port}'
    srv.should_exit = True


def call(url, path, body=None, method=None):
    req = urllib.request.Request(url + path, method=method or ('POST' if body is not None else 'GET'),
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-DB': '1'})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def upload(url, did, slot, pdf, meta):
    boundary = '----x'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="x.pdf"\r\nContent-Type: application/pdf\r\n\r\n').encode() + pdf + \
        f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="meta"\r\n\r\n{json.dumps(meta)}\r\n--{boundary}--\r\n'.encode()
    urllib.request.urlopen(urllib.request.Request(f'{url}/api/dossiers/{did}/slots/{urllib.parse.quote(slot, safe="")}/documents', data=body, method='POST',
                                                  headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'X-DB': '1'}), timeout=60).read()


def complete(url, tmp_path, country):
    """A dossier whose gate is open: every required item holds a made-up document."""
    profile = {**GENERIC, 'extra': {'eu_procedure': 'dcp', 'eu_legal_basis': 'generic'}} if country == 'DE' else LOCAL if not country else GENERIC
    d = call(url, '/api/dossiers', dict(name='Dermacure', profile=profile, product=PRODUCT, envelope=ENV, **({'country': country} if country else {})))
    pdf = make_pdf(tmp_path / 'd.pdf', 'A made-up document').read_bytes()
    for s in call(url, f"/api/dossiers/{d['id']}/board")['slots']:
        if s['level'] not in (('R', 'O') if not country else ('R',)) or s['status'] != 'not_started':    # the other authorities: what they require
            continue
        meta = {'signed': True}
        if s['req_id'] in ('M1-09', 'EU-1.3.1'):
            meta |= {'pi_type': 'spc', 'lang': 'en'}
        if s['module'] == 5:
            meta |= {'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'}
        upload(url, d['id'], s['slot_id'], pdf, meta)
    gate = call(url, f"/api/dossiers/{d['id']}/gate")
    assert gate['ok'], {k: gate.get(k) for k in ('missing_required', 'non_conforming', 'unsigned', 'ectd_blocking')}
    return d


@pytest.mark.parametrize('country, outputs, regional', [
    (None, ['ctd', 'ectd32', 'ectd40'], '0000/m1/eg/eg-regional.xml'),        # Egypt: the three formats
    ('DE', ['ctd', 'ectd32'], '0000/m1/eu/eu-regional.xml'),
    ('SA', ['ctd', 'ectd32', 'nees'], '0000/m1/gc/gc-regional.xml'),
    ('US', None, None),
    ('JO', None, None),
])
def test_the_export_button_gives_every_format_of_the_authority(server, tmp_path, country, outputs, regional):
    d = complete(server, tmp_path, country)
    did = d['id']
    au = call(server, f'/api/dossiers/{did}')['authority']
    outputs = outputs or au['outputs']
    assert au['outputs'] == outputs, au['outputs']
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True).new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar')")
        page.goto(f'{server}/#/d/{did}/export')
        page.wait_for_selector('#go')
        assert not page.locator('#go').is_disabled(), 'the gate is open: the real export is offered'
        assert sorted(page.eval_on_selector_all('[data-out]:checked', 'xs => xs.map(x => x.dataset.out)')) == sorted(outputs)
        if page.locator('#ack').is_visible():
            page.check('#ack')                                                       # Egypt: the provisional EG profiles acknowledged
        page.click('#go')
        page.wait_for_selector('#res .dl a', timeout=240000)
        res = page.inner_text('#res')
        assert 'Unprocessable' not in res and 'فشل التصدير' not in res, res
        links = page.eval_on_selector_all('#res .dl a[download]', 'xs => xs.map(x => x.getAttribute("href"))')
        assert sorted(u.rsplit('/', 1)[-1] for u in links) == sorted(f'{o}.zip' for o in outputs), links
        for u in links:
            with page.expect_download(timeout=60000) as dl:
                page.click(f'#res .dl a[href="{u}"]')
            out = tmp_path / dl.value.suggested_filename
            dl.value.save_as(out)
            names = zipfile.ZipFile(out).namelist()
            assert any(n.endswith('.pdf') for n in names), (out.name, names[:5])
            if out.name == 'ectd32.zip':
                assert regional in names and '0000/index.xml' in names
                assert 'WORKING COPY' not in zipfile.ZipFile(out).read(regional).decode('utf-8')   # the real one is not marked
            if out.name == 'ectd40.zip':
                assert any(n.endswith('/1/submissionunit.xml') for n in names)
        b.close()
    assert not errors, errors
    subs = call(server, f'/api/dossiers/{did}/submissions')
    for o in ('ectd32', 'ectd40'):
        assert [str(h['seq']) for h in subs[o]] == ([('0000' if o == 'ectd32' else '1')] if o in outputs else []), subs   # recorded: for submission


def test_the_export_page_asks_for_the_indication_and_the_export_then_goes(server, tmp_path):
    """A complete Egyptian dossier made without the product's indication: the export page asks for it (2.7.3 / 5.3.5 carry it in the
    eCTD, ICH DTD «#REQUIRED») with a field, before any export; once written, the three formats go (found 15/11/2026: the real
    export stopped late with «5.3.5.4 needs an indication»)."""
    global PRODUCT
    keep = PRODUCT
    PRODUCT = {k: v for k, v in keep.items() if k != 'indication'}
    try:
        d = complete(server, tmp_path, None)
    finally:
        PRODUCT = keep
    did = d['id']
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_context(viewport={'width': 1440, 'height': 1000}).new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        page.add_init_script("localStorage.setItem('db.lang','ar')")
        page.goto(f'{server}/#/d/{did}/export')
        page.wait_for_selector('#indCard')
        assert 'دواعي استعمال' in page.inner_text('#indCard') and '5.3.5' in page.inner_text('#indCard')
        page.fill('#indText', 'الألم الخفيف والمتوسط')
        page.click('#indSave')
        page.wait_for_selector('#indCard', state='detached')
        page.wait_for_selector('#go')
        if page.locator('#ack').is_visible():
            page.check('#ack')
        page.click('#go')
        page.wait_for_selector('#res .dl a', timeout=240000)
        links = page.eval_on_selector_all('#res .dl a[download]', 'xs => xs.map(x => x.getAttribute("href"))')
        assert sorted(u.rsplit('/', 1)[-1] for u in links) == ['ctd.zip', 'ectd32.zip', 'ectd40.zip'], links
        b.close()
    assert not errors, errors
    assert call(server, f'/api/dossiers/{did}')['product']['indication'] == 'الألم الخفيف والمتوسط'
