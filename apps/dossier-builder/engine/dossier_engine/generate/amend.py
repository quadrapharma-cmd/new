"""Amending a document per the rules.

* apply_edits(docx_bytes, edits, author) — edits a Word document with TRACKED CHANGES (w:ins / w:del, author and date), so the
  company sees every change, accepts or rejects it in Word, then signs. Edits locate a paragraph by its text (exact, or a
  unique substring) and replace it, insert a new paragraph after it, or delete it. Each edit carries the rule it serves; the
  change log is returned with the result and is also appended as a final section of the document.
* memo(...) — an amendment memo (DOCX) for documents that cannot be edited here: PDFs without a Word source, and third-party
  documents (which are never altered — the memo tells the issuer or the author what must change and why).
"""
import copy
import datetime as _dt
import io
import re

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from . import docx_kit

AUTHOR = 'Dossier Builder Assistant'


class AmendError(ValueError):
    pass


def _norm(s):
    return re.sub(r'\s+', ' ', (s or '')).strip().lower()


def _all_paragraphs(doc):
    """Body paragraphs and table-cell paragraphs, in document order."""
    out = list(doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                out.extend(cell.paragraphs)
    return out


def _locate(paragraphs, find):
    key = _norm(find)
    if not key:
        raise AmendError('empty «find» text')
    exact = [p for p in paragraphs if _norm(p.text) == key]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise AmendError(f'«{find[:60]}» matches {len(exact)} paragraphs exactly; quote more of the paragraph')
    part = [p for p in paragraphs if key in _norm(p.text)]
    if len(part) == 1:
        return part[0]
    if not part:
        raise AmendError(f'no paragraph contains «{find[:60]}»')
    raise AmendError(f'«{find[:60]}» is in {len(part)} paragraphs; quote a longer, unique passage')


_ID = [1000]


def _mark(tag, author, date):
    el = OxmlElement(tag)
    _ID[0] += 1
    el.set(qn('w:id'), str(_ID[0]))
    el.set(qn('w:author'), author)
    el.set(qn('w:date'), date)
    return el


def _first_rpr(p):
    for r in p.runs:
        if r._r.rPr is not None:
            return copy.deepcopy(r._r.rPr)
    return None


def _del_runs(p, author, date):
    """Every run of the paragraph becomes a deletion (its text moves into w:delText)."""
    for r in list(p._p.findall(qn('w:r'))):
        d = _mark('w:del', author, date)
        p._p.replace(r, d)
        d.append(r)
        for t in r.findall(qn('w:t')):
            t.tag = qn('w:delText')


def _ins_run(p, text, rpr, author, date):
    ins = _mark('w:ins', author, date)
    r = OxmlElement('w:r')
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = OxmlElement('w:t')
    t.set(qn('xml:space'), 'preserve')
    t.text = text
    r.append(t)
    ins.append(r)
    p._p.append(ins)
    return ins


def _para_mark(p, tag, author, date):
    """Mark the paragraph mark itself as inserted / deleted (w:pPr/w:rPr/w:ins|w:del)."""
    ppr = p._p.get_or_add_pPr()
    rpr = ppr.find(qn('w:rPr'))
    if rpr is None:
        rpr = OxmlElement('w:rPr')
        ppr.append(rpr)
    rpr.append(_mark(tag, author, date))


def apply_edits(docx_bytes, edits, author=AUTHOR, log_heading=None):
    """→ (new_docx_bytes, change_log). edits: [{op: replace|insert_after|delete, find, text, rule, reason}]."""
    if not edits:
        raise AmendError('no edits')
    doc = Document(io.BytesIO(docx_bytes))
    date = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    log = []
    for i, e in enumerate(edits, 1):
        op = (e.get('op') or 'replace').lower()
        find, text = e.get('find') or '', e.get('text') or ''
        paras = _all_paragraphs(doc)
        p = _locate(paras, find)
        before = p.text
        if op == 'replace':
            if not text.strip():
                raise AmendError(f'edit {i}: replacement text is empty (use op delete)')
            rpr = _first_rpr(p)
            _del_runs(p, author, date)
            _ins_run(p, text, rpr, author, date)
        elif op == 'insert_after':
            if not text.strip():
                raise AmendError(f'edit {i}: text to insert is empty')
            new_p = copy.deepcopy(p._p)
            for child in list(new_p):
                if child.tag != qn('w:pPr'):
                    new_p.remove(child)
            p._p.addnext(new_p)
            from docx.text.paragraph import Paragraph
            np_ = Paragraph(new_p, p._parent)
            _para_mark(np_, 'w:ins', author, date)
            _ins_run(np_, text, _first_rpr(p), author, date)
        elif op == 'delete':
            _del_runs(p, author, date)
            _para_mark(p, 'w:del', author, date)
        else:
            raise AmendError(f'edit {i}: unknown op {op}')
        log.append({'n': i, 'op': op, 'rule': e.get('rule'), 'reason': e.get('reason'), 'before': before[:300], 'after': (text if op != 'delete' else '')[:300]})
    # the change log as a final section (plain, not tracked, so it survives accept-all)
    doc.add_page_break()
    h = doc.add_paragraph()
    r = h.add_run(log_heading or 'Change log — amendments per the rules / سجل التغييرات حسب القواعد')
    r.bold = True
    for item in log:
        doc.add_paragraph(f"{item['n']}. [{item['rule'] or '-'}] {item['op']}: {item['reason'] or ''}")
        if item['before']:
            doc.add_paragraph('   was: ' + item['before'])
        if item['after']:
            doc.add_paragraph('   now: ' + item['after'])
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue(), log


def memo(items, doc_name, product, out_path, lang='en', to=None, letterhead=None):
    """Amendment memo: rule · where · what is wrong · required change, for a document that is not edited here."""
    ar = lang == 'ar'
    d = docx_kit.new_doc(letterhead=letterhead, draft=True)
    docx_kit.para(d, 'مذكرة تعديل مستند حسب القواعد' if ar else 'Document amendment memo (per the rules)', ar=ar, bold=True, size=14, align='center')
    docx_kit.para(d, (f'المستند: {doc_name}' if ar else f'Document: {doc_name}') + (f' · {product}' if product else ''), ar=ar)
    if to:
        docx_kit.para(d, ('إلى: ' if ar else 'To: ') + to, ar=ar)
    docx_kit.para(d, _dt.date.today().isoformat(), ar=ar)
    docx_kit.para(d, ('المطلوب تعديله في هذا المستند، مع القاعدة التي يستند إليها كل بند:' if ar else
                      'What must change in this document, with the rule each item rests on:'), ar=ar)
    header = ['#', 'القاعدة', 'الموضع', 'الملاحظة', 'التعديل المطلوب'] if ar else ['#', 'Rule', 'Where', 'Finding', 'Required change']
    rows = [[i, it.get('rule') or '', it.get('where') or '', it.get('finding') or '', it.get('change') or ''] for i, it in enumerate(items, 1)]
    docx_kit.table(d, header, rows, widths=[0.8, 3.0, 2.6, 5.3, 5.3], ar=ar)
    docx_kit.para(d, '', ar=ar)
    docx_kit.para(d, 'يُطبَّق التعديل في المصدر الأصلي للمستند ويُعاد إصداره موقَّعًا.' if ar else
                  'The change is applied in the document\'s source and the document is re-issued signed.', ar=ar)
    d.save(out_path)
    return out_path
