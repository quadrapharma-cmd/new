"""NeeS (updates list, item 40): the eCTD's folders and names without XML, a table of contents for the dossier and one per module whose
entries open the documents by relative links; read back from the disk by its own checks."""
import io, json, zipfile
from pathlib import Path
import pytest
from pypdf import PdfReader
from fixtures_pdf import make_pdf
from dossier_engine.writers import nees
from test_authorities import c, new                                                   # noqa: F401  (the app fixture and a dossier for a country)


@pytest.fixture
def exported(c, tmp_path):
    did = new(c, 'SA')['id']                                                              # the Gulf: a CTD and a NeeS, no eCTD written here
    pdf = make_pdf(tmp_path / 'd.pdf', 'content').read_bytes()
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] == 'R':
            assert c.post(f"/api/dossiers/{did}/slots/{s['slot_id']}/documents", files={'file': ('x.pdf', io.BytesIO(pdf), 'application/pdf')},
                          data={'meta': json.dumps({'signed': True})}).status_code == 201
    r = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['nees']})
    assert r.status_code == 201, r.text
    z = zipfile.ZipFile(io.BytesIO(c.get(r.json()['downloads']['nees']).content))
    out = tmp_path / 'nees'
    z.extractall(out)
    return r.json(), out / '0000'


def test_a_nees_has_the_ectd_folders_and_tables_whose_links_open_the_documents(exported):
    res, seq = exported
    assert res['validation']['NeeS']['ok'], res['validation']['NeeS']
    assert (seq / 'ctd-toc.pdf').is_file() and (seq / 'm1' / 'm1-toc.pdf').is_file() and (seq / 'm3' / 'm3-toc.pdf').is_file()
    assert not list(seq.rglob('*.xml')) and not list(seq.rglob('*md5*'))
    files = [p.relative_to(seq).as_posix() for p in seq.rglob('*.pdf')]
    assert any(f.startswith('m3/32-body-data/32s-drug-sub/neomycin-sulphate-example-api-co/') for f in files)     # one folder per substance and maker
    assert any(f.startswith('m3/32-body-data/32p-drug-prod/dermacure/') for f in files)
    assert any(f.startswith('m1/sa/') for f in files)
    m3 = PdfReader(str(seq / 'm3' / 'm3-toc.pdf'))
    acts = [a.get_object()['/A'] for p in m3.pages for a in (p.get('/Annots') or [])]
    assert acts and all(a['/S'] == '/GoToR' and not str(a['/F']).startswith(('/', '..')) for a in acts)
    assert all((seq / 'm3' / str(a['/F'])).is_file() for a in acts)
    assert m3.outline and 'table of contents' in m3.pages[0].extract_text()
    top = PdfReader(str(seq / 'ctd-toc.pdf'))
    assert {str(a.get_object()['/A']['/F']) for p in top.pages for a in p['/Annots']} >= {'m1/m1-toc.pdf', 'm3/m3-toc.pdf'}


def test_the_checks_catch_a_broken_link_and_a_bad_name(exported):
    _, seq = exported
    victim = next(p for p in (seq / 'm3').rglob('*.pdf') if p.name != 'm3-toc.pdf')
    victim.rename(victim.with_name('Renamed File.pdf'))
    r = nees.check(seq)
    bad = {x['rule'] for x in r['results'] if x['status'] == 'fail'}
    assert not r['ok'] and {'NEES-2', 'NEES-3'} <= bad


def test_clean_names_are_the_ectds():
    assert nees.clean('Stability (summary, protocol & commitment)') == 'stability-summary-protocol-commitment'
    assert nees.clean('') == 'document' and len(nees.clean('x' * 100)) == 40


def test_actd_puts_the_ctd_in_four_parts(c, tmp_path):
    from dossier_engine.writers import actd
    assert actd.place('2.3') == ('II', 'B', None) and actd.place('3.2.S.4.1') == ('II', 'C', 'S4.1') and actd.place('3.2.P.8') == ('II', 'C', 'P8')
    assert actd.place('4.2.3') == ('III', 'D', None) and actd.place('4.3') == ('III', 'E', None) and actd.place('5.3.1.2') == ('IV', 'E', None)
    assert actd.place('1.2.1') == ('I', None, None) and actd.place('2.5') == ('IV', 'B', None) and actd.place('5.4') == ('IV', 'F', None)
    did = new(c, 'TH')['id']                                                              # an ASEAN member state: «any other country» pack
    assert 'actd' in c.get(f'/api/dossiers/{did}').json()['authority']['outputs']
    pdf = make_pdf(tmp_path / 'd.pdf', 'content').read_bytes()
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['level'] == 'R':
            assert c.post(f"/api/dossiers/{did}/slots/{s['slot_id']}/documents", files={'file': ('x.pdf', io.BytesIO(pdf), 'application/pdf')},
                          data={'meta': json.dumps({'signed': True})}).status_code == 201
    r = c.post(f'/api/dossiers/{did}/export', json={'outputs': ['actd']})
    assert r.status_code == 201, r.text
    names = zipfile.ZipFile(io.BytesIO(c.get(r.json()['downloads']['actd']).content)).namelist()
    assert any('/Part II - Quality/Section C - Body of data/' in n for n in names) and any('/Part I - Administrative' in n for n in names)
    assert any(n.endswith('00-actd-map.csv') for n in names) and not any('/Module ' in n for n in names)


def test_the_fda_is_offered_no_nees(c):
    did = new(c, 'US')['id']
    assert 'nees' not in c.get(f'/api/dossiers/{did}').json()['authority']['outputs']
