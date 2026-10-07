"""Parity check: the app's interface must be byte-identical to the approved demo.
Usage: python3 tools/parity_check.py <reference-demo.html> [built.html] [--ignore-snapshot]
The whole file is compared, including the lite (no-JS) snapshot: web/src/snapshot.py renders it with a fixed date,
a seeded Math.random and no network, so two builds of the same sources are identical.
--ignore-snapshot leaves the lite snapshot out (both files must then contain its start and end markers)."""
import sys, os, hashlib
MIN_BYTES = 500_000   # a real demo build is several MB: an empty or truncated file is an error, never "OK"
START, END = '<div id="dxStaticWrap"', '<!--/dxStaticWrap-->'
args = [a for a in sys.argv[1:] if not a.startswith('--')]
ignore_snapshot = '--ignore-snapshot' in sys.argv[1:]
if not args: raise SystemExit(__doc__)
def fail(msg): print('PARITY FAILED — ' + msg); sys.exit(1)
def load(path):
    if not os.path.isfile(path): fail('file not found: %s' % path)
    s = open(path, encoding='utf-8').read()
    if len(s.encode()) < MIN_BYTES: fail('%s is only %d bytes — not a complete build' % (path, len(s.encode())))
    if '</html>' not in s[-4096:]: fail('%s does not end with </html> — truncated?' % path)
    return s
def strip(s, path):
    i = s.find(START); j = s.find(END, i + 1) if i >= 0 else -1
    if i < 0 or j < 0: fail('%s has no complete lite snapshot (markers missing), cannot use --ignore-snapshot' % path)
    return s[:i] + s[j:]
ref_path, new_path = args[0], args[1] if len(args) > 1 else 'web/dist/drugbox.html'
ref, new = load(ref_path), load(new_path)
if ignore_snapshot: ref, new = strip(ref, ref_path), strip(new, new_path)
if ref == new:
    print('PARITY OK — interface identical to the demo%s (sha256 %s)' % (' (lite snapshot not compared)' if ignore_snapshot else '', hashlib.sha256(new.encode()).hexdigest()[:16])); sys.exit(0)
n = min(len(ref), len(new)); i = next((k for k in range(n) if ref[k] != new[k]), n)
where = ''
a, b = new.find(START), new.find(END)
if 0 <= a <= i < b: where = '\n  (the difference is inside the lite no-JS snapshot — rebuild, or compare with --ignore-snapshot to check the app itself)'
print('PARITY FAILED at char %d\n  demo: %r\n  new : %r%s' % (i, ref[max(0, i - 60):i + 80], new[max(0, i - 60):i + 80], where)); sys.exit(1)
