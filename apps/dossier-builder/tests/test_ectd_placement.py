"""Every requirement has an eCTD 3.2.2 placement that exists in the backbone:
m1 nodes in the EG provisional folder map (leaf containers), M2–M5 nodes as
ICH DTD elements."""
import csv, re
import pytest
from conftest import REPO
from dossier_engine import packs

PROFILE = REPO / 'docs' / 'ctd' / 'ectd' / 'EG-PROVISIONAL-PROFILE-v0'


@pytest.fixture(scope='module')
def pack():
    return packs.load('eda.ctd.nta065.v5')


def m1_leaves():
    out = {}
    for r in csv.DictReader(open(PROFILE / 'folders.csv', encoding='utf-8')):
        if r['ctd_number']:
            out[r['ctd_number']] = r['kind']
    return out


def ich_elements():
    dtd = (PROFILE / 'util' / 'dtd' / 'ich-ectd-3-2.dtd').read_text(encoding='utf-8')
    return re.findall(r'<!ELEMENT\s+(m[2-5][a-z0-9-]*)', dtd)


def ich_has(node, elements):
    stem = 'm' + node.lower().replace('.', '-') + '-'
    return any(e.startswith(stem) and not e[len(stem)].isdigit() for e in elements)


def test_every_requirement_placed(pack):
    m1, els = m1_leaves(), ich_elements()
    for r in pack.requirements:
        nodes = r['ectd']['nodes']
        if r['id'] == 'M5-01':
            assert nodes == []          # TOC: CTD output only
            continue
        assert nodes, r['id']
        for n in nodes:
            if n.startswith('1.'):
                assert m1.get(n) in ('leaf container', 'pi-doc container'), (r['id'], n, m1.get(n))
            else:
                assert ich_has(n, els), (r['id'], n)


def test_placement_module_consistent(pack):
    for r in pack.requirements:
        for n in r['ectd']['nodes']:
            m = int(n.split('.')[0])
            assert m == r['module'] or (r['id'] in ('M1-39', 'M1-40') and n == '3.2.R'), (r['id'], n)


def test_assumptions_are_tagged(pack):
    for r in pack.requirements:
        if 'ASSUMPTION' in r['ectd']['source']:
            assert r['ectd']['provenance'] == 'ASSUMPTION', r['id']
