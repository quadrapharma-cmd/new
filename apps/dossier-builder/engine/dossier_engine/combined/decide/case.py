"""What Claude may read of the dossier, through the program: a page's text (its own, or the OCR's), a page drawn as a picture,
a search over every kept page, the documents as the program placed them. Pages of a block received twice were never read."""
import base64
import io
import re
import subprocess
import tempfile
from pathlib import Path

from ..common import parse_ranges, ranges, tool
from .brain import ToolError

MAX_PAGES = 40          # pages read in one call
PAGE_CHARS = 3500       # characters of one page given back (the rest is cut, and said so)


def clean(t):
    t = re.sub(r'[ \t]+', ' ', t or '')
    return re.sub(r'\n{3,}', '\n\n', t).strip()


class Case:
    def __init__(self, w):
        self.w = w
        self.pages = w.load('read/pages.json', []) or []
        self.files = w.load('read/files.json', []) or []
        self.ocr = w.pages_text('read/ocr.txt')
        self.own = w.pages_text('read/text.txt')
        self.kept = set()
        for a, b in (w.load('repeats.json', {}) or {}).get('kept', []):
            self.kept |= set(range(a, b + 1))
        self.n = len(self.pages)

    # -- the pages
    def text(self, p):
        t = self.ocr[p - 1] if p - 1 < len(self.ocr) else ''
        if not (t or '').strip() and p - 1 < len(self.own):
            t = self.own[p - 1]
        return t or ''

    def check_pages(self, spec, most=MAX_PAGES):
        try:
            pages = parse_ranges(spec)
        except (ValueError, TypeError):
            raise ToolError(f'«{spec}» is not a page list; write it like «12-15, 20».')
        if not pages:
            raise ToolError('No page given.')
        bad = [p for p in pages if not 1 <= p <= self.n]
        if bad:
            raise ToolError(f'Pages {ranges(bad)} do not exist: the dossier has pages 1–{self.n}.')
        if most and len(pages) > most:
            raise ToolError(f'{len(pages)} pages asked; read at most {most} at a time.')
        return pages

    def read_pages(self, spec, chars=PAGE_CHARS):
        out = []
        for p in self.check_pages(spec):
            if p not in self.kept:
                out.append(f'— page {p}: in a block received twice (left out; its text was not read)')
                continue
            t = clean(self.text(p))
            if len(t) > chars:
                t = t[:chars] + f' […{len(t) - chars} more characters]'
            out.append(f'— page {p} —\n{t or "(no text on this page: look at its picture with view_page)"}')
        return '\n'.join(out)

    def view_page(self, p, dpi=100, longest=1600):
        self.check_pages(str(p), most=1)
        info = self.pages[p - 1]
        f = self.files[info['file']]
        src = f.get('pdf') or f['path']
        with tempfile.TemporaryDirectory() as tmp:
            stem = Path(tmp) / 'p'
            subprocess.run([tool('pdftoppm'), '-r', str(dpi), '-png', '-f', str(info['index']), '-l', str(info['index']),
                            '-singlefile', str(src), str(stem)], check=True, capture_output=True)
            png = Path(str(stem) + '.png').read_bytes()
        from PIL import Image
        im = Image.open(io.BytesIO(png))
        if max(im.size) > longest:
            im.thumbnail((longest, longest))
            buf = io.BytesIO()
            im.save(buf, 'PNG', optimize=True)
            png = buf.getvalue()
        return [{'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                             'data': base64.standard_b64encode(png).decode('ascii')}},
                {'type': 'text', 'text': f'page {p} (of {self.n})'}]

    def search(self, text, regex=False, most=40):
        try:
            pat = re.compile(text if regex else re.escape(text).replace(r'\ ', r'\s+'), re.I)
        except re.error as e:
            raise ToolError(f'Not a valid regular expression: {e}')
        hits = []
        for p in sorted(self.kept):
            t = self.text(p)
            m = pat.search(t)
            if m:
                a, b = max(0, m.start() - 90), min(len(t), m.end() + 90)
                hits.append(f'p {p}: …{clean(t[a:b])}…'.replace('\n', ' '))
                if len(hits) >= most:
                    hits.append(f'(stopped at {most} pages: search for something narrower)')
                    break
        return '\n'.join(hits) or 'Not found on any kept page.'

    # -- what the program made
    def documents(self, plan=None, first_line=True):
        plan = plan or self.w.load('plan.json', {}) or {}
        rows = []
        for i, d in enumerate(plan.get('docs', []), 1):
            row = f"{i}. p {ranges(d['pages'])} | {d.get('ctd', '')} | {d.get('title', '')} | {d['path']} | by {d.get('by', 'program')}"
            if d.get('note'):
                row += f" | note: {d['note']}"
            if first_line:
                lines = [l.strip() for l in clean(self.text(d['pages'][0])).split('\n') if len(l.strip()) > 3][:3]
                row += f" | first lines: {' / '.join(lines)[:160]}"
            rows.append(row)
        return '\n'.join(rows)

    def removed(self, plan=None):
        plan = plan or self.w.load('plan.json', {}) or {}
        runs, cur = [], None
        for r in plan.get('removed', []):
            if cur and r['page'] == cur[1] + 1 and r['why'] == cur[2]:
                cur[1] = r['page']
            else:
                cur = [r['page'], r['page'], r['why']]
                runs.append(cur)
        return '\n'.join(f'p {a}{"–" + str(b) if b != a else ""}: {why}' for a, b, why in runs) or '(none)'

    def outline(self, depth=2, most=400):
        rows = [f"{'  ' * o['level']}{o['title']} (p {o['page']})" for o in (self.w.load('read/outline.json', []) or [])
                if o['level'] < depth]
        if len(rows) > most:
            rows = rows[:most] + [f'… and {len(rows) - most} more bookmarks']
        return '\n'.join(rows) or '(the PDF has no bookmarks)'

    def received(self):
        out = []
        for f in self.files:
            line = f"{f['name']} — {f.get('kind')}"
            if f.get('pages'):
                line += f", {f['pages']} pages (pages {f.get('from')}–{f.get('to')} of the dossier)"
            if f.get('aside'):
                line += ', kept aside (not part of the page numbering)'
            out.append(line)
        rep = self.w.load('repeats.json', {}) or {}
        for d in rep.get('dropped', []):
            out.append(f"pages {d['from']}–{d['to']}: a second copy of pages {d['same_as'][0]}–{d['same_as'][1]} (left out)")
        return '\n'.join(out)


READ_TOOLS = [
    {'name': 'read_pages', 'eager_input_streaming': True, 'description': 'The text of pages of the dossier (its own text, or the OCR of a scanned page), at most '
     f'{MAX_PAGES} pages a call and {PAGE_CHARS} characters a page. Read the first page or two of a document to know what it is; '
     'read more only when the decision needs it.',
     'input_schema': {'type': 'object', 'properties': {'pages': {'type': 'string', 'description': 'e.g. "12-15, 20"'}},
                      'required': ['pages']}},
    {'name': 'view_page', 'eager_input_streaming': True, 'description': 'One page drawn as a picture: for a page with no or unclear text (a scan, a form, '
     'a mock-up, a table), or to check a heading or a signature.',
     'input_schema': {'type': 'object', 'properties': {'page': {'type': 'integer'}}, 'required': ['page']}},
    {'name': 'search_text', 'eager_input_streaming': True, 'description': 'The pages (kept pages only) whose text has these words, with a short extract each. '
     'Spaces match any whitespace; case is ignored. regex=true for a regular expression.',
     'input_schema': {'type': 'object', 'properties': {'text': {'type': 'string'}, 'regex': {'type': 'boolean'}},
                      'required': ['text']}},
]


def read_handlers(case):
    return {'read_pages': lambda a: case.read_pages(a['pages']),
            'view_page': lambda a: case.view_page(int(a['page'])),
            'search_text': lambda a: case.search(a['text'], bool(a.get('regex')))}
