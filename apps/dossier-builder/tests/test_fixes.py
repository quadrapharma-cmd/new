"""Auto-fix: each fixable defect is fixed and re-checked; evidence stays pixel-identical; signed PDFs untouched; the PDF version is
the version line alone (every other byte the same); no OCR — a scan is not «fixed» here."""
import shutil
import pytest
from pypdf import PdfWriter
from fixtures_pdf import make_pdf
from dossier_engine.checks.pdf import check
from dossier_engine.fixes import apply, ops_for, same_pixels

needs_tools = pytest.mark.skipif(not shutil.which('gs'), reason='ghostscript missing (the pixel check renders the pages)')


def findings(path, cls):
    return [f.to_dict() for f in check(str(path), cls).findings]


def fix(path, cls, tmp):
    r = apply(path, findings(path, cls), cls)
    if r['data']:
        out = tmp / 'fixed.pdf'
        out.write_bytes(r['data'])
        r['path'] = out
    return r


@pytest.fixture()
def pdf13(tmp_path):
    p = make_pdf(tmp_path / 'a.pdf', 'GMP certificate Example')
    p.write_bytes(p.read_bytes().replace(b'%PDF-1.4', b'%PDF-1.3', 1))
    return p


@needs_tools
def test_version_fixed_on_evidence_pixels_identical(pdf13, tmp_path):
    r = fix(pdf13, 'third_party_certificate', tmp_path)
    assert [d['op'] for d in r['done']] == ['pdf_version_normalise']
    assert r['report'].status == 'conforming' and r['report'].info['version'] == '1.7'
    assert same_pixels(pdf13, r['path'])


def test_the_version_line_alone_changes(pdf13):
    from dossier_engine.fixes import set_version_17
    old = pdf13.read_bytes()
    new = set_version_17(old)
    assert new is not None and len(new) == len(old) and new[:8] == b'%PDF-1.7'
    assert [i for i in range(len(old)) if old[i] != new[i]] == [7]                     # one byte: the version digit, nothing else
    r = apply(pdf13, findings(pdf13, 'executed_record'), 'executed_record')            # even on a locked record: only the version line
    assert r['data'] == new and [d['op'] for d in r['done']] == ['pdf_version_normalise']
    assert set_version_17(new) is None and set_version_17(b'%PDF-1.3 ' + b'/ByteRange [0 1 2 3]') is None    # 1.7 already; a signed file: never


def test_security_on_evidence_refused(tmp_path):
    src = make_pdf(tmp_path / 's.pdf', 'x')
    w = PdfWriter(clone_from=str(src)); w.encrypt(user_password='', owner_password='o', permissions_flag=0)
    p = tmp_path / 'sec.pdf'
    w.write(open(p, 'wb'))
    p.write_bytes(p.read_bytes().replace(b'%PDF-1.3', b'%PDF-1.4', 1))
    f = findings(p, 'third_party_certificate')
    assert f[0]['action'] == 're_obtain' and ops_for(f) == []           # nothing to auto-fix: re-obtain


@needs_tools
def test_security_removed_on_company_doc(tmp_path):
    src = make_pdf(tmp_path / 's.pdf', 'Composition certificate')
    w = PdfWriter(clone_from=str(src)); w.encrypt(user_password='', owner_password='o', permissions_flag=0)
    p = tmp_path / 'sec.pdf'
    w.write(open(p, 'wb'))
    r = fix(p, 'company_letter', tmp_path)
    assert 'remove_security' in [d['op'] for d in r['done']] and r['report'].status == 'conforming'


def test_javascript_removed(tmp_path):
    src = make_pdf(tmp_path / 's.pdf', 'x')
    w = PdfWriter(clone_from=str(src)); w.add_js('app.alert(1)')
    p = tmp_path / 'js.pdf'
    w.write(open(p, 'wb'))
    r = fix(p, 'company_technical', tmp_path)
    assert [d['op'] for d in r['done']] == ['remove_javascript', 'pdf_version_normalise'] or 'remove_javascript' in [d['op'] for d in r['done']]
    assert 'PDF-JS' not in {f.rule for f in r['report'].findings}


def test_a_scan_is_made_searchable_where_pdfcraft_reads_scans(tmp_path):
    """A scan blocks (NP.CAPP.065 v5 note 4). Where PdfCraft reads scans (OCR) «make searchable» is its fix — and a scan with no words on
    it is not «fixed»: the fix says so and the document stays as it was. Elsewhere the text layer is made when scanning."""
    from dossier_engine import pdfcraft
    PIL = pytest.importorskip('PIL.Image')
    from PIL import ImageDraw
    img = PIL.new('RGB', (1240, 1754), 'white')
    ImageDraw.Draw(img).rectangle([100, 100, 600, 160], fill='black')                # a black bar, as a picture: no words
    p = tmp_path / 'scan.pdf'
    img.save(p, 'PDF', resolution=150)
    ocr = bool(pdfcraft.ocr_info())
    for cls in ('company_technical', 'third_party_certificate'):
        f = findings(p, cls)
        n4 = [x for x in f if x['rule'] == 'NTA065-N4']
        assert n4 and n4[0]['severity'] == 'block' and 'searchable' in n4[0]['en'], cls
        assert n4[0]['action'] == ('auto_fix' if ocr else 'user_fix') and (('make_searchable' in ops_for(f)) == ocr)
        if ocr:
            out = apply(p, f, cls)
            assert out['data'] is None and any(r['op'] == 'make_searchable' and 'no text could be read' in r['en'].lower() and 'امسحه' in r['ar'] for r in out['refused'])


def test_signed_pdf_never_rewritten(pdf13):
    pdf13.write_bytes(pdf13.read_bytes() + b'% /ByteRange [0 1 2 3]\n')
    f = findings(pdf13, 'third_party_certificate')
    v = next(x for x in f if x['rule'] == 'EG-PF-16.1')
    assert v['severity'] == 'warn' and v['action'] == 'none' and 'signed' in v['en'].lower()      # the version line is under the signature: left as it is
    assert apply(pdf13, f, 'third_party_certificate')['data'] is None
    r = apply(pdf13, [dict(v, action='auto_fix')], 'third_party_certificate')                     # and even when asked, a signed file is not rewritten
    assert r['data'] is None and 'signature' in r['refused'][0]['en']


def _long_doc(tmp_path, pages=12):
    """Multi-page text PDF with numbered headings (built with pypdf from the single-page fixture)."""
    from pypdf import PdfReader
    w = PdfWriter()
    for i in range(pages):
        p = make_pdf(tmp_path / f'p{i}.pdf', f'3.2.P.{i % 8 + 1}.{i // 8 + 1} Section {i}' if i % 2 == 0 else f'Body text page {i}')
        w.add_page(PdfReader(str(p)).pages[0])
    out = tmp_path / 'long.pdf'
    w.pdf_header = '%PDF-1.7'
    w.write(open(out, 'wb'))
    return out


@needs_tools
def test_bookmarks_added_from_headings(tmp_path):
    p = _long_doc(tmp_path)
    assert 'NTA065-BM' in {f['rule'] for f in findings(p, 'company_technical')}
    r = fix(p, 'company_technical', tmp_path)
    assert [d['op'] for d in r['done']] == ['add_bookmarks', 'doc_info']
    from pypdf import PdfReader
    titles = [o.title for o in PdfReader(str(r['path'])).outline if not isinstance(o, list)]
    assert titles[0].startswith('3.2.P.1.1') and len(titles) >= 6
    assert 'NTA065-BM' not in {f.rule for f in r['report'].findings}
    r2 = fix(p, 'third_party_certificate', tmp_path)               # bookmarks on evidence: allowed, pixels identical
    assert [d['op'] for d in r2['done']] == ['add_bookmarks'] and same_pixels(p, r2['path'])
