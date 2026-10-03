"""Shared helpers for the seed / oracle / batch tools (code only, no company data).

Everything the tools write goes to the PRIVATE directory (never inside the repository):
    <private>/seed/<collection path>/<doc id>.json     one file per db document
    <private>/review/*.csv                            human review files
    <private>/batches/batch_NNN.json                  ArtifactData batch payloads
    <private>/oracle.json                             independent acceptance numbers
Environment:
    STRIFA_REAL_XLSX     path of the workbook (default: the single xlsx under /root/.claude/uploads)
    STRIFA_PRIVATE_DIR   private directory (default /home/user/.strifa-private)
"""
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

DEFAULT_PRIVATE = '/home/user/.strifa-private'
DOC_BYTES_LIMIT = 200 * 1024  # task limit per document (platform limit is 256 KiB)

AR_DIGITS = '٠١٢٣٤٥٦٧٨٩'
_AR2WEST = {ord(a): str(i) for i, a in enumerate(AR_DIGITS)}
_AR2WEST.update({ord(a): str(i) for i, a in enumerate('۰۱۲۳۴۵۶۷۸۹')})


class SeedError(Exception):
    """Raised for input problems that must stop the run (the message never carries amounts or names)."""


# --------------------------------------------------------------------------- paths
def private_dir():
    return os.environ.get('STRIFA_PRIVATE_DIR') or DEFAULT_PRIVATE


def xlsx_path(explicit=None):
    if explicit:
        return explicit
    env = os.environ.get('STRIFA_REAL_XLSX')
    if env:
        return env
    found = sorted(glob.glob('/root/.claude/uploads/*/*.xlsx'))
    if len(found) == 1:
        return found[0]
    if not found:
        raise SeedError('workbook not found: set STRIFA_REAL_XLSX or pass --xlsx')
    raise SeedError('several workbooks found: set STRIFA_REAL_XLSX or pass --xlsx')


def assert_outside_repo(path):
    """Refuse to write real-data output inside the git repository that holds this tool."""
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    p = os.path.abspath(path)
    if p == repo or p.startswith(repo + os.sep):
        # tests may point STRIFA_PRIVATE_DIR at a temp dir; anything under the repo is refused
        raise SeedError('refusing to write output inside the repository: ' + p)


# --------------------------------------------------------------------------- hashing / json
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def dumps(obj):
    """Deterministic compact JSON (sorted keys, UTF-8 Arabic kept as is)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def write_json(path, obj, check_size=True):
    text = dumps(obj) + '\n'
    data = text.encode('utf-8')
    if check_size and len(data) > DOC_BYTES_LIMIT:
        raise SeedError(f'document too large ({len(data)} bytes > {DOC_BYTES_LIMIT}): {os.path.basename(path)}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'wb') as fh:
        fh.write(data)
    os.replace(tmp, path)
    return len(data)


# --------------------------------------------------------------------------- numbers (integer cents)
def to_cents(x):
    """Workbook number -> integer cents, ROUND_HALF_UP on the shortest decimal representation."""
    if x is None or x == '':
        return 0
    if isinstance(x, bool):
        raise SeedError('boolean where a number was expected')
    if isinstance(x, int):
        return x * 100
    d = Decimal(str(x)) if not isinstance(x, Decimal) else x
    return int((d * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def exact_cents(x):
    """Like to_cents but returns None when the number has more than two decimals (never silently rounds)."""
    if x is None or x == '':
        return 0
    d = Decimal(str(x))
    c = d * 100
    if c != c.to_integral_value():
        return None
    return int(c)


def from_cents(c):
    """Integer cents -> JSON number (int when whole, else float with 2 decimals)."""
    if c % 100 == 0:
        return c // 100
    return float(Decimal(c) / Decimal(100))


def fmt_cents(c):
    sign = '-' if c < 0 else ''
    c = abs(c)
    return f'{sign}{c // 100:,}.{c % 100:02d}'


def num(x):
    """Cell value -> float/int or None (accepts numeric strings with separators and Arabic digits)."""
    if x is None or x == '':
        return None
    if isinstance(x, (int, float, Decimal)) and not isinstance(x, bool):
        return x
    s = to_western(str(x)).replace(',', '').replace('٬', '').replace('٫', '.').replace(' ', '')
    s = s.replace('(', '-').replace(')', '')
    try:
        return int(s) if re.fullmatch(r'-?\d+', s) else float(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------- text
def to_western(s):
    return str(s).translate(_AR2WEST)


_DIAC = re.compile('[ً-ٰٟـ]')


def clean(s):
    """Trim + collapse whitespace; None -> ''."""
    if s is None:
        return ''
    return re.sub(r'\s+', ' ', str(s)).strip()


def cell_text(v):
    if v is None:
        return ''
    if isinstance(v, (datetime, date)):
        return iso(v)
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return clean(v)


def iso(d):
    if isinstance(d, datetime):
        d = d.date()
    return d.isoformat()


def parse_dmy(text):
    """First dd/mm/yyyy (or d/m/yyyy) in text -> ISO string, else None."""
    m = re.search(r'(?<!\d)(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})(?!\d)', to_western(text or ''))
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


def arabic_index(n):
    return ''.join(AR_DIGITS[int(c)] for c in str(n))


def norm_text(s):
    """Light normalisation used for matching (NFKC, diacritics, hamza/yaa/taa-marbuta, spaces)."""
    s = unicodedata.normalize('NFKC', str(s or ''))
    s = _DIAC.sub('', s)
    for a, b in (('أ', 'ا'), ('إ', 'ا'), ('آ', 'ا'), ('ى', 'ي'), ('ة', 'ه'), ('ؤ', 'و'), ('ئ', 'ي')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip().lower()


def eprint(*a):
    print(*a, file=sys.stderr)
