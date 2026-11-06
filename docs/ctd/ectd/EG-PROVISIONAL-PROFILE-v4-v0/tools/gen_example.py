"""Build examples/1 (sequence 1) of the EG provisional v4 profile: tiny placeholder PDFs, submissionunit.xml, sha256.txt.
UUIDs are fixed (generated once with uuid4 and pasted) so the output is reproducible.
Usage: python3 -I gen_example.py <profile_dir>
"""
import hashlib, os, sys

PROFILE = sys.argv[1]
SEQ = os.path.join(PROFILE, 'examples', '1')
ROOT = '2.16.840.1.113883.3.989.5.x.EG-PLACEHOLDER'
O = lambda n: f'{ROOT}.1.{n}.0'
EG_IG = f'{ROOT}.6.1.0'
ICH_IG = '2.16.840.1.113883.3.989.2.2.1.11.6'      # CV Index: ICH eCTD v4.0 IG v1.7
ICH_COU = '2.16.840.1.113883.3.989.2.2.1.1.6'      # CV Index: ICH Context of Use v6
ICH_KWT = '2.16.840.1.113883.3.989.2.2.1.5.4'      # CV Index: ICH Keyword Definition Type
SENDER_CS = '2.25.329800735698586629295641978511506172918'  # sender code system: UUID-derived OID (2.25 arc, ITU-T X.667)

def pdf(text):
    """Minimal one-page PDF 1.4 with correct xref offsets."""
    content = f'BT /F1 12 Tf 72 720 Td ({text}) Tj ET'.encode('latin-1')
    objs = [b'<< /Type /Catalog /Pages 2 0 R >>',
            b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
            b'<< /Length %d >>\nstream\n' % len(content) + content + b'\nendstream',
            b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out = bytearray(b'%PDF-1.4\n')
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b'%d 0 obj\n' % i + o + b'\nendobj\n'
    x = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1)
    for off in offs:
        out += b'%010d 00000 n \n' % off
    out += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, x)
    return bytes(out)

DOCS = [  # (doc uuid, cou uuid, path, title, lang, cou code, codesystem, priority, keywords[(code, cs)])
    ('5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c01', '0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b01', 'm1/cover-seq1.pdf', 'Cover Letter for Sequence 1', 'en',
     'eg_1.0', O(1), 1000, [('cover', O(9))]),
    ('5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c02', '0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b02', 'm1/tracking.pdf', 'Tracking Table', 'en',
     'eg_1.0', O(1), 1000, [('tracking', O(9))]),
    ('5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c03', '0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b03', 'm1/form-af.pdf', 'Application Form', 'en',
     'eg_1.2.1', O(1), 1000, []),
    ('5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c04', '0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b04', 'm1/spc-en.pdf', 'Summary of Product Characteristics (English)', 'en',
     'eg_1.3.1', O(1), 1000, [('spc', O(9)), ('en', O(10)), ('eg', O(11))]),
    ('5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c05', '0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b05', 'm1/pl-ar.pdf', 'Package Leaflet (Arabic)', 'ar',
     'eg_1.3.1', O(1), 1000, [('pl', O(9)), ('ar', O(10)), ('eg', O(11))]),
    ('5b0c2e57-8d0a-4f43-9a35-6f0b8e2a1c06', '0e5f7a32-6c41-4b8e-9d13-2a7c4f6e8b06', 'm3/32-prod/description-composition.pdf', 'Description and Composition of the Drug Product', 'en',
     'ich_3.2.p.1', ICH_COU, 1000, [('PROD001', SENDER_CS)]),
]
SU_ID = '9a1d6c4e-3b2f-4e7a-8c5d-1f0e2d3c4b01'
SUB_ID = '9a1d6c4e-3b2f-4e7a-8c5d-1f0e2d3c4b02'
APP_ID = '9a1d6c4e-3b2f-4e7a-8c5d-1f0e2d3c4b03'   # = the application UUID (v3.2.2 envelope identifier would be reused)
REVIEW_ID = '9a1d6c4e-3b2f-4e7a-8c5d-1f0e2d3c4b04'
MP_ID = '9a1d6c4e-3b2f-4e7a-8c5d-1f0e2d3c4b05'
CONTACT_ID = '9a1d6c4e-3b2f-4e7a-8c5d-1f0e2d3c4b06'

os.makedirs(SEQ, exist_ok=True)
shas = {}
for d in DOCS:
    p = os.path.join(SEQ, d[2])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    data = pdf(f'FICTIONAL EXAMPLE - {d[3]} - Exemplofen 400 mg - EG provisional eCTD v4 profile v0')
    open(p, 'wb').write(data)
    shas[d[2]] = hashlib.sha256(data).hexdigest()

def cou_xml(d):
    kws = ''.join(f'\n            <referencedBy typeCode="REFR"><keyword><code code="{c}" codeSystem="{cs}"/></keyword></referencedBy>' for c, cs in d[8])
    return f'''
        <component>
          <priorityNumber value="{d[7]}"/>
          <contextOfUse>
            <id root="{d[1]}"/>
            <code code="{d[5]}" codeSystem="{d[6]}"/>
            <statusCode code="active"/>
            <derivedFrom><documentReference><id root="{d[0]}"/></documentReference></derivedFrom>{kws}
          </contextOfUse>
        </component>'''

def doc_xml(d):
    return f'''
                <component>
                  <document>
                    <id root="{d[0]}"/>
                    <title value="{d[3]}"/>
                    <text integrityCheckAlgorithm="SHA256" language="{d[4]}" mediaType="application/pdf">
                      <reference value="{d[2]}"/>
                      <integrityCheck>{shas[d[2]]}</integrityCheck>
                    </text>
                  </document>
                </component>'''

xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- FICTIONAL EXAMPLE. EG provisional regional profile v0 for eCTD v4.0 - NOT an EDA format.
     Every codeSystem containing "EG-PLACEHOLDER" is an invalid marker awaiting an EDA-registered OID.
     Product, company, people and numbers are invented. -->
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
        <item root="{EG_IG}" identifierName="EG M1 v4 provisional profile v0 (PLACEHOLDER)"/>
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
        <id root="{SU_ID}"/>
        <code code="eg_su_initial" codeSystem="{O(2)}"/>
        <title value="Initial MAA - Exemplofen 400 mg film-coated tablets (fictional)"/>
        <statusCode code="active"/>{''.join(cou_xml(d) for d in DOCS)}
        <componentOf1>
          <sequenceNumber value="1"/>
          <submission>
            <id><item root="{SUB_ID}" extension="PLACEHOLDER-TRACKING-0001"/></id>
            <code code="eg_st_maa" codeSystem="{O(3)}"/>
            <callBackContact>
              <contactParty>
                <id root="{CONTACT_ID}"/>
                <code code="eg_contact_1" codeSystem="{O(13)}"/>
                <statusCode code="active"/>
                <contactPerson>
                  <name><part type="GIV" value="Example"/><part type="FAM" value="Contact"/></name>
                  <telecom xsi:type="BAG_TEL"><item value="mailto:regulatory@example.invalid"/></telecom>
                  <asAgent><representedOrganization><name><part value="Fictitious Pharma Co. (EXAMPLE)"/></name></representedOrganization></asAgent>
                </contactPerson>
              </contactParty>
            </callBackContact>
            <subject2>
              <review>
                <id root="{REVIEW_ID}"/>
                <statusCode code="active"/>
                <subject1>
                  <manufacturedProduct>
                    <id root="{MP_ID}"/>
                    <manufacturedProduct>
                      <name><part value="Exemplofen"/></name>
                      <ingredient classCode="ACTI">
                        <ingredientSubstance><name><part value="Exemplofen sodium (fictional INN)"/></name></ingredientSubstance>
                      </ingredient>
                    </manufacturedProduct>
                  </manufacturedProduct>
                </subject1>
                <subject2><productCategory><code code="eg_regtype_local" codeSystem="{O(6)}"/></productCategory></subject2>
                <subject2><productCategory><code code="eg_mkttype_local" codeSystem="{O(7)}"/></productCategory></subject2>
              </review>
            </subject2>
            <componentOf>
              <application>
                <id><item root="{APP_ID}"/></id>
                <code code="eg_application_type_2" codeSystem="{O(4)}"/>
                <holder>
                  <applicant>
                    <sponsorOrganization>
                      <id><item root="{O(14)}" extension="PLACEHOLDER-PORTAL-ID-0001"/></id>
                      <name><part value="Fictitious Pharma Co. (EXAMPLE)"/></name>
                    </sponsorOrganization>
                  </applicant>
                </holder>
                <informationRecipient>
                  <territorialAuthority>
                    <territory><code code="eg" codeSystem="{O(11)}"/></territory>
                    <governingAuthority>
                      <id root="{O(12)}" extension="EG-EDA"/>
                      <name><part value="Egyptian Drug Authority"/></name>
                    </governingAuthority>
                  </territorialAuthority>
                </informationRecipient>{''.join(doc_xml(d) for d in DOCS)}
                <referencedBy>
                  <keywordDefinition>
                    <code code="ich_keyword_type_4" codeSystem="{ICH_KWT}"/>
                    <statusCode code="active"/>
                    <value>
                      <item code="PROD001" codeSystem="{SENDER_CS}">
                        <displayName value="Exemplofen 400 mg film-coated tablets"/>
                      </item>
                    </value>
                  </keywordDefinition>
                </referencedBy>
              </application>
            </componentOf>
          </submission>
        </componentOf1>
      </submissionUnit>
    </subject>
  </controlActProcess>
</PORP_IN000001UV>
'''
open(os.path.join(SEQ, 'submissionunit.xml'), 'w', encoding='utf-8', newline='\n').write(xml)
h = hashlib.sha256(xml.encode('utf-8')).hexdigest()
open(os.path.join(SEQ, 'sha256.txt'), 'w', newline='\n').write(h)   # 64 lower-case hex, no newline (format not fixed by IG: gap)
print('submissionunit.xml sha256', h)
