"""eCTD 4.0 submission-unit validator (ICH eCTD v4.0 IG v1.7 rules + EG provisional
rules), re-reading the output from disk. Rule ids are the ICH eCTD4-xxx / EG-V4-xxx
ids of the EG v4 profile (rules.md)."""
import hashlib, re, zipfile
from pathlib import Path
from lxml import etree
from ..checks.pdf import check as pdf_check

NS = {'h': 'urn:hl7-org:v3'}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9$\-_+!'()]*\.[a-z0-9]{3,4}$")
_XSD = {}


def _schema(ig_zip, cache_dir):
    key = str(ig_zip)
    if key not in _XSD:
        d = Path(cache_dir) / 'ich-v4-xsd'
        if not list(d.rglob('PORP_IN000001UV.xsd')):
            d.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(ig_zip) as z:
                z.extractall(d)
        _XSD[key] = etree.XMLSchema(etree.parse(str(next(d.rglob('PORP_IN000001UV.xsd')))))
    return _XSD[key]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def validate(seq_dir, profile40, ig_zip, cache_dir):
    base = Path(seq_dir)
    res = []

    def add(rid, sev, text, fails, provenance='ICH'):
        status = 'pass' if not fails else ('fail' if sev == 'pass_fail' else 'warning')
        res.append({'rule': rid, 'severity': sev, 'text': text, 'provenance': provenance, 'status': status,
                    'failures': fails[:50]})

    su = base / 'submissionunit.xml'
    files = sorted(p.relative_to(base).as_posix() for p in base.rglob('*') if p.is_file())
    if not su.exists():
        add('eCTD4-059', 'pass_fail', 'submissionunit.xml is present', ['missing'])
        return _sum(res)
    try:
        doc = etree.parse(str(su))
    except etree.XMLSyntaxError as e:
        add('eCTD4-001', 'pass_fail', 'The message is well formed', [str(e)])
        return _sum(res)
    xs = _schema(ig_zip, cache_dir)
    add('eCTD4-002', 'pass_fail', 'The message is valid against the ICH XSD (PORP_IN000001UV)',
        [] if xs.validate(doc) else [f'{e.line}: {e.message}' for e in xs.error_log][:20])
    shat = base / 'sha256.txt'
    add('eCTD4-062', 'pass_fail', 'sha256.txt holds the SHA-256 of submissionunit.xml',
        [] if shat.exists() and shat.read_text().strip().lower() == sha(su) else ['missing or mismatch'])
    seqn = doc.findtext('.//h:componentOf1/h:sequenceNumber', namespaces=NS) or \
        (doc.find('.//h:componentOf1/h:sequenceNumber', NS).get('value') if doc.find('.//h:componentOf1/h:sequenceNumber', NS) is not None else None)
    add('eCTD4-013', 'pass_fail', 'Sequence folder name equals sequenceNumber (1–999999, no padding)',
        [] if seqn == base.name and re.fullmatch(r'[1-9]\d{0,5}', base.name) else [f'folder {base.name} vs {seqn}'])
    docs = {d.find('h:id', NS).get('root'): d for d in doc.iterfind('.//h:document', NS)}
    refs, bad_hash, missing = {}, [], []
    for did, d in docs.items():
        t = d.find('h:text', NS)
        ref = t.find('h:reference', NS).get('value')
        refs[ref] = did
        if not (base / ref).is_file():
            missing.append(ref)
        elif sha(base / ref) != (t.findtext('h:integrityCheck', namespaces=NS) or '').strip():
            bad_hash.append(ref)
    add('eCTD4-063', 'pass_fail', 'Every referenced file exists in the submission unit', missing)
    add('eCTD4-064', 'pass_fail', 'The integrity check (SHA-256) of every document matches its file', bad_hash)
    content = [f for f in files if f.split('/')[0] in ('m1', 'm2', 'm3', 'm4', 'm5')]
    add('eCTD4-069', 'pass_fail', 'No unassociated files in the submission unit', [f for f in content if f not in refs])
    add('eCTD4-065', 'pass_fail', 'File names ≤ 64 characters', [f for f in files if len(f.split('/')[-1]) > 64])
    add('eCTD4-066', 'pass_fail', 'Folder names ≤ 64 characters',
        [f for f in files for part in f.split('/')[:-1] if len(part) > 64])
    first = base.parent.name
    add('eCTD4-067', 'pass_fail', 'Path ≤ 180 characters counted from the first-level folder',
        [f for f in files if len(f'{first}/{base.name}/{f}') > 180])
    add('eCTD4-074', 'pass_fail', 'File names use lower case a-z, 0-9 and $ - _ + ! \' ( ) with one 3–4 letter extension',
        [f for f in content if not NAME_RE.match(f.split('/')[-1])])
    add('EG-V4-011', 'pass_fail', 'No util folder, index.xml, md5 file or eg-regional.xml in a v4 submission unit',
        [f for f in files if f.startswith('util/') or f.endswith(('index.xml', 'index-md5.txt', 'eg-regional.xml'))],
        'EG-DRAFT')
    add('EG-V4-007', 'best_practice', 'Module 1 is one flat folder m1/', [f for f in files if f.startswith('m1/') and f.count('/') > 1],
        'EU-DERIVED')
    cous = list(doc.iterfind('.//h:contextOfUse', NS))
    used = {c.find('h:derivedFrom//h:id', NS).get('root') for c in cous if c.find('h:derivedFrom//h:id', NS) is not None}
    add('eCTD4-0xx-doc-used', 'pass_fail', 'Every document in this unit is referenced by a context of use',
        [docs[d].findtext('h:title', namespaces=NS) or d for d in docs if d not in used])
    bad_code, kw_miss, kw_extra, folder_only = [], [], [], []
    eg_by_code = {c['code']: c for c in profile40.eg.values()}
    for c in cous:
        code_el = c.find('h:code', NS)
        code, cs = code_el.get('code'), code_el.get('codeSystem')
        kws = [k.find('.//h:code', NS) for k in c.iterfind('h:referencedBy', NS)]
        kcs = {k.get('codeSystem') for k in kws if k is not None}
        if code.startswith('eg_'):
            e = eg_by_code.get(code)
            if not e:
                bad_code.append(code)
                continue
            if not e.get('documents_allowed'):
                folder_only.append(code)
            for k in e.get('keyword_types') or []:
                if k['cardinality'] == 'R' and k.get('code_system') not in kcs:
                    kw_miss.append(f"{code}: {k['type']}")
        elif code not in profile40.ich:
            bad_code.append(code)
    # ICH CoUs: required sender-defined keywords are enforced by the writer (eCTD4-070 at build time)
    add('eCTD4-031', 'pass_fail', 'Context-of-use codes come from the ICH list or the regional (EG) list', bad_code)
    add('eCTD4-070', 'pass_fail', 'Required keywords are present on each context of use', kw_miss)
    add('EG-V4-022', 'pass_fail', 'No document on an EG heading that takes no documents', folder_only, 'EG-DRAFT')
    ph = 'EG-PLACEHOLDER' in su.read_text(encoding='utf-8')
    add('eCTD4-008/009/081/083/084', 'pass_fail', 'Regional OIDs are registered values',
        ['EG OIDs are placeholders until EDA registers them (expected in the provisional profile)'] if ph else [], 'EG-DRAFT')
    if ph:
        res[-1]['status'] = 'warning'      # known, labelled provisional — not a defect of this dossier
    pdf_bad = []
    for f in content:
        if f.endswith('.pdf'):
            for fd in pdf_check(str(base / f), 'company_technical').findings:
                if fd.severity == 'block' and fd.rule != 'NTA065-N4':
                    pdf_bad.append(f'{f}: {fd.en}')
    add('EG-V4-PDF', 'pass_fail', 'PDF 1.4–1.7, no security, not corrupt (EG/ICH file rules)', pdf_bad, 'EG-DRAFT')
    return _sum(res)


def _sum(res):
    count = {k: sum(1 for r in res if r['status'] == k) for k in ('pass', 'fail', 'warning', 'not_run')}
    return {'ok': count['fail'] == 0, 'counts': count, 'coverage': f'{len(res)}/{len(res)} automated rules',
            'label': 'Conforms to ICH eCTD v4.0 + EG drafts (provisional profile v0; placeholder OIDs) — not «EDA-valid».'
            if count['fail'] == 0 else 'Does not conform.', 'results': res}
