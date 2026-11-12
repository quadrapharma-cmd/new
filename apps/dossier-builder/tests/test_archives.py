"""Compressed files: an archive is opened and the documents inside it are taken like uploads. ZIP, TAR and a single packed file are
read with the standard library (every edition); RAR and 7z go through the unpacker of the machine and are refused, with the reason,
where there is none (the browser edition). Names keep their Arabic, lose «..», drive letters and system files; an archive that
expands too much, holds too many files or needs a password is refused or reported, never half-taken in silence.
Made-up data («Dermacure»); the RAR samples are libarchive's public test files (web/vendor.sh), skipped when absent."""
import bz2, gzip, io, json, lzma, pathlib, struct, tarfile, zipfile, zlib
import pytest
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine import archives
from dossier_engine.app.api import create_app

DATA = pathlib.Path(__file__).parent / 'data'
RAR = pathlib.Path(__file__).resolve().parents[1] / 'web' / 'vendor' / 'arch' / 'test'
PRICING = 'Pricing Certificate\nProduct: Dermacure 2 % cream\nPrice: EGP 45.00'
STABILITY = 'Stability Study Report\nProduct: Dermacure\nStorage condition: 30 C / 65 % RH'
needs_tool = pytest.mark.skipif(not archives.tools(), reason='no RAR/7z unpacker on this machine (bsdtar, 7z, unrar or unar)')


def zipped(entries, **kw):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED, **kw) as z:
        for name, data in entries:
            z.writestr(name, data)
    return b.getvalue()


def names(r):
    return [n for n, _ in r['files']]


def test_a_zip_gives_its_documents_and_leaves_the_system_files(tmp_path):
    pdf = make_pdf(tmp_path / 'p.pdf', 'Pricing Certificate').read_bytes()
    docx = (DATA / 'office' / 'slides.pptx').read_bytes()
    z = zipped([('Module 1/pricing.pdf', pdf), ('Module 1/slides.pptx', docx), ('ثبات/تقرير الثبات.txt', STABILITY.encode()),
                ('__MACOSX/Module 1/._pricing.pdf', b'x'), ('Module 1/.DS_Store', b'x'), ('Thumbs.db', b'x'), ('Module 1/~$draft.docx', b'x'), ('empty dir/', b'')])
    r = archives.unpack('dossier.zip', z)
    assert r['kind'] == 'zip' and names(r) == ['Module 1/pricing.pdf', 'Module 1/slides.pptx', 'ثبات/تقرير الثبات.txt']
    assert dict(r['files'])['Module 1/pricing.pdf'] == pdf and r['skipped'] == []


def test_an_office_file_is_not_an_archive():
    for n in ('slides.pptx', 'sheet.xlsx', 'letter.odt', 'sheet.ods'):
        assert archives.archive_kind(n, (DATA / 'office' / n).read_bytes()) is None, n      # a zip inside, a document outside
    assert archives.archive_kind('x.zip', zipped([('a.txt', b'a')])) == 'zip'
    assert archives.archive_kind('x.pdf', b'%PDF-1.7') is None
    with pytest.raises(archives.ArchiveError) as e:
        archives.unpack('x.pdf', b'%PDF-1.7')
    assert e.value.code == 'E-ARCHIVE'


def test_names_from_windows_keep_their_arabic():
    name = 'شهادة التسعير.pdf'
    for cp in ('cp1256', 'utf-8'):                              # Windows wrote the name in its code page, macOS in UTF-8, neither set the UTF-8 flag
        raw = name.encode(cp)
        hold = b'N' * len(raw)                                  # an ASCII name of the same length, then the raw bytes in its place (both headers)
        data = zipped([(hold.decode(), b'%PDF-1.4 x')]).replace(hold, raw)
        assert data.count(raw) == 2 and not zipfile.ZipFile(io.BytesIO(data)).infolist()[0].flag_bits & 0x800
        assert names(archives.unpack('a.zip', data)) == [name], cp


def test_a_name_never_leaves_the_archive():
    z = zipped([('../../etc/passwd.txt', b'a'), ('C:\\Users\\me\\secret.txt', b'b'), ('/abs/path.txt', b'c'), ('ok/./x/../y.txt', b'd')])
    assert names(archives.unpack('a.zip', z)) == ['etc/passwd.txt', 'Users/me/secret.txt', 'abs/path.txt', 'ok/x/y.txt']


def test_an_archive_that_expands_too_much_is_refused(monkeypatch):
    bomb = zipped([('zeros.bin', b'\0' * (120 * 1024 * 1024))])
    assert len(bomb) < 200 * 1024
    with pytest.raises(archives.ArchiveError) as e:
        archives.unpack('bomb.zip', bomb)
    assert e.value.code == 'E-ARCHIVE-BIG'
    monkeypatch.setattr(archives, 'MAX_FILES', 3)
    with pytest.raises(archives.ArchiveError) as e:
        archives.unpack('many.zip', zipped([(f'{i}.txt', b'x') for i in range(5)]))
    assert e.value.code == 'E-ARCHIVE-BIG' and '3' in e.value.en
    monkeypatch.setattr(archives, 'MAX_FILES', 600)
    monkeypatch.setattr(archives, 'MAX_TOTAL', 1000)
    with pytest.raises(archives.ArchiveError) as e:                               # the real size is counted, whatever the archive declares
        archives.unpack('big.tar', tarred([('a.txt', b'x' * 600), ('b.txt', b'x' * 600)]))
    assert e.value.code == 'E-ARCHIVE-BIG'


def encrypted(data, which=None):
    """Mark entries as needing a password (flag bit 0) in the local headers and the central directory."""
    d = bytearray(data)
    n = 0
    for sig, off in ((b'PK\x03\x04', 6), (b'PK\x01\x02', 8)):
        i, k = d.find(sig), 0
        while i >= 0:
            if which is None or k in which:
                d[i + off] |= 1
                n += 1
            k += 1
            i = d.find(sig, i + 4)
    assert n
    return bytes(d)


def test_a_password_is_reported_never_guessed():
    z = zipped([('open.txt', b'readable'), ('locked.txt', b'secret')])
    r = archives.unpack('a.zip', encrypted(z, which={1}))
    assert names(r) == ['open.txt'] and r['skipped'] == [{'name': 'locked.txt', 'why': 'password'}]
    with pytest.raises(archives.ArchiveError) as e:                               # nothing readable at all: say why
        archives.unpack('a.zip', encrypted(z))
    assert e.value.code == 'E-ARCHIVE-PASSWORD' and 'كلمة سر' in e.value.ar


def tarred(entries, mode='w', links=()):
    b = io.BytesIO()
    with tarfile.open(fileobj=b, mode=mode) as t:
        for name, data in entries:
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            t.addfile(ti, io.BytesIO(data))
        for name, target in links:
            ti = tarfile.TarInfo(name)
            ti.type, ti.linkname = tarfile.SYMTYPE, target
            t.addfile(ti)
    return b.getvalue()


@pytest.mark.parametrize('mode,kind', [('w', 'tar'), ('w:gz', 'gz'), ('w:bz2', 'bz2'), ('w:xz', 'xz')])
def test_tar_of_every_kind(mode, kind):
    t = tarred([('Module 3/stability.txt', STABILITY.encode()), ('./تسعير.txt', PRICING.encode())], mode, links=[('link.txt', '/etc/passwd')])
    r = archives.unpack('dossier.tar' + ('' if kind == 'tar' else '.' + kind), t)
    assert r['kind'] == kind and names(r) == ['Module 3/stability.txt', 'تسعير.txt']
    assert r['skipped'] == [{'name': 'link.txt', 'why': 'link'}]                   # a link is never followed


def test_a_tar_cut_short_keeps_what_was_read():
    t = tarred([('first.txt', b'a' * 3000), ('second.txt', b'b' * 3000), ('third.txt', b'c' * 3000)])
    r = archives.unpack('cut.tar', t[:5000])                                        # the download stopped in the second file
    assert names(r) == ['first.txt'] and r['skipped'] and r['skipped'][-1]['why'] == 'unreadable'


def test_a_method_this_python_does_not_have_is_said_not_crashed(monkeypatch):
    doc = PRICING.encode()
    xz, tar_xz = lzma.compress(doc), tarred([('a.txt', doc)], 'w:xz')
    monkeypatch.setattr(archives, 'lzma', None)                                     # the browser edition's Python has no xz
    for name, data in (('pricing.txt.xz', xz), ('dossier.tar.xz', tar_xz)):
        with pytest.raises(archives.ArchiveError) as e:
            archives.unpack(name, data)
        assert e.value.code == 'E-ARCHIVE-TOOL' and 'ZIP' in e.value.ar
    assert names(archives.unpack('d.zip', zipped([('a.txt', doc)]))) == ['a.txt']   # ZIP, TAR and gzip need nothing extra
    assert names(archives.unpack('d.tar.gz', tarred([('a.txt', doc)], 'w:gz'))) == ['a.txt']


def test_one_file_packed_by_itself():
    doc = PRICING.encode()
    assert archives.unpack('pricing.txt.gz', gzip.compress(doc))['files'] == [('pricing.txt', doc)]
    co = zlib.compressobj(9, zlib.DEFLATED, -15)                                    # gzip remembers the name it packed (as the tool writes it: raw UTF-8)
    named = b'\x1f\x8b\x08\x08' + b'\0' * 4 + b'\x00\x03' + 'شهادة.txt'.encode() + b'\0' + co.compress(doc) + co.flush() + struct.pack('<II', zlib.crc32(doc), len(doc))
    assert gzip.decompress(named) == doc
    assert archives.unpack('download.gz', named)['files'] == [('شهادة.txt', doc)]
    assert archives.unpack('pricing.txt.bz2', bz2.compress(doc))['files'] == [('pricing.txt', doc)]
    assert archives.unpack('pricing.txt.xz', lzma.compress(doc))['files'] == [('pricing.txt', doc)]
    ppt = archives.unpack('slides.ppt.gz', (DATA / 'office' / 'slides.ppt.gz').read_bytes())['files']
    assert [n for n, _ in ppt] == ['slides.ppt'] and ppt[0][1][:4] == b'\xd0\xcf\x11\xe0'


def test_an_archive_inside_an_archive_is_opened_too():
    inner = zipped([('stability.txt', STABILITY.encode())])
    deep = zipped([('level3.zip', zipped([('too deep.txt', b'x')]))])
    outer = zipped([('pricing.txt', PRICING.encode()), ('Module 3.zip', inner), ('more.zip', zipped([('deep.zip', deep)]))])
    r = archives.unpack('all.zip', outer)
    assert names(r) == ['pricing.txt', 'Module 3/stability.txt', 'more/deep/level3.zip']        # two levels are opened, the third stays a file
    with pytest.raises(archives.ArchiveError) as e:
        archives.unpack('bad.zip', b'PK\x03\x04' + b'garbage' * 20)
    assert e.value.code == 'E-ARCHIVE'
    r = archives.unpack('part.zip', zipped([('good.txt', b'ok'), ('broken.zip', b'PK\x03\x04' + b'garbage' * 20)]))
    assert names(r) == ['good.txt', 'broken.zip'] or (names(r) == ['good.txt'] and r['skipped'])     # a damaged inner archive never loses the rest


def test_without_an_unpacker_a_rar_is_refused_with_the_reason(monkeypatch):
    monkeypatch.setattr(archives, 'tools', lambda: [])                              # the browser edition
    for head, label in ((b'Rar!\x1a\x07\x00', 'RAR'), (b'Rar!\x1a\x07\x01\x00', 'RAR'), (b"7z\xbc\xaf'\x1c", '7z')):
        with pytest.raises(archives.ArchiveError) as e:
            archives.unpack('x', head + b'\0' * 64)
        assert e.value.code == 'E-ARCHIVE-TOOL' and label in e.value.en and 'ZIP' in e.value.ar


@needs_tool
def test_a_7z_with_arabic_names():
    r = archives.unpack('dermacure.7z', (DATA / 'archives' / 'dermacure.7z').read_bytes())
    assert r['kind'] == '7z' and sorted(names(r)) == ['Module 1/pricing certificate.txt', 'ثبات.txt']
    assert b'Dermacure' in dict(r['files'])['Module 1/pricing certificate.txt']


@needs_tool
@pytest.mark.parametrize('name,inside', [('test_read_format_rar_compress_normal.rar', {'LibarchiveAddingTest.html': 20111, 'testdir/test.txt': 20, 'testdir/LibarchiveAddingTest.html': 20111}),
                                         ('test_read_format_rar5_compressed.rar', {'test.bin': 1200}), ('test_read_format_rar5_stored.rar', {'helloworld.txt': 29})])
def test_rar_old_and_new(name, inside):
    if not (RAR / name).exists():
        pytest.skip('public RAR samples not fetched (web/vendor.sh)')
    r = archives.unpack(name, (RAR / name).read_bytes())
    assert r['kind'] == 'rar' and {n: len(b) for n, b in r['files']} == inside
    assert all(s['why'] == 'link' for s in r['skipped'])


def cut(body):
    """The framed answer of /api/archives/unpack → (header, [(name, bytes)])."""
    assert body[:5] == b'DBAR1'
    n = int.from_bytes(body[5:9], 'big')
    head = json.loads(body[9:9 + n])
    pos, out = 9 + n, []
    for f in head['files']:
        out.append((f['name'], body[pos:pos + f['size']]))
        pos += f['size']
    assert pos == len(body)
    return head, out


def test_the_page_gets_the_files_back_in_one_answer(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'p.pdf', 'Pricing Certificate').read_bytes()
    z = zipped([('Module 1/pricing.pdf', pdf), ('ثبات.txt', STABILITY.encode())])
    r = c.post('/api/archives/unpack', files={'file': ('dossier.zip', z, 'application/zip')}, headers={'X-DB': '1'})
    assert r.status_code == 200
    head, files = cut(r.content)
    assert head['kind'] == 'zip' and files == [('Module 1/pricing.pdf', pdf), ('ثبات.txt', STABILITY.encode())]
    r = c.post('/api/archives/unpack', files={'file': ('dermacure.tar.gz', (DATA / 'archives' / 'dermacure.tar.gz').read_bytes(), 'application/gzip')}, headers={'X-DB': '1'})
    assert sorted(n for n, _ in cut(r.content)[1]) == ['Module 1/pricing certificate.txt', 'ثبات.txt']
    bad = c.post('/api/archives/unpack', files={'file': ('x.pdf', pdf, 'application/pdf')}, headers={'X-DB': '1'})
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-ARCHIVE' and bad.json()['detail']['ar']
    assert not list((tmp_path / 'ws' / 'blobs').iterdir())                         # nothing is stored by looking inside an archive
