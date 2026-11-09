"""Check a sequence folder against (a) the ICH XSD, (b) a subset of ICH eCTD v4.0 business rules (IG v1.7 §12),
(c) the EG provisional regional rules of ../rules.md, using the YAML vocabularies in ../cv/.
PROVISIONAL tool for the EG v4 profile v0 — not an EDA validator.
Usage: python3 -I check_example.py <sequence_dir> <path to PORP_IN000001UV.xsd>
"""
import hashlib, os, re, sys
import yaml
from lxml import etree

SEQ, XSD = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
CV = os.path.join(HERE, '..', 'cv')
NS = {'h': 'urn:hl7-org:v3'}
UUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
NAME_OK = re.compile(r"^[a-z0-9$\-_+!'()./]+$")
res = []
def rule(rid, ok, msg=''):
    res.append((rid, 'PASS' if ok else 'FAIL', msg))

y = lambda f: yaml.safe_load(open(os.path.join(CV, f), encoding='utf-8'))
cou = {c['code']: c for c in y('eg-m1-context-of-use.yaml')['codes']}
cou_oid = y('eg-m1-context-of-use.yaml')['code_system']['oid']
su_codes = {c['code'] for c in y('eg-submission-units.yaml')['codes']}
st = y('eg-submission-types.yaml')
st_codes = {c['code'] for c in st['codes']}
app_codes = {c['code'] for c in y('eg-application-types.yaml')['codes']}

# ICH eCTD4-059/060/061/063 package
xmlp = os.path.join(SEQ, 'submissionunit.xml')
rule('eCTD4-059', os.path.isfile(xmlp)); rule('eCTD4-060', os.path.isfile(os.path.join(SEQ, 'sha256.txt')))
raw = open(xmlp, 'rb').read()
rule('eCTD4-062', open(os.path.join(SEQ, 'sha256.txt')).read().strip().lower() == hashlib.sha256(raw).hexdigest(), 'sha256.txt vs computed')
# eCTD4-001/002 schema
doc = etree.fromstring(raw)
schema = etree.XMLSchema(etree.parse(XSD))
ok = schema.validate(etree.ElementTree(doc)); rule('eCTD4-001/002', ok, str(schema.error_log) if not ok else 'XSD PORP_IN000001UV.xsd')
x = lambda p: doc.xpath(p, namespaces=NS)
su = x('/h:PORP_IN000001UV/h:controlActProcess/h:subject/h:submissionUnit')
rule('eCTD4-005', len(su) == 1); su = su[0]
rule('eCTD4-003/004', bool(UUID.match(su.find('h:id', NS).get('root'))))
code = su.find('h:code', NS)
rule('eCTD4-006/007 (EG list)', code is not None and code.get('code') in su_codes, code.get('code'))
rule('eCTD4-010', su.find('h:statusCode', NS).get('code') == 'active')
comps = su.findall('h:component', NS); rule('eCTD4-011', len(comps) >= 1)
seq = su.xpath('h:componentOf1/h:sequenceNumber/@value', namespaces=NS)
rule('eCTD4-012/013', len(seq) == 1 and seq[0].isdigit() and 1 <= int(seq[0]) <= 999999, seq[0] if seq else '')
rule('EG-V4-002 folder = sequence', seq and os.path.basename(os.path.normpath(SEQ)) == seq[0])
docs = {d.find('h:id', NS).get('root'): d for d in x('//h:application/h:component/h:document')}
kwdefs = {(i.get('code'), i.get('codeSystem')): kd.find('h:code', NS).get('code')
          for kd in x('//h:application/h:referencedBy/h:keywordDefinition') for i in kd.findall('h:value/h:item', NS)}
used_docs = set(); ids = []
for c in comps:
    pn = c.find('h:priorityNumber', NS).get('value')
    rule('eCTD4-017/018', pn.isdigit() and 1 <= int(pn) <= 999999, pn)
    cu = c.find('h:contextOfUse', NS); cid = cu.find('h:id', NS).get('root'); ids.append(cid)
    rule('eCTD4-020/021', bool(UUID.match(cid)), cid)
    cc = cu.find('h:code', NS); ccode, ccs = cc.get('code'), cc.get('codeSystem')
    rule('eCTD4-022/023', cu.find('h:statusCode', NS).get('code') in ('active', 'suspended'))
    dref = cu.xpath('h:derivedFrom/h:documentReference/h:id/@root', namespaces=NS)
    rule('eCTD4-027/076', len(dref) == 1 and dref[0] in docs, ccode); used_docs.update(dref)
    kws = [(k.get('code'), k.get('codeSystem')) for k in cu.findall('h:referencedBy/h:keyword/h:code', NS)]
    if ccs == cou_oid:
        e = cou.get(ccode)
        rule('eCTD4-075 (EG CoU)', e is not None, ccode)
        if e:
            rule('EG-V4-022 documents allowed on heading', e['documents_allowed'], ccode)
            allowed = {}
            for kt in e['keyword_types']:
                allowed[kt['code_system'] if 'keyword_definition_type' not in kt else kt['keyword_definition_type']] = kt
            seen = []
            for kc, kcs in kws:
                t = kwdefs.get((kc, kcs))
                key = t if t else kcs
                kt = allowed.get(key)
                rule('eCTD4-071 keyword type allowed', kt is not None, f'{ccode}:{kc}')
                if kt and 'allowed_values' in kt:
                    rule('EG-V4-023 keyword value in EG list', kc in kt['allowed_values'], f'{ccode}:{kc}')
                seen.append(key)
            rule('eCTD4-072 one keyword per type', len(seen) == len(set(seen)), ccode)
            for k, kt in allowed.items():
                if kt['cardinality'] == 'R':
                    rule('eCTD4-070 required keyword present', k in seen, f'{ccode}:{kt["type"]}')
    else:
        rule('ICH CoU list (not checked in detail)', ccs == '2.16.840.1.113883.3.989.2.2.1.1.6', ccode)
        for kc, kcs in kws:
            rule('eCTD4-032 keyword code defined', (kc, kcs) in kwdefs or kcs.startswith('2.16.840.1.113883.3.989.2.2.1.'), kc)
rule('eCTD4-020 CoU ids unique', len(ids) == len(set(ids)))
for did, d in docs.items():
    rule('eCTD4-043..046', bool(UUID.match(did)), did)
    rule('eCTD4-047', d.find('h:title', NS) is not None)
    t = d.find('h:text', NS); ref = t.find('h:reference', NS).get('value'); p = os.path.join(SEQ, ref)
    rule('eCTD4-050/051', os.path.isfile(p), ref)
    if os.path.isfile(p):
        rule('eCTD4-064', hashlib.sha256(open(p, 'rb').read()).hexdigest() == t.find('h:integrityCheck', NS).text.strip(), ref)
    rule('eCTD4-065 file name <= 64', len(os.path.basename(ref)) <= 64, ref)
    rule('eCTD4-067 path <= 180 (from first-level folder; +1 seq folder here)', len(ref) + len(seq[0]) + 1 <= 180, ref)
    rule('eCTD4-074 characters / lower case', bool(NAME_OK.match(ref)), ref)
    rule('EG-V4-020 text@language ar|en', t.get('language') in ('ar', 'en'), ref)
    rule('eCTD4-082 new document referenced by a CoU in this SU', did in used_docs, did)
files = {os.path.relpath(os.path.join(r, f), SEQ) for r, _, fs in os.walk(SEQ) for f in fs} - {'submissionunit.xml', 'sha256.txt'}
refs = {d.find('h:text/h:reference', NS).get('value') for d in docs.values()}
rule('eCTD4-069 no unassociated file', files <= refs, str(files - refs))
sub = su.find('h:componentOf1/h:submission', NS)
rule('eCTD4-033/077', all(UUID.match(i.get('root')) for i in sub.findall('h:id/h:item', NS)))
rule('EG-V4-040 one submission id item (EU-IG "Submission")', len(sub.findall('h:id/h:item', NS)) == 1)
sc = sub.find('h:code', NS).get('code'); rule('eCTD4-034..037 (EG list)', sc in st_codes, sc)
needs_mode = ('eg_st_' + t for t in st['mode_required_for']['tokens'])
rule('EG-V4-041 mode present for variation types', (sc not in set(needs_mode)) or sub.find('h:subject3/h:mode', NS) is not None, sc)
rule('EG-V4-042 at least one contact party (EU-IG "Contact Party")', len(sub.findall('h:callBackContact', NS)) >= 1)
if code.get('code') == 'eg_su_initial' and sc.startswith('eg_st_maa'):
    rule('EG-V4-043 review with product name for initial MAA', bool(sub.xpath('h:subject2/h:review/h:subject1/h:manufacturedProduct/h:manufacturedProduct/h:name', namespaces=NS)))
    pcs = sub.xpath('h:subject2/h:review/h:subject2/h:productCategory/h:code/@codeSystem', namespaces=NS)
    rule('EG-V4-044 registration + marketing type present', len(pcs) == 2 and len(set(pcs)) == 2)
ap = sub.find('h:componentOf/h:application', NS)
rule('eCTD4-038', bool(ap.findall('h:id/h:item', NS)))
rule('eCTD4-039..042 (EG list)', ap.find('h:code', NS).get('code') in app_codes)
rule('EG-V4-045 recipient EG-EDA', bool(ap.xpath('h:informationRecipient/h:territorialAuthority/h:governingAuthority/h:id[@extension="EG-EDA"]', namespaces=NS)))
for kd in x('//h:keywordDefinition'):
    rule('eCTD4-057 exactly one value item', len(kd.findall('h:value/h:item', NS)) == 1)
    rule('eCTD4-058 displayName', kd.find('h:value/h:item/h:displayName', NS) is not None)
hdr = x('/h:PORP_IN000001UV/h:receiver/h:device/h:id/h:item/@root')
rule('eCTD4-084 two header OIDs present', len(hdr) == 2, ' | '.join(hdr))
placeholders = sorted(set(re.findall(rb'[0-9.]+x\.EG-PLACEHOLDER[0-9.]*', raw)))
rule('eCTD4-008/009/031/081/083/084 registered OIDs', not placeholders,
     f'{len(placeholders)} distinct EG-PLACEHOLDER OIDs - EXPECTED FAIL until EDA registers OIDs')
w = max(len(r[0]) for r in res)
for r in res:
    print(f'{r[1]}  {r[0]:<{w}}  {r[2]}')
print(f'\n{sum(r[1] == "PASS" for r in res)} PASS / {sum(r[1] == "FAIL" for r in res)} FAIL')
