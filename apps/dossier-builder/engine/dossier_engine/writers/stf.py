"""Study Tagging Files — ICH eCTD STF Specification v2.6.1 (3 June 2008), DTD ich-stf-v2-2.dtd (updates list, item 46).

An STF tells a reviewer's tool which study each file of Modules 4 and 5 belongs to and what the file is (the synopsis, the protocol,
the CRFs…). The FDA requires one per study; the EU does not and asks that it be removed from a reused US dossier, grouping each
study under a node-extension instead; Japan does not allow it; EDA's drafts ask for the node-extension per study. So the eCTD
writers here group the studies by node-extension (writers/ectd32.py: study_of), and this module makes the STF a US sequence needs:

  <the study's folder>/stf-<study-id>.xml     one per study per sequence, next to the study's files (spec p. 4)
  its leaf in index.xml                       in the same Module 4/5 element, operation «new» the first time and «append» after,
                                              version="STF version 2.2" (spec p. 4–5)
  doc-content xlink:href                      ../…/index.xml#<leaf ID> of each study file, with its file-tag

The file-tags are the specification's table (pp. 7–9); the eCTD 4.0 document types 1–26 are the same names, so a document's
`doc_type` (the 4.0 code the page asks for) gives its tag. Categories (species, route of administration, type of control, and the
US duration) only for 4.2.3.1, 4.2.3.2, 4.2.3.4.1 and 5.3.5.1 (spec p. 5–7). Every STF made here is checked against the DTD."""
import posixpath
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

DTD = Path(__file__).resolve().parents[3] / 'rulepacks' / 'ich.ectd.v322' / 'stf' / 'ich-stf-v2-2.dtd'

FILE_TAGS = {                                            # name → (E3 reference, what the file is) — the specification's table
    'pre-clinical-study-report': ('', 'Pre-clinical study report'),
    'legacy-clinical-study-report': ('', 'Clinical study report submitted as one file'),
    'synopsis': ('2', 'Study report synopsis'),
    'study-report-body': ('1, 3–15', 'Study report body'),
    'protocol-or-amendment': ('16.1.1', 'Protocol and/or amendments'),
    'sample-case-report-form': ('16.1.2', 'Sample CRF'),
    'iec-irb-consent-form-list': ('16.1.3', 'IEC and IRB and consent form listings'),
    'list-description-investigator-site': ('16.1.4', 'Description of investigators and sites'),
    'signatures-investigators': ('16.1.5', 'Signatures of principal or coordinating investigator(s) or sponsor\'s responsible officer'),
    'list-patients-with-batches': ('16.1.6', 'Listing of patients receiving test drug(s) from specified batch'),
    'randomisation-scheme': ('16.1.7', 'Randomisation scheme'),
    'audit-certificates-report': ('16.1.8', 'Audit certificates or similar documentation'),
    'statistical-methods-interim-analysis-plan': ('16.1.9', 'Documentation of statistical methods and interim analysis plans'),
    'inter-laboratory-standardisation-methods-quality-assurance': ('16.1.10', 'Inter-laboratory standardisation methods and quality assurance'),
    'publications-based-on-study': ('16.1.11', 'Publications based on the study'),
    'publications-referenced-in-report': ('16.1.12', 'Publications referenced in the study report'),
    'discontinued-patients': ('16.2.1', 'Discontinued patients listing'),
    'protocol-deviations': ('16.2.2', 'Protocol deviation listing'),
    'patients-excluded-from-efficacy-analysis': ('16.2.3', 'Patients excluded from efficacy analysis listing'),
    'demographic-data': ('16.2.4', 'Demographic data listing'),
    'compliance-and-drug-concentration-data': ('16.2.5', 'Compliance and/or drug concentration data listing'),
    'individual-efficacy-response-data': ('16.2.6', 'Individual efficacy response data listing'),
    'adverse-event-listings': ('16.2.7', 'Adverse event listings'),
    'listing-individual-laboratory-measurements-by-patient': ('16.2.8', 'Individual laboratory measurements listed by patient'),
    'case-report-forms': ('16.3', 'CRF for an individual subject (in the US with its site-identifier property)'),
    'available-on-request': ('', 'A file listing documents available upon request for a single study'),
}
CATEGORIES = {                                           # name → (info-type, values)
    'species': ('ich', ('mouse', 'rat', 'hamster', 'other-rodent', 'rabbit', 'dog', 'non-human-primate', 'other-non-rodent-mammal', 'non-mammals')),
    'route-of-admin': ('ich', ('oral', 'intravenous', 'intramuscular', 'intraperitoneal', 'subcutaneous', 'inhalation', 'topical', 'other')),
    'duration': ('us', ('short', 'medium', 'long')),
    'type-of-control': ('ich', ('placebo', 'no-treatment', 'dose-response-without-placebo', 'active-control-without-placebo', 'external')),
}
CATEGORY_NODES = {'4.2.3.1': ('species', 'route-of-admin'), '4.2.3.2': ('species', 'route-of-admin', 'duration'),
                  '4.2.3.4.1': ('species',), '5.3.5.1': ('type-of-control',)}


class STFError(ValueError):
    pass


def tag_of(doc_type):
    """The file-tag of an eCTD 4.0 document type code (ich_document_type_1 … _26 are the STF's tags), or a tag given by name."""
    if doc_type in FILE_TAGS:
        return doc_type
    try:
        n = int(str(doc_type).rsplit('_', 1)[-1])
    except ValueError:
        return None
    return list(FILE_TAGS)[n - 1] if 1 <= n <= len(FILE_TAGS) else None


def file_name(study_id):
    """«stf-» + the sponsor's study code + «.xml» (spec p. 4), in the eCTD's characters."""
    import re
    code = re.sub(r'[^a-z0-9-]+', '-', (study_id or '').lower()).strip('-')
    if not code:
        raise STFError('An STF needs the study identifier.')
    return f'stf-{code}.xml'


def make(study_id, title, docs, stf_rel, node=None, categories=(), lang='en', stylesheet=False):
    """The STF of one study for one sequence. docs: [{'leaf_id', 'doc_type' or 'tag', 'title'?, 'site'?}]; stf_rel: where the STF goes
    in the sequence (e.g. m5/53-clin-stud-rep/…/study-1/stf-study-1.xml); categories: [(name, value)] — only where the node takes them.
    → the XML text, checked against the DTD."""
    depth = posixpath.dirname(stf_rel).count('/') + 1 if posixpath.dirname(stf_rel) else 0
    up = '../' * depth
    allowed = CATEGORY_NODES.get(node or '', ())
    cats = []
    for name, value in categories:
        if name not in allowed:
            raise STFError(f'{node}: no «{name}» category here (only {", ".join(allowed) or "none"}; spec p. 5).')
        info, values = CATEGORIES[name]
        if value not in values:
            raise STFError(f'{name}: «{value}» is not one of {", ".join(values)}.')
        cats.append(f'  <category name={quoteattr(name)} info-type={quoteattr(info)}>{escape(value)}</category>\n')
    body = []
    for d in docs:
        tag = d.get('tag') or tag_of(d.get('doc_type'))
        if tag not in FILE_TAGS:
            raise STFError(f'{d.get("leaf_id")}: no STF file-tag for {d.get("doc_type") or d.get("tag")!r}.')
        prop = (f'      <property name="site-identifier" info-type="us">{escape(d["site"])}</property>\n'
                if d.get('site') and tag == 'case-report-forms' else '')
        t = f'    <title>{escape(d["title"])}</title>\n' if d.get('title') else ''
        body.append(f'  <doc-content xlink:href={quoteattr(up + "index.xml#" + d["leaf_id"])}>\n{t}'
                    f'    <file-tag name={quoteattr(tag)} info-type="ich">\n{prop}    </file-tag>\n  </doc-content>\n'
                    if prop else
                    f'  <doc-content xlink:href={quoteattr(up + "index.xml#" + d["leaf_id"])}>\n{t}'
                    f'    <file-tag name={quoteattr(tag)} info-type="ich"/>\n  </doc-content>\n')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           + (f'<?xml-stylesheet type="text/xsl" href="{up}util/style/ich-stf-stylesheet.xsl"?>\n' if stylesheet else '')
           + f'<!DOCTYPE ectd:study SYSTEM "{up}util/dtd/ich-stf-v2-2.dtd">\n'
           f'<ectd:study xmlns:ectd="http://www.ich.org/ectd" xml:lang={quoteattr(lang)} dtd-version="2.2" xmlns:xlink="http://www.w3.org/1999/xlink">\n'
           f' <study-identifier>\n  <title>{escape(title or study_id)}</title>\n  <study-id>{escape(study_id)}</study-id>\n{"".join(cats)} </study-identifier>\n'
           + (' <study-document>\n' + ''.join('  ' + ln + '\n' for ln in ''.join(body).splitlines()) + ' </study-document>\n' if body else ' <study-document/>\n')
           + '</ectd:study>\n')
    problems = check(xml)
    if problems:
        raise STFError('; '.join(problems))
    return xml


def check(xml_text):
    """[] when the STF is valid against ich-stf-v2-2.dtd, else the DTD's messages."""
    from lxml import etree
    dtd = etree.DTD(str(DTD))
    doc = etree.fromstring(xml_text.encode('utf-8'), etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False))
    return [] if dtd.validate(doc) else [str(e) for e in dtd.error_log.filter_from_errors()][:20]


def for_sequence(history, docs_meta, seq_dir):
    """The STFs a US sequence would carry: one per (element, study) of its study reports (4.2.x, 5.3.x — the tabular listing and the
    literature references are not studies). history: the writer's leaves
    [{doc_id, leaf_id, href, node, op}]; docs_meta: {doc_id: {'study', 'doc_type', 'title'}}. → [(stf path, xml)]"""
    groups = {}
    for lf in history:
        m = docs_meta.get(lf.get('doc_id')) or {}
        if lf.get('op') == 'delete' or not m.get('study') or not str(lf.get('node') or '').startswith(('4.2.', '5.3.')) or not lf.get('href'):
            continue
        groups.setdefault((lf['node'], m['study']), []).append({'leaf_id': lf['leaf_id'], 'doc_type': m.get('doc_type'), 'title': m.get('title'),
                                                               'folder': posixpath.dirname(lf['href'])})
    out = []
    for (node, study), docs in groups.items():
        rel = posixpath.join(docs[0]['folder'], file_name(study))
        out.append((rel, make(study, study, docs, rel, node)))
    return out
