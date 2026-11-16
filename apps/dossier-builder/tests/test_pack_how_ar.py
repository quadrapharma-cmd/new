"""«كيفية الحصول عليه» is said in Arabic for every item of the Egyptian pack (eBOX stage 3, 16/11/2026: station 7 puts it in front of every
item that is still open, and it stood in English in an Arabic page). The Arabic is the pack's own file, item by item."""
import pathlib
import re

from dossier_engine import packs
from dossier_engine.yamlfast import load as yload

PACK = 'eda.ctd.nta065.v5'
FILE = pathlib.Path(packs.PACKS_DIR) / PACK / 'how.ar.yaml'


def test_every_item_that_says_how_says_it_in_arabic_too():
    reqs = packs.load(PACK).requirements
    how = yload(FILE.read_text(encoding='utf-8'))
    with_how = {r['id'] for r in reqs if (r.get('rebuild') or {}).get('needs')}
    assert with_how and set(how) == with_how, (sorted(with_how - set(how)), sorted(set(how) - with_how))
    for r in reqs:
        ar = (r.get('rebuild') or {}).get('needs_ar')
        assert ar == how[r['id']] and re.search(r'[؀-ۿ]', ar), r['id']
        assert not re.search(r'\b(tool|sheet|From|Re-obtain)\b', ar), (r['id'], ar)      # translated, not carried over


def test_the_board_gives_it_beside_the_english():
    from fastapi.testclient import TestClient
    from dossier_engine.app.api import create_app
    import tempfile
    c = TestClient(create_app(pathlib.Path(tempfile.mkdtemp()) / 'ws'))
    did = c.post('/api/dossiers', headers={'X-DB': '1'}, json={'name': 'Dermacure (made up)', 'profile': {'dossier_kind': 'generic', 'origin': 'local', 'licence': 'own', 'activity': 'new',
                 'apis': [{'name': 'Exampletine', 'manufacturer': 'Example API Co.', 'option': 'CEP'}]}, 'product': {'name': 'Dermacure 20 mg', 'dosageform': 'cream', 'manufacturer': 'Example Pharm'},
                 'envelope': {}}).json()['id']
    slots = c.get(f'/api/dossiers/{did}/board', headers={'X-DB': '1'}).json()['slots']
    gmp = next(s for s in slots if s['req_id'] == 'M1-37')
    assert gmp['how'] == 'Re-obtain from authority.' and gmp['how_ar'] == 'يُعاد استخراجه من السلطة التي أصدرته.'
    assert all(s.get('how_ar') for s in slots if s.get('how'))
    items = [i for g in c.get(f'/api/dossiers/{did}/missing', headers={'X-DB': '1'}).json()['parties'] for i in g['items']]
    assert items and all(i['how_ar'] for i in items if i['how'])
