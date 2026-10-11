#!/usr/bin/env python3
"""Self-test of the dead-end crawler: crawls tools/qa/fixtures/deadend_fixture.html (a tiny page with one dead end of each
kind, built like the demo) and checks that every planted dead end is reported and that the working controls are not.
Prints N / N and exits non-zero on a miss.   python3 tools/qa/selftest.py [--keep DIR]"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    out = sys.argv[sys.argv.index('--keep') + 1] if '--keep' in sys.argv else tempfile.mkdtemp(prefix='deadend-selftest-')
    allow = os.path.join(out, 'allow-empty.json')
    os.makedirs(out, exist_ok=True)
    json.dump({'allow': []}, open(allow, 'w'))
    p = subprocess.run([sys.executable, os.path.join(HERE, 'deadend_crawler.py'), '--target', os.path.join(HERE, 'fixtures', 'deadend_fixture.html'),
                        '--langs', 'en', '--widths', '1440', '--workers', '2', '--out', out, '--allow', allow],
                       capture_output=True, text=True, timeout=900)
    try:
        d = json.load(open(os.path.join(out, 'crawl.json'), encoding='utf-8'))
    except Exception:
        print(p.stdout[-2000:], p.stderr[-2000:]); print('0 / 1 — the crawler did not write its report'); sys.exit(1)
    F = d['findings']
    R = [r for r in d['records'] if r['cfgname'] == 'en-1440']

    def kind_of(text, depth=1):
        return [r['kind'] for r in R if r['text'].startswith(text) and r['depth'] == depth]

    def finding(page, kind, contains=''):
        return any(f['page'] == page and f['kind'] == kind and contains in f['detail'] for f in F)
    checks = [
        ('a button that does nothing → no_effect', 'no_effect' in kind_of('Does nothing')),
        ('a button that only shows a toast → toast_only', 'toast_only' in kind_of('Only a toast')),
        ('"coming soon" → placeholder_toast', 'placeholder_toast' in kind_of('Export')),
        ('href="#p-need" → placeholder_href', finding('home', 'placeholder_href')),
        ('a real dialog (with fields) is fine', kind_of('Request a quote') == ['dialog']),
        ('a confirmation dialog is recognised', kind_of('Edit settings') == ['dialog_confirm']),
        ('"Save" that only closes its dialog → confirm_no_effect', 'confirm_no_effect' in kind_of('Save', 2)),
        ('"Send request" in the dialog changes the page (fine)', kind_of('Send request', 2) == ['changed']),
        ('a button that changes the page is fine', kind_of('Refresh') == ['changed']),
        ('group cards open a header-only detail → dialog_thin', finding('groups', 'dialog_thin')),
        ('only the first 2 of 6 cards open their own group → family_wrong_detail',
         finding('groups', 'family_wrong_detail', 'only the first 2 of 6 cards open their own item')),
        ('navigation found both pages', {r['view'].split('/')[0] for r in R} >= {'home', 'groups'}),
        ('no JavaScript error', not any(f['kind'] == 'js_error' for f in F)),
        ('the run fails (exit 1) because of the dead ends', p.returncode == 1),
    ]
    for name, ok in checks:
        print(('PASS ' if ok else 'FAIL ') + name)
    n = sum(ok for _, ok in checks)
    print('%d / %d  (report: %s)' % (n, len(checks), os.path.join(out, 'crawl.md')))
    sys.exit(0 if n == len(checks) else 1)


if __name__ == '__main__':
    main()
