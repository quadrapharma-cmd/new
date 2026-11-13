"""The rules catalogue (updates list, item 20): every rule the engine emits is in it with a source and a status; the eCTD draft's
rules are «draft», never «in force»; the validators' rules come from their profiles with what runs and what does not, and why; the
official texts are listed with their SHA-256."""
import inspect, re
from fastapi.testclient import TestClient
from dossier_engine import rules_catalogue
from dossier_engine.checks.pdf import ECTD_DRAFT
from dossier_engine.app.api import create_app


def emitted():
    import dossier_engine.checks.pdf as pdf, dossier_engine.app.store as store
    ids = set()
    for mod in (pdf, store):
        ids |= set(re.findall(r"Finding\(\s*'([A-Z][A-Z0-9_.-]+)'", inspect.getsource(mod)))
        ids |= set(re.findall(r"'rule': '([A-Z][A-Z0-9_.-]+)'", inspect.getsource(mod)))
        ids |= set(re.findall(r"'id': '(XC-[A-Z]+)'", inspect.getsource(mod)))
    return ids


def test_every_rule_the_engine_emits_has_its_source_and_status(tmp_path):
    cat = rules_catalogue.catalogue()
    by = {r['id']: r for r in cat['rules']}
    missing = emitted() - set(by)
    assert not missing, missing
    assert all(by[r]['status'] == 'draft' for r in ECTD_DRAFT if r in by and r != 'ECTD-WORD')          # the eCTD draft is never «in force»
    assert by['NTA065-N4']['status'] == 'in_force' and 'NP.CAPP.065 v5' in by['NTA065-N4']['source']
    assert all(r['source'] and r['status'] in ('in_force', 'draft', 'policy') for r in cat['rules'])
    eu = [r for r in cat['rules'] if r['stage'] == 'ectd32_eu']
    assert len(eu) == 111 and sum(r['run'] == 'not_run' for r in eu) == 3 and all(r['why_not'] for r in eu if r['run'] == 'not_run')
    assert any(r['stage'] == 'ectd32' for r in cat['rules']) and cat['counts']['upload']['draft'] >= 5
    src = {s['file']: s for s in cat['sources']}
    assert 'EDA_NP.CAPP.065_v5_2025_CTD-submission-guidance.pdf' in src and len(src['EDA_NP.CAPP.065_v5_2025_CTD-submission-guidance.pdf']['sha256']) == 64
    c = TestClient(create_app(tmp_path / 'ws', auth_enabled=False))
    assert c.get('/api/rules').json()['counts'] == cat['counts']
