"""Bilingual HTML validation report (kept OUTSIDE the submission: EG-BP-E21)."""
import html, time

AR = {'pass': 'ناجح', 'fail': 'فشل', 'warning': 'تحذير', 'not_run': 'لم يُشغَّل'}


EG_NOTE = ('Provisional EG profiles — reports say «conforms to EDA drafts + ICH», never «EDA-valid».',
           'ملفات التعريف المصرية مؤقتة — التقرير يقول «مطابق لمسودات الهيئة و ICH» وليس «معتمد من الهيئة».')
EU_NOTE = ('EU Module 1 v3.1.1 (the EMA\'s DTD) and the EU eCTD validation criteria v8.2 — checked here; this is not an EMA-accepted '
           'validation tool: run one before submission.',
           'موديول ١ الأوروبي 3.1.1 (الـ DTD بتاع الوكالة) ومعايير التحقق الأوروبية 8.2 — اتفحصوا هنا؛ ده مش فاحص معتمد من الوكالة: شغّل واحد معتمد قبل التقديم.')


def render(title, reports, note=EG_NOTE):
    e = html.escape
    secs = []
    for name, r in reports.items():
        rows = ''.join(
            f"<tr class='{x['status']}'><td><bdi>{e(x['rule'])}</bdi></td><td>{e(x['status'])} · {AR[x['status']]}</td>"
            f"<td>{e(x['text'])}<div class='m'>{e(x.get('source') or x.get('provenance') or '')}</div>"
            f"{''.join(f'<div class=f>• {e(str(f))}</div>' for f in x['failures'][:10])}"
            f"{'<div class=m>' + e(x['reason']) + '</div>' if x.get('reason') else ''}</td></tr>"
            for x in sorted(r['results'], key=lambda x: ['fail', 'warning', 'pass', 'not_run'].index(x['status'])))
        c = r['counts']
        secs.append(f"<h2>{e(name)}</h2><p class='{'ok' if r['ok'] else 'bad'}'><b>{e(r['label'])}</b><br>"
                    f"pass {c['pass']} · fail {c['fail']} · warning {c['warning']} · not run {c['not_run']} · coverage {e(r['coverage'])}</p>"
                    f"<div class=w><table><thead><tr><th>Rule</th><th>Status</th><th>Rule text / evidence</th></tr></thead><tbody>{rows}</tbody></table></div>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} - validation</title><style>
:root{{--bg:#fff;--fg:#14202e;--m:#5b6b7c;--l:#e1e6ec;--ok:#15803d;--bad:#c62828;--w:#b45309}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0d141c;--fg:#e6edf3;--m:#93a3b5;--l:#253343;--ok:#4ade80;--bad:#f87171;--w:#f5a64a}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,"Segoe UI",Tahoma,sans-serif}}
.w{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;min-width:560px}} td,th{{text-align:start;padding:6px 8px;border-bottom:1px solid var(--l);vertical-align:top}}
.m{{color:var(--m);font-size:12px}} .f{{font-size:12.5px}} .ok{{color:var(--ok)}} .bad{{color:var(--bad)}}
tr.fail td:nth-child(2){{color:var(--bad);font-weight:600}} tr.warning td:nth-child(2){{color:var(--w)}} tr.not_run td{{color:var(--m)}}
</style></head><body><h1>{e(title)}</h1><p class=m>{time.strftime('%Y-%m-%d %H:%M')} · {e(note[0])}
 / {e(note[1])}</p>{''.join(secs)}</body></html>"""
