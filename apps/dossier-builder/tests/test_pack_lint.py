from dossier_engine import packs


def test_pack_is_clean():
    p = packs.load('eda.ctd.nta065.v5')
    assert packs.lint(p) == []


def test_every_requirement_cited_and_tagged():
    p = packs.load('eda.ctd.nta065.v5')
    for r in p.requirements:
        assert r['sources'], r['id']
        assert r['provenance'] in p.meta['provenance_tags'], r['id']


def test_locked_classes_present():
    p = packs.load('eda.ctd.nta065.v5')
    classes = {r['id']: r['doc_class'] for r in p.requirements}
    assert classes['M1-14'] == 'third_party_certificate'   # CPP
    assert classes['M1-05'] == 'eda_document'              # pricing certificate
    assert classes['R-01'] == 'executed_record'
    assert classes['M1-01'] == 'generated'                 # Annex I
    assert classes['M1-31'] == 'company_letter'            # composition certificate
