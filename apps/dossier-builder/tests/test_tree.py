"""Station 5, «الشجرة المقترحة» (eBOX stage 2, 16/11/2026 — the owner: the documents «shown as tree points before the file is made»).
GET/POST /api/dossiers/{id}/tree: the dossier's items with the documents placed in them, and every waiting file with what was read
of it, the item it would go to and the name it would carry there. The call places nothing. Made-up files."""
from fastapi.testclient import TestClient
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf_lines

H = {'X-DB': '1'}
NEW = {'name': 'Dermacure (made up)', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new',
       'apis': [{'name': 'Exampletine', 'manufacturer': 'Example API Co.', 'option': 'CEP'}]},
       'product': {'name': 'Dermacure 20 mg', 'dosageform': 'cream', 'manufacturer': 'Example Pharm'}, 'envelope': {}}


def staged(c, did, tmp_path, name, lines):
    f = make_pdf_lines(tmp_path / name, lines, name)
    r = c.post(f'/api/dossiers/{did}/unplaced', headers=H, files={'files': (name, f.read_bytes())}, data={'meta': '{}'})
    assert r.status_code == 201, r.text[:300]
    return r.json()[0]['id']


def test_the_proposed_tree_shows_each_waiting_file_in_its_place_with_its_name(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', headers=H, json=NEW).json()['id']
    coa = staged(c, did, tmp_path, 'made-up-coa.pdf', ['Certificate of Analysis', 'Exampletine', 'Batch No.: 240101', 'Assay 99.6 %'])
    spec = staged(c, did, tmp_path, 'made-up-spec.pdf', ['Specification of the finished product', '3.2.P.5.1 Specification', 'Appearance: white cream'])
    note = staged(c, did, tmp_path, 'made-up-note.pdf', ['A note about nothing in particular', 'made up'])
    t = c.get(f'/api/dossiers/{did}/tree').json()
    w = {x['id']: x for x in t['waiting']}
    assert set(w) == {coa, spec, note}
    # what was read of each, and what it is
    assert w[coa]['kind'] == 'coa' and w[coa]['kind_name'] == {'en': 'certificate of analysis', 'ar': 'شهادة تحليل'}
    assert w[coa]['reading']['reader'] == 'text' and w[coa]['reading']['pages'] == 1 and 'batches×1' in w[coa]['reading']['found']
    assert w[note]['kind'] == 'other' and w[note]['kind_name'] is None
    # the place the program proposes (the same as «not placed yet» always offered) and the name the file would carry there
    assert w[coa]['place'] == w[coa]['auto'] and w[coa]['place'].startswith('M1-35@Exampletine')
    assert w[coa]['name'].startswith('Dermacure (made up)/Module 1/') and w[coa]['name'].endswith('.pdf') and '1.2.3.1' in w[coa]['name']
    assert w[spec]['place'] == 'P-09' and '3.2.P.5.1' in w[spec]['name']
    assert w[note]['place'] is None and w[note]['name'] is None                # nothing sure: no place is invented for it
    # the items: only the ones this product needs (required or optional), each with what is proposed for it
    slots = {s['slot_id']: s for s in t['slots']}
    assert all(s['level'] in ('R', 'O') for s in t['slots']) and slots[w[coa]['place']]['proposed'] == [coa] and slots['P-09']['proposed'] == [spec]
    assert slots['P-09']['generable'] is True and slots['M1-02']['generable'] is False and all(s['documents'] == [] for s in t['slots'])   # ✦: the program can write it
    assert t['counts'] == {'required': sum(1 for s in t['slots'] if s['level'] == 'R'), 'have': 0, 'filled': 2, 'waiting': 3, 'proposed': 2, 'unplaced': 1}
    # the person's own choice: another item for one file, none for another — the names follow
    other = next(s['slot_id'] for s in t['slots'] if s['module'] == 3 and s['slot_id'].startswith('S-01'))
    t2 = c.post(f'/api/dossiers/{did}/tree', headers=H, json={'place': {note: other, coa: '', spec: 'NO-SUCH-ITEM'}}).json()
    w2 = {x['id']: x for x in t2['waiting']}
    assert w2[note]['place'] == other and '3.2.S.1.1' in w2[note]['name'] and w2[coa]['place'] is None and w2[coa]['name'] is None
    assert w2[spec]['place'] is None                                             # an item this dossier does not have is no place
    assert w2[coa]['auto'] == w[coa]['auto']                                     # what the program itself proposes is still said
    # the call placed nothing
    board = c.get(f'/api/dossiers/{did}/board').json()
    assert all(not s['documents'] for s in board['slots']) and len(board['unassigned']) == 3
    assert [x['id'] for x in c.get(f'/api/dossiers/{did}/prepare').json()['waiting']] == [x['id'] for x in t['waiting']]


def test_a_placed_document_shows_in_the_tree_with_its_name_and_counts_as_had(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    did = c.post('/api/dossiers', headers=H, json=NEW).json()['id']
    spec = staged(c, did, tmp_path, 'made-up-spec.pdf', ['Specification of the finished product', '3.2.P.5.1 Specification', 'Appearance: white cream'])
    proposed = c.get(f'/api/dossiers/{did}/tree').json()['waiting'][0]
    r = c.post(f'/api/dossiers/{did}/documents/{spec}/place', headers=H, json={'slot_id': proposed['place']})
    assert r.status_code == 200, r.text[:300]
    t = c.get(f'/api/dossiers/{did}/tree').json()
    s = next(x for x in t['slots'] if x['slot_id'] == 'P-09')
    assert t['waiting'] == [] and [d['filename'] for d in s['documents']] == ['made-up-spec.pdf'] and s['proposed'] == []
    assert s['documents'][0]['name'] == proposed['name']                         # placed, it carries the name the tree said it would
    assert t['counts']['have'] == 1 and t['counts']['filled'] == 1 and t['counts']['waiting'] == 0
