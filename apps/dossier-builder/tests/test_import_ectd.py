"""Import an application's earlier eCTD sequences (updates list, item 24): the documents land in their items, the sequences become
the dossier's frozen history, and the next sequence continues the lifecycle against the imported leaves."""
import io, json, shutil, zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from test_api import new
from test_lifecycle_api import fill_all

pytestmark = pytest.mark.skipif(not shutil.which('soffice'), reason='LibreOffice missing (tracking table)')


def zipped(root):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for p in sorted(Path(root).rglob('*')):
            if p.is_file():
                z.writestr(p.relative_to(root).as_posix(), p.read_bytes())
    return buf.getvalue()


def test_sequences_made_elsewhere_become_this_dossiers_history(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    src = new(c)
    fill_all(c, src, pdf)
    assert c.post(f'/api/dossiers/{src}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32']}).status_code == 201
    made = tmp_path / 'ws' / 'lifecycle' / src / 'ectd-3.2.2'                    # «elsewhere»: the folder another program would deliver
    index = (made / '0000' / 'index.xml').read_text(encoding='utf-8')
    assert '<node-extension>' in index and '<title>EXM-BE-01</title>' in index                 # a study's documents under its own node (EDA M1 spec p. 9)
    assert any('/exm-be-01/' in p.as_posix() for p in (made / '0000' / 'm5').rglob('*.pdf'))   # and in its own folder
    assert '<node-extension>' not in index.split('m5-2-tabular-listing')[0]                     # never above the lowest heading, never in m1–m4 here
    did = new(c)
    r = c.post(f'/api/dossiers/{did}/import-ectd', files={'file': ('app.zip', zipped(made), 'application/zip')})
    assert r.status_code == 201, r.text
    rep = r.json()
    assert [x['sequence'] for x in rep['sequences']] == ['0000'] and rep['sequences'][0]['region'] == 'eg' and rep['placed'] > 20
    h = c.get(f'/api/dossiers/{did}/submissions').json()['ectd32']
    assert [x['seq'] for x in h] == ['0000'] and h[0]['frozen']
    board = c.get(f'/api/dossiers/{did}/board').json()
    comp = next(s for s in board['slots'] if s['slot_id'] == 'M1-31')
    assert comp['documents'] and comp['documents'][0]['meta']['imported']['seq'] == '0000'
    placed = {s['slot_id']: s['documents'][0]['filename'] for s in board['slots'] if s['documents']}
    assert placed['S-01@Paracetamol|Granules India'] == 'nomenclature.pdf' and placed['P-04'] == 'batch-formula.pdf'   # a section under an element: by its file
    assert placed['M1-38@Paracetamol|Granules India'] == 'gmpcert-2.pdf' and placed['M1-37'] == 'gmpcert.pdf'        # one place, two items: by the title
    assert placed['R-02'].startswith('master-production') and not rep['unplaced'] and not rep['check'], rep
    assert 'tracking.pdf' not in placed.values()                                       # the tracking table is made again, not imported
    be = next(s for s in board['slots'] if s['slot_id'] == 'M5-04')['documents'][0]
    assert be['meta'].get('study') == 'EXM-BE-01'                                       # the study comes back from its node-extension
    # an item eCTD does not carry (the Module 5 table of contents: CTD only) is the person's to add
    c.post(f'/api/dossiers/{did}/slots/M5-01/documents', files={'file': ('m5-toc.pdf', io.BytesIO(pdf), 'application/pdf')}, data={'meta': '{}'})
    again = c.post(f'/api/dossiers/{did}/import-ectd', files={'file': ('app.zip', zipped(made), 'application/zip')})
    assert again.json()['detail']['code'] == 'E-SEQ-EXISTS'
    # the next sequence continues from the imported one: the changed composition certificate is a «replace»
    pdf2 = make_pdf(tmp_path / 'd2.pdf', 'composition v2').read_bytes()
    c.post(f'/api/dossiers/{did}/slots/M1-31/documents', files={'file': ('comp-v2.pdf', io.BytesIO(pdf2), 'application/pdf')},
           data={'meta': '{}', 'replaces': comp['documents'][0]['id']})
    cover = next(s for s in board['slots'] if s['slot_id'] == 'M1-43')['documents'][0]['id']
    c.post(f'/api/dossiers/{did}/slots/M1-43/documents', files={'file': ('cover-0001.pdf', io.BytesIO(make_pdf(tmp_path / 'c1.pdf', 'cover 0001').read_bytes()), 'application/pdf')},
           data={'meta': '{}', 'replaces': cover})
    sub = {'type': 'var-pac-b', 'unit': 'initial', 'mode': 'single', 'description': 'PAC-B', 'tracking': 'P-VAR-0001'}
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32'], 'submission': sub})
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['sequences']['ectd32']['sequence'] == '0001' and j['sequences']['ectd32']['operations']['replace'] == 1
    assert j['sequences']['ectd32']['operations']['delete'] == 0, j['sequences']['ectd32']
    assert j['validation']['eCTD 3.2.2']['ok'], j['validation']['eCTD 3.2.2']
