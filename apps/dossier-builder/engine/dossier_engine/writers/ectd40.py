"""Writer 3 — eCTD 4.0 submission unit (HL7 RPS PORP_IN000001UV) with the EG
provisional v4 profile.

Layout (EG-V4-001…011): <app>/<n>/submissionunit.xml + sha256.txt, flat m1/,
M2–M5 folders as App. 4. Headings are contexts of use (CoU): EG M1 codes
(eg_<ctd>) from the provisional CV, M2–M5 ICH codes (CV v1.0.3). Keywords
required by a CoU (R) must be supplied or the build stops; sender-defined
values (substance, manufacturer, product, …) are declared once as keyword
definitions on the application. Every EG OID is a PLACEHOLDER until EDA
registers real ones — the output is labelled provisional.
"""
import csv, hashlib, os, re, shutil, uuid as _uuid
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr
import yaml
from .ectd32 import Doc, Product, Profile32, WriterError, rel_path, slug, REPO, APP
from ..lifecycle import location_key

DEFAULT_V4 = REPO / 'docs' / 'ctd' / 'ectd' / 'EG-PROVISIONAL-PROFILE-v4-v0'
ICH_DIR = APP / 'rulepacks' / 'ich.ectd.v40'
ICH_IG = '2.16.840.1.113883.3.989.2.2.1.11.6'
ICH_COU = '2.16.840.1.113883.3.989.2.2.1.1.6'
ICH_KWT = '2.16.840.1.113883.3.989.2.2.1.5.4'
ICH_DOCTYPE = '2.16.840.1.113883.3.989.2.2.1.3.1'
ICH_CONTROL = '2.16.840.1.113883.3.989.2.2.1.10.1'
KW_TYPE = {'indication': 'ich_keyword_type_1', 'substance': 'ich_keyword_type_2', 'manufacturer': 'ich_keyword_type_3',
           'product': 'ich_keyword_type_4', 'dosage form': 'ich_keyword_type_5', 'excipient': 'ich_keyword_type_6',
           'study id_study title': 'ich_keyword_type_8', 'group title': 'ich_keyword_type_11'}
MAX_NAME, MAX_PATH = 64, 180


@dataclass
class Envelope4:
    application_uuid: str        # = v3.2.2 envelope identifier (same application)
    submission_uuid: str         # one per regulatory activity; responses reuse it
    tracking: str                # EDA procedure tracking number -> submission/id@extension
    submission_type: str         # eg_st_* token without prefix, e.g. maa
    unit: str                    # initial / response / …
    sequence: int                # 1…999999, no padding
    title: str                   # = v3.2.2 submission-description
    applicant: str
    applicant_portal_id: str
    product_name: str
    inn: list
    registration: str            # local / toll / f-toll / under-license / imported-finished / imported-bulk
    marketing: str               # local / tender / export / hospital
    application_type: str = 'eg_application_type_2'
    contact_given: str = 'Regulatory'
    contact_family: str = 'Affairs'
    contact_email: str = 'regulatory@example.invalid'
    first_level: str = None      # EDA application number; default = application UUID


class Profile40:
    def __init__(self, root=DEFAULT_V4, v32=None):
        self.root = Path(root)
        cv = self.root / 'cv'
        self.v32 = v32 or Profile32()
        cou = yaml.safe_load(open(cv / 'eg-m1-context-of-use.yaml', encoding='utf-8'))
        self.eg_cou_oid = cou['code_system']['oid']
        self.eg = {c['ctd_section']: c for c in cou['codes'] if c.get('ctd_section')}
        app = yaml.safe_load(open(cv / 'eg-application-types.yaml', encoding='utf-8'))
        self.app_oid = app['code_system']['oid']
        rl = app['related_lists']
        self.reg = {c['v322_token']: (c['code'], rl['registration_type']['code_system']['oid'])
                    for c in rl['registration_type']['codes']}
        self.mkt = {c['v322_token']: (c['code'], rl['marketing_type']['code_system']['oid'])
                    for c in rl['marketing_type']['codes']}
        self.authority_oid = rl['territorial_authority']['code_system']['oid']
        self.country_oid = rl['territory']['code_system']['oid']
        self.contact_oid = rl['contact_party_role']['code_system']['oid']
        self.org_oid = rl['organisation_identifier']['code_system']['oid']
        st = yaml.safe_load(open(cv / 'eg-submission-types.yaml', encoding='utf-8'))
        self.st_oid, self.st = st['code_system']['oid'], {c['code'] for c in st['codes']}
        su = yaml.safe_load(open(cv / 'eg-submission-units.yaml', encoding='utf-8'))
        self.su_oid, self.su = su['code_system']['oid'], {c['code'] for c in su['codes']}
        self.ich = {}
        for r in csv.DictReader(open(ICH_DIR / 'context-of-use.csv', encoding='utf-8')):
            if r['status'] == 'Active':
                self.ich[r['code']] = _parse_kw(r['keywords'])
        self.doc_types = {r['code'] for r in csv.DictReader(open(ICH_DIR / 'document-type.csv')) if r['status'] == 'Active'}
        self.controls = {r['code'] for r in csv.DictReader(open(ICH_DIR / 'type-of-control.csv')) if r['status'] == 'Active'}

    def cou(self, node):
        """(code, codeSystem, keyword spec[(name, R/O, codeSystem|None, allowed)])"""
        if node.startswith('1.'):
            c = self.eg.get(node)
            if not c or not c.get('documents_allowed'):
                raise WriterError(f'{node}: EG heading does not take documents (EG-V4-022)')
            spec = [(k['type'], k['cardinality'], k.get('code_system'), k.get('allowed_values'))
                    for k in (c.get('keyword_types') or [])]
            return c['code'], self.eg_cou_oid, spec
        parts = node.lower().split('.')
        while parts:
            code = 'ich_' + '.'.join(parts)
            if code in self.ich:
                return code, ICH_COU, [(n, card, None, None) for n, card in self.ich[code]]
            parts.pop()
        raise WriterError(f'{node}: no ICH context of use')


def _parse_kw(s):
    out = []
    for part in (s or '').split(','):
        m = re.match(r'\s*(.+?)\s*\((R|O)\)', part)
        if m:
            out.append((m[1].strip().replace('site-id', 'site id'), m[2]))
    return out


def _sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _u(*parts):
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, '/'.join(map(str, parts))))


def write(out_dir, env: Envelope4, product: Product, docs, profile: Profile40 = None, suspend=None):
    """suspend: [{'cou_id', 'priority'}] contexts of use to suspend (3.2.2 «delete»; IG §9.2.11.3)."""
    p = profile or Profile40()
    if f'eg_st_{env.submission_type}' not in p.st:
        raise WriterError(f'submission type {env.submission_type!r} not in the EG v4 list')
    if f'eg_su_{env.unit}' not in p.su:
        raise WriterError(f'submission unit {env.unit!r} not in the EG v4 list')
    if env.registration not in p.reg or env.marketing not in p.mkt:
        raise WriterError('registration / marketing type not in the EG v4 lists')
    if not (isinstance(env.sequence, int) and 1 <= env.sequence <= 999999):
        raise WriterError('v4 sequence is a whole number 1–999999 (EG-V4-002)')
    first = (env.first_level or env.application_uuid).lower()
    base = Path(out_dir) / first / str(env.sequence)
    if base.exists():
        raise WriterError(f'{base} exists — a sequence is never overwritten')

    sender_cs = '2.25.' + str(_uuid.UUID(env.application_uuid).int)   # UUID-derived OID (X.667)
    kwdefs = {}                                                      # (type, value) -> code
    placed, used, cous = [], set(), []
    for i, d in enumerate(docs):
        if not Path(d.file).is_file():
            raise WriterError(f'missing file {d.file}')
        code, cs, spec = p.cou(d.node)
        if d.node.startswith('1.'):
            stem = os.path.basename(rel_path(d, product, p.v32))[:-4]
            if d.node == '1.3.1':
                stem = f'{d.pi_type}-{d.lang}'
            rel = f'm1/{stem}.pdf'
        else:
            rel = rel_path(d, product, p.v32)
        n, k = rel, 2
        while n in used:
            n = rel[:-4] + f'-{k}.pdf'
            k += 1
        used.add(n)
        rel = n
        full = f'{first}/{env.sequence}/{rel}'
        if len(os.path.basename(rel)) > MAX_NAME or any(len(x) > MAX_NAME for x in rel.split('/')):
            raise WriterError(f'eCTD4-065/066 name > 64: {rel}')
        if len(full) > MAX_PATH:
            raise WriterError(f'eCTD4-067 path {len(full)} > 180: {full}')
        kws = []
        for name, card, kcs, allowed in spec:
            val = _kw_value(name, d, product)
            if val is None:
                if card == 'R':
                    raise WriterError(f'{d.node} ({code}): required keyword «{name}» missing (eCTD4-070)')
                continue
            if name.startswith('eg '):
                if allowed and val not in allowed:
                    raise WriterError(f'{d.node}: keyword «{name}» value {val!r} not in {allowed}')
                kws.append((val, kcs))
            elif name == 'document type':
                if val not in p.doc_types:
                    raise WriterError(f'{d.node}: unknown ICH document type {val!r}')
                kws.append((val, ICH_DOCTYPE))
            elif name == 'type of control':
                if val not in p.controls:
                    raise WriterError(f'{d.node}: unknown ICH type of control {val!r}')
                kws.append((val, ICH_CONTROL))
            elif name in KW_TYPE:
                key = (KW_TYPE[name], val)
                kwdefs.setdefault(key, f'kw{len(kwdefs) + 1:04d}')
                kws.append((kwdefs[key], sender_cs))
        doc_id = d.uuid or _u(env.application_uuid, 'doc', d.doc_id or rel)
        if d.operation == 'replace' and not d.cou_replaces:
            raise WriterError(f'{d.node}: replace needs the context of use being replaced (eCTD4-024)')
        cous.append(dict(code=code, cs=cs, doc=doc_id, kws=kws, id=_u(env.application_uuid, env.sequence, 'cou', i),
                         replaces=d.cou_replaces if d.operation == 'replace' else None, d=d, rel=rel))
        placed.append((d, rel, doc_id))

    for d, rel, _ in placed:
        dst = base / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(d.file, dst)

    prio = {}
    comps = ''
    for c in cous:
        prio[c['code']] = prio.get(c['code'], 0) + 1000
        c['priority'] = prio[c['code']]
        kw = ''.join(f'\n            <referencedBy typeCode="REFR"><keyword><code code="{escape(v)}" codeSystem="{cs}"/></keyword></referencedBy>'
                     for v, cs in c['kws'])
        comps += f'''
        <component>
          <priorityNumber value="{prio[c['code']]}"/>
          <contextOfUse>
            <id root="{c['id']}"/>
            <code code="{c['code']}" codeSystem="{c['cs']}"/>
            <statusCode code="active"/>{f'''
            <replacementOf typeCode="RPLC"><relatedContextOfUse><id root="{c['replaces']}"/></relatedContextOfUse></replacementOf>''' if c['replaces'] else ''}
            <derivedFrom><documentReference><id root="{c['doc']}"/></documentReference></derivedFrom>{kw}
          </contextOfUse>
        </component>'''
    for sp in suspend or []:
        comps += f'''
        <component>
          <priorityNumber value="{int(sp.get('priority') or 1000)}"/>
          <contextOfUse>
            <id root="{sp['cou_id']}"/>
            <statusCode code="suspended"/>
          </contextOfUse>
        </component>'''
    history = [{'doc_id': c['d'].doc_id, 'key': list(location_key(c['d'])),
                'leaf_id': c['id'], 'cou_id': c['id'], 'href': c['rel'], 'op': 'replace' if c['replaces'] else 'new',
                'replaces': c['replaces'], 'priority': c['priority'], 'doc_uuid': c['doc'], 'node': c['d'].node,
                'title': c['d'].title} for c in cous]
    history += [{'doc_id': None, 'key': [], 'leaf_id': sp['cou_id'], 'cou_id': sp['cou_id'], 'op': 'delete',
                 'replaces': sp['cou_id'], 'href': None} for sp in suspend or []]
    docs_xml = ''
    for d, rel, doc_id in placed:
        lang = d.lang or 'en'
        docs_xml += f'''
                <component>
                  <document>
                    <id root="{doc_id}"/>
                    <title value={quoteattr(d.title)}/>
                    <text integrityCheckAlgorithm="SHA256" language="{lang}" mediaType="application/pdf">
                      <reference value={quoteattr(rel)}/>
                      <integrityCheck>{_sha(base / rel)}</integrityCheck>
                    </text>
                  </document>
                </component>'''
    kd = ''
    for (ktype, val), code in kwdefs.items():
        kd += f'''
                <referencedBy>
                  <keywordDefinition>
                    <code code="{ktype}" codeSystem="{ICH_KWT}"/>
                    <statusCode code="active"/>
                    <value>
                      <item code="{code}" codeSystem="{sender_cs}">
                        <displayName value={quoteattr(val)}/>
                      </item>
                    </value>
                  </keywordDefinition>
                </referencedBy>'''
    ingredients = ''.join(f'''
                      <ingredient classCode="ACTI">
                        <ingredientSubstance><name><part value={quoteattr(i)}/></name></ingredientSubstance>
                      </ingredient>''' for i in env.inn)
    reg_code, reg_cs = p.reg[env.registration]
    mkt_code, mkt_cs = p.mkt[env.marketing]
    A = env.application_uuid
    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- PROVISIONAL EG regional profile v0 for eCTD v4.0 - not an EDA format. Codes with "EG-PLACEHOLDER"
     await EDA-registered OIDs. Conforms to ICH eCTD v4.0 IG v1.7 + EG drafts; never claimed "EDA-valid". -->
<PORP_IN000001UV ITSVersion="XML_1.0" xmlns="urn:hl7-org:v3" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="urn:hl7-org:v3 PORP_IN000001UV.xsd">
  <id/>
  <creationTime/>
  <interactionId/>
  <processingCode/>
  <processingModeCode/>
  <acceptAckCode/>
  <receiver>
    <device classCode="DEV" determinerCode="INSTANCE">
      <id>
        <item root="{ICH_IG}" identifierName="ICH eCTD v4.0 IG v1.7"/>
        <item root="{p.app_oid.rsplit('.1.4.0', 1)[0]}.6.1.0" identifierName="EG M1 v4 provisional profile v0 (PLACEHOLDER)"/>
      </id>
    </device>
  </receiver>
  <sender>
    <device classCode="DEV" determinerCode="INSTANCE">
      <id/>
    </device>
  </sender>
  <controlActProcess classCode="ACTN" moodCode="EVN">
    <subject typeCode="SUBJ">
      <submissionUnit>
        <id root="{_u(A, env.sequence, 'su')}"/>
        <code code="eg_su_{env.unit}" codeSystem="{p.su_oid}"/>
        <title value={quoteattr(env.title)}/>
        <statusCode code="active"/>{comps}
        <componentOf1>
          <sequenceNumber value="{env.sequence}"/>
          <submission>
            <id><item root="{env.submission_uuid}" extension={quoteattr(env.tracking)}/></id>
            <code code="eg_st_{env.submission_type}" codeSystem="{p.st_oid}"/>
            <callBackContact>
              <contactParty>
                <id root="{_u(A, 'contact')}"/>
                <code code="eg_contact_1" codeSystem="{p.contact_oid}"/>
                <statusCode code="active"/>
                <contactPerson>
                  <name><part type="GIV" value={quoteattr(env.contact_given)}/><part type="FAM" value={quoteattr(env.contact_family)}/></name>
                  <telecom xsi:type="BAG_TEL"><item value={quoteattr('mailto:' + env.contact_email)}/></telecom>
                  <asAgent><representedOrganization><name><part value={quoteattr(env.applicant)}/></name></representedOrganization></asAgent>
                </contactPerson>
              </contactParty>
            </callBackContact>
            <subject2>
              <review>
                <id root="{_u(A, env.submission_uuid, 'review')}"/>
                <statusCode code="active"/>
                <subject1>
                  <manufacturedProduct>
                    <id root="{_u(A, 'product')}"/>
                    <manufacturedProduct>
                      <name><part value={quoteattr(env.product_name)}/></name>{ingredients}
                    </manufacturedProduct>
                  </manufacturedProduct>
                </subject1>
                <subject2><productCategory><code code="{reg_code}" codeSystem="{reg_cs}"/></productCategory></subject2>
                <subject2><productCategory><code code="{mkt_code}" codeSystem="{mkt_cs}"/></productCategory></subject2>
              </review>
            </subject2>
            <componentOf>
              <application>
                <id><item root="{A}"/></id>
                <code code="{env.application_type}" codeSystem="{p.app_oid}"/>
                <holder>
                  <applicant>
                    <sponsorOrganization>
                      <id><item root="{p.org_oid}" extension={quoteattr(env.applicant_portal_id)}/></id>
                      <name><part value={quoteattr(env.applicant)}/></name>
                    </sponsorOrganization>
                  </applicant>
                </holder>
                <informationRecipient>
                  <territorialAuthority>
                    <territory><code code="eg" codeSystem="{p.country_oid}"/></territory>
                    <governingAuthority>
                      <id root="{p.authority_oid}" extension="EG-EDA"/>
                      <name><part value="Egyptian Drug Authority"/></name>
                    </governingAuthority>
                  </territorialAuthority>
                </informationRecipient>{docs_xml}{kd}
              </application>
            </componentOf>
          </submission>
        </componentOf1>
      </submissionUnit>
    </subject>
  </controlActProcess>
</PORP_IN000001UV>
'''
    (base / 'submissionunit.xml').write_text(xml, encoding='utf-8', newline='\n')
    (base / 'sha256.txt').write_text(_sha(base / 'submissionunit.xml'), encoding='ascii')
    files = sorted(str(x.relative_to(base)) for x in base.rglob('*') if x.is_file())
    return {'path': str(base), 'files': files, 'documents': len(placed), 'keyword_definitions': len(kwdefs),
            'history': history}


def _kw_value(name, d, product):
    return {
        'substance': d.substance, 'manufacturer': d.manufacturer,
        'product': product.name if d.node.startswith(('3.2.P', '2.3.P')) else None,
        'dosage form': product.dosageform if d.node.startswith(('3.2.P', '2.3.P')) else None,
        'indication': d.indication or product.indication,
        'excipient': d.excipient, 'study id_study title': d.study,
        'document type': d.doc_type, 'type of control': d.control,
        'eg document type (product information)': d.pi_type, 'eg language': d.lang,
        'eg country': 'eg' if d.node == '1.3.1' else None,
    }.get(name)
