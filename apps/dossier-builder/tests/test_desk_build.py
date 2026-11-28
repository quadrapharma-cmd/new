"""The desk's «build» stage (combined/build.py) on the made-up dossier, as a desk session uses it (desk/WORKER.md): after the
corrections, the open items the company itself issues are listed from eBOX's own copy of the dossier; Claude writes one from its
template (write) and one through its generator (generate), and leaves the rest to the company (cannot) with the reason; every
wrong answer is refused with its reason; finish writes built.json; the eCTD stage puts both documents in the three outputs at
their Egyptian Module 1 elements, ctd.zip and eBOX's copy no longer count them missing, the global check runs on the sequence,
and the worker's summary names what must be signed. Made-up product, made-up data."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
APP = HERE.parent
sys.path.insert(0, str(APP / 'engine'))
sys.path.insert(0, str(HERE))

from dossier_engine.combined.common import Work  # noqa: E402

import combined_fixture  # noqa: E402
from test_decide import NEED  # noqa: E402
from test_desk_worker import decisions_by_session, patch, wk  # noqa: E402

pytestmark = pytest.mark.skipif(bool(NEED), reason=f'tools missing: {NEED}')

COUNTRIES = {"sections": {"date": {"date": "2026-11-28"},
                          "to": "Egyptian Drug Authority — General Administration for Human Pharmaceuticals Registration",
                          "subject": "List of countries where Zentorix film-coated tablets are registered and marketed",
                          "countries": {"rows": [["[…]", "[…]", "[…]", "[…]", "[…]"]]},
                          "signature": {"signatory": "____________________", "signatory_title": "____________________",
                                        "company": "Example Pharma Ltd."}},
             "gaps": [{"what": "Countries of registration and marketing", "why": "not in the dossier's pages",
                       "ar": "دول التسجيل والتسويق غير مذكورة في صفحات الملف"}],
             "sources": {"subject": "pl-ar.pdf"}, "notes": ""}
S_OPTION = {"sections": {"options": {"rows": [["Zentorine", "Example Pharma Ltd., Example City", "3 — full details in Module 3.2.S",
                                                "Not applicable", "Not applicable"]]}}, "gaps": [], "sources": {"options": "3.2.S"}, "notes": ""}
COMPOSITION = {"trade_name": "Zentorix", "dosage_form": "film-coated tablet",
               "components": [{"name": "Zentorine", "function": "active", "qty_mg": 250, "standard": "In-house"},
                              {"name": "Microcrystalline cellulose", "function": "diluent", "qty_mg": 150, "standard": "Ph. Eur."}],
               "signatory": "____________________", "signatory_title": "____________________", "company": "Example Pharma Ltd."}


def bt(w, *args):
    p = subprocess.run([sys.executable, '-m', 'dossier_engine.combined.build', str(w), *map(str, args)], cwd=str(APP / 'engine'),
                       capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout + p.stderr


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp('desk-build')
    combined_fixture.build(root / 'received')
    w = Work(root / 'work')
    assert wk('start', w.root, 'session_test')[0] == 0
    for s in ('read', 'repeats', 'ocr', 'split', 'assemble', 'checks'):
        code, out = wk('stage', w.root, s, *([root / 'received'] if s == 'read' else []))
        assert code == 0, out
    decisions_by_session(w)
    assert wk('mark', w.root, 'decide', 'done', 'اتُّخذت القرارات الخمس.')[0] == 0
    for s in ('fix', 'build'):
        code, out = wk('stage', w.root, s)
        assert code == 0, out
    seen = {'listed': json.loads((w.root / 'build.json').read_text(encoding='utf-8'))}
    seen['list'] = bt(w.root, 'list')
    seen['brief_gen'] = bt(w.root, 'brief', 'M1-31')
    seen['brief_tpl'] = bt(w.root, 'brief', 'M1-15')
    (root / 'countries.json').write_text(json.dumps(COUNTRIES, ensure_ascii=False), encoding='utf-8')
    (root / 'composition.json').write_text(json.dumps(COMPOSITION, ensure_ascii=False), encoding='utf-8')
    (root / 'bad.json').write_text(json.dumps({'sections': {'nothing': 'x'}}), encoding='utf-8')
    (root / 'option.json').write_text(json.dumps(S_OPTION, ensure_ascii=False), encoding='utf-8')
    seen['refused'] = [bt(w.root, 'write', 'M1-31', '@' + str(root / 'countries.json')),      # a generator item: the letter's sections
                       bt(w.root, 'write', 'M1-15', '@' + str(root / 'bad.json')),            # a section the template has not
                       bt(w.root, 'cannot', 'M1-15', 'not written'),                           # a reason not in Arabic
                       bt(w.root, 'brief', 'S-01'),                                            # it has its document: not an open item
                       bt(w.root, 'finish')]                                                   # items still to do
    seen['write'] = bt(w.root, 'write', 'M1-15', '@' + str(root / 'countries.json'))
    seen['generate'] = bt(w.root, 'generate', 'M1-31', '@' + str(root / 'composition.json'))
    rec = json.loads((w.root / 'build.json').read_text(encoding='utf-8'))
    n = next(i for i, x in enumerate(rec['items'], 1) if x['req'] == 'S-15')
    seen['option'] = bt(w.root, 'write', f'#{n}', '@' + str(root / 'option.json'))          # at the head of 3.2.S, the substance's own
    seen['later'] = bt(w.root, 'later', 'P-13', 'يُجمع من صفحات المواصفات؛ يُكتب في تشغيل لاحق.')
    rec = json.loads((w.root / 'build.json').read_text(encoding='utf-8'))
    for n, x in enumerate(rec['items'], 1):
        if x['state'] == 'to do':
            code, out = bt(w.root, 'cannot', f'#{n}', 'لا تذكر صفحات الملف ما يلزم لكتابته؛ تقدّمه الشركة.')
            assert code == 0, out
    seen['finish'] = bt(w.root, 'finish')
    for s in ('ectd', 'report'):
        code, out = wk('stage', w.root, s)
        assert code == 0, out
    code, out = wk('summary', w.root)
    assert code == 0, out
    seen['handed'] = json.loads(out[out.index('{'):])
    seen['patch'] = patch(w.root)
    return w, seen


def test_the_open_items_the_company_issues_are_listed(built):
    w, seen = built
    items = seen['listed']['items']
    by = {x['req']: x for x in items}
    assert seen['listed']['others'] > 0 and len(items) >= 30                       # the other parties' stay in the request letters
    assert by['M1-43']['state'] == 'later'                                           # the cover letter: written at the eCTD stage
    assert 'M1-09' not in by or by['M1-09']['state'] == 'later'                      # the product information: the corrections stage's
    assert 'P-01' not in by                                                          # it has its document: open in eBOX's copy, not missing
    assert by['M5-04']['state'] == 'cannot' and by['R-01']['state'] == 'cannot'    # a study report, a batch record: never written
    assert by['M1-31']['generator'] == 'composition' and by['M1-15']['state'] == 'to do' and not by['M1-15']['generator']
    assert seen['list'][0] == 0 and '#1 ' in seen['list'][1] and 'to do' in seen['list'][1]
    assert 'GENERATOR «composition»' in seen['brief_gen'][1] and '"trade_name": "Zentorix"' in seen['brief_gen'][1]
    assert 'Never invent a number' in seen['brief_tpl'][1] and 'countries [table]' in seen['brief_tpl'][1]
    assert 'BASE DOCUMENTS' in seen['brief_tpl'][1]


def test_wrong_answers_are_refused_with_their_reason(built):
    _, seen = built
    gen, section, english, ambiguous, early = seen['refused']
    assert gen[0] == 2 and 'sections not in the template: date, to, countries' in gen[1]   # a generator item takes the letter's
    assert section[0] == 2 and 'sections not in the template: nothing' in section[1]
    assert english[0] == 2 and 'in formal Arabic' in english[1]
    assert ambiguous[0] == 2 and 'no open item «S-01»' in ambiguous[1]
    assert early[0] == 2 and 'still to do' in early[1]


def test_written_and_generated_then_placed_in_the_three_outputs(built):
    w, seen = built
    assert seen['write'][0] == 0 and 'to be signed by the company' in seen['write'][1] and 'gaps left in it (1)' in seen['write'][1]
    assert seen['generate'][0] == 0 and 'M1-31-composition.pdf' in seen['generate'][1]
    assert seen['option'][0] == 0 and seen['later'][0] == 0
    assert seen['finish'][0] == 0 and seen['finish'][1].startswith('built: 3 ')
    b = json.loads((w.root / 'built.json').read_text(encoding='utf-8'))
    assert {x['req'] for x in b} == {'M1-15', 'M1-31', 'S-15'} and all(Path(x['pdf']).exists() and x['sign'] for x in b)
    index = (w.root / 'ectd' / 'out' / '0000' / 'index.xml').read_text(encoding='utf-8')
    assert 'statement-of-s-part-option' in index and index.count('<m3-2-s-drug-substance ') == index.count('<m3-2-s-drug-substance')
    assert not (w.root / 'build' / 'store').exists()                                # eBOX's copy is made again at the eCTD stage
    reg = (w.root / 'ectd' / 'out' / '0000' / 'm1' / 'eg' / 'eg-regional.xml').read_text(encoding='utf-8')
    assert '<m1-2-8-1-compositcert>' in reg and '<m1-2-4-10-countries>' in reg
    assert (w.root / 'ectd' / 'out' / '0000' / 'm1' / 'eg' / '12-form' / '128-composit' / '1281-compositcert' / 'composition-certificate.pdf').exists()
    e = json.loads((w.root / 'ectd.json').read_text(encoding='utf-8'))
    assert sorted(e['built']) == ['M1-15', 'M1-31', 'S-15@Zentorine (EX)|example pharma ltd., example city'] and e['built_out'] == []
    assert e['validation']['pf_fail'] == 1                                          # the tracking number, as before: the XML stays valid
    e4 = json.loads((w.root / 'ectd40.json').read_text(encoding='utf-8'))
    assert e4['left_out'] == [] and e4['validation']['fail'] == 0
    cz = json.loads((w.root / 'ctdzip.json').read_text(encoding='utf-8'))
    assert len(cz['required_missing']) == 53 and cz['unplaced'] == []                # 56 before the build stage: these three are there
    eb = json.loads((w.root / 'ebox.json').read_text(encoding='utf-8'))
    assert eb['missing_required'] == 53 and not eb['unplaced']


def test_the_global_check_and_what_the_page_says(built):
    w, seen = built
    g = json.loads((w.root / 'ectd.json').read_text(encoding='utf-8'))['global']
    assert g['region'] == 'eg' and list(g['layers'])[0].startswith('1 · ICH') and g['layers'][list(g['layers'])[0]]['fail'] == 0
    assert (w.root / 'global.json').exists() and g['note']['ar']
    s = seen['patch']['summary']
    assert s['built'] == 3 and s['built_to_sign'] == 3 and s['left_to_company'] >= 25 and s['global_failed_rules'] == 1
    assert s['ctd_required_missing'] == 53
    found = json.loads((w.root / 'desk' / 'state.json').read_text(encoding='utf-8'))['needs_found']      # all of them; the page shows the first
    assert any('لم يُكتب في هذا التشغيل' in n and 'P-13' in n for n in found)
    needs = seen['patch']['needs']
    assert any('توقيع الشركة وختمها على' in n and 'M1-31' in n for n in needs)
    assert all(v == 'done' for v in seen['patch']['stages'].values())
    files = seen['handed']['outputs']
    assert any(k.startswith('built:M1-31') for k in files) and any(k.endswith('.docx') for k in files if k.startswith('built:M1-15'))
    rep = (w.root / 'report.json').read_text(encoding='utf-8')
    assert rep
