"""Each PDF rule fires on its fixture and not on clean files (01-PLAN §3 «Checks»)."""
import pytest
from pypdf import PdfWriter, PdfReader
from pypdf.generic import NameObject, DictionaryObject
from fixtures_pdf import make_pdf
from dossier_engine.checks.pdf import check
from dossier_engine.guard import assert_allowed, LockedError


def rules(rep):
    return {f.rule for f in rep.findings}


@pytest.fixture()
def clean(tmp_path):
    return make_pdf(tmp_path / 'clean.pdf', 'Composition certificate')


def _rewrite(src, dst, fn):
    w = PdfWriter(clone_from=str(src))
    fn(w)
    with open(dst, 'wb') as f:
        w.write(f)
    return dst


def test_clean_passes(clean):
    r = check(str(clean), 'company_letter')
    assert r.findings == [] and r.status == 'conforming'
    assert r.info['version'] == '1.4'


def test_zero_byte(tmp_path):
    p = tmp_path / 'empty.pdf'
    p.write_bytes(b'')
    assert 'EG-PF-16.5' in rules(check(str(p)))


def test_corrupt(tmp_path, clean):
    p = tmp_path / 'corrupt.pdf'
    p.write_bytes(clean.read_bytes()[:200])
    r = check(str(p), 'third_party_certificate')
    assert 'EG-PF-16.5' in rules(r) and r.findings[0].action == 're_obtain'


def test_not_pdf(tmp_path):
    p = tmp_path / 'x.pdf'
    p.write_bytes(b'PK\x03\x04 this is a zip')
    assert 'EG-PF-16.5' in rules(check(str(p)))


def test_pdf_13(tmp_path, clean):
    p = tmp_path / 'old.pdf'
    p.write_bytes(clean.read_bytes().replace(b'%PDF-1.4', b'%PDF-1.3', 1))
    r = check(str(p))
    assert 'EG-PF-16.1' in rules(r) and r.status == 'conforming'                 # an eCTD-readiness rule: not the One Submission's
    assert next(f for f in r.findings if f.rule == 'EG-PF-16.1').scope == 'ectd'


def test_password_to_open(tmp_path, clean):
    p = _rewrite(clean, tmp_path / 'pw.pdf', lambda w: w.encrypt(user_password='secret', owner_password='o'))
    assert 'EG-PF-16.2' in rules(check(str(p)))


def test_restrictions(tmp_path, clean):
    p = _rewrite(clean, tmp_path / 'restr.pdf', lambda w: w.encrypt(user_password='', owner_password='owner', permissions_flag=0))
    r = check(str(p), 'third_party_certificate')
    assert 'EG-PF-16.3' in rules(r) and r.findings[0].action == 're_obtain'
    assert check(str(p), 'company_letter').findings[0].action == 'auto_fix'


def test_scan_without_text(tmp_path):
    w = PdfWriter()
    w.add_blank_page(595, 842)
    p = tmp_path / 'scan.pdf'
    with open(p, 'wb') as f:
        w.write(f)
    p.write_bytes(p.read_bytes().replace(b'%PDF-1.3', b'%PDF-1.4', 1))   # pypdf writes 1.3 by default
    assert check(str(p), 'third_party_certificate').status == 'non_conforming'    # a scanned certificate too: every document searchable (note 4)
    r = check(str(p), 'company_technical')
    assert 'NTA065-N4' in rules(r) and r.status == 'non_conforming'
    assert check(str(p), 'generated').findings[0].action == 'rebuild'


def test_portfolio(tmp_path, clean):
    def add(w):
        w._root_object[NameObject('/Collection')] = DictionaryObject()
    p = _rewrite(clean, tmp_path / 'portfolio.pdf', add)
    assert 'EG-BP-E23' in rules(check(str(p)))


def test_javascript(tmp_path, clean):
    p = _rewrite(clean, tmp_path / 'js.pdf', lambda w: w.add_js('app.alert(1);'))
    assert 'PDF-JS' in rules(check(str(p)))


def test_long_and_unicode_names(tmp_path, clean):
    p = tmp_path / ('a' * 70 + '.pdf')
    p.write_bytes(clean.read_bytes())
    long_name = check(str(p))
    assert 'EG-PF-15.4' in rules(long_name) and long_name.status == 'conforming'       # the export gives the file its eCTD name
    q = tmp_path / 'شهادة GMP.pdf'
    q.write_bytes(clean.read_bytes())
    r = check(str(q), ectd_name=True)
    assert 'ICH-NAME' in rules(r) and r.status == 'conforming'


# ---- read-only evidence (PLAN principle 3; negative test of P1 acceptance) ----
@pytest.mark.parametrize('cls', ['third_party_certificate', 'eda_document', 'executed_record', 'signed_scan'])
@pytest.mark.parametrize('op', ['edit_text', 'redact', 'replace_page', 'retype', 'regenerate'])
def test_locked_content_edit_impossible(cls, op):
    audit = []
    with pytest.raises(LockedError, match='E-LOCKED'):
        assert_allowed(cls, op, audit)
    assert audit == [{'event': 'E-LOCKED', 'doc_class': cls, 'op': op}]


def test_locked_allows_placement():
    for op in ('rename', 'place', 'split_pages', 'add_bookmarks', 'pdf_version_normalise'):
        assert assert_allowed('third_party_certificate', op)
    with pytest.raises(LockedError):
        assert_allowed('third_party_certificate', 'remove_security')     # only the issuer can
    with pytest.raises(LockedError):
        assert_allowed('executed_record', 'split_pages')                 # placement and the version line only
    assert assert_allowed('executed_record', 'pdf_version_normalise')
    with pytest.raises(ValueError):
        assert_allowed('company_technical', 'add_ocr_layer')             # no OCR in the program


def test_generated_is_editable():
    assert assert_allowed('generated', 'regenerate') and assert_allowed('company_letter', 'edit_text')
