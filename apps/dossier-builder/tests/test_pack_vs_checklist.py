"""Golden test: the pack and the company checklist (xlsx) must agree.

1. Same ids, same order, same titles, matrix cells verbatim (NP.CAPP.065 v5).
2. For every unconditional requirement (applies == true, no cases, not per-API),
   the resolver's level for each column equals the normalised xlsx cell.
"""
import openpyxl, pytest
from conftest import CHECKLIST
from dossier_engine import packs
from dossier_engine.profile import Profile, Api
from dossier_engine.resolver import resolve

SHEET = 'قائمة المستندات Checklist'
NORM = {'R': 'R', 'NR': 'NR', 'O': 'O', '—': 'R', 'R*': 'R', 'R if applicable': 'R'}
COLS = {'I': dict(dossier_kind='innovator', origin='imported', licence='imported'),
        'G_IMP': dict(dossier_kind='generic', origin='imported', licence='imported'),
        'G_LOC': dict(dossier_kind='generic', origin='local', licence='own')}


def xlsx_rows():
    ws = openpyxl.load_workbook(CHECKLIST)[SHEET]
    out = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] and row[1]:
            out.append(row)
    return out


@pytest.fixture(scope='module')
def pack():
    return packs.load('eda.ctd.nta065.v5')


def test_ids_titles_matrix_verbatim(pack):
    rows = xlsx_rows()
    assert [str(r[0]).strip() for r in rows] == [r['id'] for r in pack.requirements]
    for row, req in zip(rows, pack.requirements):
        assert req['title']['en'] == str(row[3]).strip()
        assert req['title']['ar'] == str(row[4]).strip()
        assert req['ctd']['nta065_v5'] == str(row[2]).strip()
        assert req['matrix'] == {'I': str(row[5]).strip(), 'G_IMP': str(row[6]).strip(), 'G_LOC': str(row[7]).strip()}


@pytest.mark.parametrize('col', ['I', 'G_IMP', 'G_LOC'])
def test_unconditional_levels_match_matrix(pack, col):
    prof = Profile(**COLS[col], apis=[Api('Paracetamol', 'API Co', 'FULL')])
    got = {s.req_id: s.level for s in resolve(prof, pack) if '@' not in s.slot_id}
    checked = 0
    for r in pack.requirements:
        if r['applies'] != 'true' or 'per' in r or not isinstance(r['required'][col], str):
            continue
        assert got[r['id']] == NORM[r['matrix'][col]], (r['id'], col)
        checked += 1
    assert checked >= 50          # M5 study items became biowaiver-conditional (see test_biowaiver)


@pytest.mark.parametrize('col', ['G_IMP', 'G_LOC'])
def test_case_cells_default_to_matrix_without_biowaiver(pack, col):
    """An oral tablet with no waiver basis gets exactly the matrix level for the biowaiver-conditional cells."""
    prof = Profile(**COLS[col], apis=[Api('Paracetamol', 'API Co', 'FULL')])
    got = {s.req_id: s.level for s in resolve(prof, pack) if '@' not in s.slot_id}
    for r in pack.requirements:
        if r['id'].startswith('M5-') and isinstance(r['required'][col], dict):
            assert got[r['id']] == NORM[r['matrix'][col]], r['id']
