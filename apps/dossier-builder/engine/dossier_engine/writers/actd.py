"""Writer — the ASEAN Common Technical Dossier (ACTD) from the same dossier (updates list, item 45).

The ACTD holds the CTD's content in four parts instead of five modules: the overviews and summaries of Module 2 sit at the front of
the part they summarise. The map (ASEAN Common Technical Dossier, Organization of the Dossier, Revision 1 — taken as data from the
ectd-dossier-builder project, Apache-2.0, see THIRD-PARTY-NOTICES.md; check it against the ASEAN text and the member state's own
guidance before filing):

  Module 1                              → Part I    Table of contents, administrative data and product information
  2.3 Quality overall summary           → Part II   Section B  Quality overall summary
  3.2 Body of data (S, P, A, R)         → Part II   Section C  Body of data (S1–S7 per substance, P1–P8, then 3.2.A / 3.2.R)
  3.3 Literature references             → Part II   Section D  Key literature references
  2.4 Nonclinical overview              → Part III  Section B  Nonclinical overview
  2.6 Nonclinical summaries             → Part III  Section C  Nonclinical written and tabulated summaries
  Module 4 study reports                → Part III  Section D  Nonclinical study reports
  4.3 Literature references             → Part III  Section E  Key literature references
  2.5 Clinical overview                 → Part IV   Section B  Clinical overview
  2.7 Clinical summary                  → Part IV   Section C  Clinical summary
  5.2 Tabular listing                   → Part IV   Section D  Tabular listing of all clinical studies
  5.3 Clinical study reports            → Part IV   Section E  Clinical study reports
  5.4 Literature references             → Part IV   Section F  List of key literature references

2.1 (the CTD's table of contents) and 2.2 (its introduction) go to Part I, where the ACTD keeps the dossier's table of contents.
The ACTD is a paper or PDF format with no eCTD backbone: the folders carry the parts and sections, 00-actd-map.csv says for every
document where it came from in the CTD, and 00-navigator.html lists everything."""
import csv, shutil
from pathlib import Path
from .ctd import clean, _navigator, MAX_PATH
from .ectd32 import WriterError

PARTS = {'I': 'Part I - Administrative data and product information', 'II': 'Part II - Quality',
         'III': 'Part III - Nonclinical', 'IV': 'Part IV - Clinical'}
SECTIONS = {('II', 'B'): 'Section B - Quality overall summary', ('II', 'C'): 'Section C - Body of data', ('II', 'D'): 'Section D - Key literature references',
            ('III', 'B'): 'Section B - Nonclinical overview', ('III', 'C'): 'Section C - Nonclinical written and tabulated summaries',
            ('III', 'D'): 'Section D - Nonclinical study reports', ('III', 'E'): 'Section E - Key literature references',
            ('IV', 'B'): 'Section B - Clinical overview', ('IV', 'C'): 'Section C - Clinical summary',
            ('IV', 'D'): 'Section D - Tabular listing of all clinical studies', ('IV', 'E'): 'Section E - Clinical study reports',
            ('IV', 'F'): 'Section F - List of key literature references'}


def place(ctd):
    """A CTD section number → (part, section or None, the ACTD heading of the section inside its part or None)."""
    c = (ctd or '').split(' (')[0].strip()
    if c.startswith('1') or c in ('2.1', '2.2') or c.startswith(('2.1.', '2.2.')):
        return 'I', None, None
    if c.startswith('2.3'):
        return 'II', 'B', None
    if c.startswith('3.2.S'):
        return 'II', 'C', 'S' + c[len('3.2.S.'):] if len(c) > 5 else 'S'
    if c.startswith('3.2.P'):
        return 'II', 'C', 'P' + c[len('3.2.P.'):] if len(c) > 5 else 'P'
    if c.startswith(('3.2.A', '3.2.R')) or c in ('3.2', '3'):
        return 'II', 'C', c[4:].replace('.', '') if c.startswith('3.2.') else None
    if c.startswith('3.3'):
        return 'II', 'D', None
    if c.startswith('2.4'):
        return 'III', 'B', None
    if c.startswith('2.6'):
        return 'III', 'C', None
    if c.startswith('4.3'):
        return 'III', 'E', None
    if c.startswith('4'):
        return 'III', 'D', None
    if c.startswith('2.5'):
        return 'IV', 'B', None
    if c.startswith('2.7'):
        return 'IV', 'C', None
    if c.startswith('5.2'):
        return 'IV', 'D', None
    if c.startswith('5.4'):
        return 'IV', 'F', None
    if c.startswith('5'):
        return 'IV', 'E', None
    return 'I', None, None


def write(out_dir, root_name, slots, files):
    """slots: the resolver's (all, with NR/NA); files: {slot_id: [{file, title?, ext?}]}. → {path, files, missing}"""
    root = Path(out_dir) / clean(root_name + ' - ACTD', 60)
    if root.exists():
        raise WriterError(f'{root} exists — an export is never overwritten')
    rows, written, missing, mapping, n = [], [], [], [], {}
    for s in slots:
        if not s.active:
            rows.append((s, []))
            continue
        sec = s.ctd.split(' (')[0]
        part, section, head = place(sec)
        base = Path(PARTS[part]) / (SECTIONS[(part, section)] if section else '')
        if s.item and sec.startswith('3.2.S'):                  # one folder per substance and manufacturer, as the CTD
            base = base / clean(f"S {s.item['name']} - {s.item['manufacturer']}", 60)
        n[base] = n.get(base, 0) + 1
        label = f'{head} {s.title["en"]}' if head else f'{sec} {s.title["en"]}'
        folder = base / clean(f'{n[base]:02d} {label}', 44)
        got = files.get(s.slot_id, [])
        if not got and s.level == 'R':
            missing.append(s.slot_id)
        placed = []
        for i, f in enumerate(got):
            suffix = (f'-{i + 1}' if len(got) > 1 else '') + (f.get('ext') or '.pdf')
            budget = min(56, MAX_PATH - len(f'{root.name}/{folder}/') - len(suffix))
            if budget < 12:
                raise WriterError(f'path budget exhausted under {folder}')
            rel = folder / (clean(f'{head or sec} {f.get("title") or s.title["en"]}', budget) + suffix)
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f['file'], root / rel)
            placed.append(str(rel))
            written.append(str(rel))
            mapping.append([sec, s.title['en'], PARTS[part], SECTIONS.get((part, section), ''), head or '', str(rel)])
        rows.append((s, placed))
    root.mkdir(parents=True, exist_ok=True)
    with open(root / '00-actd-map.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['CTD section', 'Document', 'ACTD part', 'ACTD section', 'ACTD heading', 'File'])
        w.writerows(mapping)
    (root / '00-navigator.html').write_text(_navigator(root_name + ' — ACTD', rows,
                                            'ACTD: the CTD content in four parts (ASEAN Common Technical Dossier, Organization of the Dossier, Rev. 1). '
                                            'Check against the ASEAN text and the member state\'s guidance before filing.'), encoding='utf-8')
    return {'path': str(root), 'files': sorted(written) + ['00-actd-map.csv', '00-navigator.html'], 'missing': missing}
