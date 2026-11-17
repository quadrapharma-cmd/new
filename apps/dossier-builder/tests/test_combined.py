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

from dossier_engine.combined import assemble, checks, ectd, fix, ocr, read, repeats, report, split  # noqa: E402
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


def test_reports(work):
    out = report.run(work)
    for kind in ('ctd', 'ectd'):
        assert Path(out[kind]['pdf']).stat().st_size > 5000 and Path(out[kind]['docx']).exists()
    text = subprocess.run(['pdftotext', out['ctd']['pdf'], '-'], capture_output=True, text=True).stdout
    assert 'الخلاصة' in text and 'الملاحظات' in text
