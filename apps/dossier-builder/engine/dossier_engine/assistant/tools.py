"""The Assistant's tools = the program's own operations, described for Claude and executed against the engine.

Reading tools call the store directly; writing tools go through the program's HTTP API in-process (same validation, same
errors, same audit as the screen), with the actor «claude». Three tools never run without a person's approval: export,
signing a review, withdrawing a document (see APPROVAL). A tool may attach document pages (as a PDF document block) or an
image to the next user turn so Claude sees scanned pages itself."""
import base64
import io
import json
import re
import time

from .. import extract
from . import storage

APPROVAL = {'export_dossier', 'sign_review', 'withdraw_document'}
WRITES = APPROVAL | {'draft_document', 'put_data', 'set_profile', 'place_document', 'generate_document', 'run_review', 'act_on_finding',
                     'add_response', 'reassess_finding', 'make_review_letter', 'request_reissue', 'save_reading',
                     'record_document_review', 'amend_document', 'amendment_memo', 'drive_fetch'}
MAX_TEXT = 60_000          # characters of document text returned per call
MAX_PAGES = 20             # pages attached per call
MAX_ATTACH = 24_000_000    # bytes of PDF attached per call

DATA_SHAPE = ('Product data record: {"apis": [{"name", "manufacturer", "country", "strength", "option": "CEP|DMF|PQ|FULL", "cep_no", "cep_status", '
              '"address_gmp", "coa_name", "spec_standard", "proposed_retest_months", "cep_retest_months"}], '
              '"batches": [{"no", "kind": "fpp|api", "api", "size", "scale": "pilot|production|smaller", "date": "YYYY-MM-DD", "site", "expiry", "conformity"}], '
              '"specs": {"product": [{"test", "limit", "method"}], "api": {"<api name>": [{"test", "limit", "method"}]}}, '
              '"results": {"<batch no>": {"<test>": "<value>"}}, '
              '"composition": [{"name", "amount", "standard", "function": "active|excipient|…", "equivalent"}], '
              '"registration": {"reg_no", "reg_date", "valid_until", "shelf_life", "storage", "price", "prices": [{"price", "pack"}], "packs": [], "licence_type", "marketing"}, '
              '"pack": {...}, "leaflet": {...}, "be_batches": [...], "uncomplicated_fpp": bool, "applicant_names": {"<document>": "<name as printed>"}}')


class ToolError(Exception):
    pass


def _s(d, keys):
    return {k: d.get(k) for k in keys if d.get(k) not in (None, '', [], {})}


def _obj(desc, props, required=()):
    return {'type': 'object', 'description': desc, 'properties': props, 'required': list(required), 'additionalProperties': False}


S = lambda desc, **kw: {'type': 'string', 'description': desc, **kw}        # noqa: E731
B = lambda desc: {'type': 'boolean', 'description': desc}                    # noqa: E731
I = lambda desc: {'type': 'integer', 'description': desc}                    # noqa: E731
ANY = {'type': 'object', 'description': 'JSON object', 'additionalProperties': True}

SPECS = [
    {'name': 'get_dossier', 'description': 'The dossier as the program knows it: name, product, applicant/envelope, regulatory profile, rule pack, counts.',
     'input_schema': _obj('no input', {})},
    {'name': 'get_board', 'description': 'Every required/optional CTD item (slot) with its status and documents, plus files not yet placed in any slot '
                                         '(«unassigned»). Use only_open to see just what still needs work.',
     'input_schema': _obj('filter', {'only_open': B('true → only items that are not started, waiting, non-conforming or need attention')})},
    {'name': 'get_slot', 'description': 'One CTD item in full: what EDA requires (acceptance text, sources), how it is produced, its documents with their '
                                        'technical findings, cross-check findings and any open re-issue request.',
     'input_schema': _obj('which item', {'slot_id': S('slot id from get_board, e.g. M1-05 or S-07@Paracetamol|Granules India')}, ['slot_id'])},
    {'name': 'get_data', 'description': 'The structured product data (APIs, batches, specifications, results, composition, registration, packs). ' + DATA_SHAPE,
     'input_schema': _obj('no input', {})},
    {'name': 'put_data', 'description': 'Write structured product data, merged over what exists (a list you send replaces that list; omitted keys are kept). '
                                        'Only values read from the documents — never guessed; leave unknown fields out. ' + DATA_SHAPE,
     'input_schema': _obj('data + why', {'data': ANY, 'rationale': S('one sentence: which document and pages the values come from')}, ['data', 'rationale'])},
    {'name': 'set_profile', 'description': 'Change the regulatory profile (dossier_kind generic|innovator, origin local|imported, licence own|toll|f_toll|under_licence|'
                                           'imported|imported_bulk, activity new|re_registration, admin_route oral|topical|parenteral|ophthalmic|inhalation|other, '
                                           'leaflet english|non_english, dosage_specifics [], apis [{name, manufacturer, option}]). Merged over the current profile; '
                                           'the program re-resolves which items are required.',
     'input_schema': _obj('profile fields + why', {'profile': ANY, 'rationale': S('why, with the document that says so')}, ['profile', 'rationale'])},
    {'name': 'read_document', 'description': 'Read a stored document: returns its text (text layer or OCR) and ATTACHES the requested pages as a PDF so you can '
                                             'see them (scans, tables, stamps). Read at most 20 pages per call; use pages like "1-5" or "6-10" for long files. '
                                             'Your earlier saved readings of the document are returned first — do not re-read what you already noted.',
     'input_schema': _obj('document and pages', {'doc_id': S('document id from get_board / get_slot'), 'pages': S('page range "a-b" (1-based); omit for the first 20 pages')},
                          ['doc_id'])},
    {'name': 'save_reading', 'description': 'Save your digest of a document (what it states: names, numbers, dates, batches, conclusions, page references) so '
                                            'later sessions do not read it again. Facts only, as printed.',
     'input_schema': _obj('digest', {'doc_id': S('document id'), 'pages': S('pages covered, e.g. "1-4"'), 'note': S('the digest, ≤ 2000 characters')}, ['doc_id', 'note'])},
    {'name': 'get_readings', 'description': 'Saved digests for the dossier (optionally one document).',
     'input_schema': _obj('filter', {'doc_id': S('document id; omit for all')})},
    {'name': 'classify_unassigned', 'description': 'Where the program suggests each unplaced file should go (by file name and first-page text), with scores. A suggestion, '
                                                   'not a placement — confirm from the document itself, then call place_document.',
     'input_schema': _obj('no input', {})},
    {'name': 'place_document', 'description': 'Place an unplaced (or wrongly placed) document into a CTD item. The program runs its technical PDF checks with the item\'s '
                                              'document class; the old entry is withdrawn with reason «placed».',
     'input_schema': _obj('placement', {'doc_id': S('document id'), 'slot_id': S('target slot id'), 'title': S('document title (optional)'),
                                        'rationale': S('one sentence: what in the document shows it belongs here')}, ['doc_id', 'slot_id', 'rationale'])},
    {'name': 'generate_document', 'description': 'Generate a program document (kinds: cover, tracking, composition, salt, cep_commitment, translation, stability_commitment, '
                                                 'justification, annex1, p51, p54, s41, s44). The program prefills what it knows; pass only the remaining fields in data. '
                                                 'The result is an UNSIGNED DRAFT the user must print, sign and upload; say so.',
     'input_schema': _obj('generator', {'kind': S('generator kind'), 'data': ANY, 'ctx': ANY, 'slot_id': S('slot id, needed for kind justification'),
                                        'rationale': S('why this document is needed now')}, ['kind', 'rationale'])},
    {'name': 'get_gate', 'description': 'Why export is blocked (missing required items, non-conforming documents, unsigned drafts, external-only references, '
                                        'blocking cross-checks) or ok.',
     'input_schema': _obj('no input', {})},
    {'name': 'run_review', 'description': 'Run the Regulatory Reviewer (deterministic checks of the eda.review pack: screening, quality, CADC, stability, BE, labelling, '
                                          'gates, international layer). Returns the run id, verdicts per department and counts. Then read the open findings with '
                                          'get_findings and judge them yourself from the documents.',
     'input_schema': _obj('options', {'strictness': S('eda | international | strict', enum=['eda', 'international', 'strict']),
                                      'departments': {'type': 'array', 'items': {'type': 'string'}, 'description': 'subset of departments; omit for all'}})},
    {'name': 'get_findings', 'description': 'Findings of a review run (latest when run_id is omitted), compact. Filter by dept, status (open|closed|…), verdict '
                                            '(adequate|deficient|not_assessable|not_applicable|needs_review), severity.',
     'input_schema': _obj('filter', {'run_id': S('review run id'), 'dept': S('department'), 'status': S('status'), 'verdict': S('verdict'), 'severity': S('severity'),
                                     'limit': I('max rows (default 60)')})},
    {'name': 'get_finding', 'description': 'One finding in full: the question (EN/AR), the deficiency wording, evidence found (documents, pages, excerpts), responses so far.',
     'input_schema': _obj('which finding', {'run_id': S('review run id'), 'finding_id': S('finding id')}, ['run_id', 'finding_id'])},
    {'name': 'act_on_finding', 'description': 'Record your assessment of a finding: action confirm (agree with the current verdict), override (set a verdict with a reason), '
                                              'withdraw, reopen or dismiss_ai. Your assessment is marked as the assistant\'s and waits for the human reviewer\'s confirmation.',
     'input_schema': _obj('assessment', {'run_id': S('review run id'), 'finding_id': S('finding id'),
                                         'action': S('confirm | override | withdraw | reopen | dismiss_ai', enum=['confirm', 'override', 'withdraw', 'reopen', 'dismiss_ai']),
                                         'verdict': S('for override: adequate | deficient | not_assessable | not_applicable'),
                                         'reason': S('the evidence (document, page, what it states)')}, ['run_id', 'finding_id', 'action', 'reason'])},
    {'name': 'add_response', 'description': 'Draft the applicant\'s response to a deficiency (in the voice of a regulatory affairs professional, EN or AR as the user '
                                            'prefers), referencing the documents that answer it.',
     'input_schema': _obj('response', {'run_id': S('review run id'), 'finding_id': S('finding id'), 'text': S('the response text'),
                                       'doc_ids': {'type': 'array', 'items': {'type': 'string'}, 'description': 'documents that support the response'}},
                          ['run_id', 'finding_id', 'text'])},
    {'name': 'reassess_finding', 'description': 'Re-run the deterministic check of one finding after data or documents changed.',
     'input_schema': _obj('which finding', {'run_id': S('review run id'), 'finding_id': S('finding id')}, ['run_id', 'finding_id'])},
    {'name': 'make_review_letter', 'description': 'Produce the deficiency letter or the assessment report of a department for a run (DOCX stored on the run).',
     'input_schema': _obj('letter', {'run_id': S('review run id'), 'dept': S('department'), 'kind': S('letter | report', enum=['letter', 'report'])}, ['run_id', 'dept', 'kind'])},
    {'name': 'request_reissue', 'description': 'Open a request to an issuer for a conforming copy of a third-party document (certificate, licence…): the program drafts the '
                                               'request letter and marks the item «waiting on issuer».',
     'input_schema': _obj('request', {'slot_id': S('slot id'), 'issuer': S('issuer name'), 'lang': S('en | ar', enum=['en', 'ar']), 'due_days': I('days until follow-up (default 21)'),
                                      'reason': S('what is wrong with the current copy')}, ['slot_id', 'issuer', 'reason'])},
    {'name': 'get_audit', 'description': 'The last actions on this dossier (who did what, when).',
     'input_schema': _obj('limit', {'limit': I('rows (default 30)')})},
    {'name': 'get_document_rubric', 'description': 'The rules ONE document must satisfy: the review pack\'s questions for its CTD item (with sources and the deficiency wording) '
                                                   'plus general document rules (text layer, product named, signed, dated, validity, issuer). Start a document review here, then read the '
                                                   'document and call record_document_review.',
     'input_schema': _obj('which document', {'doc_id': S('document id')}, ['doc_id'])},
    {'name': 'record_document_review', 'description': 'Record your review of a document against its rubric: one finding per rule with verdict adequate | deficient | '
                                                      'not_assessable | not_applicable, where (page + short excerpt), what is wrong (finding) and the required change (change), '
                                                      'each in English and Arabic. Judge content: wording, values, consistency with the licence and the data, required statements.',
     'input_schema': _obj('review', {'doc_id': S('document id'), 'summary': S('two or three sentences: overall state of the document'),
                                     'findings': {'type': 'array', 'description': 'one per rule', 'items': {'type': 'object', 'properties': {
                                         'rule': S('rule id from the rubric'), 'verdict': S('adequate | deficient | not_assessable | not_applicable'),
                                         'severity': S('critical | major | minor | note (default: the rule\'s)'),
                                         'where': {'type': 'array', 'items': {'type': 'object', 'properties': {'page': I('page'), 'excerpt': S('≤ 40 words as printed')}}},
                                         'finding': {'type': 'object', 'properties': {'en': S('en'), 'ar': S('ar')}}, 'change': {'type': 'object', 'properties': {'en': S('en'), 'ar': S('ar')}}},
                                         'required': ['rule', 'verdict']}}}, ['doc_id', 'findings'])},
    {'name': 'amend_document', 'description': 'Amend a WORD document per the rules with TRACKED CHANGES: each edit quotes the paragraph to find (exact text or a unique '
                                              'passage) and gives the new text, the rule and the reason; ops replace | insert_after | delete. The program stores the result as a new '
                                              'unsigned draft version with a change log; the company accepts the changes in Word and signs. PDFs and third-party documents cannot be '
                                              'amended here: use amendment_memo (and request_reissue for third-party documents); program-generated documents: fix the data and generate again.',
     'input_schema': _obj('edits', {'doc_id': S('document id (.docx)'), 'edits': {'type': 'array', 'items': {'type': 'object', 'properties': {
                                        'op': S('replace | insert_after | delete', enum=['replace', 'insert_after', 'delete']), 'find': S('paragraph text to locate'),
                                        'text': S('new text (replace / insert_after)'), 'rule': S('rule id'), 'reason': S('why, one sentence')}, 'required': ['op', 'find']}},
                                    'rationale': S('one sentence: which review findings these edits answer')}, ['doc_id', 'edits', 'rationale'])},
    {'name': 'amendment_memo', 'description': 'Write an amendment memo (DOCX) for a document that is not edited here (a PDF without a Word source, or a third-party document '
                                              'that must be re-issued): rule · where · finding · required change per item. Stored next to the dossier\'s files, linked to the document.',
     'input_schema': _obj('memo', {'doc_id': S('document id'), 'lang': S('en | ar', enum=['en', 'ar']), 'to': S('addressee (issuer or author), optional'),
                                   'items': {'type': 'array', 'items': {'type': 'object', 'properties': {'rule': S('rule id'), 'where': S('page / section'), 'finding': S('what is wrong'),
                                                                                                         'change': S('what must change')}, 'required': ['rule', 'change']}},
                                   'rationale': S('one sentence')}, ['doc_id', 'items', 'rationale'])},
    {'name': 'drive_list', 'description': 'List the files of a Google Drive folder link (or one file link) the company shared: name, type, size, whether the program can '
                                          'read it (PDF, Word, images, Google Docs). Use recursive for sub-folders.',
     'input_schema': _obj('link', {'link': S('Google Drive folder or file link'), 'recursive': B('also list sub-folders (≤ 3 levels)')}, ['link'])},
    {'name': 'drive_fetch', 'description': 'Read a Drive file into the dossier as an unplaced document (Google Docs are exported to Word); then read_document and '
                                           'place_document as with any file.',
     'input_schema': _obj('file', {'file_id': S('Drive file id from drive_list'), 'name': S('file name as listed'), 'mime': S('mimeType as listed'),
                                   'rationale': S('why this file is needed')}, ['file_id', 'rationale'])},
    {'name': 'export_dossier', 'description': 'Export the dossier (CTD folder, eCTD 3.2.2, eCTD 4.0). REQUIRES THE USER\'S APPROVAL: the program asks them before this runs. '
                                              'Call it only when get_gate says ok (or the user asked to export anyway with acknowledge_provisional).',
     'input_schema': _obj('export', {'outputs': {'type': 'array', 'items': {'type': 'string', 'enum': ['ctd', 'ectd32', 'ectd40']}, 'description': 'outputs; default all three'},
                                     'acknowledge_provisional': B('the user accepts that the EG eCTD profiles are provisional'),
                                     'rationale': S('why the dossier is ready')}, ['rationale'])},
    {'name': 'sign_review', 'description': 'Sign a review run as assessor or peer reviewer. REQUIRES THE USER\'S APPROVAL; the signature is the user\'s, not yours.',
     'input_schema': _obj('signature', {'run_id': S('review run id'), 'role': S('assessor | peer', enum=['assessor', 'peer']), 'by': S('the signer\'s name'),
                                        'rationale': S('why the run is complete')}, ['run_id', 'role', 'by', 'rationale'])},
    {'name': 'get_draft_template', 'description': 'What ONE dossier document must look like and what the program knows for it: the template (sections with kind para|list|table|fields, '
                                                   'columns, fields, hints EN/AR), the requirement\'s acceptance text, which base documents are present, their texts (excerpts) and the product data. '
                                                   'Items with draft none (third-party / EDA documents) are never drafted: say so and offer a re-issue request. Call before draft_document.',
     'input_schema': _obj('item', {'slot_id': S('the slot id from get_board')}, ['slot_id'])},
    {'name': 'draft_document', 'description': 'Make the document of an item from your answers to its template and store it in the item as an UNSIGNED WORD DRAFT the user reviews. '
                                              'answers = {"sections": {"<section id>": "text" | {"en","ar"} | ["bullet", …] | {"rows": [[cell, …], …]} | {"<field key>": "value"}}, '
                                              '"gaps": [{"what","why","ar"}], "sources": {"<section id>": "file name"}, "notes": "…"}. Use only facts from the documents and the data; '
                                              'write […] for anything unknown and list it in gaps. lang: en | ar (the edition of the Word file).',
     'input_schema': _obj('draft', {'slot_id': S('the slot id'), 'answers': {'type': 'object', 'description': 'your filled template, see the description'}, 'lang': S('en | ar'),
                                    'rationale': S('one line: which documents you drew on')}, ['slot_id', 'answers', 'rationale'])},
    {'name': 'withdraw_document', 'description': 'Withdraw a document from its item (kept in history, can be restored). REQUIRES THE USER\'S APPROVAL.',
     'input_schema': _obj('withdrawal', {'doc_id': S('document id'), 'reason': S('why')}, ['doc_id', 'reason'])},
]
BY_NAME = {t['name']: t for t in SPECS}


# ---------------- helpers
def _pages(spec, n):
    """"a-b" (1-based) → (a, b) within 1..n, at most MAX_PAGES."""
    if not spec:
        return 1, min(n, MAX_PAGES)
    m = re.fullmatch(r'\s*(\d+)\s*(?:-\s*(\d+))?\s*', str(spec))
    if not m:
        raise ToolError('pages must look like "1-5"')
    a = max(1, int(m.group(1)))
    b = int(m.group(2)) if m.group(2) else a
    a, b = min(a, n), min(max(a, b), n)
    if b - a + 1 > MAX_PAGES:
        b = a + MAX_PAGES - 1
    return a, b


def _subpdf(data, a, b):
    from pypdf import PdfReader, PdfWriter
    rd = PdfReader(io.BytesIO(data), strict=False)
    w = PdfWriter()
    for i in range(a - 1, min(b, len(rd.pages))):
        w.add_page(rd.pages[i])
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def _doc_summary(d):
    return {'id': d['id'], 'filename': d['filename'], 'title': d.get('title'), 'version': d.get('version'), 'slot_id': d.get('slot_id'),
            'check_status': d.get('check_status'), 'findings': [{'code': f.get('code'), 'severity': f.get('severity'), 'en': f.get('en')} for f in (d.get('findings') or [])][:8],
            'valid_until': (d.get('meta') or {}).get('valid_until'), 'draft_unsigned': bool((d.get('meta') or {}).get('draft_unsigned')),
            'external': bool((d.get('meta') or {}).get('external')), 'generated': (d.get('meta') or {}).get('generated')}


def _title(t):
    return t.get('en') if isinstance(t, dict) else t


def _check(ctx, status, body, what):
    if status >= 400:
        det = body.get('detail') if isinstance(body, dict) else None
        msg = (det.get('en') if isinstance(det, dict) else None) or (json.dumps(det, ensure_ascii=False) if det else None) or body.get('text') if isinstance(body, dict) else str(body)
        raise ToolError(f'{what} failed ({status}): {msg}')
    return body


def _merge(base, patch):
    out = dict(base or {})
    for k, v in (patch or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


# ---------------- executors
def run_tool(ctx, name, args):
    """→ {'content': str | [blocks], 'attach': [blocks]}; raises ToolError for a result Claude should see as an error."""
    fn = globals().get('t_' + name)
    if fn is None or name not in BY_NAME:
        raise ToolError(f'unknown tool {name}')
    args = dict(args or {})
    if name in WRITES:
        ctx.st.audit(ctx.did, 'assistant.tool', tool=name, args={k: v for k, v in args.items() if k not in ('data', 'profile', 'note', 'text')} | (
            {'keys': sorted((args.get('data') or {}).keys())} if isinstance(args.get('data'), dict) else {}), rationale=args.get('rationale') or args.get('reason'))
    out = fn(ctx, **args) if isinstance(args, dict) else fn(ctx)
    if isinstance(out, dict) and 'content' in out:
        return out
    return {'content': json.dumps(out, ensure_ascii=False, default=str) if not isinstance(out, str) else out, 'attach': []}


def t_get_dossier(ctx):
    d = ctx.st.dossier(ctx.did)
    b = ctx.st.board(ctx.did)
    return {'id': d['id'], 'name': d['name'], 'product': d['product'], 'envelope': d['envelope'], 'profile': d['profile'], 'pack': d['pack'],
            'counts': b['counts'], 'unassigned_documents': len(b['unassigned']), 'created': d.get('created')}


def t_get_board(ctx, only_open=False):
    b = ctx.st.board(ctx.did)
    open_states = {'not_started', 'waiting', 'non_conforming', 'needs_attention', 'received'}
    slots = []
    for s in b['slots']:
        if s['status'] == 'not_applicable':
            continue
        if only_open and s['status'] not in open_states:
            continue
        slots.append({'slot_id': s['slot_id'], 'ctd': s['ctd'], 'title': _title(s['title']), 'level': s['level'], 'status': s['status'],
                      'documents': [{'id': d['id'], 'filename': d['filename'], 'version': d['version'], 'check_status': d['check_status'],
                                     'findings': len(d['findings']), 'draft_unsigned': bool(d['meta'].get('draft_unsigned'))} for d in s['documents']],
                      'cross_findings': len(s.get('cross') or []), 'waiting_on_issuer': bool(s.get('request'))})
    return {'slots': slots, 'unassigned': [{'id': d['id'], 'filename': d['filename'], 'title': d.get('title')} for d in b['unassigned']], 'counts': b['counts']}


def t_get_slot(ctx, slot_id):
    b = ctx.st.board(ctx.did)
    s = next((x for x in b['slots'] if x['slot_id'] == slot_id), None)
    if not s:
        raise ToolError(f'unknown slot {slot_id}')
    docs = [_doc_summary(ctx.st.document(d['id'])) for d in s['documents']]
    return {**_s(s, ('slot_id', 'req_id', 'ctd', 'ectd', 'level', 'doc_class', 'module', 'status', 'reasons', 'acceptance', 'sources', 'how', 'produced_by', 'provenance')),
            'title': s['title'], 'documents': docs, 'cross': s.get('cross'), 'request': s.get('request')}


def t_get_data(ctx):
    return ctx.st.dossier(ctx.did)['data'] or {}


def t_put_data(ctx, data, rationale):
    if not isinstance(data, dict):
        raise ToolError('data must be an object')
    cur = ctx.st.dossier(ctx.did)['data'] or {}
    status, body = ctx.call('PUT', f'/api/dossiers/{ctx.did}/data', json=_merge(cur, data))
    _check(ctx, status, body, 'put_data')
    cross = body.get('cross') or []
    return {'saved_keys': sorted(data.keys()), 'cross_findings': [{'id': f.get('id'), 'severity': f.get('severity'), 'en': f.get('en')} for f in cross][:20]}


def t_set_profile(ctx, profile, rationale):
    if not isinstance(profile, dict):
        raise ToolError('profile must be an object')
    cur = ctx.st.dossier(ctx.did)['profile'] or {}
    status, body = ctx.call('PUT', f'/api/dossiers/{ctx.did}/profile', json=_merge(cur, profile))
    _check(ctx, status, body, 'set_profile')
    return body


def t_read_document(ctx, doc_id, pages=None):
    d = ctx.st.document(doc_id)
    if d['dossier_id'] != ctx.did:
        raise ToolError('document not in this dossier')
    if d['meta'].get('external'):
        raise ToolError('external reference: no file stored; its link is ' + str(d['meta'].get('url')))
    if d.get('doc_class') in set(ctx.never_send or []):
        raise ToolError(f"documents of class {d['doc_class']} are not sent to Claude by the company's settings; ask the user to read it")
    data = ctx.st.blob_path(d['sha256']).read_bytes()
    name = d['filename']
    notes = storage.readings(ctx.st, ctx.did, doc_id)
    head = [f"document: {name} (id {doc_id}, slot {d.get('slot_id')}, class {d.get('doc_class')}, status {d.get('check_status')})"]
    if notes:
        head.append('saved readings:\n' + '\n'.join(f"- [{n['pages'] or 'all'}] {n['note']}" for n in notes[-5:]))
    attach, text = [], ''
    low = name.lower()
    if data[:4] == b'%PDF':
        from pypdf import PdfReader
        try:
            n = len(PdfReader(io.BytesIO(data), strict=False).pages)
        except Exception:
            n = 1
        a, b = _pages(pages, n)
        part = _subpdf(data, a, b) if (a, b) != (1, n) else data
        rt = extract.read_text(name, part, max_pages=MAX_PAGES)
        text = rt['text']
        head.append(f'pages {a}-{b} of {n}' + (' (scan: no text layer' + (', OCR text below' if rt['ocr'] else ', read the attached pages') + ')' if rt['scanned'] else ''))
        if len(part) <= MAX_ATTACH:
            attach.append({'type': 'document', 'title': f'{name} p.{a}-{b}', 'source': {'type': 'base64', 'media_type': 'application/pdf', 'data': base64.standard_b64encode(part).decode()}})
        else:
            head.append('(too large to attach as pages; text only)')
    elif extract.word_kind(data):
        text = extract.read_text(name, data)['text']
        head.append('Word document: text below')
    else:
        from .. import arabic
        mt = arabic.image_type(data)
        if mt:
            text = extract.read_text(name, data)['text']
            attach.append({'type': 'image', 'source': {'type': 'base64', 'media_type': mt, 'data': base64.standard_b64encode(data).decode()}})
            head.append('image: attached')
        else:
            raise ToolError('unsupported file type')
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT] + f'\n… [{len(text) - MAX_TEXT} more characters; ask for a smaller page range]'
    return {'content': '\n'.join(head) + ('\n\n--- text ---\n' + text if text.strip() else '\n\n(no text layer: look at the attached pages)'), 'attach': attach}


def t_save_reading(ctx, doc_id, note, pages=None):
    d = ctx.st.document(doc_id)
    if d['dossier_id'] != ctx.did:
        raise ToolError('document not in this dossier')
    rid = storage.add_reading(ctx.st, ctx.did, doc_id, pages, str(note)[:2000])
    return {'saved': rid}


def t_get_readings(ctx, doc_id=None):
    return [{'doc_id': r['doc_id'], 'pages': r['pages'], 'note': r['note'], 'created': r['created']} for r in storage.readings(ctx.st, ctx.did, doc_id)]


def t_classify_unassigned(ctx):
    from ..classify import Classifier
    from pypdf import PdfReader
    d = ctx.st.dossier(ctx.did)
    clf = Classifier(ctx.st.pack(d['pack']))
    slots = ctx.st.slots(ctx.did)
    out = []
    for doc in ctx.st.board(ctx.did)['unassigned']:
        data = ctx.st.blob_path(doc['sha256']).read_bytes()
        text = ''
        try:
            rd = PdfReader(io.BytesIO(data), strict=False)
            text = ' '.join((p.extract_text() or '') for p in rd.pages[:1])
        except Exception:
            pass
        out.append({'doc_id': doc['id'], 'filename': doc['filename'], 'suggestions': clf.suggest(doc['filename'], text, slots)[:5]})
    return out


def t_place_document(ctx, doc_id, slot_id, rationale, title=None):
    d = ctx.st.document(doc_id)
    if d['dossier_id'] != ctx.did:
        raise ToolError('document not in this dossier')
    if d['meta'].get('external'):
        raise ToolError('an external reference cannot be placed; upload its file')
    data = ctx.st.blob_path(d['sha256']).read_bytes()
    meta = {k: v for k, v in d['meta'].items() if k not in ('placed_from',)}
    meta.update({'placed_by': 'assistant', 'placed_from': d.get('slot_id'), 'rationale': rationale})
    try:
        ctx.st.check_item_meta(ctx.did, slot_id, meta)              # the leaflet / a study: the user places it from the board with its details
        new = ctx.st.add_document(ctx.did, slot_id, d['filename'], data, title or d.get('title'), meta)
    except Exception as e:                                    # StoreError carries en/ar
        raise ToolError(getattr(e, 'en', None) or str(e))
    if d['state'] == 'current':
        ctx.st.withdraw(ctx.did, doc_id, 'placed')
    return {'placed': _doc_summary(new), 'note': 'technical check ran with the item\'s document class; findings above if any'}


def t_generate_document(ctx, kind, rationale, data=None, ctx_=None, slot_id=None, **kw):
    ctx_ = ctx_ if ctx_ is not None else kw.get('ctx') or {}
    status, pre = ctx.call('GET', f'/api/dossiers/{ctx.did}/generate/{kind}/prefill', params={'slot_id': slot_id} if slot_id else None)
    _check(ctx, status, pre, 'prefill')
    merged = {**(pre.get('data') or {}), **(data or {})}
    status, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/generate/{kind}', json={'data': merged, 'ctx': ctx_ or {}, 'slot_id': slot_id})
    _check(ctx, status, body, 'generate')
    return {'document': _doc_summary(body), 'unsigned_draft': bool((body.get('meta') or {}).get('draft_unsigned')),
            'next': 'the user prints, signs and uploads the signed PDF; the program then replaces the draft'}


def t_get_draft_template(ctx, slot_id):
    status, body = ctx.call('GET', f'/api/dossiers/{ctx.did}/slots/{slot_id}/template')
    _check(ctx, status, body, 'template')
    from ..generate import draft as _draft
    tpl = body.get('template') or {}
    if tpl.get('draft') not in ('full', 'partial'):
        return {'draftable': False, 'draft': tpl.get('draft'), 'example': tpl.get('example'), 'requirement': body.get('requirement'),
                'next': 'this document is issued by a third party / EDA or made by a generator: ask for the upload, or request_reissue; generate_document for generator kinds'}
    slot = next(s for s in ctx.st.slots(ctx.did) if s.slot_id == slot_id)
    ctx_ = _draft.context(ctx.st, ctx.did, slot, with_texts=True)
    return {'draftable': True, 'template': {k: tpl.get(k) for k in ('id', 'kind', 'draft', 'lang', 'letterhead', 'sections', 'note')}, 'requirement': body.get('requirement'),
            'inputs': body.get('inputs'), 'product_data': {k: ctx_.get(k) for k in ('product', 'profile', 'apis', 'composition', 'batches', 'specs', 'results', 'packs', 'registration', 'readings')},
            'documents': [{'filename': d['filename'], 'slot_id': d.get('slot_id'), 'text': d['text'][:6000]} for d in ctx_.get('documents', [])],
            'next': 'fill every section from the documents and the data, […] where unknown, then draft_document'}


def t_draft_document(ctx, slot_id, answers, rationale, lang=None):
    status, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/slots/{slot_id}/draft', json={'answers': answers, 'lang': lang or 'en', 'ai': False})
    _check(ctx, status, body, 'draft')
    return {'document': _doc_summary(body['document']), 'gaps': body.get('gaps'), 'unsigned_draft': True,
            'next': 'tell the user what is in the draft and what is still missing; the user reviews, completes, prints and signs where the template says so'}


def t_get_gate(ctx):
    return ctx.st.gate(ctx.did)


def t_run_review(ctx, strictness='international', departments=None):
    status, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/review', json={'strictness': strictness, 'departments': departments, 'ai': False, 'actor': 'claude'})
    _check(ctx, status, body, 'run_review')
    run, findings = body['run'], body['findings']
    return {'run_id': run['id'], 'verdict': run.get('verdict'), 'dept_verdicts': run.get('dept_verdicts'), 'counts': run.get('counts'),
            'open_findings': sum(1 for f in findings if f.get('status') == 'open'), 'next': 'call get_findings to see them'}


def _latest_run_id(ctx):
    status, body = ctx.call('GET', f'/api/dossiers/{ctx.did}/review/latest')
    _check(ctx, status, body, 'latest run')
    return body['run']['id'] if body.get('run') else None


def t_get_findings(ctx, run_id=None, dept=None, status=None, verdict=None, severity=None, limit=60):
    rid = run_id or _latest_run_id(ctx)
    if not rid:
        raise ToolError('no review run yet: call run_review')
    params = {k: v for k, v in dict(dept=dept, status=status, verdict=verdict, severity=severity).items() if v}
    st_, body = ctx.call('GET', f'/api/dossiers/{ctx.did}/review/{rid}', params=params or None)
    _check(ctx, st_, body, 'get_findings')
    rows = body['findings'][: int(limit or 60)]
    return {'run_id': rid, 'verdict': body['run'].get('verdict'), 'total': len(body['findings']),
            'findings': [{'id': f['id'], 'question_id': f['question_id'], 'dept': f['dept'], 'ctd': f['ctd'], 'severity': f['severity'], 'verdict': f['verdict'],
                          'status': f['status'], 'title': _title(f['payload'].get('title')), 'slot_id': f.get('slot_id'),
                          'needs_review': bool(f['payload'].get('needs_review')), 'evidence': len(f['payload'].get('evidence') or [])} for f in rows]}


def t_get_finding(ctx, run_id, finding_id):
    st_, body = ctx.call('GET', f'/api/dossiers/{ctx.did}/review/{run_id}')
    _check(ctx, st_, body, 'get_finding')
    f = next((x for x in body['findings'] if x['id'] == finding_id), None)
    if not f:
        raise ToolError('finding not found in that run')
    p = f['payload']
    return {'id': f['id'], 'question_id': f['question_id'], 'dept': f['dept'], 'ctd': f['ctd'], 'severity': f['severity'], 'verdict': f['verdict'], 'status': f['status'],
            'slot_id': f.get('slot_id'), 'title': p.get('title'), 'question': p.get('question'), 'deficiency': p.get('deficiency'), 'adequate': p.get('adequate'),
            'source': p.get('source'), 'evidence': p.get('evidence'), 'detail': p.get('detail'), 'ai': p.get('ai'), 'override': f.get('override'),
            'confirmed_by': f.get('confirmed_by'), 'responses': f.get('responses')}


def t_act_on_finding(ctx, run_id, finding_id, action, reason, verdict=None):
    st_, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/review/{run_id}/findings/{finding_id}', json={'action': action, 'verdict': verdict, 'reason': reason, 'by': 'claude'})
    _check(ctx, st_, body, 'act_on_finding')
    return {'finding': {k: body.get(k) for k in ('id', 'verdict', 'status', 'confirmed_by', 'override')} if isinstance(body, dict) else body,
            'note': 'recorded as the assistant\'s assessment; the human reviewer confirms it in the Review screen'}


def t_add_response(ctx, run_id, finding_id, text, doc_ids=None):
    st_, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/review/{run_id}/findings/{finding_id}/responses', json={'text': text, 'doc_ids': doc_ids or [], 'by': 'claude'})
    _check(ctx, st_, body, 'add_response')
    return body


def t_reassess_finding(ctx, run_id, finding_id):
    st_, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/review/{run_id}/findings/{finding_id}/reassess', json={})
    _check(ctx, st_, body, 'reassess')
    return body


def t_make_review_letter(ctx, run_id, dept, kind):
    path = 'letters' if kind == 'letter' else 'reports'
    st_, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/review/{run_id}/{path}/{dept}', json={})
    _check(ctx, st_, body, 'make_review_letter')
    return body


def t_request_reissue(ctx, slot_id, issuer, reason, lang='en', due_days=21):
    st_, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/slots/{slot_id}/request', json={'issuer': issuer, 'lang': lang, 'due_days': int(due_days or 21)})
    _check(ctx, st_, body, 'request_reissue')
    return body


def t_get_audit(ctx, limit=30):
    rows = ctx.st.db.execute('select ts, event, detail, actor from audit where dossier_id=? order by id desc limit ?', (ctx.did, int(limit or 30))).fetchall()
    return [{'when': time.strftime('%Y-%m-%d %H:%M', time.localtime(r['ts'])), 'actor': r['actor'], 'event': r['event'], 'detail': json.loads(r['detail'])} for r in rows]


def t_export_dossier(ctx, rationale, outputs=None, acknowledge_provisional=False):
    st_, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/export', json={'outputs': outputs or ['ctd', 'ectd32', 'ectd40'], 'acknowledge_provisional': bool(acknowledge_provisional)})
    _check(ctx, st_, body, 'export')
    return body


def t_sign_review(ctx, run_id, role, by, rationale):
    st_, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/review/{run_id}/sign', json={'role': role, 'by': by})
    _check(ctx, st_, body, 'sign_review')
    return body


def t_withdraw_document(ctx, doc_id, reason):
    st_, body = ctx.call('POST', f'/api/dossiers/{ctx.did}/documents/{doc_id}/withdraw', params={'reason': reason})
    _check(ctx, st_, body, 'withdraw')
    return _doc_summary(body) if isinstance(body, dict) and body.get('id') else body


# ---------------- one document: review per the rules, amend per the rules
def t_get_document_rubric(ctx, doc_id):
    from ..review import docreview
    try:
        rb = docreview.rubric(ctx.st, ctx.did, doc_id)
    except KeyError:
        raise ToolError('document not in this dossier')
    prev = docreview.latest(ctx.st, doc_id)
    rb['rules'] = [{k: r[k] for k in ('id', 'kind', 'dept', 'severity', 'title', 'question', 'deficiency', 'source') if k in r} for r in rb['rules']]
    rb['previous_review'] = prev and {'origin': prev['origin'], 'verdict': prev['verdict'], 'counts': prev['counts'], 'created': prev['created']}
    rb['how_to_amend'] = ('amend_document (Word, tracked changes)' if rb['document']['is_docx'] else 'amendment_memo + request_reissue (third-party)' if rb['document']['third_party']
                          else 'put_data + generate_document' if rb['document']['generated'] else 'amendment_memo (PDF without a Word source)')
    return rb


def t_record_document_review(ctx, doc_id, findings, summary=None):
    from ..review import docreview
    try:
        rv = docreview.record(ctx.st, ctx.did, doc_id, findings, summary, actor='claude', origin='assistant')
    except KeyError:
        raise ToolError('document not in this dossier')
    except ValueError as e:
        raise ToolError(str(e))
    return {'review_id': rv['id'], 'verdict': rv['verdict'], 'counts': rv['counts']}


def t_amend_document(ctx, doc_id, edits, rationale):
    from ..generate import amend
    d = ctx.st.document(doc_id)
    if d['dossier_id'] != ctx.did:
        raise ToolError('document not in this dossier')
    if d.get('doc_class') in ('third_party_certificate', 'eda_document'):
        raise ToolError('a third-party document is never altered: write an amendment_memo and request_reissue')
    data = ctx.st.blob_path(d['sha256']).read_bytes()
    fname, wk = d['filename'], extract.word_kind(data)
    if wk == 'doc':                                     # the old Word format: tracked changes need .docx, LibreOffice converts it
        from ..generate.docx_kit import find_soffice, to_docx
        if not find_soffice():
            raise ToolError('an old-format Word file (.doc): open it in Word, save it as .docx and upload that (then amend_document), or write an amendment_memo')
        try:
            data, fname = to_docx(data), fname.rsplit('.', 1)[0] + '.docx'
        except Exception as e:
            raise ToolError(f'could not convert the .doc to .docx ({e}): save it as .docx in Word and upload that')
    elif wk != 'docx':
        raise ToolError('not a Word document: use amendment_memo (or put_data + generate_document for a generated document)')
    try:
        out, log = amend.apply_edits(data, edits)
    except amend.AmendError as e:
        raise ToolError(str(e))
    meta = {k: v for k, v in d['meta'].items() if k not in ('amended_from', 'change_log')}
    meta.update({'amended_from': doc_id, 'change_log': log, 'draft_unsigned': True, 'amended_by': 'assistant', 'rationale': rationale})
    try:
        new = ctx.st.add_document(ctx.did, d['slot_id'], fname, out, d.get('title'), meta, supersede=doc_id)
    except Exception as e:
        raise ToolError(getattr(e, 'en', None) or str(e))
    return {'document': _doc_summary(new), 'changes': len(log), 'next': 'the company opens the Word file, accepts the tracked changes, signs and uploads the signed PDF'}


def t_amendment_memo(ctx, doc_id, items, rationale, lang='en', to=None):
    import tempfile, pathlib
    from ..generate import amend
    d = ctx.st.document(doc_id)
    if d['dossier_id'] != ctx.did:
        raise ToolError('document not in this dossier')
    if not items:
        raise ToolError('no items')
    product = (ctx.st.dossier(ctx.did).get('product') or {}).get('name')
    tmp = pathlib.Path(tempfile.mkdtemp())
    try:
        p = amend.memo(items, d['filename'], product, tmp / 'memo.docx', lang=lang or 'en', to=to)
        data = p.read_bytes()
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    name = f"Amendment memo - {d['filename'].rsplit('.', 1)[0]}.docx"
    memo = storage.stage_document(ctx.st, ctx.did, name, data, title=name, meta={'memo_for': doc_id, 'kind': 'amendment_memo', 'rationale': rationale, 'items': len(items)})
    return {'memo': {'id': memo['id'], 'filename': memo['filename']}, 'items': len(items), 'next': 'the user downloads the memo from the document\'s panel and sends it to the author or issuer'}


# ---------------- Google Drive as a source
def t_drive_list(ctx, link, recursive=False):
    from .. import drive as _drive
    lk = _drive.parse_link(link)
    if not lk:
        raise ToolError('not a Google Drive folder or file link')
    d = _drive.Drive(_drive.load(ctx.st.root))
    try:
        if lk['kind'] == 'folder':
            files = ctx.run_async(d.list_folder(lk['id'], bool(recursive)))
        else:
            m = ctx.run_async(d.meta(lk['id']))
            files = [m] if m else [{'id': lk['id'], 'name': lk['id'], 'mimeType': 'application/pdf', 'kind': 'file', 'usable': True, 'path': lk['id']}]
    except _drive.DriveError as e:
        raise ToolError(e.en)
    return {'mode': d.mode, 'files': [{k: f.get(k) for k in ('id', 'name', 'mimeType', 'size', 'modified', 'kind', 'usable', 'path')} for f in files][:200]}


def t_drive_fetch(ctx, file_id, rationale, name=None, mime=None):
    from .. import drive as _drive
    d = _drive.Drive(_drive.load(ctx.st.root))
    try:
        fname, data, mt = ctx.run_async(d.fetch(file_id, name, mime))
    except _drive.DriveError as e:
        raise ToolError(e.en)
    doc = storage.stage_document(ctx.st, ctx.did, fname, data, meta={'from_drive': file_id, 'rationale': rationale})
    return {'document': {'id': doc['id'], 'filename': fname, 'bytes': len(data)}, 'next': 'read_document, then place_document into its CTD item'}
