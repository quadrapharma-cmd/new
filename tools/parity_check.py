"""Parity check: the app's interface must be byte-identical to the approved demo.
Usage: python3 tools/parity_check.py <reference-demo.html> [built.html]
The lite snapshot (captured at build time, so it contains the build date) is excluded from the comparison."""
import sys, hashlib
def strip(s):
    i = s.find('<div id="dxStaticWrap"')
    if i < 0: return s
    j = s.find('<!--/dxStaticWrap-->', i); j = j if j >= 0 else s.find('<script', i)
    return s[:i] + s[j:]
ref = strip(open(sys.argv[1], encoding='utf-8').read())
new = strip(open(sys.argv[2] if len(sys.argv) > 2 else 'web/dist/drugbox.html', encoding='utf-8').read())
if ref == new:
    print('PARITY OK — interface identical to the demo (sha256 %s)' % hashlib.sha256(new.encode()).hexdigest()[:16]); sys.exit(0)
i = next(k for k in range(min(len(ref), len(new))) if ref[k] != new[k]) if min(len(ref), len(new)) else 0
print('PARITY FAILED at char %d\n  demo: %r\n  new : %r' % (i, ref[i-60:i+80], new[i-60:i+80])); sys.exit(1)
