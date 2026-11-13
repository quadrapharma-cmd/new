"""Documents' places and attributes from a sheet (updates list, item 47): one row per document — its file name, its item (the item
id or its CTD number), its title and attributes (leaflet type, language, study, document type, EU country). The program first says
what it would do with every row (place a file from the unplaced box, move a document, change its title or attributes, or why a row
cannot be done), and does it only when asked. The sheet can be downloaded first, filled with the dossier's own documents."""
import csv, io

COLUMNS = ['file', 'item', 'title', 'pi_type', 'lang', 'study', 'doc_type', 'eu_country']
ATTRS = ('pi_type', 'lang', 'study', 'doc_type', 'eu_country')


def template(st, did):
    """The sheet with the dossier's documents in it (placed and unplaced), as CSV text."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLUMNS)
    for d in st.documents(did):
        if d['meta'].get('external'):
            continue
        w.writerow([d['filename'], d['slot_id'] or '', d['title'] or ''] + [d['meta'].get(k, '') for k in ATTRS])
    return buf.getvalue()


def parse(name, data):
    """Rows (dicts by the COLUMNS) of a CSV/TSV or an Excel sheet; the header row names the columns, in any order."""
    low = (name or '').lower()
    if low.endswith(('.xlsx', '.xlsm')):
        try:
            import openpyxl
            ws = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True).active
            table = [[('' if c is None else str(c)).strip() for c in row] for row in ws.iter_rows(values_only=True)]
        except ImportError:                              # the browser edition: the engine's own reader, «a | b | c» lines
            from .officefiles import xlsx_text
            table = [[x.strip() for x in ln.split(' | ')] for ln in xlsx_text(data).splitlines()]
    else:
        text = data.decode('utf-8-sig', 'replace')
        table = list(csv.reader(io.StringIO(text), delimiter='\t' if low.endswith('.tsv') or ('\t' in text.split('\n', 1)[0] and ',' not in text.split('\n', 1)[0]) else ','))
    table = [r for r in table if any(c.strip() for c in r)]
    if not table:
        return []
    head = [h.strip().lower().replace(' ', '_') for h in table[0]]
    return [{h: (r[i].strip() if i < len(r) else '') for i, h in enumerate(head) if h in COLUMNS} for r in table[1:]]


def _slot_of(item, slots):
    if item in slots:
        return slots[item], None
    hits = [s for s in slots.values() if s.ctd.split(' (')[0] == item]
    if len(hits) == 1:
        return hits[0], None
    if len(hits) > 1:
        return None, f'{len(hits)} items are {item}: write the item id ({", ".join(s.slot_id for s in hits[:4])})'
    return None, f'no item {item} in this dossier'


def plan(st, did, rows):
    """What each row would do: [{row, file, action: place|move|update|none|error, slot_id, doc_id, changes, why}]."""
    slots = {s.slot_id: s for s in st.slots(did) if s.active}
    docs = [d for d in st.documents(did) if not d['meta'].get('external')]
    out = []
    for i, r in enumerate(rows, 2):
        f = r.get('file', '')
        cands = [d for d in docs if d['filename'] == f] or [d for d in docs if d['filename'].lower() == f.lower()]
        if not f or not cands:
            out.append({'row': i, 'file': f, 'action': 'error', 'why': 'no document with this file name in the dossier'})
            continue
        if len(cands) > 1:
            cands = [d for d in cands if d['slot_id'] == r.get('item')] or cands
        d = cands[0]
        slot, why = _slot_of(r.get('item') or d['slot_id'] or '', slots) if (r.get('item') or d['slot_id']) else (None, 'name its item')
        if not slot:
            out.append({'row': i, 'file': f, 'action': 'error', 'why': why})
            continue
        attrs = {k: r[k] for k in ATTRS if r.get(k) and r[k] != d['meta'].get(k)}
        try:
            st.check_item_meta(did, slot.slot_id, {**{k: v for k, v in d['meta'].items() if k in ATTRS}, **attrs})
        except Exception as e:                           # the item's own required attributes (a leaflet's type and language…)
            out.append({'row': i, 'file': f, 'action': 'error', 'why': getattr(e, 'en', str(e))})
            continue
        changes = dict(attrs, **({'title': r['title']} if r.get('title') and r['title'] != d['title'] else {}))
        action = 'place' if d['slot_id'] is None else 'move' if d['slot_id'] != slot.slot_id else ('update' if changes else 'none')
        out.append({'row': i, 'file': f, 'action': action, 'slot_id': slot.slot_id, 'ctd': slot.ctd, 'doc_id': d['id'], 'changes': changes})
    return out


def apply(st, did, steps):
    """Do what the plan says (errors and «none» are left as they are): → [{row, done, doc_id}]."""
    done = []
    for p in steps:
        if p['action'] in ('error', 'none'):
            continue
        meta = {k: v for k, v in p['changes'].items() if k in ATTRS}
        if p['action'] in ('place', 'move'):
            new = st.move_document(did, p['doc_id'], p['slot_id'], meta)
            if p['changes'].get('title'):
                st.set_document_details(did, new['id'], None, p['changes']['title'])
            done.append({'row': p['row'], 'done': p['action'], 'doc_id': new['id']})
        else:
            st.set_document_details(did, p['doc_id'], meta, p['changes'].get('title'))
            done.append({'row': p['row'], 'done': 'update', 'doc_id': p['doc_id']})
    return done
