"""The working copy with its eCTD (the owner, 15/11/2026: «اعمله، خلي نسخة العمل تطلع بالـ XML»). Whatever the gate says, the working
copy gives — beside the CTD folders — the authority's eCTD sequence with its XML, written by the real export's own code, marked
«not for submission» in its envelope and beside it in the zip, and never recorded: the submissions, the lifecycle folder and the
next sequence's number stay as they were. Made-up documents only."""
import io, shutil, zipfile
import pytest
from docx import Document
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf, make_pdf_lines
from dossier_engine.app import exporter
from dossier_engine.app.api import create_app

PROFILE = dict(dossier_kind='generic', origin='local', licence='toll', activity='re_registration',
               apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='FULL')])
PRODUCT = dict(name='Dermacure', dosageform='Cutaneous powder', manufacturer='Example Pharm Co.', indication='skin-infections')
ENV = dict(tracking='T-0001', applicant='Example Pharm Co.', invented_name='Dermacure', inn=['neomycin'])
GENERIC = dict(dossier_kind='generic', origin='imported', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])
MARK = 'WORKING COPY — NOT FOR SUBMISSION'


@pytest.fixture()
def c(tmp_path):
    client = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    client.headers.update({'X-DB': '1'})
    client.ws = tmp_path / 'ws'
    return client


def up(c, did, slot, name, data, ctype='application/pdf'):
    r = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': (name, io.BytesIO(data), ctype)}, data={'meta': '{}'})
    assert r.status_code == 201, r.text


def egypt(c, tmp_path, word=True):
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope=ENV)).json()['id']
    up(c, did, 'M1-37', 'gmp.pdf', make_pdf_lines(tmp_path / 'g.pdf', ['CERTIFICATE OF GMP COMPLIANCE OF A MANUFACTURER', 'Example Pharm Co.']).read_bytes())
    if word:
        w = Document()
        w.add_paragraph('Finished product specification of Dermacure (made up)')
        b = io.BytesIO()
        w.save(b)
        up(c, did, 'P-09', 'fps.docx', b.getvalue(), 'application/msword')
    return did


def zipped(c, url):
    return zipfile.ZipFile(io.BytesIO(c.get(url).content))


def test_the_working_copy_gives_the_ectd_with_its_xml_and_records_nothing(c, tmp_path):
    did = egypt(c, tmp_path)
    assert c.post(f'/api/dossiers/{did}/export', json={'outputs': ['ectd32']}).json()['detail']['code'] == 'E-GATE'     # the real one still waits
    r = c.post(f'/api/dossiers/{did}/export', json={'working': True})
    assert r.status_code == 201, r.text
    w = r.json()
    assert list(w['downloads']) == ['ctd-working', 'ectd32-working', 'ectd40-working'] and w['missing_required'] > 50
    assert w['sequences']['ectd32']['sequence'] == '0000' and w['sequences']['ectd40']['sequence'] == 1
    assert w['validation']['eCTD 3.2.2']['ok'] and w['validation']['eCTD 3.2.2']['counts']['fail'] == 0, w['validation']
    assert w['validation']['eCTD 4.0']['ok'] and w['validation']['eCTD 4.0']['counts']['fail'] == 0, w['validation']
    assert w['ectd']['region'] == 'eg' and w['ectd']['skipped'] == {}
    assert [e['name'][-10:] for e in w['ectd']['left_out']] == ([] if shutil.which('soffice') else ['(fps.docx)'])   # the Word file goes in as its PDF where LibreOffice is
    z = zipped(c, w['downloads']['ectd32-working'])
    names = z.namelist()
    assert {'0000/index.xml', '0000/index-md5.txt', '0000/m1/eg/eg-regional.xml', exporter.WORKING_NOTE} <= set(names), names
    assert any(n.startswith('0000/util/dtd/') for n in names) and any(n.endswith('.pdf') and '/m1/eg/' in n for n in names)
    assert all(n == exporter.WORKING_NOTE or n.startswith('0000/') for n in names)              # the note beside the sequence, never in it
    regional = z.read('0000/m1/eg/eg-regional.xml').decode('utf-8')
    assert f'<submission-description>{MARK} — ' in regional                                      # the XML itself says it
    note = z.read(exporter.WORKING_NOTE).decode('utf-8')
    assert MARK in note and 'ليست للتقديم' in note and 'index.xml' in note
    assert 'submissionunit.xml' in ' '.join(zipped(c, w['downloads']['ectd40-working']).namelist())
    report = c.get(w['report'])
    assert report.status_code == 200 and MARK in report.text and 'eCTD 3.2.2' in report.text
    ctd = zipped(c, w['downloads']['ctd-working']).namelist()
    assert any(n.endswith('00-MISSING.txt') for n in ctd) and any(n.endswith('.docx') for n in ctd)  # the CTD folders as before
    # nothing recorded: no submission, no lifecycle folder, and the next working copy (and the real export) still start at 0000
    assert c.get(f'/api/dossiers/{did}/submissions').json() == {'ectd32': [], 'ectd40': []}
    assert not (c.ws / 'lifecycle' / did).exists()
    again = c.post(f'/api/dossiers/{did}/export', json={'working': True}).json()
    assert again['sequences']['ectd32']['sequence'] == '0000' and again['id'] != w['id']


def test_without_libreoffice_a_word_file_is_left_out_of_the_working_ectd_and_named(c, tmp_path, monkeypatch):
    def no_office(*a, **k):
        raise RuntimeError('no LibreOffice here (the browser edition)')
    monkeypatch.setattr(exporter, 'to_pdf', no_office)
    did = egypt(c, tmp_path)
    w = c.post(f'/api/dossiers/{did}/export', json={'working': True}).json()
    [e] = w['ectd']['left_out']
    assert e['name'].endswith(' (fps.docx)') and e['why'] == exporter.WHY_WORD and w['ectd']['skipped'] == {}    # its item, its file, and why
    z = zipped(c, w['downloads']['ectd32-working'])
    assert 'fps.docx' in z.read(exporter.WORKING_NOTE).decode('utf-8')
    assert not any(n.endswith(('.docx', '.doc')) for n in z.namelist())                         # an eCTD takes PDF only
    assert w['validation']['eCTD 3.2.2']['counts']['fail'] == 0
    assert any(n.endswith('.docx') for n in zipped(c, w['downloads']['ctd-working']).namelist())  # the CTD folders keep the Word file


def test_a_sheet_stays_in_the_ctd_folders_and_is_named_beside_the_ectd(c, tmp_path):
    openpyxl = pytest.importorskip('openpyxl')
    did = egypt(c, tmp_path, word=False)
    wb = openpyxl.Workbook()
    wb.active['A1'] = 'Cost analysis (made up)'
    b = io.BytesIO()
    wb.save(b)
    up(c, did, 'M1-05', 'costs.xlsx', b.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    w = c.post(f'/api/dossiers/{did}/export', json={'working': True}).json()
    assert w['ectd']['left_out'] == [{'name': 'Pricing Certificate (costs.xlsx)', 'why': exporter.WHY_NOT_PDF}], w['ectd']
    z = zipped(c, w['downloads']['ectd32-working'])
    assert not any(n.endswith('.xlsx') for n in z.namelist()) and 'costs.xlsx' in z.read(exporter.WORKING_NOTE).decode('utf-8')
    assert any(n.endswith('.xlsx') for n in zipped(c, w['downloads']['ctd-working']).namelist())


def fill_all(c, did, pdf):
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] in ('R', 'O') and s['status'] == 'not_started':
            meta = {'pi_type': 'spc', 'lang': 'en'} if s['req_id'] == 'M1-09' else (
                {'study': 'EXM-BE-01', 'doc_type': 'ich_document_type_2'} if s['module'] == 5 else {})
            r = c.post(f"/api/dossiers/{did}/slots/{s['slot_id']}/documents", files={'file': ('x.pdf', io.BytesIO(pdf), 'application/pdf')},
                       data={'meta': __import__('json').dumps(meta)})
            assert r.status_code == 201, r.text


@pytest.mark.skipif(not shutil.which('soffice'), reason='LibreOffice missing (the real export\'s tracking table)')
def test_after_a_submitted_sequence_the_working_copy_shows_the_next_one_and_takes_nothing(c, tmp_path):
    from test_api import new
    did = new(c)
    fill_all(c, did, make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes())
    real = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32'], 'submission': None})   # as the page sends a first one
    assert real.status_code == 201, real.text
    assert real.json()['sequences']['ectd32']['sequence'] == '0000'
    lifecycle = sorted(p.name for p in (c.ws / 'lifecycle' / did / 'ectd-3.2.2').iterdir())
    # a changed document; the working copy shows sequence 0001 with only the change, without asking its type or a new cover letter
    old = next(s for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['slot_id'] == 'M1-31')['documents'][0]['id']
    r = c.post(f'/api/dossiers/{did}/slots/M1-31/documents', files={'file': ('comp-v2.pdf', io.BytesIO(make_pdf(tmp_path / 'd2.pdf', 'composition v2').read_bytes()), 'application/pdf')},
               data={'meta': '{}', 'replaces': old})
    assert r.status_code == 201
    w = c.post(f'/api/dossiers/{did}/export', json={'working': True, 'submission': {'type': 'var-pac-b', 'unit': 'initial', 'mode': 'single'}}).json()
    assert w['sequences']['ectd32']['sequence'] == '0001' and w['sequences']['ectd32']['operations']['replace'] == 1, w['sequences']
    names = zipped(c, w['downloads']['ectd32-working']).namelist()
    assert all(n == exporter.WORKING_NOTE or n.startswith('0001/') for n in names)                 # only the new sequence, as a real one
    # the history, the lifecycle folder and the next number untouched: the real follow-on still takes 0001
    assert [h['seq'] for h in c.get(f'/api/dossiers/{did}/submissions').json()['ectd32']] == ['0000']
    assert sorted(p.name for p in (c.ws / 'lifecycle' / did / 'ectd-3.2.2').iterdir()) == lifecycle


@pytest.mark.parametrize('country, regional', [('DE', '0000/m1/eu/eu-regional.xml'), ('SA', '0000/m1/gc/gc-regional.xml')])
def test_the_eu_and_gulf_working_copies_carry_their_own_module_1(c, tmp_path, country, regional):
    d = c.post('/api/dossiers', json=dict(name='Dermacure', country=country, profile=GENERIC, product=dict(PRODUCT, dosageform='topical powder'), envelope=ENV)).json()
    slot = next(s['slot_id'] for s in c.get(f"/api/dossiers/{d['id']}/board").json()['slots'] if s['level'] == 'R' and s['module'] in (1, 3))
    up(c, d['id'], slot, 'x.pdf', make_pdf(tmp_path / 'x.pdf', 'A made-up document').read_bytes())
    w = c.post(f"/api/dossiers/{d['id']}/export", json={'working': True}).json()
    assert list(w['downloads']) == ['ctd-working', 'ectd32-working'] and w['ectd']['skipped'] == {}, w
    z = zipped(c, w['downloads']['ectd32-working'])
    assert regional in z.namelist() and '0000/index.xml' in z.namelist()
    assert MARK in z.read(regional).decode('utf-8')
    assert all(v['counts']['fail'] == 0 for v in w['validation'].values()), w['validation']
    assert c.get(f"/api/dossiers/{d['id']}/submissions").json() == {'ectd32': [], 'ectd40': []}


def test_an_authority_without_an_ectd_gives_the_ctd_folders_only(c, tmp_path):
    d = c.post('/api/dossiers', json=dict(name='Dermacure', country='JO', profile=GENERIC, product=PRODUCT, envelope=ENV)).json()
    slot = next(s['slot_id'] for s in c.get(f"/api/dossiers/{d['id']}/board").json()['slots'] if s['level'] == 'R' and s['module'] in (1, 3))
    up(c, d['id'], slot, 'x.pdf', make_pdf(tmp_path / 'x.pdf', 'A made-up document').read_bytes())
    w = c.post(f"/api/dossiers/{d['id']}/export", json={'working': True}).json()
    assert list(w['downloads']) == ['ctd-working'] and w['ectd'] is None and w['report'] is None and w['sequences'] == {}


def test_a_document_the_ectd_cannot_place_is_left_out_with_its_reason_and_the_rest_is_written(c, tmp_path, monkeypatch):
    """Found on his real Wouncure files (15/11/2026): the SmPC and PIL put in the leaflet item as Word files become PDFs where LibreOffice
    is, without their PI type and language, and the writer refuses 1.3.1 — the whole working eCTD was lost. Now each document is
    tried alone: that one is left out, named with the reason in both languages, and the XML of the rest is written."""
    made = make_pdf(tmp_path / 'converted.pdf', 'The SmPC, converted (made up)')
    monkeypatch.setattr(exporter, 'to_pdf', lambda p, *a, **k: made)      # a computer with LibreOffice, without having it here
    did = egypt(c, tmp_path, word=False)
    w = Document()
    w.add_paragraph('Summary of product characteristics (made up)')
    b = io.BytesIO()
    w.save(b)
    up(c, did, 'M1-09', 'spc.docx', b.getvalue(), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    r = c.post(f'/api/dossiers/{did}/export', json={'working': True}).json()
    [e] = r['ectd']['left_out']
    assert e['name'].endswith(' (spc.docx)') and '1.3.1 needs pi_type and lang' in e['why']['en'] and 'نوع النشرة' in e['why']['ar'], e
    assert r['ectd']['skipped'] == {} and list(r['downloads']) == ['ctd-working', 'ectd32-working', 'ectd40-working']
    z = zipped(c, r['downloads']['ectd32-working'])
    assert '0000/m1/eg/eg-regional.xml' in z.namelist() and not any('/13-pi/' in n or '1-3-1' in n for n in z.namelist())
    assert 'نوع النشرة' in z.read(exporter.WORKING_NOTE).decode('utf-8')
    assert all(v['counts']['fail'] == 0 for v in r['validation'].values()), r['validation']
