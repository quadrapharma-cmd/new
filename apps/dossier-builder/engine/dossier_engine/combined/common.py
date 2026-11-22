"""What the stages share: the work folder, JSON files, page ranges, the tools on the computer."""
import atexit
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1]
APP = ENGINE.parents[1]                      # apps/dossier-builder
REPO = APP.parents[1]
PROFILE_EG = REPO / 'docs' / 'ctd' / 'ectd' / 'EG-PROVISIONAL-PROFILE-v0'
APP4 = APP / 'rulepacks' / 'ich.ectd.v322' / 'app4.csv'
FONTS = APP / 'vendor' / 'fonts'
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


# The fonts the printed pages use, given to Chromium from the program's own files: Linux has them installed, a Mac has none of
# them, and both must draw the same pages.
WEB_FONTS = (('Noto Naskh Arabic', 'NotoNaskhArabic-Regular.ttf', 400, 'normal'), ('Noto Naskh Arabic', 'NotoNaskhArabic-Bold.ttf', 700, 'normal'),
             ('Liberation Sans', 'LiberationSans-Regular.ttf', 400, 'normal'), ('Liberation Sans', 'LiberationSans-Bold.ttf', 700, 'normal'),
             ('Liberation Sans', 'LiberationSans-Italic.ttf', 400, 'italic'), ('Liberation Sans', 'LiberationSans-BoldItalic.ttf', 700, 'italic'))
_faces = {}


def font_faces(families=None):
    """@font-face rules for the printed pages' fonts, each font file as a data: URL (a page opened from a file may not load
    fonts from other files)."""
    key = tuple(families or ())
    if key not in _faces:
        out = []
        for fam, file, weight, style in WEB_FONTS:
            if families and fam not in families:
                continue
            data = base64.standard_b64encode((FONTS / file).read_bytes()).decode('ascii')
            out.append(f"@font-face {{ font-family: '{fam}'; src: url(data:font/ttf;base64,{data}) format('truetype'); "
                       f'font-weight: {weight}; font-style: {style}; }}')
        _faces[key] = '\n'.join(out)
    return _faces[key]


# LibreOffice with a profile of the program's own: never the person's own LibreOffice (an open LibreOffice would take the
# conversion over), and a font table that draws the fonts Word files name with the fonts of the same measures, as fontconfig
# does on Linux, so a Mac (which has Times New Roman and Arial themselves) draws the same pages.
LO_FONTS = (('Times New Roman', 'Liberation Serif'), ('Arial', 'Liberation Sans'), ('Courier New', 'Liberation Mono'),
            ('Calibri', 'Carlito'), ('Cambria', 'Caladea'))
_lo = {}


def lo_profile():
    if 'dir' not in _lo:
        d = Path(tempfile.mkdtemp(prefix='ebox-lo-'))
        atexit.register(shutil.rmtree, d, True)
        items = ['<item oor:path="/org.openoffice.Office.Common/Font/Substitution"><prop oor:name="Replacement" oor:op="fuse">'
                 '<value>true</value></prop></item>']
        for i, (a, b) in enumerate(LO_FONTS):
            items.append('<item oor:path="/org.openoffice.Office.Common/Font/Substitution/FontPairs">'
                         f'<node oor:name="_{i}" oor:op="replace"><prop oor:name="Always" oor:op="fuse"><value>true</value></prop>'
                         '<prop oor:name="OnScreenOnly" oor:op="fuse"><value>false</value></prop>'
                         f'<prop oor:name="ReplaceFont" oor:op="fuse"><value>{a}</value></prop>'
                         f'<prop oor:name="SubstituteFont" oor:op="fuse"><value>{b}</value></prop></node></item>')
        (d / 'user').mkdir(parents=True)
        (d / 'user' / 'registrymodifications.xcu').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
            'xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
            + '\n'.join(items) + '\n</oor:items>\n', encoding='utf-8')
        _lo['dir'] = d
    return _lo['dir']


def soffice_pdf(src, outdir, timeout=600):
    """A Word or RTF file made PDF by LibreOffice, in outdir under the same stem."""
    subprocess.run([tool('soffice'), f'-env:UserInstallation={lo_profile().as_uri()}', '--headless', '--norestore',
                    '--convert-to', 'pdf', '--outdir', str(outdir), str(src)], check=True, capture_output=True, timeout=timeout)
    return Path(outdir) / (Path(src).stem + '.pdf')


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


NOUNS = {   # one, two, three to ten, eleven to ninety-nine (and the hundreds take «one» without «واحد»)
    'مستند': ('مستند', 'مستندان', 'مستندات', 'مستندًا'), 'صفحة': ('صفحة', 'صفحتان', 'صفحات', 'صفحةً'),
    'ملف': ('ملف', 'ملفان', 'ملفات', 'ملفًّا'), 'ملاحظة': ('ملاحظة', 'ملاحظتان', 'ملاحظات', 'ملاحظةً'),
    'قرار': ('قرار', 'قراران', 'قرارات', 'قرارًا'), 'ورقة': ('ورقة', 'ورقتان', 'أوراق', 'ورقةً'),
    'قاعدة': ('قاعدة', 'قاعدتان', 'قواعد', 'قاعدةً'), 'مجموعة': ('مجموعة', 'مجموعتان', 'مجموعات', 'مجموعةً'),
    'كتلة': ('كتلة', 'كتلتان', 'كتل', 'كتلةً'), 'جزء': ('جزء', 'جزآن', 'أجزاء', 'جزءًا'),
}


def count(n, noun):
    """A number with its noun in formal Arabic: «مستند واحد», «مستندان», «5 مستندات», «181 مستندًا», «200 مستند»."""
    one, two, few, many = NOUNS[noun]
    n = int(n)
    if n == 1:
        return f'{one} واحد' if not one.endswith('ة') else f'{one} واحدة'
    if n == 2:
        return two
    r = n % 100
    shown = f'{n:,}'
    if 3 <= r <= 10:
        return f'{shown} {few}'
    if 11 <= r <= 99:
        return f'{shown} {many}'
    if n == 0:
        return f'لا {one}'
    return f'{shown} {one}'
