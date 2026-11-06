"""Generators for the documents the tool rebuilds (checklist «Yes — rebuild»).

Every function: (data, out_path) -> Path of the .docx. Missing required data
raises MissingData(fields) — the UI turns it into a request_data list; nothing
is guessed. Arithmetic is computed here and printed with its formula.
Company letters carry the «DRAFT — unsigned» header until a signed scan is
uploaded (02-LOGIC §8)."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import yaml
from .. import expr
from .docx_kit import new_doc, para, table, require, MissingData

TPL = Path(__file__).resolve().parents[3] / 'rulepacks' / 'eda.ctd.nta065.v5' / 'templates'


def _d(x):
    return Decimal(str(x))


def _fmt(x, places='0.001'):
    return str(_d(x).quantize(Decimal(places), rounding=ROUND_HALF_UP).normalize())


# ---------------------------------------------------------------- Annex I
def annex1(data, ctx, out, letterhead=None):
    """data: Annex I field values; ctx: profile env + apis/variations/distributors/signatory."""
    t = yaml.safe_load(open(TPL / 'annex1.yaml', encoding='utf-8'))
    req = [f['key'] for s in t['sections'] for f in s['fields'] if f.get('required')]
    req += [f['key'] for f in t['contact'] if f.get('required')]
    req += ['signatory', 'signatory_title', 'company', 'distributors']
    miss = [k for k in req if data.get(k) in (None, '', [])]
    for i, a in enumerate(ctx.get('apis', [])):
        miss += [f'apis[{i}].{f["key"]}' for f in t['api_box'] if f.get('required') and not a.get(f['key'])]
    if not ctx.get('apis'):
        miss.append('apis')
    if ctx.get('activity') == 're_registration' and not data.get('rereg_studies_api_source'):
        miss.append('rereg_studies_api_source')
    if miss:
        raise MissingData(miss)
    d = new_doc(letterhead=letterhead)
    para(d, 'Annex I — Application form', bold=True, size=13, align='center')
    for line in t['salutation_ar']:
        para(d, line, ar=True)
    for sec in t['sections']:
        if sec['title']:
            para(d, sec['title'], bold=True)
        table(d, ['Field', 'Value'], [(f['label'], data.get(f['key']) or ('N/A' if not f.get('required') else ''))
                                     for f in sec['fields']], widths=[7, 10])
    for i, a in enumerate(ctx['apis'], 1):
        para(d, f'API {i}', bold=True)
        rows = []
        for f in t['api_box']:
            v = a.get(f['key'])
            if f['key'] == 'option':
                v = '  '.join(('☒ ' if c == v else '☐ ') + c for c in f['choices'])
            rows.append((f['label'], v or 'N/A'))
        table(d, ['Field', 'Value'], rows, widths=[7, 10])
    table(d, ['Contact', ''], [(f['label'], data[f['key']]) for f in t['contact']], widths=[7, 10])
    para(d, '')
    fill = dict(data)
    fill.setdefault('pending_studies_api_source', '')
    vars_ = ctx.get('variations') or []
    fill['variations_statement'] = t['variations_statement_ar']['with' if vars_ else 'none']
    para(d, t['undertaking_intro_ar'].format(**fill), ar=True, bold=True)
    env = dict(ctx)
    env.setdefault('decree_case', 'other')
    env['pending_studies_api_source'] = bool(data.get('pending_studies_api_source'))
    for cl in t['undertaking_ar']:
        if 'when' in cl and not expr.evaluate(cl['when'], env):
            continue
        para(d, cl['text'].format(**fill), ar=True, bullet=True)
    if vars_:
        table(d, t['variations_table'], [(v['type'], v['from'], v['to'], v['status']) for v in vars_])
    para(d, '')
    for line in t['signature_ar']:
        para(d, line, ar=True)
    out = Path(out)
    d.save(out)
    return out


# ---------------------------------------------------------------- composition + salt
def salt_equivalence(api):
    """api: label_claim_mg (as base), mw_salt, mw_base, mw_ref; optional assay_pct (as-is),
    water_pct. Returns dict with the quantities and the formulas used."""
    require(api, ['name_base', 'name_salt', 'label_claim_mg', 'mw_salt', 'mw_base', 'mw_ref'])
    factor = _d(api['mw_salt']) / _d(api['mw_base'])
    salt = _d(api['label_claim_mg']) * factor
    out = {'factor': factor, 'salt_mg': salt,
           'formula': f"{api['label_claim_mg']} mg × {api['mw_salt']} / {api['mw_base']} = {_fmt(salt)} mg"}
    if api.get('assay_pct'):
        adj = salt * 100 / _d(api['assay_pct'])
        out['adjusted_mg'] = adj
        out['formula_assay'] = f"{_fmt(salt)} mg × 100 / {api['assay_pct']} % = {_fmt(adj)} mg (assay as-is)"
    return out


def salt_calc_letter(data, out, letterhead=None):
    require(data, ['trade_name', 'apis', 'signatory', 'signatory_title'])
    d = new_doc(letterhead=letterhead)
    para(d, 'Equivalence (salt) calculation', bold=True, size=13, align='center')
    para(d, f"Product: {data['trade_name']}")
    rows = []
    for a in data['apis']:
        r = salt_equivalence(a)
        rows.append((a['name_salt'], a['name_base'], f"{a['label_claim_mg']} mg", f"{a['mw_salt']} / {a['mw_base']}",
                     _fmt(r['factor'], '0.0001'), r['formula'] + ('\n' + r['formula_assay'] if 'formula_assay' in r else ''),
                     a['mw_ref']))
    table(d, ['Salt / hydrate', 'Base', 'Label claim (base)', 'MW salt / base', 'Factor', 'Calculation', 'MW reference'], rows)
    _sign(d, data)
    d.save(out)
    return Path(out)


def composition_certificate(data, out, letterhead=None):
    """components: [{name, function, qty_mg, standard, part: core|coat|body|cap|fill}]; overage_pct optional."""
    require(data, ['trade_name', 'dosage_form', 'components', 'signatory', 'signatory_title'])
    for i, c in enumerate(data['components']):
        require({**c, '_': 1}, ['name', 'function', 'qty_mg', 'standard'])
    d = new_doc(letterhead=letterhead)
    para(d, 'Composition certificate', bold=True, size=13, align='center')
    para(d, f"Trade name: {data['trade_name']}")
    para(d, f"Dosage form: {data['dosage_form']}")
    parts = []
    for c in data['components']:
        p = c.get('part', 'core')
        if p not in parts:
            parts.append(p)
    grand = Decimal(0)
    for p in parts:
        comps = [c for c in data['components'] if c.get('part', 'core') == p]
        sub = sum(_d(c['qty_mg']) for c in comps)
        grand += sub
        para(d, {'core': 'Core', 'coat': 'Coating', 'body': 'Capsule body', 'cap': 'Capsule cap',
                 'fill': 'Capsule fill'}.get(p, p.title()), bold=True)
        rows = [(c['name'], c['function'], _fmt(c['qty_mg']), _fmt(_d(c['qty_mg']) * 100 / sub, '0.01'), c['standard'])
                for c in comps]
        rows.append(('Total', '', _fmt(sub), '100', ''))
        table(d, ['Component', 'Function', 'mg / unit', '% w/w', 'Standard'], rows)
    para(d, f"Total unit weight: {_fmt(grand)} mg" + (f" (capsule size {data['capsule_size']})" if data.get('capsule_size') else ''),
         bold=True)
    if data.get('overage_pct'):
        para(d, f"Overage: {data['overage_pct']} % ({data.get('overage_reason', 'justified in 3.2.P.2')}).")
    _sign(d, data)
    d.save(out)
    return Path(out), grand


# ---------------------------------------------------------------- letters
def cep_commitment(data, out, letterhead=None):
    require(data, ['api', 'cep_number', 'cep_holder', 'trade_name', 'signatory', 'signatory_title', 'company'])
    d = new_doc(letterhead=letterhead)
    para(d, 'To: Egyptian Drug Authority — General Administration for Human Pharmaceuticals Registration')
    para(d, f"Subject: Commitment regarding Certificate of Suitability {data['cep_number']} — {data['api']}", bold=True)
    para(d, f"We, {data['company']}, applicant for {data['trade_name']}, hereby commit to inform the Egyptian Drug "
            f"Authority without delay of any revision, renewal, suspension or withdrawal of Certificate of Suitability "
            f"{data['cep_number']} held by {data['cep_holder']} for {data['api']}.")
    para(d, 'We acknowledge that if the CEP is suspended or withdrawn, full data for section 3.2.S of the CTD will be '
            'required (CTD Quality Module guideline v2/2023, CEP option).')
    _sign(d, data)
    d.save(out)
    return Path(out)


def translation_declaration(data, out, letterhead=None):
    require(data, ['trade_name', 'leaflet_version', 'source_language', 'translator', 'signatory', 'signatory_title', 'company'])
    d = new_doc(letterhead=letterhead)
    para(d, 'Declaration — leaflet translation', bold=True, size=13, align='center')
    para(d, f"We, {data['company']}, declare that the {data['source_language']} leaflet of {data['trade_name']} "
            f"(version {data['leaflet_version']}) has been translated by an authorised medical translator "
            f"({data['translator']}), and that the translation is faithful and complete.")
    para(d, f"نقر نحن {data['company']} بأن نشرة المستحضر {data['trade_name']} (الإصدار {data['leaflet_version']}) "
            f"تمت ترجمتها بواسطة مترجم طبي معتمد ({data['translator']}) وأن الترجمة مطابقة وكاملة.", ar=True)
    _sign(d, data)
    d.save(out)
    return Path(out)


def cover_letter(data, out, letterhead=None):
    require(data, ['trade_name', 'sequence', 'submission_type', 'unit', 'tracking', 'description', 'company',
                   'signatory', 'signatory_title'])
    d = new_doc(letterhead=letterhead)
    para(d, data.get('date') or date.today().isoformat())
    para(d, 'To: Egyptian Drug Authority — General Administration for Human Pharmaceuticals Registration')
    para(d, f"Subject: {data['trade_name']} — sequence {data['sequence']} ({data['submission_type']}, {data['unit']})", bold=True)
    table(d, ['Item', 'Value'], [('Procedure tracking number', data['tracking']), ('Sequence', data['sequence']),
                                 ('Submission type / unit', f"{data['submission_type']} / {data['unit']}"),
                                 ('Description', data['description'])], widths=[6, 11])
    if data.get('baseline'):
        para(d, 'This is a baseline (reformatted) sequence: the content is unchanged from the approved dossier.')
    para(d, 'We confirm that the submission is true, complete and correct, and that the electronic submission has been '
            'checked with up-to-date virus-checking software.')
    _sign(d, data)
    d.save(out)
    return Path(out)


def tracking_table(data, out):
    require(data, ['trade_name', 'sequences'])
    d = new_doc(landscape=True, draft=False)
    para(d, f"Tracking table — {data['trade_name']}", bold=True, size=13, align='center')
    table(d, ['Sequence', 'Related sequence', 'Description', 'Submission type', 'Submission unit', 'Date submitted',
              'Tracking number', 'Status'],
          [(s['sequence'], s.get('related', ''), s['description'], s['type'], s['unit'], s.get('date', ''),
            s.get('tracking', ''), s.get('status', '')) for s in data['sequences']])
    d.save(out)
    return Path(out)


def _sign(d, data):
    para(d, '')
    para(d, f"Name: {data['signatory']}")
    para(d, f"Title: {data['signatory_title']}")
    para(d, 'Signature: ______________________     Company stamp:')
    para(d, f"Date: {data.get('date') or '____/____/________'}")
