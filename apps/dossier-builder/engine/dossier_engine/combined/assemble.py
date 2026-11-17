"""Stage 5 — the CTD folder, every page checked against its source.

Each document of plan.json becomes its own PDF: its pages copied unchanged from the parts after the OCR, its title, one bookmark
with the title, the bookmarks pane open. The pages left out go together into one PDF «not for submission», and the Word files
received are kept beside it under the name their content calls for. Then every page is checked, as the hand-built dossier was:
  1. each document has the pages the plan gives it, in that order — each page's pictures compared, byte for byte, with the page
     of the combined file it came from (its copy before the text layer);
  2. the text layer did not change how a page looks: every page of each part drawn at 20 dpi beside the same page before the
     OCR (the share of pixels that differ by more than 48 of 255);
  3. how many pages of each document can be searched (30 characters or more).
Writes ctd/<folder>/… and assembled.json."""
import hashlib
import shutil
import subprocess

import pikepdf
from PIL import Image, ImageChops

from .common import NO_TEXT, Work, pdftext, say, tool

PRODUCER = "pikepdf (pages copied unchanged from the company's combined file; text layer by OCRmyPDF)"


class Pages:
    """The page of the combined file numbered n, from the part that holds it (after the OCR, or before it)."""

    def __init__(self, parts, which='pdf'):
        self.parts = [(p['from'], p['to'], pikepdf.open(p[which])) for p in parts]

    def __call__(self, n):
        for a, b, pdf in self.parts:
            if a <= n <= b:
                return pdf.pages[n - a]
        raise ValueError(f'الصفحة {n} في كتلة مكررة تُركت: لا تؤخذ')

    def close(self):
        for _, _, pdf in self.parts:
            pdf.close()


def write(path, pages, title, page_of):
    path.parent.mkdir(parents=True, exist_ok=True)
    pdf = pikepdf.new()
    for n in pages:
        pdf.pages.append(page_of(n))
    pdf.docinfo['/Title'] = title
    pdf.docinfo['/Producer'] = PRODUCER
    with pdf.open_outline() as ol:
        ol.root.append(pikepdf.OutlineItem(title, 0))
    pdf.Root.PageMode = pikepdf.Name.UseOutlines
    pdf.save(path)
    return path.stat().st_size


def images(pg):
    """The page's pictures, by their bytes (the text layer adds a form of its own: pictures inside forms are taken too)."""
    got = []

    def walk(res, depth=0):
        if res is None or depth > 4 or '/XObject' not in res:
            return
        for k in sorted(res.XObject.keys()):
            x = res.XObject[k]
            if x.get('/Subtype') == '/Image':
                got.append(hashlib.sha256(x.read_raw_bytes()).hexdigest()[:16])
            elif x.get('/Subtype') == '/Form':
                walk(x.get('/Resources'), depth + 1)
    walk(pg.obj.get('/Resources'))
    return sorted(got)


def look(part, tmp):
    """The worst share of a page's pixels changed by the text layer (> 48 of 255), drawn at 20 dpi."""
    worst = 0.0
    for tag, f in (('A', part['raw']), ('B', part['pdf'])):
        subprocess.run([tool('pdftoppm'), '-r', '20', '-gray', '-png', str(f), str(tmp / (part['name'] + tag))], check=True)
    A = sorted(tmp.glob(part['name'] + 'A-*.png'))
    B = sorted(tmp.glob(part['name'] + 'B-*.png'))
    n = part['to'] - part['from'] + 1
    assert len(A) == len(B) == n, (len(A), len(B), n)
    for x, y in zip(A, B):
        a, b = Image.open(x).convert('L'), Image.open(y).convert('L')
        if a.size != b.size:
            b = b.resize(a.size)
        h = ImageChops.difference(a, b).histogram()
        worst = max(worst, sum(h[48:]) / (a.size[0] * a.size[1]))
    for f in A + B:
        f.unlink()
    return worst


def run(work, check=True):
    w = work if isinstance(work, Work) else Work(work)
    plan = w.load('plan.json')
    parts = w.load('parts.json')
    files = w.load('read/files.json')
    dec = w.decisions()
    folder = dec.get('ctd_folder') or 'CTD'
    out = w.ctd / folder
    if out.exists():
        shutil.rmtree(out)
    page_of = Pages(parts)
    total = 0
    say(f'كتابة {len(plan["docs"])} مستندًا في {out}')
    for d in plan['docs']:
        d['bytes'] = write(out / d['path'], d['pages'], d['title'], page_of)
        total += d['bytes']
    kept = set()
    for p in parts:
        kept |= set(range(p['from'], p['to'] + 1))
    gone = sorted(r['page'] for r in plan['removed'] if r['page'] in kept)
    aside = out / 'Not for submission'
    if gone:
        write(aside / 'Pages left out (covers, separators, repeated tables of contents).pdf', gone,
              'Pages left out of the dossier – kept for reference', page_of)
    words = [f for f in files if f.get('kind') in ('rtf', 'doc', 'docx')]
    if words:
        (aside / 'Word files received').mkdir(parents=True, exist_ok=True)
        for f in words:
            shutil.copyfile(f['path'], aside / 'Word files received' / f['keep_as'])
    page_of.close()
    res = {'folder': str(out), 'docs': len(plan['docs']), 'bytes': total, 'left_out_pages': len(gone)}
    if check:
        say('مطابقة كل صفحة بأصلها')
        before = Pages(parts, 'raw')
        bad, checked, searchable, pages_in = [], 0, 0, 0
        for d in plan['docs']:
            pdf = pikepdf.open(out / d['path'])
            if len(pdf.pages) != len(d['pages']):
                bad.append({'doc': d['path'], 'what': 'pages', 'has': len(pdf.pages), 'should': len(d['pages'])})
                pdf.close()
                continue
            for i, n in enumerate(d['pages']):
                if images(pdf.pages[i]) != images(before(n)):
                    bad.append({'doc': d['path'], 'what': 'page', 'index': i + 1, 'source': n})
                checked += 1
            pdf.close()
            t = pdftext(out / d['path'])
            d['searchable'] = sum(1 for x in t[:len(d['pages'])] if len(x.strip()) >= NO_TEXT)
            d['no_text'] = [n for i, n in enumerate(d['pages']) if i >= len(t) or len(t[i].strip()) < NO_TEXT]
            searchable += d['searchable']
            pages_in += len(d['pages'])
        before.close()
        say('رسم الصفحات قبل طبقة النص وبعدها بدقة 20 نقطة في البوصة')
        tmp = w.tmp / 'look'
        tmp.mkdir(parents=True, exist_ok=True)
        worst = max(look(p, tmp) for p in parts) if parts else 0.0
        shutil.rmtree(tmp, ignore_errors=True)
        res.update({'pages_checked': checked, 'wrong': bad, 'worst_look_change': round(worst, 5),
                    'searchable': searchable, 'pages_in_docs': pages_in})
        say(f'المستندات {len(plan["docs"])} · الصفحات المطابقة لأصلها {checked - len(bad)} من {checked} · '
            f'أسوأ تغير في شكل صفحة {worst:.5f} · الصفحات القابلة للبحث {searchable} من {pages_in}')
    w.save('plan.json', plan)
    w.save('assembled.json', res)
    return res
