"""«Make it for me»: a draft of any authored dossier document, built from the template library, the product data and the base
documents the company uploaded (their texts and saved readings). The model fills the template (claude.ai's built-in model in the
browser edition, the Anthropic API on a server with a key); without a model the program fills what it knows from the data and
marks the rest as gaps. The result is a Word draft stored in the item as an unsigned version, with the list of gaps.

Template library: rulepacks/eda.ctd.nta065.v5/templates/library.yaml (see its header)."""
import datetime as _dt
import json
import os
import re
from pathlib import Path

import yaml

from dossier_engine.yamlfast import load as yload

from .docx_kit import new_doc, para, table, _has_ar

PACK = Path(__file__).resolve().parents[3] / 'rulepacks' / 'eda.ctd.nta065.v5'
LIB_FILE = PACK / 'templates' / 'library.yaml'
_LIB = None
ASK = None                      # tests / other hosts: a callable(prompt: str) -> dict replaces the Anthropic call
MAX_DOC_CHARS = 9000            # of one base document's text in the prompt
MAX_CONTEXT_CHARS = 60000
GAP = '[…]'


def library():
    global _LIB
    if _LIB is None:
        _LIB = {e['id']: e for e in yload(LIB_FILE.read_text(encoding='utf-8'))}
    return _LIB


THIRD = ('third_party_certificate', 'eda_document', 'executed_record', 'signed_scan')
_T = lambda en, ar: {'en': en, 'ar': ar}                                                   # noqa: E731


def derived(req):
    """The entry of an item the library does not describe — another authority's Module 1, the common CTD's own sections — made from
    the requirement's own words: its title and what its section must hold. A certificate is uploaded as issued; a letter or a
    declaration is drafted whole; a technical section gets its structure and what the documents give."""
    acc, cls, title = req.get('acceptance_text') or '', req.get('doc_class'), req['title']
    e = {'id': req['id'], 'lang': 'en', 'example': {'en': acc, 'ar': ''}, 'derived': True}
    if cls in THIRD:
        return {**e, 'kind': 'third_party', 'draft': 'none',
                'note': _T('Uploaded as issued, never re-typed; the program checks it and can open a re-issue request to the issuer.',
                           'يُرفع كما صدر ولا يُعاد كتابته؛ البرنامج يفحصه ويقدر يفتح طلب إعادة إصدار للجهة.')}
    hint = _T(acc, '')
    if cls == 'generated':
        return {**e, 'kind': 'toc', 'draft': 'full', 'sections': [
            {'id': 'contents', 'title': _T('Contents', 'المحتويات'), 'kind': 'table', 'columns': ['Section', 'Document', 'Location'], 'hint': hint}]}
    if cls == 'company_letter':
        return {**e, 'kind': 'letter', 'draft': 'full', 'letterhead': True, 'sections': [
            {'id': 'addressee', 'title': _T('Addressed to', 'موجَّه إلى'), 'kind': 'para', 'hint': _T('The authority, and the department it asks to be addressed.', 'الهيئة والإدارة اللي بتطلب المخاطبة عليها.')},
            {'id': 'subject', 'title': _T('Subject', 'الموضوع'), 'kind': 'para', 'source': 'product', 'hint': _T(f"{title['en']} — trade name, dosage form, strength.", f"{title['ar']} — الاسم التجاري، الشكل الصيدلي، التركيز.")},
            {'id': 'body', 'title': _T('Text', 'النص'), 'kind': 'para', 'hint': hint},
            {'id': 'enclosures', 'title': _T('Enclosures', 'المرفقات'), 'kind': 'list', 'hint': _T('What is attached to this document, one per line.', 'المرفقات، كل واحد في سطر.')},
            {'id': 'signature', 'title': _T('Signature', 'التوقيع'), 'kind': 'fields', 'fields': [
                {'key': 'signatory', 'label': _T('Name', 'الاسم')}, {'key': 'signatory_title', 'label': _T('Position', 'الوظيفة')},
                {'key': 'applicant', 'label': _T('Company', 'الشركة')}, {'key': 'date', 'label': _T('Date', 'التاريخ')}]}]}
    return {**e, 'kind': 'section', 'draft': 'partial', 'sections': [
        {'id': 'content', 'title': title, 'kind': 'para', 'hint': hint},
        {'id': 'references', 'title': _T('Supporting documents and references', 'المستندات المؤيدة والمراجع'), 'kind': 'list',
         'hint': _T('The documents this section rests on, one per line.', 'المستندات اللي القسم ده مبني عليها، كل واحد في سطر.')}]}


def template(req_id, req=None):
    """The library's entry; for an item it does not describe, one made from the requirement itself when `req` is given."""
    return library().get(req_id) or (derived(req) if req else None)


def _req(st, did, req_id):
    return st.pack(st.dossier(did)['pack']).by_id.get(req_id)


def summary():
    """For the board: per requirement, can the program draft it, how, and with which generator — the library's items and, for every
    other authority's items, what their own words give."""
    from .. import packs
    out = {k: {'draft': e['draft'], 'kind': e['kind'], 'generator': e.get('generator'), 'lang': e.get('lang', 'en')} for k, e in library().items()}
    for m in packs.available():
        for r in packs.load(m['id']).requirements:
            if r['id'] not in out:
                e = derived(r)
                out[r['id']] = {'draft': e['draft'], 'kind': e['kind'], 'generator': None, 'lang': 'en'}
    return out


def lint():
    """Every requirement has an entry; draftable entries have sections with EN/AR titles; sections have known kinds."""
    reqs = yload((PACK / 'requirements.yaml').read_text(encoding='utf-8'))
    lib = library()
    problems = [f'{r["id"]}: no template entry' for r in reqs if r['id'] not in lib]
    problems += [f'{k}: not a requirement' for k in lib if k not in {r['id'] for r in reqs}]
    for k, e in lib.items():
        if e['draft'] not in ('full', 'partial', 'generator', 'none'):
            problems.append(f'{k}: draft={e["draft"]}')
        if e['draft'] in ('full', 'partial') and not e.get('sections'):
            problems.append(f'{k}: draftable without sections')
        for s in e.get('sections') or []:
            if s.get('kind') not in ('para', 'list', 'table', 'fields'):
                problems.append(f'{k}/{s.get("id")}: kind {s.get("kind")}')
            if not (s.get('title') or {}).get('en') or not (s.get('title') or {}).get('ar'):
                problems.append(f'{k}/{s.get("id")}: title EN/AR missing')
            if s.get('kind') == 'table' and not s.get('columns'):
                problems.append(f'{k}/{s.get("id")}: table without columns')
            if s.get('kind') == 'fields' and not s.get('fields'):
                problems.append(f'{k}/{s.get("id")}: fields without fields')
    return problems


# ---------------- context: what the program knows about this dossier and this item
def _texts(st, did, slot, inputs, budget):
    """Base documents: the item's own documents first, then documents whose type matches the template's inputs, then the rest."""
    from .. import extract
    docs = st.documents(did)
    want = set(inputs or [])
    def rank(d):
        meta = d.get('meta') or {}
        kind = meta.get('doc_type') or meta.get('kind') or ''
        return (0 if d.get('slot_id') == slot.slot_id else 1 if kind in want else 2, -(d.get('version') or 0))
    out, used = [], 0
    for d in sorted(docs, key=rank):
        if (d.get('meta') or {}).get('external') or d.get('state') not in (None, 'current'):
            continue
        if used >= budget:
            break
        try:
            data = st.blob_path(d['sha256']).read_bytes()
            rt = extract.read_text(d['filename'], data, max_pages=8)
            text = (rt.get('text') or '').strip()
        except Exception:
            text = ''
        if not text:
            continue
        text = text[:min(MAX_DOC_CHARS, budget - used)]
        used += len(text)
        out.append({'id': d['id'], 'filename': d['filename'], 'slot_id': d.get('slot_id'), 'doc_class': d.get('doc_class'), 'chars': len(text), 'text': text})
    return out


def context(st, did, slot, with_texts=True):
    from ..assistant import storage
    d = st.dossier(did)
    entry = template(slot.req_id) or {}
    product, profile, env, data = d.get('product') or {}, d.get('profile') or {}, d.get('envelope') or {}, d.get('data') or {}
    pk = st.pack(d['pack'])
    apis = data.get('apis') or profile.get('apis') or []
    ctx = {
        'dossier': {'id': did, 'name': d.get('name')},
        'product': {'trade_name': product.get('name'), 'dosage_form': product.get('dosageform') or product.get('dosage_form'), 'strength': product.get('strength'),
                    'pack': product.get('pack'), 'manufacturer': product.get('manufacturer'), 'manufacturer_country': product.get('manufacturer_country'),
                    'applicant': product.get('applicant') or env.get('applicant'), 'registration_number': product.get('registration_number') or env.get('registration_number'),
                    'shelf_life': product.get('shelf_life'), 'storage': product.get('storage'), 'route': product.get('route')},
        'profile': {k: profile.get(k) for k in ('dossier_kind', 'origin', 'licence', 'activity') if k in profile},
        'apis': apis, 'composition': data.get('composition') or [], 'batches': data.get('batches') or [], 'specs': data.get('specs') or data.get('specifications') or [],
        'results': data.get('results') or [], 'packs': data.get('packs') or [], 'registration': data.get('registration') or {},
        'item': slot.item, 'requirement': {'id': slot.req_id, 'title': slot.title, 'ctd': slot.ctd},
        'readings': [{'doc_id': n.get('doc_id'), 'note': n.get('note')} for n in storage.readings(st, did)][-20:],
        'date': _dt.date.today().isoformat(),
        'authority': {'id': pk.authority['id'], 'name': pk.authority['name']['en'], 'egypt': pk.egypt, 'country': env.get('country'),
                      'general': pk.meta.get('verified') is False, 'answers': profile.get('extra') or {}},
    }
    if with_texts:
        ctx['documents'] = _texts(st, did, slot, entry.get('inputs'), MAX_CONTEXT_CHARS)
    return ctx


def view(st, did, slot, req_item=None):
    """The template panel: the entry, the requirement's own words, which base documents are present, and the prompt the browser
    edition sends to claude.ai's model."""
    entry = template(slot.req_id, req_item or _req(st, did, slot.req_id))
    ctx = context(st, did, slot, with_texts=True)
    kinds_present = {(d.get('meta') or {}).get('doc_type') or (d.get('meta') or {}).get('kind') for d in st.documents(did)}
    inputs = [{'id': i, 'present': i in kinds_present} for i in (entry or {}).get('inputs') or []]
    out = {'req_id': slot.req_id, 'slot_id': slot.slot_id, 'template': entry, 'inputs': inputs, 'product': ctx.get('product'), 'date': ctx.get('date'),
           'examples': examples(entry) if entry else {}, 'prefill': deterministic(entry, ctx)['sections'] if entry and entry.get('sections') else {},
           'documents': [{k: v for k, v in dd.items() if k != 'text'} for dd in ctx.get('documents', [])],
           'requirement': {'title': slot.title, 'ctd': slot.ctd, 'acceptance': (req_item or {}).get('acceptance_text'), 'produced_by': (req_item or {}).get('produced_by'),
                           'rebuild': (req_item or {}).get('rebuild'), 'sources': (req_item or {}).get('sources')},
           'ai_server': bool(_server_key(st))}
    if entry and entry['draft'] in ('full', 'partial'):
        out['prompt'] = prompt(entry, ctx)
    return out


# ---------------- the model
def prompt(entry, ctx):
    secs = []
    for s in entry.get('sections') or []:
        line = f"- {s['id']} [{s['kind']}] {s['title']['en']} / {s['title']['ar']}"
        if s.get('hint'):
            line += f"\n    what: {s['hint'].get('en', '')}"
        if s.get('columns'):
            line += f"\n    columns: {s['columns']}"
        if s.get('fields'):
            line += "\n    fields: " + ', '.join(f"{f['key']} ({f['label']['en']})" for f in s['fields'])
        secs.append(line)
    docs = '\n\n'.join(f"=== Document {i + 1}: {d['filename']} (item {d.get('slot_id')})\n{d['text']}" for i, d in enumerate(ctx.get('documents') or []))
    data = {k: ctx.get(k) for k in ('product', 'profile', 'apis', 'composition', 'batches', 'specs', 'results', 'packs', 'registration', 'item', 'readings')}
    lang = entry.get('lang', 'en')
    au = ctx.get('authority') or {'egypt': True}
    if au.get('egypt'):
        whom, terms = 'the Egyptian Drug Authority (EDA)', 'the EDA / ICH terms; no marketing language; Arabic in formal Egyptian regulatory style'
    else:
        whom = au.get('name') or 'the authority of the country of registration'
        if au.get('country'):
            whom += f" (country of registration: {au['country']})"
        if au.get('answers'):
            whom += f"; the application: {json.dumps(au['answers'], ensure_ascii=False)}"
        terms = "the authority's own and the ICH terms; no marketing language; Arabic, where the document is in Arabic, in formal regulatory style"
        if au.get('general'):
            terms += ". The program does not hold this country's own Module 1 text: follow ICH and general practice, and say in \"notes\" what must be checked against the authority's checklist"
    return f"""You draft one document of a CTD registration dossier for {whom}, as a regulatory affairs professional would.
Document: {ctx['requirement']['id']} — {ctx['requirement']['title'].get('en')} / {ctx['requirement']['title'].get('ar')} (CTD {ctx['requirement']['ctd']}). Kind: {entry.get('kind')}.
Language of the document: {'English and Arabic (give both)' if lang == 'both' else 'Arabic' if lang == 'ar' else 'English'}.
Date: {ctx['date']}.

RULES
- Use only facts found in the product data and the base documents below. Never invent a number, a date, a name, a batch, a limit or a result.
- Where a required fact is not in the data or the documents, write the placeholder {GAP} in the text and list it in "gaps" (what is missing, which document would give it).
- Tables: rows as lists of strings in the order of the columns given; an unknown cell is "{GAP}".
- Regulatory wording: precise, formal, {terms}.
- Cite, per section, which document the facts came from (file name) in "sources".

TEMPLATE (section id [kind] title EN / AR):
{chr(10).join(secs)}

PRODUCT DATA (JSON):
{json.dumps(data, ensure_ascii=False)[:20000]}

BASE DOCUMENTS (their text as read from the files):
{docs or '(none uploaded yet)'}

Answer with ONE JSON object and nothing else:
{{"sections": {{"<section id>": <para/list: "text" or {{"en": "...", "ar": "..."}}; list: ["item", ...]; table: {{"rows": [["cell", ...], ...]}}; fields: {{"<key>": "value"}}>}},
 "gaps": [{{"what": "...", "why": "...", "ar": "..."}}], "sources": {{"<section id>": "file name"}}, "notes": "anything the reviewer must check"}}"""


def _server_key(st):
    try:
        from ..assistant import settings
        return settings.api_key(st.root)
    except Exception:
        return os.environ.get('ANTHROPIC_API_KEY')


def ask_model(st, text):
    """The model fills the template (server editions, with the company's key). Returns the parsed JSON or raises."""
    if ASK is not None:
        return ASK(text)
    key = _server_key(st)
    if not key:
        return None
    import anthropic
    from ..assistant import settings
    cfg = settings.load(st.root)
    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(model=cfg.get('model') or 'claude-opus-5-5', max_tokens=12000, messages=[{'role': 'user', 'content': text}])
    out = ''.join(b.text for b in msg.content if getattr(b, 'type', '') == 'text')
    return parse_answers(out)


def parse_answers(text):
    if isinstance(text, dict):
        return text
    s = str(text)
    try:
        return json.loads(s[s.index('{'):s.rindex('}') + 1])
    except ValueError:
        raise ValueError('the model did not return the expected JSON')


# ---------------- deterministic fill from the product data
def _s(v):
    return '' if v is None else str(v)


def _spec_rows(ctx):
    """specs as the data model keeps them: {'product': [...], 'api': [...] | {api name: [...]}} or a flat list → one list of {test, limit, method, reference}."""
    sp = ctx.get('specs') or []
    req = (ctx.get('requirement') or {}).get('id') or ''
    if isinstance(sp, list):
        return sp
    if not isinstance(sp, dict):
        return []
    if req.startswith('S-'):
        rows = []
        for k, v in sp.items():
            if k == 'product':
                continue
            if isinstance(v, list):
                rows += v
            elif isinstance(v, dict):
                for vv in v.values():
                    rows += vv if isinstance(vv, list) else []
        return rows
    return sp.get('product') or []


def deterministic(entry, ctx):
    """What the program can fill without a model: product fields and the API / composition / batch / specification / manufacturer
    tables, in the data model's own keys (composition: name|ingredient, standard, amount, role; batches: no, size, date, scale, site;
    specs: test, limit, method; results: {batch no: {test: value}})."""
    out, gaps = {}, []
    p = ctx.get('product') or {}
    results = ctx.get('results') or {}
    for s in entry.get('sections') or []:
        src, kind, ncol = s.get('source'), s['kind'], len(s.get('columns') or [])
        if kind == 'fields':
            vals = {}
            for f in s.get('fields') or []:
                k = f['key']
                v = ctx.get('date') if k == 'date' else p.get(k) if src in ('product', None) else None
                vals[k] = _s(v) or GAP
                if not v and k not in ('image',):
                    gaps.append({'what': f['label']['en'], 'why': 'not in the product data', 'ar': f['label']['ar']})
            out[s['id']] = vals
        elif kind == 'table':
            rows = []
            if src == 'apis':
                for a in ctx.get('apis') or []:
                    rows.append([_s(a.get('name')), _s(a.get('manufacturer')), _s(a.get('address')), _s(a.get('country')), _s(a.get('option'))])
            elif src == 'composition':
                for c in ctx.get('composition') or []:
                    rows.append([_s(c.get('name') or c.get('ingredient')), _s(c.get('role') or c.get('function')), _s(c.get('standard') or c.get('grade')),
                                 _s(c.get('amount') or c.get('quantity')), _s(c.get('percent'))])
            elif src == 'batches':
                specs = _spec_rows(ctx)
                for b in ctx.get('batches') or []:
                    base = [_s(b.get('no')), _s(b.get('size')), _s(b.get('date')), _s(b.get('scale') or b.get('kind')), _s(b.get('site'))]
                    tests = [t for t in specs if t.get('test')] if ncol >= 8 else []
                    if tests:
                        for t in tests:
                            rows.append(base + [_s(t.get('test')), _s(t.get('limit')), _s((results.get(b.get('no')) or {}).get(t.get('test')))])
                    else:
                        rows.append(base)
            elif src == 'specs':
                for t in _spec_rows(ctx):
                    rows.append([_s(t.get('test')), _s(t.get('limit') or t.get('acceptance')), _s(t.get('method')), _s(t.get('reference') or t.get('ref'))])
            elif src == 'manufacturers':
                if p.get('manufacturer'):
                    rows.append([_s(p.get('manufacturer')), '', _s(p.get('manufacturer_country')), 'Manufacture of the finished product', ''])
                for a in ctx.get('apis') or []:
                    if a.get('manufacturer'):
                        rows.append([_s(a.get('manufacturer')), _s(a.get('address')), _s(a.get('country')), f"Manufacture of {a.get('name') or 'the API'}", ''])
            if rows:
                out[s['id']] = {'rows': [[(c if c != '' else GAP) for c in r[:ncol]] + [GAP] * max(0, ncol - len(r)) for r in rows]}
            else:
                gaps.append({'what': s['title']['en'], 'why': 'no data of this kind in the dossier yet', 'ar': s['title']['ar']})
        elif kind in ('para', 'list'):
            if src == 'product' and p.get('trade_name'):
                out[s['id']] = f"{p.get('trade_name')} {_s(p.get('strength'))} {_s(p.get('dosage_form'))}".strip() + f" — {p.get('applicant') or GAP}"
            else:
                gaps.append({'what': s['title']['en'], 'why': 'needs the base documents or the model', 'ar': s['title']['ar']})
    return {'sections': out, 'gaps': gaps, 'sources': {}, 'notes': 'filled from the product data only; no model was available'}


# ---------------- examples: what a filled section looks like (fictional values, marked as examples in the page)
SAMPLE_COLS = [('country', 'Egypt'), ('status', 'Registered & marketed'), ('authority', 'EDA'), ('registration', 'EG-12345'), ('date', '2024-03-15'),
               ('batch', 'DC2301'), ('size', '50 kg'), ('type', 'pilot'), ('scale', 'pilot'), ('site', 'Cairo plant'), ('test', 'Assay'), ('limit', '95.0–105.0 %'),
               ('acceptance', '95.0–105.0 %'), ('criterion', '95.0–105.0 %'), ('method', 'HPLC'), ('reference', 'Ph. Eur. 11.0 (2.2.29)'), ('result', '99.1 %'),
               ('name', 'Example Pharm Co.'), ('address', '12 Industrial Zone, 6th of October City'), ('responsibility', 'Manufacture and release of the finished product'),
               ('gmp', 'GMP-2024-0001'), ('licence', 'GMP-2024-0001'), ('component', 'Neomycin sulphate'), ('substance', 'Neomycin sulphate'), ('ingredient', 'Talc'),
               ('excipient', 'Talc'), ('function', 'Active substance'), ('standard', 'Ph. Eur.'), ('grade', 'Ph. Eur.'), ('quantity', '3.5 mg'), ('%', '0.35 %'),
               ('overage', 'none'), ('manufacturer', 'Example API Ltd.'), ('route', 'CEP'), ('option', 'Option 1 — CEP'), ('version', '1.0'), ('cep', 'R1-CEP 2020-123'),
               ('impurity', 'Impurity A'), ('origin', 'Synthesis'), ('structure', 'C23H46N6O13'), ('justification', 'ICH Q3A reporting / identification thresholds'),
               ('solvent', 'Methanol'), ('class', 'Class 2'), ('technique', 'IR spectroscopy'), ('observation', 'Bands at 3300, 1640 cm⁻¹'), ('interpretation', 'Consistent with the structure'),
               ('spectrum', 'Annex 3.2.S.3.1-1'), ('property', 'Solubility (pH 6.8, 37 °C)'), ('value', '> 100 mg/mL (very soluble)'), ('source', 'Supplier data sheet'),
               ('parameter', 'Mixing time'), ('target', '15 min'), ('range', '12–18 min'), ('equipment', 'Bin blender 200 L'), ('capacity', '200 L'), ('step', 'Blending'),
               ('ipc', 'Blend uniformity'), ('sampling', '10 locations'), ('hold', '48 h'), ('condition', '30 °C / 75 % RH'), ('time', '6 months'), ('container', 'HDPE bottle 20 g'),
               ('specificity', 'No interference'), ('linearity', 'r² = 0.9995, 50–150 %'), ('accuracy', '99.2–100.6 %'), ('precision', 'RSD 0.6 %'), ('lod', '0.02 / 0.05 %'),
               ('robustness', 'Complies'), ('report', 'VAL-2024-07'), ('study', 'BE-2024-01'), ('design', 'Crossover, 2×2, fasting'), ('subjects', '28 healthy volunteers'),
               ('product', 'Dermacure 3.5 mg/g'), ('cro', 'Example CRO, Cairo'), ('location', '5.3.1.2'), ('section', '2.3.P.1'), ('title', 'Description and composition'),
               ('included', 'yes'), ('module', '3.2.P.1'), ('node', 'STF-01'), ('material', 'HDPE'), ('certificate', 'TSE/BSE statement 2024'), ('validity', '2026-12-31'),
               ('field', 'Trade name'), ('party', 'Example Pharm Co.'), ('role', 'Licence holder'), ('register', 'CR 123456'), ('content', 'QOS-PD table'),
               ('cross', '3.2.P.5.1'), ('attribute', 'Dissolution'), ('trial', 'F3 / DC2201'), ('change', 'Disintegrant 2 % → 4 %'), ('conclusion', 'Faster release, within limits'),
               ('medium', 'pH 6.8 phosphate buffer'), ('point', '15 min'), ('f2', '62'), ('match', 'yes'), ('text', 'Dermacure 3.5 mg/g topical powder')]
SAMPLE_FIELDS = {'trade_name': 'Dermacure', 'dosage_form': 'Topical powder', 'strength': '3.5 mg/g', 'pack': 'Bottle of 20 g', 'manufacturer': 'Example Pharm Co.',
                 'applicant': 'Example Pharm Co.', 'registration_number': 'EG-12345', 'date': '2024-03-15', 'signatory': 'Dr. A. Example', 'signatory_title': 'Regulatory Affairs Manager',
                 'company': 'Example Pharm Co.', 'version': '1.0', 'inn': 'Neomycin sulfate', 'compendial': 'Neomycin Sulfate Ph. Eur.', 'chemical': '…', 'iupac': '…', 'code': 'EX-001',
                 'other': 'Neomycin sulphate (BAN)', 'cas': '1405-10-3', 'formula': 'C23H46N6O13 · xH2SO4', 'mw': '614.6 (base)', 'stereo': 'Several chiral centres (aminoglycoside)',
                 'image': '[structure drawing]'}


def _sample_for(col):
    c = str(col).lower()
    for key, val in SAMPLE_COLS:
        if key in c:
            return val
    return '…'


def examples(entry):
    """Per section: an example of a filled section — one sample row per table, sample field values, the hint as the example of a text."""
    out = {}
    for s in entry.get('sections') or []:
        if s['kind'] == 'table':
            out[s['id']] = {'rows': [[_sample_for(c) for c in s['columns']]]}
        elif s['kind'] == 'fields':
            out[s['id']] = {f['key']: SAMPLE_FIELDS.get(f['key'], '…') for f in s.get('fields') or []}
        elif s['kind'] == 'list':
            h = (s.get('hint') or {})
            out[s['id']] = {'en': [x.strip() for x in (h.get('en') or '').replace(';', '.').split('.') if x.strip()][:6] or ['…'],
                            'ar': [x.strip() for x in (h.get('ar') or '').replace('؛', '.').split('.') if x.strip()][:6] or ['…']}
        else:
            h = (s.get('hint') or {})
            out[s['id']] = {'en': h.get('en') or '…', 'ar': h.get('ar') or h.get('en') or '…'}
    return out


def compute(st, did, slot, answers=None, use_ai=True):
    """The filled template without storing anything: (answers, how, ctx). answers given → used as they are (the page's model or the
    user's edits); None → the server's model when a key exists and use_ai, else the deterministic fill. The data's own values fill
    any section the answers left empty."""
    entry = template(slot.req_id, _req(st, did, slot.req_id))
    if not entry or entry['draft'] not in ('full', 'partial'):
        raise ValueError('this item is not drafted by the program')
    ctx = context(st, did, slot, with_texts=True)
    how = 'answers'
    if answers is None:
        got = ask_model(st, prompt(entry, ctx)) if use_ai else None
        if got is None:
            answers, how = deterministic(entry, ctx), 'data'
        else:
            answers, how = got, 'server-model'
    answers = dict(answers or {})
    if not isinstance(answers.get('sections'), dict):
        answers['sections'] = {}
    det = deterministic(entry, ctx)
    for k, v in det['sections'].items():
        if not answers['sections'].get(k):
            answers['sections'][k] = v
    if 'gaps' not in answers or not isinstance(answers['gaps'], list):
        answers['gaps'] = det['gaps'] if how == 'data' else []
    return answers, how, ctx


# ---------------- the Word draft
def _lang_of(entry, lang):
    return lang if lang in ('en', 'ar') else ('ar' if entry.get('lang') == 'ar' else 'en')


def render(entry, answers, ctx, out, lang=None, title=None):
    lang = _lang_of(entry, lang)
    ar = lang == 'ar'
    d = new_doc(draft=True)
    t = title or ctx['requirement']['title']
    para(d, t.get('ar') if ar else t.get('en'), ar=ar, bold=True, size=15)
    head = f"{ctx['requirement']['ctd']} · {ctx['requirement']['id']} · {ctx.get('date')}"
    para(d, head, size=9)
    p = ctx.get('product') or {}
    if p.get('trade_name'):
        para(d, f"{p['trade_name']} — {_s(p.get('strength'))} {_s(p.get('dosage_form'))}".strip(), ar=False, bold=True)
    secs = answers.get('sections') or {}
    for s in entry.get('sections') or []:
        title_s = s['title']['ar'] if ar else s['title']['en']
        para(d, title_s, ar=ar, bold=True, size=12)
        val = secs.get(s['id'])
        if s['kind'] == 'table':
            rows = (val or {}).get('rows') if isinstance(val, dict) else (val if isinstance(val, list) and val and isinstance(val[0], list) else None)
            if rows:
                table(d, s['columns'], [[_s(c) for c in r] + [GAP] * (len(s['columns']) - len(r)) for r in rows], ar=ar and all(_has_ar(_s(c)) for r in rows for c in r if c))
            else:
                table(d, s['columns'], [[GAP] * len(s['columns'])], ar=False)
        elif s['kind'] == 'fields':
            vals = val if isinstance(val, dict) else {}
            table(d, ['Field' if not ar else 'البند', 'Value' if not ar else 'القيمة'], [[f['label']['ar' if ar else 'en'], _s(vals.get(f['key'])) or GAP] for f in s.get('fields') or []], ar=ar)
        elif s['kind'] == 'list':
            items = val if isinstance(val, list) else [val] if isinstance(val, str) and val else []
            if isinstance(val, dict):
                items = [val.get('ar' if ar else 'en') or val.get('en') or '']
            for it in items or [GAP]:
                para(d, _s(it), ar=ar or _has_ar(_s(it)), bullet=True)
        else:
            text = val.get('ar' if ar else 'en') or val.get('en') if isinstance(val, dict) else val
            text = _s(text) if text else GAP
            for chunk in re.split(r'\n\s*\n', text):
                para(d, chunk.strip(), ar=ar or _has_ar(chunk))
        if s.get('hint') and not val:
            para(d, ('ما يُكتب هنا: ' if ar else 'What goes here: ') + (s['hint'].get('ar' if ar else 'en') or ''), ar=ar, size=9)
    if entry.get('letterhead'):
        para(d, '')
        para(d, 'يُطبع على ورق الشركة، يُوقَّع من المفوَّض، يُختم ويُؤرَّخ، ثم يُمسح ويُرفع بدل هذه المسودة.' if ar else
                'Print on company letterhead, sign by the authorised person, stamp and date, then scan and upload in place of this draft.', ar=ar, size=9)
    gaps = answers.get('gaps') or []
    if gaps:
        para(d, 'ما ينقص هذه المسودة' if ar else 'Gaps in this draft', ar=ar, bold=True, size=12)
        table(d, ['البند' if ar else 'Missing', 'السبب / المصدر' if ar else 'Why / where to get it'], [[_s(g.get('ar') if ar and g.get('ar') else g.get('what')), _s(g.get('why'))] for g in gaps], ar=ar)
    if answers.get('notes'):
        para(d, ('ملاحظات للمراجع: ' if ar else 'Notes for the reviewer: ') + _s(answers['notes']), ar=ar or _has_ar(_s(answers['notes'])), size=9)
    d.save(out)
    return Path(out)


def draft(st, did, slot, answers=None, lang=None, use_ai=True, req_item=None):
    """Build the draft and store it in the item as an unsigned Word version. answers: the model's JSON or the user's edited
    preview (the page sends it); None → the server's model when a key exists and use_ai, else the deterministic fill."""
    import tempfile, shutil
    entry = template(slot.req_id, req_item or _req(st, did, slot.req_id))
    answers, how, ctx = compute(st, did, slot, answers=answers, use_ai=use_ai)
    tmp = Path(tempfile.mkdtemp())
    try:
        out = tmp / f"{slot.req_id}-draft.docx"
        render(entry, answers, ctx, out, lang=lang)
        blob = out.read_bytes()
        doc = st.add_document(did, slot.slot_id, out.name, blob, meta={'generated': 'draft', 'template': slot.req_id, 'draft_unsigned': True, 'draft_docx': True,
                                                                        'draft_how': how, 'gaps': answers['gaps'][:40], 'sources': answers.get('sources') or {},
                                                                        'lang': _lang_of(entry, lang)})
        st.audit(did, 'document.drafted', slot=slot.slot_id, template=slot.req_id, how=how, gaps=len(answers['gaps']))
        return {'document': doc, 'gaps': answers['gaps'], 'how': how, 'notes': answers.get('notes'), 'sources': answers.get('sources') or {}}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
