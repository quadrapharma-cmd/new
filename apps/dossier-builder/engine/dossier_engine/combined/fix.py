"""Stage 7 — the corrections the dossier itself can make, as the dossier's decisions file lists them (dossier.json):
  · fixes: a phrase corrected inside a PDF page by removing characters only («1.25 mcg» → «1.25 mg», «P.2.1» → «P.1»), every
    other glyph and picture of the page untouched — proved by drawing the page before and after (the share of changed pixels
    and where they are);
  · pi: the product information written again from its corrected text (pi content: blocks of title, heading, sub-heading,
    paragraph, bullet, two-column rows) — English as Word and PDF (LibreOffice), a translation (Arabic) checked block by block
    against its source (same blocks in the same order, the same numbers in every block, the composition values identical) and
    written as Word (right to left, the Latin and the numbers kept left to right) and as PDF (Chromium, the fonts embedded).
Writes fixed/…, pi/… and fixed.json: {docs: {ctd path: {pdf, note, edits, changed}}, pi: [{type, lang, title, pdf, docx}]}."""
import json
import re
import subprocess
from pathlib import Path

import pikepdf
from PIL import Image, ImageChops

from .common import Work, say, tool
from .pdfedit import edit_page

AR = re.compile('[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
ISLAND = re.compile(r"(?:[≤≥<>±~+]\s?|[(\[])?[A-Za-z0-9µ°½][A-Za-z0-9µ°½.,:\/\-–+%'’&_=×≤≥<>±~()\[\]™ ]*[A-Za-z0-9µ°½%™+)\]]|[A-Za-z0-9µ°½]")
LRM, ZWSP = '\u200e', '\u200b'


# ------------------------------------------------------------------ corrections inside a PDF
def changed_pixels(a, b, page, w):
    """The page drawn at 100 dpi before and after: the share of pixels changed by more than 48 of 255, and their box."""
    tmp = w.tmp / 'fixlook'
    tmp.mkdir(parents=True, exist_ok=True)
    for f, tag in ((a, 'A'), (b, 'B')):
        subprocess.run([tool('pdftoppm'), '-r', '100', '-gray', '-png', '-f', str(page), '-l', str(page), str(f), str(tmp / tag)], check=True)
    A = sorted(tmp.glob('A*.png'))[0]
    B = sorted(tmp.glob('B*.png'))[0]
    ia, ib = Image.open(A).convert('L'), Image.open(B).convert('L')
    diff = ImageChops.difference(ia, ib).point(lambda v: 255 if v > 48 else 0)
    share = diff.histogram()[255] / (ia.size[0] * ia.size[1])
    box = diff.getbbox()
    A.unlink()
    B.unlink()
    return round(share, 5), box


def fix_pdfs(w, ctd_root, fixes):
    out = {}
    for f in fixes:
        src = ctd_root / f['doc']
        pdf = pikepdf.open(src)
        done = edit_page(pdf, int(f['page']) - 1, [tuple(e) for e in f['edits']])
        dst = w.fixed / (Path(f['doc']).stem + '.fixed.pdf')
        dst.parent.mkdir(parents=True, exist_ok=True)
        pdf.save(dst)
        pdf.close()
        share, box = changed_pixels(src, dst, int(f['page']), w)
        out[f['doc']] = {'pdf': str(dst), 'note': f.get('note', ''), 'edits': done, 'page': int(f['page']),
                         'changed_pixels': share, 'box': box}
        say(f"تصحيح في {Path(f['doc']).name}، الصفحة {f['page']}: " + '؛ '.join(f'«{a}» ← «{b}»' for a, b in done)
            + f' · البكسلات المتغيرة {share}')
    return out


# ------------------------------------------------------------------ the product information
def kind(b):
    return next(iter(b))


def text_of(b):
    return ' '.join(' '.join(r) for r in b['rows']) if 'rows' in b else b[kind(b)]


def numbers(s):
    return sorted(n.replace(',', '') for n in re.findall(r'\d+(?:[.,]\d+)*', s))


def check_translation(src, tr):
    """Same blocks in the same order and of the same kind, the same numbers in every block, the composition values identical."""
    bad = []
    if len(src) != len(tr):
        return [f'عدد الكتل {len(src)} في الأصل و{len(tr)} في الترجمة']
    for i, (a, b) in enumerate(zip(src, tr)):
        if kind(a) != kind(b):
            bad.append(f'الكتلة {i}: نوعها {kind(a)} في الأصل و{kind(b)} في الترجمة')
        if numbers(text_of(a)) != numbers(text_of(b)):
            bad.append(f'الكتلة {i}: الأرقام {" ".join(numbers(text_of(a)))} | {" ".join(numbers(text_of(b)))}')
        if 'rows' in a and any(r[1] != b['rows'][j][1] for j, r in enumerate(a['rows'])):
            bad.append(f'الكتلة {i}: قيم التركيب مختلفة')
    return bad


def pieces(t):
    """Right-to-left text cut into its left-to-right stretches (numbers, units, Latin names) — the brackets kept balanced."""
    if not AR.search(t):
        return [(t, True)]
    out, last = [], 0
    cnt = str.count
    pos = 0
    while True:
        m = ISLAND.search(t, pos)
        if not m:
            break
        s, at = m.group(0), m.start()
        if (s[0] == '(' and cnt(s, '(') > cnt(s, ')')) or (s[0] == '[' and cnt(s, '[') > cnt(s, ']')):
            s, at = s[1:], at + 1
        while (s.endswith(')') and cnt(s, '(') < cnt(s, ')')) or (s.endswith(']') and cnt(s, '[') < cnt(s, ']')):
            s = s[:-1]
        s = re.sub(r'[\s.,:\-–(\[]+$', '', s)
        if not s:
            pos = m.end()
            continue
        out.append((t[last:at], False))
        out.append((s, True))
        last = at + len(s)
        pos = last
    out.append((t[last:], False))
    return [(x, ltr) for x, ltr in out if x]


def keep(s):
    s = re.sub(r'([≤≥<>±~]) ', '\\1\u00a0', s)
    s = re.sub(r'(\d) (mg|mcg|ml|Lf|IU|OU|%)', '\\1\u00a0\\2', s)
    return re.sub(r'(\d)–(\d)', '\\1–\u2060\\2', s)


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def html_rtl(blocks, title):
    def h(t):
        if not AR.search(t):
            return f'<span dir="ltr">{esc(t)}</span>'
        out = ''
        for x, ltr in pieces(t):
            if ltr:
                nw = ' class="nw"' if len(x) <= 30 and ' ' not in x else ''
                out += f'<span dir="ltr"{nw}>{esc(keep(x))}</span>'
            else:
                out += esc(x)
        return out
    body = ''
    for b in blocks:
        if 't' in b:
            body += f'<h1>{h(b["t"])}</h1>'
        elif 'h' in b:
            body += f'<h2>{h(b["h"])}</h2>'
        elif 'b' in b:
            body += f'<ul><li>{h(b["b"])}</li></ul>'
        elif 'p' in b:
            cls = '' if AR.search(b['p']) else ' class="ltr"'
            body += f'<p{cls}>{h(b["p"])}</p>'
        elif 'rows' in b:
            body += '<table>' + ''.join(f'<tr><td>{h(r[0])}</td><td class="v">{h(r[1])}</td></tr>' for r in b['rows']) + '</table>'
    return f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>{esc(title)}</title><style>
@page {{ size: A4; margin: 20mm 22mm 18mm 22mm; }}
body {{ font-family: "Liberation Sans", "Noto Naskh Arabic", sans-serif; font-size: 11pt; line-height: 1.65; color: #111; margin: 0; }}
h1 {{ font-size: 14pt; text-align: center; margin: 0 0 6pt; }}
h2 {{ font-size: 11.5pt; margin: 12pt 0 4pt; break-after: avoid; }}
p {{ margin: 0 0 5pt; text-align: justify; }}
p.ltr {{ direction: ltr; text-align: right; }}
ul {{ margin: 0 0 3pt; padding: 0 18pt 0 0; }}
table {{ border-collapse: collapse; margin: 2pt 0 8pt; width: 100%; }}
td {{ padding: 1pt 4pt; vertical-align: top; }}
td.v {{ width: 35%; }}
.nw {{ white-space: nowrap; }}
</style></head><body>{body}</body></html>'''


def print_html(src, dest, footer_rtl=True):
    from playwright.sync_api import sync_playwright
    footer = ('<div style="font-size:7.5pt;color:#777;width:100%;text-align:center;font-family:\'Noto Naskh Arabic\';direction:rtl">'
              'صفحة <span class="pageNumber"></span> من <span class="totalPages"></span></div>')
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        page.goto('file://' + str(src), wait_until='load')
        page.evaluate('() => document.fonts.ready')
        page.pdf(path=str(dest), format='A4', print_background=True, prefer_css_page_size=True, display_header_footer=True,
                 header_template='<div></div>', footer_template=footer)
        b.close()


def docx_doc(font, size_half_points, rtl=False):
    from docx import Document
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Twips
    d = Document()
    sec = d.sections[0]
    sec.page_width, sec.page_height = Twips(11906), Twips(16838)
    sec.top_margin = sec.bottom_margin = Twips(1300)
    sec.left_margin = sec.right_margin = Twips(1440)
    sec.header_distance = sec.footer_distance = Twips(600)
    styles = d.styles.element
    defaults = styles.find(qn('w:docDefaults'))
    rpr = defaults.find(qn('w:rPrDefault')).find(qn('w:rPr'))
    for tag in ('w:rFonts', 'w:sz', 'w:szCs', 'w:lang'):
        for x in rpr.findall(qn(tag)):
            rpr.remove(x)
    fonts = OxmlElement('w:rFonts')
    for k in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
        fonts.set(qn(k), font)
    rpr.append(fonts)
    for tag in ('w:sz', 'w:szCs'):
        e = OxmlElement(tag)
        e.set(qn('w:val'), str(size_half_points))
        rpr.append(e)
    if rtl:
        lang = OxmlElement('w:lang')
        lang.set(qn('w:val'), 'en-GB')
        lang.set(qn('w:bidi'), 'ar-EG')
        rpr.append(lang)
    ppr_default = defaults.find(qn('w:pPrDefault'))
    if ppr_default is not None:
        defaults.remove(ppr_default)
    for st in d.styles:
        if st.name == 'Normal':
            st.font.name = font
            st.paragraph_format.space_after = 0
            st.paragraph_format.space_before = 0
            st.paragraph_format.line_spacing = 1.0
    return d


def bullet_numbering(d):
    """One bullet list («•», indent 540, hanging 270) added to the document's numbering part: its num id."""
    from docx.oxml import parse_xml
    numbering = d.part.numbering_part.element
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    aid = 90
    numbering.insert(0, parse_xml(
        f'<w:abstractNum {ns} w:abstractNumId="{aid}"><w:multiLevelType w:val="hybridMultilevel"/><w:lvl w:ilvl="0">'
        '<w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>'
        '<w:pPr><w:ind w:left="540" w:hanging="270"/></w:pPr></w:lvl></w:abstractNum>'))
    numbering.append(parse_xml(f'<w:num {ns} w:numId="{aid}"><w:abstractNumId w:val="{aid}"/></w:num>'))
    return aid


def set_num(par, num_id):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    ppr = par._p.get_or_add_pPr()
    npr = OxmlElement('w:numPr')
    il = OxmlElement('w:ilvl')
    il.set(qn('w:val'), '0')
    ni = OxmlElement('w:numId')
    ni.set(qn('w:val'), str(num_id))
    npr.append(il)
    npr.append(ni)
    ppr.append(npr)


def run_props(run, size=None, bold=None, color=None, font=None, rtl=False):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt, RGBColor
    if size:
        run.font.size = Pt(size / 2)
        rpr = run._r.get_or_add_rPr()
        szcs = OxmlElement('w:szCs')
        szcs.set(qn('w:val'), str(size))
        rpr.append(szcs)
    if bold:
        run.font.bold = True
        run.font.cs_bold = True
    if color:
        run.font.color.rgb = RGBColor.from_string(color)
    if font:
        run.font.name = font
        rpr = run._r.get_or_add_rPr()
        rf = rpr.find(qn('w:rFonts'))
        if rf is None:
            rf = OxmlElement('w:rFonts')
            rpr.insert(0, rf)
        for k in ('w:ascii', 'w:hAnsi', 'w:cs', 'w:eastAsia'):
            rf.set(qn(k), font)
    if rtl:
        rpr = run._r.get_or_add_rPr()
        e = OxmlElement('w:rtl')
        rpr.append(e)


def page_field(par, size, color, font, words=('Page ', ' of '), rtl=False):
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def field(code):
        r = par.add_run()
        run_props(r, size=size, color=color, font=font, rtl=rtl)
        for kind_, text in (('begin', None), (None, code), ('separate', None), (None, '1'), ('end', None)):
            if kind_:
                f = OxmlElement('w:fldChar')
                f.set(qn('w:fldCharType'), kind_)
                r._r.append(f)
            elif text == code:
                it = OxmlElement('w:instrText')
                it.set(qn('xml:space'), 'preserve')
                it.text = f' {code} '
                r._r.append(it)
            else:
                t = OxmlElement('w:t')
                t.text = text
                r._r.append(t)
    r = par.add_run(words[0])
    run_props(r, size=size, color=color, font=font, rtl=rtl)
    field('PAGE')
    r = par.add_run(words[1])
    run_props(r, size=size, color=color, font=font, rtl=rtl)
    field('NUMPAGES')


def spacing(par, before=None, after=None, keep_next=None, align=None, bidi=False):
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.shared import Twips
    pf = par.paragraph_format
    if before is not None:
        pf.space_before = Twips(before)
    if after is not None:
        pf.space_after = Twips(after)
    if keep_next:
        pf.keep_with_next = True
    if align:
        par.alignment = {'center': WD_ALIGN_PARAGRAPH.CENTER, 'both': WD_ALIGN_PARAGRAPH.JUSTIFY, 'left': WD_ALIGN_PARAGRAPH.LEFT,
                         'right': WD_ALIGN_PARAGRAPH.RIGHT}[align]
    if bidi:
        par._p.get_or_add_pPr().insert(0, OxmlElement('w:bidi'))


def no_borders(table):
    from docx.oxml import parse_xml
    tblpr = table._tbl.tblPr
    tblpr.append(parse_xml('<w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                           + ''.join(f'<w:{s} w:val="none" w:sz="0" w:space="0" w:color="FFFFFF"/>' for s in
                                     ('top', 'left', 'bottom', 'right', 'insideH', 'insideV')) + '</w:tblBorders>'))
    tblpr.append(parse_xml('<w:tblCellMar xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                           '<w:top w:w="20" w:type="dxa"/><w:left w:w="60" w:type="dxa"/><w:bottom w:w="20" w:type="dxa"/>'
                           '<w:right w:w="60" w:type="dxa"/></w:tblCellMar>'))


def word_en(path, title, blocks, header_line, creator, font='Times New Roman'):
    from docx.shared import Twips
    d = docx_doc(font, 22)
    d.core_properties.title = title
    d.core_properties.author = creator
    num = bullet_numbering(d)
    sec = d.sections[0]
    hp = sec.header.paragraphs[0]
    spacing(hp, align='right')
    run_props(hp.add_run(f'{header_line} — {title}'), size=16, color='666666', font=font)
    fp = sec.footer.paragraphs[0]
    spacing(fp, align='center')
    page_field(fp, 16, '666666', font)
    first = (d.paragraphs[0] if d.paragraphs else d.add_paragraph())
    used_first = False

    def para():
        nonlocal used_first
        if not used_first:
            used_first = True
            return first
        return d.add_paragraph()
    for b in blocks:
        if 't' in b:
            p = para()
            spacing(p, 0, 160, True, 'center')
            run_props(p.add_run(b['t']), size=26, bold=True, font=font)
        elif 'h' in b:
            p = para()
            spacing(p, 220, 80, True)
            run_props(p.add_run(b['h']), size=22, bold=True, font=font)
        elif 's' in b:
            p = para()
            spacing(p, 140, 60, True)
            run_props(p.add_run(b['s']), size=22, bold=True, font=font)
        elif 'b' in b:
            p = para()
            spacing(p, None, 40)
            set_num(p, num)
            run_props(p.add_run(b['b']), size=22, font=font)
        elif 'p' in b:
            p = para()
            spacing(p, None, 80, align='both')
            run_props(p.add_run(b['p']), size=22, font=font)
        elif 'rows' in b:
            t = d.add_table(rows=len(b['rows']), cols=2)
            no_borders(t)
            for i, r in enumerate(b['rows']):
                for j, c in enumerate(r):
                    cell = t.cell(i, j)
                    cell.width = Twips((5600, 3426)[j])
                    run_props(cell.paragraphs[0].add_run(c), size=22, font=font)
            p = d.add_paragraph()
            spacing(p, None, 60)
    d.save(path)


def word_rtl(path, title, blocks, creator, font='Arial'):
    from docx.shared import Twips
    d = docx_doc(font, 22, rtl=True)
    d.core_properties.title = title
    d.core_properties.author = creator
    num = bullet_numbering(d)
    sec = d.sections[0]
    fp = sec.footer.paragraphs[0]
    spacing(fp, align='center', bidi=True)
    page_field(fp, 16, '666666', font, ('صفحة ', ' من '), rtl=True)
    first = (d.paragraphs[0] if d.paragraphs else d.add_paragraph())
    used = [False]

    def runs(par, t, size=22, bold=False):
        if not AR.search(t):
            run_props(par.add_run(t), size=size, bold=bold, font=font)
            return
        ps = pieces(t)
        for i, (x, ltr) in enumerate(ps):
            if ltr:
                if i == 0:
                    run_props(par.add_run(LRM + ZWSP), size=size, bold=bold, font=font, rtl=True)
                run_props(par.add_run(keep(x) + ('' if re.search(r'[A-Za-z0-9µ½]$', x) else LRM)), size=size, bold=bold, font=font)
            else:
                nxt = ps[i + 1] if i + 1 < len(ps) else None
                run_props(par.add_run(x + (LRM + ZWSP if nxt and nxt[1] else '')), size=size, bold=bold, font=font, rtl=True)

    def para(t, **o):
        if not used[0]:
            used[0] = True
            p = first
        else:
            p = d.add_paragraph()
        ar = bool(AR.search(t))
        spacing(p, o.get('before'), o.get('after', 80), o.get('keep'), 'center' if o.get('center') else ('both' if ar else 'left'), bidi=ar)
        if o.get('bullet'):
            set_num(p, num)
        runs(p, t, o.get('size', 22), o.get('bold', False))
        return p
    for b in blocks:
        if 't' in b:
            para(b['t'], center=True, bold=True, size=26, keep=True, after=140)
        elif 'h' in b:
            para(b['h'], bold=True, keep=True, before=200, after=80)
        elif 'b' in b:
            para(b['b'], bullet=True, after=40)
        elif 'p' in b:
            para(b['p'])
        elif 'rows' in b:
            t = d.add_table(rows=len(b['rows']), cols=2)
            no_borders(t)
            from docx.oxml import OxmlElement
            t._tbl.tblPr.append(OxmlElement('w:bidiVisual'))
            for i, r in enumerate(b['rows']):
                for j, c in enumerate(r):
                    cell = t.cell(i, j)
                    cell.width = Twips((5600, 3426)[j])
                    p = cell.paragraphs[0]
                    ar = bool(AR.search(c))
                    spacing(p, None, 0, align='both' if ar else 'left', bidi=ar)
                    runs(p, c)
            p = d.add_paragraph()
            spacing(p, None, 60)
    d.save(path)


def to_pdf_lo(docx, outdir):
    subprocess.run([tool('soffice'), '--headless', '--norestore', '--convert-to', 'pdf', '--outdir', str(outdir), str(docx)],
                   check=True, capture_output=True, timeout=600)
    return outdir / (Path(docx).stem + '.pdf')


def make_pi(w, pi):
    content = json.loads((w.root / pi['content']).read_text(encoding='utf-8'))
    w.pi.mkdir(parents=True, exist_ok=True)
    out, checks = [], {}
    for doc in pi.get('documents', []):
        blocks = content[doc['blocks']]
        stem = doc.get('file', f"{doc['type']}-{doc['lang']}")
        docx = w.pi / f'{stem}.docx'
        if doc['lang'] == 'ar':
            src = content[doc['check_against']] if doc.get('check_against') else None
            if src is not None:
                bad = check_translation(src, blocks)
                checks[stem] = bad
                if bad:
                    raise SystemExit('الترجمة لا تطابق أصلها:\n' + '\n'.join(bad[:20]))
                say(f'{stem}: {len(blocks)} كتلة بالترتيب والأنواع نفسها، والأرقام نفسها في كل كتلة، وقيم التركيب متطابقة')
            word_rtl(docx, doc['title'], blocks, pi.get('creator_ar', pi.get('creator', '')))
            html = w.pi / f'{stem}.html'
            html.write_text(html_rtl(blocks, doc['title']), encoding='utf-8')
            pdf = w.pi / f'{stem}.pdf'
            print_html(html, pdf)
        else:
            word_en(docx, doc['title'], blocks, pi.get('header', ''), pi.get('creator', ''))
            pdf = to_pdf_lo(docx, w.pi)
        out.append({'type': doc['type'], 'lang': doc['lang'], 'title': doc.get('ectd_title', doc['title']), 'pdf': str(pdf), 'docx': str(docx)})
        say(f'{stem}: Word و PDF')
    return out, checks


def run(work):
    w = work if isinstance(work, Work) else Work(work)
    dec = w.decisions()
    ctd_root = w.ctd / (dec.get('ctd_folder') or 'CTD')
    docs = fix_pdfs(w, ctd_root, dec.get('fixes') or [])
    pi, checks = ([], {})
    if dec.get('pi'):
        pi, checks = make_pi(w, dec['pi'])
    rec = {'docs': docs, 'pi': pi, 'translation_checks': checks, 'changes': dec.get('pi', {}).get('changes_key')}
    w.save('fixed.json', rec)
    return rec
