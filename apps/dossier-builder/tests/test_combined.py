"""The combined-file program (dossier_engine.combined) on a made-up dossier (tests/combined_fixture.py: «Zentorix», «Example
Pharma Ltd.» — rule 7): every stage from the received files to the eCTD sequence and the reports."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pikepdf
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'engine'))
sys.path.insert(0, str(HERE))

from dossier_engine.combined import assemble, assess, checks, ctdzip, ebox, ectd, ectd40, fix, ocr, read, repeats, report, split  # noqa: E402
from dossier_engine.combined.common import Work, parse_ranges, ranges  # noqa: E402
from dossier_engine.combined.pdfedit import edit_page  # noqa: E402

import combined_fixture  # noqa: E402

NEED = [t for t in ('ocrmypdf', 'tesseract', 'pdftoppm', 'pdftotext', 'soffice') if not shutil.which(t)]
pytestmark = pytest.mark.skipif(bool(NEED), reason=f'tools missing: {NEED}')


@pytest.fixture(scope='module')
def work(tmp_path_factory):
    root = tmp_path_factory.mktemp('combined')
    combined_fixture.build(root / 'received')
    w = Work(root / 'work')
    read.run(root / 'received', w)
    repeats.run(w)
    ocr.run(w)
    return w


def test_ranges():
    assert ranges([1, 2, 3, 7, 9, 10]) == '1–3, 7, 9–10'
    assert parse_ranges('1-3, 7') == [1, 2, 3, 7]
    assert parse_ranges('4–5') == [4, 5]


def test_read(work):
    files = work.load('read/files.json')
    pdf = next(f for f in files if f['kind'] == 'pdf')
    assert pdf['pages'] == 47
    word = next(f for f in files if f['kind'] == 'rtf')
    assert word['keep_as'] == 'MODULE - I ZENTORIX.rtf' and word['aside']
    assert word['matches']['block'] == 'MODULE I'
    top = [o for o in work.load('read/outline.json') if o['level'] == 0]
    assert [o['page'] for o in top] == [1, 13, 20, 30, 40, 45]
    assert len(list((work.read / 'thumbs').glob('p*.png'))) == 47


def test_repeated_block(work):
    rep = work.load('repeats.json')
    assert [(d['from'], d['to'], d['same_as']) for d in rep['dropped']] == [(30, 39, [20, 29])]
    assert rep['kept'] == [[1, 29], [40, 47]]


def test_ocr_reads_the_pictures(work):
    parts = work.load('parts.json')
    assert [(p['from'], p['to']) for p in parts] == [(1, 29), (40, 47)]
    assert all(not p['still_without_text'] for p in parts)
    text = work.pages_text('read/ocr.txt')
    assert 'Reactor R-101' in text[7] and 'Certificate 3' in text[21]
    assert text[33] == ''                                            # a page of the repeated block: never read


def test_split_proposal(work):
    docs, removed = split.run(work)
    by = {d['ctd']: d for d in docs}
    out = {r['page']: r['why'] for r in removed}
    assert 1 in out and 2 in out                                      # the drug substance's table of contents
    assert by['3.2.S.1.1']['pages'] == [3]
    assert 5 in out and '3.2.S.2' in out[5]                           # the group's separator
    assert by['3.2.S.2.2']['pages'] == [7, 8]                         # the picture page joins the document before it
    assert by['3.2.P.1']['pages'] == [14]                             # printed «3.2.P.2.1», its title is 3.2.P.1's
    assert 'printed heading «3.2.P.2.1»' in by['3.2.P.1']['note']
    assert 40 in out and 45 in out                                    # the modules' covers
    assert by['2.2']['pages'] == [41] and by['2.5']['pages'] == [44]
    annex = next(d for d in docs if d['title'].startswith('Annexure 1'))
    assert annex['pages'] == list(range(20, 30)) and annex['path'].startswith('Module 3/Annexures to be placed/')
    assert all(p not in out and p not in [x for d in docs for x in d['pages']] for p in range(30, 40))
    assert not work.load('plan.json')['missing']


def test_decisions_and_record(work):
    plan = work.load('plan.json')
    wanted = [dict(d) for d in plan['proposal']['docs']]
    for d in wanted:
        if d['title'].startswith('Annexure 1'):
            d.update({'path': 'Module 3/3.2.S Zentorine/3.2.S.2 Manufacture/3.2.S.2.3 Control of materials.pdf', 'ctd': '3.2.S.2.3',
                      'title': '3.2.S.2.3 Control of materials (Zentorine)'})
    edits, notes = split.record(plan['proposal']['docs'], plan['proposal']['removed'], wanted, plan['proposal']['removed'])
    assert len(edits) == 1 and edits[0]['ctd'] == '3.2.S.2.3' and edits[0]['pages'] == '20-29'
    (work.root / 'dossier.json').write_text(json.dumps({'plan': edits, 'names': {'product': 'Zentorix tablets'}}), encoding='utf-8')
    docs, _ = split.run(work)
    got = next(d for d in docs if d['ctd'] == '3.2.S.2.3')
    assert got['pages'] == list(range(20, 30)) and got['by'] == 'decision'
    same, renamed, other = split.compare(docs, [d for d in wanted])
    assert len(other) == 0


def test_assemble_checks_every_page(work):
    res = assemble.run(work)
    assert res['wrong'] == [] and res['pages_checked'] == sum(len(d['pages']) for d in work.load('plan.json')['docs'])
    assert res['worst_look_change'] < 0.01
    folder = Path(res['folder'])
    assert (folder / 'Not for submission' / 'Word files received' / 'MODULE - I ZENTORIX.rtf').exists()
    one = next(folder.rglob('3.2.S.1.1 Nomenclature.pdf'))
    with pikepdf.open(one) as pdf:
        assert len(pdf.pages) == 1 and str(pdf.Root.PageMode) == '/UseOutlines'


def test_findings(work):
    found = checks.run(work)
    rules = {f['rule'] for f in found}
    assert 'units' in rules and 'heading_number' in rules
    units = next(f for f in found if f['rule'] == 'units')
    assert units['severity'] == 'critical' and '41' in units['where'] and '14' in units['where']


def test_correction_inside_a_pdf(work, tmp_path):
    folder = Path(work.load('assembled.json')['folder'])
    src = folder / 'Module 2' / '2.2 CTD introduction.pdf'
    with pikepdf.open(src) as pdf:
        assert edit_page(pdf, 0, [('1.25 mcg', '1.25 mg')]) == [('1.25 mcg', '1.25 mg')]
        pdf.save(tmp_path / 'fixed.pdf')
    text = subprocess.run(['pdftotext', str(tmp_path / 'fixed.pdf'), '-'], capture_output=True, text=True).stdout
    assert '1.25 mg' in text and 'mcg' not in text
    with pikepdf.open(src) as pdf, pytest.raises(ValueError):
        edit_page(pdf, 0, [('1.25 mcg', '1.25 mcgx')])                  # adding is refused: deletions only


def test_qos_file_names_the_substance_without_its_manufacturer():
    assert ectd.without_maker('zentorine-ep', 'example pharma ltd., some city') == 'zentorine'          # initials
    assert ectd.without_maker('zentorine-example', 'Example Pharma Ltd.') == 'zentorine'               # first word
    assert ectd.without_maker('zentorine-exp', '', 'Zentorine (EXP)') == 'zentorine'                   # the dossier's short name
    assert ectd.without_maker('zentorine-ex', 'example pharma ltd.') == 'zentorine-ex'                 # not the manufacturer's
    assert ectd.without_maker('ep', 'example pharma ltd.') == 'ep'                                     # nothing left: kept
    assert ectd.without_maker('zentorine-whole-cell', '', 'Zentorine (whole cell)') == 'zentorine-whole-cell'


def test_translation_check_and_rtl_page():
    en = [{'t': 'PACKAGE LEAFLET'}, {'p': 'Each tablet contains 10 mg.'}, {'rows': [['Zentorine', '10 mg']]}]
    ar = [{'t': 'النشرة الداخلية'}, {'p': 'يحتوي كل قرص على 10 mg.'}, {'rows': [['زنتورين', '10 mg']]}]
    assert fix.check_translation(en, ar) == []
    bad = [{'t': 'النشرة الداخلية'}, {'p': 'يحتوي كل قرص على 20 mg.'}, {'rows': [['زنتورين', '10 mg']]}]
    assert fix.check_translation(en, bad)
    html = fix.html_rtl(ar, 'Leaflet')
    assert '<span dir="ltr">10\u00a0mg</span>' in html            # the number and its unit kept together, left to right


def test_ectd_sequence_and_validation(work):
    dec = json.loads((work.root / 'dossier.json').read_text(encoding='utf-8'))
    dec['fixes'] = [{'doc': 'Module 2/2.2 CTD introduction.pdf', 'page': 1, 'edits': [['1.25 mcg', '1.25 mg']], 'note': 'unit corrected'}]
    dec['ectd'] = {'today': '2026-11-17', 'envelope': {
        'identifier': '0a7c1c1e-5b8a-4d6e-9f10-3c2b1a0d9e8f', 'submission_type': 'maa', 'tracking': 'EDA-TEST-1', 'unit': 'initial',
        'applicant': 'Example Pharma Ltd.', 'invented_name': 'Zentorix', 'registration': 'imported-finished', 'marketing': 'local',
        'inn': ['zentorine'], 'description': 'A made-up product for the tests'},
        'manufacturer': 'example pharma ltd.', 'product': {'product-name': 'zentorix', 'dosageform': 'film-coated tablet', 'manufacturer': 'example pharma ltd.'},
        'indication': 'example indication', 'substances': {'Zentorine': {'folder': 'zentorine-ex', 'substance': 'zentorine'}}}
    (work.root / 'dossier.json').write_text(json.dumps(dec), encoding='utf-8')
    rec = fix.run(work)
    assert rec['docs']['Module 2/2.2 CTD introduction.pdf']['changed_pixels'] < 0.01
    e = ectd.run(work)
    val = {r['rule']: r for r in work.load('validation.json')}
    assert val['EG-PF-7.4']['ok'] and val['EG-PF-9.4']['ok']          # both XML files valid against their DTDs
    assert val['EG-PF-11.2']['ok'] and val['EG-PF-15.8']['ok']        # checksums right, nothing unreferenced
    assert val['EG-PF-16.1']['ok']                                    # no PDF older than 1.4
    assert e['validation']['pf_fail'] == 0, [r for r in val.values() if not r['ok'] and r['kind'] == 'P/F']
    seq = Path(e['sequence'])
    index = (seq / 'index.xml').read_text(encoding='utf-8')
    assert 'm2/22-intro/introduction.pdf' in index
    fixed = next(l for l in e['leaves'] if l['code'] == '2.2')
    assert fixed['source'].endswith('.fixed.pdf')


def test_ectd40_and_ctd_zip_carry_the_same_documents(work):
    e = work.load('ectd.json')
    r4 = ectd40.run(work)
    assert r4['validation']['fail'] == 0, [x for x in r4['results'] if x['status'] == 'fail']
    assert r4['number'] == 1 and r4['documents'] == len(e['leaves']) + len(e['m1'])
    seq4 = Path(r4['sequence'])
    assert seq4.parent.name == e['envelope']['identifier'].lower() and (seq4 / 'submissionunit.xml').exists()
    if any(l['code'] == '2.3.intro' for l in e['leaves']):       # 2.3's introduction: its own heading in 4.0 (a real dossier, 28/11)
        assert 'ich_2.3.i"' in (seq4 / 'submissionunit.xml').read_text(encoding='utf-8')
    md5s = {l['md5'] for l in e['leaves']}                       # the same bytes as the 3.2.2 sequence's
    import hashlib
    pdfs4 = [p for p in seq4.rglob('*.pdf')]
    assert pdfs4 and all(hashlib.md5(p.read_bytes()).hexdigest() in md5s | {m[4] for m in e['m1']} for p in pdfs4)
    cz = ctdzip.run(work)
    assert cz['unplaced'] == [] and cz['documents'] == r4['documents']
    import zipfile
    names = zipfile.ZipFile(cz['zip']).namelist()
    assert any(n.endswith('00-navigator.html') for n in names) and any(n.endswith('00-checklist.csv') for n in names)
    assert any('/3.2.S Zentorine - ' in n and '3.2.S.7 Stability' in n for n in names)        # 3.2.S.7.1 → EDA's 3.2.S.7 item
    assert not any('3.2.S.1.1 3.2.S.1.1' in n for n in names)                                # the number once in a name


@pytest.mark.parametrize('country, outputs, check', [('SA', {'ctd-working', 'ectd32-working'}, 'eCTD 3.2.2 (GCC M1 1.5)'),
                                                     ('DE', {'ctd-working', 'ectd32-working'}, 'eCTD 3.2.2 (EU M1 3.1.1)'),
                                                     ('US', {'ctd-working'}, None)])
def test_another_country_through_the_full_program(work, country, outputs, check):
    r = ebox.run(work, country)
    assert r['country'] == country and set(r['files']) == outputs and all(Path(f).exists() for f in r['files'].values())
    assert r['placed'] >= 18
    if check:
        assert r['validation'][check]['ok'], r['validation'][check]


def test_the_assessors_review_and_one_request_per_party(work):
    ebox.run(work, 'EG')
    r = assess.run(work)
    assert r['verdict'] in ('ready', 'ready_with_risks', 'not_ready') and r['counts']['total'] > 50
    screening = next(d for d in r['desks'] if d['dept'] == 'screening')
    assert screening['name'] == 'الفحص الأولي' and Path(screening['files']['report_pdf']).exists()
    asked = [p for p in r['parties'] if p['kind'] != 'company']
    assert asked and all(p.get('letter') and Path(p['letter']).exists() for p in asked)
    assert all(':' not in Path(p['letter']).name for p in asked)                 # a name every computer can keep
    text = subprocess.run(['pdftotext', asked[0]['letter'], '-'], capture_output=True, text=True).stdout
    assert 'Request for documents' in text and 'Zentorix' in text


def test_reports(work):
    out = report.run(work)
    for kind in ('ctd', 'ectd'):
        assert Path(out[kind]['pdf']).stat().st_size > 5000 and Path(out[kind]['docx']).exists()
    text = subprocess.run(['pdftotext', out['ctd']['pdf'], '-'], capture_output=True, text=True).stdout
    assert 'الخلاصة' in text and 'الملاحظات' in text
    assert Path(out['deliver']['ctd_zip']).exists() and Path(out['deliver']['ectd40_zip']).exists()
    etext = subprocess.run(['pdftotext', out['ectd']['pdf'], '-'], capture_output=True, text=True).stdout
    assert 'الصيغتان الأخريان' in etext
    ctext = subprocess.run(['pdftotext', out['ctd']['pdf'], '-'], capture_output=True, text=True).stdout
    assert 'مراجعة المق' in ctext and Path(out['deliver']['review']).exists()


def test_the_delivered_sequence_opens_in_the_full_program(work, tmp_path):
    """The desk's eCTD zip imported into eBOX's full program («import earlier sequences»): every document of Modules 3 finds its
    item — a sub-section's (3.2.S.7.1) in EDA's whole-section item (3.2.S.7)."""
    import dataclasses
    import zipfile
    from dossier_engine.app.store import Store
    from dossier_engine.profile import Api, Profile
    rep = work.load('report.json')
    st = Store(tmp_path / 'ebox')
    did = st.create_dossier('Zentorix', dataclasses.asdict(Profile(origin='imported', licence='imported', apis=[Api('Zentorine', 'example pharma ltd.')])),
                            {'name': 'Zentorix', 'dosageform': 'film-coated tablet', 'manufacturer': 'example pharma ltd.'}, {'applicant': 'Example Pharma Ltd.'})
    z = zipfile.ZipFile(rep['deliver']['zip'])
    r = st.import_ectd(did, [(n, z.read(n)) for n in z.namelist() if not n.endswith('/')])
    assert not [u for u in r['unplaced'] if u['href'].startswith('m3/')], r['unplaced']
    assert [h['seq'] for h in st.history(did, 'ectd32')] == ['0000']


def test_every_product_information_type_of_the_322_profile_is_taken_by_the_40_profile():
    # 28/11/2026: a real dossier's separate immediate-label text («impack», a 3.2.2 type) stopped its eCTD 4.0 sequence
    import yaml
    from dossier_engine.writers.ectd40 import Profile40
    v0 = Path(ectd40.__file__).resolve().parents[5] / 'docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v0/vocab/pi-doc-type.yaml'
    t322 = {v['value'] for v in yaml.safe_load(v0.read_text(encoding='utf-8'))['values']}
    spec = Profile40().cou('1.3.1')[2]
    allowed = next(a for name, _c, _cs, a in spec if name == 'eg document type (product information)')
    assert 'impack' in t322 and t322 <= set(allowed)


def test_the_introduction_of_23_is_its_own_heading_in_both_writers():
    # 28/11/2026: the desk's 3.2.2 stage files 2.3's introduction as «2.3.intro»; the 4.0 writer knew no ICH element for it
    from dossier_engine.writers import ectd32
    from dossier_engine.writers.ectd40 import Profile40
    p = Profile40()
    assert ectd40.CODES['2.3.intro'] == '2.3.I' and p.cou('2.3.I')[0] == 'ich_2.3.i'
    d = ectd32.Doc(node='2.3.I', file='x.pdf', title='Introduction')
    assert ectd32.rel_path(d, ectd32.Product(name='P', dosageform='tablet', manufacturer='M'), p.v32) == 'm2/23-qos/introduction.pdf'


def test_a_sequence_with_the_introduction_of_23_is_written_and_validated_in_40(work):
    import copy
    e = copy.deepcopy(work.load('ectd.json'))
    two = next(l for l in e['leaves'] if l['code'] == '2.2')
    e['leaves'].append(dict(two, code='2.3.intro', title='2.3 Introduction', id='leaf-23-intro'))
    r4 = ectd40.run(work, rec=e)
    assert r4['validation']['fail'] == 0, [x for x in r4['results'] if x['status'] == 'fail']
    su = (Path(r4['sequence']) / 'submissionunit.xml').read_text(encoding='utf-8')
    assert 'code="ich_2.3.i"' in su and any(p.as_posix().endswith('m2/23-qos/introduction.pdf') for p in Path(r4['sequence']).rglob('*.pdf'))
    ectd40.run(work)                                             # the work folder's own 4.0 sequence again, for what follows
