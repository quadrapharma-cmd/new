"""Stage «build» — what the dossier lacks and the company itself issues, written; after the corrections, before the eCTD.

eBOX's full program makes this dossier's own copy (ebox.make, in build/store, without anything this stage wrote) and its matrix
says which required items are still open, and who issues each one's document (api.py `/missing`). The company's own — a letter, a
declaration, an undertaking, a commitment, a certificate, a table, a section or a summary — are written here. A document of
another party (a certificate, a licence, the substance manufacturer's analysis) is never written: it stays in that party's
request letter at the eCTD stage, as before. A study report or a batch record is never written either: its template says so
(generate/draft.py, «none»), and it stays the company's to give.

Who writes: Claude, in the desk's work session (desk/WORKER.md), from the dossier's own pages — never a fact that is not in
them. The program gives Claude each item's template (eBOX's «make it for me» templates) or its generator (generate/letters.py),
with what the dossier already knows and the texts of its documents; Claude writes the sections (write) or the generator's data
(generate), or says why the item cannot be written from these pages (cannot) — then it is the company's to give. A document the
company must sign is written ready to sign, and named in the needs. finish writes built.json: the eCTD stage puts every built
document in the three outputs (ectd.py: Module 1 at its EG element, Modules 2–5 at their headings) and in eBOX's copy
(ebox.documents), so the review counts it as there.

  python -m dossier_engine.combined.build <work> list                  the open items the company issues, and the state of each
  python -m dossier_engine.combined.build <work> docs                  the dossier's documents: CTD heading, title, pages
  python -m dossier_engine.combined.build <work> brief <item>          the item's template or generator, its data, the documents' texts
  python -m dossier_engine.combined.build <work> pages <ranges>        the dossier's pages as read (e.g. 12-15,40)
  python -m dossier_engine.combined.build <work> write <item> @<answers.json>       a template's sections (the brief says the form)
  python -m dossier_engine.combined.build <work> generate <item> @<data.json>       a generator's data
  python -m dossier_engine.combined.build <work> cannot <item> '<why, formal Arabic>'
  python -m dossier_engine.combined.build <work> finish                built.json, for the eCTD stage
"""
import datetime
import json
import re
import shutil
import sys
from pathlib import Path

from .common import Work, say

# written elsewhere, or not a document of this dossier
LATER = {'M1-43': 'يُكتب خطاب التغطية في مرحلة تسلسل eCTD.', 'M1-44': 'يُكتب جدول التتبع في مرحلة تسلسل eCTD.',
         'M1-09': 'معلومات المستحضر تكتبها مهمة Claude الثالثة (معلومات المستحضر)، لا هذه المرحلة.',
         'M5-01': 'جدول محتويات Module 5: يقوم مقامه ملف XML في تسلسل eCTD.'}
NOT_WRITTEN = 'تقرير دراسة أو سجل تشغيلة: لا يُكتب من صفحات الملف، ويقدّمه صاحبه.'
STATES = ('to do', 'built', 'cannot', 'later')


def _client(root):
    from fastapi.testclient import TestClient
    from ..app.api import create_app
    return TestClient(create_app(root, auth_enabled=False))


def _title(t):
    return t if isinstance(t, dict) else {'en': t or '', 'ar': ''}


def _gen_kind(req):
    from ..app.api import GEN
    return next((k for k, (_fn, r) in GEN.items() if r == req), None)


def _slug(s):
    return re.sub(r'[^a-z0-9]+', '-', (s or '').lower()).strip('-')[:60] or 'document'


def run(work):
    """The open items the company issues, from eBOX's own copy of this dossier; nothing is written yet (that is Claude's)."""
    from ..generate import draft
    w = work if isinstance(work, Work) else Work(work)
    for name in ('built', 'build'):
        if (w.root / name).exists():
            shutil.rmtree(w.root / name)
    for name in ('built.json', 'build.json'):
        if (w.root / name).exists():
            (w.root / name).unlink()
    (w.root / 'built').mkdir()
    from . import ebox
    m = ebox.make(w, root=w.root / 'build' / 'store', built=False)
    st, did = m['st'], m['did']
    c = _client(m['root'])
    miss = c.get(f'/api/dossiers/{did}/missing').json()
    slots = {s.slot_id: s for s in st.slots(did)}
    items, others = [], 0
    for g in miss.get('parties') or []:
        if g['kind'] != 'company':
            others += len(g['items'])
            continue
        for i in g['items']:
            s = slots.get(i['slot_id'])
            req = i['req_id']
            entry = draft.template(req) or {}
            nodes = list(getattr(s, 'ectd', None) or []) if s else []
            kind = _gen_kind(req)
            it = {'item': i['slot_id'], 'req': req, 'ctd': i.get('ctd'), 'node': nodes[0] if nodes else (i.get('ctd') or ''),
                  'title': _title(i.get('title')), 'substance': (i.get('item') or {}).get('name') if isinstance(i.get('item'), dict) else None,
                  'why_open': i.get('why') or [], 'how_ar': i.get('how_ar'), 'template': entry.get('draft'), 'kind': entry.get('kind'),
                  'generator': kind if entry.get('draft') == 'generator' else None, 'state': 'to do', 'note': ''}
            if req in LATER:
                it.update(state='later', note=LATER[req])
            elif entry.get('draft') == 'none' or not entry:
                it.update(state='cannot', by='program', note=NOT_WRITTEN if entry.get('draft') == 'none' else 'لا قالب لهذا البند في البرنامج.')
            elif entry.get('draft') == 'generator' and not kind:
                it.update(state='cannot', by='program', note='لا مولّد لهذا البند في البرنامج.')
            items.append(it)
    rec = {'at': datetime.datetime.now().isoformat(timespec='seconds'), 'country': m['country'], 'pack': m['meta']['id'],
           'dossier': did, 'store': str(m['root']), 'items': items, 'others': others, 'finished': False}
    w.save('build.json', rec)
    todo = sum(1 for x in items if x['state'] == 'to do')
    say(f'البنود الناقصة التي تُصدرها الشركة: {len(items)} · تُكتب من صفحات الملف: {todo} · '
        f'تقرير أو سجل يقدّمه صاحبه: {sum(1 for x in items if x["state"] == "cannot")} · '
        f'تُكتب في مرحلة أخرى: {sum(1 for x in items if x["state"] == "later")} · بنود جهات أخرى (خطابات الطلب): {others}')
    return rec


# ------------------------------------------------------------------ Claude's part
class Refused(Exception):
    pass


def _rec(w):
    rec = w.load('build.json')
    if not rec:
        raise Refused('the build stage has not run here: `python3 -m dossier_engine.combined build <work>` first.')
    return rec


def _item(rec, item):
    """An item by its id as `list` prints it, by its requirement (S-01) where only one item has it, or by its number in the list (#3)."""
    items = rec['items']
    it = next((x for x in items if x['item'] == item), None)
    if not it and item.startswith('#') and item[1:].isdigit() and 1 <= int(item[1:]) <= len(items):
        it = items[int(item[1:]) - 1]
    if not it:
        same = [x for x in items if x['req'] == item]
        if len(same) > 1:
            raise Refused(f'«{item}» is {len(same)} items (one a substance): name one as `list` prints it, or by its number (#n).')
        it = same[0] if same else None
    if not it:
        raise Refused(f'no open item «{item}»: `list` names them.')
    return it


def _open(rec):
    from ..app.store import Store
    st = Store(Path(rec['store']))
    slot = {s.slot_id: s for s in st.slots(rec['dossier'])}
    return st, slot


def cmd_list(w):
    rec = _rec(w)
    lines = []
    for n, x in enumerate(rec['items'], 1):
        how = 'generate' if x.get('generator') else 'write' if x['state'] == 'to do' else ''
        lines.append(f"#{n:<3} {x['item']:22} {x['state']:7} {how:9} {x['node'] or x['ctd'] or '':12} {x['title'].get('en', '')[:70]}"
                     + (f"  — {x['note']}" if x['note'] else ''))
    return '\n'.join(lines) + f"\n\n{sum(1 for x in rec['items'] if x['state'] == 'to do')} to do. Items of other parties (request letters): {rec['others']}."


def cmd_docs(w):
    plan = w.load('plan.json') or {}
    rows = []
    for d in plan.get('docs') or []:
        p = d.get('pages') or []
        rows.append(f"{d['ctd']:14} pages {p[0] if p else ''}-{p[-1] if p else ''}  {d['title'][:90]}")
    return '\n'.join(rows)


def cmd_pages(w, spec):
    text = w.pages_text('read/text.txt')
    ocr = w.pages_text('read/ocr.txt')
    ocr = ocr if len(ocr) == len(text) else text
    out = []
    for part in spec.split(','):
        a, _, b = part.strip().partition('-')
        if not a.isdigit() or (b and not b.isdigit()):
            raise Refused(f'pages: «{part}» is not a page or a range (12-15).')
        for p in range(int(a), int(b or a) + 1):
            if 1 <= p <= len(text):
                t = text[p - 1] if len(text[p - 1].strip()) >= 30 else ocr[p - 1]
                out.append(f'===== page {p}\n{t.strip()}')
    return '\n\n'.join(out) or 'no such page.'


def cmd_brief(w, item):
    from ..generate import draft, letters
    rec = _rec(w)
    it = _item(rec, item)
    head = (f"ITEM {it['item']} — {it['req']} {it['title'].get('en', '')} / {it['title'].get('ar', '')} (CTD {it['ctd']}, eCTD node "
            f"{it['node']}); why it is open: {'; '.join(map(str, it['why_open'])) or '-'}; how the authority wants it: {it.get('how_ar') or '-'}\n")
    if it['state'] != 'to do':
        return head + f"\nState: {it['state']} — {it['note']}\n(write, generate or cannot it again to change it.)"
    st, slots = _open(rec)
    slot = slots.get(it['item'])
    if not slot:
        raise Refused('the item is not in the copy of the dossier any more: run the build stage again.')
    rules = ('\nHOW TO ANSWER\n- Read the pages before you write: `docs` lists the dossier\'s documents with their pages, `pages 12-15` reads them.\n'
             '- Only facts found in these pages or in the data below. Never invent a number, a date, a name, a batch, a limit or a result.\n'
             '- If what the document needs is not in the pages: `cannot <item> \'<what is missing, formal Arabic>\'` — the company gives it.\n'
             '- The signatory: who signs is named in the pages, or the lines are left blank (____) to be signed; never a made-up name.\n')
    if it.get('generator'):
        kind = it['generator']
        schema = letters.SCHEMAS.get(kind) or {}
        pre = _client(Path(rec['store'])).get(f"/api/dossiers/{rec['dossier']}/generate/{kind}/prefill", params={'slot_id': it['item']}).json()
        return (head + f"\nGENERATOR «{kind}»: the program writes the document from the data you give.\n"
                f"FIELDS (JSON schema of the data): {json.dumps(schema.get('fields') or [], ensure_ascii=False)}\n"
                f"WHAT THE DOSSIER ALREADY KNOWS (prefill; correct it from the pages): {json.dumps(pre, ensure_ascii=False)}\n" + rules +
                f"- Answer: `generate {it['item']} @<file>` with ONE JSON object of the fields' values.")
    entry = draft.template(it['req'])
    ctx = draft.context(st, rec['dossier'], slot, with_texts=True)
    return head + rules + f"- Answer: `write {it['item']} @<file>` with the JSON object the prompt below asks for.\n\n" + draft.prompt(entry, ctx)


def _built(rec, it, pdf, docx, how, gaps=None, sign=False, notes=None):
    it.update(state='built', pdf=str(pdf), docx=str(docx) if docx else None, how=how, gaps=gaps or [], sign=sign, note=notes or '')


def cmd_write(w, item, answers):
    from ..generate import draft
    from ..generate.docx_kit import to_pdf
    rec = _rec(w)
    it = _item(rec, item)
    if it.get('generator'):
        raise Refused(f'«{item}» is written by its generator: `generate {item} @<data.json>`.')
    if it['state'] in ('later',) or it.get('template') in (None, 'none'):
        raise Refused(f'«{item}» is not written here: {it["note"]}')
    if not isinstance(answers, dict) or not isinstance(answers.get('sections'), dict) or not answers['sections']:
        raise Refused('the answer is one JSON object with "sections" (each section id of the template with its text), "gaps", "sources".')
    entry = draft.template(it['req'])
    ids = {s['id'] for s in entry.get('sections') or []}
    unknown = [k for k in answers['sections'] if k not in ids]
    if unknown:
        raise Refused(f'sections not in the template: {", ".join(unknown)} (the template\'s: {", ".join(sorted(ids))}).')
    st, slots = _open(rec)
    slot = slots[it['item']]
    filled, how, ctx = draft.compute(st, rec['dossier'], slot, answers=answers, use_ai=False)
    name = f"{it['req']}-{_slug(it['title'].get('en'))}" + (f"-{_slug(it['substance'])}" if it.get('substance') else '')
    out = w.root / 'built' / f'{name}.docx'
    draft.render(entry, filled, ctx, out)
    pdf = to_pdf(out)
    sign = entry.get('kind') in ('declaration', 'letter', 'statement', 'commitment', 'form', 'certificate') or bool(entry.get('letterhead'))
    gaps = [g for g in filled.get('gaps') or [] if g]
    _built(rec, it, pdf, out, 'written', gaps, sign, filled.get('notes'))
    w.save('build.json', rec)
    return (f"written: {pdf.name}" + (' — to be signed by the company' if sign else '') +
            (f" — gaps left in it ({len(gaps)}): " + '; '.join(str(g.get('what') if isinstance(g, dict) else g) for g in gaps[:8]) if gaps else ''))


def cmd_generate(w, item, data):
    rec = _rec(w)
    it = _item(rec, item)
    kind = it.get('generator')
    if not kind:
        raise Refused(f'«{item}» has no generator: `write {item} @<answers.json>` (its brief says the form).')
    if not isinstance(data, dict) or not data:
        raise Refused('the data is one JSON object of the generator\'s fields.')
    c = _client(Path(rec['store']))
    r = c.post(f"/api/dossiers/{rec['dossier']}/generate/{kind}", json={'data': data, 'slot_id': it['item'], 'ctx': {}})
    if r.status_code != 201:
        try:
            det = r.json().get('detail') or {}
        except ValueError:
            det = {'en': r.text[:300]}
        miss = det.get('request_data') if isinstance(det, dict) else None
        raise Refused((det.get('en') if isinstance(det, dict) else str(det)) +
                      (f' Read these from the pages, or `cannot {item} \'<what is missing>\'`: {", ".join(miss)}' if miss else ''))
    doc = r.json()
    from ..app.store import Store
    st = Store(Path(rec['store']))
    src = st.blob_path(doc['sha256'])
    name = f"{it['req']}-{kind}" + (f"-{_slug(it['substance'])}" if it.get('substance') else '')
    ext = Path(doc['filename']).suffix or '.pdf'
    dst = w.root / 'built' / f'{name}{ext}'
    shutil.copyfile(src, dst)
    if ext != '.pdf':
        raise Refused('the program could not make the PDF (LibreOffice is missing on this machine).')
    from .. app.store import SIGN_KINDS
    _built(rec, it, dst, None, 'generated', [], kind in SIGN_KINDS)
    w.save('build.json', rec)
    return f"generated: {dst.name}" + (' — to be signed by the company' if kind in SIGN_KINDS else '')


def cmd_cannot(w, item, why):
    rec = _rec(w)
    it = _item(rec, item)
    if not why or not re.search(r'[؀-ۿ]', why):
        raise Refused('say why, in formal Arabic: what is missing from the pages, and who gives it.')
    it.update(state='cannot', by='claude', note=why.strip(), pdf=None, docx=None)
    w.save('build.json', rec)
    return f'left to the company: {it["req"]}'


def cmd_finish(w):
    rec = _rec(w)
    todo = [x['item'] for x in rec['items'] if x['state'] == 'to do']
    if todo:
        raise Refused(f'still to do: {", ".join(todo)} — write, generate or cannot each.')
    built = [{'item': x['item'], 'req': x['req'], 'node': x['node'], 'ctd': x['ctd'], 'title': x['title'].get('en') or x['req'],
              'title_ar': x['title'].get('ar'), 'substance': x.get('substance'), 'pdf': x['pdf'], 'docx': x.get('docx'),
              'how': x.get('how'), 'sign': x.get('sign'), 'gaps': x.get('gaps') or []}
             for x in rec['items'] if x['state'] == 'built']
    w.save('built.json', built)
    rec['finished'] = True
    w.save('build.json', rec)
    store = Path(rec['store'])
    if store.exists():                                    # the eCTD stage makes eBOX's copy again, with what was built
        shutil.rmtree(store)
    cannot = sum(1 for x in rec['items'] if x['state'] == 'cannot')
    return f'built: {len(built)} · left to the company: {cannot} · to be signed: {sum(1 for b in built if b["sign"])}'


def summary(w):
    """For the report and the worker: what was built, what is left to the company, what must be signed, the gaps left."""
    rec = w.load('build.json') or {}
    items = rec.get('items') or []
    return {'built': [x for x in items if x['state'] == 'built'], 'cannot': [x for x in items if x['state'] == 'cannot'],
            'later': [x for x in items if x['state'] == 'later'], 'todo': [x for x in items if x['state'] == 'to do'],
            'finished': rec.get('finished', False), 'others': rec.get('others', 0)}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    w, cmd, args = Work(Path(argv[0])), argv[1], argv[2:]

    def load(raw):
        try:
            if raw == '-':
                raw = sys.stdin.read()
            elif raw.startswith('@'):
                raw = Path(raw[1:]).read_text(encoding='utf-8')
            return json.loads(raw)
        except (OSError, json.JSONDecodeError) as e:
            raise Refused(f'the input is not a JSON object that could be read ({e}).')
    try:
        if cmd == 'list':
            out = cmd_list(w)
        elif cmd == 'docs':
            out = cmd_docs(w)
        elif cmd == 'pages' and args:
            out = cmd_pages(w, args[0])
        elif cmd == 'brief' and args:
            out = cmd_brief(w, args[0])
        elif cmd == 'write' and len(args) == 2:
            out = cmd_write(w, args[0], load(args[1]))
        elif cmd == 'generate' and len(args) == 2:
            out = cmd_generate(w, args[0], load(args[1]))
        elif cmd == 'cannot' and len(args) == 2:
            out = cmd_cannot(w, args[0], args[1])
        elif cmd == 'finish':
            out = cmd_finish(w)
        else:
            print(__doc__)
            return 1
    except Refused as e:
        print('REFUSED: ' + str(e))
        return 2
    print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
