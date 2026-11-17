"""Stage 3 — the kept pages made searchable.

Each run of kept pages becomes a part (parts/u1.pdf, u2.pdf …: the pages copied unchanged with pikepdf). OCRmyPDF reads every
page that has no text of its own (--mode skip: a page with text is left as it is); the pages that still have fewer than 30
characters are read again with --mode redo (their pictures kept, a new text layer laid over them). The language is English,
with Arabic added when the received text has Arabic on at least one page in a hundred. The pass-1 file is removed once the
second pass is written.

Writes parts.json and read/ocr.txt (the text of every page after the OCR, by the global page number; '' for pages left out)."""
import os
import re
import shutil
import subprocess

import pikepdf

from .common import NO_TEXT, Work, pdftext, say, tool

ARABIC = re.compile(r'[؀-ۿ]')


def language(w):
    text = w.pages_text()
    with_ar = sum(1 for t in text if ARABIC.search(t))
    return 'eng+ara' if text and with_ar * 100 >= len(text) else 'eng'


def ocrmypdf(args, w, log):
    env = dict(os.environ, TMPDIR=str(w.tmp))
    with open(log, 'w') as f:
        r = subprocess.run([tool('ocrmypdf')] + [str(a) for a in args], stdout=f, stderr=subprocess.STDOUT, env=env)
    return r.returncode


def clean_tmp(w):
    """OCRmyPDF's temporary folders of an earlier run that was stopped (they hold every page drawn: gigabytes)."""
    if w.tmp.exists():
        for d in w.tmp.iterdir():
            if d.is_dir() and d.name.startswith('ocrmypdf.io.'):
                shutil.rmtree(d, ignore_errors=True)


def free_space(path):
    return shutil.disk_usage(path).free


def run(work, jobs=4, lang=None):
    w = work if isinstance(work, Work) else Work(work)
    clean_tmp(w)
    files = w.load('read/files.json')
    pages = w.load('read/pages.json')
    rep = w.load('repeats.json')
    lang = lang or language(w)
    file_of = {p['n']: files[p['file']] for p in pages}
    parts, total = [], len(pages)
    for i, (a, b) in enumerate(rep['kept'], 1):
        name = f'u{i}'
        raw, p1, p2 = w.parts / f'{name}.pdf', w.parts / f'{name}.ocr.pdf', w.parts / f'{name}.ocr2.pdf'
        f = file_of[a]
        if not p2.exists():
            say(f'الجزء {name}: الصفحات {a}–{b}')
            src = pikepdf.open(f['path'])
            out = pikepdf.new()
            off = f['from']
            out.pages.extend(src.pages[a - off:b - off + 1])
            out.save(raw)
            src.close()
            need = raw.stat().st_size * 8
            if free_space(w.root) < need:
                say(f'تنبيه: المساحة الحرة {free_space(w.root) // 10**6} ميجابايت، والتعرف الضوئي على هذا الجزء قد يحتاج نحو {need // 10**6}')
            say(f'التعرف الضوئي، المرور الأول ({b - a + 1} صفحة، اللغة {lang})')
            code = ocrmypdf(['--mode', 'skip', '-l', lang, '--optimize', '0', '--output-type', 'pdf', '-j', jobs,
                             '--tesseract-timeout', '300', raw, p1], w, w.parts / f'{name}.ocr.log')
            if code != 0:
                raise SystemExit(f'توقف التعرف الضوئي على الجزء {name} (الرمز {code}): انظر {w.parts / (name + ".ocr.log")}')
            t1 = pdftext(p1)
            again = [i + 1 for i, t in enumerate(t1[:b - a + 1]) if len(t.strip()) < NO_TEXT]
            if again:
                say(f'المرور الثاني على {len(again)} صفحة ما زالت بلا نص')
                code = ocrmypdf(['--mode', 'redo', '--pages', ','.join(map(str, again)), '-l', lang, '--optimize', '0',
                                 '--output-type', 'pdf', '-j', jobs, p1, p2], w, w.parts / f'{name}.redo.log')
                if code != 0:
                    raise SystemExit(f'توقف المرور الثاني على الجزء {name} (الرمز {code})')
                p1.unlink()
            else:
                p1.replace(p2)
            clean_tmp(w)
        t2 = pdftext(p2)
        still = [a + i for i, t in enumerate(t2[:b - a + 1]) if len(t.strip()) < NO_TEXT]
        parts.append({'name': name, 'from': a, 'to': b, 'raw': str(raw), 'pdf': str(p2), 'lang': lang, 'still_without_text': still})
    text = [''] * total
    for part in parts:
        t = pdftext(part['pdf'])
        for i in range(part['to'] - part['from'] + 1):
            text[part['from'] - 1 + i] = t[i] if i < len(t) else ''
    (w.read / 'ocr.txt').write_text('\f'.join(text), encoding='utf-8')
    w.save('parts.json', parts)
    shutil.rmtree(w.tmp, ignore_errors=True)
    w.tmp.mkdir(exist_ok=True)
    say('بقيت بلا نص بعد التعرف الضوئي: ' + str(sum(len(p['still_without_text']) for p in parts)) + ' صفحة')
    return parts
