"""Links between documents (updates list, item 25): a link made in Word to a file on the author's disk becomes, in the eCTD, the
relative link from the document's place to the target's place — in the same sequence, or in the earlier one the target stayed in."""
import io, posixpath, zipfile
from fastapi.testclient import TestClient
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from dossier_engine import links
from dossier_engine.app.api import create_app
from fixtures_pdf import make_pdf
from test_api import new
from test_lifecycle_api import fill_all


def linked_pdf(text, targets):
    """A one-page PDF with text and a link to each target (as Word writes them: file:// or a bare name)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 760, text)
    for i, t in enumerate(targets):
        c.drawString(72, 700 - 30 * i, f'see {t}')
        c.linkURL(t, (70, 695 - 30 * i, 300, 712 - 30 * i), relative=1)
    c.save()
    return buf.getvalue()


def links_of(data):
    out = []
    for p in PdfReader(io.BytesIO(data)).pages:
        for a in p.get('/Annots') or []:
            act = a.get_object()['/A']
            out.append((str(act['/S']), str(act.get('/F') or act.get('/URI'))))
    return out


def test_the_key_of_a_link_is_the_files_name():
    assert links.key('file:///C:/Dossier/3.2.P.5.4%20Batch%20Analyses.DOCX') == '3-2-p-5-4-batch-analyses'
    assert links.key('..\\m3\\batch-analyses.pdf#page=2') == 'batch-analyses' and links.key('') == ''


def test_links_become_relative_in_this_sequence_and_reach_the_earlier_one(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    did = new(c)
    fill_all(c, did, pdf)
    board = {s['slot_id']: s for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}
    ba = linked_pdf('Batch analyses of three batches', [])
    r = c.post(f'/api/dossiers/{did}/slots/P-11/documents', files={'file': ('Batch Analyses.pdf', io.BytesIO(ba), 'application/pdf')},
               data={'meta': '{}', 'replaces': board['P-11']['documents'][0]['id']})
    assert r.status_code == 201, r.text
    stab = linked_pdf('Stability summary: the batches are those of the batch analyses', ['file:///C:/Dossier/Batch%20Analyses.docx', 'nowhere.pdf',
                                                                                           'https://www.edaegypt.gov.eg'])
    r = c.post(f'/api/dossiers/{did}/slots/P-16/documents', files={'file': ('stability.pdf', io.BytesIO(stab), 'application/pdf')},
               data={'meta': '{}', 'replaces': board['P-16']['documents'][0]['id']})
    assert r.status_code == 201, r.text
    e = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32']})
    assert e.status_code == 201, e.text
    info = e.json()['sequences']['ectd32']
    assert info['links']['rewritten'] == 1 and [u['link'] for u in info['links']['unresolved']] == ['nowhere.pdf'], info['links']
    z = zipfile.ZipFile(io.BytesIO(c.get(e.json()['downloads']['ectd32']).content))
    names = z.namelist()
    sp = next(n for n in names if '/32p8-stab/' in n and n.endswith('.pdf'))
    bp = next(n for n in names if '/32p54-batch-analys/' in n and n.endswith('.pdf'))
    got = links_of(z.read(sp))
    want = posixpath.relpath(bp, posixpath.dirname(sp))
    assert ('/GoToR', want) in got and ('/URI', 'https://www.edaegypt.gov.eg') in got                     # web links are left alone
    assert e.json()['validation']['eCTD 3.2.2']['ok'], e.json()['validation']
    # the next sequence changes only the stability summary: its link reaches the batch analyses where they stayed, in 0000
    board = {s['slot_id']: s for s in c.get(f'/api/dossiers/{did}/board').json()['slots']}
    stab2 = linked_pdf('Stability summary v2 with 24 months', ['file:///C:/Dossier/Batch%20Analyses.docx'])
    c.post(f'/api/dossiers/{did}/slots/P-16/documents', files={'file': ('stability.pdf', io.BytesIO(stab2), 'application/pdf')},
           data={'meta': '{}', 'replaces': board['P-16']['documents'][0]['id']})
    cover = make_pdf(tmp_path / 'c1.pdf', 'cover 0001').read_bytes()
    c.post(f'/api/dossiers/{did}/slots/M1-43/documents', files={'file': ('cover-0001.pdf', io.BytesIO(cover), 'application/pdf')},
           data={'meta': '{}', 'replaces': board['M1-43']['documents'][0]['id']})
    sub = {'type': 'var-pac-b', 'unit': 'initial', 'mode': 'single', 'description': 'PAC-B', 'tracking': 'P-VAR-0001'}
    e2 = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32'], 'submission': sub})
    assert e2.status_code == 201, e2.text
    z2 = zipfile.ZipFile(io.BytesIO(c.get(e2.json()['downloads']['ectd32']).content))
    sp2 = next(n for n in z2.namelist() if '/32p8-stab/' in n and n.endswith('.pdf'))
    (act, to), = links_of(z2.read(sp2))
    seq_dir = posixpath.dirname(posixpath.dirname(sp2.split('/m3/')[0] + '/m3/x'))
    assert act == '/GoToR' and to.startswith('../') and '/0000/m3/' in to and to.endswith(bp.split('/0000/')[-1].split('/', 0)[0].rsplit('/', 1)[-1])
    assert posixpath.normpath(posixpath.join(posixpath.dirname(sp2), to)).endswith(bp.split('/', 1)[-1].split('/', 1)[-1] if bp.count('/0000/') else bp)
