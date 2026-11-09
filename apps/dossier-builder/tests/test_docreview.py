"""One document against its rules: the rubric (pack questions of its item + general document rules), the rules run, tracked-change
amendments of a Word document, amendment memos, and the Assistant doing review → record → amend → memo through its tools."""
import io, json, re, time, zipfile
from types import SimpleNamespace
import pytest
from docx import Document
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine.app.api import create_app
from dossier_engine.assistant import runner
from dossier_engine.generate import amend
from test_assistant import FakeClient, msg, _results, _last_user, _wait

PROFILE = {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new', 'admin_route': 'topical', 'leaflet': 'english', 'dosage_specifics': [],
           'apis': [{'name': 'Neomycin Sulphate', 'manufacturer': 'Sichuan Example', 'option': 'FULL'}]}


def _dossier(c):
    r = c.post('/api/dossiers', json={'name': 'Dermacure 10 g', 'profile': PROFILE, 'product': {'name': 'Dermacure', 'dosage_form': 'Topical Powder'}, 'envelope': {'applicant': 'EXAMPLE PHARM'}})
    assert r.status_code in (200, 201), r.text
    return r.json()['id']


def _slot(c, did, **cond):
    for s in c.get(f'/api/dossiers/{did}/board').json()['slots']:
        if s['status'] != 'not_applicable' and all(s.get(k) == v for k, v in cond.items()):
            return s
    raise AssertionError(f'no slot {cond}')


def _docx(paragraphs):
    d = Document()
    for p in paragraphs:
        d.add_paragraph(p)
    t = d.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = 'Test', 'Limit'
    out = io.BytesIO()
    d.save(out)
    return out.getvalue()


def _xml(docx_bytes):
    return zipfile.ZipFile(io.BytesIO(docx_bytes)).read('word/document.xml').decode('utf-8')


def test_rubric_and_rules_run_on_a_cover_letter(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = _dossier(c)
    slot = _slot(c, did, slot_id='M1-43')                                           # cover letter: the pack asks for the completeness statement
    weak = make_pdf_lines(tmp_path / 'cover1.pdf', ['Cover letter', 'Dermacure Topical Powder registration', 'We submit the dossier.'], 'Cover')
    r = c.post(f"/api/dossiers/{did}/slots/{slot['slot_id']}/documents", files={'file': ('cover.pdf', weak.read_bytes(), 'application/pdf')})
    assert r.status_code == 201, r.text
    doc = r.json()['id']
    rb = c.get(f'/api/dossiers/{did}/documents/{doc}/rubric').json()
    ids = {x['id'] for x in rb['rules']}
    assert 'SC-COVER-01' in ids and {'DOC-TEXT', 'DOC-NAME', 'DOC-SIGN', 'DOC-DATE'} <= ids and 'DOC-VALID' not in ids   # company document, not a certificate
    assert all(x['source'] for x in rb['rules']) and rb['document']['is_docx'] is False
    rv = c.post(f'/api/dossiers/{did}/documents/{doc}/review').json()
    by = {f['rule']: f for f in rv['findings']}
    assert by['SC-COVER-01']['verdict'] == 'deficient' and 'true, complete and correct' in by['SC-COVER-01']['change']['en']
    assert by['DOC-TEXT']['verdict'] == 'adequate' and by['DOC-NAME']['verdict'] == 'adequate' and by['DOC-NAME']['where'][0]['page'] == 1
    assert by['DOC-SIGN']['verdict'] == 'deficient' and by['DOC-DATE']['verdict'] == 'deficient' and rv['verdict'] == 'deficient' and rv['origin'] == 'rules'
    good = make_pdf_lines(tmp_path / 'cover2.pdf', ['Cover letter, 12 March 2025', 'Dermacure Topical Powder', 'We confirm that the submitted data are true, complete and correct.',
                                                    'Signature: Dr. Example, Regulatory Affairs Manager'], 'Cover')
    r = c.post(f"/api/dossiers/{did}/slots/{slot['slot_id']}/documents", files={'file': ('cover.pdf', good.read_bytes(), 'application/pdf')}, data={'replaces': doc})
    doc2 = r.json()['id']
    rv2 = c.post(f'/api/dossiers/{did}/documents/{doc2}/review').json()
    by2 = {f['rule']: f for f in rv2['findings']}
    assert by2['SC-COVER-01']['verdict'] == 'adequate' and by2['SC-COVER-01']['where'][0]['page'] == 1 and by2['DOC-SIGN']['verdict'] == 'adequate' and by2['DOC-DATE']['verdict'] == 'adequate'
    g = c.get(f'/api/dossiers/{did}/documents/{doc2}/review').json()
    assert g['latest']['id'] == rv2['id'] and g['history'] == 1 and g['rules'] == len(rb['rules']) and g['memos'] == []
    audit = c.get(f'/api/dossiers/{did}/audit').json()
    assert sum(1 for a in audit if a['event'] == 'document.reviewed') == 2


def test_tracked_change_amendments_and_memo(tmp_path):
    src = _docx(['Product: Dermacure', 'Shelf life: 24 months', 'Store below 25°C', 'Store below 25°C in the original pack'])
    out, log = amend.apply_edits(src, [{'op': 'replace', 'find': 'Shelf life: 24 months', 'text': 'Shelf life: 36 months', 'rule': 'P-16', 'reason': 'per the long-term stability data'},
                                       {'op': 'insert_after', 'find': 'Store below 25°C in the original pack', 'text': 'Protect from light.', 'rule': 'LB-STOR-02', 'reason': 'photolabile API'},
                                       {'op': 'delete', 'find': 'Product: Dermacure', 'rule': 'DOC-DUP', 'reason': 'duplicated heading'}])
    x = _xml(out)
    assert x.count('<w:ins ') >= 3 and x.count('<w:del ') >= 2 and 'w:delText' in x and 'Shelf life: 24 months' in x and 'Shelf life: 36 months' in x and 'Protect from light.' in x
    assert 'w:author="Dossier Builder Assistant"' in x and [l['op'] for l in log] == ['replace', 'insert_after', 'delete'] and log[0]['before'] == 'Shelf life: 24 months'
    assert 'Change log' in x                                                           # appended as a plain final section
    with pytest.raises(amend.AmendError):                                              # «below 25°C» is inside two paragraphs: ambiguous
        amend.apply_edits(src, [{'op': 'replace', 'find': 'below 25°C', 'text': 'x'}])
    assert amend.apply_edits(src, [{'op': 'replace', 'find': 'Store below 25°C', 'text': 'x'}])[1][0]['before'] == 'Store below 25°C'   # an exact paragraph wins
    with pytest.raises(amend.AmendError):
        amend.apply_edits(src, [{'op': 'replace', 'find': 'not in the document', 'text': 'x'}])
    p = amend.memo([{'rule': 'P-16', 'where': 'p.2 §4', 'finding': 'shelf life 24 months', 'change': '36 months per stability'}], 'spec.pdf', 'Dermacure', tmp_path / 'memo.docx', lang='ar')
    txt = '\n'.join(par.text for par in Document(str(p)).paragraphs) + ' '.join(c.text for t in Document(str(p)).tables for r in t.rows for c in r.cells)
    assert 'مذكرة تعديل' in txt and 'spec.pdf' in txt and 'P-16' in txt and '36 months' in txt


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    fake = FakeClient([])
    runner.CLIENT_FACTORY = lambda key: fake
    try:
        c = TestClient(create_app(tmp_path / 'ws'))
        c.put('/api/assistant/settings', json={'api_key': 'sk-ant-test-0123456789abcdef'})
        yield c, fake
    finally:
        runner.CLIENT_FACTORY = None


def test_assistant_reviews_amends_and_writes_a_memo(app_client, tmp_path):
    c, fake = app_client
    did = _dossier(c)
    tech = _slot(c, did, doc_class='company_technical')
    r = c.post(f"/api/dossiers/{did}/slots/{tech['slot_id']}/documents",
               files={'file': ('spec.docx', _docx(['Dermacure Topical Powder — specification', 'Shelf life: 24 months', 'Store below 25°C']), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')})
    assert r.status_code == 201, r.text
    word = r.json()['id']
    cover = _slot(c, did, slot_id='M1-43')
    pdf = make_pdf_lines(tmp_path / 'cover.pdf', ['Cover letter', 'Dermacure'], 'Cover')
    pdfdoc = c.post(f"/api/dossiers/{did}/slots/{cover['slot_id']}/documents", files={'file': ('cover.pdf', pdf.read_bytes(), 'application/pdf')}).json()['id']

    def s1(kw):
        return msg([{'type': 'tool_use', 'id': 'r1', 'name': 'get_document_rubric', 'input': {'doc_id': word}}], 'tool_use')

    def s2(kw):
        rb = json.loads(_results(kw)['r1']['content'])
        assert rb['how_to_amend'].startswith('amend_document') and any(x['id'] == 'DOC-SIGN' for x in rb['rules'])
        return msg([{'type': 'tool_use', 'id': 'r2', 'name': 'record_document_review', 'input': {'doc_id': word, 'summary': 'Shelf life inconsistent with the stability data; unsigned.',
                     'findings': [{'rule': 'DOC-SIGN', 'verdict': 'deficient', 'finding': {'en': 'No signature block.', 'ar': 'لا يوجد توقيع.'}, 'change': {'en': 'Add signatory, title, signature.', 'ar': 'أضف الموقّع وصفته وتوقيعه.'}},
                                  {'rule': 'DOC-NAME', 'verdict': 'adequate', 'where': [{'page': 1, 'excerpt': 'Dermacure Topical Powder — specification'}]},
                                  {'rule': 'DOC-DATE', 'verdict': 'deficient', 'severity': 'minor', 'finding': {'en': 'Undated.', 'ar': 'بلا تاريخ.'}, 'change': {'en': 'Date it.', 'ar': 'أرِّخه.'}}]}},
                    {'type': 'tool_use', 'id': 'r3', 'name': 'amend_document', 'input': {'doc_id': word, 'rationale': 'answers DOC-SIGN and the shelf-life finding',
                     'edits': [{'op': 'replace', 'find': 'Shelf life: 24 months', 'text': 'Shelf life: 36 months', 'rule': 'P-16', 'reason': 'long-term data support 36 months'},
                               {'op': 'insert_after', 'find': 'Store below 25°C', 'text': 'Signature: ____________  Name / title: ____________  Date: ________', 'rule': 'DOC-SIGN', 'reason': 'signature block'}]}}], 'tool_use')

    def s3(kw):
        res = _results(kw)
        assert not res['r2'].get('is_error') and not res['r3'].get('is_error'), res
        return msg([{'type': 'tool_use', 'id': 'r4', 'name': 'amendment_memo', 'input': {'doc_id': pdfdoc, 'lang': 'ar', 'rationale': 'PDF without a Word source',
                     'items': [{'rule': 'SC-COVER-01', 'where': 'p.1', 'finding': 'no completeness statement', 'change': 'add «true, complete and correct»'}]}},
                    {'type': 'tool_use', 'id': 'r5', 'name': 'amend_document', 'input': {'doc_id': pdfdoc, 'rationale': 'x', 'edits': [{'op': 'replace', 'find': 'Cover letter', 'text': 'y'}]}}], 'tool_use')

    def s4(kw):
        res = _results(kw)
        assert not res['r4'].get('is_error') and res['r5'].get('is_error') and 'amendment_memo' in res['r5']['content']
        return msg([{'type': 'text', 'text': 'راجعت المواصفة وعدّلتها بتغييرات متتبعة، وكتبت مذكرة تعديل لخطاب التغطية.'}])
    fake.steps = [s1, s2, s3, s4]
    r = c.post(f'/api/dossiers/{did}/assistant/messages', data={'text': 'راجع المواصفة وعدّلها حسب القواعد'})
    assert r.status_code == 201, r.text
    s = _wait(c, did, states=('done', 'error'))
    assert s['run']['status'] == 'done', s['run']
    g = c.get(f'/api/dossiers/{did}/documents/{word}/review').json()
    assert g['latest']['origin'] == 'assistant' and g['latest']['verdict'] == 'deficient' and g['latest']['counts'] == {'deficient': 2, 'adequate': 1}
    assert g['latest']['findings'][0]['title']['en'] == 'Signed' and g['latest']['findings'][0]['change']['ar'] == 'أضف الموقّع وصفته وتوقيعه.'
    slot = _slot(c, did, slot_id=tech['slot_id'])
    assert len(slot['documents']) == 1 and slot['documents'][0]['version'] == 2 and slot['documents'][0]['meta']['amended_from'] == word
    new = slot['documents'][0]
    assert new['meta']['draft_unsigned'] and len(new['meta']['change_log']) == 2 and new['meta']['change_log'][0]['rule'] == 'P-16'
    body = c.get(f"/api/dossiers/{did}/documents/{new['id']}/file").content
    assert b'w:ins' in _xml(body).encode() and 'Shelf life: 36 months' in _xml(body)
    m = c.get(f'/api/dossiers/{did}/documents/{pdfdoc}/review').json()['memos']
    assert len(m) == 1 and m[0]['filename'].startswith('Amendment memo')
    memo_bytes = c.get(f"/api/dossiers/{did}/documents/{m[0]['id']}/file").content
    assert 'SC-COVER-01' in ' '.join(cell.text for t in Document(io.BytesIO(memo_bytes)).tables for row in t.rows for cell in row.cells)
    audit = c.get(f'/api/dossiers/{did}/audit').json()
    assert {a['event'] for a in audit if a['actor'] == 'claude'} >= {'document.reviewed', 'document.added', 'document.staged', 'assistant.tool'}
