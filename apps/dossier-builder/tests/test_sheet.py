"""Documents' items, titles and attributes from a sheet (updates list, item 47): the sheet comes down with the dossier's documents,
goes back filled (CSV or Excel), the program says what it would do with every row, and does it only when asked."""
import csv, io
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine.app.api import create_app
from dossier_engine.app.store import Store
from dossier_engine.assistant import storage

H = {'X-DB': '1'}
PROFILE = dict(dossier_kind='generic', origin='local', licence='toll', activity='new', apis=[dict(name='Neomycin sulphate', manufacturer='Example API Co.', option='DMF')])


def setup(tmp_path):
    ws = tmp_path / 'ws'
    c = TestClient(create_app(ws, auth_enabled=False))
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=PROFILE, product=dict(name='Dermacure'), envelope={}), headers=H).json()['id']
    stab = make_pdf_lines(tmp_path / 's.pdf', ['Stability summary and conclusion', 'three batches'], 'S').read_bytes()
    assert c.post(f'/api/dossiers/{did}/slots/P-16/documents', files={'file': ('stability.pdf', stab, 'application/pdf')}, data={'meta': '{}'}, headers=H).status_code == 201
    gmp = make_pdf_lines(tmp_path / 'g.pdf', ['Good Manufacturing Practice certificate', 'Example Pharm Co.'], 'G').read_bytes()
    storage.stage_document(Store(ws), did, 'gmp.pdf', gmp)                         # a file in the unplaced box
    return c, did


def sheet(rows):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['File', 'Item', 'Title', 'PI type', 'Lang'])                        # headers as a person types them
    w.writerows(rows)
    return buf.getvalue().encode('utf-8')


def test_the_sheet_comes_down_with_the_documents_and_goes_back_with_a_plan_first(tmp_path):
    c, did = setup(tmp_path)
    t = c.get(f'/api/dossiers/{did}/metadata-sheet.csv')
    assert t.status_code == 200 and 'attachment' in t.headers['content-disposition']
    rows = list(csv.reader(io.StringIO(t.content.decode('utf-8-sig'))))
    assert rows[0][:3] == ['file', 'item', 'title'] and {'stability.pdf', 'gmp.pdf'} <= {r[0] for r in rows[1:]}
    assert next(r for r in rows if r[0] == 'stability.pdf')[1] == 'P-16' and next(r for r in rows if r[0] == 'gmp.pdf')[1] == ''
    filled = sheet([['stability.pdf', '3.2.P.8', 'Stability — three batches', '', ''],          # a CTD number names the item
                    ['gmp.pdf', 'M1-37', '', '', ''],                                          # from the unplaced box into its item
                    ['missing.pdf', 'M1-37', '', '', ''],
                    ['stability.pdf', 'M1-09', '', '', '']])                                   # the leaflet item needs its type and language
    before = c.get(f'/api/dossiers/{did}/board').json()
    p = c.post(f'/api/dossiers/{did}/metadata-sheet', files={'file': ('docs.csv', filled, 'text/csv')}, headers=H)
    assert p.status_code == 200, p.text
    plan = p.json()['plan']
    assert [x['action'] for x in plan] == ['update', 'place', 'error', 'error'], plan
    assert plan[0]['changes'] == {'title': 'Stability — three batches'} and plan[1]['slot_id'] == 'M1-37'
    assert 'pi_type' in plan[3]['why'] or 'details' in plan[3]['why']
    assert c.get(f'/api/dossiers/{did}/board').json() == before                       # nothing done yet
    d = c.post(f'/api/dossiers/{did}/metadata-sheet?apply=1', files={'file': ('docs.csv', filled, 'text/csv')}, headers=H).json()
    assert [x['done'] for x in d['done']] == ['update', 'place']
    board = {s['slot_id']: s for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}
    assert [x['filename'] for x in board['M1-37']['documents']] == ['gmp.pdf']
    st = board['P-16']['documents'][0]
    assert st['title'] == 'Stability — three batches' and st['version'] == 1                 # the same version: only its details changed


def test_an_excel_sheet_is_read_the_same(tmp_path):
    import openpyxl
    c, did = setup(tmp_path)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['file', 'item', 'title'])
    ws.append(['gmp.pdf', 'M1-37', 'GMP certificate — Example Pharm Co.'])
    buf = io.BytesIO()
    wb.save(buf)
    plan = c.post(f'/api/dossiers/{did}/metadata-sheet', files={'file': ('docs.xlsx', buf.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
                  headers=H).json()['plan']
    assert plan == [dict(plan[0], action='place', slot_id='M1-37', changes={'title': 'GMP certificate — Example Pharm Co.'})]
    empty = c.post(f'/api/dossiers/{did}/metadata-sheet', files={'file': ('e.csv', b'file,item\n', 'text/csv')}, headers=H)
    assert empty.status_code == 422 and empty.json()['detail']['code'] == 'E-SHEET'
