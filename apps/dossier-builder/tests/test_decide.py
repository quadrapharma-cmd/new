"""The «decide» stage (Claude inside the program) on the made-up dossier, with a stand-in for the Claude API
(tests/claude_script.py): every task's tools reach the decisions file, a wrong decision is refused with its reason (what Claude
would read and correct), the stages run again after the tasks that change them, the cost is counted, and the program goes on
to the eCTD sequence and the reports. No network, no key, no cost."""
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'engine'))
sys.path.insert(0, str(HERE))

from dossier_engine.combined import assemble, checks, decide, ocr, read, repeats, report, split  # noqa: E402
from dossier_engine.combined.common import Work  # noqa: E402

import combined_fixture  # noqa: E402
from claude_script import ScriptedClient  # noqa: E402

NEED = [t for t in ('ocrmypdf', 'tesseract', 'pdftoppm', 'pdftotext', 'soffice') if not shutil.which(t)]
pytestmark = pytest.mark.skipif(bool(NEED), reason=f'tools missing: {NEED}')

SUBST = 'Module 3/3.2.S Zentorine (EX)'
M2 = 'Module 2/2.2 CTD introduction.pdf'
MOCK = 'Module 1 - EU layout as received (for reference)/1.3.2 Mock-ups.pdf'
PIL = [{'t': 'PACKAGE LEAFLET'}, {'h': '1. What Zentorix is'}, {'p': 'Each tablet contains 10 mg of zentorine.'},
       {'rows': [['Zentorine', '10 mg']]}, {'b': 'Keep below 25 °C.'}]
PIL_AR_WRONG = [{'t': 'النشرة الداخلية'}, {'h': '1. ما هو Zentorix'}, {'p': 'يحتوي كل قرص على 20 mg من zentorine.'},
                {'rows': [['Zentorine', '10 mg']]}, {'b': 'يُحفظ في درجة حرارة أقل من 25 °C.'}]
PIL_AR = [dict(b) for b in PIL_AR_WRONG]
PIL_AR[2] = {'p': 'يحتوي كل قرص على 10 mg من zentorine.'}

SCRIPT = {
    'documents': [
        [('set_names', {'substances': {'Zentorine-Drug Substance': 'Zentorine (EX)'}, 'product': 'Zentorix tablets (EX)'})],
        [('place_pages', {'pages': '100-120', 'path': f'{SUBST}/x.pdf', 'ctd': '3.2.S.2.3', 'title': 'x'}),     # no such pages
         ('leave_out', {'pages': '30', 'why': 'cover'})],                                                     # a repeated page
        [('place_pages', {'pages': '20-29', 'path': f'{SUBST}/3.2.S.2 Manufacture/3.2.S.2.3 Control of materials.pdf',
                          'ctd': '3.2.S.2.3', 'title': '3.2.S.2.3 Control of materials (Zentorine)',
                          'note': 'Annexure 1 is cited in 3.2.S.2.3.'}),
         ('finish', {'summary': 'Annexure 1 filed under 3.2.S.2.3.'})],
    ],
    'product': [
        [('set_envelope', {'applicant': 'Example Pharma Ltd.', 'invented_name': 'Zentorix', 'inn': ['zentorine'],
                           'registration': 'imported-finished', 'marketing': 'local',
                           'description': 'Initial marketing authorisation application of Zentorix 10 mg tablets'}),
         ('set_product', {'product_name': 'Zentorix', 'dosage_form': 'Film-coated tablet', 'manufacturer': 'Example Pharma Ltd., Example City',
                          'indication': 'example indication', 'substances': [{'name': 'Zentorine (EX)', 'folder': 'zentorine-ex',
                                                                              'substance': 'zentorine'}],
                          'product_folder': 'zentorix', 'indication_folder': 'example-indication'}),
         ('set_product_card', {'row_count': 3, 'rows': [['الاسم', 'Zentorix 10 mg', 'ص 46'], ['المادة الفعالة', 'zentorine 10 mg', 'ص 14']]}),
         ('set_cover', {'subject_html': 'eCTD sequence 0000 of <b>Zentorix</b>', 'opening': 'Please find enclosed eCTD sequence 0000.',
                        'product': [['Name', 'Zentorix 10 mg film-coated tablets']], 'content': ['Module 1 (EG)', 'Module 2', 'Module 3']})],
        [('set_product_card', {'row_count': 2, 'rows': [['الاسم', 'Zentorix 10 mg', 'ص 46'], ['المادة الفعالة', 'zentorine 10 mg', 'ص 14']]}),
         ('set_eg_m1', {'intro': 'Module 1 الوارد مكتوب على نموذج الاتحاد الأوروبي.', 'row_count': 1,
                        'rows': [['1.1.1 نموذج الطلب والتعهد', 'غير موجود', 'الشركة']]}),
         ('set_titles', {'title': 'ملف تسجيل Zentorix', 'subtitle': 'بناه البرنامج', 'ectd_title': 'ملف eCTD لـ Zentorix',
                         'ectd_subtitle': 'التسلسل 0000'}),
         ('add_to_confirm', {'item': 'المتقدم', 'value': 'Example Pharma Ltd.', 'why': 'يُغيَّر إن كان المتقدم الوكيل المصري'}),
         ('add_company_gap', {'item': 'شهادة GMP', 'where': 'الوحدة 1، البند 1.2.4', 'who': 'الشركة المصنعة'}),
         ('finish', {'summary': 'Envelope, product, cover, card, Module 1.'})],
    ],
    'pi': [
        [('write_pi_document', {'key': 'PIL_AR', 'title': 'النشرة', 'ectd_title': 'Package leaflet (Arabic)', 'block_count': 5,
                                'blocks': PIL_AR})],                                                         # before the English
        [('write_pi_document', {'key': 'SPC', 'title': 'Summary of Product Characteristics', 'ectd_title': 'SmPC (English)',
                                'header': 'Zentorix 10 mg film-coated tablets', 'creator': 'Example Pharma Ltd.', 'block_count': 3,
                                'blocks': [{'t': 'SUMMARY OF PRODUCT CHARACTERISTICS'}, {'h': '1. NAME'}, {'p': 'Zentorix 10 mg tablets'}]}),
         ('write_pi_document', {'key': 'PIL', 'title': 'Package Leaflet', 'ectd_title': 'Package leaflet (English)', 'block_count': 5,
                                'blocks': PIL})],
        [('write_pi_document', {'key': 'PIL_AR', 'title': 'النشرة الداخلية', 'ectd_title': 'Package leaflet (Arabic)', 'block_count': 5,
                                'blocks': PIL_AR_WRONG})],                                                   # a number changed
        [('write_pi_document', {'key': 'PIL_AR', 'title': 'النشرة الداخلية', 'ectd_title': 'Package leaflet (Arabic)', 'block_count': 5,
                                'creator_ar': 'الترجمة العربية للنشرة', 'blocks': PIL_AR}),
         ('add_pi_change', {'where': 'SmPC 2', 'old': '1.25 mcg', 'new': '1.25 mg', 'source': '3.2.P.1 (p 14)'}),
         ('correct_in_pdf', {'doc': M2, 'page': 1, 'old': '1.25 mcg', 'new': '1.25 mcgx', 'note': 'unit'})],      # adds a character
        [('correct_in_pdf', {'doc': M2, 'page': 1, 'old': '1.25 mcg', 'new': '1.25 mg', 'note': 'corrected: 1.25 mcg -> 1.25 mg'}),
         ('add_translation_note', {'text': 'تُرجمت النشرة فقرةً فقرة.'}),
         ('finish', {'summary': 'SmPC, leaflet EN/AR, one correction.'})],
    ],
    'review': [
        [('add_finding', {'severity': 'major', 'text': 'لا تذكر النشرة شروط التخزين كما في 3.2.P.8.', 'where': 'ص 18',
                          'action': 'توحيد شروط التخزين.'}),
         ('finish', {'summary': 'One finding.'})],
    ],
    'sequence': [
        [('set_leaf', {'doc': M2, 'file': 'Bad Name.pdf'}),                                                   # not an ICH file name
         ('set_leaf', {'doc': M2, 'title': 'Introduction to the dossier'}),
         ('set_m1_leaf', {'doc': MOCK, 'title': 'Mock-ups of the current packs - Egyptian artwork to follow'}),
         ('finish', {'summary': 'Two titles.'})],                                                 # refused: a decision of its turn was
        [('finish', {'summary': 'Two titles; the bad file name dropped.'})],
    ],
}


@pytest.fixture(scope='module')
def done(tmp_path_factory):
    root = tmp_path_factory.mktemp('decide')
    combined_fixture.build(root / 'received')
    w = Work(root / 'work')
    read.run(root / 'received', w)
    repeats.run(w)
    ocr.run(w)
    split.run(w)
    assemble.run(w)
    checks.run(w)
    dec = {'ctd_folder': 'Zentorix dossier', 'ectd': {'today': '2026-11-22'}}
    (w.root / 'dossier.json').write_text(json.dumps(dec), encoding='utf-8')
    (w.root / 'decide.json').write_text('{}', encoding='utf-8')         # the program's own start, not a person's decisions
    assemble.run(w)
    client = ScriptedClient(SCRIPT, w)
    rec = decide.run(w, client=client, budget_usd=5)
    return w, client, rec


def test_every_task_finished_and_costed(done):
    w, client, rec = done
    assert rec['finished'] and all(rec['tasks'][t]['finished'] for t in decide.TASKS)
    calls = sum(len(v) for v in SCRIPT.values())
    assert rec['budget']['calls'] == calls
    assert abs(rec['budget']['spent_usd'] - calls * 0.0158) < 1e-6                 # 1200 in, 300 out, 800 cache write, 5000 read
    log = (w.root / 'decide' / 'log.jsonl').read_text(encoding='utf-8').splitlines()
    assert any('"tool": "place_pages"' in l and '"ok": true' in l for l in log)


def test_wrong_decisions_are_refused_with_the_reason(done):
    _, client, _ = done
    errs = client.errors()
    assert any('do not exist' in e for e in errs)                                   # pages beyond the dossier
    assert any('received twice' in e for e in errs)                                 # a page of the repeated block
    assert any('row_count' in e for e in errs)                                      # a list cut short
    assert any('English leaflet (PIL) first' in e for e in errs)
    assert any('الأرقام' in e for e in errs)                                          # the translation's numbers
    assert any('تحذف ولا تضيف' in e for e in errs)                                    # an edit that adds a character
    assert any('lower case letters' in e for e in errs)                             # a file name ICH does not allow
    assert any(e.startswith('Not finished: 1 of') for e in errs)                     # finish with a refused decision in its turn
    assert len(errs) == 8


def test_decisions_reach_the_program(done):
    w, _, _ = done
    dec = w.decisions()
    assert dec['names']['product'] == 'Zentorix tablets (EX)'
    assert dec['plan'] == [{'pages': '20-29', 'path': f'{SUBST}/3.2.S.2 Manufacture/3.2.S.2.3 Control of materials.pdf',
                            'ctd': '3.2.S.2.3', 'title': '3.2.S.2.3 Control of materials (Zentorine)'}]
    plan = w.load('plan.json')
    annex = next(d for d in plan['docs'] if d['ctd'] == '3.2.S.2.3')
    assert annex['pages'] == list(range(20, 30)) and annex['by'] == 'decision'
    assert all(d['path'].startswith(SUBST) for d in plan['docs'] if d['ctd'].startswith('3.2.S'))
    assert dec['ectd']['envelope']['registration'] == 'imported-finished' and dec['ectd']['envelope']['identifier']
    assert dec['report']['company_gaps'][0][1] == 'Module 1، البند 1.2.4'           # the glossary: «Module N», never «الوحدة N»
    assert [x['blocks'] for x in dec['pi']['documents']] == ['SPC', 'PIL', 'PIL_AR']
    assert dec['fixes'] == [{'doc': M2, 'page': 1, 'edits': [['1.25 mcg', '1.25 mg']], 'note': 'corrected: 1.25 mcg -> 1.25 mg'}]
    assert dec['findings'][0]['rule'] == 'reviewer'
    assert dec['ectd']['leaves'][M2] == {'title': 'Introduction to the dossier'}


def test_the_sequence_and_the_reports(done):
    w, _, _ = done
    e = w.load('ectd.json')
    failed = [r['rule'] for r in w.load('validation.json') if not r['ok'] and r['kind'] == 'P/F']
    assert failed == ['EG-PF-E06']                                                  # only the tracking number EDA gives
    leaf = next(l for l in e['leaves'] if l['doc'] == M2)
    assert leaf['title'] == 'Introduction to the dossier' and leaf['source'].endswith('.fixed.pdf')
    assert any(x[3] == 'Mock-ups of the current packs - Egyptian artwork to follow' for x in e['m1'])
    assert any(x[2].endswith('ar/pl.pdf') for x in e['m1'])
    out = report.run(w)
    assert Path(out['ctd']['pdf']).stat().st_size > 5000 and Path(out['ectd']['pdf']).exists()


def test_without_a_key_the_program_goes_on(tmp_path, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    w = Work(tmp_path / 'w')
    rec = decide.run(w)
    assert rec['skipped'] == 'no key' and w.load('decide.json')['skipped'] == 'no key'


def test_a_persons_decisions_are_left_as_they_are(tmp_path):
    w = Work(tmp_path / 'w')
    (w.root / 'dossier.json').write_text(json.dumps({'plan': [{'pages': '1', 'drop': 'cover'}]}), encoding='utf-8')
    assert decide.run(w, client=ScriptedClient({}))['skipped'] == 'decisions made by a person'
