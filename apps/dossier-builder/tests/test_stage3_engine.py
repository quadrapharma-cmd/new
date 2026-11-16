"""eBOX stage 3 (16/11/2026), the engine's side of stations 6 and 7: a tree point is closed or open and says why; the vault's overview
counts what the sign is made of; a document that has no pages to draw gives its words; a waiting file takes the place of the
document it is a newer copy of; what is missing is listed under who issues it, and one request covers one party; a certificate is
judged valid on the target submission date; the validity date read in «القراءة والفرز» stays with the file. Made-up files."""
import io
import json
from datetime import date, timedelta

from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf_lines

H = {'X-DB': '1'}
NEW = {'name': 'Dermacure (made up)', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new',
       'apis': [{'name': 'Exampletine', 'manufacturer': 'Example API Co.', 'option': 'CEP'}]},
       'product': {'name': 'Dermacure 20 mg', 'dosageform': 'cream', 'manufacturer': 'Example Pharm'},
       'envelope': {'applicant': 'Example Pharm', 'invented_name': 'Dermacure'}}
GMP = ['Certificate of GMP compliance of a manufacturer', 'Example Pharm, 1 Made-up Street', 'Certificate No. GMP-0001', 'made up for a test']
SPEC = ['Specification of the finished product', '3.2.P.5.1 Specification', 'Appearance: white cream']
COA = ['Certificate of Analysis', 'Exampletine', 'Batch No.: 240101', 'Assay 99.6 %']


def client(tmp_path, **env):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', headers=H, json={**NEW, 'envelope': {**NEW['envelope'], **env}}).json()['id']
    return c, did


def board(c, did):
    return c.get(f'/api/dossiers/{did}/board', headers=H).json()


def slot(c, did, ctd):
    return next(s for s in board(c, did)['slots'] if s['ctd'] == ctd and s['level'] in ('R', 'O'))


def put(c, did, slot_id, tmp_path, name, lines):
    f = make_pdf_lines(tmp_path / name, lines, name)
    r = c.post(f'/api/dossiers/{did}/slots/{slot_id}/documents', headers=H, files={'file': (name, f.read_bytes())}, data={'meta': '{}'})
    assert r.status_code == 201, r.text[:300]
    return r.json()


def staged(c, did, tmp_path, name, lines, **said):
    f = make_pdf_lines(tmp_path / name, lines, name)
    r = c.post(f'/api/dossiers/{did}/unplaced', headers=H, files={'files': (name, f.read_bytes())}, data={'meta': json.dumps({name: said})})
    assert r.status_code == 201, r.text[:300]
    return r.json()[0]['id']


def test_a_tree_point_is_closed_or_open_and_says_why(tmp_path):
    c, did = client(tmp_path)
    b = board(c, did)
    req = [s for s in b['slots'] if s['level'] == 'R']
    made = sum(1 for s in req if s['status'] == 'auto')                         # what the program makes itself at the export
    assert b['points'] == {'required': len(req), 'closed': made, 'open': len(req) - made}
    assert all(s['point'] == 'open' and s['open_why'] == ['missing'] for s in req if s['status'] != 'auto')
    assert all(s['point'] is None and s['open_why'] == [] for s in b['slots'] if s['level'] == 'O')      # nothing asks for it: not a point to close
    assert all('point' in s for s in b['slots'])
    # a document in its item, not prepared yet: open, and that is why
    doc = put(c, did, 'P-09', tmp_path, 'made-up-spec.pdf', SPEC)
    s = slot(c, did, '3.2.P.5.1')
    assert s['point'] == 'open' and 'not_prepared' in s['open_why'] and 'missing' not in s['open_why']
    assert s['documents'][0]['prep']['prepared'] is False and s['documents'][0]['prep']['ready'] is False
    # prepared: closed when nothing is left on it, open with what is left otherwise — the same word the vault says
    r = c.post(f'/api/dossiers/{did}/prepare/{doc["id"]}', headers=H, json={}).json()
    s = slot(c, did, '3.2.P.5.1')
    pr = s['documents'][0]['prep']
    assert pr['prepared'] is True and pr['ready'] is r['state']['ready']
    assert (s['point'] == 'closed') == (pr['ready'] and not s['open_why'])
    ov = c.get(f'/api/dossiers/{did}/prepare', headers=H).json()
    mine = next(x for x in ov['placed'] if x['slot_id'] == 'P-09')
    assert mine['point'] == s['point'] and mine['bucket'] == ('ready' if pr['ready'] else 'needs_you' if (pr['needs_you'] or pr['check']) else 'not_prepared')
    assert board(c, did)['points']['closed'] == made + (1 if s['point'] == 'closed' else 0)
    # asked of its issuer: still open, and «waiting» is said beside the reason
    gmp = slot(c, did, '1.2.4.1')
    assert c.post(f'/api/dossiers/{did}/slots/{gmp["slot_id"]}/request', headers=H,
                  json={'issuer': 'Example Authority', 'signatory': 'A. Tester', 'signatory_title': 'Regulatory Affairs'}).status_code == 201
    assert slot(c, did, '1.2.4.1')['open_why'] == ['missing', 'waiting']
    # the proposed tree says the same of every point
    t = c.get(f'/api/dossiers/{did}/tree', headers=H).json()
    assert {x['slot_id']: (x['point'], x['open_why']) for x in t['slots']} == {x['slot_id']: (x['point'], x['open_why']) for x in board(c, did)['slots'] if x['level'] in ('R', 'O')}


def test_the_vault_counts_what_the_sign_is_made_of(tmp_path):
    c, did = client(tmp_path)
    ov = c.get(f'/api/dossiers/{did}/prepare', headers=H).json()
    assert ov['counts']['documents'] == 0 and ov['ready'] is False                # an empty vault is not «ready»
    assert ov['counts']['missing'] == board(c, did)['points']['open']
    # a file of two documents, cut, each part placed: the vault says what each was cut from
    two = make_pdf_lines(tmp_path / 'made-up-two.pdf', COA, 'made-up-two.pdf')
    from dossier_engine import pages as _pages
    both = _pages.merge([two.read_bytes(), make_pdf_lines(tmp_path / 'p2.pdf', SPEC, 'p2').read_bytes()])
    up = c.post(f'/api/dossiers/{did}/unplaced', headers=H, files={'files': ('made-up-two.pdf', both)}, data={'meta': '{}'}).json()[0]['id']
    parts = c.post(f'/api/dossiers/{did}/documents/{up}/split', headers=H, json={'starts': [1, 2]}).json()['parts']
    assert len(parts) == 2
    ov = c.get(f'/api/dossiers/{did}/prepare', headers=H).json()
    assert ov['counts']['waiting'] == 2 and ov['ready'] is False
    coa = slot(c, did, '1.2.3.1')['slot_id']
    for part, sid in zip(parts, (coa, 'P-09')):
        assert c.post(f'/api/dossiers/{did}/documents/{part["id"]}/place', headers=H, json={'slot_id': sid}).status_code == 200
    ov = c.get(f'/api/dossiers/{did}/prepare', headers=H).json()
    assert ov['counts'] == {**ov['counts'], 'documents': 2, 'ready': 0, 'needs_you': 0, 'not_prepared': 2, 'waiting': 0}
    cuts = sorted((x['cut']['from'], tuple(x['cut']['pages'])) for x in ov['placed'])
    assert cuts == [('made-up-two.pdf', (1, 1)), ('made-up-two.pdf', (2, 2))]
    assert all(x['bucket'] == 'not_prepared' and x['reader'] is None and x['module'] in (1, 3) and x['req_id'] for x in ov['placed'])
    for x in ov['placed']:
        c.post(f'/api/dossiers/{did}/prepare/{x["id"]}', headers=H, json={})
    ov = c.get(f'/api/dossiers/{did}/prepare', headers=H).json()
    n = ov['counts']
    assert n['documents'] == 2 and n['not_prepared'] == 0 and n['ready'] + n['needs_you'] == 2
    assert all(x['reader'] == 'text' and x['prepared'] for x in ov['placed'])
    assert ov['ready'] is (n['ready'] == 2 and not n['conflicts'])                # every document ready, nothing waiting, no difference to choose
    assert {x['bucket'] for x in ov['placed']} <= {'ready', 'needs_you'}


def test_a_document_with_no_pages_to_draw_gives_its_words(tmp_path):
    import docx
    c, did = client(tmp_path)
    d = docx.Document()
    d.add_paragraph('Made-up justification of the specification')
    d.add_paragraph('The limits follow the made-up pharmacopoeia.')
    buf = io.BytesIO()
    d.save(buf)
    r = c.post(f'/api/dossiers/{did}/slots/P-09/documents', headers=H, files={'file': ('made-up-note.docx', buf.getvalue())}, data={'meta': '{}'})
    assert r.status_code == 201, r.text[:300]
    t = c.get(f'/api/dossiers/{did}/documents/{r.json()["id"]}/text', headers=H).json()
    assert t['filename'] == 'made-up-note.docx' and len(t['pages']) == 1 and 'Made-up justification' in t['pages'][0] and 'pharmacopoeia' in t['pages'][0]
    assert t['chars'] == len(t['pages'][0])
    pdf = put(c, did, slot(c, did, '1.2.3.1')['slot_id'], tmp_path, 'made-up-coa.pdf', COA)
    t2 = c.get(f'/api/dossiers/{did}/documents/{pdf["id"]}/text', headers=H).json()
    assert len(t2['pages']) == 1 and 'Batch No.: 240101' in t2['pages'][0]
    # after a new version, the id it had is shown the document as it is now (as the viewer's pages are)
    fixed = c.post(f'/api/dossiers/{did}/prepare/{pdf["id"]}', headers=H, json={}).json()['document']
    assert c.get(f'/api/dossiers/{did}/documents/{pdf["id"]}/text', headers=H).json()['id'] == fixed['id']
    assert c.get(f'/api/dossiers/{did}/documents/no-such-document/text', headers=H).status_code == 404


def test_a_newer_copy_takes_its_documents_place_as_a_new_version(tmp_path):
    c, did = client(tmp_path)
    gmp = slot(c, did, '1.2.4.1')['slot_id']
    old = put(c, did, gmp, tmp_path, 'made-up-gmp-2024.pdf', GMP + ['Valid until 31 January 2027'])
    soon = (date.today() + timedelta(days=400)).isoformat()
    assert c.put(f'/api/dossiers/{did}/documents/{old["id"]}/validity', headers=H, json={'valid_until': soon}).status_code == 200
    later = (date.today() + timedelta(days=900)).isoformat()
    new = staged(c, did, tmp_path, 'made-up-gmp-2026.pdf', GMP + ['a later copy'], kind='gmp', valid_until=later)
    plain = staged(c, did, tmp_path, 'made-up-gmp-undated.pdf', GMP + ['no date on this one'], kind='gmp')
    t = c.post(f'/api/dossiers/{did}/tree', headers=H, json={'place': {new: gmp, plain: gmp}}).json()
    w = {x['id']: x for x in t['waiting']}
    name_of_old = next(s for s in t['slots'] if s['slot_id'] == gmp)['documents'][0]['name']
    # the file whose validity ends later is proposed as its newer copy, and would carry its name; the undated one is not proposed
    assert w[new]['beside'] == [{'id': old['id'], 'filename': 'made-up-gmp-2024.pdf', 'version': 1, 'valid_until': soon}]
    assert w[new]['newer_of'] == old['id'] and w[new]['replaces'] == old['id'] and w[new]['name'] == name_of_old
    assert w[plain]['newer_of'] is None and w[plain]['replaces'] is None and w[plain]['name'] != name_of_old
    # the person says «beside it»: no replacement, another name
    t2 = c.post(f'/api/dossiers/{did}/tree', headers=H, json={'place': {new: gmp, plain: ''}, 'replaces': {new: ''}}).json()
    w2 = {x['id']: x for x in t2['waiting']}
    assert w2[new]['newer_of'] == old['id'] and w2[new]['replaces'] is None and w2[new]['name'] != name_of_old
    # a company's own item proposes nothing (it is said only of certificates and the authority's documents)
    spec_old = put(c, did, 'P-09', tmp_path, 'made-up-spec.pdf', SPEC)
    spec_new = staged(c, did, tmp_path, 'made-up-spec-2.pdf', SPEC + ['revised'], kind='spec', valid_until=later)
    w3 = {x['id']: x for x in c.post(f'/api/dossiers/{did}/tree', headers=H, json={'place': {spec_new: 'P-09'}}).json()['waiting']}
    assert w3[spec_new]['newer_of'] is None and [x['id'] for x in w3[spec_new]['beside']] == [spec_old['id']]
    # placed as the new version: one document in the item, version 2, the old one kept in its history
    bad = c.post(f'/api/dossiers/{did}/documents/{new}/place', headers=H, json={'slot_id': gmp, 'replaces': spec_old['id']})
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-REPLACES'
    r = c.post(f'/api/dossiers/{did}/documents/{new}/place', headers=H, json={'slot_id': gmp, 'replaces': old['id']})
    assert r.status_code == 200, r.text[:300]
    docs = slot(c, did, '1.2.4.1')['documents']
    assert len(docs) == 1 and docs[0]['version'] == 2 and docs[0]['filename'] == 'made-up-gmp-2026.pdf' and docs[0]['meta']['claude_valid_until'] == later   # its date goes with it (its own at its preparation)
    assert c.get(f'/api/dossiers/{did}/documents/{old["id"]}/text', headers=H).json()['id'] == docs[0]['id']       # the old id leads to the new version
    t4 = c.get(f'/api/dossiers/{did}/tree', headers=H).json()
    assert next(s for s in t4['slots'] if s['slot_id'] == gmp)['documents'][0]['name'] == name_of_old               # and the name did not change


def test_what_is_missing_is_listed_under_who_issues_it_and_one_request_covers_a_party(tmp_path):
    c, did = client(tmp_path)
    m = c.get(f'/api/dossiers/{did}/missing', headers=H).json()
    kinds = [p['kind'] for p in m['parties']]
    assert kinds == sorted(kinds, key=['company', 'authority', 'api', 'other'].index) and set(kinds) == {'company', 'authority', 'api', 'other'}
    b = board(c, did)
    assert m['points'] == b['points'] and sum(len(p['items']) for p in m['parties']) == b['points']['open']
    by = {p['kind']: p for p in m['parties']}
    assert all(i['doc_class'] == 'eda_document' for i in by['authority']['items']) and by['authority']['name']['ar']
    assert by['api']['key'] == 'api:example api co.' and by['api']['name']['en'].startswith('Example API Co.')
    assert all(i['doc_class'] == 'third_party_certificate' and i['item']['manufacturer'] == 'Example API Co.' for i in by['api']['items'])
    assert all(i['doc_class'] == 'third_party_certificate' and not i['item'] for i in by['other']['items'])
    assert all(i['doc_class'] not in ('eda_document', 'third_party_certificate') for i in by['company']['items'])
    assert all(i['why'] == ['missing'] and i['request'] is None for p in m['parties'] for i in p['items'])
    assert any(i['generable'] for i in by['company']['items']) and all(i['how'] for i in by['authority']['items'])
    # one request for two items of the authority: one letter that names both, both waiting with the same due date
    two = [i['slot_id'] for i in by['authority']['items'][:2]]
    titles = [i['title']['en'] for i in by['authority']['items'][:2]]
    who = {'issuer': 'Egyptian Drug Authority', 'lang': 'en', 'due_days': 30, 'signatory': 'A. Tester', 'signatory_title': 'Regulatory Affairs'}
    r = c.post(f'/api/dossiers/{did}/requests', headers=H, json={**who, 'slot_ids': two})
    assert r.status_code == 201, r.text[:300]
    out = r.json()
    assert out['items'] == 2 and len(out['request_ids']) == 2 and out['batch']
    letter = c.get(out['letter'], headers=H)
    assert letter.status_code == 200
    if letter.content[:4] == b'%PDF':
        from pypdf import PdfReader
        said = ' '.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(letter.content)).pages)
    else:
        import docx
        said = ' '.join(p.text for p in docx.Document(io.BytesIO(letter.content)).paragraphs)
    flat = ' '.join(said.split())
    assert 'Egyptian Drug Authority' in flat and 'Dermacure' in flat and all(' '.join(x.split())[:30] in flat for x in titles), flat[:400]
    assert '1. ' in flat and '2. ' in flat
    rows = c.get(f'/api/dossiers/{did}/requests', headers=H).json()
    assert len(rows) == 2 and len({x['batch'] for x in rows}) == 1 and len({x['due'] for x in rows}) == 1 and {x['slot_id'] for x in rows} == set(two)
    m2 = c.get(f'/api/dossiers/{did}/missing', headers=H).json()
    au = next(p for p in m2['parties'] if p['kind'] == 'authority')
    assert au['asked'] == 2 and all(i['why'] == ['missing', 'waiting'] and i['request']['batch'] == out['batch'] for i in au['items'] if i['slot_id'] in two)
    assert all(s['status'] == 'waiting' for s in board(c, did)['slots'] if s['slot_id'] in two)
    # asked twice: refused, and it says which item
    again = c.post(f'/api/dossiers/{did}/requests', headers=H, json={**who, 'slot_ids': [two[0], by['authority']['items'][2]['slot_id']]})
    assert again.status_code == 422 and again.json()['detail']['code'] == 'E-REQUEST-OPEN'
    assert len(c.get(f'/api/dossiers/{did}/requests', headers=H).json()) == 2                       # nothing was opened by the refused call
    # one document arrives: its own request closes, the other item still waits
    put(c, did, two[0], tmp_path, 'made-up-letter.pdf', ['A letter of the authority', 'made up'])
    left = c.get(f'/api/dossiers/{did}/requests', headers=H).json()
    assert [x['slot_id'] for x in left] == [two[1]]
    # one item asked through the same door: the letter for one item, as before, and no batch
    one = c.post(f'/api/dossiers/{did}/requests', headers=H, json={**who, 'slot_ids': [by['other']['items'][0]['slot_id']]}).json()
    assert one['batch'] is None and one['items'] == 1 and len(one['request_ids']) == 1
    assert c.post(f'/api/dossiers/{did}/requests', headers=H, json={**who, 'slot_ids': []}).status_code == 422
    assert c.post(f'/api/dossiers/{did}/requests', headers=H, json={**who, 'issuer': ' ', 'slot_ids': [by['other']['items'][1]['slot_id']]}).status_code == 422


def test_a_certificate_is_judged_on_the_target_submission_date(tmp_path):
    c, did = client(tmp_path)
    gmp = slot(c, did, '1.2.4.1')['slot_id']
    doc = put(c, did, gmp, tmp_path, 'made-up-gmp.pdf', GMP)
    until = date.today() + timedelta(days=200)
    c.put(f'/api/dossiers/{did}/documents/{doc["id"]}/validity', headers=H, json={'valid_until': until.isoformat()})
    look = lambda: next(d for d in slot(c, did, '1.2.4.1')['documents'])
    valid = lambda: next(x for x in next(p for p in c.get(f'/api/dossiers/{did}/prepare', headers=H).json()['placed'] if p['slot_id'] == gmp)['conditions'] if x['id'] == 'valid')
    assert not [f for f in look()['findings'] if f['rule'].startswith('DOC-EXP')] and valid()['status'] == 'ok'
    # a target date after the certificate's end: said now — a warning on the document, «needs you» in its preparation
    target = date.today() + timedelta(days=300)
    r = c.put(f'/api/dossiers/{did}/target-date', headers=H, json={'target_date': target.isoformat()})
    assert r.status_code == 200 and r.json() == {'target_date': target.isoformat()}
    f = [x for x in look()['findings'] if x['rule'] == 'DOC-EXPIRES-BEFORE-SUBMISSION']
    assert len(f) == 1 and f[0]['severity'] == 'warn' and target.strftime('%d/%m/%Y') in f[0]['en'] and until.strftime('%d/%m/%Y') in f[0]['ar']
    v = valid()
    assert v['status'] == 'needs_you' and v['action'] == 're_obtain' and 'target submission date' in v['why']['en'] and 'تاريخ التقديم المستهدف' in v['why']['ar']
    assert c.get(f'/api/dossiers/{did}/prepare', headers=H).json()['target_date'] == target.isoformat()
    assert c.get(f'/api/dossiers/{did}', headers=H).json()['envelope']['target_date'] == target.isoformat()
    assert slot(c, did, '1.2.4.1')['open_why'] == ['not_prepared']            # not read yet: that is all that is said of its point
    c.post(f'/api/dossiers/{did}/prepare/{look()["id"]}', headers=H, json={})
    assert 'needs_you' in slot(c, did, '1.2.4.1')['open_why'] and 'not_prepared' not in slot(c, did, '1.2.4.1')['open_why']
    # a target date before the certificate's end: nothing is said
    c.put(f'/api/dossiers/{did}/target-date', headers=H, json={'target_date': (date.today() + timedelta(days=100)).isoformat()})
    assert not [x for x in look()['findings'] if x['rule'] == 'DOC-EXPIRES-BEFORE-SUBMISSION'] and valid()['status'] == 'ok'
    # a date that has passed counts for nothing; taken away: gone; not a date: refused
    c.put(f'/api/dossiers/{did}/target-date', headers=H, json={'target_date': (date.today() - timedelta(days=5)).isoformat()})
    assert valid()['status'] == 'ok'
    assert c.put(f'/api/dossiers/{did}/target-date', headers=H, json={'target_date': ''}).json() == {'target_date': None}
    assert 'target_date' not in c.get(f'/api/dossiers/{did}', headers=H).json()['envelope']
    bad = c.put(f'/api/dossiers/{did}/target-date', headers=H, json={'target_date': 'next spring'})
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-DATE'
    # given with the product card: kept when it is a date, dropped when it is not
    c2, d2 = client(tmp_path / 'b', target_date=target.isoformat())
    assert c2.get(f'/api/dossiers/{d2}', headers=H).json()['envelope']['target_date'] == target.isoformat()
    c3, d3 = client(tmp_path / 'c', target_date='soon')
    assert 'target_date' not in c3.get(f'/api/dossiers/{d3}', headers=H).json()['envelope']


def test_the_validity_date_read_with_the_file_stays_with_it(tmp_path):
    c, did = client(tmp_path)
    until = (date.today() + timedelta(days=700)).isoformat()
    up = staged(c, did, tmp_path, 'made-up-gmp.pdf', GMP, kind='gmp', valid_until=until, issued='2026-05-02')
    meta = next(u for u in board(c, did)['unassigned'] if u['id'] == up)['meta']
    # kept beside the document, not as its own date: its own reading comes first (store.take_claude_date)
    assert meta['claude_valid_until'] == until and meta['claude_issued'] == '2026-05-02' and 'valid_until' not in meta
    odd = staged(c, did, tmp_path, 'made-up-gmp-2.pdf', GMP + ['another'], kind='gmp', valid_until='not a date')
    assert 'claude_valid_until' not in next(u for u in board(c, did)['unassigned'] if u['id'] == odd)['meta']
    gmp = slot(c, did, '1.2.4.1')['slot_id']
    placed = c.post(f'/api/dossiers/{did}/documents/{up}/place', headers=H, json={'slot_id': gmp}).json()
    assert placed['meta']['claude_valid_until'] == until and 'valid_until' not in placed['meta']      # its text gives no date
    valid = lambda: next(x for x in next(p for p in c.get(f'/api/dossiers/{did}/prepare', headers=H).json()['placed'] if p['slot_id'] == gmp)['conditions'] if x['id'] == 'valid')
    v = valid()
    assert v['status'] == 'ok' and v['how'] == 'model'                            # not asked again, and said to come from a reading
    # prepared: its own reading gave no date, so the one Claude read becomes its date (the expiry rule then has it too)
    c.post(f'/api/dossiers/{did}/prepare/{placed["id"]}', headers=H, json={})
    doc = slot(c, did, '1.2.4.1')['documents'][0]
    assert doc['meta']['valid_until'] == until and doc['meta']['validity_note'] == 'read by Claude' and doc['meta']['issued'] == '2026-05-02'
    v = valid()
    assert v['status'] == 'ok' and v['how'] == 'model'
    cur = slot(c, did, '1.2.4.1')['documents'][0]['id']
    other = (date.today() + timedelta(days=500)).isoformat()
    c.put(f'/api/dossiers/{did}/documents/{cur}/validity', headers=H, json={'valid_until': other})
    v = valid()
    assert v['status'] == 'ok' and v['how'] == 'person'                           # the person wrote another date: it is theirs now


def test_a_request_with_the_signatory_left_empty_is_answered_in_the_engines_own_words(tmp_path):
    """16/11/2026: the request form sends an empty signatory as null, and the request's model refused null with a validator's list in
    place of the engine's own «some data is missing» — on the request for one item (since that form was made) as on the new one."""
    c, did = client(tmp_path)
    sid, other = slot(c, did, '1.2.4.1')['slot_id'], slot(c, did, '1.1.5')['slot_id']
    empty = {'issuer': 'Example Authority', 'lang': 'en', 'due_days': 21, 'company': None, 'signatory': None, 'signatory_title': None}
    for url, more in ((f'/api/dossiers/{did}/slots/{sid}/request', {}), (f'/api/dossiers/{did}/requests', {'slot_ids': [sid]}),
                      (f'/api/dossiers/{did}/requests', {'slot_ids': [sid, other]})):
        r = c.post(url, headers=H, json={**empty, **more})
        assert r.status_code == 422, r.text[:300]
        d = r.json()['detail']
        assert d['code'] == 'E-MISSING-DATA' and 'signatory' in d['request_data'] and d['ar'], d
    assert c.get(f'/api/dossiers/{did}/requests', headers=H).json() == []      # nothing was opened by a refused request


def test_a_document_already_small_is_not_prepared_again_only_to_try_the_same_improvement(tmp_path):
    """«تجهيز الكل» took every PDF whose improvement had given nothing as still «improvable», and prepared it again on each press, only
    to try the same thing once more — the button never stopped being the main one (16/11/2026). The try is kept on the document with
    the digest of the bytes tried: the same bytes are not tried again, other bytes are."""
    c, did = client(tmp_path)
    doc = put(c, did, 'P-05', tmp_path, 'made-up-process.pdf', ['A made-up document', 'Dermacure 20 mg cream (made up)', 'Example Pharm'])
    row = lambda: next(x for x in c.get(f'/api/dossiers/{did}/prepare', headers=H).json()['placed'] if x['slot_id'] == 'P-05')
    held = lambda: next(d for s in board(c, did)['slots'] if s['slot_id'] == 'P-05' for d in s['documents'])
    assert row()['improvable'] is True
    assert c.post(f'/api/dossiers/{did}/prepare/{doc["id"]}', headers=H, json={}).status_code == 200
    after = row()
    assert after['prepared'] and not after['improved'] and after['improvable'] is False       # tried: already small — not offered again
    tried = held()['meta']['improve_tried']
    assert tried == {'sha256': held()['sha256'], 'why': 'already small'}
    assert c.post(f'/api/dossiers/{did}/prepare/{after["id"]}', headers=H, json={}).status_code == 200
    again = row()
    assert again['id'] == after['id'] and again['version'] == after['version']                  # prepared again by hand: no new version for nothing
    # other bytes (a page turned): a new version, tried afresh
    new = c.post(f'/api/dossiers/{did}/documents/{after["id"]}/pages', headers=H, json={'op': 'rotate', 'pages': [1], 'degrees': 90}).json()['document']
    assert row()['id'] == new['id'] and row()['improvable'] is True


def test_the_vault_counts_the_cross_document_findings_that_touch_its_documents(tmp_path):
    """A point stays open under a document that is itself ready when a blocking finding of the cross-document checks names its item:
    the sign of station 6 says so (and where they are looked at) from this count — only the findings on documents the vault holds."""
    c, did = client(tmp_path)
    assert c.put(f'/api/dossiers/{did}/data', headers=H, json={'batches': [{'no': 'EX0001', 'size': '100,000', 'date': '2026-01', 'site': 'A', 'scale': 'pilot'}]}).status_code == 200
    found = [f for f in board(c, did)['cross'] if f['id'] == 'NP040-P54']
    assert found and found[0]['severity'] == 'block' and 'P-16' in found[0]['slots']       # one batch where two are asked
    ov = c.get(f'/api/dossiers/{did}/prepare', headers=H).json()
    assert ov['counts']['cross'] == 0                                                       # no document of the vault is touched yet
    doc = put(c, did, 'P-16', tmp_path, 'made-up-item.pdf', ['A made-up document', 'Dermacure 20 mg cream (made up)', 'Example Pharm'])
    assert c.post(f'/api/dossiers/{did}/prepare/{doc["id"]}', headers=H, json={}).status_code == 200
    ov = c.get(f'/api/dossiers/{did}/prepare', headers=H).json()
    row = next(x for x in ov['placed'] if x['slot_id'] == 'P-16')
    assert row['bucket'] == 'ready' and ov['points']['P-16'] == {'point': 'open', 'why': ['cross']}
    held = {x['slot_id'] for x in ov['placed']}
    assert ov['counts']['cross'] == sum(1 for f in board(c, did)['cross'] if f['severity'] == 'block' and held & set(f['slots'])) >= 1
    assert ov['ready'] is True                                                              # the documents themselves are ready: what keeps the point open is counted beside


def test_the_date_a_documents_own_text_gives_stands_and_another_reading_is_said(tmp_path):
    """Found by his real files through «ملف جديد» against version 53: the date Claude read in «القراءة والفرز», carried as the
    document's own date, stood over the date its own text gave — four certificates expired by their text passed as valid. The
    document's text comes first; where Claude read another date, the condition says both and asks; a date read from the text is
    said to come from the text (it was said to be the person's)."""
    c, did = client(tmp_path)
    gmp = slot(c, did, '1.2.4.1')['slot_id']
    later = (date.today() + timedelta(days=700))

    def through(name, lines, claude):
        up = staged(c, did, tmp_path, name, lines, kind='gmp', valid_until=claude)
        assert c.post(f'/api/dossiers/{did}/documents/{up}/place', headers=H, json={'slot_id': gmp}).status_code == 200
        doc = next(d for d in slot(c, did, '1.2.4.1')['documents'] if d['filename'] == name)
        c.post(f'/api/dossiers/{did}/prepare/{doc["id"]}', headers=H, json={})
        row = next(p for p in c.get(f'/api/dossiers/{did}/prepare', headers=H).json()['placed'] if p['filename'] == name)
        doc = next(d for d in slot(c, did, '1.2.4.1')['documents'] if d['filename'] == name)
        return doc, next(x for x in row['conditions'] if x['id'] == 'valid')

    # expired by its text, valid by Claude's reading: the text's date stands, the expiry is said, and so is the other reading
    doc, v = through('made-up-gmp-old.pdf', GMP + ['Valid until 31 January 2019'], later.isoformat())
    assert doc['meta']['valid_until'] == '2019-01-31' and doc['meta'].get('valid_until_read') and doc['meta']['claude_valid_until'] == later.isoformat()
    assert any(f['rule'] == 'DOC-EXPIRED' for f in doc['findings'])
    assert v['status'] == 'needs_you' and v['how'] == 'text' and later.strftime('%d/%m/%Y') in v['why']['ar'] and 'وقرأ Claude على صفحاته تاريخًا آخر' in v['why']['ar']
    # valid by both, on different days: asked, not picked
    text_day = date.today() + timedelta(days=400)
    doc, v = through('made-up-gmp-two.pdf', GMP + ['two dates', f'Valid until {text_day.day} {text_day.strftime("%B %Y")}'], later.isoformat())
    assert doc['meta']['valid_until'] == text_day.isoformat() and v['status'] == 'check' and v['how'] == 'text' and v['action'] == 'set_validity'
    # the same day both ways: nothing to ask, and said to come from its text
    doc, v = through('made-up-gmp-same.pdf', GMP + ['one date', f'Valid until {later.day} {later.strftime("%B %Y")}'], later.isoformat())
    assert v['status'] == 'ok' and v['how'] == 'text'
    # the person writes the date: it is theirs, whatever was read
    c.put(f'/api/dossiers/{did}/documents/{doc["id"]}/validity', headers=H, json={'valid_until': (date.today() + timedelta(days=300)).isoformat()})
    v = next(x for x in next(p for p in c.get(f'/api/dossiers/{did}/prepare', headers=H).json()['placed'] if p['filename'] == 'made-up-gmp-same.pdf')['conditions'] if x['id'] == 'valid')
    assert v['status'] == 'ok' and v['how'] == 'person'
