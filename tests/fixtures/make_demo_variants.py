"""Variants of the demo build that imitate viewers which cannot run the app (used by tests/demo/legacy lite/sanit/splash suites):
  csp_block.html  scripts blocked by a Content-Security-Policy (script-src 'none'), as some in-app viewers do
  worst.html      the same + no animations or transitions
  sanitized.html  every <script> and every on…= attribute removed, as e-mail / file previews do
Usage: python3 tests/fixtures/make_demo_variants.py [demo.html] [out dir]   (defaults: $DEMO_FILE or web/dist/drugbox.html, $DEMO_VARIANTS or /tmp)"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('DEMO_FILE', ROOT + '/web/dist/drugbox.html')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('DEMO_VARIANTS', '/tmp')
os.makedirs(OUT, exist_ok=True)
H = open(SRC, encoding='utf-8').read()
csp = H.replace('<head>', '<head><meta http-equiv="Content-Security-Policy" content="script-src \'none\'">', 1)
worst = csp.replace('</head>', '<style>*,*::before,*::after{animation:none!important;transition:none!important}</style></head>', 1)
san = re.sub(r'\son[a-z]+="[^"]*"|\son[a-z]+=\'[^\']*\'', '', re.sub(r'<script\b[^>]*>[\s\S]*?</script>', '', H))
for name, text in (('csp_block.html', csp), ('worst.html', worst), ('sanitized.html', san)):
    open(os.path.join(OUT, name), 'w', encoding='utf-8').write(text)
print('demo variants in', OUT, 'from', SRC)
