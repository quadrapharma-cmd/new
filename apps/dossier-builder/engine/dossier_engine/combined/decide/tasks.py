"""The five tasks Claude does inside the program, in order: the documents, the product and Egypt's Module 1, the product
information, the reviewer's findings, the eCTD sequence. Each: its part of the playbook (general rules), its writing tools, and its case file (the first message, made by the
program from the work folder)."""
import json

import yaml

from ..common import APP, ranges

PREAMBLE = """You work inside eBOX, a program that prepares medicines' registration dossiers for the Egyptian Drug Authority (EDA). \
A company's dossier arrived as received files — often one combined PDF of thousands of pages, partly scanned, with blocks sent \
twice and a Module 1 written for another region. The program has numbered every page, read every page's text (with OCR for \
scanned pages), left out the blocks received twice and proposed how to cut the pages into CTD documents, by its rules. Then it \
builds the CTD folder, checks it, corrects what can be corrected, writes the product information, builds the eCTD sequence (EG \
eCTD 3.2.2) and validates it, and writes the reports for the owner.

You make the decisions its rules cannot make — the decisions an experienced regulatory publisher and reviewer makes by hand — \
and you record them with the tools. The program checks each decision when you record it; when a tool returns an error, correct \
the decision and record it again. Nobody reviews your work before it is used: be exact.

How you work:
- Work from the dossier's own pages. Every fact you record comes from a page you read, with its pages («p 324», or «ص 324» in \
Arabic). Never invent a value; what the dossier does not show goes to the values to confirm or the company's gaps, never into \
the documents.
- The company's documents stay as they are: you cut, place, name and title them. A correction inside a company PDF deletes \
characters only (a wrong unit, a misprinted number) and only where the dossier itself shows the right value.
- Read economically: the document list shows each document's first lines; read a page or two to know what a document is; \
search for a phrase before reading many pages; look at a page's picture only when its text is missing or unclear.
- Language: what the report shows the owner (findings, the product card, Module 1's needs, the company's gaps, the values to \
confirm, translation notes, the reports' titles) is written in formal Arabic (فصحى), never colloquial. A CTD module is \
«Module N» in Latin letters, never «الوحدة N»; CTD numbers, units, and product, company and substance names stay in Latin \
letters as the dossier writes them. Notes on documents, file names, leaf titles, the envelope and the cover letter are in English.
- When the task is done, call finish with a short summary of what you decided. Do not stop without calling finish.
"""

TASK_TEXT = {
    'documents': """
TASK 1 — THE DOCUMENTS. Check the program's cut of the dossier into CTD documents and correct it, so that every kept page is in \
the right document under the right CTD number, and only pages without content are left out.

What to look for (the cases its rules miss):
1. Name the drug substances and the product first, with set_names: each drug substance block (its top-level bookmark title) \
gets a short name «<substance> (<manufacturer's short name>)», the product «<product> (<manufacturer's short name>)». The paths \
of the drug substance and product documents use these names.
2. Annexures and appendices the program could not place (paths under «Module 3/Annexures to be placed/…»): find where the \
dossier cites each one (search «Annexure 1», «Appendix A» …) and file it under the citing section's CTD number with its own \
title («Annexure 1 – <its title>»). An annexure cited by the same section of several drug substances goes under that section \
in the folder «Module 3/3.2.S Common to the N drug substances/». A document over the size limit was cut into parts by the \
program: keep the parts, titled «(part 1 of 2)» …
3. Guidelines and pharmacopoeial or WHO texts the company enclosed are literature references: 3.3 (quality), 4.3 (nonclinical), \
5.4 (clinical), one document for each publication, titled by it («WHO TRS 800 (1990) Annex 2 – …»).
4. Clinical study reports in 5.3: file each study by what it is — 5.3.1 biopharmaceutic, 5.3.2 PK with human biomaterials, \
5.3.3 human PK, 5.3.4 human PD, 5.3.5.1 controlled studies (one document for each study, titled by the study, its code and \
site), 5.3.5.2 uncontrolled studies, 5.3.5.3 analyses of data from more than one study (pooled), 5.3.5.4 other study reports, \
5.3.6 post-marketing experience, 5.3.7 case report forms and patient listings. A page that only says «not applicable» or «no \
studies» stays its section's document.
5. Module 2: keep the CTD table of contents (Modules 2–5) as document 2.1 when the dossier has it.
6. A Module 1 written for another region (e.g. the EU's 1.0–1.10): keep all its pages, as documents named by the received \
section, in the folder «Module 1 - EU layout as received (for reference)» (another region: its name instead of EU); a section \
that is only its heading page is «<number> <title> (heading page only)». They are mapped to Egypt's Module 1 in a later task.
7. Only tables of contents at the start of a block, covers, separators and blank pages are left out. A page with content that \
was left out goes back to its document.
8. A page whose printed CTD number contradicts its title goes where its title says (the program usually did this: read its note).

Paths follow the program's convention: «Module N/<section folders>/<CTD number> <Title>.pdf», with the folder names the \
document list already uses. place_pages moves pages into a document (a new one, or the one with the same path); leave_out \
removes pages; a note is one short English sentence on why a document is where it is.""",

    'product': """
TASK 2 — THE PRODUCT AND EGYPT'S MODULE 1. Record the product's data, the eCTD envelope, the cover letter, the product card, and \
what Egypt's Module 1 needs for this product.

Record, in this order:
1. set_envelope: the applicant (the marketing authorisation holder as the dossier states it; for an imported product usually \
the manufacturer — when the Egyptian agent may be the applicant, add it to the values to confirm), the invented name (as the \
SmPC names the product), the active substances (lower case), the registration type (imported-finished for a finished product \
made abroad; local for one made in Egypt; toll, f-toll, under-license or imported-bulk as the case is), the marketing type \
(local unless the dossier says tender, export or hospital) and a one-sentence English description of the submission.
2. set_product: the product name, the dosage form (the EDQM standard term), the manufacturer (name, city, country), the \
indication (short), each drug substance {name as given in set_names, folder «<substance>-<maker>» in lower case with hyphens, \
substance: its name}, product_folder and indication_folder (short, lower case with hyphens), excipient («all excipients»).
3. set_cover: the cover letter's subject (HTML, the product name in <b>), its opening sentence (the sequence follows the ICH \
eCTD specification v3.2.2 and the EG Module 1 eCTD specification (draft)), the product table (Name; Pharmaceutical form, route; \
Composition per unit; Presentations; Marketing authorisation holder and manufacturer; Registration type) and one line for each \
module saying what it holds.
4. set_product_card: the product as the dossier states it, rows [label in Arabic, value as written in the dossier, «ص n»]: \
name, the name in the clinical studies if different, form and route, composition per unit, the active substances and their \
source, indication, posology, storage, shelf life, presentations, marketing authorisation holder and manufacturer, the \
manufacturing licence, the clinical studies — what applies.
5. set_eg_m1: one sentence in Arabic on the received Module 1, then a row for each item of EDA's Module 1 (the list given) that \
applies to this product and registration type: [the item (its EDA number and Arabic name), its state in this dossier with pages \
(present, missing, or present but not usable and why), who provides it (الشركة، الشركة المصنعة، الوكيل في مصر، الهيئة، or the \
authority of the country of origin)]. Items the program builds (the cover letter, the product information, the tracking table) \
are built by the program.
6. add_to_confirm for each value the owner must confirm (the applicant, the submission, registration and marketing types, the \
name, the presentations …) and add_company_gap for each document or data the company must still provide.
7. set_titles: the two reports' titles and subtitles in Arabic: «ملف تسجيل <the product> (<its manufacturer, in Arabic>)» and «بناه البرنامج eBOX من الملف الوارد، <today>»; «ملف eCTD لـ<the product> (<its manufacturer>)» and «التسلسل 0000، بناه البرنامج eBOX، <today>» (today's date is in the case file).""",

    'pi': """
TASK 3 — THE PRODUCT INFORMATION. Write the product information to submit in Egypt from the company's own texts in the dossier: \
the SmPC, the package leaflet, the outer and the immediate labelling texts in English, corrected where the dossier itself shows \
them wrong, and the package leaflet in formal Arabic.

1. Read the company's texts and the data they must agree with: 3.2.P.1 (composition), 3.2.P.4 (excipients), 3.2.P.3.2 (batch \
formula), 3.2.P.7 (container closure), 3.2.P.8 (stability: shelf life, storage), the mock-ups (presentations), the clinical \
sections (posology).
2. Write each document with write_pi_document as blocks in the company's order: {"t": the document's title}, {"h": a section \
heading}, {"s": a sub-heading}, {"p": a paragraph}, {"b": a bullet item}, {"rows": [[name, value], …]} for the composition \
table. Keep the company's wording; change only what is wrong or missing, and record every change with add_pi_change [where in \
the product information, the old text, the new text, the pages that show it]: a unit that contradicts 3.2.P.1, an incomplete \
list of excipients, a shelf life or storage condition stated otherwise in 3.2.P.8, a container described otherwise in 3.2.P.7, \
presentations against the mock-ups. Keys: SPC, PIL, OUTER, IMPACK (English), then PIL_AR. A long document can be written in \
one call; give block_count = the number of blocks.
3. PIL_AR is the leaflet in formal Arabic: the same blocks, in the same order and of the same kinds, the same numbers in each \
block, the composition values written exactly as in English (the program checks this and returns each difference: correct it \
and write it again). Product, substance and company names and units stay in Latin letters.
4. When the same error is printed in the company's own PDFs (e.g. a wrong unit in Module 2), correct it there with \
correct_in_pdf: the document's path, the page within the document, the exact phrase and the phrase with characters deleted \
(«1.25 mcg» → «1.25 mg»). The program refuses an edit that adds characters or a phrase it does not find exactly once.
5. add_translation_note for what the reader of the Arabic leaflet must know (in Arabic).
Names: title = the document's own title («Summary of Product Characteristics», «Package Leaflet», «Labelling (outer packaging)», «Labelling (immediate packaging)», «Package leaflet (Arabic)»); ectd_title = «Summary of Product Characteristics (English) - proposed, corrected» (or «- proposed» when nothing was corrected), «Package leaflet (English) - proposed, corrected», «Outer packaging labelling text (English)», «Immediate packaging labelling text (English)», «Package leaflet (Arabic) - proposed». With the first document give header = the product's full name, creator = «<company> (text) — corrections listed in the report», and with PIL_AR creator_ar = «Arabic translation of the corrected package leaflet».""",

    'review': """
TASK 4 — THE REVIEWER'S FINDINGS. The program's rules made the findings you are given. Find what a reviewer at EDA would find and \
the rules cannot: contradictions between the product information and Module 3, between Module 2 and Module 3, incomplete \
lists, a section that says «not applicable» where the dossier shows it applies (e.g. materials of animal origin with an \
adventitious agents section that says not applicable), outdated references, data a product of this kind needs and the dossier \
lacks, stability data shorter than the shelf life claimed.
For each, add_finding: severity (critical: a wrong value that changes the product information or safety; major: missing or \
contradictory data EDA will ask for; minor: form), the finding in formal Arabic with its values and pages, where (pages), and \
what the company must do. Do not repeat a finding the rules made. add_company_gap and add_to_confirm where needed.""",

    'sequence': """
TASK 5 — THE eCTD SEQUENCE. You get the sequence the program built: each document's leaf (CTD number, folder, file, title), the \
documents it left out of the sequence and why, the EG Module 1 leaves mapped from the received Module 1, and the validation's \
failed rules. Correct:
- leaf titles: the document's own title, clear, in English; a drug substance's document ends with the substance in parentheses \
when several substances share the section;
- file names: ICH's (the program's), with a short suffix when several documents share a section («control-of-materials-annex1-\
part1.pdf»);
- the documents left out: a document that only says «not applicable» is left out unless the section needs the statement; a \
wrong «not applicable» is left out with the reason in Arabic (and it is a company gap); a document that only refers to another \
section is left out with the reason;
- Module 1 (EG): each leaf's title (e.g. «Mock-ups of the current packs (languages) - Egyptian artwork to follow»), and which \
pages of the received document go into it (the pages with content, not the heading pages).
Use set_leaf, leave_out_of_sequence, keep_in_sequence and set_m1_leaf. Validation failures you cannot fix (e.g. the tracking \
number EDA gives) stay.""",
}


def T(name, desc, props, required):
    return {'name': name, 'description': desc, 'eager_input_streaming': True,
            'input_schema': {'type': 'object', 'properties': props, 'required': required}}


S = {'type': 'string'}
ROWS3 = {'type': 'array', 'items': {'type': 'array', 'items': {'anyOf': [S, {'type': 'array', 'items': S}]}}}   # a cell: a text or its lines
FINISH = T('finish', 'The task is done: a short summary of what you decided.', {'summary': S}, ['summary'])

TOOLS = {
    'documents': [
        T('set_names', 'The drug substances\' short names (by their top-level bookmark title) and the product\'s.',
          {'substances': {'type': 'object', 'additionalProperties': S}, 'product': S}, ['substances', 'product']),
        T('place_pages', 'Pages into a document of the CTD folder (a new one, or the one with this path).',
          {'pages': S, 'path': S, 'ctd': S, 'title': S, 'note': S}, ['pages', 'path', 'ctd', 'title']),
        T('leave_out', 'Pages left out of the CTD folder (covers, separators, tables of contents, blank pages), with why.',
          {'pages': S, 'why': S}, ['pages', 'why']),
        T('set_note', 'A note on a document: why it is where it is (one short English sentence).', {'path': S, 'note': S}, ['path', 'note']),
    ],
    'product': [
        T('set_envelope', 'The eCTD envelope.', {'applicant': S, 'invented_name': S, 'inn': {'type': 'array', 'items': S},
          'registration': {'type': 'string', 'enum': ['local', 'toll', 'f-toll', 'under-license', 'imported-finished', 'imported-bulk']},
          'marketing': {'type': 'string', 'enum': ['local', 'tender', 'export', 'hospital']}, 'description': S},
          ['applicant', 'invented_name', 'inn', 'registration', 'marketing', 'description']),
        T('set_product', 'The product\'s data for the sequence.',
          {'product_name': S, 'dosage_form': S, 'manufacturer': S, 'indication': S,
           'substances': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': S, 'folder': S, 'substance': S},
                                                     'required': ['name', 'folder', 'substance']}},
           'product_folder': S, 'indication_folder': S, 'excipient': S},
          ['product_name', 'dosage_form', 'manufacturer', 'indication', 'substances', 'product_folder', 'indication_folder']),
        T('set_cover', 'The cover letter.', {'subject_html': S, 'opening': S, 'product': ROWS3, 'content': {'type': 'array', 'items': S}},
          ['subject_html', 'opening', 'product', 'content']),
        T('set_product_card', 'The product card: rows [label (Arabic), value, pages].', {'row_count': {'type': 'integer'}, 'rows': ROWS3},
          ['row_count', 'rows']),
        T('set_eg_m1', 'Egypt\'s Module 1 for this product: an Arabic sentence, then rows [item, state with pages, who provides it].',
          {'intro': S, 'row_count': {'type': 'integer'}, 'rows': ROWS3}, ['intro', 'row_count', 'rows']),
        T('set_titles', 'The reports\' titles (Arabic).', {'title': S, 'subtitle': S, 'ectd_title': S, 'ectd_subtitle': S},
          ['title', 'subtitle', 'ectd_title', 'ectd_subtitle']),
    ],
    'pi': [
        T('write_pi_document', 'One document of the product information, as blocks (see the task).',
          {'key': {'type': 'string', 'enum': ['SPC', 'PIL', 'OUTER', 'IMPACK', 'PIL_AR']}, 'title': S, 'ectd_title': S,
           'header': S, 'creator': S, 'creator_ar': S, 'block_count': {'type': 'integer'},
           'blocks': {'type': 'array', 'items': {'type': 'object'}}},
          ['key', 'title', 'ectd_title', 'block_count', 'blocks']),
        T('add_pi_change', 'A change made to the company\'s product information, with the pages that show it.',
          {'where': S, 'old': S, 'new': S, 'source': S}, ['where', 'old', 'new', 'source']),
        T('correct_in_pdf', 'A correction inside a company PDF of the CTD folder: characters deleted only.',
          {'doc': S, 'page': {'type': 'integer'}, 'old': S, 'new': S, 'note': S}, ['doc', 'page', 'old', 'new', 'note']),
        T('add_translation_note', 'A note on the Arabic translation, for the report (Arabic).', {'text': S}, ['text']),
    ],
    'review': [
        T('add_finding', 'A reviewer\'s finding (formal Arabic).', {'severity': {'type': 'string', 'enum': ['critical', 'major', 'minor']},
          'text': S, 'where': S, 'action': S}, ['severity', 'text', 'where', 'action']),
    ],
    'sequence': [
        T('set_leaf', 'A document\'s leaf in the sequence: its file name, folder or title.', {'doc': S, 'file': S, 'folder': S, 'title': S},
          ['doc']),
        T('leave_out_of_sequence', 'A document not submitted as a leaf, with why (Arabic).', {'doc': S, 'why': S}, ['doc', 'why']),
        T('keep_in_sequence', 'A document the program left out that must be submitted.', {'doc': S}, ['doc']),
        T('set_m1_leaf', 'An EG Module 1 leaf made from a received Module 1 document: its title, the pages kept, or skip.',
          {'doc': S, 'title': S, 'pages': S, 'skip': {'type': 'boolean'}}, ['doc']),
    ],
}
GAP_TOOLS = [
    T('add_to_confirm', 'A value the owner must confirm: [item, the value recorded, why] (Arabic).', {'item': S, 'value': S, 'why': S},
      ['item', 'value', 'why']),
    T('add_company_gap', 'What the company must still provide: [what, where it is needed, who provides it] (Arabic).',
      {'item': S, 'where': S, 'who': S}, ['item', 'where', 'who']),
]
for _t in ('product', 'review'):
    TOOLS[_t] = TOOLS[_t] + GAP_TOOLS


def counted(fn, key, count):
    """A list sent with its count: a list the tolerant parser cut short is refused, not recorded short."""
    def run(a):
        from .brain import ToolError
        items = a.get(key)
        if not isinstance(a.get(count), int) or not isinstance(items, list) or len(items) != a[count]:
            raise ToolError(f'«{count}» ({a.get(count)}) is not the number of «{key}» received ({len(items) if isinstance(items, list) else 0}): '
                            'send the whole list again.')
        return fn(a)
    return run


def handlers(task, store):
    s = store
    return {
        'documents': {'set_names': s.names, 'place_pages': s.place, 'leave_out': s.leave_out, 'set_note': s.note},
        'product': {'set_envelope': s.envelope, 'set_product': s.product, 'set_cover': s.cover,
                    'set_product_card': counted(s.card, 'rows', 'row_count'), 'set_eg_m1': counted(s.eg_m1, 'rows', 'row_count'),
                    'set_titles': s.titles, 'add_to_confirm': s.to_confirm, 'add_company_gap': s.gap},
        'pi': {'write_pi_document': counted(s.write_pi, 'blocks', 'block_count'), 'add_pi_change': s.pi_change,
               'correct_in_pdf': s.fix_in_pdf, 'add_translation_note': s.translation_note},
        'review': {'add_finding': s.finding, 'add_to_confirm': s.to_confirm, 'add_company_gap': s.gap},
        'sequence': {'set_leaf': s.leaf, 'leave_out_of_sequence': s.ectd_out, 'keep_in_sequence': s.ectd_in, 'set_m1_leaf': s.m1},
    }[task]


# -- the case files
def eda_m1():
    """EDA's Module 1 items as the program holds them (NTA 065 v5, rulepacks/eda.ctd.nta065.v5)."""
    p = APP / 'rulepacks' / 'eda.ctd.nta065.v5' / 'requirements.yaml'
    items = yaml.safe_load(p.read_text(encoding='utf-8'))
    out = ['(required for: I = innovator, G_IMP = generic imported, G_LOC = generic local; R required, O optional, NR not '
           'required; «when» is the condition the program holds)']
    for x in items:
        if str(x.get('id', '')).startswith('M1'):
            num = (x.get('ctd') or {}).get('nta065_v5', '')
            t = x.get('title') or {}
            title = f"{t.get('en', '')} / {t.get('ar', '')}" if isinstance(t, dict) else str(t)
            req = x.get('required') or {}
            req = ', '.join(f"{k}={v if isinstance(v, str) else 'by case'}" for k, v in req.items()) if isinstance(req, dict) else str(req)
            when = '' if str(x.get('applies', True)).lower() == 'true' else f" — when: {x.get('applies')}"
            cond = f" — {x['condition_note']}" if x.get('condition_note') else ''
            out.append(f'{num} {title} [{req}]{when}{cond}')
    return '\n'.join(out)


def findings_text(w):
    return '\n'.join(f"[{f['severity']}] {f['text']} — {f.get('where', '')}" for f in (w.load('findings.json', []) or [])) or '(none)'


def first_message(task, w, case):
    plan = w.load('plan.json', {}) or {}
    dec = w.decisions()
    head = f"The dossier: {case.n} pages.\n\nRECEIVED FILES\n{case.received()}\n"
    if task == 'documents':
        miss = plan.get('missing') or []
        pf = '\n'.join(json.dumps(x, ensure_ascii=False) for x in plan.get('findings', [])) or '(none)'
        return (head + f"\nBOOKMARKS (two levels)\n{case.outline()}\n\nTHE DOCUMENTS AS PROPOSED ({len(plan.get('docs', []))})\n"
                f"{case.documents(plan)}\n\nPAGES LEFT OUT\n{case.removed(plan)}\n\nPAGES WITH NO PLACE\n"
                f"{ranges(miss) if miss else '(none)'}\n\nWHAT THE PROGRAM NOTICED WHILE CUTTING\n{pf}\n\n"
                'Check the cut and correct it (task 1).')
    docs = case.documents(plan, first_line=(task != 'sequence'))
    if task == 'product':
        import datetime
        today = (dec.get('ectd') or {}).get('today') or datetime.date.today().isoformat()
        head += f"TODAY: {datetime.date.fromisoformat(today).strftime('%d/%m/%Y')}\n"
        return (head + f"\nTHE DOCUMENTS ({len(plan.get('docs', []))})\n{docs}\n\nTHE NAMES GIVEN\n"
                f"{json.dumps(dec.get('names', {}), ensure_ascii=False)}\n\nEDA'S MODULE 1 ITEMS (NTA 065 v5)\n{eda_m1()}\n\n"
                'Record the product and Egypt\'s Module 1 (task 2).')
    if task == 'pi':
        return (head + f"\nTHE DOCUMENTS ({len(plan.get('docs', []))})\n{docs}\n\nTHE RULES' FINDINGS\n{findings_text(w)}\n\n"
                f"THE PRODUCT (recorded in task 2)\n{json.dumps((dec.get('ectd') or {}).get('product', {}), ensure_ascii=False)}\n\n"
                'Write the product information (task 3).')
    if task == 'review':
        return (head + f"\nTHE DOCUMENTS ({len(plan.get('docs', []))})\n{docs}\n\nTHE RULES' FINDINGS\n{findings_text(w)}\n\n"
                f"THE PRODUCT INFORMATION'S CHANGES (task 3)\n"
                f"{json.dumps((dec.get('report') or {}).get('pi_changes', []), ensure_ascii=False)}\n\nFind what the rules did not (task 4).")
    if task == 'sequence':
        e = w.load('ectd.json', {}) or {}
        leaves = '\n'.join(f"{l.get('code')} | {l.get('folder')}/{l.get('file')} | {l.get('title')} | {l.get('doc')}"
                           for l in e.get('leaves', []))
        out = '\n'.join(f'{k}: {v}' for k, v in (e.get('left_out') or {}).items())
        folder = str(w.ctd / (dec.get('ctd_folder') or 'CTD')) + '/'
        m1 = '\n'.join(f"{x[0]} | {x[2]} | {x[3]} | from {str(x[6])[len(folder):] if str(x[6]).startswith(folder) else 'made by the program'}"
                       f" | pages {ranges(x[7]) if x[7] else '-'}" for x in e.get('m1', []))
        failed = '\n'.join(f"{r['rule']} ({r['kind']}): {r.get('detail', '')}" for r in (w.load('validation.json', []) or []) if not r['ok'])
        return (head + f"\nTHE DOCUMENTS ({len(plan.get('docs', []))})\n{docs}\n\nTHE LEAVES (CTD | folder/file | title | document)\n{leaves}"
                f"\n\nLEFT OUT OF THE SEQUENCE\n{out or '(none)'}\n\nMODULE 1 (EG)\n{m1}\n\nVALIDATION: FAILED RULES\n{failed or '(none)'}\n\n"
                'Correct the sequence (task 5).')
    raise KeyError(task)
