"""Writer 1 — CTD One Submission package (soft copy) per NP.CAPP.065 v5.

EDA prescribes the numbering and «searchable PDF» (NP.CAPP.065 general note 4)
but no folder/file naming for the soft copy, so the layout below is an
ASSUMPTION, kept Windows-safe:
  <root>/Module N/<NN> <section> <short title>/<section> <title>.pdf
  3.2.S per API manufacturer: Module 3/3.2.S <substance> - <manufacturer>/…
  1.1.7: one sub-folder per variation (named by the variation type), date order
Plus 00-navigator.html (bilingual, every item with status and reason) and
00-checklist.csv. Paths are kept ≤ 180 characters (same budget as eCTD).
"""
import csv, html, os, re, shutil
from pathlib import Path
from .ectd32 import WriterError

MAX_PATH = 180
_BAD = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean(s, n=48):
    s = _BAD.sub(' ', s or '').replace('—', '-').replace('–', '-')
    s = re.sub(r'\s+', ' ', s).strip().rstrip('.')
    return s[:n].rstrip(' -.') or 'x'


def _sec_key(sec):
    return [int(x) if x.isdigit() else x for x in re.split(r'[.\s–-]+', sec)]


def write(out_dir, root_name, slots, files, lang_note=None, dry_run=False):
    """slots: resolver output (all, incl. NR/NA). files: {slot_id: [{file, title?, variation?, date?}]}.
    Returns {path, files, missing}."""
    root = Path(out_dir) / clean(root_name, 60)
    plan = {}
    if root.exists() and not dry_run:
        raise WriterError(f'{root} exists — an export is never overwritten')
    rows, written, missing = [], [], []
    order = {}
    for s in slots:
        m = s.module
        order.setdefault(m, 0)
        sec = s.ctd.split(' (')[0]
        if not s.active:
            rows.append((s, []))
            continue
        order[m] += 1
        base = Path(f'Module {m}')
        if s.item and m == 3:
            base = base / clean(f"3.2.S {s.item['name']} - {s.item['manufacturer']}", 60)
        folder = base / clean(f'{order[m]:02d} {sec} {s.title["en"]}', 44)
        got = files.get(s.slot_id, [])
        if not got:
            missing.append(s.slot_id) if s.level == 'R' else None
        placed = []
        for i, f in enumerate(sorted(got, key=lambda f: f.get('date', ''))):
            sub = folder
            if f.get('variation'):
                sub = folder / clean(f"{f.get('date', '')} {f['variation']}", 56)
            title = f.get('title') or s.title['en']
            suffix = (f'-{i + 1}' if len(got) > 1 and not f.get('variation') else '') + '.pdf'
            budget = min(56, MAX_PATH - len(f'{root.name}/{sub}/') - len(suffix))
            if budget < 12:
                raise WriterError(f'path budget exhausted under {sub}')
            name = clean(f'{sec} {title}', budget) + suffix
            rel = sub / name
            if len(f'{root.name}/{rel}') > MAX_PATH:
                raise WriterError(f'path > {MAX_PATH}: {rel}')
            plan.setdefault(s.slot_id, []).append(str(rel))
            if dry_run:
                placed.append(str(rel))
                continue
            if not Path(f['file']).is_file():
                raise WriterError(f'missing file {f["file"]}')
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f['file'], root / rel)
            placed.append(str(rel))
            written.append(str(rel))
        rows.append((s, placed))

    if dry_run:
        return {'root': root.name, 'plan': plan, 'missing': missing}
    root.mkdir(parents=True, exist_ok=True)
    with open(root / '00-checklist.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['ID', 'Section', 'Document', 'المستند', 'API', 'Level', 'Status', 'Files', 'Reason'])
        for s, placed in rows:
            w.writerow([s.req_id, s.ctd, s.title['en'], s.title['ar'],
                        f"{s.item['name']} / {s.item['manufacturer']}" if s.item else '',
                        s.level, _status(s, placed), ' | '.join(placed), s.reasons[-1]['en']])
    (root / '00-navigator.html').write_text(_navigator(root_name, rows, lang_note), encoding='utf-8')
    return {'path': str(root), 'files': sorted(written) + ['00-checklist.csv', '00-navigator.html'],
            'missing': missing}


def _status(s, placed):
    if s.level in ('NR', 'NA'):
        return {'NR': 'Not required', 'NA': 'Not applicable'}[s.level]
    return 'Provided' if placed else ('Missing' if s.level == 'R' else 'Optional - not provided')


_AR = {'Provided': 'مقدَّم', 'Missing': 'ناقص', 'Not required': 'غير مطلوب', 'Not applicable': 'لا ينطبق',
       'Optional - not provided': 'اختياري - غير مقدَّم'}


def _navigator(title, rows, note):
    e = html.escape
    trs = []
    for s, placed in rows:
        st = _status(s, placed)
        links = '<br>'.join(f'<a href="{e(p)}">{e(os.path.basename(p))}</a>' for p in placed)
        api = f"<div class=api>{e(s.item['name'])} · {e(s.item['manufacturer'])} · {e(s.item['option'])}</div>" if s.item else ''
        reason = '' if st == 'Provided' else f'<div class=why><span class=en>{e(s.reasons[-1]["en"])}</span><span class=ar>{e(s.reasons[-1].get("ar", ""))}</span></div>'
        trs.append(f'<tr class="st-{st.split()[0].lower()}"><td><bdi>{e(s.ctd)}</bdi></td>'
                   f'<td><span class=en>{e(s.title["en"])}</span><span class=ar>{e(s.title["ar"])}</span>{api}{reason}</td>'
                   f'<td><bdi>{e(s.level)}</bdi></td><td><span class=en>{e(st)}</span><span class=ar>{_AR[st]}</span></td><td>{links}</td></tr>')
    n = {k: sum(1 for s, p in rows if _status(s, p) == k) for k in _AR}
    return f'''<!doctype html>
<html lang="en" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} - CTD navigator</title>
<style>
:root{{--bg:#fff;--fg:#1b2430;--mut:#5b6675;--line:#e3e7ee;--ok:#1a7f4b;--bad:#b42318;--na:#8a94a3}}
@media (prefers-color-scheme:dark){{:root{{--bg:#11161d;--fg:#e8edf3;--mut:#9aa6b5;--line:#263040;--ok:#4cc38a;--bad:#ff7a6e;--na:#6c7889}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,"Segoe UI","Noto Sans Arabic",Tahoma,sans-serif}}
header{{padding:16px;border-bottom:1px solid var(--line);display:flex;gap:12px;flex-wrap:wrap;align-items:center}}
h1{{font-size:18px;margin:0;flex:1}} .note{{color:var(--mut);font-size:12px;padding:8px 16px}}
button{{font:inherit;padding:6px 12px;border:1px solid var(--line);background:transparent;color:inherit;border-radius:6px;cursor:pointer}}
.wrap{{overflow-x:auto;padding:0 16px 24px}} table{{border-collapse:collapse;width:100%;min-width:640px}}
th,td{{text-align:start;vertical-align:top;padding:8px;border-bottom:1px solid var(--line)}} th{{color:var(--mut);font-weight:600}}
.api,.why{{color:var(--mut);font-size:12px}} .st-provided td:nth-child(4){{color:var(--ok)}} .st-missing td:nth-child(4){{color:var(--bad);font-weight:600}}
.st-not td{{color:var(--na)}} a{{color:inherit}}
html[lang=en] .ar,html[lang=ar] .en{{display:none}}
</style></head><body>
<header><h1>{e(title)} <span class=en>- CTD One Submission</span><span class=ar>- ملف CTD</span></h1>
<span><span class=en>Provided</span><span class=ar>مقدَّم</span> {n["Provided"]} · <span class=en>Missing</span><span class=ar>ناقص</span> {n["Missing"]} · NR {n["Not required"]} · NA {n["Not applicable"]}</span>
<button onclick="var h=document.documentElement,a=h.lang==='en';h.lang=a?'ar':'en';h.dir=a?'rtl':'ltr'">EN / عربي</button></header>
<div class=note><span class=en>{e(note or "Numbering per NP.CAPP.065 v5. Conforms to EDA guidance + ICH; folder naming is the tool's convention (EDA publishes none).")}</span><span class=ar>الترقيم حسب NP.CAPP.065 الإصدار 5. مطابق لإرشادات الهيئة و ICH؛ تسمية المجلدات من الأداة (الهيئة لم تنشر تسمية).</span></div>
<div class=wrap><table><thead><tr><th>CTD</th><th><span class=en>Document</span><span class=ar>المستند</span></th><th><span class=en>Level</span><span class=ar>المستوى</span></th><th><span class=en>Status</span><span class=ar>الحالة</span></th><th><span class=en>Files</span><span class=ar>الملفات</span></th></tr></thead>
<tbody>{"".join(trs)}</tbody></table></div></body></html>
'''
