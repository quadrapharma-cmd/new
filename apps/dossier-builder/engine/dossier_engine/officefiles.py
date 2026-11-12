"""Every document format a company's folders hold, old and new, read from the inside with the standard library and lxml (which
the engine already uses), so every edition reads them, the browser one included:

  Word          .docx .docm .dotx (extract.docx_text) · .doc 97-2003 and 6/95 (msdoc) · Word 2003 XML
  Excel         .xlsx .xlsm .xltx · .xls 97-2003 (and 5/95) · Excel 2003 XML · .csv .tsv
  PowerPoint    .pptx .ppsx · .ppt 97-2003
  OpenDocument  .odt .ods .odp
  RTF · HTML · plain text (UTF-8, UTF-16, Windows-1256 / 1252)

`sniff(name, data)` says what a file is by its bytes (the name only when the bytes cannot say); `text(kind, data)` gives its text
the way the rules read a document: lines in their order, a table or sheet row as «cell | cell», a date as YYYY-MM-DD."""
import csv
import datetime
import io
import re
import struct
import zipfile

from . import msdoc

MAX_CHARS = 400000          # a workbook of a hundred thousand rows is not read to its end
MAX_ROWS = 4000

IMAGES = ((b'\x89PNG', 'png'), (b'\xff\xd8\xff', 'jpg'), (b'GIF8', 'gif'), (b'II*\x00', 'tif'), (b'MM\x00*', 'tif'), (b'BM', 'bmp'))
ARCHIVES = (b'Rar!\x1a\x07', b"7z\xbc\xaf'\x1c", b'\x1f\x8b\x08')
TEXT_EXT = ('.txt', '.csv', '.tsv', '.md', '.log', '.xml', '.json', '.htm', '.html')
OFFICE = ('docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'odt', 'ods', 'odp', 'rtf', 'html', 'text')        # what `text` reads
FAMILY = {'docx': 'word', 'doc': 'word', 'odt': 'word', 'rtf': 'word', 'xlsx': 'excel', 'xls': 'excel', 'ods': 'excel',
          'pptx': 'powerpoint', 'ppt': 'powerpoint', 'odp': 'powerpoint', 'html': 'text', 'text': 'text'}
# what the interface and the Drive listing accept, by extension (the bytes decide what the file really is)
EXTENSIONS = ('.pdf', '.docx', '.docm', '.dotx', '.dotm', '.doc', '.dot', '.rtf', '.odt', '.xlsx', '.xlsm', '.xltx', '.xls', '.xlt', '.ods', '.csv', '.tsv',
              '.pptx', '.ppsx', '.potx', '.ppt', '.pps', '.odp', '.txt', '.md', '.htm', '.html', '.xml', '.json',
              '.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.bmp', '.gif', '.heic', '.heif')
MIME = {'.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.doc': 'application/msword',
        '.docm': 'application/vnd.ms-word.document.macroEnabled.12', '.dotx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.template',
        '.dot': 'application/msword', '.rtf': 'application/rtf', '.odt': 'application/vnd.oasis.opendocument.text',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsm': 'application/vnd.ms-excel.sheet.macroEnabled.12',
        '.xls': 'application/vnd.ms-excel', '.xlt': 'application/vnd.ms-excel', '.ods': 'application/vnd.oasis.opendocument.spreadsheet', '.csv': 'text/csv',
        '.tsv': 'text/tab-separated-values', '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.ppsx': 'application/vnd.openxmlformats-officedocument.presentationml.slideshow', '.ppt': 'application/vnd.ms-powerpoint', '.pps': 'application/vnd.ms-powerpoint',
        '.odp': 'application/vnd.oasis.opendocument.presentation', '.txt': 'text/plain', '.md': 'text/markdown', '.htm': 'text/html', '.html': 'text/html',
        '.xml': 'application/xml', '.json': 'application/json', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp',
        '.tif': 'image/tiff', '.tiff': 'image/tiff', '.bmp': 'image/bmp', '.gif': 'image/gif', '.heic': 'image/heic', '.heif': 'image/heif'}


def media_type(filename, data=None):
    low = (filename or '').lower()
    ext = low[low.rfind('.'):] if '.' in low else ''
    if ext in MIME:
        return MIME[ext]
    return 'application/pdf' if (data or b'')[:5] == b'%PDF-' else 'application/octet-stream'


def _local(el):
    t = el.tag
    return t.rsplit('}', 1)[-1] if isinstance(t, str) else ''


def _xml(data):
    from lxml import etree
    return etree.fromstring(data, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False, recover=True))


def _is_text(data):
    head = data[:4096]
    if head[:2] in (b'\xff\xfe', b'\xfe\xff') or head[:3] == b'\xef\xbb\xbf':
        return True
    if not head or b'\x00' in head:
        return False
    return sum(1 for b in head if b < 9 or 13 < b < 32) < len(head) / 100


def sniff(name, data):
    """'pdf' | 'image' | one of OFFICE | 'archive' | 'other' — what the file is, by its bytes."""
    data, low = data or b'', (name or '').lower()
    if data[:5] == b'%PDF-' or (b'%PDF-' in data[:1024] and low.endswith('.pdf')):
        return 'pdf'
    if any(data.startswith(m) for m, _ in IMAGES) or (data[:4] == b'RIFF' and data[8:12] == b'WEBP') or data[4:8] == b'ftyp' and data[8:12] in (
            b'heic', b'heix', b'hevc', b'mif1', b'msf1', b'heif', b'avif'):
        return 'image'
    if data[:2] == b'PK':
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
            names = set(z.namelist())
            if 'word/document.xml' in names:
                return 'docx'
            if 'xl/workbook.xml' in names:
                return 'xlsx'
            if 'ppt/presentation.xml' in names:
                return 'pptx'
            if 'content.xml' in names:
                mt = z.read('mimetype').decode('latin-1') if 'mimetype' in names else ''
                return 'ods' if 'spreadsheet' in mt or low.endswith('.ods') else 'odp' if 'presentation' in mt or low.endswith('.odp') else 'odt'
        except Exception:
            pass
        return 'archive'
    if data[:8] == msdoc.MAGIC:
        try:
            streams = msdoc.streams(data)
        except Exception:
            streams = {}
        return 'doc' if 'WordDocument' in streams else 'xls' if ('Workbook' in streams or 'Book' in streams) else 'ppt' if 'PowerPoint Document' in streams else 'other'
    if any(data.startswith(m) for m in ARCHIVES):
        return 'archive'
    head = data[:3000].lstrip(b'\xef\xbb\xbf \t\r\n')
    if head.startswith(b'{\\rtf'):
        return 'rtf'
    if not _is_text(data):
        return 'other'
    if re.search(rb'<(!doctype\s+html|html[\s>]|body[\s>]|table[\s>])', head, re.I) and not head.startswith(b'<?mso-application'):
        return 'html'
    return 'text'


# ---------------------------------------------------------------- numbers and dates as a person reads them
DATE_IDS = set(range(14, 23)) | set(range(27, 37)) | set(range(45, 48)) | set(range(50, 59))


def _date_format(fmt_id, code):
    if code is None:
        return fmt_id in DATE_IDS
    plain = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.|_.|\*.', '', code)
    return bool(re.search(r'[dmyhs]', plain, re.I)) and not re.search(r'general|[0#?]', plain, re.I)


def _serial(v, base1904=False):
    """An Excel date serial as a date (and the time when it has one)."""
    try:
        if not (0 <= v < 2958466):
            return _num(v)
        d = datetime.datetime(1904, 1, 1) + datetime.timedelta(days=v) if base1904 else datetime.datetime(1899, 12, 30) + datetime.timedelta(days=v)
        d += datetime.timedelta(microseconds=500000)
        d = d.replace(microsecond=0)
        if v < 1:
            return d.strftime('%H:%M')
        return d.strftime('%Y-%m-%d') if (d.hour, d.minute, d.second) == (0, 0, 0) else d.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return _num(v)


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return ('%.10g' % f)


def _rows_text(rows):
    """rows: {row: {col: text}} → lines «a | b | c» (empty cells between two filled ones keep their place)."""
    out = []
    for r in sorted(rows)[:MAX_ROWS]:
        cells = {c: v for c, v in rows[r].items() if str(v).strip()}
        if not cells:
            continue
        first, last = min(cells), max(cells)
        out.append(' | '.join(str(cells.get(c, '')).strip() for c in range(first, last + 1)))
    return out


# ---------------------------------------------------------------- Excel 2007+ (.xlsx .xlsm .xltx)
def _col(ref):
    n = 0
    for ch in ref:
        if ch.isalpha():
            n = n * 26 + (ord(ch.upper()) - 64)
        else:
            break
    return n - 1


def _si_text(si):
    parts = []
    for ch in si:
        tag = _local(ch)
        if tag == 't':
            parts.append(ch.text or '')
        elif tag == 'r':
            parts += [t.text or '' for t in ch if _local(t) == 't']
    return ''.join(parts)


def xlsx_text(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    shared = [_si_text(si) for si in _xml(z.read('xl/sharedStrings.xml')) if _local(si) == 'si'] if 'xl/sharedStrings.xml' in names else []
    date_style = []
    if 'xl/styles.xml' in names:
        st, codes = _xml(z.read('xl/styles.xml')), {}
        for el in st.iter():
            if _local(el) == 'numFmt':
                codes[int(el.get('numFmtId') or 0)] = el.get('formatCode') or ''
        for el in st:
            if _local(el) == 'cellXfs':
                for xf in el:
                    i = int(xf.get('numFmtId') or 0)
                    date_style.append(_date_format(i, codes.get(i)))
    wb = _xml(z.read('xl/workbook.xml'))
    base1904 = any(_local(el) == 'workbookPr' and (el.get('date1904') or '') in ('1', 'true') for el in wb.iter())
    rels = {}
    if 'xl/_rels/workbook.xml.rels' in names:
        for r in _xml(z.read('xl/_rels/workbook.xml.rels')):
            target = (r.get('Target') or '').lstrip('/')
            rels[r.get('Id')] = target if target.startswith('xl/') else 'xl/' + target
    sheets = []
    for el in wb.iter():
        if _local(el) == 'sheet':
            rid = next((v for k, v in el.attrib.items() if k.endswith('}id')), None)
            if rels.get(rid) in names:
                sheets.append((el.get('name') or '', rels[rid]))
    if not sheets:
        sheets = [('', n) for n in sorted(names) if re.match(r'xl/worksheets/sheet\d+\.xml$', n)]
    out, size = [], 0
    for name, path in sheets:
        rows = {}
        for row in _xml(z.read(path)).iter():
            if _local(row) != 'row':
                continue
            r = int(row.get('r') or len(rows) + 1)
            if len(rows) >= MAX_ROWS:
                break
            cells, nxt = {}, 0
            for c in row:
                if _local(c) != 'c':
                    continue
                col = _col(c.get('r')) if c.get('r') else nxt
                nxt = col + 1
                t, v = c.get('t') or 'n', next((x.text for x in c if _local(x) == 'v'), None)
                if t == 'inlineStr':
                    val = ''.join(_si_text(x) for x in c if _local(x) == 'is')
                elif v is None:
                    continue
                elif t == 's':
                    val = shared[int(v)] if v.isdigit() and int(v) < len(shared) else ''
                elif t == 'b':
                    val = 'TRUE' if v == '1' else 'FALSE'
                elif t in ('str', 'e', 'd'):
                    val = v
                else:
                    s = int(c.get('s') or 0)
                    try:
                        val = _serial(float(v), base1904) if s < len(date_style) and date_style[s] else _num(v)
                    except ValueError:
                        val = v
                cells[col] = val
            rows[r] = cells
        lines = _rows_text(rows)
        if lines:
            if len(sheets) > 1 and name and not re.match(r'(sheet|ورقة)\s*\d+$', name, re.I):
                out.append(name)
            out += lines
            size += sum(len(x) for x in lines)
        if size > MAX_CHARS:
            break
    return '\n'.join(out)


# ---------------------------------------------------------------- Excel 97-2003 (.xls, BIFF8) and 5/95 (BIFF5)
class _Chunks:
    """The shared-string table runs over CONTINUE records; where a string's characters cross into the next record, that
    record starts with its own flags byte (the width of the characters may change there)."""

    def __init__(self, chunks):
        self.c, self.i, self.p = chunks, 0, 0

    def _next(self):
        self.i += 1
        self.p = 0
        if self.i >= len(self.c):
            raise EOFError

    def read(self, n):
        out = b''
        while n:
            if self.p >= len(self.c[self.i]):
                self._next()
                continue
            part = self.c[self.i][self.p:self.p + n]
            self.p += len(part)
            n -= len(part)
            out += part
        return out

    def chars(self, cch, wide):
        out = []
        while cch:
            left = len(self.c[self.i]) - self.p
            if left <= 0 or (wide and left < 2):
                self._next()
                wide = bool(self.c[self.i][0] & 1)
                self.p = 1
                continue
            k = min(cch, left // 2 if wide else left)
            raw = self.c[self.i][self.p:self.p + (k * 2 if wide else k)]
            out.append(raw.decode('utf-16-le' if wide else 'latin-1', 'replace'))
            self.p += len(raw)
            cch -= k
        return ''.join(out)

    def string(self):
        cch, flags = struct.unpack('<HB', self.read(3))
        runs = struct.unpack('<H', self.read(2))[0] if flags & 8 else 0
        ext = struct.unpack('<I', self.read(4))[0] if flags & 4 else 0
        s = self.chars(cch, bool(flags & 1))
        self.read(4 * runs + ext)
        return s


def _ustr(b, pos, lenbytes, biff8, cp):
    """A string inside a cell record: 8-bit in the workbook's code page (BIFF5) or with a flags byte (BIFF8)."""
    cch = struct.unpack_from('<H' if lenbytes == 2 else '<B', b, pos)[0]
    pos += lenbytes
    if not biff8:
        return b[pos:pos + cch].decode(cp, 'replace')
    wide = b[pos] & 1
    pos += 1
    return b[pos:pos + cch * 2].decode('utf-16-le', 'replace') if wide else b[pos:pos + cch].decode('latin-1')


def _rk(v):
    n = (struct.unpack('<i', struct.pack('<I', v))[0] >> 2) if v & 2 else struct.unpack('<d', struct.pack('<II', 0, v & 0xFFFFFFFC))[0]
    return n / 100 if v & 1 else n


def biff_text(wb):
    """The cells of a BIFF workbook stream, sheet by sheet."""
    recs, pos = [], 0
    while pos + 4 <= len(wb):
        rt, ln = struct.unpack_from('<HH', wb, pos)
        recs.append((rt, wb[pos + 4:pos + 4 + ln], pos))
        pos += 4 + ln
    biff8, cp, base1904 = True, 'cp1252', False
    sst, formats, xfs, names = [], {}, [], {}
    out, rows, depth, sheet_at, pending, total = [], None, 0, None, None, 0
    i = 0
    while i < len(recs):
        rt, b, at = recs[i]
        i += 1
        try:
            if rt == 0x0809:                                              # BOF
                ver, kind = struct.unpack_from('<HH', b, 0)
                depth += 1
                if depth == 1:
                    if kind == 0x0005:
                        biff8 = ver >= 0x0600
                    rows, sheet_at = ({} if kind == 0x0010 else None), at
            elif rt == 0x000A:                                            # EOF
                depth = max(0, depth - 1)
                if depth == 0 and rows:
                    lines = _rows_text(rows)
                    if lines:
                        name = names.get(sheet_at, '')
                        if len(names) > 1 and name and not re.match(r'(sheet|ورقة)\s*\d+$', name, re.I):
                            out.append(name)
                        out += lines
                        total += sum(len(x) for x in lines)
                rows = None if depth == 0 else rows
                if total > MAX_CHARS:
                    break
            elif rt == 0x0042:
                n = struct.unpack_from('<H', b, 0)[0]
                cp = 'utf-16-le' if n == 1200 else 'mac_roman' if n == 10000 else 'cp%d' % (1252 if n == 32769 else n)
                try:
                    b''.decode(cp)
                except LookupError:
                    cp = 'cp1252'
            elif rt == 0x0022:
                base1904 = bool(struct.unpack_from('<H', b, 0)[0])
            elif rt == 0x0085:                                            # BOUNDSHEET: where the sheet starts, and its name
                names[struct.unpack_from('<I', b, 0)[0]] = _ustr(b, 6, 1, biff8, cp)
            elif rt == 0x041E:
                formats[struct.unpack_from('<H', b, 0)[0]] = _ustr(b, 2, 2 if biff8 else 1, biff8, cp)
            elif rt == 0x00E0:
                xfs.append(struct.unpack_from('<H', b, 2)[0])
            elif rt == 0x00FC:                                            # SST and the CONTINUE records after it
                chunks = [b]
                while i < len(recs) and recs[i][0] == 0x003C:
                    chunks.append(recs[i][1])
                    i += 1
                rd = _Chunks(chunks)
                count = struct.unpack('<II', rd.read(8))[1]
                try:
                    for _ in range(count):
                        sst.append(rd.string())
                except (EOFError, struct.error, IndexError):
                    pass
            elif rows is not None and depth == 1 and len(b) >= 6:
                r, c, xf = struct.unpack_from('<HHH', b, 0)

                def put(col, value, ixf=xf):
                    if len(rows) < MAX_ROWS or r in rows:
                        fmt = xfs[ixf] if ixf < len(xfs) else 0
                        is_date = isinstance(value, float) and _date_format(fmt, formats.get(fmt))
                        rows.setdefault(r, {})[col] = _serial(value, base1904) if is_date else _num(value) if isinstance(value, (int, float)) else value

                if rt == 0x00FD:
                    k = struct.unpack_from('<I', b, 6)[0]
                    put(c, sst[k] if k < len(sst) else '')
                elif rt in (0x0204, 0x00D6):
                    put(c, _ustr(b, 6, 2, biff8, cp))
                elif rt == 0x0203:
                    put(c, struct.unpack_from('<d', b, 6)[0])
                elif rt == 0x027E:
                    put(c, float(_rk(struct.unpack_from('<I', b, 6)[0])))
                elif rt == 0x00BD:
                    for k in range((len(b) - 6) // 6):
                        ixf, rk = struct.unpack_from('<HI', b, 4 + 6 * k)
                        put(c + k, float(_rk(rk)), ixf)
                elif rt == 0x0006:
                    res = b[6:14]
                    if res[6:8] == b'\xff\xff':
                        if res[0] == 0:
                            pending = (r, c)
                        elif res[0] == 1:
                            put(c, 'TRUE' if res[2] else 'FALSE')
                    else:
                        put(c, struct.unpack('<d', res)[0])
                elif rt == 0x0207 and pending:
                    rows.setdefault(pending[0], {})[pending[1]] = _ustr(b, 0, 2, biff8, cp)
                    pending = None
                elif rt == 0x0205 and not b[7]:
                    put(c, 'TRUE' if b[6] else 'FALSE')
        except (struct.error, IndexError):
            continue
    return '\n'.join(out)


def xls_text(data):
    streams = msdoc.streams(data)
    name = 'Workbook' if 'Workbook' in streams else 'Book'
    return biff_text(msdoc.stream(data, name) or b'')


# ---------------------------------------------------------------- PowerPoint (.pptx .ppsx · .ppt)
def _dml(el, out):
    """The paragraphs of a slide in their order; a table row as «cell | cell»."""
    tag = _local(el)
    if tag == 'tbl':
        for tr in el:
            if _local(tr) == 'tr':
                cells = [' '.join(x for x in _paras(tc) if x) for tc in tr if _local(tc) == 'tc']
                if any(cells):
                    out.append(' | '.join(cells))
        return
    if tag == 'p' and 'drawingml' in el.tag:
        out += _paras(el, True)
        return
    for ch in el:
        _dml(ch, out)


def _paras(el, itself=False):
    out = []
    for p in ([el] if itself else [x for x in el.iter() if _local(x) == 'p' and 'drawingml' in x.tag]):
        s = ''.join('\n' if _local(x) == 'br' else (x.text or '') for x in p.iter() if _local(x) in ('t', 'br'))
        if s.strip():
            out.append(s.strip())
    return out


def pptx_text(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    names = set(z.namelist())
    order = []
    if 'ppt/_rels/presentation.xml.rels' in names:
        rels = {r.get('Id'): 'ppt/' + (r.get('Target') or '').lstrip('/').replace('ppt/', '', 1) for r in _xml(z.read('ppt/_rels/presentation.xml.rels'))}
        for el in _xml(z.read('ppt/presentation.xml')).iter():
            if _local(el) == 'sldId':
                rid = next((v for k, v in el.attrib.items() if k.endswith('}id')), None)
                if rels.get(rid) in names:
                    order.append(rels[rid])
    if not order:
        order = sorted((n for n in names if re.match(r'ppt/slides/slide\d+\.xml$', n)), key=lambda n: int(re.search(r'(\d+)\.xml$', n).group(1)))
    out = []
    for path in order:
        _dml(_xml(z.read(path)), out)
    return '\n'.join(out)


def ppt_text(data):
    doc = msdoc.stream(data, 'PowerPoint Document') or b''
    out = []

    def walk(pos, end, depth):
        while pos + 8 <= end:
            ver, rtype, rlen = struct.unpack_from('<HHI', doc, pos)
            pos += 8
            nxt = min(end, pos + rlen)
            if rtype == 4000:                                             # TextCharsAtom: UTF-16
                out.append(doc[pos:nxt].decode('utf-16-le', 'replace'))
            elif rtype == 4008:                                           # TextBytesAtom: one byte a character
                out.append(doc[pos:nxt].decode('latin-1'))
            elif ver & 0x000F == 0x000F and rtype not in (1016, 1008) and depth < 40:   # a container; masters and notes are left out
                walk(pos, nxt, depth + 1)
            pos = nxt

    walk(0, len(doc), 0)
    lines = [ln.strip() for s in out for ln in re.split(r'[\r\x0b\n]', s)]
    return '\n'.join(ln for ln in lines if ln and not re.match(r'^(Click to edit|\*|[‹<]#[›>])', ln))


# ---------------------------------------------------------------- OpenDocument (.odt .ods .odp)
def _odf_inline(el):
    parts = [el.text or '']
    for ch in el:
        tag = _local(ch)
        if tag == 's':
            parts.append(' ' * int(next((v for k, v in ch.attrib.items() if k.endswith('}c')), 1)))
        elif tag == 'tab':
            parts.append('\t')
        elif tag == 'line-break':
            parts.append('\n')
        elif tag not in ('note', 'annotation', 'tracked-changes'):
            parts.append(_odf_inline(ch))
        parts.append(ch.tail or '')
    return ''.join(parts)


def _odf(el, out):
    tag = _local(el)
    if tag == 'table-row':
        cells = []
        for c in el:
            if _local(c) in ('table-cell', 'covered-table-cell'):
                txt = ' '.join(_odf_inline(p).strip() for p in c.iter() if _local(p) in ('p', 'h')).strip()
                rep = int(next((v for k, v in c.attrib.items() if k.endswith('}number-columns-repeated')), 1))
                cells += [txt] * (min(rep, 50) if txt else 1)
        while cells and not cells[-1]:
            cells.pop()
        if any(cells):
            out.append(' | '.join(cells))
        return
    if tag in ('p', 'h'):
        out.append(_odf_inline(el))
        return
    if tag in ('tracked-changes', 'annotation'):
        return
    for ch in el:
        _odf(ch, out)


def odf_text(data):
    root = _xml(zipfile.ZipFile(io.BytesIO(data)).read('content.xml'))
    out = []
    for el in root:
        if _local(el) == 'body':
            _odf(el, out)
    return '\n'.join(out)


# ---------------------------------------------------------------- RTF
CHARSETS = {0: None, 1: None, 2: 'cp1252', 77: 'mac_roman', 128: 'cp932', 129: 'cp949', 134: 'cp936', 136: 'cp950', 161: 'cp1253', 162: 'cp1254', 163: 'cp1258',
            177: 'cp1255', 178: 'cp1256', 186: 'cp1257', 204: 'cp1251', 222: 'cp874', 238: 'cp1250'}
RTF_SKIP = {'fonttbl', 'colortbl', 'stylesheet', 'info', 'pict', 'object', 'objdata', 'header', 'headerl', 'headerr', 'headerf', 'footer', 'footerl', 'footerr', 'footerf',
            'footnote', 'generator', 'xmlnstbl', 'listtable', 'listoverridetable', 'rsidtbl', 'themedata', 'colorschememapping', 'datastore', 'latentstyles', 'pgdsctbl',
            'fldinst', 'template', 'operator', 'author', 'title', 'bkmkstart', 'bkmkend', 'datafield', 'panose', 'falt', 'revtbl', 'mmathPr', 'defchp', 'defpap',
            'wgrffmtfilter', 'filetbl', 'nonshppict', 'shpinst', 'nonesttables', 'userprops', 'xe', 'tc'}
RTF_CHARS = {'par': '\n', 'sect': '\n', 'page': '\n', 'line': '\n', 'row': '\n', 'cell': ' | ', 'nestcell': ' | ', 'nestrow': '\n', 'tab': '\t', 'emdash': '—', 'endash': '–',
             'lquote': '‘', 'rquote': '’', 'ldblquote': '“', 'rdblquote': '”', 'bullet': '•', 'emspace': ' ', 'enspace': ' ', 'qmspace': ' '}
RTF_TOKEN = re.compile(r"\\([a-zA-Z]{1,32})(-?\d{1,10})?[ ]?|\\'([0-9a-fA-F]{2})|\\([^a-zA-Z])|([{}])|([\r\n]+)|([^\\{}\r\n]+)")


def rtf_text(data):
    s = data.decode('latin-1')
    default, fonts, out = 'cp1252', {}, []
    stack, state = [], {'skip': False, 'cp': None, 'uc': 1, 'fonttbl': False}
    star, font, eat, raw = False, None, 0, bytearray()

    def flush():
        if raw:
            out.append(bytes(raw).decode(state['cp'] or default, 'replace'))
            raw.clear()

    pos = 0
    while pos < len(s):
        m = RTF_TOKEN.match(s, pos)
        if not m:
            pos += 1
            continue
        pos = m.end()
        word, num, hx, sym, brace, _nl, plain = m.groups()
        if brace == '{':
            flush()
            stack.append(dict(state))
            star = False
        elif brace == '}':
            flush()
            if stack:
                state = stack.pop()
        elif word:
            n = int(num) if num else None
            if word == 'bin' and n:
                pos += n
            elif word == 'fonttbl':
                state.update(skip=True, fonttbl=True)
            elif word in RTF_SKIP or star:
                state['skip'] = True
            elif word == 'ansicpg' and n:
                try:
                    b''.decode('cp%d' % n)
                    default = 'cp%d' % n
                except LookupError:
                    pass
            elif word == 'f' and n is not None:
                if state['fonttbl']:
                    font = n
                else:
                    flush()
                    state['cp'] = fonts.get(n)
            elif word == 'fcharset' and state['fonttbl'] and font is not None and n in CHARSETS:
                fonts[font] = CHARSETS[n]
            elif word == 'uc' and n is not None:
                state['uc'] = n
            elif word == 'u' and n is not None and not state['skip']:
                flush()
                out.append(chr(n + 65536 if n < 0 else n))
                eat = state['uc']
            elif word in RTF_CHARS and not state['skip']:
                flush()
                out.append(RTF_CHARS[word])
            star = False
        elif hx:
            if eat:
                eat -= 1
            elif not state['skip']:
                raw.append(int(hx, 16))
        elif sym:
            if sym == '*':
                star = True
            elif not state['skip']:
                flush()
                out.append({'~': ' ', '_': '-', '-': '', '\n': '\n', '\r': '\n'}.get(sym, sym if sym in '\\{}' else ''))
        elif plain and not state['skip']:
            if eat:
                plain, eat = plain[eat:], max(0, eat - len(plain))
            if plain:
                flush()
                out.append(plain)
    flush()
    text = ''.join(out).encode('utf-16', 'surrogatepass').decode('utf-16', 'replace')
    lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in text.split('\n')]
    return '\n'.join(re.sub(r'(?:\s*\|)+\s*$', '', ln).strip() for ln in lines)


# ---------------------------------------------------------------- HTML, XML of Office 2003, plain text
def decode(data):
    """Bytes of a text file as text: its byte-order mark, UTF-8 when it is valid, else Windows-1256 (Arabic) or 1252."""
    if data[:3] == b'\xef\xbb\xbf':
        return data[3:].decode('utf-8', 'replace')
    if data[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return data.decode('utf-16', 'replace')
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        high = [b for b in data[:20000] if b >= 0x80]
        arabic = sum(1 for b in high if 0xC1 <= b <= 0xDB or 0xDD <= b <= 0xDF or b in (0xE1, 0xE3, 0xE4, 0xE5, 0xE6, 0xEC, 0xED))
        return data.decode('cp1256' if high and arabic > len(high) / 2 else 'cp1252', 'replace')


def html_text(data):
    from html.parser import HTMLParser
    m = re.search(rb'charset\s*=\s*["\']?\s*([A-Za-z0-9_-]+)', data[:4000])
    try:
        src = data.decode(m.group(1).decode('ascii')) if m and data[:2] not in (b'\xff\xfe', b'\xfe\xff') else decode(data)
    except (LookupError, UnicodeDecodeError):
        src = decode(data)
    block = {'p', 'div', 'br', 'tr', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'ul', 'ol', 'section', 'article', 'title', 'blockquote', 'pre', 'hr', 'dt', 'dd', 'caption'}
    skip = {'script', 'style', 'noscript', 'template', 'svg', 'head'}
    out = []

    class P(HTMLParser):
        hidden = cell = 0

        def handle_starttag(self, tag, attrs):
            if tag in skip:
                self.hidden += 1
            elif tag in ('td', 'th'):
                self.cell += 1
                out.append('\x00')
            elif tag in block:
                out.append(' ' if self.cell and tag != 'tr' else '\n')          # a paragraph inside a cell stays in its row

        def handle_endtag(self, tag):
            if tag in skip:
                self.hidden = max(0, self.hidden - 1)
            elif tag in ('td', 'th'):
                self.cell = max(0, self.cell - 1)
            elif tag in block:
                out.append(' ' if self.cell and tag != 'tr' else '\n')

        def handle_data(self, d):
            if not self.hidden:
                out.append(re.sub(r'\s+', ' ', d))

    p = P(convert_charrefs=True)
    try:
        p.feed(src)
        p.close()
    except Exception:
        pass
    lines = []
    for ln in ''.join(out).split('\n'):
        cells = [c.strip() for c in ln.split('\x00')]
        ln = ' | '.join(cells[1:] if not cells[0] else cells) if len(cells) > 1 else cells[0]
        ln = re.sub(r'(?:\s*\|)+\s*$', '', ln).strip()
        if ln.strip(' |'):
            lines.append(ln)
    return '\n'.join(lines)


def _office_xml(src):
    """Word 2003 XML and Excel 2003 XML (a single .xml file each); None when the XML is something else."""
    if 'schemas-microsoft-com:office:spreadsheet' not in src[:3000] and 'office/word/2003/wordml' not in src[:3000]:
        return None
    try:
        root = _xml(src.encode('utf-8'))
    except Exception:
        return None
    out = []
    if _local(root) == 'Workbook':
        for row in root.iter():
            if _local(row) == 'Row':
                cells, col = {}, 0
                for c in row:
                    if _local(c) != 'Cell':
                        continue
                    idx = next((v for k, v in c.attrib.items() if k.endswith('}Index')), None)
                    col = int(idx) - 1 if idx else col
                    for d in c:
                        if _local(d) == 'Data':
                            v = ''.join(d.itertext())
                            kind = next((x for k, x in d.attrib.items() if k.endswith('}Type')), '')
                            cells[col] = v[:10] if kind == 'DateTime' and v[10:] in ('', 'T00:00:00.000', 'T00:00:00') else _num(v) if kind == 'Number' else v
                    col += 1
                out += _rows_text({0: cells})
        return '\n'.join(out)
    for body in root.iter():
        if _local(body) == 'body':
            def walk(el):
                tag = _local(el)
                if tag == 'tr':
                    cells = [' '.join(''.join(t.text or '' for t in p.iter() if _local(t) == 't') for p in tc.iter() if _local(p) == 'p').strip() for tc in el if _local(tc) == 'tc']
                    if any(cells):
                        out.append(' | '.join(cells))
                elif tag == 'p':
                    out.append(''.join(t.text or '' for t in el.iter() if _local(t) == 't'))
                else:
                    for ch in el:
                        walk(ch)
            walk(body)
    return '\n'.join(out)


def plain_text(data, name=''):
    src = decode(data[:4 * MAX_CHARS])
    low = (name or '').lower()
    if src.lstrip()[:5] == '<?xml' or low.endswith('.xml'):
        got = _office_xml(src)
        if got is not None:
            return got
    if low.endswith(('.csv', '.tsv')) or (low.rsplit('.', 1)[-1] not in ('txt', 'md', 'log', 'xml', 'json') and re.match(r'[^\n]*[,;\t][^\n]*\n[^\n]*[,;\t]', src)):
        try:
            sample = src[:4000]
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t') if not low.endswith('.tsv') else csv.excel_tab
            rows = list(csv.reader(io.StringIO(src), dialect))
            if rows and max(len(r) for r in rows) > 1:
                return '\n'.join(' | '.join(c.strip() for c in r).strip(' |') for r in rows[:MAX_ROWS] if any(c.strip() for c in r))
        except Exception:
            pass
    return src


READERS = {'xlsx': xlsx_text, 'xls': xls_text, 'pptx': pptx_text, 'ppt': ppt_text, 'odt': odf_text, 'ods': odf_text, 'odp': odf_text, 'rtf': rtf_text, 'html': html_text}


def text(kind, data, name=''):
    """The text of an office file of that kind ('' when it cannot be read: a damaged or password-protected file)."""
    try:
        if kind == 'doc':
            out = msdoc.doc_text(data)
        elif kind == 'docx':
            from .extract import docx_text
            out = docx_text(data)
        elif kind == 'text':
            out = plain_text(data, name)
        elif kind in READERS:
            out = READERS[kind](data)
        else:
            return ''
    except Exception:
        return ''
    out = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]', '', out or '')
    lines = [re.sub(r'[ \t\xa0]+', ' ', ln).strip() for ln in out.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()[:MAX_CHARS]
