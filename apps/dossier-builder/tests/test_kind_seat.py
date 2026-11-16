"""Three things the proposed tree needs of the engine — each shown by the owner's real files when they first went through it
(16/11/2026), and each true of the program before it:

1. The kind rule («is this the document the item asks for», judged by what is written in the file) spoke only when a file arrived
   in its item. A scan placed from the tree has no words yet — where Claude reads the scans, the page does not read them first — so
   the rule passed it on what Claude took it for, and was not asked again when the scan was read for its preparation. Before the
   tree, a waiting scan was read and placed in one step, and the rule saw its words. Now it judges a placed document again when it
   is prepared: once, and never after the person overruled it.

2. The documents of one item are numbered in their names (-1, -2 …) in the order of their current versions. A document fixed,
   improved or turned after its neighbours jumped to the end, and every name in the item changed — while the tree shows each file
   «the name it will carry». A new version now keeps the seat of the document it replaces.

3. A combined file was cut wherever a page read as another kind of document than the page before it. The pages of one document
   often do (a specification with its test methods, a validation protocol with its section on the stability of the solutions):
   two real documents were cut at pages that begin in the middle of a sentence, and their pages scattered over several items. A
   part now begins under a title, at «page 1 of N», or at another batch's certificate of analysis.
Made-up files."""
import io
import json
import pytest
from fastapi.testclient import TestClient
from dossier_engine import extract, pdfcraft
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf_lines
from test_browser_reading import scan, REP, TAG, browser          # noqa: F401 — the engine as in the browser edition: no OCR of its own
from test_priority2 import PROFILE, PRODUCT

H = {'X-DB': '1'}
needs_pdfcraft = pytest.mark.skipif(not pdfcraft.available(), reason='needs PdfCraft')
STABILITY = ['Stability study approval', 'Accelerated stability study: 40 C / 75 % RH, 6 months', 'Long term stability study: 30 C / 65 % RH', 'Approved shelf life: 24 months']


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


def new(c):
    return c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=PRODUCT, envelope={}), headers=H).json()['id']


def stage(c, did, name, data, kind=None):
    r = c.post(f'/api/dossiers/{did}/unplaced', files=[('files', (name, io.BytesIO(data), 'application/pdf'))],
               data={'meta': json.dumps({name: {'kind': kind}} if kind else {})}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()[0]['id']


def place(c, did, doc, slot):
    r = c.post(f'/api/dossiers/{did}/documents/{doc}/place', json={'slot_id': slot, 'meta': {}}, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def kind_findings(doc):
    return [f for f in doc['findings'] if f['rule'] == 'DOC-KIND']


def in_item(c, did, slot):
    return next(s for s in c.get(f'/api/dossiers/{did}/board', headers=H).json()['slots'] if s['slot_id'] == slot)['documents']


def names(c, did):
    return {d['original_name'] if d.get('original_name') else d['filename']: d['names']['ctd'] for d in c.get(f'/api/dossiers/{did}/prepare', headers=H).json()['placed']}


def test_a_scan_placed_from_the_tree_is_judged_by_its_words_when_it_is_prepared(browser, c):
    did = new(c)
    data = scan(seed=3)
    doc = stage(c, did, 'scan0007.pdf', data, kind='licence')                         # what Claude took it for, from its pictures
    w = c.get(f'/api/dossiers/{did}/tree', headers=H).json()['waiting'][0]
    assert w['place'] == 'M1-04' and w['reading']['reader'] == 'none'                  # proposed on Claude's word: the file itself says nothing yet
    placed = place(c, did, doc, 'M1-04')                                               # «اعتماد الشجرة»
    assert not kind_findings(placed)
    # its preparation: the page reads the scan (web/boot.js readWholeScan), then the engine prepares it — and the rule sees its words
    assert c.post('/api/ocr/browser', json={'sha256': extract._sha(data), 'texts': ['\n'.join(STABILITY)], 'rep': REP, 'tag': TAG}).status_code == 200
    r = c.post(f'/api/dossiers/{did}/prepare/{placed["id"]}', json={}, headers=H)
    assert r.status_code == 200, r.text
    now = in_item(c, did, 'M1-04')[0]
    said = kind_findings(now)
    assert len(said) == 1 and said[0]['severity'] == 'block' and 'stability' in said[0]['en'].lower() and 'ثبات' in said[0]['ar']
    assert now['check_status'] == 'non_conforming'
    assert any(x['id'] == 'rule:DOC-KIND' and x['status'] == 'needs_you' for x in r.json()['conditions'])
    # prepared again: said once, not twice
    c.post(f'/api/dossiers/{did}/prepare/{now["id"]}', json={}, headers=H)
    now = in_item(c, did, 'M1-04')[0]
    assert len(kind_findings(now)) == 1
    # «it is in the right place»: the person overrules the rule — and it does not come back at the next preparation
    assert c.post(f'/api/dossiers/{did}/documents/{now["id"]}/confirm-kind', headers=H).status_code == 200
    c.post(f'/api/dossiers/{did}/prepare/{now["id"]}', json={}, headers=H)
    now = in_item(c, did, 'M1-04')[0]
    assert not kind_findings(now) and now['meta']['kind_confirmed']['rule_said'] == 'stability'


def test_a_document_whose_words_agree_with_its_item_is_left_alone(browser, c, tmp_path):
    did = new(c)
    data = scan(seed=4)
    placed = place(c, did, stage(c, did, 'scan0008.pdf', data, kind='licence'), 'M1-04')
    c.post('/api/ocr/browser', json={'sha256': extract._sha(data), 'texts': ['Final Registration License\nTrade Name: Dermacure\nEgyptian Drug Authority'], 'rep': REP, 'tag': TAG})
    r = c.post(f'/api/dossiers/{did}/prepare/{placed["id"]}', json={}, headers=H)
    assert r.status_code == 200 and not kind_findings(in_item(c, did, 'M1-04')[0])
    # a document with its own words, put by the person in an item the rule objects to: said when it arrives, as before — and once
    coa = make_pdf_lines(tmp_path / 'coa.pdf', ['Certificate of Analysis', 'Neomycin sulphate', 'Batch No.: 240101', 'Assay 99.6 %'], 'CoA').read_bytes()
    wrong = place(c, did, stage(c, did, 'made-up-coa.pdf', coa), 'M1-04')
    assert len(kind_findings(wrong)) == 1
    c.post(f'/api/dossiers/{did}/prepare/{wrong["id"]}', json={}, headers=H)
    assert [len(kind_findings(d)) for d in in_item(c, did, 'M1-04') if d['filename'].startswith('made-up-coa')] == [1]


@needs_pdfcraft
def test_a_new_version_keeps_its_documents_seat_and_the_names_the_tree_showed_stay(c, tmp_path):
    did = new(c)
    a = stage(c, did, 'made-up-method-a.pdf', make_pdf_lines(tmp_path / 'a.pdf', ['Analytical procedure: assay by HPLC', 'Mobile phase: buffer and acetonitrile'], 'Method A').read_bytes())
    b = stage(c, did, 'made-up-method-b.pdf', make_pdf_lines(tmp_path / 'b.pdf', ['Analytical procedure: related substances', 'Column: C18, 250 mm'], 'Method B').read_bytes())
    t = c.post(f'/api/dossiers/{did}/tree', json={'place': {a: 'P-10', b: 'P-10'}}, headers=H).json()
    shown = {w['filename']: w['name'] for w in t['waiting']}                           # «اسمه في الملف», before anything is placed
    assert shown['made-up-method-a.pdf'].endswith('-1.pdf') and shown['made-up-method-b.pdf'].endswith('-2.pdf')
    pa, pb = place(c, did, a, 'P-10'), place(c, did, b, 'P-10')
    first = names(c, did)
    assert first['made-up-method-a.pdf'].endswith('-1.pdf') and first['made-up-method-b.pdf'].endswith('-2.pdf')
    # the first one gets a new version after its neighbour (a page turned; a fix or an improvement does the same)
    r = c.post(f'/api/dossiers/{did}/documents/{pa["id"]}/pages', json={'op': 'rotate', 'pages': [1], 'degrees': 90}, headers=H)
    assert r.status_code == 201, r.text
    a2 = r.json()['document']
    assert a2['id'] != pa['id'] and [d['id'] for d in in_item(c, did, 'P-10')] == [a2['id'], pb['id']]   # where it sat (before: after its neighbour)
    assert names(c, did) == first                                                      # …and each name is the one the tree showed
    for k, v in first.items():
        assert shown[k].endswith(v.rsplit('/', 1)[-1])
    # and again (a chain of versions keeps the first seat)
    a3 = c.post(f'/api/dossiers/{did}/documents/{a2["id"]}/pages', json={'op': 'rotate', 'pages': [1], 'degrees': 90}, headers=H).json()['document']
    assert [d['id'] for d in in_item(c, did, 'P-10')] == [a3['id'], pb['id']] and names(c, did) == first
    # moved to another item, it takes the last seat there — not a seat from where it came
    third = place(c, did, stage(c, did, 'made-up-spec.pdf', make_pdf_lines(tmp_path / 's.pdf', ['Specification of the finished product', 'Appearance: white powder'], 'Spec').read_bytes()), 'P-09')
    mv = c.post(f'/api/dossiers/{did}/documents/{a3["id"]}/move', json={'slot_id': 'P-09', 'meta': {}}, headers=H)
    assert mv.status_code in (200, 201), mv.text
    assert [d['filename'] for d in in_item(c, did, 'P-09')] == ['made-up-spec.pdf', 'made-up-method-a.pdf']
    assert 'seat' not in in_item(c, did, 'P-09')[1]['meta']


# 3. the cutting rule: a change of subject is not the beginning of a document
ONE_DOCUMENT = [      # a «specification and test method»: its pages read as four kinds, and three of them begin in the middle of a sentence
    ['Example Pharm', 'Specification And Test Method Of Finished Product', 'Document Code: QC/FP/001', 'Specification of the finished product', 'Description: white powder', 'Assay limits: 95.0 % to 105.0 %'],
    ['and the mean of the two readings is taken.', 'Method validation: linearity, accuracy, precision and specificity were shown', 'System suitability: five injections of the made-up standard'],
    ['made up to volume with the same solvent and mixed.', 'Stability of the standard solution: stable for 24 hours', 'Accelerated stability study at 40 C / 75 % RH for 6 months'],
    ['before the next sample is injected.', 'Analytical procedure: assay by HPLC', 'Method of analysis: mobile phase acetonitrile and buffer (20 : 80)'],
]
TWO_BATCHES = [       # one stability report, a page for each batch
    ['Stability data of the finished product', 'Long term stability study 30 C / 65 % RH', 'Batch No: AAA111', 'Assay at 3 months: 99.1 %'],
    ['Stability data of the finished product, continued', 'Long term stability study 30 C / 65 % RH', 'Batch No: BBB222', 'Assay at 3 months: 98.7 %'],
]


def pdf_of(tmp_path, doc, stem):
    from dossier_engine import pages
    return pages.merge([make_pdf_lines(tmp_path / f'{stem}{i}.pdf', lines[1:], lines[0]).read_bytes() for i, lines in enumerate(doc)])


def test_one_document_whose_pages_read_as_several_kinds_is_not_cut(tmp_path):
    """The owner's «Specification and Test Method» (12 pages) was proposed as six documents, and a method validation protocol (6 pages)
    as four — its section on the stability of the solutions sent to the stability item: pages that begin in the middle of a sentence,
    each made a document because it spoke of another subject. A part now begins under a title, at «page 1 of N», or at another
    batch's certificate of analysis."""
    from dossier_engine import pages, packs
    pk = packs.load('eda.ctd.nta065.v5')
    r = pages.propose(pdf_of(tmp_path, ONE_DOCUMENT, 'one'), pk)
    assert [x['kind'] for x in r['page_info']] == ['spec', 'validation', 'stability', 'method']      # the pages do read as four kinds
    assert [(p['from'], p['to'], p['kind']) for p in r['parts']] == [(1, 4, 'spec')]                    # …and are one document, of the kind it opens as
    assert [x['starts'] for x in r['page_info']] == [True, False, False, False]
    r = pages.propose(pdf_of(tmp_path, TWO_BATCHES, 'two'), pk)
    assert [(p['from'], p['to'], p['kind']) for p in r['parts']] == [(1, 2, 'stability')]               # a report's page for another batch is not another report
    # a file that does hold several documents — each under its title, two certificates of analysis of two batches — is cut as before
    from test_priority2 import combined
    r = pages.propose(combined(tmp_path), pk)
    assert [(p['from'], p['to'], p['kind']) for p in r['parts']] == [(1, 1, 'licence'), (2, 2, 'pricing'), (3, 3, 'coa'), (4, 5, 'coa')]


def test_such_a_document_stays_whole_on_the_tree_and_can_still_be_cut_by_hand(c, tmp_path):
    did = new(c)
    doc = stage(c, did, 'made-up-spec-and-method.pdf', pdf_of(tmp_path, ONE_DOCUMENT, 'one'))
    prop = c.get(f'/api/dossiers/{did}/documents/{doc}/split', headers=H).json()
    assert prop['pages'] == 4 and len(prop['parts']) == 1                              # nothing for the page to cut on arrival
    w = c.get(f'/api/dossiers/{did}/tree', headers=H).json()['waiting']
    assert len(w) == 1 and w[0]['kind'] == 'spec' and w[0]['place']                    # whole, under the item of the kind it opens as
    r = c.post(f'/api/dossiers/{did}/documents/{doc}/split', json={'starts': [1, 4]}, headers=H)       # the person's own cut is still theirs to make
    assert r.status_code == 201 and [p['filename'] for p in r.json()['parts']] == ['made-up-spec-and-method (p1-3).pdf', 'made-up-spec-and-method (p4).pdf']
