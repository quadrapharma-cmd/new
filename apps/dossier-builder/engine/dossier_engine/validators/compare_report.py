"""Another validator's report beside ours (updates list, item 27) — EXTEDO's or LORENZ's, a consultant's, or the authority's portal
when it runs: rule by rule, where both agree, and where they differ with the reason.

Their report is read as text, whatever its form (PDF, Excel, CSV, HTML, XML, text): a line that names a validation criterion
(«14.5», «15.BP3», «EG-PF-11.2») and says how it ended (failed / error / passed / OK / warning) is one result; a rule named on
several lines keeps its worst result. Our side is the validation report of the same sequence (the export's validation-report.json).
The criteria are matched by their number: our EU rules are the EU validation criteria v8.2 (EU-14.5 is criterion 14.5), our EG rules
carry the EU criterion they come from (eu_vc_ref) and their own id."""
import csv, html, io, json, re
from pathlib import Path

RULE = re.compile(r'(?<![\w.])(?:(EG-(?:PF|BP)-[\w.]+)|(?:EU[- ]?)?((?:\d{1,2})\.(?:BP)?\d{1,2}))(?![\w])')
FAIL = re.compile(r'\b(fail(?:ed|s)?|error|errors|not met|not passed|invalid|reject(?:ed)?|✗|×)\b', re.I)
WARN = re.compile(r'\b(warning|warn|best[- ]practice not met|not followed)\b', re.I)
PASS = re.compile(r'\b(pass(?:ed)?|ok|met|valid|✓|success(?:ful)?)\b', re.I)
NA = re.compile(r'\b(n/?a|not applicable|not run|skipped)\b', re.I)
ORDER = {'fail': 3, 'warning': 2, 'pass': 1, 'na': 0}


def text_of(name, data):
    """Their report as lines of text."""
    low = (name or '').lower()
    if low.endswith('.pdf'):
        from pypdf import PdfReader
        return '\n'.join((p.extract_text() or '') for p in PdfReader(io.BytesIO(data)).pages)
    if low.endswith(('.xlsx', '.xlsm')):
        from ..officefiles import xlsx_text
        return xlsx_text(data)
    t = data.decode('utf-8-sig', 'replace')
    if low.endswith(('.html', '.htm', '.xml')) or t.lstrip().startswith('<'):
        t = re.sub(r'<(br|/p|/tr|/li|/div|/h\d)[^>]*>', '\n', t, flags=re.I)
        t = re.sub(r'</t[dh]>', ' | ', t, flags=re.I)
        t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return t


def read(name, data):
    """{criterion number or EG id: {'status', 'line'}} from their report."""
    out = {}
    for ln in text_of(name, data).splitlines():
        ids = [(m.group(1) or m.group(2)) for m in RULE.finditer(ln)]
        if not ids:
            continue
        st = 'fail' if FAIL.search(ln) else 'warning' if WARN.search(ln) else 'pass' if PASS.search(ln) else 'na' if NA.search(ln) else None
        if not st:
            continue
        rid = ids[0]
        if rid not in out or ORDER[st] > ORDER[out[rid]['status']]:
            out[rid] = {'status': st, 'line': ln.strip()[:240]}
    return out


def _our_index(ours, criteria=None):
    """{number or id: our result} — EU-14.5 answers to «14.5»; an EG rule to its id and to the EU criterion it comes from."""
    idx = {}
    for r in ours.get('results') or []:
        rid = r['rule']
        idx[rid] = r
        if rid.startswith('EU-'):
            idx.setdefault(rid[3:], r)
        ref = (criteria or {}).get(rid)
        if ref:
            idx.setdefault(ref, r)
    return idx


def eg_refs(profile_root):
    """{EG rule id: the EU criterion number it comes from} from the EG profile's criteria table."""
    p = Path(profile_root) / 'validation-criteria.csv'
    if not p.exists():
        return {}
    out = {}
    for r in csv.DictReader(open(p, encoding='utf-8')):
        m = re.search(r'EU VC [\d.]+ ([\d.]+(?:BP\d+)?|\d+\.BP\d+)', r.get('eu_vc_ref') or '')
        if m:
            out[r['rule_id']] = m.group(1)
    return out


def compare(theirs, ours, criteria=None):
    """Rows: {rule, theirs, ours, agree, why, their_line, our_text, our_failures}; and counts."""
    idx = _our_index(ours, criteria)
    rows, seen = [], set()
    for rid, t in sorted(theirs.items(), key=lambda kv: [int(x) if x.isdigit() else x for x in re.split(r'[.-]', kv[0])]):
        o = idx.get(rid)
        if o:
            seen.add(o['rule'])
        ost = None if not o else ('na' if o['status'] == 'not_run' else 'fail' if o['status'] == 'fail' else 'warning' if o['status'] == 'warning' else 'pass')
        agree = o is not None and (ost == t['status'] or {ost, t['status']} <= {'pass', 'na'})
        if o is None:
            why = 'Not one of our criteria: a rule of another region or the tool\'s own — read their message.'
        elif agree:
            why = ''
        elif t['status'] == 'fail' and ost == 'na':
            why = f'We do not run it automatically ({o.get("reason") or "a manual or visual check"}): check it by hand — their message names the file.'
        elif t['status'] == 'fail':
            why = 'We pass it and they fail it: open the file their message names; tell us if their reading is right, so the rule is corrected.'
        elif ost == 'fail':
            why = ('We fail it and they do not: our check found ' + '; '.join((o.get('failures') or [])[:2])
                   + ' — they may not run this rule, or read it more leniently; the criterion is the reference.')
        else:
            why = f'They say {t["status"]}, we say {ost}.'
        rows.append({'rule': rid, 'our_rule': o['rule'] if o else None, 'theirs': t['status'], 'ours': ost, 'agree': agree, 'why': why,
                     'their_line': t['line'], 'our_text': o['text'] if o else None, 'our_failures': (o.get('failures') or [])[:3] if o else []})
    for r in ours.get('results') or []:                 # what we fail and their report does not name at all
        if r['status'] == 'fail' and r['rule'] not in seen:
            rows.append({'rule': r['rule'], 'our_rule': r['rule'], 'theirs': None, 'ours': 'fail', 'agree': False,
                         'why': 'Their report does not name it: it may be outside their criteria, or they stop at the first errors.',
                         'their_line': None, 'our_text': r['text'], 'our_failures': (r.get('failures') or [])[:3]})
    counts = {'agree': sum(1 for r in rows if r['agree']), 'differ': sum(1 for r in rows if not r['agree']), 'theirs': len(theirs)}
    return {'rows': rows, 'counts': counts}


def ours_of(export_dir, output='eCTD 3.2.2'):
    """Our report of an export, by the name the export gave it ('eCTD 3.2.2', 'eCTD 3.2.2 (EU)', 'eCTD 4.0', 'NeeS')."""
    p = Path(export_dir) / 'validation-report.json'
    if not p.exists():
        return None
    reports = json.loads(p.read_text(encoding='utf-8'))
    return reports.get(output) or next(iter(reports.values()), None)
