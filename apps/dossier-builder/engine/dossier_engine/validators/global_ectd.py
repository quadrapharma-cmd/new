"""The eCTD 3.2.2 check for a sequence from any country, in two layers, each said in the report:

  1. ICH — what every eCTD in every region must pass, whoever receives it: ICH's own validator checklist (eCTD Q&A 36), the
     naming, checksum and life-cycle rules of the eCTD specification v3.2.2, and the format rules (ICH M2 FMT v1.3, which
     replaces the specification's Appendix 7). This layer also reads the region's Module 1 the way any authority would: the
     regional XML in its folder, valid against the regional DTD the sequence carries, its files there with their MD5, its
     sequence number. Rules and sources: docs/ctd/ectd/ICH-eCTD-3.2.2-reference.md (SPEC = the specification, QA = the Q&A).
  2. The authority's own criteria, where the program has them: the EU (validation criteria 8.2, official), Egypt (the program's
     provisional profile: EDA has published no criteria), the GCC (its specification's DTD and codes). For any other region
     the report names the criteria that authority publishes (rulepacks/countries.yaml) and says they were not run.

    validate(sequence folder, previous=[earlier sequence folders]) → {'region', 'country', 'authority', 'criteria', 'layers', 'ok'}
    python -m dossier_engine.validators.global_ectd <sequence folder> [--previous <folder>]… [--html <file>]

A check like this is not an authority's own validator: the report says so."""
import hashlib
import re
import sys
from pathlib import Path

import yaml
from lxml import etree

XLINK = '{http://www.w3c.org/1999/xlink}href'          # the namespace the ICH DTD fixes («w3c.org», as written in the DTD)
XLINK_W3 = '{http://www.w3.org/1999/xlink}href'        # the W3C's own: a common slip the DTD does not accept
ICH_DTD_MD5 = '1d6f631cc6b6357f0f4fe378e5f79a27'      # ich-ectd-3-2.dtd (KB §0; the value the EU and GCC profiles use too)
ICH_XSL_MD5 = '3a07a202455e954a2eb203c5bb443f77'      # ectd-2-0.xsl
NAME = re.compile(r'[a-z0-9-]+')
PF, BP = 'pass_fail', 'best_practice'
MB = 1024 * 1024
REGIONS = {'eu': 'EU', 'eg': 'EG', 'gc': 'GCC', 'us': 'US', 'ca': 'CA', 'ch': 'CH', 'au': 'AU', 'jp': 'JP', 'jo': 'JO'}
COUNTRIES = Path(__file__).resolve().parents[3] / 'rulepacks' / 'countries.yaml'

# id, kind, what is checked (English · formal Arabic), where it is written
RULES = [
    ('ICH-Q36-01', PF, 'index.xml and index-md5.txt are in the sequence folder · الملفان index.xml وindex-md5.txt في مجلد التسلسل',
     'QA 36 item 1; SPEC App 2 p. 2-1'),
    ('ICH-Q36-02', PF, 'The eCTD DTD in util/dtd is ICH\'s ich-ectd-3-2.dtd unchanged (the MD5 the EU, Egypt and GCC profiles check); '
     'the stylesheet ectd-2-0.xsl beside it (a warning only) · ملف DTD في util/dtd هو ich-ectd-3-2.dtd الصادر عن ICH دون تغيير، ومعه '
     'ectd-2-0.xsl', 'QA 36 item 2; QA 50; SPEC App 6 Table 6-2; EU VC 1.3, 2.3'),
    ('ICH-Q36-03', PF, 'index.xml is well formed, valid against that DTD, and its DOCTYPE points to it · index.xml سليم البنية '
     'ومطابق لذلك الـ DTD ويشير إليه', 'QA 36 item 3; SPEC App 6'),
    ('ICH-Q36-04', PF, 'Leaf attributes agree: ID, operation, checksum and checksum-type (md5) present; new without modified-file; '
     'append, replace and delete with one; new, append and replace with an xlink:href; IDs start with a letter or «_» · سمات '
     'الأوراق متسقة', 'QA 36 item 4; QA 49; SPEC Table 6-3, Table 6-8'),
    ('ICH-Q36-05', PF, 'The regional Module 1 file m1/xx/xx-regional.xml is in its folder · ملف Module 1 الإقليمي في مجلده',
     'QA 36 item 5; SPEC App 5'),
    ('ICH-Q36-07', PF, 'The regional XML is well formed and valid against the regional DTD (or schema) the sequence carries in util/dtd · '
     'الملف الإقليمي مطابق للـ DTD الإقليمي الموجود في التسلسل', 'QA 36 items 6-7, 10'),
    ('ICH-Q36-11', PF, 'Every file\'s MD5 equals its leaf\'s checksum; index-md5.txt holds the MD5 of index.xml and nothing else · '
     'بصمة كل ملف تساوي ما في ورقته، وindex-md5.txt يحمل بصمة index.xml وحدها', 'QA 36 item 11; QA 48; SPEC p. 2-2, p. 5-2'),
    ('ICH-Q36-12', PF, 'Every xlink:href points to a file that exists · كل إحالة تشير إلى ملف موجود', 'QA 36 item 12'),
    ('ICH-Q36-13', PF, 'No file in m1-m5 is left without a leaf · لا ملف في m1-m5 بلا ورقة تشير إليه', 'QA 36 item 13'),
    ('ICH-Q36-15', PF, 'Names: a-z, 0-9 and «-» only, one extension, at most 64 characters; paths at most 230 characters · الأسماء '
     'بحروف صغيرة وأرقام و«-» وامتداد واحد وحتى 64 حرفًا، والمسار حتى 230 حرفًا', 'QA 36 item 15; SPEC App 2 pp. 2-3/2-4'),
    ('ICH-Q36-16', PF, 'Every lowest-level heading in index.xml holds at least one leaf · كل عنوان في أدنى مستوى فيه ورقة واحدة على الأقل',
     'QA 36 item 16'),
    ('ICH-Q36-17', PF, 'No file is larger than 500 MB (above 100 MB, the 2009 checklist\'s line, a warning) · لا ملف أكبر من 500 ميجابايت',
     'QA 36 item 17; SPEC App 7 p. 7-1; ICH M2 FMT v1.3 §2.3'),
    ('ICH-Q36-18', PF, 'The sequence folder is a four-digit number · اسم مجلد التسلسل أربعة أرقام', 'QA 36 item 18'),
    ('ICH-Q36-19', PF, 'The sequence folder equals the sequence number in the regional XML · اسم المجلد يساوي رقم التسلسل في الملف '
     'الإقليمي', 'QA 36 item 19 (not Japan)'),
    ('ICH-Q36-20', PF, 'Leaf and node-extension titles are not empty (a delete leaf aside) · عناوين الأوراق غير فارغة', 'QA 36 item 20'),
    ('ICH-Q36-21', PF, 'No file has a password or security settings · لا ملف عليه كلمة مرور أو قيود حماية',
     'QA 36 item 21; SPEC App 7 p. 7-4; FMT v1.3 §2.17'),
    ('ICH-Q36-22', BP, 'PDF links and bookmarks are relative and keep the reader\'s zoom · روابط PDF نسبية وتحفظ تكبير القارئ',
     'QA 36 item 22; SPEC App 7 pp. 7-3/7-4; FMT v1.3 §2.13'),
    ('ICH-Q36-23', BP, 'PDFs are optimised for fast web view and open as QA 55 asks · ملفات PDF محسّنة للعرض السريع',
     'QA 36 item 23; QA 55; FMT v1.3 §2.15-2.16'),
    ('ICH-FMT-01', PF, 'Every PDF opens and is version 1.4 to 1.7 · كل ملف PDF يُفتح وإصداره من 1.4 إلى 1.7', 'QA 71; FMT v1.3 §2.2'),
    ('ICH-FMT-02', PF, 'No JavaScript, portfolio, attachment or other active content · لا JavaScript ولا مرفقات ولا محتوى نشط',
     'FMT v1.3 §2.1'),
    ('ICH-FMT-03', BP, 'Fonts are embedded · الخطوط مضمَّنة', 'SPEC App 7 pp. 7-1/7-2; FMT v1.3 §2.4'),
    ('ICH-FMT-04', BP, 'Documents of more than five pages have bookmarks · المستند الذي يزيد على خمس صفحات له علامات مرجعية',
     'SPEC App 7 pp. 7-3/7-4; FMT v1.3 §2.13 (bookmarks expected even without a table of contents; five pages is the program\'s line)'),
    ('ICH-FMT-05', BP, 'The text can be searched (not an image only) · النص قابل للبحث وليس صورة فحسب', 'SPEC App 7 p. 7-3; FMT v1.3 §2.8'),
]
TEXT = {r[0]: r for r in RULES}
PDF_CODES = {           # the program's PDF check (checks/pdf.py) → (the ICH rule it shows, blocking: True / False / None = as found)
    'EG-PF-16.5': ('ICH-FMT-01', True), 'EG-PF-16.1': ('ICH-FMT-01', True), 'EG-BP-16.BP1': ('ICH-FMT-01', False),
    'PDF-REPAIR': ('ICH-FMT-01', False),
    'EG-PF-16.2': ('ICH-Q36-21', True), 'EG-PF-16.3': ('ICH-Q36-21', True),
    'PDF-JS': ('ICH-FMT-02', True), 'EG-BP-E23': ('ICH-FMT-02', True), 'PDF-ATTACH': ('ICH-FMT-02', None),
    'PDF-ANNOT': ('ICH-FMT-02', False),
    'PDF-FONTS': ('ICH-FMT-03', False), 'PDF-ZOOM': ('ICH-Q36-22', False), 'PDF-VIEW': ('ICH-Q36-23', False),
    'PDF-SIZE': ('ICH-Q36-17', False),
}
LOCAL = re.compile(r'\s*\((?:EDA|EG|NP\.)[^)]*\)')      # an Egyptian source named in a finding's text: the ICH rule carries its own


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def summarise(results, label_ok, label_bad):
    count = {k: sum(1 for r in results if r['status'] == k) for k in ('pass', 'fail', 'warning', 'not_run')}
    return {'ok': count['fail'] == 0, 'counts': count, 'coverage': f"{len(results) - count['not_run']}/{len(results)}",
            'label': label_ok if count['fail'] == 0 else label_bad, 'results': results}


def regional_xml(seq):
    """(region code, path) of m1/xx/xx-regional.xml, or (None, None)."""
    for p in sorted((seq / 'm1').glob('*/*-regional.xml')) if (seq / 'm1').is_dir() else []:
        if p.name == f'{p.parent.name}-regional.xml':
            return p.parent.name, p
    return None, None


def country(region):
    """The authority's row in rulepacks/countries.yaml (its criteria and how sure that is)."""
    code = REGIONS.get(region, (region or '').upper())
    try:
        rows = yaml.safe_load(COUNTRIES.read_text(encoding='utf-8'))['countries']
    except (OSError, KeyError, yaml.YAMLError):
        rows = []
    row = next((r for r in rows if r.get('code') == code), {})
    return code, row


def parse(path, dtd=None):
    """(tree, errors): well formed, and valid against `dtd` when one is given."""
    try:
        tree = etree.parse(str(path), etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False))
    except (OSError, etree.XMLSyntaxError) as e:
        return None, [f'{path.name}: {e}']
    if dtd is None:
        return tree, []
    try:
        d = etree.DTD(str(dtd))
    except (OSError, etree.DTDParseError) as e:
        return tree, [f'{dtd.name}: {e}']
    return tree, [] if d.validate(tree) else [f'{path.name}: {e.message} (line {e.line})' for e in d.error_log.filter_from_errors()][:20]


XSI = '{http://www.w3.org/2001/XMLSchema-instance}'


def regional_valid(tree, xml, seq):
    """The regional XML against what it names itself: the DTD of its DOCTYPE, or the schema of its xsi:schemaLocation; the file
    must be in the sequence (util/dtd). (errors, why it was not run): a schema that cannot be read here (it imports from the web)
    is said, not failed."""
    sid = tree.docinfo.system_url or ''
    root = tree.getroot()
    xsd = (root.get(XSI + 'noNamespaceSchemaLocation') or (root.get(XSI + 'schemaLocation') or '').split()[-1:] or [''])
    xsd = xsd if isinstance(xsd, str) else xsd[0]
    name = sid or xsd
    if not name:
        return [f'{xml.name} names no DTD (DOCTYPE) and no schema (xsi:schemaLocation)'], None
    target = (xml.parent / name).resolve()
    try:
        target.relative_to(seq.resolve())
    except ValueError:
        return [f'the regional {"DTD" if sid else "schema"} «{name}» is outside the sequence'], None
    if not target.is_file():
        return [f'the regional {"DTD" if sid else "schema"} «{name}» is not in the sequence'], None
    if sid:
        return parse(xml, target)[1], None
    try:
        schema = etree.XMLSchema(etree.parse(str(target), etree.XMLParser(no_network=True)))
    except (OSError, etree.XMLSchemaParseError, etree.XMLSyntaxError) as e:
        return [], f'the schema «{name}» could not be read here ({str(e)[:120]})'
    return ([] if schema.validate(tree) else [f'{xml.name}: {e.message} (line {e.line})' for e in schema.error_log][:20]), None


def pdf_checks(files, out):
    """The program's PDF check on every PDF, its findings sorted into the ICH format rules; links, fast web view, bookmarks and
    searchable text read here."""
    from ..checks.pdf import check
    try:
        import pikepdf
    except ImportError:
        pikepdf = None
    for p, rel in files:
        r = check(str(p), doc_class='company_technical', ectd_name=False, authority='OTHER')
        for f in r.findings:
            rid, block = PDF_CODES.get(f.rule, (None, None))
            if rid:
                out[rid].append((f'{rel}: {LOCAL.sub("", f.en)}', f.severity == 'block' if block is None else block))
        pages = r.info.get('pages') or 0
        if pikepdf is None:
            continue
        try:
            with pikepdf.open(str(p)) as pdf:
                if not pdf.is_linearized:
                    out['ICH-Q36-23'].append((f'{rel}: not linearised (fast web view)', False))
                if pages > 5 and not len(pdf.open_outline().root):
                    out['ICH-FMT-04'].append((f'{rel}: {pages} pages, no bookmarks', False))
                absolute = 0
                for page in pdf.pages:
                    for a in page.get('/Annots') or []:
                        act = a.get('/A') or {}
                        target = str(act.get('/URI') or act.get('/F') or '')
                        if re.match(r'(?i)(file:|[a-z]:[\\/]|/)', target):
                            absolute += 1
                if absolute:
                    out['ICH-Q36-22'].append((f'{rel}: {absolute} link(s) with an absolute path', False))
        except Exception as e:                       # a file pikepdf cannot open was already reported by the PDF check
            out['ICH-FMT-01'].append((f'{rel}: {type(e).__name__}', True))
        if pages:
            try:
                from pypdf import PdfReader
                rd = PdfReader(str(p), strict=False)
                if not any((rd.pages[i].extract_text() or '').strip() for i in range(min(3, len(rd.pages)))):
                    out['ICH-FMT-05'].append((f'{rel}: no text on its first pages (image only?)', False))
            except Exception:
                pass


def ich_layer(seq, previous=()):
    seq = Path(seq)
    out = {r[0]: [] for r in RULES}                 # rule → [(failure, blocking)]
    not_run = {}
    if not re.fullmatch(r'\d{4}', seq.name):
        out['ICH-Q36-18'].append((f'folder «{seq.name}»', True))
    idx, md5f = seq / 'index.xml', seq / 'index-md5.txt'
    for f in (idx, md5f):
        if not f.is_file():
            out['ICH-Q36-01'].append((f'{f.name} missing', True))
    dtd, xsl = seq / 'util' / 'dtd' / 'ich-ectd-3-2.dtd', seq / 'util' / 'style' / 'ectd-2-0.xsl'
    for f, want, block in ((dtd, ICH_DTD_MD5, True), (xsl, ICH_XSL_MD5, False)):
        if not f.is_file():
            out['ICH-Q36-02'].append((f'{f.relative_to(seq).as_posix()} missing', block))
        elif md5(f) != want:
            out['ICH-Q36-02'].append((f'{f.relative_to(seq).as_posix()}: MD5 {md5(f)}, ICH\'s file has {want}', block))
    tree = None
    if idx.is_file():
        tree, errs = parse(idx, dtd if dtd.is_file() else None)
        out['ICH-Q36-03'] += [(e, True) for e in errs]
        if not dtd.is_file():
            not_run['ICH-Q36-03'] = 'util/dtd/ich-ectd-3-2.dtd is not in the sequence (ICH-Q36-02): index.xml could not be validated against it'
        if tree is not None and not (tree.docinfo.system_url or '').endswith('util/dtd/ich-ectd-3-2.dtd'):
            out['ICH-Q36-03'].append((f'DOCTYPE names «{tree.docinfo.system_url}»', True))
        if md5f.is_file() and md5f.read_bytes() != md5(idx).encode():
            got = md5f.read_bytes()[:40]
            out['ICH-Q36-11'].append((f'index-md5.txt holds {got!r}; index.xml\'s MD5 is {md5(idx)}', True))
    region, reg = regional_xml(seq)
    rtree = None
    if reg is None:                                   # every sequence carries its region's index, even with no Module 1 document
        out['ICH-Q36-05'].append(('no m1/xx/xx-regional.xml' + ('' if (seq / 'm1').is_dir() else ' (no m1 folder)'), True))
    if reg is not None:
        rtree, errs = parse(reg)
        if rtree is not None:
            errs, unread = regional_valid(rtree, reg, seq)
            if unread:
                not_run['ICH-Q36-07'] = unread
        out['ICH-Q36-07'] += [(e, True) for e in errs]
        seqno = [e.text.strip() for e in rtree.iter() if isinstance(e.tag, str) and e.tag.split('}')[-1] in ('sequence', 'sequence-number')
                 and e.text and e.text.strip()] if rtree is not None else []
        if region == 'jp':
            not_run['ICH-Q36-19'] = 'Japan: the sequence folder need not equal a number in the regional XML (QA 36 item 19)'
        elif not seqno:
            not_run['ICH-Q36-19'] = 'the regional XML names no sequence number'
        elif seqno[0] != seq.name:
            out['ICH-Q36-19'].append((f'folder {seq.name}, regional XML {seqno[0]}', True))
    referenced = set()
    ids = {}
    for xml, t in ((idx, tree), (reg, rtree)):
        if t is None:
            continue
        w3 = sum(1 for lf in t.iter('{*}leaf') if lf.get(XLINK_W3) is not None)
        if w3:
            rid = 'ICH-Q36-03' if xml == idx else 'ICH-Q36-07'
            out[rid].append((f'{xml.name}: {w3} leaf href(s) in the namespace http://www.w3.org/1999/xlink; the ICH DTD fixes it as '
                             'http://www.w3c.org/1999/xlink, so a validator reads no xlink:href', True))
        for lf in t.iter('{*}leaf'):                # any namespace: the TGA's regional XML puts its leaves in «tga_ectd»
            op, href = lf.get('operation') or '', lf.get(XLINK) or lf.get(XLINK_W3) or ''
            lid = lf.get('ID') or ''
            where = f'{xml.name} leaf {lid or "?"}'
            for a in ('ID', 'operation', 'checksum-type'):
                if lf.get(a) is None:
                    out['ICH-Q36-04'].append((f'{where}: no {a}', True))
            if lf.get('checksum') is None:
                out['ICH-Q36-04'].append((f'{where}: no checksum', True))
            if lid and not re.match(r'[A-Za-z_]', lid):
                out['ICH-Q36-04'].append((f'{where}: ID does not start with a letter or «_»', True))
            if lid in ids:
                out['ICH-Q36-04'].append((f'{where}: ID used twice', True))
            ids[lid] = 1
            mod = (lf.get('modified-file') or '').strip()
            if op == 'new' and mod:
                out['ICH-Q36-04'].append((f'{where}: new with a modified-file', True))
            if op in ('append', 'replace', 'delete') and not mod:
                out['ICH-Q36-04'].append((f'{where}: {op} without a modified-file', True))
            if op in ('new', 'append', 'replace') and not href:
                out['ICH-Q36-04'].append((f'{where}: {op} without an xlink:href', True))
            if op != 'delete' and (lf.get('checksum-type') or '').lower() not in ('md5', ''):
                out['ICH-Q36-04'].append((f'{where}: checksum-type «{lf.get("checksum-type")}»', True))
            t_el = lf.find('{*}title')
            if op != 'delete' and (t_el is None or not (t_el.text or '').strip()):
                out['ICH-Q36-20'].append((f'{where}: empty title', True))
            if not href or op == 'delete':
                continue
            target = (xml.parent / href).resolve()
            try:
                rel = target.relative_to(seq.resolve()).as_posix()
            except ValueError:
                rel = None
            if rel is None:                           # an earlier sequence, or another application (the region decides, QA 36 item 12)
                if target.is_file():                  # found where it points, beside this sequence: its MD5 is checked too
                    if lf.get('checksum') and lf.get('checksum').lower() != md5(target):
                        out['ICH-Q36-11'].append((f'{href}: MD5 {md5(target)}, the leaf says {lf.get("checksum")}', True))
                elif previous:
                    out['ICH-Q36-12'].append((f'{where}: «{href}» outside this sequence and not found where it points', True))
                else:
                    not_run.setdefault('ICH-Q36-12-outside', f'{where}: «{href}» points to an earlier sequence (none given)')
                continue
            referenced.add(rel)
            if not target.is_file():
                out['ICH-Q36-12'].append((f'{where}: «{rel}» missing', True))
            elif lf.get('checksum') and lf.get('checksum').lower() != md5(target):      # a missing checksum is ICH-Q36-04's
                out['ICH-Q36-11'].append((f'{rel}: MD5 {md5(target)}, the leaf says {lf.get("checksum")}', True))
        for ne in t.iter('{*}node-extension'):
            t_el = ne.find('{*}title')
            if t_el is None or not (t_el.text or '').strip():
                out['ICH-Q36-20'].append((f'{xml.name}: node-extension with an empty title', True))
    if tree is not None:                              # a lowest-level heading present must hold a leaf (QA 36 item 16)
        for el in tree.iter():
            if not isinstance(el.tag, str) or el.tag in ('leaf', 'title', 'node-extension', 'link-text', 'xref'):
                continue
            kids = [k for k in el if isinstance(k.tag, str)]
            if el.getparent() is not None and not kids and el.tag.startswith('m'):
                out['ICH-Q36-16'].append((f'{el.tag} has no leaf', True))
    pdfs = []
    for p in sorted(seq.rglob('*')):
        rel = p.relative_to(seq).as_posix()
        parts = rel.split('/')
        for i, part in enumerate(parts):
            last = i == len(parts) - 1 and p.is_file()
            stem_ext = part.split('.')
            ok = (len(stem_ext) == 2 and all(NAME.fullmatch(x) for x in stem_ext)) if last else bool(NAME.fullmatch(part))
            if not ok and not (last and part in ('index-md5.txt',)):
                out['ICH-Q36-15'].append((f'«{"/".join(parts[:i + 1])}»: not a-z, 0-9, «-»' + (' and one extension' if last else ''), True))
                break
            if len(part) > 64:
                out['ICH-Q36-15'].append((f'«{part}»: {len(part)} characters', True))
                break
        if len(f'{seq.name}/{rel}') > 230:
            out['ICH-Q36-15'].append((f'«{rel}»: path of {len(seq.name) + 1 + len(rel)} characters', True))
        if not p.is_file():
            continue
        if p.stat().st_size > 500 * MB:
            out['ICH-Q36-17'].append((f'{rel}: {p.stat().st_size // MB} MB', True))
        if re.match(r'm[1-5]/', rel) and rel not in referenced and not (reg is not None and p.resolve() == reg.resolve()):
            out['ICH-Q36-13'].append((rel, True))
        if p.suffix.lower() == '.pdf':
            pdfs.append((p, rel))
    pdf_checks(pdfs, out)
    results = []
    for rid, kind, text, source in RULES:
        fails = out[rid]
        if rid in not_run and not fails:
            results.append({'rule': rid, 'severity': kind, 'text': text, 'source': source, 'status': 'not_run',
                            'reason': not_run[rid], 'failures': []})
            continue
        block = any(b for _, b in fails)
        status = 'pass' if not fails else ('fail' if block and kind == PF else 'warning')
        results.append({'rule': rid, 'severity': kind, 'text': text, 'source': source, 'status': status,
                        'failures': [f for f, _ in fails][:50]})
    if 'ICH-Q36-12-outside' in not_run:
        r12 = next(r for r in results if r['rule'] == 'ICH-Q36-12')
        r12['reason'] = 'references to earlier sequences were not followed: give them with --previous'
    return region, summarise(results, 'Passes every ICH check — يجتاز فحوص ICH كلها',
                             'Fails an ICH check: no authority would take it as it is — يرسب في فحص من فحوص ICH')


def validate(seq, previous=None):
    """The two layers for one sequence. `previous`: the earlier sequences of the same application, oldest first; None = not given
    (a first sequence 0000 has none; for a later one the authority's lifecycle rules are then said not run)."""
    seq = Path(seq)
    earlier = [Path(p) for p in previous] if previous is not None else ([] if seq.name == '0000' else None)
    region, ich = ich_layer(seq, earlier or ())
    inherited = None
    if region is None:                                # a later sequence without its regional index: the application's region
        inherited = next((r for r in (regional_xml(Path(p))[0] for p in earlier or ()) if r), None)
        region = inherited
    code, row = country(region)
    authority = row.get('authority') or (f'the authority of region «{region}»' if region else 'no regional Module 1')
    layers = {'1 · ICH — every country': ich}
    own = None
    if region == 'eu':
        from . import ectd32_eu as v
        from ..writers import ectd32_eu as w
        own = v.validate(seq, w.DEFAULT_PROFILE, previous=earlier)
    elif region == 'eg':
        from . import ectd32 as v
        from ..writers import ectd32 as w
        own = v.validate(seq, w.DEFAULT_PROFILE, previous=earlier)
    elif region == 'gc':
        from . import ectd32_gcc as v
        own = v.validate(seq)
    if own is not None:
        layers[f'2 · {authority} — its own criteria'] = own
    criteria = row.get('criteria') or 'unknown'
    return {'region': region, 'region_from_earlier': bool(inherited), 'country': code, 'authority': authority, 'criteria': criteria,
            'evidence': row.get('evidence'), 'own_criteria_run': own is not None, 'layers': layers, 'ok': all(x['ok'] for x in layers.values())}


def note(res):
    if res['own_criteria_run']:
        en = (f"Layer 1 is ICH's, the same in every country. Layer 2 is {res['authority']}'s own ({res['criteria']}; "
              f"evidence: {res['evidence']}). Not an authority's own validator.")
        ar = ('الطبقة الأولى قواعد ICH، وهي نفسها في كل الدول. والطبقة الثانية معايير الجهة نفسها كما يعرفها البرنامج. '
              'وهذه ليست أداة التحقق الخاصة بالجهة.')
    else:
        en = (f"Layer 1 is ICH's, the same in every country. {res['authority']}'s own criteria ({res['criteria']}) are not in the "
              f"program yet: only the ICH layer was run. Not an authority's own validator.")
        ar = ('الطبقة الأولى قواعد ICH، وهي نفسها في كل الدول. ومعايير هذه الجهة نفسها ليست في البرنامج بعد، فلم تُفحص إلا قواعد ICH. '
              'وهذه ليست أداة التحقق الخاصة بالجهة.')
    return en, ar


def html(res, title):
    from . import report
    return report.render(title, res['layers'], note(res))


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__)
        return 1
    seq, prev, out = Path(argv[0]), [], None
    it = iter(argv[1:])
    for a in it:
        if a == '--previous':
            prev.append(Path(next(it)))
        elif a == '--html':
            out = Path(next(it))
    res = validate(seq, prev or None)
    print(f"region: {res['region'] or 'none'}{' (from the earlier sequences)' if res.get('region_from_earlier') else ''} · {res['authority']} · its criteria: {res['criteria']}")
    for name, layer in res['layers'].items():
        c = layer['counts']
        print(f"{name}: {layer['label']} — pass {c['pass']} · fail {c['fail']} · warning {c['warning']} · not run {c['not_run']}")
        for r in layer['results']:
            if r['status'] == 'fail':
                print(f"   {r['rule']}: {r['failures'][:3]}")
    if not res['own_criteria_run']:
        print('the authority\'s own criteria are not in the program: only the ICH layer was run')
    if out:
        out.write_text(html(res, f'{seq.name} — eCTD check for any country'), encoding='utf-8')
        print(f'report: {out}')
    return 0 if res['ok'] else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
