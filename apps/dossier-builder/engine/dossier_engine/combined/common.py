"""What the stages share: the work folder, JSON files, page ranges, the tools on the computer."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
APP = ENGINE.parents[1]                      # apps/dossier-builder
REPO = APP.parents[1]
PROFILE_EG = REPO / 'docs' / 'ctd' / 'ectd' / 'EG-PROVISIONAL-PROFILE-v0'
APP4 = APP / 'rulepacks' / 'ich.ectd.v322' / 'app4.csv'
NO_TEXT = 30                                  # a page with fewer characters than this has no text of its own


class Work:
    """The work folder of one dossier. Nothing in it belongs in the repository: it holds the company's pages."""

    def __init__(self, root):
        self.root = Path(root).resolve()
        self.read = self.root / 'read'
        self.parts = self.root / 'parts'
        self.ctd = self.root / 'ctd'
        self.fixed = self.root / 'fixed'
        self.pi = self.root / 'pi'
        self.ectd = self.root / 'ectd'
        self.report = self.root / 'report'
        self.tmp = self.root / 'tmp'
        for d in (self.root, self.read, self.parts, self.tmp):
            d.mkdir(parents=True, exist_ok=True)

    def path(self, name):
        return self.root / name

    def load(self, name, default=None):
        p = self.root / name
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding='utf-8'))

    def save(self, name, obj):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + '.tmp')
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, default=str), encoding='utf-8')
        os.replace(tmp, p)
        return p

    def decisions(self):
        """The dossier's decisions file (dossier.json): what a person (or Claude) decided where the rules cannot. Optional."""
        return self.load('dossier.json', {}) or {}

    def pages_text(self, which='read/text.txt'):
        p = self.root / which
        if not p.exists():
            return []
        return p.read_text(encoding='utf-8', errors='replace').split('\f')


def say(msg):
    print(time.strftime('%H:%M:%S'), msg, flush=True)


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def md5_file(path, chunk=1 << 20):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(chunk), b''):
            h.update(b)
    return h.hexdigest()


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(s))]


def rng(a, b):
    return list(range(a, b + 1))


def ranges(pages):
    """[1, 2, 3, 7, 9, 10] -> '1–3, 7, 9–10'"""
    out, pages = [], sorted(set(pages))
    i = 0
    while i < len(pages):
        j = i
        while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
            j += 1
        out.append(str(pages[i]) if i == j else f'{pages[i]}–{pages[j]}')
        i = j + 1
    return ', '.join(out)


def parse_ranges(text):
    """'1-3, 7' or '1–3,7' or [1, [3, 5]] -> [1, 2, 3, 7]"""
    if isinstance(text, int):
        return [text]
    if isinstance(text, list):
        out = []
        for x in text:
            out += rng(x[0], x[1]) if isinstance(x, list) else parse_ranges(x)
        return out
    out = []
    for part in re.split(r'\s*,\s*', str(text).strip()):
        if not part:
            continue
        m = re.fullmatch(r'(\d+)\s*[-–]\s*(\d+)', part)
        out += rng(int(m.group(1)), int(m.group(2))) if m else [int(part)]
    return out


def tool(name):
    """The path of a program the stages need, or a clear stop."""
    p = shutil.which(name)
    if not p:
        raise SystemExit(f'البرنامج «{name}» غير موجود على هذا الجهاز، وهذه المرحلة تحتاج إليه.')
    return p


def run(cmd, **kw):
    kw.setdefault('check', True)
    return subprocess.run([str(c) for c in cmd], **kw)


def pdftext(pdf, first=None, last=None):
    """The text of each page of a PDF, as poppler's pdftotext gives it (no layout), one string per page."""
    cmd = [tool('pdftotext'), '-enc', 'UTF-8']
    if first:
        cmd += ['-f', str(first)]
    if last:
        cmd += ['-l', str(last)]
    out = subprocess.run(cmd + [str(pdf), '-'], capture_output=True, check=True).stdout.decode('utf-8', 'replace')
    pages = out.split('\f')
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def python():
    return sys.executable
