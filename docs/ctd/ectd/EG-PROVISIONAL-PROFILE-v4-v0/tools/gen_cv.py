"""Generate the provisional EG v4 controlled-vocabulary YAML files.
Data comes from rows.json (parsed from EG-M1-eCTD-Specification-DRAFT-v1.0-reference.md §6.2)
and from facts transcribed (with citations) below. Run: python3 -I gen_cv.py <outdir>
"""
import json, sys, os, yaml

OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, 'cv'), exist_ok=True)
rows = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rows.json')))

ROOT = '2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER'
def oid(n):
    return f'{ROOT}.1.{n}.0'
OIDS = {
    'cou': oid(1), 'su': oid(2), 'st': oid(3), 'app': oid(4), 'mode': oid(5),
    'regtype': oid(6), 'mkttype': oid(7), 'kwdeftype': oid(8), 'doctype': oid(9),
    'lang': oid(10), 'country': oid(11), 'authority': oid(12), 'contact': oid(13),
    'org': oid(14),
}
HDR = """# =====================================================================================
# PROVISIONAL — NOT ISSUED BY EDA.  EG provisional regional profile v0 for eCTD v4.0.
# Every OID containing "EG-PLACEHOLDER" is a deliberately INVALID marker, not an OID.
# EDA must register real OIDs before any of these codes can pass ICH rules
# eCTD4-008/009/031/075/081/083/084.  See ../README.md (provenance tags, OID plan).
# Provenance tags:  ICH | EU-DERIVED | EG-DRAFT | ASSUMPTION
# Source short-cites: IG = ICH eCTD v4.0 IG v1.7 (5 May 2026); CV = ICH CV package v1.0.3;
#   EU-IG = EU eCTD v4.0 M1 IG draft v1.2 (Oct 2024, cited by heading); SPEC = EG M1 eCTD
#   Specification DRAFT v1.0 (2026, page/line/App.2 row); TG = EDA draft Technical Guidance
#   for eCTD Submissions in Egypt v1.0/2026 (PDF page / margin line).
# =====================================================================================
"""

def dump(name, obj, extra_hdr=''):
    p = os.path.join(OUT, 'cv', name)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(HDR + extra_hdr + '\n')
        yaml.safe_dump(obj, f, sort_keys=False, allow_unicode=True, width=110, default_flow_style=False)
    return p

# ---------------------------------------------------------------- Context of Use (M1)
# Folder-only parents in TG Annex 5 (printed in italics, TG p.55 l.1414 "Titles in italics are folders,
# containing subfolders but do not contain documents"). Detected from the PDF font (TimesNewRomanPS-ItalicMT).
TG_ITALIC = {'1.2', '1.2.3', '1.2.4', '1.2.5', '1.2.6', '1.2.7', '1.2.8', '1.2.10', '1.2.12', '1.2.13', '1.2.15', '1.2.16'}
MANUFACTURER_OK = {'1.2.2.2', '1.2.2.3', '1.2.2.5', '1.2.2.21', '1.2.4.2', '1.2.4.5', '1.2.4.6', '1.2.3.10',
                   '1.2.16.1', '1.2.16.2', '1.2.16.3', '1.2.16.5', '1.2.16.6'}

def code_for(ctd, el):
    if el == 'm1-responses':
        return 'eg_responses'
    if el == 'm1-additional-data':
        return 'eg_additional-data'
    return 'eg_' + ctd

sections = []
cur = None
for r in rows:
    if r['el'] and r['el'] != 'm1-eg':
        cur = dict(row=r['n'], page=r['page'], ctd=r['ctd'], title=r['title'], el=r['el'], dir=r['dir'], files=[], subdirs=[])
        sections.append(cur)
    elif cur is not None and r['el'] == '' and (r['file'] or r['dir']) and not r['dir'].startswith(('util', 'm1/eg/util')):
        if r['file']:
            cur['files'].append(dict(row=r['n'], page=r['page'], pattern=r['file'].replace('`', '').replace(' or ', ' | '), comment=r['comment']))
        elif r['dir'] and r['dir'] != cur['dir']:
            cur['subdirs'].append(dict(row=r['n'], page=r['page'], dir=r['dir'], comment=r['comment']))

codes_by_ctd = {s['ctd']: code_for(s['ctd'], s['el']) for s in sections}
children = {}
for s in sections:
    ctd = s['ctd']
    if ctd and '.' in ctd and ctd != '1.0':
        par = ctd.rsplit('.', 1)[0]
        if par in codes_by_ctd and par != '1':
            children.setdefault(par, []).append(ctd)

cou = []
for s in sections:
    ctd, el = s['ctd'], s['el']
    code = code_for(ctd, el)
    par = None
    if ctd and ctd.count('.') >= 2:
        par = codes_by_ctd.get(ctd.rsplit('.', 1)[0])
    has_children = ctd in children
    # documents allowed?
    if ctd in TG_ITALIC:
        docs, docs_prov = False, 'EG-DRAFT (TG p.55-58 Annex 5, italic = folder only)'
    elif ctd == '1.2.2':
        docs, docs_prov = False, ('ASSUMPTION: TG Annex 5 prints 1.2.2 NON-italic although it only has sub-folders '
                                  '(TG p.55); treated as folder-only for consistency with the other 1.2.x parents — confirm with EDA')
    elif has_children:
        docs, docs_prov = False, ('ASSUMPTION: parent heading with sub-headings and no file-name row in SPEC App.2; '
                                  'same rule as TG Annex 5 applied by analogy')
    else:
        docs, docs_prov = True, 'EG-DRAFT (leaf heading in SPEC App.2)'
    if el == 'm1-responses':
        disp = 'M1 Responses to Questions'
    elif el == 'm1-additional-data':
        disp = 'M1 Additional Data'
    else:
        disp = f'M{ctd} {s["title"]}'
    kws = []
    if docs:
        if ctd == '1.3.1':
            kws = [
                dict(type='eg document type (product information)', cardinality='R', code_system=OIDS['doctype'],
                     allowed_values=['spc', 'pl', 'interpack', 'combined', 'outer', 'other'],
                     provenance='EG-DRAFT pi-doc@type Mandatory (SPEC p.27; App.2.3 p.78; TG p.19 l.471-473) + EU-DERIVED (EU-IG "Product Information Texts in EU Module 1.3.1": PI document type as CoU keyword)'),
                dict(type='eg language', cardinality='R', code_system=OIDS['lang'], allowed_values=['ar', 'en'],
                     provenance='EG-DRAFT pi-doc@xml:lang Mandatory + language folder LL (SPEC p.27, App.2 rows 129-130, App.2.2 p.78) + EU-DERIVED (EU-IG keyword-definition sample: language code "fr" as CoU keyword)'),
                dict(type='eg country', cardinality='R', code_system=OIDS['country'], allowed_values=['eg'],
                     provenance='EG-DRAFT pi-doc@country Mandatory (SPEC p.27; App.2.1) + EU-DERIVED (EU-IG "Keywords and Controlled Vocabularies for EU Purpose": country keyword required for 13-pi)'),
            ]
        elif ctd == '1.0':
            kws = [dict(type='eg document type (cover)', cardinality='O', code_system=OIDS['doctype'], allowed_values=['cover', 'tracking'],
                        provenance='EG-DRAFT fixed file-name components cover-/tracking- (SPEC App.2 rows 4-5 p.29-30) turned into a keyword as EU-IG "Naming Conventions" does; ASSUMPTION (optional)')]
        elif ctd == '1.5.2':
            kws = [dict(type='eg document type (application basis)', cardinality='O', code_system=OIDS['doctype'], allowed_values=['generic', 'hybrid', 'biosimilar'],
                        provenance='EG-DRAFT fixed file-name components (SPEC App.2 row 150 p.64); keyword form = ASSUMPTION')]
        if ctd in MANUFACTURER_OK:
            kws.append(dict(type='manufacturer', keyword_definition_type='ich_keyword_type_3', cardinality='O',
                            code_system='2.16.840.1.113883.3.989.2.2.1.5.4',
                            provenance='ICH type (CV sheet "ICH Keyword Definition Type"); use on this EG heading = ASSUMPTION'))
        kws.append(dict(type='group title', keyword_definition_type='ich_keyword_type_11', cardinality='O',
                        code_system='2.16.840.1.113883.3.989.2.2.1.5.4',
                        provenance=('ICH type; replaces node-extensions (IG §9.2.10.2, §8.1.2 Table 9). '
                                    + ('EG-DRAFT: responses "should be grouped under a node-extension" per regulatory activity (SPEC p.10 l.137-142) -> RECOMMENDED here'
                                       if el == 'm1-responses' else 'Use on this EG heading = ASSUMPTION'))))
    entry = dict(
        code=code,
        display_name=disp,
        ctd_section=ctd or None,
        parent=par,
        status='Active (provisional)',
        documents_allowed=docs,
        documents_allowed_basis=docs_prov,
        keyword_types=kws,
        maps_from_v322=dict(element=el, folder=s['dir'],
                            file_patterns=[f['pattern'] for f in s['files']] or None,
                            spec_ref=f"SPEC App.2 row {s['row']}, p.{s['page']}"),
    )
    if s['subdirs']:
        entry['maps_from_v322']['sub_folders'] = [d['dir'] for d in s['subdirs']]
    eu = {'1.0': dict(code='100000164029', code_system='2.16.840.1.113883.3.6905.1.17.1', display='M1.0 Cover Letter',
                       basis='EU-IG table 3 "Example of Controlled Vocabularies for EU purpose"'),
          '1.2.1': dict(code='100000164030', code_system='2.16.840.1.113883.3.6905.1.17.1',
                        basis='EU-IG territorial-authority sample, comment "Component Application Form" (display name not printed; inferred)'),
          '1.3.1': dict(code='100000164032', code_system='2.16.840.1.113883.3.6905.1.17.1', display='1.3.1 SmPC, Label, PL',
                        basis='EU-IG "Product Information Texts in EU Module 1.3.1" sample originalText')}
    if ctd in eu:
        entry['eu_equivalent'] = eu[ctd]
    notes = []
    if ctd in ('1.6.1', '1.6.2'):
        notes.append('EG-DRAFT: "Only one of the 2 folders 1.6.1 or 1.6.2 can have content when sending a sequence" (SPEC App.2 rows 159,161). Kept as regional rule EG-V4-031.')
    if ctd == '1.3.5':
        notes.append('EG-DRAFT title "approved in the Member States" is an EU remnant (EG ref §10 item 21) — kept verbatim, flagged.')
    if ctd in ('1.2.2.3', '1.2.2.21'):
        notes.append('Overlap: 1.2.2.3 "GMP Certificate(s) / Alternative Documents" vs 1.2.2.21 "GMP Certificate" (EG ref §10 item 20). Placement rule needed from EDA.')
    if el == 'm1-responses':
        notes.append('EG-DRAFT file name responses-<activity>-<n>-<content>.pdf (SPEC p.11 l.174-178). TG 2.9.8 forbids extra folders in m1-responses (TG p.20); irrelevant in v4 (flat m1).')
    if el == 'm1-additional-data':
        notes.append('Conflict: SPEC row 178 (supportive docs go here) vs TG 3.2.4.1 (supportive docs go to 1.2). Unresolved in EG drafts.')
    if notes:
        entry['notes'] = notes
    cou.append(entry)

cou_doc = dict(
    code_system=dict(
        name='EG eCTD Context of Use (Module 1)', short_name='eg-context-of-use', oid=OIDS['cou'], version='0 (provisional)',
        status='PROVISIONAL - not issued by EDA',
        xpath='/PORP_IN000001UV/controlActProcess/subject/submissionUnit/component/contextOfUse/code/@code',
        purpose='Module 1 headings for Egypt; ICH CoU list covers M2-M5 only (IG §6.1 "Consult Regional/Module 1 IG to complete the list"; IG §6.2 "Context of Use Codes ... specifically Module 1").',
        naming=('Code pattern eg_<CTD number> follows the ICH CoU pattern ich_<section> (CV sheet "ICH Context of Use") with the '
                'regional prefix style seen in ICH/EU samples (us_application_type_1, IG §9.2.14; eu_keyword_definition_type_2, EU-IG "Keyword Definition"). '
                'Display names follow the EU M1 CoU display style "M1.0 Cover Letter" (EU-IG Table 3). The EU itself uses opaque numeric '
                'SPOR-RMS term IDs (OID 2.16.840.1.113883.3.6905.1.17.1); EDA may later replace these mnemonic codes with opaque IDs — '
                'the maps_from_v322 block keeps the forward-compatibility link either way. ASSUMPTION.'),
        hierarchy_rule=('No ICH table of contents exists for v4 (VEN 30 Sep 2026 Open Discussion #2); viewers build the tree from '
                        'the parent field. The Module 1 root itself has NO code (cf. ich_2 retired in CV v1.0.3, CR 00790).'),
        keyword_rule='Keyword types not listed for a code are not allowed on it (rule eCTD4-071); R types are required (eCTD4-070); one keyword per type per CoU (eCTD4-072).',
        source_rows='185 rows of SPEC App.2 (p.28-78); util rows 180-183 and the eg-regional.xml row 2 have no v4 equivalent (IG §5.1 no util folder; one submissionunit.xml).',
    ),
    count=len(cou),
    codes=cou,
)
dump('eg-m1-context-of-use.yaml', cou_doc)

# ---------------------------------------------------------------- Submission units
su_src = 'TG p.73-74 Annex 6 "EG Submission Unit" (l.1440 ff.)'
su = [
    ('initial', 'Initial submission to start any regulatory activity', 'SPEC p.24 l.269-273; ' + su_src, None),
    ('validation-response', 'For rectifying submission in response to content validation issues', 'SPEC p.24 Table 1; ' + su_src, None),
    ('response', 'Response to any kind of question, outstanding issues or information requested by the agency; also used when consolidating the dossier after withdrawal/rejection of a single regulatory activity (submission description must say so)',
     'SPEC p.25 l.283-287; ' + su_src, 'EU v4 uses a distinct "consolidating" type for this (EU-IG "Submission Unit"). EG drafts use response — kept (EG-DRAFT). Open question for EDA.'),
    ('additional-info', 'Other additional information (e.g. missing files); only if validation-response or response is not suitable', 'SPEC p.22, p.21 l.264; ' + su_src, None),
    ('corrigendum', 'Correction of information after the regulatory activity has concluded; exceptional, agreed with EDA in advance', su_src, 'Not in SPEC (only as a word, p.18).'),
    ('reformat', 'Baseline: reformatting an existing application from any format to eCTD, no content change, not reviewed; always with submission type none',
     'SPEC p.25 l.279-280; TG p.22 l.592-606; ' + su_src,
     'ICH v4 defines no baseline/transition submission (TMM removed, CR 00710); EU-IG "COMPATIBILITY..." says the same baselining rules can presumably be applied. In v4 use only for non-eCTD -> v4 baselines; v3.2.2 -> v4 uses Forward Compatibility, not reformat (see ../migration.md).'),
    ('re-examination', 'Request for re-examination of an authority opinion (MAA, type II variation)', su_src, 'Not in SPEC.'),
]
su_doc = dict(code_system=dict(name='EG Submission Unit Type', short_name='eg-submission-unit', oid=OIDS['su'], version='0 (provisional)',
                               xpath='/PORP_IN000001UV/controlActProcess/subject/submissionUnit/code/@code',
                               ich_basis='IG §9.2.4.2: SU code + codeSystem are regional (rules eCTD4-006..009); IG §6.2 "Submission Unit Codes".',
                               eu_model='EU-IG "Submission Unit": OID 2.16.840.1.113883.3.6905.1.8.1, e.g. 100000155047 "Initial".',
                               status_rule='submissionUnit/statusCode only "active" (IG §9.2.4.2, rule eCTD4-010, CR 00800). An SU cannot be suspended (EU-IG "Submission Unit").',
                               code_pattern='eg_su_<EG v3.2.2 token> (ASSUMPTION; keeps a 1:1 link to the 3.2.2 token)'),
              codes=[dict(code='eg_su_' + t, v322_token=t, display_name=t, description=d, provenance='EG-DRAFT', source=s, **({'note': n} if n else {}))
                     for t, d, s, n in su],
              not_adopted=[dict(token='closing', reason='EU v3 type; absent from both EG drafts (EG ref §9.1)'),
                           dict(token='consolidating', reason='EU type; EG drafts use response instead (SPEC p.25; TG Annex 6)'),
                           dict(token='responses / Response', reason='typos in SPEC p.25 Table 4 and l.285 for "response" (EG ref §10 item 13)')])
dump('eg-submission-units.yaml', su_doc)

# ---------------------------------------------------------------- Submission types
ST = [  # token, title, group(s), TG page, note
    ('maa', 'Marketing Authorisation Application', ['pharmaceuticals'], '59', 'Also the only type shown in SPEC (p.14, 22, 24).'),
    ('var-pac-n', 'Variation PAC-N (notification)', ['pharmaceuticals'], '59', 'SPEC tracking example P-VAR-PAC-N-0002 (p.17).'),
    ('var-pac-b', 'Variation PAC-B', ['pharmaceuticals'], '60', None),
    ('var-pac-a', 'Variation PAC-A (annual)', ['pharmaceuticals'], '60', None),
    ('var-pac-ii', 'Variation PAC-II (major)', ['pharmaceuticals'], '60', 'Spelled "Var PAC-II" (SPEC p.23-25), "var-pac-II" (TG 2.9.5 p.17, TG p.22 Table 3), "var-pac-ii" (Annex 6). Lower-case token adopted (ICH lower-case convention).'),
    ('renewal', 'Renewal', ['pharmaceuticals', 'biologics-and-innovative'], '61, 64', None),
    ('asmf', 'Active Substance Master File', ['pharmaceuticals'], '61', None),
    ('cep', 'Certificate of Suitability', ['pharmaceuticals'], '61', None),
    ('none', 'none (reformat/baseline only)', ['pharmaceuticals', 'biologics-and-innovative'], '61, 64', 'Only with SU type reformat (TG p.74; SPEC p.25).'),
    ('preass', 'Pre-assessment', ['pharmaceuticals'], '61', None),
    ('pacstab', 'Post MA Commitments (Stability Studies)', ['pharmaceuticals', 'biologics-and-innovative'], '62, 64', None),
    ('paccadc', 'Post MA Commitments (CADC analysis)', ['pharmaceuticals', 'biologics-and-innovative'], '62, 64', None),
    ('paci', 'Post MA Commitments (Inspection)', ['pharmaceuticals', 'biologics-and-innovative'], '62, 65', None),
    ('pacqr', 'Post MA Commitments (Quality requirements)', ['pharmaceuticals', 'biologics-and-innovative'], '62, 65', None),
    ('5yr', 'Fifth Year Report', ['pharmaceuticals'], '62', None),
    ('appeal', 'Appeals', ['pharmaceuticals'], '63', None),
    ('preappinq', 'Preliminary Approval Inquiry', ['pharmaceuticals'], '63', None),
    ('pmf', 'Plasma Master File', ['biologics-and-innovative'], '65', 'Printed upper case "PMF" in TG Annex 6; lower-cased here (ASSUMPTION).'),
    ('withdrawal', 'Withdrawal (of the entire MA application)', ['biologics-and-innovative'], '65', 'Printed only in the Biologics & Innovative list, but SPEC p.26 l.291-294 and TG 4.6 present it as general (EG ref §10 item 38). Offered to all administrations here (ASSUMPTION).'),
    ('maa-inn', 'MAA for an innovative product', ['innovative'], '66', None),
    ('ipv-admc', 'Innovative product variation - administrative changes', ['innovative'], '66', None),
    ('ipv-admlc', 'Innovative product variation - administrative product labelling information changes', ['innovative'], '66', 'Abbreviation printed "IPV-ADMIC".'),
    ('ipv-tlc', 'Innovative product variation - therapeutic labelling information changes', ['innovative'], '66', None),
    ('ipv-pu', 'Innovative product variation - pack update', ['innovative'], '66', 'SPEC tracking example I-IPV-PU-0001 (p.17).'),
    ('ipv-safeffc', 'Innovative product variation - safety and efficacy labelling changes', ['innovative'], '67', None),
    ('imv-majvar', 'Innovative medicinal products variation - major', ['innovative'], '67', None),
    ('imv-minvar', 'Innovative medicinal products variation - minor', ['innovative'], '67', None),
    ('imv-not', 'Innovative medicinal products variation - notification', ['innovative'], '67', None),
    ('ibv-majqualc', 'Innovative biological products variation - major quality changes', ['innovative'], '67', None),
    ('ibv-modqualc', 'Innovative biological products variation - moderate quality changes', ['innovative'], '67', None),
    ('ibv-minqualc', 'Innovative biological products variation - minor quality changes', ['innovative'], '68', None),
    ('ibv-qcnoimp', 'Innovative biological products variation - quality changes with no impact', ['innovative'], '68', None),
    ('maa-nt', 'MAA - Normal Track', ['biologicals'], '69', None),
    ('maa-ft', 'MAA - Fast Track', ['biologicals'], '69', None),
    ('maa-sb', 'MAA - Second Brand', ['biologicals'], '69', None),
    ('maa-rl1', 'MAA - Reliance level 1', ['biologicals'], '69', None),
    ('maa-rl2', 'MAA - Reliance level 2', ['biologicals'], '69', None),
    ('maa-bios', 'MAA - Biosimilar', ['biologicals'], '69', None),
    ('np-modqualc', 'Normal pathway - moderate quality changes', ['biologicals'], '70', None),
    ('np-pilc', 'Normal pathway - product labelling information changes', ['biologicals'], '70', None),
    ('np-majqualc', 'Normal pathway - major quality changes', ['biologicals'], '70', None),
    ('np-safeffc', 'Normal pathway - safety and efficacy changes', ['biologicals'], '70', None),
    ('np-admpilc', 'Normal pathway - administrative product labelling information changes', ['biologicals'], '70', None),
    ('np-packup', 'Normal pathway - pack update', ['biologicals'], '70', None),
    ('np-adminc', 'Normal pathway - administrative changes', ['biologicals'], '71', None),
    ('rp-majcq', 'Reliance pathway - major quality changes', ['biologicals'], '71', None),
    ('rp-modqc', 'Reliance pathway - moderate quality changes', ['biologicals'], '71', None),
    ('rl-pilc', 'Reliance pathway - product labelling information changes', ['biologicals'], '71', None),
    ('not-minqc', 'Notification - minor quality changes', ['biologicals'], '71', None),
    ('not-qcnoimp', 'Notification - quality changes with no impact', ['biologicals'], '71', None),
]
VARIATION_TOKENS = [t for t, *_ in ST if t.startswith(('var-', 'ipv-', 'imv-', 'ibv-', 'np-', 'rp-', 'rl-', 'not-'))]
st_doc = dict(code_system=dict(name='EG Submission Type (regulatory activity)', short_name='eg-submission-type', oid=OIDS['st'], version='0 (provisional)',
                               xpath='/PORP_IN000001UV/controlActProcess/subject/submissionUnit/componentOf1/submission/code/@code',
                               ich_basis='IG Table 11 / §12.2: submission code + codeSystem regional (rules eCTD4-034..037); IG §6.2 "Submission Codes".',
                               eu_model='EU-IG "Submission": OID 2.16.840.1.113883.3.6905.1.11.1, e.g. 100000155689 = initial MAA; submission id.item@root stays the same for all SUs of the regulatory activity; only one id item.',
                               v322_source='eg-envelope submission/@type (SPEC App.1.1 p.14) - the CV itself is NOT in SPEC; values from TG Annex 6 (TG p.59-71, l.1417 ff.).',
                               code_pattern='eg_st_<EG v3.2.2 token> (ASSUMPTION)'),
              mode_required_for=dict(tokens=VARIATION_TOKENS, rule='submission/subject3/mode required in every SU of these activities (SPEC p.8 l.78-80, p.15; TG p.27 l.722-724). Which tokens count as "variation" is inferred from the token names = ASSUMPTION.'),
              codes=[dict(code='eg_st_' + t, v322_token=('PMF' if t == 'pmf' else t), display_name=title, administrations=g,
                          provenance='EG-DRAFT', source=f'TG Annex 6 p.{p}', **({'note': n} if n else {})) for t, title, g, p, n in ST])
dump('eg-submission-types.yaml', st_doc)

# ---------------------------------------------------------------- Mode (kept in the submission-types file? separate small list in app types file)
mode = dict(code_system=dict(name='EG Submission Mode', short_name='eg-mode', oid=OIDS['mode'], version='0 (provisional)',
                             xpath='/PORP_IN000001UV/controlActProcess/subject/submissionUnit/componentOf1/submission/subject3/mode/code/@code',
                             eu_model='EU-IG "Mode": OID 2.16.840.1.113883.3.6905.1.10.1 (100000155556 = worksharing); only for variation/extension activities, in every sequence.'),
            codes=[dict(code='eg_mode_single', v322_token='single', display_name='A Single Regulatory Activity', provenance='EG-DRAFT', source='SPEC p.8 l.79, p.15; TG p.72'),
                   dict(code='eg_mode_grouping', v322_token='grouping', display_name='A Grouped Activity', provenance='EG-DRAFT', source='SPEC p.8 l.79, p.15; TG p.72',
                        note='Meaning differs: Human Pharmaceuticals = several variations, single product; Biological/Innovative = also multi-product (SPEC p.15).'),
                   dict(code='eg_mode_parallel-single', v322_token='parallel-single', display_name='Parallel Assessment Single RA', provenance='EG-DRAFT', source='SPEC p.8 l.79, p.15; TG p.72 ("Parallel Single")'),
                   dict(code='eg_mode_parallel-grouping', v322_token='parallel-grouping', display_name='Parallel Assessment Grouped RA', provenance='EG-DRAFT', source='SPEC p.8 l.79 (p.15 prints "parallel  grouping"); TG p.72',
                        note='Definition identical to parallel-single in SPEC p.15 (EG ref §10 item 14).')])

# ---------------------------------------------------------------- Application types (+ mode, registration, marketing as carrier lists)
app = [
    ('eg_application_type_1', 'Full / stand-alone dossier (incl. innovative product)', 'EU-DERIVED (EU-IG "Application" terminology: Full Dossier) + EG-DRAFT maa-inn (TG p.66)', None),
    ('eg_application_type_2', 'Generic', 'EG-DRAFT M1.5.2 heading + file component "generic" (SPEC App.2 rows 149-150 p.64); EU-DERIVED (EU-IG "Application": Generic)', None),
    ('eg_application_type_3', 'Hybrid', 'EG-DRAFT M1.5.2 "hybrid" (SPEC row 150 p.64); EU-DERIVED', None),
    ('eg_application_type_4', 'Biosimilar', 'EG-DRAFT M1.5.2 "biosimilar" (SPEC row 150); maa-bios (TG p.69); EU-DERIVED (EU-IG "Application": Biosimilar)', None),
    ('eg_application_type_5', 'Bibliographic (well-established use)', 'EG-DRAFT M1.5.1 (SPEC rows 147-148 p.63-64); EU-DERIVED (EU-IG "Application": Bibliographic)', None),
    ('eg_application_type_6', 'Active Substance Master File', 'ASSUMPTION from EG submission type asmf (TG p.61): a master file has its own lifecycle, so its own v4 application', None),
    ('eg_application_type_7', 'Plasma Master File', 'ASSUMPTION from submission type PMF (TG p.65)', None),
    ('eg_application_type_8', 'Certificate of Suitability (CEP) application', 'ASSUMPTION from submission type cep (TG p.61)', 'Whether a CEP is an application or a document inside an MA lifecycle must be decided by EDA.'),
]
app_doc = dict(
    code_system=dict(name='EG Application Type', short_name='eg-application-type', oid=OIDS['app'], version='0 (provisional)',
                     xpath='/PORP_IN000001UV/controlActProcess/subject/submissionUnit/componentOf1/submission/componentOf/application/code/@code',
                     ich_basis='IG §9.2.14: application code + codeSystem regional, "The concept of application element differs among regions" (rules eCTD4-038..042).',
                     eu_model='EU-IG "Application": "EU Application Code - Legal Basis" OID 2.16.840.1.113883.3.6905.1.4.1 (e.g. 100000116047 Art. 8(3)); application/id/item@root = the v3.2.2 envelope UUID, @extension = procedure number.',
                     gap='GAP: neither EG draft defines an application-type list. This list is EU-DERIVED from the EG M1 1.5 headings, which EG copied from the EU.',
                     eg_scope_rule='EG-DRAFT: "For products with different dosage forms and strengths are submitted under separate applications" (SPEC Glossary p.3-4) -> one v4 application per strength/dosage form.'),
    codes=[dict(code=c, display_name=d, provenance=p, **({'note': n} if n else {})) for c, d, p, n in app],
    related_lists=dict(
        mode=mode,
        registration_type=dict(
            code_system=dict(name='EG Registration Type', short_name='eg-registration-type', oid=OIDS['regtype'], version='0 (provisional)',
                             v4_carrier='/…/submission/subject2/review/subject2/productCategory/code (one productCategory per EG list) — ASSUMPTION, see ../rules.md §6',
                             gap='GAP: "Registration Type CV" referenced (SPEC p.18; TG p.28 l.754-756 "published on the EDA web site") but not published. Codes below are built from the examples only; spelling is ASSUMPTION.'),
            codes=[dict(code='eg_regtype_local', v322_token='local', display_name='Locally Manufactured', provenance='EG-DRAFT example value (SPEC p.18); label HPG p.9'),
                   dict(code='eg_regtype_toll', v322_token='toll', display_name='Toll', provenance='EG-DRAFT label (HPG p.10, p.17 l.388); token ASSUMPTION — harmonised with v3.2.2 profile vocab/registration-type.yaml'),
                   dict(code='eg_regtype_f-toll', v322_token='f-toll', display_name='F-Toll', provenance='EG-DRAFT label (HPG p.9-10, p.15 l.285); token ASSUMPTION — harmonised with v3.2.2 profile'),
                   dict(code='eg_regtype_under-license', v322_token='under-license', display_name='Under License', provenance='EG-DRAFT label (HPG p.11, p.20 l.504); token ASSUMPTION — harmonised with v3.2.2 profile'),
                   dict(code='eg_regtype_imported-finished', v322_token='imported-finished', display_name='Imported Finished', provenance='EG-DRAFT description example (SPEC p.18; TG p.28 l.755); token harmonised with v3.2.2 profile'),
                   dict(code='eg_regtype_imported-bulk', v322_token='imported-bulk', display_name='Imported Bulk', provenance='EG-DRAFT description example (SPEC p.18; TG p.28 l.755); token harmonised with v3.2.2 profile')]),
        marketing_type=dict(
            code_system=dict(name='EG Marketing Type', short_name='eg-marketing-type', oid=OIDS['mkttype'], version='0 (provisional)',
                             v4_carrier='second productCategory element (ASSUMPTION, see ../rules.md §6)',
                             gap='GAP: "Marketing Type CV" not published (SPEC p.19; TG p.28 l.757-759). Whether "Tender and Export" is one value or two is unknown.'),
            codes=[dict(code='eg_mkttype_local', v322_token='local', display_name='Local', provenance='EG-DRAFT example (SPEC p.19)'),
                   dict(code='eg_mkttype_tender', v322_token='tender', display_name='Tender', provenance='EG-DRAFT HPG p.52 (Local/Tender/Export/Hospital); SPEC p.19 prints "Tender and Export" — split per HPG, ASSUMPTION; harmonised with v3.2.2 profile'),
                   dict(code='eg_mkttype_export', v322_token='export', display_name='Export', provenance='EG-DRAFT HPG p.52; harmonised with v3.2.2 profile'),
                   dict(code='eg_mkttype_hospital', v322_token='hospital', display_name='Hospital', provenance='EG-DRAFT HPG p.52; harmonised with v3.2.2 profile')]),
        territorial_authority=dict(
            code_system=dict(name='EG Territorial Authority', short_name='eg-authority', oid=OIDS['authority'], version='0 (provisional)',
                             v4_carrier='/…/application/informationRecipient/territorialAuthority/governingAuthority (EU-IG "Territorial Authority (as information recipient related to application)")'),
            codes=[dict(code='EG-EDA', display_name='Egyptian Drug Authority', provenance='EG-DRAFT agency/@code (SPEC p.18; App.2.4 p.78)',
                        note='TG p.27 says the authority code is "EDA" (conflict, EG ref §10 item 29). SPEC value adopted.')]),
        territory=dict(
            code_system=dict(name='EG Territory / Country (constrained ISO 3166-1 alpha-2)', short_name='eg-country', oid=OIDS['country'], version='0 (provisional)',
                             note='IG §6.4 names ISO 3166-1; EU constrains it in SPOR (EU-IG "Controlled Vocabulary specified by ISO"). EG constrains it to one value.'),
            codes=[dict(code='eg', display_name='Egypt', provenance='EG-DRAFT App.2.1 p.78; envelope/@country (SPEC p.14)')]),
        contact_party_role=dict(
            code_system=dict(name='EG Contact Party Role', short_name='eg-contact-party-role', oid=OIDS['contact'], version='0 (provisional)',
                             gap='GAP: EG drafts have no contact-party concept. EU-DERIVED (EU-IG "Contact Party": at least one per SU; role list 2.16.840.1.113883.3.6905.1.6.1).'),
            codes=[dict(code='eg_contact_1', display_name='Regulatory contact (person authorised for communication on behalf of the applicant)', provenance='EU-DERIVED'),
                   dict(code='eg_contact_2', display_name='eCTD technical contact', provenance='EU-DERIVED (EU-IG: technical contact for troubleshooting, e.g. forward compatibility)')]),
        organisation_identifier=dict(
            code_system=dict(name='EDA portal organisation identifier (namespace)', short_name='eg-org-id', oid=OIDS['org'], version='0 (provisional)',
                             use='sponsorOrganization/id/item@root = this OID, @extension = applicant ID issued by the EDA portal (https://reg-submit.edaegypt.gov.eg, TG p.26 l.686). EU-DERIVED from EU OMS LOC-ID (EU-IG "Applicant"); ASSUMPTION that EDA has such an ID.'),
            codes=[]),
    ),
)
dump('eg-application-types.yaml', app_doc)

# ---------------------------------------------------------------- Keyword definitions / keyword CVs
kw_doc = dict(
    purpose=('Keyword vocabularies for EG Module 1 CoUs, plus the place of each EG v3.2.2 envelope/leaf attribute (registration type, '
             'marketing type, product, manufacturer, INN, language, ...) in v4. In v4 keywords attach ONLY to contextOfUse (IG §9.2.9; '
             'document/referencedBy/keyword is excluded, IG §4.7.2). Application-level facts therefore do NOT become keywords.'),
    eg_keyword_definition_types=dict(
        code_system=dict(name='EG Keyword Definition Type (regional sender-defined types)', short_name='eg-keyword-definition-type', oid=OIDS['kwdeftype'], version='0 (provisional)',
                         xpath='/…/application/referencedBy/keywordDefinition/code/@code',
                         eu_model='EU allows ONE regional type in M1: eu_keyword_definition_type_2 = strength, list 2.16.840.1.113883.3.6905.5.1.1, value pattern FIGURE_UNIT e.g. 30_mg (EU-IG "Keyword Definition", "Guidance regarding Keyword Definition values").'),
        codes=[],
        decision=('EMPTY in v0 (ASSUMPTION). EU needs strength because one EU application spans several strengths; EG requires one '
                  'application per strength/dosage form (SPEC Glossary p.3-4), and EG v3.2.2 has no strength attribute. '
                  'Sender-defined keywords in EG M1 use the ICH types listed below.'),
    ),
    ich_keyword_definition_types_allowed_in_eg_m1=[
        dict(code='ich_keyword_type_11', display_name='group title', code_system='2.16.840.1.113883.3.989.2.2.1.5.4',
             where='all document-bearing EG CoUs (O); recommended on eg_responses (one group title per regulatory activity)',
             source='CV sheet "ICH Keyword Definition Type"; IG §9.2.10.2; EG node-extension rules SPEC p.9-10 N1-N10', provenance='ICH + EG-DRAFT'),
        dict(code='ich_keyword_type_3', display_name='manufacturer', code_system='2.16.840.1.113883.3.989.2.2.1.5.4',
             where='EG CoUs flagged in eg-m1-context-of-use.yaml (GMP, licences, API declarations, inspection docs) (O)',
             source='CV sheet "ICH Keyword Definition Type"', provenance='ICH type; EG use = ASSUMPTION'),
        dict(code='ich_keyword_type_4', display_name='product', code_system='2.16.840.1.113883.3.989.2.2.1.5.4',
             where='NOT used in M1 (one product per EG application). Remains available in M2/M3 per ICH CV.',
             source='CV; replaces v3.2.2 product-name attribute', provenance='ICH'),
    ],
    eg_keyword_code_systems=[
        dict(code_system=dict(name='EG Document Type', short_name='eg-document-type', oid=OIDS['doctype'], version='0 (provisional)',
                              eu_model='EU Document Type list 2.16.840.1.113883.3.6905.1.18.1 (e.g. 100000155532 SmPC) used as CoU keyword (EU-IG "Keyword", PI section).'),
             codes=[
                 dict(code='spc', display_name='Summary of Product Characteristics', use_on='eg_1.3.1', provenance='EG-DRAFT App.2.3 p.78'),
                 dict(code='pl', display_name='Package Leaflet', use_on='eg_1.3.1', provenance='EG-DRAFT App.2.3 p.78'),
                 dict(code='interpack', display_name='Outer and immediate labelling in one file', use_on='eg_1.3.1', provenance='EG-DRAFT App.2.3 footnote p.78'),
                 dict(code='combined', display_name='Combined product information', use_on='eg_1.3.1', provenance='EG-DRAFT App.1.2 example p.27; SPEC p.11 l.172; TG p.19 l.471'),
                 dict(code='outer', display_name='Outer labelling', use_on='eg_1.3.1', provenance='EG-DRAFT file-name example SPEC p.11 l.171'),
                 dict(code='other', display_name='Other product information', use_on='eg_1.3.1', provenance='EG-DRAFT TG p.19 l.473'),
                 dict(code='cover', display_name='Cover letter', use_on='eg_1.0', provenance='EG-DRAFT SPEC App.2 row 4 (fixed file component)'),
                 dict(code='tracking', display_name='Tracking table', use_on='eg_1.0', provenance='EG-DRAFT SPEC App.2 row 5; TG p.28 l.776-780'),
                 dict(code='generic', display_name='Generic application information', use_on='eg_1.5.2', provenance='EG-DRAFT SPEC App.2 row 150'),
                 dict(code='hybrid', display_name='Hybrid application information', use_on='eg_1.5.2', provenance='EG-DRAFT SPEC App.2 row 150'),
                 dict(code='biosimilar', display_name='Biosimilar application information', use_on='eg_1.5.2', provenance='EG-DRAFT SPEC App.2 row 150'),
             ],
             gap='SPEC App.2.3 lists only spc and pl, but the drafts themselves use interpack, combined, outer, other (EG ref §10 item 16). All six kept.'),
        dict(code_system=dict(name='EG Language (constrained ISO 639-1)', short_name='eg-language', oid=OIDS['lang'], version='0 (provisional)',
                              note='Also used for document/text@language (ISO 639-1 two-letter, IG §6.4, §9.2.15.2) — that attribute carries the bare ISO code, no codeSystem.'),
             codes=[dict(code='ar', display_name='Arabic', provenance='EG-DRAFT App.2.2 p.78'),
                    dict(code='en', display_name='English', provenance='EG-DRAFT App.2.2 p.78')]),
        dict(code_system=dict(name='EG Country', short_name='eg-country', oid=OIDS['country'], version='0 (provisional)', note='Same list as application informationRecipient territory.'),
             codes=[dict(code='eg', display_name='Egypt', provenance='EG-DRAFT App.2.1 p.78')]),
    ],
    v322_envelope_and_attribute_destinations=[
        dict(v322='envelope/identifier (UUID)', v4='application/id/item@root', provenance='EU-DERIVED (EU-IG "Application": root reflects the UUID introduced in v3.2.2)', note='Not a keyword.'),
        dict(v322='registration/@type', v4='submission/subject2/review/subject2/productCategory/code (code system eg-registration-type)', provenance='ASSUMPTION', note='No RPS class matches; alternatives: componentOf2/categoryEvent (regional, IG Table 11). Open question for EDA.'),
        dict(v322='marketing/@type', v4='second review/subject2/productCategory/code (code system eg-marketing-type)', provenance='ASSUMPTION', note='XSD allows productCategory 0..*; EU limits to one (EU-IG validation table) — EG deviates.'),
        dict(v322='invented-name', v4='submission/subject2/review/subject1/manufacturedProduct/manufacturedProduct/name', provenance='EU-DERIVED (EU-IG "Manufactured Product")', note='Required with SU type initial of an MAA-type submission (EU: initial MAA only).'),
        dict(v322='inn', v4='…/manufacturedProduct/manufacturedProduct/ingredient[@classCode="ACTI"]/ingredientSubstance/name', provenance='EU-DERIVED (EU-IG "Manufactured Product"; EU uses SPOR SMS codes — EG has no substance list, so name only)'),
        dict(v322='leaf attribute product-name / dosageform / manufacturer / substance (ICH index.xml)', v4='ICH keywordDefinition types 4 / 5 / 3 / 2 on M2-M5 CoUs', provenance='ICH (IG §8.1.2 Table 9)'),
        dict(v322='pi-doc @type / @xml:lang / @country', v4='CoU keywords eg-document-type / eg-language / eg-country on eg_1.3.1 (all R) + document/text@language', provenance='EG-DRAFT + EU-DERIVED'),
        dict(v322='node-extension/title', v4='group title keyword ich_keyword_type_11 (nested: joined with "_$")', provenance='ICH (IG §8.1.2 Table 9; CR 00840)'),
        dict(v322='language folder 131-spclabelpl/LL', v4='document/text@language + eg-language keyword', provenance='EU-DERIVED (EU-IG "Keywords and Controlled Vocabularies for EU Purpose" note: language folder replaced)'),
    ],
)
dump('eg-keyword-definitions.yaml', kw_doc)
print('CoU codes:', len(cou), 'docs-allowed:', sum(1 for c in cou if c['documents_allowed']))
