"""THIRD-PARTY-LICENSES.txt for the PdfCraft program the Dossier Builder carries: every crate compiled into pdfcraft-cli (built without
its MCP server), with its version, licence, source and its own licence and notice files, read from the build's Cargo metadata.
    python3 licenses.py <pdfcraft source> <output folder> [target]"""
import json, re, subprocess, sys
from pathlib import Path

src, out = Path(sys.argv[1]), Path(sys.argv[2])
target = ['--target', sys.argv[3]] if len(sys.argv) > 3 else []          # e.g. wasm32-wasip1: the browser edition's build
tree = subprocess.run(['cargo', 'tree', '--locked', '-p', 'pdfcraft-cli', '--no-default-features', '-e', 'normal', '--prefix', 'none',
                       '--format', '{p}|{l}', *target], cwd=src, capture_output=True, text=True, check=True).stdout
want = set()
for line in tree.splitlines():
    p = line.split('|')[0].replace('(*)', '').strip()
    m = re.match(r'(\S+) v(\S+)', p)
    if m:
        want.add((m[1], m[2]))
meta = json.loads(subprocess.run(['cargo', 'metadata', '--locked', '--format-version', '1'], cwd=src, capture_output=True, text=True,
                                 check=True).stdout)
members = set(meta.get('workspace_members') or [])
LIC = re.compile(r'^(licen[cs]e|copying|notice|copyright|authors|unlicense)', re.I)
parts = ['Third-party licences of the PdfCraft program carried by the Dossier Builder (pdfcraft-cli, built without its MCP server).',
         'PdfCraft itself: LICENSE-MIT, LICENSE-APACHE, NOTICE and ATTRIBUTION.md beside this file.', '']
n = 0
for pkg in sorted(meta['packages'], key=lambda x: (x['name'], x['version'])):
    if (pkg['name'], pkg['version']) not in want or pkg['id'] in members:
        continue
    n += 1
    d = Path(pkg['manifest_path']).parent
    parts += ['=' * 100, f"{pkg['name']} {pkg['version']} — {pkg.get('license') or pkg.get('license_file') or 'see below'}",
              f"source: {pkg.get('repository') or pkg.get('homepage') or 'crates.io'}"]
    if pkg.get('authors'):
        parts.append('authors: ' + ', '.join(pkg['authors']))
    for f in sorted(x for x in d.iterdir() if x.is_file() and LIC.match(x.name)):
        try:
            parts += ['-' * 40 + f' {f.name}', f.read_text(encoding='utf-8', errors='replace').strip()]
        except OSError:
            pass
    parts.append('')
out.mkdir(parents=True, exist_ok=True)
(out / 'THIRD-PARTY-LICENSES.txt').write_text('\n'.join(parts) + '\n', encoding='utf-8')
print(f'{n} crates → {out / "THIRD-PARTY-LICENSES.txt"}')
