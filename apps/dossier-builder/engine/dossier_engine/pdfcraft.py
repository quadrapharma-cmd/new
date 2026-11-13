"""PdfCraft — the program's PDF engine (updates list, item 49; the owner's decision of 13/11/2026: the whole of PdfCraft, its features
placed where each stage needs them, the program's PDF logic rebuilt on it).

The whole PdfCraft program (github.com/storytold/pdfcraft, MIT OR Apache-2.0, pinned commit in tools/pdfcraft/PIN) is built as
`pdfcraft-cli` without its MCP server (tools/pdfcraft/build.sh) and run as a separate process for each job: a JSON script of its tools,
confined to a private working folder (`--root`), with a time limit. A tool that fails ends the job, and nothing it was writing is kept
(every change is written to a new file; the stored original is never touched).

Where each stage uses it (docs/ctd/PDFCRAFT-INTEGRATION.md):
  upload       tolerant opening and repair, text in reading order (Arabic too), hidden information, faux redactions
  checks       document information (fonts, security, bookmarks, links, attachments, open view), signatures
  preparation  security, JavaScript and hidden content removed, bookmarks from the structure or the type styles, open view, link
               zoom, properties, smaller files — each result a new version, compared page for page with the original
  pages        split, extract, combine
  links        list and retarget
  review       word comparison with places on the page, a marked copy
  publishing   watermark, redaction
  viewer       page images, text search with places

When the program is not there — the browser edition, or a machine it was not built on — `available()` is False and each stage keeps
its earlier reading (pypdf), so the program still works and says which engine read the file."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2]            # apps/dossier-builder
PIN_FILE = APP / 'tools' / 'pdfcraft' / 'PIN'
TIMEOUT = 180                                        # seconds for one job
EXE = 'pdfcraft-cli.exe' if os.name == 'nt' else 'pdfcraft-cli'
_found = {}


class PdfCraftError(RuntimeError):
    """A job that did not finish: the tool, and PdfCraft's own message."""
    def __init__(self, message, tool=None, steps=None):
        super().__init__(message)
        self.tool, self.steps = tool, steps or []


def pin():
    try:
        return PIN_FILE.read_text().strip()
    except OSError:
        return None


def binary():
    """The PdfCraft program: PDFCRAFT_CLI, then vendor/pdfcraft beside the program (the desktop build carries it there), then the
    PATH. None in the browser edition, when PDFCRAFT=0, or when it is not on this machine."""
    if sys.platform == 'emscripten' or os.environ.get('PDFCRAFT') == '0':
        return None
    env = os.environ.get('PDFCRAFT_CLI')
    if env in _found:
        return _found[env]
    cands = [env] if env else []
    base = getattr(sys, '_MEIPASS', None)
    if base:
        cands.append(str(Path(base) / 'pdfcraft' / EXE))
    cands += [str(APP / 'vendor' / 'pdfcraft' / EXE), shutil.which('pdfcraft-cli')]
    hit = next((c for c in cands if c and os.path.isfile(c) and os.access(c, os.X_OK)), None)
    _found[env] = hit
    return hit


def available():
    return binary() is not None


def version():
    b = binary()
    if not b:
        return None
    try:
        r = subprocess.run([b, '--version'], capture_output=True, text=True, timeout=20)
        return ((r.stdout or r.stderr).strip().splitlines() or [None])[0]
    except (OSError, subprocess.SubprocessError):
        return None


def status():
    """What the interface shows: which engine reads the PDFs here."""
    b = binary()
    return {'available': bool(b), 'version': version() if b else None, 'pin': pin(),
            'engine': 'PdfCraft' if b else 'pypdf',
            'why': None if b else ('the browser edition reads PDFs with pypdf' if sys.platform == 'emscripten'
                                   else 'PdfCraft is not built on this machine (tools/pdfcraft/build.sh)')}


class Job:
    """One PdfCraft run in its own folder. put() the files, add steps, run(), then read() what the steps wrote.

        with Job() as j:
            j.put('in.pdf', data)
            j.step('doc_open', path='in.pdf')
            j.step('doc_info', doc=1)
            info = j.run()[1][0]
    """
    def __init__(self, timeout=TIMEOUT):
        self.timeout, self.steps = timeout, []
        self.dir = Path(tempfile.mkdtemp(prefix='pdfcraft-'))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.dir, ignore_errors=True)

    def path(self, name):
        p = (self.dir / name).resolve()
        if self.dir.resolve() not in p.parents and p != self.dir.resolve():
            raise ValueError(f'{name}: outside the job folder')
        return p

    def put(self, name, data):
        p = self.path(name)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, (bytes, bytearray)) else Path(data).read_bytes())
        return name

    def step(self, tool, args=None, *, out=None, **kw):
        """A tool and its arguments (a dict, or keywords); `out` is where a tool's image is written."""
        a = {**(args or {}), **kw}
        s = {'tool': tool, 'args': {k: v for k, v in a.items() if v is not None}}
        if out:
            s['out'] = out
        self.steps.append(s)
        return len(self.steps) - 1

    def run(self):
        """Each step's result: the list of values its tool returned. Raises PdfCraftError on the first step that failed."""
        b = binary()
        if not b:
            raise PdfCraftError('PdfCraft is not available on this machine')
        script = self.dir / '.steps.json'
        script.write_text(json.dumps(self.steps))
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'USERPROFILE', 'SYSTEMROOT', 'TEMP', 'TMP', 'LANG', 'LC_ALL')}
        try:
            r = subprocess.run([b, 'run', '--script', str(script), '--root', str(self.dir), '--report'], cwd=self.dir, env=env,
                               capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            raise PdfCraftError(f'PdfCraft took longer than {self.timeout} s')
        except OSError as e:
            raise PdfCraftError(f'PdfCraft could not start: {e}')
        try:
            rep = json.loads(r.stdout)
        except ValueError:
            raise PdfCraftError((r.stderr or r.stdout or f'exit {r.returncode}').strip()[:500])
        steps = rep.get('steps') or []
        bad = next((s for s in steps if s.get('status') == 'error'), None)
        if bad or not rep.get('ok'):
            msg = (bad or {}).get('error') or (r.stderr or 'PdfCraft failed').strip()
            raise PdfCraftError(f"{(bad or {}).get('tool')}: {msg}"[:600], tool=(bad or {}).get('tool'), steps=steps)
        return [s.get('result') or [] for s in steps]

    def read(self, name):
        return self.path(name).read_bytes()


def run(steps, files=None, timeout=TIMEOUT, read=()):
    """One-call form: steps [(tool, args)] or [(tool, args, out)], files {name: bytes} → (results, {name: bytes} for `read`)."""
    with Job(timeout) as j:
        for name, data in (files or {}).items():
            j.put(name, data)
        for s in steps:
            j.step(s[0], s[1], out=s[2] if len(s) > 2 else None)
        res = j.run()
        return res, {n: j.read(n) for n in read if j.path(n).exists()}


def first(values, default=None):
    """The JSON value of a step's result (a tool returns a list of parts; most return one)."""
    for v in values or []:
        if isinstance(v, (dict, list)):
            return v
    return default


def _results(steps):
    """The results of the steps a failed run finished (their report), None for the rest."""
    return [s.get('result') if s.get('status') == 'ok' else None for s in steps]


def query(data, tools, password=None, timeout=TIMEOUT):
    """Read-only questions about one PDF, each answered even when another fails: {tool or (tool, n): value}, '_errors': {...}.
    tools: [(tool, args)] on document 1 (the file opened first). None when PdfCraft is not here or cannot open the file."""
    if not available():
        return None
    pending = list(enumerate(tools))
    out, errors, opened = {}, {}, None
    while pending:
        with Job(timeout) as j:
            j.put('in.pdf', data)
            j.step('doc_open', path='in.pdf', password=password)
            for _, (tool, args) in pending:
                j.step(tool, {'doc': 1, **(args or {})})
            try:
                res, fail = j.run(), None
            except PdfCraftError as e:
                status = [x.get('status') for x in e.steps]
                if not status:                               # no report (it stopped or took too long): what is left is not known
                    if opened is None:
                        return None
                    errors.update({tool: str(e) for _, (tool, _a) in pending})
                    break
                if status[0] != 'ok':                        # the file itself did not open
                    return None
                if 'error' not in status:
                    errors['_run'] = str(e)
                    break
                res, fail = _results(e.steps), status.index('error')
                errors[pending[fail - 1][1][0]] = str(e)
        opened = opened or first(res[0])
        done = pending if fail is None else pending[:fail - 1]
        for (i, _), r in zip(done, res[1:]):
            out[i] = first(r, r)
        pending = [] if fail is None else pending[fail:]
    named = {'_open': opened, '_errors': errors}
    for i, (tool, _) in enumerate(tools):
        if i in out:
            named[tool if tool not in named else (tool, i)] = out[i]
    return named


def pdf_pages(data, max_pages=None, password=None):
    """(page count, [text of each page read]) in reading order — PdfCraft's reading: the lines in order, right-to-left text in its own
    order, a heading number such as «3.2.P.5.1» whole. None when PdfCraft is not here or cannot read the file: the caller reads it the
    earlier way."""
    if not available() or not data or data[:5] != b'%PDF-':
        return None
    try:
        res, _ = run([('doc_open', {'path': 'in.pdf', 'password': password})], {'in.pdf': data})
        n = int(first(res[0])['pages'])
        if not n:
            return 0, []
        want = list(range(1, min(n, max_pages or n) + 1))
        res, _ = run([('doc_open', {'path': 'in.pdf', 'password': password}), ('text_extract', {'doc': 1, 'pages': want})], {'in.pdf': data})
        return n, [p.get('text') or '' for p in (first(res[1]) or {}).get('pages', [])]
    except (PdfCraftError, KeyError, TypeError, ValueError):
        return None


def page_texts(data, max_pages=None, password=None):
    r = pdf_pages(data, max_pages, password)
    return None if r is None else r[1]


def reader():
    """Which engine reads the PDFs here: 'pdfcraft' or 'pypdf' (kept readings are told apart by it)."""
    return 'pdfcraft' if available() else 'pypdf'


def page_count(data, password=None):
    if not available():
        return None
    try:
        res, _ = run([('doc_open', {'path': 'in.pdf', 'password': password})], {'in.pdf': data})
        return int(first(res[0])['pages'])
    except (PdfCraftError, KeyError, TypeError, ValueError):
        return None


def inspect(data, text_pages=12, password=None):
    """What the checks read from a PDF, in one pass: its information (version, fonts, security, bookmarks, links, attachments,
    comments, JavaScript, portfolio, repairs), how it opens, its links, its signatures, hidden information, faux redactions and the text
    of its first pages. None when PdfCraft is not here or cannot open the file."""
    q = query(data, [('doc_info', {}), ('doc_initial_view', {}), ('link_list', {}), ('sign_list', {}), ('doc_hidden_info', {}),
                     ('doc_audit_redactions', {}), ('js_document_scripts', {})], password=password)
    if q is None:
        return None
    n = int((q.get('_open') or {}).get('pages') or 0)
    texts = page_texts(data, max_pages=text_pages, password=password) if n else []
    if texts is None:                                    # PdfCraft honours «no copying»: the text is read as before (pypdf)
        texts, q['text_reader'] = pypdf_texts(data, text_pages), 'pypdf'
    q['texts'], q['pages'] = texts, n
    return q


def pypdf_texts(data, max_pages=None):
    """The earlier reading (pypdf): the browser edition's, and a file whose security does not let PdfCraft copy its text."""
    import io as _io
    from pypdf import PdfReader
    try:
        rd = PdfReader(_io.BytesIO(data), strict=False)
        if rd.is_encrypted:
            rd.decrypt('')
        out = []
        for p in (rd.pages[:max_pages] if max_pages else rd.pages):
            try:
                out.append(p.extract_text() or '')
            except Exception:
                out.append('')
        return out
    except Exception:
        return []


def render(data, pages=None, dpi=60, password=None):
    """PNG images of the pages (all, or the 1-based `pages`). None when PdfCraft is not here or cannot draw them."""
    if not available():
        return None
    try:
        n = page_count(data, password) if pages is None else None
        pages = pages or list(range(1, (n or 0) + 1))
        with Job() as j:
            j.put('in.pdf', data)
            j.step('doc_open', path='in.pdf', password=password)
            for p in pages:
                j.step('page_render', doc=1, page=int(p), dpi=dpi, out=f'p{int(p):05d}.png')
            j.run()
            return [j.read(f'p{int(p):05d}.png') for p in pages]
    except (PdfCraftError, OSError, ValueError):
        return None


def same_pixels(a, b, dpi=60):
    """Do two PDFs look the same, page for page (drawn by PdfCraft at `dpi`)? True / False, or None when it cannot be told here
    (no PdfCraft, or no image library to compare the pictures)."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    import io as _io
    ra, rb = render(a, dpi=dpi), render(b, dpi=dpi)
    if ra is None or rb is None:
        return None
    if len(ra) != len(rb):
        return False
    for x, y in zip(ra, rb):
        if x == y:
            continue
        ia, ib = Image.open(_io.BytesIO(x)).convert('RGB'), Image.open(_io.BytesIO(y)).convert('RGB')
        if ia.size != ib.size or ImageChops.difference(ia, ib).getbbox() is not None:
            return False
    return True


def repair(data):
    """A clean copy of a damaged PDF (PdfCraft reads it tolerantly — the cross-reference rebuilt from the objects — and writes it
    whole): (bytes, notes), or (None, why)."""
    if not available():
        return None, 'PdfCraft is not here'
    try:
        res, out = run([('doc_open', {'path': 'in.pdf'}), ('doc_info', {'doc': 1}), ('doc_save', {'doc': 1, 'path': 'out.pdf', 'full': True})],
                       {'in.pdf': data}, read=('out.pdf',))
        return out.get('out.pdf'), list((first(res[1]) or {}).get('repairs') or [])
    except PdfCraftError as e:
        return None, str(e)


def split(data, ranges):
    """The PDF of each page range (1-based, inclusive), with the links, bookmarks and fields of its pages."""
    with Job() as j:
        j.put('in.pdf', data)
        j.step('doc_open', path='in.pdf')
        for k, (a, b) in enumerate(ranges, 1):
            j.steps.append({'tool': 'page_extract', 'args': {'doc': 1, 'pages': list(range(int(a), int(b) + 1)), 'out': f'part-{k}.pdf', 'open': False}})
        j.run()
        return [j.read(f'part-{k}.pdf') for k in range(1, len(ranges) + 1)]


def combine(datas):
    """One PDF of all the given PDFs' pages, in order (their bookmarks kept, one entry per file)."""
    with Job() as j:
        names = [j.put(f'in-{k:04d}.pdf', d) for k, d in enumerate(datas, 1)]
        if len(names) == 1:
            return datas[0]
        j.steps.append({'tool': 'doc_combine', 'args': {'paths': names, 'out': 'out.pdf', 'open': False}})
        j.run()
        return j.read('out.pdf')


def compare(old, new, limit=400, marked=False):
    """What changed from the older PDF to the newer one, word by word, with pages and places: {'counts', 'changes': [...]} and,
    with marked=True, 'marked': the newer PDF with the changes as comments (blue replaced, green inserted, red deleted)."""
    steps = [('doc_open', {'path': 'old.pdf'}), ('doc_open', {'path': 'new.pdf'}), ('doc_compare', {'doc': 2, 'other': 1, 'limit': limit})]
    if marked:
        steps += [('doc_compare_mark', {'doc': 2, 'other': 1}), ('doc_save', {'doc': 2, 'path': 'marked.pdf'})]
    res, out = run(steps, {'old.pdf': old, 'new.pdf': new}, read=('marked.pdf',) if marked else ())
    r = dict(first(res[2]) or {})
    if marked:
        r['marked'] = out.get('marked.pdf')
    return r


def find(data, phrase, limit=200):
    """Where a phrase is, page by page, with its rectangles (points from the top-left of the page)."""
    res, _ = run([('doc_open', {'path': 'in.pdf'}), ('text_find', {'doc': 1, 'query': phrase, 'limit': limit})], {'in.pdf': data})
    return (first(res[1]) or {}).get('matches') or []


def page_png(data, page, dpi=96):
    res, out = run([('doc_open', {'path': 'in.pdf'}), ('page_render', {'doc': 1, 'page': int(page), 'dpi': dpi}, 'page.png')],
                   {'in.pdf': data}, read=('page.png',))
    return out.get('page.png')


def reduce(data):
    """A smaller copy (images above 225 ppi brought to 150 ppi and recompressed, as Acrobat's Reduce File Size): (bytes, report)."""
    res, out = run([('doc_open', {'path': 'in.pdf'}), ('doc_reduce', {'doc': 1, 'path': 'out.pdf'})], {'in.pdf': data}, read=('out.pdf',))
    return out.get('out.pdf'), first(res[1]) or {}


def watermark(data, text, opacity=0.25, color='#b00020'):
    res, out = run([('doc_open', {'path': 'in.pdf'}), ('doc_watermark', {'doc': 1, 'text': text, 'opacity': opacity, 'color': color}),
                    ('doc_save', {'doc': 1, 'path': 'out.pdf'})], {'in.pdf': data}, read=('out.pdf',))
    return out.get('out.pdf')


def redact(data, words=None, rects=None):
    """Real redaction: the text, images and drawings under each mark removed for good and a box drawn in their place; PdfCraft then
    checks nothing readable is left and fails the whole job when something is. words: phrases (every match); rects: [(page, [x0, y0,
    x1, y1])] in points from the top-left. → (bytes, {'marks': n})"""
    steps = [('doc_open', {'path': 'in.pdf'})]
    for w in words or []:
        steps.append(('redact_mark', {'doc': 1, 'find': w}))
    for page, rect in rects or []:
        steps.append(('redact_mark', {'doc': 1, 'page': int(page), 'rect': [float(v) for v in rect]}))
    steps += [('redact_apply', {'doc': 1}), ('doc_save', {'doc': 1, 'path': 'out.pdf', 'full': True})]
    res, out = run(steps, {'in.pdf': data}, read=('out.pdf',))
    return out.get('out.pdf'), {'marks': len(steps) - 3, 'applied': first(res[-2]) or {}}
