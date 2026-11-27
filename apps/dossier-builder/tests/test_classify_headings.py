"""A document that prints its own CTD section at its start is placed there (found with a public sample dossier laid out by CTD
section, 27/11/2026): its heading decides over the kind its words suggest, a sub-section finds its item, a section the document
merely cites further on does not, a section this dossier has no item for is offered and never placed elsewhere, and a strength
such as «250 mg» is never read as a section. Made-up product, made-up texts."""
import io, json
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf_lines
from dossier_engine.app.api import create_app
from test_review import PROFILE, PRODUCT, ENV


@pytest.fixture(scope='module')
def us(tmp_path_factory):
    root = tmp_path_factory.mktemp('headings')
    c = TestClient(create_app(root / 'ws', auth_enabled=False))
    r = c.post('/api/dossiers', json=dict(name='Examplol', country='US', profile=PROFILE, product=PRODUCT, envelope=ENV))
    assert r.status_code == 201, r.text
    did = r.json()['id']
    board = {s['slot_id']: s for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}

    def place(lines, title='Document'):
        pdf = make_pdf_lines(root / f'{abs(hash(lines[0]))}.pdf', lines, title)
        out = c.post(f'/api/dossiers/{did}/classify', files=[('files', ('scan_0001.pdf', io.BytesIO(pdf.read_bytes()), 'application/pdf'))]).json()[0]
        first = (out.get('suggestions') or [{}])[0].get('slot_id')
        return out, (board.get(first) or {}).get('ctd'), (board.get(out['auto']) or {}).get('ctd') if out.get('auto') else None
    return place


def test_the_heading_decides_over_the_kind_its_words_suggest(us):
    out, first, auto = us(['3.2.S.4.1 Specification', 'Identification: IR conforms to the USP Reference Standard.',
                           'Assay 98.0-102.0 per cent by HPLC.'])
    assert first == auto and auto.startswith('3.2.S.4.1'), out                    # not 3.2.P.6, the reference standards


def test_a_sub_section_finds_its_item(us):
    out, first, auto = us(['3.2.S.7.1 Stability summary and conclusions', 'Long-term 25 C / 60% RH and accelerated 40 C / 75% RH.'])
    assert auto and auto.startswith('3.2.S.7'), out                                 # the substance's stability, not the product's


def test_its_own_heading_over_a_section_it_cites(us):
    out, first, auto = us(['3.2.A.1 Facilities and equipment', 'Not applicable: Examplol is made at the sites named in 3.2.S.2.1',
                           'and 3.2.P.3.1 of this dossier.'])
    assert first.startswith('3.2.A.1'), out


def test_a_section_without_an_item_here_is_offered_not_placed(us):
    out, first, auto = us(['2.4 Nonclinical overview', 'This abbreviated application relies on the RLD labeling; no new studies.',
                           'The labeling text of the reference listed drug was reviewed.'])
    assert auto is None, out                                                          # this generic dossier has no 2.4 item


def test_a_strength_is_never_a_section(us):
    out, first, auto = us(['Examplol 250 mg tablets', 'Certificate of analysis, batch EX-001.', 'Assay 99.1 per cent; complies.'])
    assert not (first or '').startswith('2.5') and not (auto or '').startswith('2.5'), out
