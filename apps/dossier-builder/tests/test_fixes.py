"""Auto-fix: each fixable defect is fixed and re-checked; evidence stays pixel-identical; signed PDFs untouched."""
import shutil
import pytest
from pypdf import PdfWriter
from fixtures_pdf import make_pdf
from dossier_engine.checks.pdf import check
from dossier_engine.fixes import apply, ops_for, same_pixels

needs_tools = pytest.mark.skipif(not (shutil.which('gs') and shutil.which('tesseract')), reason='ghostscript/tesseract missing')


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


@needs_tools
def test_ocr_on_scan(tmp_path):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new('RGB', (1240, 1754), 'white')
    ImageDraw.Draw(img).text((120, 200), 'GOOD MANUFACTURING PRACTICE CERTIFICATE', fill='black',
                             font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 40))
    p = tmp_path / 'scan.pdf'
    img.save(p, 'PDF', resolution=150)
    p.write_bytes(p.read_bytes().replace(b'%PDF-1.3', b'%PDF-1.4', 1) if p.read_bytes().startswith(b'%PDF-1.3') else p.read_bytes())
    assert 'NTA065-N4' in {f['rule'] for f in findings(p, 'company_technical')}
    r = fix(p, 'company_technical', tmp_path)
    assert 'add_ocr_layer' in [d['op'] for d in r['done']]
    assert 'NTA065-N4' not in {f.rule for f in r['report'].findings}
    r2 = fix(p, 'third_party_certificate', tmp_path)                         # OCR on evidence: allowed, pixels kept
    assert 'add_ocr_layer' in [d['op'] for d in r2['done']] and same_pixels(p, r2['path'])


def test_signed_pdf_never_rewritten(pdf13):
    pdf13.write_bytes(pdf13.read_bytes() + b'% /ByteRange [0 1 2 3]\n')
    r = apply(pdf13, findings(pdf13, 'third_party_certificate'), 'third_party_certificate')
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
    assert [d['op'] for d in r['done']] == ['add_bookmarks']
    from pypdf import PdfReader
    titles = [o.title for o in PdfReader(str(r['path'])).outline if not isinstance(o, list)]
    assert titles[0].startswith('3.2.P.1.1') and len(titles) >= 6
    assert 'NTA065-BM' not in {f.rule for f in r['report'].findings}
    r2 = fix(p, 'third_party_certificate', tmp_path)               # bookmarks on evidence: allowed, pixels identical
    assert [d['op'] for d in r2['done']] == ['add_bookmarks'] and same_pixels(p, r2['path'])


@needs_tools
def test_arabic_scan_ocr(tmp_path):
    """A real Arabic scan (rendered by LibreOffice, rasterised) becomes searchable Arabic text."""
    import subprocess
    from PIL import Image
    from dossier_engine.generate.docx_kit import new_doc, para, to_pdf
    if not shutil.which('soffice'):
        pytest.skip('LibreOffice missing')
    d = new_doc(draft=False)
    para(d, 'تشهد هيئة الدواء المصرية بأن المصنع مطابق لقواعد التصنيع الجيد', ar=True, size=18)
    d.save(tmp_path / 'ar.docx')
    src = to_pdf(tmp_path / 'ar.docx')
    subprocess.run(['gs', '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=pnggray', '-r200', f'-sOutputFile={tmp_path}/p.png', str(src)], check=True)
    scan = tmp_path / 'scan.pdf'
    Image.open(tmp_path / 'p.png').convert('RGB').save(scan, 'PDF', resolution=200)
    scan.write_bytes(scan.read_bytes().replace(b'%PDF-1.3', b'%PDF-1.4', 1))
    r = fix(scan, 'third_party_certificate', tmp_path)
    assert 'add_ocr_layer' in [x['op'] for x in r['done']]
    txt = subprocess.run(['pdftotext', str(r['path']), '-'], capture_output=True, text=True).stdout
    for w in ('هيئة', 'الدواء', 'المصرية', 'المصنع'):
        assert w in txt, txt
    assert same_pixels(scan, r['path'])
