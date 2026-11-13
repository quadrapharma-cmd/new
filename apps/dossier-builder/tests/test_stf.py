"""Study Tagging Files (updates list, item 46): the ICH STF v2.6.1 of a study, checked against the official DTD; the eCTD 4.0 document
types give the file-tags; categories only where the specification puts them. The EG and EU sequences group each study under a
node-extension instead (test_import_ectd), as EDA's draft and the EU guidance ask."""
import io, re, zipfile
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from dossier_engine.writers import stf
from test_api import new
from test_lifecycle_api import fill_all

REL = 'm5/53-clin-stud-rep/535-rep-effic-safety-stud/indication-1/5351-stud-rep-contr/exm-01/stf-exm-01.xml'


def test_tags_names_and_a_valid_stf():
    assert stf.tag_of('ich_document_type_2') == 'legacy-clinical-study-report' and stf.tag_of('ich_document_type_4') == 'study-report-body'
    assert stf.tag_of('ich_document_type_26') == 'available-on-request' and stf.tag_of('ich_document_type_27') is None
    assert stf.tag_of('synopsis') == 'synopsis' and stf.file_name('EXM BE/01') == 'stf-exm-be-01.xml'
    xml = stf.make('EXM-01', 'A placebo-controlled study', [
        {'leaf_id': 'id1', 'doc_type': 'ich_document_type_3', 'title': 'Synopsis'},
        {'leaf_id': 'id2', 'tag': 'case-report-forms', 'site': 'Site 001'}], REL, '5.3.5.1', [('type-of-control', 'placebo')])
    assert stf.check(xml) == []
    assert 'xlink:href="../../../../../../index.xml#id1"' in xml                       # from the study's folder back to the sequence
    assert '<category name="type-of-control" info-type="ich">placebo</category>' in xml
    assert '<property name="site-identifier" info-type="us">Site 001</property>' in xml
    assert 'dtd-version="2.2"' in xml and '"../../../../../../util/dtd/ich-stf-v2-2.dtd"' in xml


def test_what_the_specification_does_not_allow_is_refused():
    with pytest.raises(stf.STFError):
        stf.make('EXM-01', 't', [{'leaf_id': 'a', 'doc_type': 'ich_document_type_27'}], REL, '5.3.5.1')         # not an STF tag
    with pytest.raises(stf.STFError):
        stf.make('EXM-01', 't', [], REL, '5.3.1.2', [('species', 'rat')])                                     # no category at 5.3.1.2
    with pytest.raises(stf.STFError):
        stf.make('EXM-01', 't', [], REL, '4.2.3.1', [('species', 'cat')])                                     # not a value of the list
    bad = stf.make('EXM-01', 't', [], REL, '5.3.5.1').replace('<study-id>EXM-01</study-id>', '')
    assert stf.check(bad)                                                                                      # the DTD itself catches it


def test_the_stfs_of_an_exported_sequence(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    did = new(c)
    fill_all(c, did, pdf)
    r = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32']})
    assert r.status_code == 201, r.text
    from dossier_engine.app.store import Store
    hist = Store(tmp_path / 'ws').history(did, 'ectd32')[0]['leaves']
    docs = {d['id']: {'study': d['meta'].get('study'), 'doc_type': d['meta'].get('doc_type'), 'title': d['title']}
            for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] for d in s['documents']}
    out = stf.for_sequence(hist, docs, None)
    assert out and all(p.endswith('/stf-exm-be-01.xml') and '/exm-be-01/' in p and stf.check(x) == [] for p, x in out)
    index = zipfile.ZipFile(io.BytesIO(c.get(r.json()['downloads']['ectd32']).content))
    idx = next(index.read(n).decode() for n in index.namelist() if n.endswith('0000/index.xml'))
    for _, x in out:                                                                   # every doc-content points at a leaf of the sequence
        assert all(f'ID="{lid}"' in idx for lid in re.findall(r'index\.xml#([^"]+)"', x))
