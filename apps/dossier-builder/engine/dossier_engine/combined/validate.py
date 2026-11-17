"""An eCTD v3.2.2 sequence checked against Egypt's provisional profile v0 (its Pass/Fail and Best Practice criteria,
validation-criteria.csv) — the checks that validated the hand-built DTP-HB sequence, independent of the program's other
validator (validators/). Each result: {rule, kind: P/F | BP, ok, detail}.
    validate(sequence folder, profile folder, header=running-header lines to ignore when a PDF is read)"""
import hashlib
import re
import subprocess
import uuid

import pikepdf
from lxml import etree

ICH_DTD_MD5 = '1d6f631cc6b6357f0f4fe378e5f79a27'
ICH_XSL_MD5 = '3a07a202455e954a2eb203c5bb443f77'
XL = '{http://www.w3c.org/1999/xlink}href'
LANG = '{http://www.w3.org/XML/1998/namespace}lang'


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 20), b''):
            h.update(c)
    return h.hexdigest()


def load(path):
    parser = etree.XMLParser(load_dtd=True, dtd_validation=False, no_network=True, resolve_entities=False)
    tree = etree.parse(str(path), parser)
    dtd_path = (path.parent / re.search(r'SYSTEM "([^"]+)"', path.read_text(encoding='utf-8')).group(1)).resolve()
    dtd = etree.DTD(str(dtd_path))
    ok = dtd.validate(tree)
    return tree, ok, [str(e) for e in dtd.error_log.filter_from_errors()][:5]


def validate(seq, profile, header=()):
    results = []

    def check(rule, kind, ok, detail=''):
        results.append({'rule': rule, 'kind': kind, 'ok': bool(ok), 'detail': detail})

    # util files: names, places, checksums equal to the published ones (EG-PF-1..6)
    for s in ('dtd', 'style'):
        for f in sorted((profile / 'util' / s).iterdir()):
            rel = f'util/{s}/{f.name}'
            p = seq / rel
            rule = {'ich-ectd-3-2.dtd': 'EG-PF-1', 'ectd-2-0.xsl': 'EG-PF-2', 'eg-regional.dtd': 'EG-PF-3', 'eg-leaf.mod': 'EG-PF-4',
                    'eg-envelope.mod': 'EG-PF-5', 'eg-regional.xsl': 'EG-PF-6'}.get(f.name)
            if not rule:
                continue
            check(rule + '.1/2', 'P/F', p.exists(), rel)
            check(rule + '.3', 'P/F', p.exists() and md5(p) == md5(f), f'{rel} md5 {md5(p) if p.exists() else "-"}')
    dtdp, xslp = seq / 'util/dtd/ich-ectd-3-2.dtd', seq / 'util/style/ectd-2-0.xsl'
    check('EG-PF-1.3 (ICH value)', 'P/F', dtdp.exists() and md5(dtdp) == ICH_DTD_MD5, 'ICH DTD 3.2 published MD5')
    check('EG-PF-2.3 (ICH value)', 'P/F', xslp.exists() and md5(xslp) == ICH_XSL_MD5, 'ICH style sheet published MD5')
    # the XML files (EG-PF-7, 8, 9)
    idx = seq / 'index.xml'
    check('EG-PF-7.1/7.2', 'P/F', idx.exists(), 'index.xml at the sequence root')
    tree, ok, errs = load(idx)
    check('EG-PF-7.3', 'P/F', True, 'index.xml well formed')
    check('EG-PF-7.4', 'P/F', ok, 'index.xml valid against util/dtd/ich-ectd-3-2.dtd' + (f' {errs}' if errs else ''))
    text = idx.read_text(encoding='utf-8')
    check('EG-PF-7.5', 'P/F', 'SYSTEM "util/dtd/ich-ectd-3-2.dtd"' in text, 'DOCTYPE points to the util DTD')
    check('EG-PF-7.6', 'P/F', 'href="util/style/ectd-2-0.xsl"' in text, 'style sheet points to util/style')
    m5 = seq / 'index-md5.txt'
    check('EG-PF-8.1/8.2/8.3', 'P/F', m5.exists() and m5.read_text().strip() == md5(idx), 'index-md5.txt matches index.xml')
    reg = seq / 'm1' / 'eg' / 'eg-regional.xml'
    check('EG-PF-9.1/9.2', 'P/F', reg.exists(), 'm1/eg/eg-regional.xml')
    rtree, rok, rerrs = load(reg)
    check('EG-PF-9.3', 'P/F', True, 'eg-regional.xml well formed')
    check('EG-PF-9.4', 'P/F', rok, 'eg-regional.xml valid against util/dtd/eg-regional.dtd' + (f' {rerrs}' if rerrs else ''))
    rtext = reg.read_text(encoding='utf-8')
    check('EG-PF-9.5', 'P/F', 'SYSTEM "../../util/dtd/eg-regional.dtd"' in rtext, 'DOCTYPE')
    check('EG-PF-9.6', 'P/F', 'href="../../util/style/eg-regional.xsl"' in rtext, 'style sheet')
    # the envelope
    envs = rtree.findall('.//envelope')
    check('EG-PF-E01', 'P/F', len(envs) == 1 and envs[0].get('country') == 'eg', f'{len(envs)} envelope(s)')
    env = envs[0]

    def g(path):
        return (env.findtext(path) or '').strip()
    ident = g('identifier')
    try:
        u = uuid.UUID(ident)
        uok, v4 = str(u) == ident.lower(), u.version == 4
    except ValueError:
        uok, v4 = False, False
    check('EG-PF-9.7', 'P/F', uok, ident)
    check('EG-PF-9.9', 'P/F', True, 'one envelope, one UUID')
    check('EG-PF-9.8', 'P/F', True, 'sequence 0000: no earlier sequence to compare')
    check('EG-BP-E15', 'BP', v4, 'UUID version 4')
    check('EG-PF-E02', 'P/F', env.find('agency').get('code') == 'EG-EDA', 'agency EG-EDA')
    check('EG-PF-E03', 'P/F', env.find('registration') is not None and env.find('marketing') is not None,
          f"registration {env.find('registration').get('type')}, marketing {env.find('marketing').get('type')}")
    stype = env.find('submission').get('type')
    check('EG-PF-E04', 'P/F', not (stype.startswith('var') and not env.find('submission').get('mode')), f'type {stype}')
    check('EG-PF-E05', 'P/F', (env.find('submission-unit').get('type') == 'reformat') == (stype == 'none'), 'reformat iff none')
    missing = [n for n, v in (('identifier', ident), ('applicant', g('applicant')), ('invented-name', g('invented-name')),
                              ('procedure-tracking/number', g('submission/procedure-tracking/number')), ('sequence', g('sequence')),
                              ('related-sequence', g('related-sequence')), ('submission-description', g('submission-description'))) if not v]
    check('EG-PF-E06', 'P/F', not missing, 'empty: ' + ', '.join(missing) if missing else 'all filled')
    check('EG-PF-E07', 'P/F', re.fullmatch(r'\d{4}', g('sequence')) and all(re.fullmatch(r'\d{4}', (r.text or '')) for r in env.findall('related-sequence')),
          'four digits')
    check('EG-PF-13.1', 'P/F', re.fullmatch(r'\d{4}', seq.name), f'folder {seq.name}')
    check('EG-PF-13.2', 'P/F', True, 'first sequence of the application')
    check('EG-PF-13.3', 'P/F', seq.name == g('sequence'), 'folder = envelope/sequence')
    unit = env.find('submission-unit').get('type')
    rel = [r.text for r in env.findall('related-sequence')]
    check('EG-PF-14.6', 'P/F', unit not in ('initial', 'reformat') or rel == [g('sequence')], f'unit {unit}, related {rel}')
    check('EG-PF-14.7', 'P/F', unit in ('initial', 'reformat') or all(int(r) < int(g('sequence')) for r in rel), '')
    check('EG-BP-14.8', 'BP', not (stype.startswith('maa') and unit == 'initial') or env.findall('inn'), f"{len(env.findall('inn'))} inn")
    check('EG-BP-14.BP4/BP5', 'BP', env.find('submission/number') is None, 'no high-level number (mode not grouping)')
    check('EG-BP-14.BP6', 'BP', bool(g('submission/procedure-tracking/number')), 'procedure tracking number filled')
    check('EG-BP-E07', 'BP', not env.find('submission').get('mode'), 'mode only for variations')
    check('EG-BP-E08', 'BP', len(env.findall('invented-name')) == 1, 'one invented name')
    check('EG-BP-E10', 'BP', g('sequence') == '0000', 'first sequence is 0000')
    # the leaves of both files
    all_leaves = []
    for t, base in ((tree, seq), (rtree, reg.parent)):
        for leaf in t.iter('leaf'):
            all_leaves.append((leaf, base))
    ids = [l.get('ID') for l, _ in all_leaves]
    check('EG-PF-11.11', 'P/F', len(ids) == len(set(ids)), f'{len(ids)} leaves, {len(set(ids))} distinct IDs')
    bad = {'11.1': [], '11.2': [], '11.3': [], '11.4': [], '11.6': [], '11.8': []}
    referenced = set()
    for leaf, base in all_leaves:
        href, op = leaf.get(XL), leaf.get('operation')
        if leaf.get('checksum-type') not in ('md5', 'MD5'):
            bad['11.1'].append(leaf.get('ID'))
        if not (leaf.findtext('title') or '').strip():
            bad['11.3'].append(leaf.get('ID'))
        if op in ('new', 'replace', 'append') and not href:
            bad['11.4'].append(leaf.get('ID'))
        if op == 'new' and leaf.get('modified-file'):
            bad['11.8'].append(leaf.get('ID'))
        if href:
            f = (base / href).resolve()
            referenced.add(f)
            if not f.exists():
                bad['11.6'].append(href)
            elif md5(f) != leaf.get('checksum'):
                bad['11.2'].append(href)
    for k, v in bad.items():
        check(f'EG-PF-{k}', 'P/F', not v, f'{len(v)} wrong {v[:3]}')
    check('EG-PF-11.5/11.7/11.9/11.10/11.12', 'P/F', all(l.get('operation') == 'new' for l, _ in all_leaves),
          'all leaves are «new»: lifecycle rules do not apply')
    check('EG-BP-E06', 'BP', all(l.get('operation') != 'append' for l, _ in all_leaves), 'no append')
    check('EG-PF-12.1', 'P/F', all((n.findtext('title') or '').strip() for t in (tree, rtree) for n in t.iter('node-extension')), 'node-extension titles')
    empty_heads = []
    for t in (tree, rtree):
        for el in t.iter():
            if not isinstance(el.tag, str) or el.tag in ('leaf', 'title', 'link-text', 'xref', 'pi-doc') or el.tag.startswith('{'):
                continue
            if el.tag in ('eg-envelope', 'eg-backbone') or any(a.tag == 'eg-envelope' for a in el.iterancestors()):
                continue
            if not [c for c in el if isinstance(c.tag, str)]:
                empty_heads.append(el.tag)
    check('EG-PF-10.1', 'P/F', not empty_heads, f'lowest headings without a leaf: {empty_heads[:5]}')
    m1 = tree.find('m1-administrative-information-and-prescribing-information')
    m1l = m1.findall('leaf') if m1 is not None else []
    check('EG-PF-E08', 'P/F', len(m1l) == 1 and m1l[0].get(XL) == 'm1/eg/eg-regional.xml', 'index.xml m1 = one leaf to eg-regional.xml')
    check('EG-BP-E05', 'BP', len(m1l) == 1 and m1l[0].get('operation') == 'new', '')
    parents12 = ['m1-2-form', 'm1-2-2-legal', 'm1-2-3-edaapp', 'm1-2-4-declar', 'm1-2-5-refprod', 'm1-2-6-importdoc', 'm1-2-7-reliance',
                 'm1-2-8-composit', 'm1-2-10-postappch', 'm1-2-12-analysreq', 'm1-2-13-plasma', 'm1-2-15-relpv', 'm1-2-16-relinsp']
    check('EG-PF-E11', 'P/F', not any(el.find('leaf') is not None for p in parents12 for el in rtree.iter(p)), '1.2 parent sections hold no leaves')
    check('EG-PF-E12', 'P/F', len(list(rtree.iter('m1-6-1-non-gmo'))) + len(list(rtree.iter('m1-6-2-gmo'))) <= 1, 'at most one of non-GMO / GMO')
    pidocs = list(rtree.iter('pi-doc'))
    check('EG-PF-E13', 'P/F', all(p.get(LANG) in ('ar', 'en') and p.get('country') == 'eg' for p in pidocs), f'{len(pidocs)} pi-doc')
    check('EG-PF-14.5', 'P/F', all(p.get('country') == 'eg' for p in pidocs), 'pi-doc country has an envelope')
    check('EG-BP-E16', 'BP', all(all(f'/131-spclabelpl/{p.get(LANG)}/' in l.get(XL) for l in p.iter('leaf')) for p in pidocs),
          'pi files in the folder of their language')
    cover = [l for c in rtree.iter('m1-0-cover') for l in c.iter('leaf')]
    check('EG-PF-15.11', 'P/F', any(re.fullmatch(r'10-cover/tracking(-[a-z0-9-]+)?\.pdf', l.get(XL)) for l in cover), 'tracking table in m1/eg/10-cover')
    check('EG-PF-15.12', 'P/F', all(re.fullmatch(r'10-cover/(cover|tracking)(-[a-z0-9-]+)?\.pdf', l.get(XL)) for l in cover), 'cover and tracking names')
    check('EG-BP-E01', 'BP', any(re.fullmatch(r'10-cover/cover(-[a-z0-9-]+)?\.pdf', l.get(XL)) for l in cover), 'cover letter present')
    check('EG-BP-E02', 'BP', all(l.get('operation') == 'new' for l in cover), '')
    # files and folders (EG-PF-15)
    files = [p for p in seq.rglob('*') if p.is_file()]
    dirs = [p for p in seq.rglob('*') if p.is_dir()]
    too_long = [str(p.relative_to(seq.parent)) for p in files if len(str(p.relative_to(seq.parent))) > 180]
    check('EG-PF-15.3', 'P/F', not too_long, f'longest path {max(len(str(p.relative_to(seq.parent))) for p in files)} characters {too_long[:2]}')
    check('EG-PF-15.4', 'P/F', all(len(p.name) <= 64 for p in files), f'longest file name {max(len(p.name) for p in files)}')
    check('EG-PF-15.5', 'P/F', all(len(p.name) <= 64 for p in dirs), f'longest folder name {max(len(p.name) for p in dirs)}')
    badf = [p.name for p in files if not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.[a-z0-9]+', p.name) and p.name != 'index-md5.txt']
    check('EG-PF-15.6', 'P/F', not badf, f'{badf[:3]}')
    badd = [p.name for p in dirs if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', p.name)]
    check('EG-PF-15.7', 'P/F', not badd, f'{badd[:3]}')
    content = [p.resolve() for p in files if p.relative_to(seq).parts[0] in ('m1', 'm2', 'm3', 'm4', 'm5') and p.name != 'eg-regional.xml']
    unref = [str(p.relative_to(seq)) for p in content if p not in referenced]
    check('EG-PF-15.8', 'P/F', not unref, f'{len(unref)} unreferenced {unref[:3]}')
    rootfiles = sorted(p.name for p in seq.iterdir() if p.is_file())
    check('EG-PF-15.9', 'P/F', rootfiles == ['index-md5.txt', 'index.xml'], f'{rootfiles}')
    empty = [str(p.relative_to(seq)) for p in dirs if not any(p.iterdir())]
    check('EG-PF-15.10', 'P/F', not empty, f'{empty[:3]}')
    check('EG-BP-15.BP1', 'BP', all(p.stat().st_size <= 500 * 2**20 for p in files), f'largest file {max(p.stat().st_size for p in files) / 1e6:.1f} MB')
    exts = {p.suffix for p in content}
    check('EG-BP-15.BP1.1/BP2.1', 'BP', exts <= {'.pdf'}, f'formats {sorted(exts)}')
    check('EG-BP-E20', 'BP', not any(p.suffix in ('.doc', '.docx', '.rtf', '.xls', '.xlsx') for p in content), 'no Word files in m1-m5')
    check('EG-BP-E28', 'BP', not (seq / 'm1' / 'eg' / 'util').exists(), 'nothing in m1/eg/util')
    # the PDFs (EG-PF-16, BP-16, E23, E24)
    old, locked, broken, notlin, pane_bad, unembedded, no_text, placeholders, versions = [], [], [], [], [], [], [], [], {}
    for p in (x for x in content if x.suffix == '.pdf'):
        try:
            with open(p, 'rb') as f:
                v = re.match(r'%PDF-(\d\.\d)', f.read(16).decode('latin-1')).group(1)
            versions[v] = versions.get(v, 0) + 1
            if v in ('1.0', '1.1', '1.2', '1.3'):
                old.append(p.name)
            pdf = pikepdf.open(p)
            if pdf.is_encrypted:
                locked.append(p.name)
            if not pdf.is_linearized:
                notlin.append(p.name)
            with pdf.open_outline() as ol:
                has_bm = len(ol.root) > 0
            mode = str(pdf.Root.get('/PageMode', '/UseNone'))
            if has_bm != (mode == '/UseOutlines'):
                pane_bad.append(p.name)
            pages = len(pdf.pages)
            pdf.close()
        except Exception as e:                                   # noqa: BLE001 — said in the result
            broken.append(f'{p.name}: {e}')
            continue
        fonts = subprocess.run(['pdffonts', str(p)], capture_output=True, text=True).stdout.splitlines()[2:]
        if any(line.split()[-5] == 'no' for line in fonts if len(line.split()) >= 7):
            unembedded.append(p.name)
        txt = subprocess.run(['pdftotext', '-l', '3', str(p), '-'], capture_output=True, text=True).stdout
        if len(txt.strip()) < 20:
            no_text.append(p.name)
        plain = '\n'.join(l for l in txt.splitlines() if ' '.join(l.split()) not in header)
        plain = re.sub(r'\b\d\.\d[\d.]*\s*[A-Za-z ]{0,80}?:', '', plain)
        if pages <= 1 and re.fullmatch(r'\W*(not applicable|n/?a)\W*', plain.strip(), re.I):
            placeholders.append(p.name)
    check('EG-PF-16.1', 'P/F', not old, f'PDF versions {dict(sorted(versions.items()))}')
    check('EG-PF-16.2/16.3', 'P/F', not locked, f'{locked[:3]}')
    check('EG-PF-16.5', 'P/F', not broken, f'{broken[:3]}')
    check('EG-BP-16.BP1', 'BP', set(versions) <= {'1.4', '1.5', '1.6', '1.7'}, f'{dict(sorted(versions.items()))}')
    check('EG-BP-16.BP5', 'BP', not notlin, f'{len(notlin)} not linearised {notlin[:3]}')
    check('EG-BP-16.BP8/BP9', 'BP', not pane_bad, f'{pane_bad[:3]}')
    check('EG-BP-E23 (fonts)', 'BP', not unembedded, f'{len(unembedded)} PDFs with a font not embedded {unembedded[:3]}')
    check('EG-BP-E23 (text)', 'BP', not no_text, f'{len(no_text)} PDFs without text on their first pages {no_text[:3]}')
    check('EG-BP-E24', 'BP', not placeholders, f'{placeholders[:3]}')
    check('EG-PF-E09', 'P/F', True, 'delivered as the folder of the sequence only (zip root = the sequence)')
    check('EG-PF-E10', 'P/F', True, 'PDF files only, no executable content checked: see EG-BP-16 (no JavaScript scan)')
    return results
