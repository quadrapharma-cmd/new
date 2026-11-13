"""Suite module 2 (updates list, item 11): the authority's letter is read when it is added — its numbered questions and the time it
gives become questions with a due date; each question gets its answer and the reply letter is written from them; commitments; one
list of deadlines with the overdue first."""
import io, json
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine.app.api import create_app

H = {'X-DB': '1'}


@pytest.fixture()
def c(tmp_path):
    return TestClient(create_app(tmp_path / 'ws', auth_enabled=False))


def product(c):
    r = c.post('/api/suite/products', json={'name': 'Dermacure', 'dosage_form': 'topical powder'}, headers=H)
    assert r.status_code == 201, r.text
    return r.json()['id']


def letter_pdf(tmp_path):
    return make_pdf_lines(tmp_path / 'eda.pdf', ['Egyptian Drug Authority', 'Subject: Comments on the registration file of Dermacure',
                                                 'Please submit the following within 30 days:', '1- Submit the updated stability data for 3 batches',
                                                 '2- Clarify the source of Glycine and its GMP certificate.', '3- Provide the CoA of the API batch used.',
                                                 'Sincerely'], 'EDA letter').read_bytes()


def test_a_letter_is_read_into_its_questions_and_due_date(c, tmp_path):
    pid = product(c)
    meta = {'direction': 'in', 'product_id': pid, 'received': '2026-11-01', 'ref_no': 'EDA/2026/123'}
    r = c.post('/api/suite/letters', data={'meta': json.dumps(meta)}, files={'file': ('eda.pdf', letter_pdf(tmp_path), 'application/pdf')}, headers=H)
    assert r.status_code == 201, r.text
    let = r.json()
    assert let['subject'] == 'Comments on the registration file of Dermacure' and let['due'] == '2026-12-01' and let['read'] == {'questions': 3, 'due': '2026-12-01'}
    assert [q['n'] for q in let['questions']] == [1, 2, 3] and 'Glycine' in let['questions'][1]['text'] and all(q['due'] == '2026-12-01' for q in let['questions'])
    assert let['product'] == 'Dermacure' and c.get(f"/api/suite/letters/{let['id']}/file", headers=H).content[:4] == b'%PDF'
    lst = c.get('/api/suite/letters', params={'product': pid}, headers=H).json()
    assert len(lst) == 1 and lst[0]['open_questions'] == 3


def test_answers_close_the_letter_and_write_the_reply(c, tmp_path):
    pid = product(c)
    let = c.post('/api/suite/letters', data={'meta': json.dumps({'direction': 'in', 'product_id': pid, 'received': '2026-11-01'})},
                 files={'file': ('eda.pdf', letter_pdf(tmp_path), 'application/pdf')}, headers=H).json()
    assert c.post(f"/api/suite/letters/{let['id']}/reply", json={}, headers=H).json()['detail']['code'] == 'E-ANSWERS'   # not before every answer
    for q, a in zip(let['questions'], ['Attached in 3.2.P.8.', 'Tianjin Tianyao; GMP attached.', 'Attached in 1.2.3.1.']):
        r = c.put(f"/api/suite/questions/{q['id']}", json={'answer': a}, headers=H).json()
        assert r['status'] == 'drafted'
        c.put(f"/api/suite/questions/{q['id']}", json={'status': 'answered'}, headers=H)
    assert c.get(f"/api/suite/letters/{let['id']}", headers=H).json()['status'] == 'answered'
    r = c.post(f"/api/suite/letters/{let['id']}/reply", json={'lang': 'en', 'company': 'Example Pharm Co.'}, headers=H)
    assert r.status_code == 200 and r.content[:2] == b'PK'
    import docx
    text = '\n'.join(cell.text for t in docx.Document(io.BytesIO(r.content)).tables for row in t.rows for cell in row.cells)
    assert 'Clarify the source of Glycine' in text and 'Tianjin Tianyao; GMP attached.' in text
    out = c.post('/api/suite/letters', data={'meta': json.dumps({'direction': 'out', 'subject': 'Response to comments', 'reply_to': let['id']})}, headers=H).json()
    assert out['direction'] == 'out' and out['questions'] == []


def test_commitments_and_one_list_of_deadlines(c, tmp_path):
    pid = product(c)
    today = date.today()
    late = (today - timedelta(days=3)).isoformat()
    soon = (today + timedelta(days=5)).isoformat()
    later = (today + timedelta(days=60)).isoformat()
    let = c.post('/api/suite/letters', data={'meta': json.dumps({'direction': 'in', 'product_id': pid, 'subject': 'Variation questions', 'due': soon})}, headers=H).json()
    q = c.post(f"/api/suite/letters/{let['id']}/questions", json={'text': 'Justify the new pack size.'}, headers=H).json()
    assert q['due'] == soon and q['n'] == 1
    c1 = c.post('/api/suite/commitments', json={'text': 'Submit 12-month stability data of the first 3 batches', 'due': late, 'product_id': pid}, headers=H).json()
    c.post('/api/suite/commitments', json={'text': 'Inform EDA of the CEP renewal', 'due': later}, headers=H)
    d = c.get('/api/suite/deadlines', headers=H).json()
    assert [(x['kind'], x['state']) for x in d] == [('commitment', 'overdue'), ('question', 'soon'), ('commitment', 'later')]
    assert d[0]['days'] == -3 and d[0]['product'] == 'Dermacure'
    c.put(f"/api/suite/commitments/{c1['id']}", json={'status': 'done', 'evidence': 'Submitted 10/11/2026'}, headers=H)
    c.put(f"/api/suite/questions/{q['id']}", json={'answer': 'Justified.', 'status': 'answered'}, headers=H)
    assert [x['kind'] for x in c.get('/api/suite/deadlines', headers=H).json()] == ['commitment']
    assert c.put(f"/api/suite/commitments/{c1['id']}", json={'status': 'maybe'}, headers=H).status_code == 422
    assert c.post('/api/suite/letters', data={'meta': json.dumps({'direction': 'sideways', 'subject': 'x'})}, headers=H).json()['detail']['code'] == 'E-DIRECTION'
    assert c.post('/api/suite/letters', data={'meta': json.dumps({'subject': 'x', 'due': '31/12/2026'})}, headers=H).json()['detail']['code'] == 'E-DATE'
    assert c.delete(f"/api/suite/letters/{let['id']}", headers=H).json() == {'ok': True}
    assert c.get(f"/api/suite/letters/{let['id']}", headers=H).status_code == 404


def test_an_arabic_letter_gives_its_questions_and_time(tmp_path):
    from dossier_engine.app.suite_m2 import questions_in, due_in
    text = 'برجاء استيفاء الملاحظات التالية خلال ١٥ يوم:\n١- تقديم دراسة الثبات المحدثة للتشغيلات الثلاثة\n٢- توضيح مصدر المادة الفعالة وشهادة الـ GMP'
    assert [q['n'] for q in questions_in(text)] == [1, 2] and 'مصدر المادة' in questions_in(text)[1]['text']
    assert due_in(text, '2026-11-01') == '2026-11-16' and due_in('within 2 months', '2026-11-30') == '2027-01-30'
    assert questions_in('Dated 12/11/2026. Total 3 pages.') == []                          # no numbered question, none made up
