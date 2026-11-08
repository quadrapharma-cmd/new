"""Intake: the rules read certificates, CoAs and licences into the forms' shape; the API prepares the AI prompt."""
import io, json
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf, make_pdf_lines
from dossier_engine import extract
from dossier_engine.app.api import create_app


def sample_docs(tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', ['Certificate of Pharmaceutical Product', 'Certificate No: CPP-2024-0117', 'Trade name: Cardiolol 10 mg',
                         'Dosage form: film-coated tablet', 'Active ingredient: Bisoprolol fumarate', 'Manufacturer: Medis S.A., Nabeul, Tunisia',
                         'Marketing authorisation holder: Medis S.A.', 'Date of issue: 12 March 2025', 'Valid until: 11 March 2027',
                         'Issued by: Ministry of Health'], 'WHO Certification Scheme')
    coa = make_pdf_lines(tmp_path / 'coa.pdf', ['Certificate of Analysis', 'Product: Cardiolol 10 mg tablets', 'Batch No: CB2401',
                         'Batch size: 300000 tablets', 'Date of manufacture: 2025-02-10', 'Assay 98.7 %', 'Dissolution 94 %', 'Water content 3.1 %'])
    gmp = make_pdf_lines(tmp_path / 'gmp.pdf', ['GMP Certificate', 'Certificate Number: EG/GMP/2024/55', 'Manufacturer: Example Pharma S.A.E.',
                         'Site address: Plot 7, 6th of October City, Giza', 'Egyptian Drug Authority', 'Date of issue: 01/06/2024',
                         'Valid until: 31/05/2027'])
    return cpp, coa, gmp


def test_rules_read_certificates_into_the_forms_shape(tmp_path):
    cpp, coa, gmp = sample_docs(tmp_path)
    r = extract.read_files([(p.name, p.read_bytes()) for p in (cpp, coa, gmp)])
    f = r['rules']
    assert f['product']['name'] == 'Cardiolol 10 mg' and f['product']['dosage_form'] == 'film-coated tablet' and f['product']['strength'] == '10 mg'
    assert f['apis'][0]['name'] == 'Bisoprolol fumarate' and f['envelope']['applicant'].startswith('Medis')
    assert f['profile']['origin'] == 'imported' and f['profile']['admin_route'] == 'oral' and 'coated' in f['profile']['dosage_specifics']
    assert f['batches'][0] == {'no': 'CB2401', 'kind': 'fpp', 'size': '300000 tablets', 'date': '2025-02-10'}
    assert {x['test']: x['value'] for x in f['results']}['Assay'] == '98.7 %'
    docs = {d['filename']: d for d in f['documents']}
    assert docs['cpp.pdf'] == {'filename': 'cpp.pdf', 'kind': 'cpp', 'number': 'CPP-2024-0117', 'issuer': 'Ministry of Health',
                               'issued': '2025-03-12', 'valid_until': '2027-03-11'}
    assert docs['gmp.pdf']['issuer'] == 'Egyptian Drug Authority' and docs['gmp.pdf']['valid_until'] == '2027-05-31'
    assert [x['kind'] for x in r['files']] == ['cpp', 'coa', 'gmp'] and not any(x['scanned'] for x in r['files'])


def test_scanned_pdf_is_flagged_and_dates_parse(tmp_path):
    blank = make_pdf(tmp_path / 'scan.pdf', ' ')
    r = extract.read_files([('scan.pdf', blank.read_bytes())])
    assert r['files'][0]['scanned'] and r['rules']['documents'][0]['kind'] == 'other'
    assert extract.date_after('Valid until 5 Nov 2026', ['Valid until']) == '2026-11-05'
    assert extract.date_after('Expiry date: 31.12.2027', ['Expiry date']) == '2027-12-31'
    assert extract.date_after('Date of issue 2025-01-09', ['Date of issue']) == '2025-01-09'
    assert 'SCANNED' in extract.ai_prompt(r['files']) and '"documents"' in extract.ai_prompt(r['files'], 'document')


def test_extract_endpoints(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    cpp, coa, gmp = sample_docs(tmp_path)
    files = [('files', (p.name, io.BytesIO(p.read_bytes()), 'application/pdf')) for p in (cpp, coa, gmp)]
    r = c.post('/api/extract', files=files)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['rules']['product']['name'] == 'Cardiolol 10 mg' and 'cpp.pdf' in j['prompt'] and 'Certificate No: CPP-2024-0117' in j['prompt']
    assert 'text' in j['files'][0] and j['ai_server'] is False          # the texts go back to the browser: it re-runs the rules after its own OCR of scans
    # from the documents already in a dossier
    prof = dict(dossier_kind='generic', origin='imported', licence='imported', activity='new',
                apis=[dict(name='Bisoprolol fumarate', manufacturer='Unichem', option='CEP')])
    did = c.post('/api/dossiers', json=dict(name='Cardiolol', profile=prof, product=dict(name='Cardiolol 10 mg', dosageform='tablet', manufacturer='Medis'),
                                             envelope={})).json()['id']
    for slot, p in (('M1-14', cpp), ('M1-37', gmp)):
        assert c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': (p.name, io.BytesIO(p.read_bytes()), 'application/pdf')},
                      data={'meta': '{}'}).status_code == 201
    j = c.post(f'/api/dossiers/{did}/extract').json()
    assert j['rules']['product']['name'] == 'Cardiolol 10 mg' and sorted(f['kind'] for f in j['files']) == ['cpp', 'gmp']


def test_ai_endpoint_explains_the_missing_key(tmp_path, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'x.pdf', 'GMP certificate')
    r = c.post('/api/extract/ai', files=[('files', ('x.pdf', io.BytesIO(pdf.read_bytes()), 'application/pdf'))])
    assert r.status_code == 501 and r.json()['detail']['code'] == 'E-NO-AI' and r.json()['detail']['ar']
    assert c.get('/api/capabilities').json()['ai_server'] is False
