#!/usr/bin/env python3
"""Build the browser edition (a claude.ai artifact: open from a link, nothing to install).

    python3 apps/dossier-builder/web/build.py [--pyodide DIR] [--wheels DIR]

Output: apps/dossier-builder/web/dist/
  index.html        the builder page WITHOUT the document skeleton (the Artifact tool adds it)
  index.local.html  the same page as a full document, for local testing (python3 -m http.server --directory dist)
  suite.html        the product-file page (a full document; published as a second page)
  assets/pyodide/   the Pyodide runtime + wasm wheels (see vendor.sh)
  assets/wheels/    the pure-Python wheels (fastapi, starlette, pypdf, python-docx, …)
  assets/engine.zip the engine, rule packs, EG profiles and the ICH XSD, unpacked to /app in the browser
Binary files (.wasm .zip .whl) are written as base64 text (<name>.b64.txt): the artifact host serves text, not
archives, and boot.js decodes them when Pyodide fetches them.
"""
import argparse, base64, io, json, pathlib, re, shutil, zipfile

HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parent
REPO = APP.parents[1]
UI = APP / 'ui'
DIST = HERE / 'dist'
BUNDLE = ['apps/dossier-builder/engine/dossier_engine', 'apps/dossier-builder/rulepacks', 'apps/dossier-builder/web/pybridge.py',
          'docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v0', 'docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v4-v0', 'docs/ctd/ectd/EU-M1-3.1.1-PROFILE',
          'docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip']
SKELETON = ('<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>')


def page(src, *, builder):
    html = src.read_text(encoding='utf-8')
    css = (UI / 'assets' / 'ds.css').read_text(encoding='utf-8')
    js = (UI / 'assets' / 'ds.js').read_text(encoding='utf-8')
    boot = SHARED() + (HERE / 'boot.js').read_text(encoding='utf-8')      # large files as Blobs, the runtime kept on the device: used by the page and by the worker
    html = html.replace('<link rel="stylesheet" href="/assets/ds.css">', f'<style>\n{css}\n</style>')
    html = html.replace('<script src="/assets/ds.js"></script>',
                        f'<script>\n{js}\n</script>\n<script src="assets/pyodide/pyodide.js"></script>\n<script>\n{boot}\n</script>')
    html = html.replace('<script src="/assets/rar.js"></script>', '<script>\n' + (UI / 'assets' / 'rar.js').read_text(encoding='utf-8') + '\n</script>')      # the page's own RAR reader
    html = html.replace('<script src="/assets/archive.js"></script>', '<script>\n' + (UI / 'assets' / 'archive.js').read_text(encoding='utf-8') + '\n</script>')
    if builder:
        html = html.replace("'/suite/'", "'suite.html'").replace('<title>Dossier Builder — منشئ ملفات التسجيل</title>', '<title>منشئ ملفات التسجيل</title>')
    else:
        html = html.replace('href="/"', 'href="index.html"')
    head = re.search(r'<head>(.*?)</head>', html, re.S).group(1)
    body = re.search(r'<body>(.*?)</body>', html, re.S).group(1)
    head = re.sub(r'<meta charset="utf-8">\s*|<meta name="viewport"[^>]*>\s*', '', head)
    head = re.sub(r'<link href="(https://fonts\.googleapis\.com/[^"]+)" rel="stylesheet">',
                  r'<link href="\1" rel="stylesheet" media="print" onload="this.media=\'all\'">', head)      # the fonts load beside the page, never before it
    head = re.sub(r'(</title>)', lambda m: m.group(1) + '\n' + FIRST_SCREEN, head, count=1)
    content = head.strip() + '\n' + body.strip() + '\n'
    return content, SKELETON + content + '</body></html>\n'


# the first screen, in the page's first bytes: shown before anything loads; boot.js replaces it with its progress screen
FIRST_SCREEN = ('<div id="boot0" role="status" style="position:fixed;inset:0;z-index:999;display:grid;place-items:center;background:#070B12;'
                'color:#E9EFF7;font:15px/1.7 system-ui,-apple-system,Segoe UI,sans-serif;text-align:center;padding:0 16px">'
                '<div style="display:flex;flex-direction:column;gap:10px;align-items:center;max-width:440px">'
                '<div style="width:46px;height:46px;border-radius:13px;background:linear-gradient(135deg,#22D3EE,#A78BFA);display:grid;place-items:center;'
                'font-family:ui-monospace,monospace;font-weight:600;color:#04161B">DB</div>'
                '<b dir="rtl">بيفتح منشئ ملفات التسجيل…</b>'
                '<span dir="rtl" style="font-size:13px;color:#8C9BB0">أول مرة بينزّل البرنامج نفسه على جهازك (دقيقة تقريبًا على خط عادي)؛ بعدها بيفتح في ثواني.</span>'
                '<span dir="ltr" style="font-size:12.5px;color:#8C9BB0">Opening Dossier Builder… The first time, the program itself is downloaded to this device '
                '(about a minute on an ordinary line); after that it opens in seconds.</span></div></div>')


MARK = '/*DB_MANIFEST*/{}'


def SHARED():
    """What the page's boot script and the engine's worker both start with: the large-file storage, the on-device cache of the
    runtime's files and the list of those files (filled in at the end of the build, when they all exist)."""
    return ((HERE / 'bigfs.js').read_text(encoding='utf-8') + '\n' + (HERE / 'assets.js').read_text(encoding='utf-8')
            + '\nconst DB_MANIFEST = ' + MARK + ';\n')


def manifest(dist):
    """path → [bytes on the wire, tag, needed at start, bytes once decoded] for every binary file of the runtime, written into
    the pages and the worker: what a browser already holds with the same tag is not fetched again."""
    import base64
    import hashlib
    m = {}
    for f in sorted((dist / 'assets').rglob('*.b64.txt')):
        rel = f.relative_to(dist).as_posix()[:-len('.b64.txt')]
        if not rel.endswith(BINARY):
            continue
        data = f.read_bytes()
        start = rel.startswith(('assets/pyodide/', 'assets/wheels/')) or rel == 'assets/engine.zip'
        m[rel] = [len(data), hashlib.sha256(data).hexdigest()[:16], 1 if start else 0, len(base64.b64decode(data))]
    text = json.dumps(m, separators=(',', ':'))
    for f in (dist / 'index.html', dist / 'index.local.html', dist / 'suite.html', dist / 'assets' / 'engine.worker.js'):
        src = f.read_text(encoding='utf-8')
        assert src.count(MARK) == 1, (f, src.count(MARK))
        f.write_text(src.replace(MARK, text), encoding='utf-8')
    return m


BINARY = ('.wasm', '.zip', '.whl')


CTRL = re.compile(rb'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def put(dst, data):
    """Write a dist file; binaries as base64 text under <name>.b64.txt. Raw control bytes inside a script's string
    literals (pdf.js carries ESC and 0x03 as bytes) become the equivalent hex escapes: the artifact host refuses them."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix in BINARY:
        dst.with_name(dst.name + '.b64.txt').write_text(base64.b64encode(data).decode('ascii'))
    else:
        if dst.suffix in ('.js', '.mjs'):
            data = CTRL.sub(lambda m: b'\\x%02x' % m.group(0)[0], data)
        dst.write_bytes(data)


def engine_zip(out):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in BUNDLE:
            p = REPO / rel
            files = [p] if p.is_file() else sorted(x for x in p.rglob('*') if x.is_file() and '__pycache__' not in x.parts)
            for f in files:
                z.write(f, str(f.relative_to(REPO)))
    put(out, buf.getvalue())
    return len(buf.getvalue())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pyodide', default=str(HERE / 'vendor' / 'pyodide'))
    ap.add_argument('--wheels', default=str(HERE / 'vendor' / 'wheels'))
    a = ap.parse_args()
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / 'assets').mkdir(parents=True)
    content, full = page(UI / 'index.html', builder=True)
    (DIST / 'index.html').write_text(content, encoding='utf-8')
    (DIST / 'index.local.html').write_text(full, encoding='utf-8')
    (DIST / 'suite.html').write_text(page(UI / 'suite' / 'index.html', builder=False)[1], encoding='utf-8')
    n = engine_zip(DIST / 'assets' / 'engine.zip')
    put(DIST / 'assets' / 'engine.worker.js', SHARED().encode('utf-8') + (HERE / 'engine.worker.js').read_bytes())      # the engine's own thread (boot.js starts it)
    for src, sub in ((pathlib.Path(a.pyodide), 'pyodide'), (pathlib.Path(a.wheels), 'wheels')):
        if not src.is_dir():
            print(f'(no {sub} assets at {src}; skipped)')
            continue
        for f in sorted(src.iterdir()):
            if f.is_file():
                put(DIST / 'assets' / sub / f.name, f.read_bytes())
    manifest(DIST)
    total = sum(f.stat().st_size for f in DIST.rglob('*') if f.is_file())
    print(f'dist: {DIST}\nengine.zip {n/1e6:.1f} MB · total {total/1e6:.1f} MB · files {sum(1 for f in DIST.rglob("*") if f.is_file())}')


if __name__ == '__main__':
    main()
