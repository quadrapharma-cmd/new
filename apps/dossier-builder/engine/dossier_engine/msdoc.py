"""Word 97-2003 files (.doc) read from the inside with the standard library only, so every edition reads them (the browser
one too): the OLE2 container ([MS-CFB]), the FIB of the «WordDocument» stream and the piece table of the table stream
([MS-DOC] 2.4.1 «Retrieving Text»). The text comes out the way `extract.docx_text` gives a .docx: paragraphs in their order,
a table row as «cell | cell», a field as what it shows (never its code). Word 6/95 files and password-protected files are
not read: `doc_text` gives '' and the file is treated as unread (the person places it)."""
import re
import struct

MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
_LAST = 0xFFFFFFFA                      # sector numbers from here up are markers (free, end of chain, FAT, DIFAT)


class _Cfb:
    """The top-level streams of a compound file."""

    def __init__(self, data):
        if data[:8] != MAGIC or len(data) < 1024:
            raise ValueError('not a compound file')
        self.d = data
        self.ss = 1 << struct.unpack_from('<H', data, 0x1E)[0]
        self.mss = 1 << struct.unpack_from('<H', data, 0x20)[0]
        if self.ss not in (512, 4096) or self.mss != 64:
            raise ValueError('unusual sector size')
        _n_fat, dir_start, _txn, self.cutoff, minifat_start, _n_minifat, difat_start, _n_difat = struct.unpack_from('<8I', data, 0x2C)
        self.limit = len(data) // self.ss + 2
        difat, sec, seen = list(struct.unpack_from('<109I', data, 0x4C)), difat_start, set()
        while sec < _LAST and sec not in seen and len(seen) < self.limit:
            seen.add(sec)
            vals = self._ints(self._sector(sec))
            if not vals:
                break
            difat += vals[:-1]
            sec = vals[-1]
        self.fat = []
        for s in difat:
            if s < _LAST:
                self.fat += self._ints(self._sector(s))
        self.dir = self._chain(dir_start)
        root = self._entry(0)
        self.mini = self._chain(root['start'])[:root['size']] if root and root['start'] < _LAST else b''
        self.minifat = self._ints(self._chain(minifat_start)) if minifat_start < _LAST else []
        self.streams = {}
        todo, seen = [root['child']] if root else [], set()
        while todo:                                         # the root storage's own children (a red-black tree of siblings)
            i = todo.pop()
            if i >= _LAST or i in seen or len(seen) > 4096:
                continue
            seen.add(i)
            e = self._entry(i)
            if not e:
                continue
            todo += [e['left'], e['right']]
            if e['type'] == 2:
                self.streams.setdefault(e['name'], e)

    def _sector(self, n):
        o = (n + 1) * self.ss
        return self.d[o:o + self.ss]

    @staticmethod
    def _ints(b):
        return list(struct.unpack_from(f'<{len(b) // 4}I', b)) if len(b) >= 4 else []

    def _chain(self, start):
        out, sec, n = [], start, 0
        while sec < _LAST and sec < len(self.fat) and n < self.limit:
            out.append(self._sector(sec))
            sec, n = self.fat[sec], n + 1
        return b''.join(out)

    def _entry(self, i):
        b = self.dir[i * 128:(i + 1) * 128]
        if len(b) < 128:
            return None
        nlen = struct.unpack_from('<H', b, 0x40)[0]
        left, right, child = struct.unpack_from('<3I', b, 0x44)
        start, size = struct.unpack_from('<IQ', b, 0x74)
        return {'name': b[:max(0, min(nlen, 64) - 2)].decode('utf-16-le', 'replace'), 'type': b[0x42], 'left': left, 'right': right,
                'child': child, 'start': start, 'size': size & 0xFFFFFFFF if self.ss == 512 else size}

    def stream(self, name):
        e = self.streams.get(name)
        if not e:
            return None
        if e['size'] < self.cutoff:                         # a small stream lives in the mini stream, in 64-byte sectors
            out, sec, n = [], e['start'], 0
            while sec < _LAST and sec < len(self.minifat) and n < len(self.minifat) + 1:
                out.append(self.mini[sec * self.mss:(sec + 1) * self.mss])
                sec, n = self.minifat[sec], n + 1
            return b''.join(out)[:e['size']]
        return self._chain(e['start'])[:e['size']]


def is_doc(data):
    """A Word 97-2003 document by its bytes (an .xls or a .msg is a compound file too, with other streams)."""
    try:
        return data[:8] == MAGIC and 'WordDocument' in _Cfb(data).streams
    except Exception:
        return False


def _pieces(table, fc, lcb):
    """The piece table: [(first cp, end cp, offset in WordDocument, 8-bit?)] — where each run of the text is stored."""
    p, end = fc, min(fc + lcb, len(table))
    while p + 5 <= end:
        if table[p] == 1:                                   # property changes of a fast save: skipped
            p += 3 + struct.unpack_from('<H', table, p + 1)[0]
        elif table[p] == 2:
            n = (struct.unpack_from('<I', table, p + 1)[0] - 4) // 12
            q = p + 5
            if n <= 0 or q + 4 * (n + 1) + 8 * n > len(table):
                return []
            cps = struct.unpack_from(f'<{n + 1}I', table, q)
            out = []
            for i in range(n):
                v = struct.unpack_from('<I', table, q + 4 * (n + 1) + 8 * i + 2)[0]
                out.append((cps[i], cps[i + 1], v & 0x3FFFFFFF, bool(v & 0x40000000)))
            return out
        else:
            break
    return []


def _range(wd, pieces, a, b):
    out = []
    for c0, c1, fc, small in pieces:
        s, e = max(a, c0), min(b, c1)
        if s >= e:
            continue
        if small:                                           # one byte a character (Windows-1252), stored at fc / 2
            o = fc // 2 + (s - c0)
            out.append(wd[o:o + (e - s)].decode('cp1252', 'replace'))
        else:                                               # two bytes a character (UTF-16)
            o = fc + 2 * (s - c0)
            out.append(wd[o:o + 2 * (e - s)].decode('utf-16-le', 'replace'))
    return ''.join(out)


_DROP = re.compile('[\x00-\x08\x0e-\x1d\x1f\x7f�﻿]')


def _clean(raw):
    """Word's marks → plain text: a field keeps what it shows, a cell mark becomes « | », a row or paragraph end a new line."""
    out, state = [], []                                     # state of each open field: False = in its code, True = in its result
    for ch in raw:
        if ch == '\x13':
            state.append(False)
        elif ch == '\x14':
            if state:
                state[-1] = True
        elif ch == '\x15':
            if state:
                state.pop()
        elif all(state):
            out.append(ch)
    text = ''.join(out)
    text = text.replace('\x07\x07', '\n').replace('\x07', ' | ')        # a row ends with its last cell's mark and the row's own mark
    text = text.replace('\r', '\n').replace('\x0b', '\n').replace('\x0c', '\n').replace('\x1e', '-').replace('\xa0', ' ')
    text = _DROP.sub('', text)
    lines = [re.sub(r'[ \t]+', ' ', ln).strip() for ln in text.split('\n')]
    lines = [re.sub(r'^(?:\| )+|(?: \|)+$', '', ln).strip() if '|' in ln else ln for ln in lines]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip()


def doc_text(data):
    """The text of a .doc: the body, then what is written in its text boxes. '' when the file cannot be read."""
    try:
        cfb = _Cfb(data)
        wd = cfb.stream('WordDocument')
        if not wd or len(wd) < 0x60:
            return ''
        ident, flags = struct.unpack_from('<H', wd, 0)[0], struct.unpack_from('<H', wd, 0x0A)[0]
        if ident != 0xA5EC or flags & 0x0100:               # Word 6/95, or encrypted
            return ''
        table = cfb.stream('1Table' if flags & 0x0200 else '0Table') or cfb.stream('0Table') or cfb.stream('1Table')
        if not table:
            return ''
        p = 0x22 + 2 * struct.unpack_from('<H', wd, 0x20)[0]
        lw = p + 2
        p = lw + 4 * struct.unpack_from('<H', wd, p)[0]
        fc0 = p + 2
        ccp = struct.unpack_from('<8i', wd, lw + 12)        # text, footnotes, headers, macros, comments, endnotes, text boxes, header boxes
        fc_clx, lcb_clx = struct.unpack_from('<II', wd, fc0 + 33 * 8)
        pieces = _pieces(table, fc_clx, lcb_clx)
        if not pieces:
            return ''
        body = _clean(_range(wd, pieces, 0, max(0, ccp[0])))
        box_at = sum(max(0, c) for c in ccp[:6])
        boxes = _clean(_range(wd, pieces, box_at, box_at + max(0, ccp[6]))) if ccp[6] > 0 else ''
        return (body + ('\n' + boxes if boxes else '')).strip()
    except Exception:
        return ''
