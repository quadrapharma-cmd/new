"""What each document must be before it is uploaded — its form and its content — from the rules in force: NP.CAPP.065 v5 for Egypt
(the One Submission, in force since 01/11/2025), the authority's own requirement text for the others. One source for the three places
that show it: the start of a new dossier (every step's documents, before anything is uploaded), each base-document card, and each
item. The upload gate (a file without text), the content checks (validity, a CoA's data) and the item's one question (signed,
stamped, legalised) hold the program to it."""
from . import extract

N4 = 'NP.CAPP.065 v5, general note 4'
FORM_PDF = {'en': 'A searchable PDF — its own text layer, made when it is scanned (not a picture); one document per file.',
            'ar': 'PDF قابل للبحث — عليه طبقة نص بتتعمل وقت المسح (مش صورة)، ومستند واحد في كل ملف.'}
FORM_WORD = {'en': 'Word (.docx): the proposed SmPC and PIL, in Arabic and in English. For an eCTD the program converts it to PDF.',
             'ar': 'Word (.docx): النشرة المقترحة (SmPC وPIL) عربي وإنجليزي. في الـ eCTD البرنامج بيحوّلها PDF.'}
FORM_ART = {'en': 'A PDF of the coloured artwork, stamped — an editable PDF is preferred.',
            'ar': 'PDF للتصميم الملوّن مختوم — والأفضل PDF قابل للتعديل.'}
LETTERHEAD = {'en': "On the company's letterhead, signed by the responsible person and stamped.",
              'ar': 'على ورق الشركة، موقّع من المسؤول ومختوم.'}
DATED = {'en': 'Dated.', 'ar': 'عليه تاريخ.'}
VALID = {'en': 'Valid on the day of submission (the program reads its date and warns 90 days before it ends).',
         'ar': 'ساري يوم التقديم (البرنامج بيقرا تاريخه وبينبّه قبل ما ينتهي بـ 90 يوم).'}
PRICE_EXC = {'en': 'If it has expired: add the request for updating the price to this item — EDA accepts the two together.',
             'ar': 'لو منتهي: ضيف طلب تحديث السعر في نفس البند — الهيئة بتقبل الاتنين مع بعض.'}
LINES = {'en': 'It names the production lines of this dosage form.', 'ar': 'محدد فيه خطوط الإنتاج للشكل الصيدلي ده.'}
COA = {'en': "On the supplier's letterhead, signed and stamped, with the batch number, the manufacturing date and the expiry (or retest) date.",
       'ar': 'على ورق المورّد، موقّع ومختوم، وفيه رقم التشغيلة وتاريخ التصنيع والانتهاء (أو إعادة التحليل).'}
TRANSLATION = {'en': 'In a language other than Arabic or English: with a certified, searchable English translation.',
               'ar': 'لو بلغة غير العربي والإنجليزي: ومعاه ترجمة إنجليزي معتمدة وقابلة للبحث.'}
LEGALIZE = {'M1-14': {'en': 'Legalised by the Egyptian embassy (an electronic CPP is exempt).', 'ar': 'موثّق من السفارة المصرية (الـ CPP الإلكتروني معفي).'},
            'M1-26': {'en': "The licence holder's declaration, legalised.", 'ar': 'إقرار صاحب الترخيص، موثّق.'},
            'M1-27': {'en': "The licence holder's declaration, legalised.", 'ar': 'إقرار صاحب الترخيص، موثّق.'},
            'M1-24': {'en': 'The storage contract and the agency authorisation, legalised.', 'ar': 'عقد التخزين والتوكيل، موثّقين.'}}
DATED_ITEMS = {'M1-01', 'M1-43'}              # the application form and the cover letter carry their date, as the declarations do
DATED_WORDS = ('declaration', 'commitment', 'undertaking')
AUTO_ITEMS = {'M1-44'}                         # the tracking table: rebuilt by the program at every eCTD export
VALIDITY_KINDS = ('gmp', 'pricing', 'commercial', 'cpp', 'factory', 'licence')     # the ones EDA asks to be valid at submission


def _c(kind, text, source):
    return {'kind': kind, 'en': text['en'], 'ar': text['ar'], 'source': source}


def for_requirement(req, pack):
    """The conditions one requirement's document must meet: [{kind: form | content, en, ar, source}]."""
    rid, cls, eg = req['id'], req.get('doc_class'), pack.egypt
    out = []
    if eg and rid == 'M1-09':
        out.append(_c('form', FORM_WORD, 'NP.CAPP.065 v5 1.1.9'))
    elif eg and rid == 'M1-11':
        out.append(_c('form', FORM_ART, 'NP.CAPP.065 v5 1.1.10'))
    else:
        out.append(_c('form', FORM_PDF, N4 if eg else "the authority's electronic submission rules"))
    letter = cls == 'company_letter' or (cls == 'generated' and req.get('module') == 1 and rid not in AUTO_ITEMS)
    if letter:                                     # a letter the company signs (Module 1); Module 2–5 technical text is not a letter
        out.append(_c('content', LETTERHEAD, 'NP.CAPP.065 v5' if eg else 'general practice'))
        if eg and (rid in DATED_ITEMS or any(w in req['title']['en'].lower() for w in DATED_WORDS)):
            out.append(_c('content', DATED, 'NP.CAPP.065 v5'))
    homes = {k for k in VALIDITY_KINDS if rid in extract.kind_homes(k, pack)}
    if homes:
        out.append(_c('content', VALID, 'NP.CAPP.065 v5' if eg else "the authority's requirement"))
    if eg and rid == 'M1-05':
        out.append(_c('content', PRICE_EXC, 'NP.CAPP.065 v5 1.1.5'))
    if eg and rid == 'M1-37':
        out.append(_c('content', LINES, 'NP.CAPP.065 v5 1.2.4.1'))
    if eg and rid in LEGALIZE:
        out.append(_c('content', LEGALIZE[rid], 'NP.CAPP.065 v5'))
    if eg and rid == 'M1-35':
        out.append(_c('content', COA, 'NP.CAPP.065 v5 1.2.3.1'))
    if cls == 'third_party_certificate':          # issued abroad (an EDA document is Arabic already)
        out.append(_c('content', TRANSLATION, 'NP.CAPP.065 v5' if eg else 'general practice'))
    if req.get('acceptance_text'):                  # the source's own wording (English), shown as written
        out.append({'kind': 'source', 'en': req['acceptance_text'], 'ar': req['acceptance_text'], 'source': '; '.join(req.get('sources') or [])})
    return out


def for_kinds(pack, kinds):
    """The conditions of the item a base document of these kinds goes to (the first home this pack has)."""
    for k in kinds:
        for rid in extract.kind_homes(k, pack):
            if rid in pack.by_id:
                return for_requirement(pack.by_id[rid], pack)
    return [_c('form', FORM_PDF, N4 if pack.egypt else "the authority's electronic submission rules")]
