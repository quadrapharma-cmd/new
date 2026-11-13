"""Write docs/ctd/sources/MANIFEST.json: each official source text the rules come from, with its SHA-256, size and the day it was
taken (the day git first recorded it). Run after adding or replacing a source: python3 tools/sources_manifest.py"""
import hashlib, json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / 'docs' / 'ctd' / 'sources'


def taken(p):
    try:
        out = subprocess.run(['git', 'log', '--diff-filter=A', '--follow', '--format=%as', '--', str(p)], cwd=REPO,
                             capture_output=True, text=True, timeout=30).stdout.split()
        return out[-1] if out else None
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    rows = []
    for p in sorted(SRC.rglob('*')):
        if p.is_file() and p.name != 'MANIFEST.json' and not p.name.startswith('.'):
            rows.append({'file': p.relative_to(SRC).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                         'size': p.stat().st_size, 'taken': taken(p)})
    (SRC / 'MANIFEST.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(rows)} sources → {SRC / "MANIFEST.json"}')


if __name__ == '__main__':
    sys.exit(main())
