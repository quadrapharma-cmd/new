"""The preparation stage's verdict on one document: every condition its item asks for, read against the document itself — its form
(a searchable PDF, NP.CAPP.065 v5 general note 4, and the PDF rules PdfCraft checks: version, security, JavaScript, bookmarks, size…)
and its content (conditions.py: dated, valid on the day of submission, on letterhead signed and stamped, legalised, a CoA's batch and
dates, a translation, the production lines) — each one:
    ok         met (and how the program knows: its text, its pages read by Claude, the person's answer),
    fixed      made right by the program in this preparation (PdfCraft, the text layer…),
    fix        the program can make it right («Prepare» does it),
    needs_you  not met, and only the person can change that — why, and what to do,
    check      the program cannot tell (no model to look at the pages): one look by the person answers it.
One source for the preparation page, the item and the Assistant. The owner, 13/11/2026: «a preparation stage that reads each document,
fixes it and prepares it according to the conditions required of that document and its content»."""
import re
from datetime import date, timedelta

from . import conditions as _cond, fixes as _fixes

WARN_DAYS = 90
FORM_RULES = ('EG-PF-', 'EG-BP-', 'PDF-', 'NTA065-', 'ICH-NAME')      # the PDF rules: the document's form; any other finding is about its content
NOT_FORM = {'DOC-EXPIRED', 'DOC-EXPIRING', 'DOC-EXPIRES-BEFORE-SUBMISSION',      # validity is a content condition here
            'NTA065-N4'}                               # «searchable» is the item's first form condition (_searchable)
SAY = {
    'ok_text': ('read in its text', 'قُرئ من نصه'),
    'ok_model': ('Claude saw it on its pages', 'عاينه Claude على صفحاته'),
    'ok_person': ('you confirmed it', 'أكّدتَه أنت'),
    'look': ('the program cannot see this without the model: look at the document and confirm', 'لا يستطيع البرنامج رؤية ذلك دون النموذج: عاين المستند وأكِّد'),
}
LANG = {'ar': 'Arabic', 'en': 'English'}
OTHER_LANG = re.compile(r'\b(?:der|die|das|und|nicht|le|la|les|et|des|du|el|los|las|del|y|il|di|che|per)\b', re.I)


def _date(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def _model_doc(doc):
    """What Claude read on the document's pages (meta «model»: its entry in the reading's «documents»), or {}."""
    m = (doc.get('meta') or {}).get('model') or {}
    return m.get('doc') or {}


def _yes(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return {'true': True, 'yes': True, 'false': False, 'no': False}.get(v.strip().lower())
    return None


def _line(c, status, en, ar, how=None, action=None):
    out = {'id': c['id'], 'kind': c['kind'], 'label': {'en': c['en'], 'ar': c['ar']}, 'source': c.get('source'), 'status': status,
           'why': {'en': en, 'ar': ar}}
    if how:
        out['how'] = how
    if action:
        out['action'] = action
    return out


def _form_lines(doc):
    """The PDF rules' findings on this document as conditions: each one the program fixes, or one only the person can."""
    meta = doc.get('meta') or {}
    refused = {x['op']: x for x in meta.get('fix_refused') or []}
    out = []
    for f in doc.get('findings') or []:
        if f.get('rule') in NOT_FORM or f.get('scope') == 'ectd':
            continue
        op = _fixes.RULE_TO_OP.get(f.get('rule'))
        c = {'id': 'rule:' + str(f.get('rule')), 'kind': 'form' if str(f.get('rule') or '').startswith(FORM_RULES) else 'content',
             'en': f.get('en') or '', 'ar': f.get('ar') or f.get('en') or '', 'source': f.get('source') or f.get('rule')}
        if f.get('action') == 'auto_fix' and op and op not in refused:
            out.append(_line(c, 'fix', 'The program fixes this (PdfCraft).', 'يُصلح البرنامج ذلك.', action='fix'))
        elif op in refused:
            why = refused[op]
            out.append(_line(c, 'needs_you', why.get('en') or f.get('en'), why.get('ar') or f.get('ar'), action='replace'))
        elif f.get('severity') == 'block':
            out.append(_line(c, 'needs_you', f.get('en') or '', f.get('ar') or '', action=f.get('action')))
        else:
            out.append(_line(c, 'check', f.get('en') or '', f.get('ar') or '', action=f.get('action')))
    for op in [x for x in meta.get('fixes') or [] if x != 'make_searchable']:      # what this preparation (or an earlier one) made right
        en, ar = _fixes.LABEL.get(op, ({'optimize': 'File improved (PdfCraft\'s optimizer), the pages the same'}.get(op, op),
                                        {'optimize': 'حُسِّن الملف، والصفحات كما هي'}.get(op, op)))
        out.append(_line({'id': 'fixed:' + op, 'kind': 'form', 'en': en, 'ar': ar, 'source': 'PdfCraft'}, 'fixed', en, ar))
    return out


def _searchable(c, doc, reading):
    meta = doc.get('meta') or {}
    name = (doc.get('filename') or '').lower()
    if name.endswith('.docx') and c['id'] == 'pdf':    # turned into PDF here (LibreOffice, or the browser edition's Word program, 17/11)
        return _line(c, 'needs_you', 'A Word file where a PDF is asked: «Turn it into PDF» makes its PDF here (the Word file is kept) — or save it '
                     'as PDF in Word (signed and stamped where needed) and add it.',
                     'ملف Word والمطلوب PDF: «تحويله إلى PDF» يصنع ملف PDF منه هنا (ويبقى ملف Word محفوظًا)، أو احفظه بصيغة PDF من Word '
                     '(موقَّعًا ومختومًا إن لزم) وأضفه.', action='to_pdf')
    if name.endswith(('.doc', '.docx')) and c['id'] == 'pdf':
        return _line(c, 'needs_you', 'A Word file where a PDF is asked: save it as PDF (signed and stamped where needed) and add the PDF.',
                     'ملف Word والمطلوب PDF: احفظه بصيغة PDF (موقَّعًا ومختومًا إن لزم) وأضف ملف PDF.', action='replace')
    ar_n, all_n = meta.get('converted_arabic') or 0, meta.get('converted_words') or 0
    if meta.get('converted_by') == 'wordcraft' and (ar_n >= 20 or (all_n and ar_n >= 0.1 * all_n)):
        # measured 17/11 on his leaflet and source file: the Word program draws Arabic right, but a copy (or a search) of it comes
        # back in pieces — 318 of the leaflet's 610 words whole (LibreOffice's PDF: 567)
        return _line(c, 'check', 'Turned into PDF here from a Word file with Arabic: its pages are drawn right, but Arabic copied from it or '
                     'searched in it does not come back as whole words. For the submission, save it as PDF in Word on your computer and add '
                     'it as a new version — or accept it as it is.',
                     'حُوِّل إلى PDF هنا من ملف Word فيه نص عربي: صفحاته مرسومة سليمة، لكن النص العربي المنسوخ منه أو المبحوث فيه لا يرجع '
                     'كلماتٍ سليمة. للتقديم: احفظه بصيغة PDF من Word على جهازك وأضفه نسخةً جديدة، أو اقبله كما هو.', action='accept')
    if 'make_searchable' in (meta.get('fixes') or []):
        return _line(c, 'fixed', 'Its pages were read and their text written invisibly under them: searchable now, the pages unchanged.',
                     'قُرئت صفحاته وكُتب نصها تحتها مخفيًّا: صار قابلًا للبحث، والصفحات كما هي.')
    n4 = next((f for f in doc.get('findings') or [] if f.get('rule') == 'NTA065-N4'), None)
    if n4:
        refused = {x['op']: x for x in meta.get('fix_refused') or []}.get('make_searchable')
        if refused:
            return _line(c, 'needs_you', refused.get('en') or n4.get('en'), refused.get('ar') or n4.get('ar'), action='replace')
        if n4.get('action') == 'auto_fix':
            return _line(c, 'fix', 'A scan without text: the program reads its pages and writes their text under them (Prepare).',
                         'ممسوح ضوئيًا بلا نص: يقرأ البرنامج صفحاته ويكتب نصها تحتها («تجهيز»).', action='fix')
        return _line(c, 'needs_you', n4.get('en') or '', n4.get('ar') or '', action=n4.get('action'))
    if reading and reading.get('scanned') and not reading.get('chars'):
        return _line(c, 'fix', 'A scan without text: it is made searchable when it is prepared.', 'ممسوح ضوئيًا بلا نص: يصبح قابلًا للبحث عند التجهيز.', action='fix')
    return _line(c, 'ok', 'It has its own text: searchable.', 'له نص: قابل للبحث.', how='text')


def _validity(c, doc, md, today, target=None):
    meta = doc.get('meta') or {}
    mine = _date(meta.get('valid_until'))                # the document's own date: its text's, the person's, or a reading's kept with it
    seen = _date(md.get('valid_until')) or _date(meta.get('claude_valid_until'))   # what Claude read on its pages (here, or in «القراءة والفرز»)
    if mine:
        vu = mine
        how = 'model' if meta.get('validity_note') == 'read by Claude' else ('text' if meta.get('valid_until_read') else 'person')
    else:
        vu, how = seen, 'model'
    other = seen if (how == 'text' and seen and seen != vu) else None      # two readings that do not agree: both said, the person decides
    if not vu:
        return _line(c, 'check', 'No end date read on it: write the date it stops being valid (or confirm it has none).',
                     'لم يُقرأ عليه تاريخ انتهاء: اكتب تاريخ انتهائه (أو أكِّد أنه بلا تاريخ انتهاء).', action='set_validity')
    shown = vu.strftime('%d/%m/%Y')
    also = (f' Claude read another date on its pages: {other.strftime("%d/%m/%Y")} — write the right one if it is not this.',
            f' وقرأ Claude على صفحاته تاريخًا آخر: {other.strftime("%d/%m/%Y")} — اكتب التاريخ الصحيح إن كان غير هذا.') if other else ('', '')
    if vu < today:
        return _line(c, 'needs_you', f'Expired on {shown}: a current one from the issuer is needed.{also[0]}', f'منتهٍ منذ {shown}: يجب تقديم نسخة سارية من الجهة التي أصدرته.{also[1]}',
                     how=how, action='re_obtain')
    if target and vu < target:                          # valid today, not on the day the dossier is meant to be submitted
        day = target.strftime('%d/%m/%Y')
        return _line(c, 'needs_you', f'Valid until {shown}: it will have expired by the target submission date ({day}). Renew it before then.{also[0]}',
                     f'سارٍ حتى {shown}: ستنتهي صلاحيته قبل تاريخ التقديم المستهدف ({day}). جدِّده قبل ذلك.{also[1]}', how=how, action='re_obtain')
    if vu <= today + timedelta(days=WARN_DAYS):
        return _line(c, 'check', f'Valid until {shown} — less than {WARN_DAYS} days: start the renewal.{also[0]}', f'سارٍ حتى {shown} — أقل من {WARN_DAYS} يوم: ابدأ التجديد.{also[1]}',
                     how=how, action='re_obtain')
    if other:
        return _line(c, 'check', f'Valid until {shown} by its text.{also[0]}', f'سارٍ حتى {shown} بحسب نصه.{also[1]}', how=how, action='set_validity')
    return _line(c, 'ok', f'Valid until {shown}.', f'سارٍ حتى {shown}.', how=how)


def _seen(c, md, keys, attest, need, en_ok, ar_ok, en_no, ar_no):
    """A condition only eyes can check (signed, stamped, letterhead, legalised): what Claude saw on the pages, else the person's answer
    to the item's question, else «look»."""
    seen = [_yes(md.get(k)) for k in keys]
    if md and all(v is True for v in seen):
        return _line(c, 'ok', en_ok, ar_ok, how='model')
    if md and any(v is False for v in seen):
        missing = [k for k, v in zip(keys, seen) if v is False]
        return _line(c, 'needs_you', en_no + ' (' + ', '.join(missing) + ').', ar_no + ' (' + '، '.join({'signed': 'التوقيع', 'stamped': 'الختم',
                     'letterhead': 'ورق الشركة', 'legalized': 'التوثيق'}.get(k, k) for k in missing) + ').', how='model', action='replace')
    a = (attest or {}).get('answer')
    if need and a == 'yes':
        return _line(c, 'ok', en_ok, ar_ok, how='person')
    if need and a == 'no':
        return _line(c, 'needs_you', en_no + '.', ar_no + '.', how='person', action='replace')
    return _line(c, 'check', SAY['look'][0], SAY['look'][1], action='attest')


def verdict(doc, req, pack, reading=None, attest=None, today=None, target=None):
    """Every condition of this document's item, read against the document: [{id, kind: form | content, label {en, ar}, source,
    status: ok | fixed | fix | needs_you | check, why {en, ar}, how?: text | model | person, action?}], form first. `reading`: what the
    program read from it (extract.read_files' entry: chars, scanned, text…); `attest`: the person's answer to the item's question."""
    today = today or date.today()
    reading = reading or {}
    md = _model_doc(doc)
    text = reading.get('text') or ''
    conds = _cond.for_requirement(req, pack) if req else [_cond._c('form', _cond.FORM_PDF, _cond.N4, 'pdf')]
    form, content = [], []
    for c in conds:
        cid = c.get('id')
        if cid in ('pdf', 'art'):
            form.append(_searchable(c, doc, reading))
        elif cid == 'word':
            ok = (doc.get('filename') or '').lower().endswith('.docx')
            form.append(_line(c, 'ok' if ok else 'needs_you', 'A Word file.' if ok else 'Not a Word (.docx) file: add the Word file.',
                              'ملف Word.' if ok else 'ليس ملف Word (.docx): أضف ملف Word.', how='text', action=None if ok else 'replace'))
        elif cid == 'valid':
            content.append(_validity(c, doc, md, today, target))
        elif cid == 'dated':
            found = _date(md.get('issued')) or _date((doc.get('meta') or {}).get('issued')) or re.search(
                r'\b(?:\d{1,2}[/.-]\d{1,2}[/.-](?:19|20)\d{2}|(?:19|20)\d{2}-\d{2}-\d{2})\b', text)
            content.append(_line(c, 'ok', 'Dated.', 'مؤرَّخ.', how='model' if md.get('issued') else 'text') if found else
                           _line(c, 'check', 'No date read on it: check it is dated.', 'لم يُقرأ عليه تاريخ: تحقَّق من أنه مؤرَّخ.', action='attest'))
        elif cid == 'letterhead':
            content.append(_seen(c, md, ['letterhead', 'signed', 'stamped'], attest, True, 'On letterhead, signed and stamped.',
                                 'على ورق الشركة، موقّع ومختوم.', 'Not on letterhead, signed and stamped', 'ليس على ورق الشركة وموقَّعًا ومختومًا'))
        elif cid == 'legalized':
            content.append(_seen(c, md, ['legalized'], attest, True, 'Legalised.', 'موثّق.', 'Not legalised', 'غير موثَّق'))
        elif cid == 'coa':
            have = [k for k in ('batch', 'manufactured', 'expiry') if md.get(k)]
            if not md:
                have = [k for k, rx in (('batch', r'(?i)\b(?:batch|lot)\s*(?:no\.?|number|#)?\s*[:.]?\s*[A-Z0-9-]{3,}'),
                                        ('manufactured', r'(?i)(?:mfg|manufactur\w*)\s*(?:date)?'), ('expiry', r'(?i)(?:exp\w*|retest)'))
                        if re.search(rx, text)]
            missing = [k for k in ('batch', 'manufactured', 'expiry') if k not in have]
            names = {'batch': ('batch number', 'رقم التشغيلة'), 'manufactured': ('manufacturing date', 'تاريخ التصنيع'),
                     'expiry': ('expiry or retest date', 'تاريخ الانتهاء أو إعادة التحليل')}
            if not missing:
                content.append(_line(c, 'ok', 'Batch number, manufacturing date and expiry are on it.', 'فيه رقم التشغيلة وتاريخ التصنيع وتاريخ الانتهاء.',
                                     how='model' if md else 'text'))
            else:
                content.append(_line(c, 'needs_you' if md else 'check', 'Not read on it: ' + ', '.join(names[k][0] for k in missing) + '.',
                                     'لم يُقرأ عليه: ' + '، '.join(names[k][1] for k in missing) + '.', how='model' if md else 'text',
                                     action='replace' if md else 'attest'))
        elif cid == 'translation':
            lang = str(md.get('language') or '').strip().lower()
            other = (lang and not set(re.split(r'[+/, ]+', lang)) <= {'ar', 'en', 'arabic', 'english'}) or (
                not lang and len(OTHER_LANG.findall(text)) > 25 and not reading.get('arabic'))
            if other:
                content.append(_line(c, 'needs_you', f'Written in {lang or "another language"}: add its certified, searchable English translation to this item.',
                                     f'مكتوب بلغة أخرى ({lang or "غير العربية والإنجليزية"}): أضف ترجمته الإنجليزية المعتمدة والقابلة للبحث في البند نفسه.',
                                     how='model' if lang else 'text', action='add_translation'))
            else:
                content.append(_line(c, 'ok', 'In Arabic or English.', 'بالعربية أو الإنجليزية.', how='model' if lang else 'text'))
        elif cid == 'lines':
            found = md.get('production_lines') or re.search(r'(?i)(?:production\s+line|line\s*(?:no\.?|number)|خط\s*(?:ال)?إنتاج)', text)
            content.append(_line(c, 'ok', 'It names the production lines.', 'محدَّدة فيه خطوط الإنتاج.', how='model' if md.get('production_lines') else 'text')
                           if found else _line(c, 'check', 'No production line read on it: check it names the lines of this dosage form.',
                                               'لم يُقرأ عليه خط إنتاج: تحقَّق من أن خطوط هذا الشكل الصيدلي محدَّدة فيه.', action='attest'))
        elif cid == 'price_exc':
            continue                                    # said with «valid» when the certificate has expired
        elif cid == 'source':
            continue                                    # the source's own words: shown with the item, not a condition to tick
        else:
            content.append(_line(c, 'check', SAY['look'][0], SAY['look'][1], action='attest'))
    if md.get('one_document') is False or _yes(md.get('one_document')) is False:
        form.append(_line({'id': 'one', 'kind': 'form', 'en': 'One document per file.', 'ar': 'مستند واحد في كل ملف.', 'source': _cond.N4},
                          'needs_you', 'Claude saw more than one document in this file: split it, one document per file, each in its item.',
                          'رأى Claude أكثر من مستند في هذا الملف: قسِّمه، ليكون كل مستند في ملف وفي بنده.', how='model', action='split'))
    found = _form_lines(doc)
    out = form + [x for x in found if x['kind'] == 'form'] + content + [x for x in found if x['kind'] != 'form']
    confirmed = (doc.get('meta') or {}).get('confirmed') or {}
    for i, x in enumerate(out):                         # what the person looked at and answered, for this document
        a = confirmed.get(x['id'])
        if x['status'] == 'check' and a in ('yes', 'no'):
            out[i] = dict(x, status='ok' if a == 'yes' else 'needs_you', how='person',
                          why={'en': SAY['ok_person'][0], 'ar': SAY['ok_person'][1]} if a == 'yes' else
                          {'en': 'You said it is not so yet: replace the document when it is.', 'ar': 'ذكرتَ أنه ليس كذلك بعد: استبدل المستند عندما يجهز.'})
    return out


def summary(lines):
    """How the document stands: the counts by status, and «ready» when nothing is left to fix or to answer."""
    n = {k: sum(1 for x in lines if x['status'] == k) for k in ('ok', 'fixed', 'fix', 'needs_you', 'check')}
    return {**n, 'ready': not n['fix'] and not n['needs_you'] and not n['check']}
