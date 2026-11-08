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
import argparse, base64, io, pathlib, re, shutil, zipfile

HERE = pathlib.Path(__file__).resolve().parent
APP = HERE.parent
REPO = APP.parents[1]
UI = APP / 'ui'
DIST = HERE / 'dist'
BUNDLE = ['apps/dossier-builder/engine/dossier_engine', 'apps/dossier-builder/rulepacks', 'apps/dossier-builder/web/pybridge.py',
          'docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v0', 'docs/ctd/ectd/EG-PROVISIONAL-PROFILE-v4-v0',
          'docs/ctd/sources/ectd/ICH_eCTD_v4.0_IG_v1.7_with_XSD.zip']
SKELETON = ('<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>')


def page(src, *, builder):
    html = src.read_text(encoding='utf-8')
    css = (UI / 'assets' / 'ds.css').read_text(encoding='utf-8')
    js = (UI / 'assets' / 'ds.js').read_text(encoding='utf-8')
    boot = (HERE / 'boot.js').read_text(encoding='utf-8')
    html = html.replace('<link rel="stylesheet" href="/assets/ds.css">', f'<style>\n{css}\n</style>')
    html = html.replace('<script src="/assets/ds.js"></script>',
                        f'<script>\n{js}\n</script>\n<script src="assets/pyodide/pyodide.js"></script>\n<script>\n{boot}\n</script>')
    if builder:
        html = html.replace("'/suite/'", "'suite.html'").replace('<title>Dossier Builder — منشئ ملفات التسجيل</title>', '<title>منشئ ملفات التسجيل</title>')
    else:
        html = html.replace('href="/"', 'href="index.html"')
    head = re.search(r'<head>(.*?)</head>', html, re.S).group(1)
    body = re.search(r'<body>(.*?)</body>', html, re.S).group(1)
    head = re.sub(r'<meta charset="utf-8">\s*|<meta name="viewport"[^>]*>\s*', '', head)
    content = head.strip() + '\n' + body.strip() + '\n'
    return content, SKELETON + content + '</body></html>\n'


BINARY = ('.wasm', '.zip', '.whl')


def put(dst, data):
    """Write a dist file; binaries as base64 text under <name>.b64.txt."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.suffix in BINARY:
        dst.with_name(dst.name + '.b64.txt').write_text(base64.b64encode(data).decode('ascii'))
    else:
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
    for src, sub in ((pathlib.Path(a.pyodide), 'pyodide'), (pathlib.Path(a.wheels), 'wheels')):
        for f in sorted(src.iterdir()):
            if f.is_file():
                put(DIST / 'assets' / sub / f.name, f.read_bytes())
    total = sum(f.stat().st_size for f in DIST.rglob('*') if f.is_file())
    print(f'dist: {DIST}\nengine.zip {n/1e6:.1f} MB · total {total/1e6:.1f} MB · files {sum(1 for f in DIST.rglob("*") if f.is_file())}')


if __name__ == '__main__':
    main()
