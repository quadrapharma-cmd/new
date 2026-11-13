"""PdfCraft as the program's PDF engine (updates list, item 49; docs/ctd/PDFCRAFT-INTEGRATION.md): each stage on it — reading, checks,
fixes, pages, comparison, viewer, redaction, smaller files, EU signing — and the program still working where it is not (the browser
edition reads with pypdf). Fictional files only."""
import io, json, shutil
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from dossier_engine import fixes, pages, pdfcraft
from dossier_engine.app.api import create_app
from dossier_engine.checks import pdf as checks
from fixtures_pdf import make_pdf_lines

pc = pytest.mark.skipif(not pdfcraft.available(), reason='PdfCraft is not built here (tools/pdfcraft/build.sh)')
GENERIC = dict(dossier_kind='generic', origin='imported', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])
PRODUCT = dict(name='Dermacure', dosageform='topical powder', manufacturer='Example Pharm Co.', indication='skin-infections')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Dermacure', inn=['neomycin'])


def raw_pdf(stream):
    """One A4 page with Helvetica and the given content stream."""
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
            b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>']
    o = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offs = []
    for i, x in enumerate(objs, 1):
        offs.append(len(o))
        o += b'%d 0 obj\n' % i + x + b'\nendobj\n'
    xr = len(o)
    o += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1) + b''.join(b'%010d 00000 n \n' % f for f in offs)
    o += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xr)
    return bytes(o)


BODY = (b'BT /F1 12 Tf 16 TL 60 780 Td (Specification of the finished product Dermacure) Tj T* (Appearance: white powder) Tj T* '
        b'(Assay: 95.0 - 105.0 per cent of the labelled amount) Tj T* (Supplier: Example Chemicals Ltd) Tj ET\n')
SECRET = b'BT /F1 12 Tf 60 700 Td (Confidential price: EGP 45.00 per pack) Tj ET\n'
BOX = b'0 g 55 695 260 18 re f\n'


def check_of(tmp_path, data, cls='company_technical', name='doc.pdf'):
    p = tmp_path / name
    p.write_bytes(data)
    return p, checks.check(str(p), cls)


def test_the_engine_says_which_reads_the_pdfs(monkeypatch):
    s = pdfcraft.status()
    assert s['pin'] == (Path(__file__).parents[1] / 'tools' / 'pdfcraft' / 'PIN').read_text().strip()
    assert s['engine'] == ('PdfCraft' if s['available'] else 'pypdf')
    monkeypatch.setenv('PDFCRAFT', '0')                    # the browser edition, or a machine without it: pypdf, and it says why
    assert pdfcraft.status() == {**pdfcraft.status(), 'available': False, 'engine': 'pypdf'} and pdfcraft.page_texts(raw_pdf(BODY)) is None


@pc
def test_text_is_read_in_reading_order(tmp_path):
    data = raw_pdf(BODY)
    assert pdfcraft.page_texts(data) == ['Specification of the finished product Dermacure\nAppearance: white powder\n'
                                         'Assay: 95.0 - 105.0 per cent of the labelled amount\nSupplier: Example Chemicals Ltd']
    from dossier_engine import extract
    r = extract.pdf_text(data)
    assert r['reader'] == 'pdfcraft' and r['pages'] == 1 and 'Assay: 95.0' in r['text']


@pc
def test_a_faux_redaction_is_found_and_redacted_for_real(tmp_path):
    p, r = check_of(tmp_path, raw_pdf(BODY + SECRET + BOX))
    f = next(x for x in r.findings if x.rule == 'PDF-REDACT')
    assert 'Confidential price' in f.en and f.action == 'auto_fix' and f.scope == 'all' and r.info['faux_redactions'][0]['page'] == 1
    assert 'PDF-REDACT' not in {x.rule for x in check_of(tmp_path, raw_pdf(BODY + BOX), name='real.pdf')[1].findings}     # nothing under it
    out = fixes.apply(p, [x.to_dict() for x in r.findings], 'company_technical')
    assert 'apply_redaction' in [d['op'] for d in out['done']]
    text = pdfcraft.page_texts(out['data'])[0]
    assert 'Confidential' not in text and 'Assay: 95.0' in text and 'PDF-REDACT' not in {x.rule for x in out['report'].findings}
    _, third = check_of(tmp_path, raw_pdf(BODY + SECRET + BOX), 'third_party_certificate', 'tp.pdf')     # another's document: its issuer
    assert next(x for x in third.findings if x.rule == 'PDF-REDACT').action == 're_obtain'


@pc
def test_a_damaged_file_is_read_and_a_clean_copy_written_with_the_same_pages(tmp_path):
    good = raw_pdf(BODY)
    i = good.rfind(b'startxref')
    broken = good[:i] + b'startxref\n123\n%%EOF\n'                    # the cross-reference table points nowhere
    for cls in ('company_technical', 'third_party_certificate'):
        p, r = check_of(tmp_path, broken, cls, f'{cls}.pdf')
        assert 'PDF-REPAIR' in {x.rule for x in r.findings} and r.info['repairs'] and r.info['searchable'], cls
        out = fixes.apply(p, [x.to_dict() for x in r.findings], cls)
        assert [d['op'] for d in out['done']][:1] == ['repair'], (cls, out['refused'])
        assert 'PDF-REPAIR' not in {x.rule for x in out['report'].findings}
        assert pdfcraft.same_pixels(broken, out['data']) is True          # evidence too: the pages look the same, page for page
    assert pdfcraft.same_pixels(raw_pdf(BODY), raw_pdf(BODY + BOX)) is False


@pc
def test_attachments_comments_and_javascript_are_found_and_removed(tmp_path):
    from pypdf.annotations import FreeText
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(raw_pdf(BODY))))
    w.add_attachment('notes.txt', b'internal notes')
    w.add_js('app.alert(1);')
    w.add_annotation(0, FreeText(text='check this', rect=(50, 550, 200, 650)))
    b = io.BytesIO()
    w.write(b)
    p, r = check_of(tmp_path, b.getvalue())
    got = {x.rule: x for x in r.findings}
    assert {'PDF-ATTACH', 'PDF-ANNOT', 'PDF-JS'} <= set(got) and got['PDF-ATTACH'].scope == got['PDF-ANNOT'].scope == 'ectd'
    assert 'file formats v1.3' in got['PDF-ATTACH'].source
    out = fixes.apply(p, [x.to_dict() for x in r.findings], 'company_technical')
    assert {'remove_javascript', 'remove_attachments', 'remove_comments'} <= {d['op'] for d in out['done']}, out['refused']
    assert not {'PDF-ATTACH', 'PDF-ANNOT', 'PDF-JS'} & {x.rule for x in out['report'].findings}
    assert 'Assay: 95.0' in pdfcraft.page_texts(out['data'])[0]                       # the text stays
    _, tp = check_of(tmp_path, b.getvalue(), 'third_party_certificate', 'tp.pdf')
    assert all(x.action == 're_obtain' for x in tp.findings if x.rule in ('PDF-ATTACH', 'PDF-ANNOT', 'PDF-JS'))


@pc
def test_bookmarks_from_the_numbered_headings_at_their_place(tmp_path):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(12):
        if i % 3 == 0:
            c.setFont('Helvetica-Bold', 13)
            c.drawString(72, 760, f'3.2.P.{i // 3 + 1} Section {i // 3 + 1}')
        c.setFont('Helvetica', 10)
        for k in range(30):
            c.drawString(72, 720 - 20 * k, f'line {k} of page {i + 1}, 1.5 mg in each tablet')
        if i % 3 == 1:
            c.setFont('Helvetica-Bold', 11)
            c.drawString(72, 100, f'3.2.P.{i // 3 + 1}.1 Sub-section')
        c.showPage()
    c.save()
    p, r = check_of(tmp_path, buf.getvalue())
    assert 'NTA065-BM' in {x.rule for x in r.findings}
    out = fixes.apply(p, [x.to_dict() for x in r.findings], 'company_technical')
    assert 'add_bookmarks' in [d['op'] for d in out['done']]
    q = pdfcraft.query(out['data'], [('bookmark_list', {}), ('doc_initial_view', {})])
    tree = [(x['title'], x['page'], [y['title'] for y in x['children']]) for x in q['bookmark_list']['bookmarks']]
    assert tree[0] == ('3.2.P.1 Section 1', 1, ['3.2.P.1.1 Sub-section']) and len(tree) == 4 and tree[3][1] == 10
    assert q['doc_initial_view']['initial_view']['navigation'] == 'Bookmarks'
    assert not any('mg' in t for t, _, _ in tree)                                     # «1.5 mg» is not a heading


@pc
@pytest.mark.skipif(not shutil.which('soffice'), reason='needs LibreOffice')
def test_bookmarks_from_a_word_documents_tagged_headings(tmp_path):
    import docx, subprocess
    d = docx.Document()
    for i in range(6):
        d.add_heading(f'2.3.S.{i + 1} Drug substance part {i + 1}', 1)
        d.add_paragraph('Text of the section. ' * 200)
        d.add_heading(f'Detail {i + 1}', 2)
        d.add_paragraph('More text. ' * 200)
    d.save(tmp_path / 'qos.docx')
    opt = 'pdf:writer_pdf_Export:{"UseTaggedPDF":{"type":"boolean","value":"true"},"ExportBookmarks":{"type":"boolean","value":"false"}}'
    subprocess.run(['soffice', '--headless', '--convert-to', opt, '--outdir', str(tmp_path), str(tmp_path / 'qos.docx')], capture_output=True, timeout=240)
    data = (tmp_path / 'qos.pdf').read_bytes()
    if pdfcraft.query(data, [('bookmark_list', {})])['bookmark_list']['bookmarks']:
        pytest.skip('this LibreOffice wrote bookmarks itself')
    p, r = check_of(tmp_path, data)
    out = fixes.apply(p, [x.to_dict() for x in r.findings], 'company_technical')
    q = pdfcraft.query(out['data'], [('bookmark_list', {})])
    top = q['bookmark_list']['bookmarks']
    assert [x['title'] for x in top][:2] == ['2.3.S.1 Drug substance part 1', '2.3.S.2 Drug substance part 2']   # no «Untitled» above them
    assert top[0]['children'][0]['title'] == 'Detail 1'


@pc
def test_a_file_too_large_is_made_smaller(tmp_path, monkeypatch):
    from PIL import Image, ImageDraw
    import random
    random.seed(7)
    im = Image.new('L', (2480, 3508), 245)
    d = ImageDraw.Draw(im)
    for y in range(200, 3300, 60):
        d.rectangle([180, y, 180 + random.randint(900, 2100), y + 22], fill=random.randint(20, 60))
    buf = io.BytesIO()
    im.save(buf, 'PDF', resolution=300)
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(buf.getvalue())))
    w.pages[0].merge_page(PdfReader(io.BytesIO(raw_pdf(BODY))).pages[0])
    out = io.BytesIO()
    w.write(out)
    monkeypatch.setattr(checks, 'SIZE_LIMIT', 1000)
    p, r = check_of(tmp_path, out.getvalue())
    f = next(x for x in r.findings if x.rule == 'PDF-SIZE')
    assert f.action == 'auto_fix' and f.scope == 'ectd'
    res = fixes.apply(p, [x.to_dict() for x in r.findings], 'company_technical')
    assert 'reduce_size' in [d['op'] for d in res['done']] and len(res['data']) < len(out.getvalue())


@pc
def test_split_and_combine_keep_their_bookmarks_and_the_reading_copy_nests_them(tmp_path):
    w = PdfWriter(clone_from=PdfReader(io.BytesIO(raw_pdf(BODY))))
    w.add_page(PdfReader(io.BytesIO(raw_pdf(SECRET))).pages[0])
    w.add_outline_item('Own bookmark', 1)
    b = io.BytesIO()
    w.write(b)
    a, z = pages.split(b.getvalue(), [(1, 1), (2, 2)])
    assert pdfcraft.page_count(a) == pdfcraft.page_count(z) == 1
    assert pdfcraft.page_count(pages.merge([a, z, a])) == 3
    book = pages.bound([('Module 3', '3.2.P.5.1 Specification', 'Spec', b.getvalue()), ('Module 3', '3.2.P.5.1 Specification', 'Annex', a),
                        ('Module 1', '1.2 Form', 'Form', a), ('Module 1', '1.2 Form', 'broken', b'%PDF-1.4 nothing')], 'Dermacure')
    q = pdfcraft.query(book, [('bookmark_list', {'limit': 1000})])
    walk = lambda bs: [(x['title'], walk(x.get('children') or [])) for x in bs]
    assert walk(q['bookmark_list']['bookmarks']) == [
        ('Module 3', [('3.2.P.5.1 Specification', [('Spec', [('Own bookmark', [])]), ('Annex', [])])]),
        ('Module 1', [('1.2 Form', [('Form', [])])])]


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


def upload(c, did, data, name='doc.pdf', slot=None):
    if slot is None:
        slot = next(s['slot_id'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots']
                    if s['doc_class'] in ('company_technical', 'company_letter') and s['level'] in ('R', 'O'))
    r = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': (name, io.BytesIO(data), 'application/pdf')}, data={'meta': '{}'})
    assert r.status_code == 201, r.text
    return r.json()


@pc
def test_the_viewer_draws_pages_and_finds_words_with_their_places(client, tmp_path):
    did = client.post('/api/dossiers', json=dict(name='Dermacure', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    doc = upload(client, did, raw_pdf(BODY + SECRET))
    r = client.get(f"/api/dossiers/{did}/documents/{doc['id']}/pages/1.png?dpi=40")
    assert r.status_code == 200 and r.content[:8] == b'\x89PNG\r\n\x1a\n'
    assert client.get(f"/api/dossiers/{did}/documents/{doc['id']}/pages/9.png").json()['detail']['code'] == 'E-PAGE'
    hits = client.get(f"/api/dossiers/{did}/documents/{doc['id']}/find", params={'q': 'confidential price'}).json()['matches']
    assert len(hits) == 1 and hits[0]['page'] == 1 and 125 < hits[0]['rects'][0][1] < 145      # from the top of the page
    caps = client.get('/api/capabilities').json()['pdf_engine']
    assert caps['available'] and caps['engine'] == 'PdfCraft' and client.get('/api/pdf-engine').json() == caps


@pc
def test_redaction_and_a_smaller_file_from_the_interface_make_new_versions(client):
    did = client.post('/api/dossiers', json=dict(name='Dermacure', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    doc = upload(client, did, raw_pdf(BODY + SECRET))
    r = client.post(f"/api/dossiers/{did}/documents/{doc['id']}/redact", json={'words': ['EGP 45.00']})
    assert r.status_code == 201, r.text
    new = r.json()['document']
    assert new['version'] == doc['version'] + 1 and new['meta']['pdfcraft'] == 'redact'
    text = client.get(f"/api/dossiers/{did}/documents/{new['id']}/file").content
    assert 'EGP 45.00' not in pdfcraft.page_texts(text)[0] and 'Confidential price' in pdfcraft.page_texts(text)[0]
    assert client.post(f"/api/dossiers/{did}/documents/{new['id']}/redact", json={'words': []}).json()['detail']['code'] == 'E-REDACT'
    assert client.post(f"/api/dossiers/{did}/documents/{new['id']}/reduce").json()['detail']['code'] == 'E-REDUCE'   # nothing to make smaller
    tp = next(s['slot_id'] for s in client.get(f'/api/dossiers/{did}/board').json()['slots'] if s['doc_class'] == 'third_party_certificate')
    other = upload(client, did, raw_pdf(BODY + SECRET), 'gmp.pdf', tp)
    assert client.post(f"/api/dossiers/{did}/documents/{other['id']}/redact", json={'words': ['EGP']}).json()['detail']['code'] == 'E-LOCKED'


@pc
def test_signing_is_for_eu_dossiers_with_the_persons_own_id(client, tmp_path):
    res, out = pdfcraft.run([('sign_id_create', {'name': 'Example Signer', 'organization': 'Example Pharm Co.', 'password': 'example-pass-1',
                                                 'path': 'id.p12', 'years': 1})], read=('id.p12',))
    p12 = out['id.p12']
    eu = client.post('/api/dossiers', json=dict(name='Dermacure EU', country='DE', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    doc = upload(client, eu, raw_pdf(BODY))
    r = client.post(f"/api/dossiers/{eu}/documents/{doc['id']}/sign", files={'p12': ('id.p12', io.BytesIO(p12), 'application/x-pkcs12')},
                    data={'password': 'example-pass-1', 'reason': 'Applicant'})
    assert r.status_code == 201, r.text
    signed = client.get(f"/api/dossiers/{eu}/documents/{r.json()['document']['id']}/file").content
    sig = pdfcraft.query(signed, [('sign_list', {})])['sign_list']
    assert sig['count'] == 1 and sig['signatures'][0]['status'] in ('valid', 'unknown')       # intact; a self-made ID is not a trusted one
    bad = client.post(f"/api/dossiers/{eu}/documents/{r.json()['document']['id']}/sign", files={'p12': ('id.p12', io.BytesIO(p12), 'application/x-pkcs12')},
                      data={'password': 'wrong'})
    assert bad.json()['detail']['code'] == 'E-PDFCRAFT-OP'
    eg = client.post('/api/dossiers', json=dict(name='Dermacure', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    d2 = upload(client, eg, raw_pdf(BODY))
    r = client.post(f"/api/dossiers/{eg}/documents/{d2['id']}/sign", files={'p12': ('id.p12', io.BytesIO(p12), 'application/x-pkcs12')},
                    data={'password': 'example-pass-1'})
    assert r.json()['detail']['code'] == 'E-SIGN-REGION' and '2.10.3' in r.json()['detail']['en']


def test_without_pdfcraft_the_program_reads_with_pypdf_and_says_so(client, monkeypatch, tmp_path):
    monkeypatch.setenv('PDFCRAFT', '0')
    p, r = check_of(tmp_path, raw_pdf(BODY))
    assert r.info['engine'] == 'pypdf' and r.status == 'conforming'
    did = client.post('/api/dossiers', json=dict(name='Dermacure', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    doc = upload(client, did, raw_pdf(BODY))
    assert client.get('/api/pdf-engine').json()['engine'] == 'pypdf'
    assert client.get(f"/api/dossiers/{did}/documents/{doc['id']}/pages/1.png").json()['detail']['code'] == 'E-PDFCRAFT'
    from dossier_engine import extract
    assert extract.pdf_text(raw_pdf(BODY))['reader'] == 'pypdf'


@pc
def test_pages_turn_on_every_document_and_are_removed_or_moved_on_the_companys_own(client):
    did = client.post('/api/dossiers', json=dict(name='Dermacure', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    three = pages.merge([raw_pdf(BODY), raw_pdf(SECRET), raw_pdf(BODY)])
    doc = upload(client, did, three)
    r = client.post(f"/api/dossiers/{did}/documents/{doc['id']}/pages", json={'op': 'rotate', 'pages': [2], 'degrees': 90}).json()
    got = client.get(f"/api/dossiers/{did}/documents/{r['document']['id']}/file").content
    q = pdfcraft.query(got, [('doc_info', {})])['doc_info']
    assert [p['rotation'] for p in q['pages']] == [0, 90, 0]
    r = client.post(f"/api/dossiers/{did}/documents/{r['document']['id']}/pages", json={'op': 'move', 'pages': [2], 'to': 1}).json()
    moved = client.get(f"/api/dossiers/{did}/documents/{r['document']['id']}/file").content
    assert pdfcraft.page_texts(moved)[0].startswith('Confidential price')
    r = client.post(f"/api/dossiers/{did}/documents/{r['document']['id']}/pages", json={'op': 'delete', 'pages': [1]}).json()
    left = client.get(f"/api/dossiers/{did}/documents/{r['document']['id']}/file").content
    assert pdfcraft.page_count(left) == 2 and not any('Confidential' in t for t in pdfcraft.page_texts(left))
    last = r['document']['id']
    assert client.post(f"/api/dossiers/{did}/documents/{last}/pages", json={'op': 'delete', 'pages': [1, 2]}).json()['detail']['code'] == 'E-PAGES'
    assert client.post(f"/api/dossiers/{did}/documents/{last}/pages", json={'op': 'rotate', 'pages': [9]}).json()['detail']['code'] == 'E-PAGES'
    tp = next(s['slot_id'] for s in client.get(f'/api/dossiers/{did}/board').json()['slots'] if s['doc_class'] == 'third_party_certificate')
    cert = upload(client, did, three, 'gmp.pdf', tp)
    assert client.post(f"/api/dossiers/{did}/documents/{cert['id']}/pages", json={'op': 'rotate', 'pages': [1], 'degrees': 180}).status_code == 201
    cur = next(d for s in client.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == tp for d in s['documents'])
    assert client.post(f"/api/dossiers/{did}/documents/{cur['id']}/pages", json={'op': 'delete', 'pages': [1]}).json()['detail']['code'] == 'E-LOCKED'


@pc
def test_the_teams_notes_go_on_the_pages_of_a_copy(client):
    did = client.post('/api/dossiers', json=dict(name='Dermacure', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    doc = upload(client, did, pages.merge([raw_pdf(BODY), raw_pdf(SECRET)]))
    assert client.get(f"/api/dossiers/{did}/documents/{doc['id']}/notes.pdf").json()['detail']['code'] == 'E-NO-NOTES'
    client.post(f"/api/dossiers/{did}/documents/{doc['id']}/comments", json={'text': 'Check the assay limits', 'page': 1})
    client.post(f"/api/dossiers/{did}/documents/{doc['id']}/comments", json={'text': 'Price must not be here', 'page': 2})
    r = client.get(f"/api/dossiers/{did}/documents/{doc['id']}/notes.pdf")
    assert r.status_code == 200 and 'notes' in r.headers['content-disposition']
    notes = pdfcraft.query(r.content, [('comment_list', {})])['comment_list']
    found = {(c['page'], c.get('contents') or c.get('text')) for c in (notes.get('comments') or [])}
    assert (1, 'Check the assay limits') in found and (2, 'Price must not be here') in found
    kept = client.get(f"/api/dossiers/{did}/documents/{doc['id']}/file").content       # the filed document carries no comments
    assert not (pdfcraft.query(kept, [('comment_list', {})])['comment_list'].get('comments') or [])


@pc
def test_the_assistant_finds_and_runs_pdfcraft_tools_within_the_rules(client):
    from types import SimpleNamespace
    from dossier_engine.assistant import tools as T
    did = client.post('/api/dossiers', json=dict(name='Dermacure', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()['id']
    doc = upload(client, did, raw_pdf(BODY + SECRET))
    ctx = SimpleNamespace(st=client.app.state.store, did=did)
    found = T.run_tool(ctx, 'pdf_tools', {'query': 'find text'})
    names = [t['name'] for t in json.loads(found['content'])['tools']]
    assert 'text_find' in names and not any(n.startswith('js_') for n in names)
    r = T.run_tool(ctx, 'pdf_run', {'doc_id': doc['id'], 'steps': [{'tool': 'text_find', 'args': {'query': 'confidential price'}}]})
    body = json.loads(r['content'])
    assert body['results'][0]['result'][0]['count'] == 1
    r = T.run_tool(ctx, 'pdf_run', {'doc_id': doc['id'], 'steps': [{'tool': 'page_rotate', 'args': {'degrees': 90}}], 'save': True, 'rationale': 'test'})
    body = json.loads(r['content'])
    assert body['saved']['version'] == doc['version'] + 1
    with pytest.raises(T.ToolError):
        T.run_tool(ctx, 'pdf_run', {'doc_id': body['saved']['doc_id'], 'steps': [{'tool': 'js_run', 'args': {'script': 'app.alert(1)'}}]})
    tp = next(s['slot_id'] for s in client.get(f'/api/dossiers/{did}/board').json()['slots'] if s['doc_class'] == 'third_party_certificate')
    cert = upload(client, did, raw_pdf(BODY + SECRET), 'gmp.pdf', tp)
    with pytest.raises(T.ToolError):                                                    # another's document: only what keeps its pages as they are
        T.run_tool(ctx, 'pdf_run', {'doc_id': cert['id'], 'steps': [{'tool': 'redact_mark', 'args': {'find': 'EGP'}}, {'tool': 'redact_apply', 'args': {}}],
                                    'save': True, 'rationale': 'test'})


@pytest.mark.skipif(not hasattr(__import__('os'), 'killpg'), reason='process groups as on Linux and macOS (Windows: taskkill /T)')
def test_a_run_that_takes_too_long_is_stopped_with_every_program_it_started(tmp_path):
    """PdfCraft starts Tesseract for each page. A run stopped for taking too long stops them too: left running on, they took the
    processor from everything else (13/11/2026)."""
    import os, subprocess, sys, time
    pid = tmp_path / 'child.pid'
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):                 # a stand-in for PdfCraft: it starts a long program and waits
        pdfcraft._run_tree([sys.executable, '-c', 'import subprocess, sys, pathlib; c = subprocess.Popen(["sleep", "60"]); '
                            f'pathlib.Path({str(pid)!r}).write_text(str(c.pid)); c.wait()'], tmp_path, dict(os.environ), 3)
    assert time.monotonic() - started < 30
    child = int(pid.read_text())
    for _ in range(50):
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            break
        time.sleep(0.1)
    else:
        pytest.fail(f'the program it started ({child}) is still running')
