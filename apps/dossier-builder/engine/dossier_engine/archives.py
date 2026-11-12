"""Compressed files. An archive is unpacked and every document inside it is taken like an upload.

ZIP, TAR (also .tar.gz / .tgz, .tar.bz2, .tar.xz) and a single file packed as .gz / .bz2 / .xz are opened with the standard library,
so every edition reads them, the browser one included. RAR (old and RAR5), 7z and whatever else libarchive reads go through the
unpacker the machine has: `tar` on Windows 10+ and on macOS is bsdtar, else 7-Zip, unrar or unar. The browser edition has no such
tool: there a RAR or a 7z is refused with that reason and the person unpacks it (or zips it).

Safety: nothing is written outside a private temporary folder; names lose drive letters, «..» and leading slashes; an archive is
limited in files, in total size and in how much it expands (a «zip bomb» is refused); entries that need a password, links and
devices are skipped and reported; system files (`__MACOSX`, `Thumbs.db`, `~$…`) are left out."""
import io
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
import zlib

try:                                                    # not in every build of Python: the browser edition has neither xz nor, sometimes, bz2
    import bz2
except ImportError:
    bz2 = None
try:
    import lzma
except ImportError:
    lzma = None
_DAMAGED = (tarfile.TarError, EOFError, OSError, zlib.error) + ((lzma.LZMAError,) if lzma else ())

BROWSER = sys.platform == 'emscripten'            # the browser edition holds everything in the page's memory: smaller limits there
MAX_FILES = 600
MAX_TOTAL = (200 if BROWSER else 800) * 1024 * 1024
MAX_FILE = (100 if BROWSER else 300) * 1024 * 1024
MAX_RATIO = 250                      # uncompressed / compressed, for archives that expand past 100 MB
EXTENSIONS = ('.zip', '.rar', '.7z', '.tar', '.tgz', '.tbz', '.tbz2', '.txz', '.gz', '.bz2', '.xz')
SYSTEM = re.compile(r'(^|/)(__MACOSX/|\.DS_Store$|Thumbs\.db$|desktop\.ini$|~\$[^/]*$|\._[^/]*$|\.~lock\.[^/]*$)', re.I)


class ArchiveError(Exception):
    def __init__(self, code, en, ar):
        super().__init__(en)
        self.code, self.en, self.ar = code, en, ar


def archive_kind(name, data):
    """'zip' | 'tar' | 'gz' | 'bz2' | 'xz' | 'rar' | '7z' | None — an archive by its bytes (an office file is a zip too: it is not one)."""
    d = data or b''
    if d[:4] in (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'):
        try:
            names = zipfile.ZipFile(io.BytesIO(d)).namelist()
        except Exception:
            return None
        if any(n in names for n in ('word/document.xml', 'xl/workbook.xml', 'ppt/presentation.xml', '[Content_Types].xml')) or ('mimetype' in names and 'content.xml' in names):
            return None
        return 'zip'
    if d[:7] == b'Rar!\x1a\x07\x00' or d[:8] == b'Rar!\x1a\x07\x01\x00':
        return 'rar'
    if d[:6] == b"7z\xbc\xaf'\x1c":
        return '7z'
    if d[257:262] == b'ustar':
        return 'tar'
    if d[:3] == b'\x1f\x8b\x08':
        return 'gz'
    if d[:3] == b'BZh' and d[3:4].isdigit():
        return 'bz2'
    if d[:6] == b'\xfd7zXZ\x00':
        return 'xz'
    return None


def _clean(path):
    path = (path or '').replace('\\', '/')
    path = re.sub(r'^[A-Za-z]:', '', path)
    parts = [p for p in path.split('/') if p not in ('', '.', '..')]
    return '/'.join(re.sub(r'[\x00-\x1f]', '', p).strip() for p in parts if p.strip()) or 'file'


def _zip_name(info):
    """A name written without the UTF-8 flag: UTF-8 when it is valid (macOS), else the Arabic Windows code pages, else as it reads."""
    if info.flag_bits & 0x800:
        return info.filename
    try:
        raw = info.filename.encode('cp437')
    except UnicodeEncodeError:
        return info.filename
    if all(b < 0x80 for b in raw):
        return info.filename
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        pass
    best, score = info.filename, 0
    for cp in ('cp1256', 'cp720'):
        try:
            s = raw.decode(cp)
        except (UnicodeDecodeError, LookupError):
            continue
        n = sum(1 for ch in s if 'ء' <= ch <= 'ي')
        if n > score and n >= sum(1 for b in raw if b >= 0x80) * 0.7:
            best, score = s, n
    return best


class _Take:
    """What comes out of an archive, within the limits."""

    def __init__(self):
        self.files, self.skipped, self.total = [], [], 0

    def add(self, path, data):
        path = _clean(path)
        if SYSTEM.search(path):
            return
        if len(self.files) >= MAX_FILES:
            raise ArchiveError('E-ARCHIVE-BIG', f'The archive holds more than {MAX_FILES} files: unpack it and choose what the dossier needs.',
                               f'الأرشيف فيه أكتر من {MAX_FILES} ملف: فكّه واختار اللي الملف محتاجه.')
        self.total += len(data)
        if self.total > MAX_TOTAL:
            raise ArchiveError('E-ARCHIVE-BIG', f'The archive unpacks to more than {MAX_TOTAL >> 20} MB: unpack it and choose what the dossier needs.',
                               f'الأرشيف بيتفك لأكتر من {MAX_TOTAL >> 20} ميجا: فكّه واختار اللي الملف محتاجه.')
        self.files.append((path, data))

    def skip(self, path, why):
        self.skipped.append({'name': _clean(path), 'why': why})


def _unzip(data, take):
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ArchiveError('E-ARCHIVE', 'The ZIP file is damaged.', 'ملف الـ ZIP تالف.')
    infos = [i for i in z.infolist() if not i.is_dir()]
    declared = sum(i.file_size for i in infos)
    if declared > MAX_TOTAL or (declared > 100 * 1024 * 1024 and declared > MAX_RATIO * max(1, len(data))):
        raise ArchiveError('E-ARCHIVE-BIG', 'The archive expands too much to be opened safely: unpack it and choose what the dossier needs.',
                           'الأرشيف بيتفك لحجم كبير جدًا: فكّه واختار اللي الملف محتاجه.')
    for i in infos:
        name = _zip_name(i)
        if i.flag_bits & 0x1:
            take.skip(name, 'password')
        elif i.file_size > MAX_FILE:
            take.skip(name, 'too large')
        else:
            try:
                take.add(name, z.read(i))
            except ArchiveError:
                raise
            except Exception:                              # an unsupported method, a bad checksum
                take.skip(name, 'unreadable')


def _untar(data, take):
    try:
        t = tarfile.open(fileobj=io.BytesIO(data), mode='r:*')
    except tarfile.CompressionError:                      # packed with a method this build of Python does not have (xz in the browser edition)
        raise _no_method('TAR')
    except _DAMAGED:
        raise ArchiveError('E-ARCHIVE', 'The TAR file is damaged.', 'ملف الـ TAR تالف.')
    try:
        for m in t:
            if not m.isfile():
                if not m.isdir():
                    take.skip(m.name, 'link')
            elif m.size > MAX_FILE:
                take.skip(m.name, 'too large')
            else:
                f = t.extractfile(m)
                take.add(m.name, f.read() if f else b'')
    except _DAMAGED:                                      # cut short (a download that did not finish): what was read before the break is kept
        if not take.files:
            raise ArchiveError('E-ARCHIVE', 'The TAR file is damaged.', 'ملف الـ TAR تالف.')
        take.skip('…', 'unreadable')


def _no_method(label):
    return ArchiveError('E-ARCHIVE-TOOL', f'This {label} file is packed with a method this program cannot open here: unpack it first, or pack the files as ZIP.',
                        f'ملف الـ {label} ده مضغوط بطريقة البرنامج ما بيفتحهاش هنا: فكّه الأول، أو اضغط الملفات ZIP.')


def _gzip_name(data):
    """The name gzip remembers for the file it packed (FNAME in the header), or None."""
    if len(data) < 10 or not data[3] & 0x08:
        return None
    pos = 10
    if data[3] & 0x04:                                     # an extra field comes first
        pos += 2 + int.from_bytes(data[pos:pos + 2], 'little')
    end = data.find(b'\0', pos)
    if end <= pos or end - pos > 1024:
        return None
    raw = data[pos:end]
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin-1')


def _single(kind, name, data, take):
    """One file packed by itself (.gz, .bz2, .xz); a .tar inside goes on as a tar."""
    try:
        if kind == 'gz':
            d = zlib.decompressobj(47)
            out = d.decompress(data, MAX_FILE + 1)
            inner = _gzip_name(data)
        else:
            mod = bz2 if kind == 'bz2' else lzma
            if mod is None:
                raise _no_method(kind.upper())
            d = mod.BZ2Decompressor() if kind == 'bz2' else mod.LZMADecompressor()
            out, inner = d.decompress(data, MAX_FILE + 1), None
    except ArchiveError:
        raise
    except Exception:
        raise ArchiveError('E-ARCHIVE', 'The compressed file is damaged.', 'الملف المضغوط تالف.')
    if len(out) > MAX_FILE:
        raise ArchiveError('E-ARCHIVE-BIG', 'The compressed file is too large to be opened here.', 'الملف المضغوط أكبر من اللي يتفتح هنا.')
    if out[257:262] == b'ustar':
        return _untar(out, take)
    base = os.path.basename(name or 'file')
    take.add(inner or re.sub(r'\.(gz|bz2|xz)$', '', base, flags=re.I) or 'file', out)


def tools():
    """The unpackers this machine has for RAR, 7z and the rest, in the order they are tried."""
    if sys.platform == 'emscripten':
        return []
    found = []
    for exe in ('bsdtar', 'tar'):
        p = shutil.which(exe)
        if p and (exe == 'bsdtar' or _is_bsdtar(p)):
            found.append(('bsdtar', p))
            break
    for exe in ('7zz', '7z', '7za'):
        p = shutil.which(exe)
        if p:
            found.append(('7z', p))
            break
    for exe in ('unrar', 'unar'):
        p = shutil.which(exe)
        if p:
            found.append((exe, p))
    return found


_BSDTAR = {}
_QUIET = {'creationflags': 0x08000000} if sys.platform == 'win32' else {}      # Windows: no console window flashes when the unpacker runs


def _is_bsdtar(path):
    if path not in _BSDTAR:
        try:
            out = subprocess.run([path, '--version'], capture_output=True, text=True, timeout=20, **_QUIET).stdout
        except Exception:
            out = ''
        _BSDTAR[path] = 'bsdtar' in out or 'libarchive' in out
    return _BSDTAR[path]


def _external(kind, data, take):
    have = tools()
    if not have:
        label = 'RAR' if kind == 'rar' else '7z'
        raise ArchiveError('E-ARCHIVE-TOOL', f'A {label} archive needs an unpacker this program does not have here: unpack it first, or pack the files as ZIP.',
                           f'أرشيف {label} محتاج برنامج فك مش موجود هنا: فكّه الأول، أو اضغط الملفات ZIP.')
    env = dict(os.environ)
    if sys.platform != 'win32':
        env.update(LC_ALL='en_US.UTF-8' if sys.platform == 'darwin' else 'C.UTF-8', LANG='en_US.UTF-8' if sys.platform == 'darwin' else 'C.UTF-8')
    last = ''
    for tool, exe in have:
        with tempfile.TemporaryDirectory() as d:
            src, out = os.path.join(d, 'in.' + kind), os.path.join(d, 'out')
            os.mkdir(out)
            with open(src, 'wb') as f:
                f.write(data)
            cmd = {'bsdtar': [exe, '-xf', src, '-C', out], '7z': [exe, 'x', '-y', '-p', '-bso0', '-bsp0', '-o' + out, src],
                   'unrar': [exe, 'x', '-y', '-p-', '-inul', src, out + os.sep], 'unar': [exe, '-q', '-f', '-o', out, src]}[tool]
            try:
                r = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL, timeout=600, env=env, **_QUIET)
            except Exception as e:
                last = str(e)
                continue
            got = False
            for root, _dirs, names in os.walk(out):
                for n in sorted(names):
                    p = os.path.join(root, n)
                    rel = os.path.relpath(p, out)
                    if os.path.islink(p) or not os.path.isfile(p):
                        take.skip(rel, 'link')
                    elif os.path.getsize(p) > MAX_FILE:
                        take.skip(rel, 'too large')
                    else:
                        with open(p, 'rb') as f:
                            take.add(rel, f.read())
                        got = True
            if got:
                return tool
            last = (r.stderr or b'').decode('utf-8', 'replace')[-300:]
    if re.search(r'ncrypt|assword|passphrase', last, re.I):
        raise ArchiveError('E-ARCHIVE-PASSWORD', 'The archive is protected with a password: unpack it first.', 'الأرشيف عليه كلمة سر: فكّه الأول.')
    raise ArchiveError('E-ARCHIVE', 'The archive could not be opened: it may be damaged or of a kind the unpacker here does not read.',
                       'الأرشيف ما اتفتحش: ممكن يكون تالف أو من نوع البرنامج هنا ما بيفكّوش.')


def unpack(name, data, depth=0, take=None, prefix=''):
    """→ {'kind', 'tool', 'files': [(path, bytes)], 'skipped': [{'name', 'why'}]}. An archive inside the archive is opened too (two levels)."""
    kind = archive_kind(name, data)
    if not kind:
        raise ArchiveError('E-ARCHIVE', 'Not an archive this program opens.', 'ده مش أرشيف البرنامج بيفتحه.')
    top = take is None
    take = take or _Take()
    inner = _Take()
    inner.files, inner.skipped = [], take.skipped
    inner.total = take.total
    tool = {'zip': 'zipfile', 'tar': 'tarfile'}.get(kind, kind)
    if kind == 'zip':
        _unzip(data, inner)
    elif kind == 'tar':
        _untar(data, inner)
    elif kind in ('gz', 'bz2', 'xz'):
        _single(kind, name, data, inner)
    else:
        tool = _external(kind, data, inner)
    take.total = inner.total
    for path, blob in inner.files:
        sub = archive_kind(path, blob)
        if sub and depth < 2:
            try:
                unpack(path, blob, depth + 1, take, prefix + re.sub(r'\.[A-Za-z0-9]{1,5}$', '', path) + '/')
            except ArchiveError as e:
                take.skip(prefix + path, 'password' if e.code == 'E-ARCHIVE-PASSWORD' else 'unreadable')
        else:
            if len(take.files) >= MAX_FILES:
                raise ArchiveError('E-ARCHIVE-BIG', f'The archive holds more than {MAX_FILES} files: unpack it and choose what the dossier needs.',
                                   f'الأرشيف فيه أكتر من {MAX_FILES} ملف: فكّه واختار اللي الملف محتاجه.')
            take.files.append((prefix + path, blob))
    if top and not take.files and any(s['why'] == 'password' for s in take.skipped):
        raise ArchiveError('E-ARCHIVE-PASSWORD', 'The archive is protected with a password: unpack it first.', 'الأرشيف عليه كلمة سر: فكّه الأول.')
    return {'kind': kind, 'tool': tool, 'files': take.files, 'skipped': take.skipped}


def frame(result):
    """The unpacked files as one body for the page: «DBAR1», the length of a JSON header, the header ({kind, tool, files: [{name, size}],
    skipped}), then the files one after the other."""
    import json
    head = json.dumps({'kind': result['kind'], 'tool': result['tool'], 'skipped': result['skipped'],
                       'files': [{'name': n, 'size': len(b)} for n, b in result['files']]}, ensure_ascii=False).encode('utf-8')
    return b'DBAR1' + len(head).to_bytes(4, 'big') + head + b''.join(b for _n, b in result['files'])
