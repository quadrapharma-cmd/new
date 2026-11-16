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
import json, os, re, shutil, signal, subprocess, sys, tempfile
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


def browser():
    """The browser edition's PdfCraft — the same program built for WebAssembly, run in the engine's thread (web/pdfcraft.wasi.js) —
    once it is loaded; None elsewhere, before it is, or when PDFCRAFT=0."""
    if sys.platform != 'emscripten' or os.environ.get('PDFCRAFT') == '0':
        return None
    try:
        import js
        b = getattr(js, 'DB_PDFCRAFT', None)
        return b if b is not None and bool(b.ready) else None
    except Exception:                                    # noqa: BLE001 — no page, no PdfCraft
        return None


def available():
    return binary() is not None or browser() is not None


TESSERACT_PLACES = ('C:/Program Files/Tesseract-OCR/tesseract.exe', 'C:/Program Files (x86)/Tesseract-OCR/tesseract.exe',
                    '/opt/homebrew/bin/tesseract', '/usr/local/bin/tesseract', '/usr/bin/tesseract')


def tesseract():
    """The Tesseract program PdfCraft's text recognition drives: PDFCRAFT_TESSERACT, the PATH, or where its installers put it
    (Windows: the UB Mannheim installer; macOS: Homebrew). None when it is not on this machine."""
    if 'tess' in _found:
        return _found['tess']
    env = os.environ.get('PDFCRAFT_TESSERACT')
    hit = next((c for c in [env, shutil.which('tesseract'), *TESSERACT_PLACES] if c and os.path.isfile(c) and os.access(c, os.X_OK)), None)
    _found['tess'] = hit
    return hit


def tessdata():
    """The accurate («best») Arabic and English models the program ships (tools/tesseract/fetch.py — Apache-2.0): DOSSIER_TESSDATA,
    the desktop bundle's «tessdata», or vendor/tessdata beside the program; a folder holding ara and eng and the «tsv» setting
    PdfCraft's reading asks for. None when the program has none of its own: Tesseract then reads with the models its installer
    brought (the «fast» ones read Arabic less well)."""
    if 'tessdata' in _found:
        return _found['tessdata']
    places = [os.environ.get('DOSSIER_TESSDATA')]
    base = getattr(sys, '_MEIPASS', None)
    if base:
        places.append(str(Path(base) / 'tessdata'))
    places.append(str(APP / 'vendor' / 'tessdata'))
    need = ('ara.traineddata', 'eng.traineddata', os.path.join('configs', 'tsv'))
    hit = next((d for d in places if d and all(os.path.isfile(os.path.join(d, f)) for f in need)), None)
    _found['tessdata'] = hit
    return hit


def _tess_env(env):
    """Tesseract reads with the program's own models unless TESSDATA_PREFIX says otherwise."""
    if 'TESSDATA_PREFIX' not in env and tessdata():
        env['TESSDATA_PREFIX'] = os.path.join(tessdata(), '')
    return env


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
    b, web = binary(), browser()
    if web is not None:
        return {'available': True, 'version': f'pdfcraft-cli {pin() or ""} (WebAssembly)'.strip(), 'pin': pin(), 'engine': 'PdfCraft',
                'where': 'browser', 'why': None}
    return {'available': bool(b), 'version': version() if b else None, 'pin': pin(),
            'engine': 'PdfCraft' if b else 'pypdf',
            'why': None if b else ('PdfCraft is still loading in this browser, or this browser cannot run it: pypdf reads the PDFs meanwhile'
                                   if sys.platform == 'emscripten' else 'PdfCraft is not built on this machine (tools/pdfcraft/build.sh)')}


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
            if browser() is not None:
                return self._report(self._run_in_browser())
            raise PdfCraftError('PdfCraft is not available on this machine')
        script = self.dir / '.steps.json'
        script.write_text(json.dumps(self.steps))
        env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'USERPROFILE', 'SYSTEMROOT', 'TEMP', 'TMP', 'LANG', 'LC_ALL',
                                                            'PDFCRAFT_TESSERACT', 'TESSDATA_PREFIX', 'PDFCRAFT_MODELS', 'OMP_THREAD_LIMIT')}
        tess = tesseract()
        if tess and 'PDFCRAFT_TESSERACT' not in env:
            env['PDFCRAFT_TESSERACT'] = tess                 # Tesseract where its installer puts it, when it is not on the PATH
        _tess_env(env)                                       # and its models: the program's accurate ones, where it ships them
        try:
            r = _run_tree([b, 'run', '--script', str(script), '--root', str(self.dir), '--report'], self.dir, env, self.timeout)
        except subprocess.TimeoutExpired:
            raise PdfCraftError(f'PdfCraft took longer than {self.timeout} s')
        except OSError as e:
            raise PdfCraftError(f'PdfCraft could not start: {e}')
        return self._report(r)

    def _run_in_browser(self):
        """The same run in the browser edition: the job's files lent to PdfCraft's WebAssembly program (web/pdfcraft.wasi.js) and
        what it wrote put back in the job's folder, so read() and the folder's files work as on a computer."""
        import js
        from pyodide.ffi import to_js
        files = js.Map.new()
        for f in self.dir.rglob('*'):
            if f.is_file() and f.name != '.steps.json':
                files.set(f.relative_to(self.dir).as_posix(), to_js(f.read_bytes()))
        try:
            r = browser().run(json.dumps(self.steps), files)
        except Exception as e:                           # noqa: BLE001 — what the browser said, as PdfCraft's own failure
            raise PdfCraftError(f'PdfCraft (browser): {e}'[:500])
        for pair in r.files:                             # [[name, bytes], …]
            name, data = str(pair[0]), pair[1]
            dest = self.path(name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data.to_bytes())
        return subprocess.CompletedProcess(['pdfcraft-cli'], int(r.code), r.stdout.to_bytes().decode('utf-8', 'replace'),
                                           r.stderr.to_bytes().decode('utf-8', 'replace'))

    def _report(self, r):
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


def _run_tree(cmd, cwd, env, timeout):
    """Run PdfCraft as the head of its own process group, so a run that takes too long is stopped with every program it started
    (Tesseract reading a page): killing PdfCraft alone would leave those running on, each taking the processor for nothing."""
    win = sys.platform == 'win32'
    p = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
                         errors='replace', **({'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000} if win    # no console window
                                              else {'start_new_session': True}))
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            if win:
                subprocess.run(['taskkill', '/T', '/F', '/PID', str(p.pid)], capture_output=True, timeout=30, creationflags=0x08000000)
            else:
                os.killpg(p.pid, signal.SIGKILL)
        except (OSError, subprocess.SubprocessError):
            p.kill()
        p.communicate()
        raise
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


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


def smaller_enough(old, new):
    """A copy is kept as «smaller» only when it clearly is: at least 5 % and 4 KB less. Writing a file again changes a few bytes by
    itself (its dates, its ID) — a copy a few bytes shorter is not a smaller file, and it would only make a needless new version."""
    return bool(new) and len(new) <= 0.95 * len(old) and len(old) - len(new) >= 4096


def reduce(data):
    """A smaller copy (images above 225 ppi brought to 150 ppi and recompressed, as Acrobat's Reduce File Size): (bytes, report)."""
    res, out = run([('doc_open', {'path': 'in.pdf'}), ('doc_reduce', {'doc': 1, 'path': 'out.pdf'})], {'in.pdf': data}, read=('out.pdf',))
    return out.get('out.pdf'), first(res[1]) or {}


OPT_CLEAN = {'discard_thumbnails': True, 'discard_alternate_images': True, 'discard_search_index': True, 'flate_unencoded': True,
             'lzw_to_flate': True, 'remove_unreferenced_dests': True, 'object_streams': False}
OPT_KEEP = {'downsample': False, 'compression': 'retain'}                                      # every picture as it is
OPT_GENTLE = {'downsample': True, 'ppi': 300, 'above_ppi': 450, 'compression': 'jpeg', 'quality': 80}   # a scan stays 300 ppi: read and OCR'd as well


def optimize(data, lossless=True, links=False, pdf20=False):
    """«Improve the file» — PdfCraft's PDF Optimizer (Acrobat's): thumbnails, alternate pictures, search indexes and destinations nothing
    points to dropped, uncompressed and LZW streams compressed (Flate). lossless: every picture kept as it is, so the pages are the same
    pixel for pixel (a third party's document); otherwise pictures above 450 ppi brought to 300 ppi (JPEG quality 80; black-and-white
    stays lossless) — a scan is still read and OCR'd as well. links: links that go nowhere removed (a company's own document).
    pdf20: a PDF 2.0 written as 1.7 (eCTD takes 1.4–1.7). → (bytes, report)."""
    pics = OPT_KEEP if lossless else OPT_GENTLE
    mono = OPT_KEEP if lossless else {'downsample': True, 'ppi': 300, 'above_ppi': 450}
    args = {'doc': 1, 'path': 'out.pdf', 'preset': 'standard', 'merge_fragments': not lossless, 'color': pics, 'gray': pics, 'mono': mono,
            'remove_invalid_links': bool(links), 'compatibility': '1.7' if pdf20 else 'retain', **OPT_CLEAN}
    res, out = run([('doc_open', {'path': 'in.pdf'}), ('doc_optimize', args)], {'in.pdf': data}, read=('out.pdf',))
    return out.get('out.pdf'), first(res[1]) or {}


def split_by_size(data, limit_mb=95.0):
    """A file too large for an eCTD (100 MB a file) cut into parts that each fit: at its top-level bookmarks when every part then
    fits (each part one of its chapters), otherwise by size (PdfCraft's doc_split; pages unchanged, each part with its own pages'
    links and bookmarks). → [(bytes, first page, last page or None)], in order."""
    def cut(args):
        with Job() as j:
            j.put('in.pdf', data)
            j.step('doc_open', path='in.pdf')
            j.step('doc_split', {'doc': 1, 'out_dir': 'parts', **args})
            res = j.run()
            files = sorted((j.dir / 'parts').glob('*.pdf'), key=lambda f: [int(x) if x.isdigit() else x for x in re.split(r'(\d+)', f.name)])
            return [f.read_bytes() for f in files], first(res[1]) or {}
    parts, rep = cut({'bookmarks': True})
    if len(parts) < 2 or any(len(x) > limit_mb * 1e6 for x in parts):
        parts, rep = cut({'max_mb': limit_mb})
    return parts, rep


def to_word(data):
    """An editable Word copy of a PDF (PdfCraft's Export a PDF ▸ Word: its text, headings, bold and italic, tables), for amending a
    document that exists only as a PDF. The PDF itself is not changed. → .docx bytes, or None."""
    res, out = run([('doc_open', {'path': 'in.pdf'}), ('doc_export_office', {'doc': 1, 'path': 'out.docx'})], {'in.pdf': data}, read=('out.docx',))
    return out.get('out.docx')


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


_OCR = {}


def ocr_info():
    """What PdfCraft's text recognition reads here: {'available', 'language' ('ar+en' when Tesseract has Arabic and English,
    'en' with English alone), 'engine': 'tesseract', 'version'} — or None (no PdfCraft, or no Tesseract). Tesseract is an installed
    program PdfCraft drives as a separate process (its own fenced runner); the answer is kept for a minute."""
    import time
    if not available():
        return None
    hit = _OCR.get('info')
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    info = None
    try:
        res, _ = run([('ocr_status', {})], timeout=60)
        st = first(res[0]) or {}
        tess = next((e for e in st.get('engines') or [] if e.get('id') == 'tesseract' and e.get('available')), None)
        if tess and tess.get('path'):
            r = subprocess.run([tess['path'], '--list-langs'], capture_output=True, text=True, timeout=30, env=_tess_env(dict(os.environ)))
            langs = set((r.stdout + '\n' + r.stderr).split())
            lang = 'ar+en' if {'ara', 'eng'} <= langs else 'ar' if 'ara' in langs else 'en' if 'eng' in langs else None
            if lang:
                own = tessdata() and 'TESSDATA_PREFIX' not in os.environ
                info = {'available': True, 'language': lang, 'engine': 'tesseract', 'version': tess.get('version'),
                        'arabic': 'ara' in langs, 'models': 'best 4.1.0' if own else 'installed'}
    except (PdfCraftError, OSError, subprocess.SubprocessError, ValueError):
        info = None
    _OCR['info'] = (time.time(), info)
    return info


WEAK = 3.0                     # % of a page's words read with low confidence (< 70) past which the page is read again
STRAIGHTEN = {'deskew': True, 'auto_rotate': True}


def _quality(result):
    """Per page, from ocr_words: {page: {words, low (% of words under 70), mean, numbers (low-confidence words with digits)}}."""
    out = {}
    for p in (result or {}).get('pages') or []:
        words = p.get('words') or []
        low = [w for w in words if (w.get('confidence') or 0) < 70]
        out[int(p.get('page') or 0)] = {
            'words': len(words), 'low': round(100.0 * len(low) / len(words), 1) if words else 0.0,
            'mean': round(float(p.get('mean_confidence') or 0), 1),
            'numbers': [w.get('text') for w in low if any(ch.isdigit() for ch in (w.get('text') or ''))][:20]}
    return out


def _weak(q):
    return q['words'] == 0 or q['low'] > WEAK


def _better(new, old):
    """The reading with fewer low-confidence words; at about the same, the one with the higher mean confidence."""
    if not new or not new['words']:
        return False
    if not old['words']:
        return True
    if abs(new['low'] - old['low']) > 0.5:
        return new['low'] < old['low']
    return new['mean'] > old['mean'] + 1.0


def ocr(data, pages=None, timeout=None):
    """Text recognition by PdfCraft (Tesseract, Arabic and English), checked as it goes: the pages are read as scanned and that
    reading is written over the page image (the page looks the same, the document becomes searchable). A page read with many
    low-confidence words — skewed, sideways, upside down — is read again straightened and turned upright, and the better of the two
    readings is kept, page by page (as scanned, a straight Arabic notice: 0.5 % of its characters wrong; «straightened»: 14.7 %;
    sideways the other way round — docs/ctd/PDFCRAFT-INTEGRATION.md). Then the words Tesseract is still unsure of are read again by
    PaddleOCR (paddle_rec), and its reading written where it is sure: the Arabic-Indic number and date of a notice come back right.
    → (searchable PDF bytes, [text of each page in reading order], {'words', 'pages': [{page, words}], 'quality': {page: {words,
    low, mean, numbers (still doubtful), read, second?}}, 'weak': [pages still hard to read], 'second_reader': words corrected}).
    Pages that already have text are left as they are. None when recognition is not available here."""
    info = ocr_info()
    if not info:
        return None
    n = page_count(data) or 0
    want = sorted({int(p) for p in pages if 1 <= int(p) <= n}) if pages else None
    base = {'doc': 1, 'engine': 'tesseract', 'language': info['language']}
    sel = {'pages': want} if want else {}
    count = len(want) if want else max(n, 1)
    t = timeout or min(1800, 60 + 15 * count)
    save = ('doc_save', {'doc': 1, 'path': 'out.pdf', 'full': True})
    # 1) read as scanned, and that same reading written over the pages (one pass)
    try:
        res, out = run([('doc_open', {'path': 'in.pdf'}), ('ocr_words', {**base, **sel, 'retain_review': True}),
                        ('ocr_review_apply', {'doc': 1, 'review': 1}), save], {'in.pdf': data}, timeout=t, read=('out.pdf',))
        made, words = out.get('out.pdf'), first(res[1])
    except PdfCraftError as e:                                 # no word on any page (a blank scan): nothing to write, the file as it was
        if e.tool != 'ocr_review_apply' or len(e.steps) < 2 or e.steps[1].get('status') == 'error':
            raise
        made, words = data, first(e.steps[1].get('result') or [])
    quality = _quality(words)
    for q in quality.values():
        q['read'] = 'as scanned'
    # 2) the second reader first: on each page, the runs of words Tesseract is unsure of read again by PaddleOCR from the page image
    #    (paddle_rec); where it is sure, its reading will be written instead — the Arabic-Indic numbers above all. A page whose
    #    doubtful words it settles is no longer weak, so it is not «straightened» for them.
    from . import paddle_rec
    on_page = {int(x.get('page') or 0): x.get('words') or [] for x in (words or {}).get('pages') or []}
    fixes = {}
    if paddle_rec.available():
        for p, q in sorted(quality.items()):
            ws = on_page.get(p) or []
            if not q['words'] or not any((w.get('confidence') or 0) < 70 for w in ws):
                continue
            try:
                found, seen = paddle_rec.second_reading({300: page_png(data, p, 300), 400: page_png(data, p, 400)}, ws)
            except Exception as e:                             # noqa: BLE001 — a help, never a failure: Tesseract's reading stands
                q['second'] = {'error': str(e)[:200]}
                continue
            if found:
                fixes[p] = found
            settled = {f['word'] for f in found}
            still = [i for i, w in enumerate(ws, 1) if (w.get('confidence') or 0) < 70 and i not in settled]
            q.update(low=round(100.0 * len(still) / len(ws), 1),
                     numbers=[ws[i - 1].get('text') for i in still if any(c.isdigit() for c in ws[i - 1].get('text') or '')][:20],
                     second={'read': len(seen), 'changed': [{'was': x['tesseract'], 'now': x['paddle']} for x in seen
                                                            if x['paddle'] and x['paddle'] != x['tesseract'] and x['confidence'] >= 0.8]})
    weak = sorted(p for p, q in quality.items() if _weak(q))
    straight = []
    if weak:
        # 3) the pages still weak read again, straightened and turned upright; the better reading kept, page by page
        res2, _ = run([('doc_open', {'path': 'in.pdf'}), ('ocr_words', {**base, **STRAIGHTEN, 'pages': weak})], {'in.pdf': data},
                      timeout=min(1800, 60 + 15 * len(weak)))
        again = _quality(first(res2[1]))
        straight = [p for p in weak if _better(again.get(p), quality[p])]
        for p in straight:
            quality[p] = {**again[p], 'read': 'straightened'}
            fixes.pop(p, None)                                 # its words are not the ones the second reader read
    if fixes or straight:
        # 4) written again: each page with its own reading — as scanned with the second reader's words, or straightened
        plain = [p for p in sorted(quality) if p not in straight]
        steps = [('doc_open', {'path': 'in.pdf'})]
        if plain:
            steps += [('ocr_words', {**base, 'pages': plain, 'retain_review': True}),
                      ('ocr_review_apply', {'doc': 1, 'review': 1, 'corrections': [{'page': p, **f} for p in plain for f in fixes.get(p, [])]})]
        if straight:
            steps.append(('ocr_recognize', {**base, **STRAIGHTEN, 'pages': straight}))
        try:
            _, out4 = run(steps + [save], {'in.pdf': data}, timeout=t, read=('out.pdf',))
            made = out4.get('out.pdf') or made
        except PdfCraftError as e:                             # the plain pages had no word to write: the straightened ones alone
            if e.tool != 'ocr_review_apply' or not straight:
                raise
            _, out4 = run([('doc_open', {'path': 'in.pdf'}), ('ocr_recognize', {**base, **STRAIGHTEN, 'pages': straight}), save],
                          {'in.pdf': data}, timeout=t, read=('out.pdf',))
            made = out4.get('out.pdf') or made
    fixes = [f for fs in fixes.values() for f in fs]
    pages_rep = [{'page': p, 'words': q['words']} for p, q in sorted(quality.items())]
    rep = {'words': sum(q['words'] for q in quality.values()), 'pages': pages_rep, 'quality': quality, 'second_reader': len(fixes),
           'weak': sorted(p for p, q in quality.items() if _weak(q)), 'models': info.get('models')}
    texts = page_texts(made, max_pages=max(want) if want else None) if made else None
    return made, texts or [], rep


PROBE_DPI = 150
LYING, STANDING, CLEAR, MANY = 0.8, 0.2, 15, 30


def _flat(words):
    """The share of a reading's longer words (three characters or more) that lie flat — wider than tall: Tesseract also reads
    text lying on its side, almost as well, so the turn that is upright is the one whose words lie flat (ocr.js flat)."""
    long = [w for w in words if len(w.get('text') or '') >= 3]
    return sum(1 for w in long if (w.get('box') or [0, 0, 0, 0])[2] >= (w.get('box') or [0, 0, 0, 0])[3]) / len(long) if long else 0.0


def _upright(q):
    """ocr.js upright(): the words read surely (rounded as JavaScript rounds) times the share lying flat."""
    good = q['words'] - int(q['words'] * q['low'] / 100.0 + 0.5)
    return good * q['flat']


def _probe_dpi(data, pixels):
    """The dpi at which the page is drawn as large as the page reader draws the photo for its test: the photo brought to 2000–4200
    pixels on its long side as «300 dpi» (ocr.js images()), at 150 dpi half that — so both editions decide on the same picture."""
    try:
        import io
        from pypdf import PdfReader
        box = PdfReader(io.BytesIO(data)).pages[0].mediabox
        pts = max(float(box.width), float(box.height))
        long = max(pixels)
        fit = long * min(3.0, 2000.0 / long) if long < 2000 else 4200.0 if long > 4200 else float(long)
        return max(72.0, min(600.0, 72.0 * (fit * PROBE_DPI / 300.0) / pts))
    except Exception:                                          # noqa: BLE001 — the reader's own dpi, as a page of a scan
        return float(PROBE_DPI)


def upright_turn(data, pixels=None):
    """Which way up the first page of a photo made a PDF is: a phone lying flat on a desk does not know how it is held, so a photo
    of a sheet often comes sideways (5 of his 21 WhatsApp photos of documents). The page reader's own test and decision
    (ui/assets/ocr.js turnOf — the browser edition turns the photo there, before it leaves the page): read at 150 dpi as it is;
    then, where its words clearly lie flat, upside down only; where they clearly stand, the two sideways turns; else all three; a
    turn taken only when it is better than the page as it is by the reader's measure (1.5 × + 3) and at least twice every other
    turn read. pixels: the photo's (width, height), to draw it as large as the page reader does. → 0, 90, 180 or 270
    (clockwise); 0 when recognition is not here or nothing is clear."""
    info = ocr_info()
    if not info:
        return 0
    base = {'doc': 1, 'engine': 'tesseract', 'language': info['language'], 'dpi': _probe_dpi(data, pixels) if pixels else PROBE_DPI,
            'pages': [1], 'force_ocr': True}

    def look(rots):                                            # the page read in each turn asked: {turn: quality with flat}
        steps, at, now = [('doc_open', {'path': 'in.pdf'})], {}, 0
        for r in rots:
            if r != now:
                steps.append(('page_rotate', {'doc': 1, 'degrees': (r - now) % 360, 'pages': [1]}))
                now = r
            at[r] = len(steps)
            steps.append(('ocr_words', base))
        res, _ = run(steps, {'in.pdf': data}, timeout=min(1800, 60 + 30 * len(rots)))
        out = {}
        for r, i in at.items():
            words = (first(res[i]) or {}).get('pages') or [{}]
            q = _quality(first(res[i])).get(1) or {'words': 0, 'low': 0.0, 'mean': 0.0}
            out[r] = {**q, 'flat': _flat(words[0].get('words') or [])}
        return out
    try:
        q = look([0])
        q0 = q[0]
        rots = ([180] if q0['flat'] >= LYING and _upright(q0) >= CLEAR else
                [90, 270] if q0['words'] >= MANY and q0['flat'] <= STANDING else [90, 270, 180])
        q.update(look(rots))
    except (PdfCraftError, OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError):
        return 0
    best = None
    for r in rots:                                             # the reader's order and choice
        qq = q[r]
        if qq['words'] and (best is None or _upright(qq) > _upright(q[best]) or
                            (_upright(qq) == _upright(q[best]) and qq['mean'] > q[best]['mean'] + 1)):
            best = r
    if best is None or not _upright(q[best]) > 1.5 * _upright(q0) + 3:
        return 0
    return best if all(r == best or _upright(q[best]) >= 2 * _upright(q[r]) for r in [0, *rots]) else 0


def turn_page(data, degrees, page=1):
    """The page turned by degrees (clockwise) — its /Rotate only: the picture itself is not written again. None when it cannot be."""
    try:
        _, out = run([('doc_open', {'path': 'in.pdf'}), ('page_rotate', {'doc': 1, 'degrees': int(degrees) % 360, 'pages': [page]}),
                      ('doc_save', {'doc': 1, 'path': 'out.pdf', 'full': True})], {'in.pdf': data}, read=('out.pdf',))
        return out.get('out.pdf')
    except (PdfCraftError, OSError):
        return None


_TURNS = {}


def photo_page(data, name='image'):
    """An image made a PDF page (image_to_pdf), and a photo (JPEG) taken sideways or upside down turned upright (upright_turn,
    where recognition is here) → (PDF bytes or None, the turn made: 0/90/180/270)."""
    pdf = image_to_pdf(data, name)
    if not pdf or data[:3] != b'\xff\xd8\xff':
        return pdf, 0
    import hashlib
    from . import imagefiles
    key = hashlib.sha256(data).hexdigest()                     # the wizard reads a photo, then the item takes it: one test
    if key not in _TURNS:
        if len(_TURNS) > 256:
            _TURNS.clear()
        _TURNS[key] = upright_turn(pdf, imagefiles.jpeg_size(data))
    turn = _TURNS[key]
    turned = turn_page(pdf, turn) if turn else None
    return (turned, turn) if turned else (pdf, 0)


def picture_size(data):
    """(width, height) in pixels of a PNG or a JPEG; None for anything else."""
    if data[:8] == b'\x89PNG\r\n\x1a\n' and len(data) >= 24:
        return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
    from . import imagefiles
    return imagefiles.jpeg_size(data)


def page_picture(data, page, picture):
    """Page `page` of a PDF made a picture — a page cleaned in the photo program: the picture laid on a page the size the page is
    shown at (its crop box, its /Rotate turned in), centred and as large as fits, and that page put in the old one's place
    (page_replace: its links, comments and bookmarks stay; the other pages are not touched). → the PDF, or None when it cannot be."""
    import io
    try:
        from pypdf import PdfReader
        pages = PdfReader(io.BytesIO(data)).pages
        if not 1 <= int(page) <= len(pages):
            return None
        pg = pages[int(page) - 1]
        box = pg.cropbox
        w, h = abs(float(box.width)), abs(float(box.height))
        if int(pg.get('/Rotate') or 0) % 180:
            w, h = h, w
    except Exception:                                          # noqa: BLE001 — a PDF pypdf cannot read: not changed
        return None
    px = picture_size(picture)
    if not px or not all(px) or w <= 0 or h <= 0:
        return None
    k = min(w / px[0], h / px[1])
    rw, rh = px[0] * k, px[1] * k
    x0, y0 = (w - rw) / 2, (h - rh) / 2
    ext = 'png' if picture[:4] == b'\x89PNG' else 'jpg'
    try:
        _, out = run([('doc_create', {'from': 'blank', 'width': w, 'height': h, 'pages': 1}),
                      ('page_add_image', {'doc': 1, 'page': 1, 'path': f'pic.{ext}', 'rect': [x0, y0, x0 + rw, y0 + rh]}),
                      ('doc_save', {'doc': 1, 'path': 'pic.pdf', 'full': True}),
                      ('doc_open', {'path': 'in.pdf'}),
                      ('page_replace', {'doc': 2, 'pages': [int(page)], 'path': 'pic.pdf', 'from_pages': [1]}),
                      ('doc_save', {'doc': 2, 'path': 'out.pdf', 'full': True})],
                     {'in.pdf': data, f'pic.{ext}': picture}, read=('out.pdf',))
        return out.get('out.pdf')
    except (PdfCraftError, OSError):
        return None


def image_to_pdf(data, name='image'):
    """An image (PNG, JPEG, TIFF, GIF, BMP, JPEG 2000) made into a PDF by PdfCraft: a page for each page of the image, in their order
    (a TIFF may hold several — a fax, a scanner's file). None when it cannot be."""
    if not available():
        return None
    from . import imagefiles
    ext = (name.rsplit('.', 1)[-1].lower() if '.' in name else 'png')[:5]

    def make(n):
        """doc_combine takes two or more inputs: the image twice, then its second copy off — pages n+1 … 2n, where the image has n
        (16/11/2026: «page 2» was taken off whatever n was; a three-page TIFF came out as five pages — 1, 3, 1, 2, 3).
        → (the image's pages as PdfCraft counts them, the PDF — None when n is 0: only counted)"""
        with Job() as j:
            j.put(f'in.{ext}', data)
            j.steps.append({'tool': 'doc_combine', 'args': {'paths': [f'in.{ext}', f'in.{ext}'], 'out': 'two.pdf', 'open': False}})
            opened = j.step('doc_open', path='two.pdf')
            if n:
                j.step('page_delete', doc=1, pages=list(range(n + 1, 2 * n + 1)))
                j.step('doc_save', doc=1, path='out.pdf', full=True)
            res = j.run()
            return int(first(res[opened])['pages']) // 2, (j.read('out.pdf') if n else None)

    n = imagefiles.tiff_pages(data) if imagefiles.image_format(data) == 'tiff' else 1
    try:
        try:
            had, pdf = make(n)
        except PdfCraftError:
            if n == 1:
                raise
            had, pdf = make(0)                               # fewer pages than its header promised (nothing there to take off): counted
        if had != n:                                         # PdfCraft found another number of pages than expected: made again with its own
            pdf = make(had)[1] if had else None
        return pdf
    except (PdfCraftError, OSError, KeyError, TypeError, ValueError):
        return None
