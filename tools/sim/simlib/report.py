"""The daily report: per action attempted / ok / failed / not built / limited / skipped, latency p50/p95, every failure with a
reproduction, database growth, slow queries — written as docs/sim/report-<date>[-<tag>].md and .json."""
import collections, datetime, json, os, statistics

from . import catalog

TABLES_SQL = "select relname, n_live_tup from pg_stat_user_tables where schemaname='public' order by relname"


def db_snapshot(db):
    db.q('analyze')
    rows = {r[0]: int(r[1]) for r in db.q(TABLES_SQL)}
    exact = {}
    for t in ('profiles', 'posts', 'comments', 'reactions', 'messages', 'connections', 'notifications', 'companies', 'deals', 'deal_events', 'jobs',
              'job_applications', 'groups', 'group_members', 'products', 'enquiries', 'payment_orders', 'course_enrollments', 'company_listings'):
        exact[t] = int(db.val('select count(*) from public.%s' % t))
    size = int(db.val('select pg_database_size(current_database())'))
    objs = int(db.val('select count(*) from storage.objects'))
    return {'at': datetime.datetime.now().isoformat(timespec='seconds'), 'tables': rows, 'exact': exact, 'db_bytes': size, 'storage_objects': objs}


def pct(v, p):
    if not v: return None
    v = sorted(v); k = (len(v) - 1) * p / 100.0; f = int(k); c = min(f + 1, len(v) - 1)
    return round(v[f] + (v[c] - v[f]) * (k - f), 1)


def load(path):
    out = []
    with open(path) as f:
        for l in f:
            try: out.append(json.loads(l))
            except ValueError: pass
    return out


def signature(r):
    d = r.get('detail', '')
    for cut in (' (got', ': the app answered'):
        if cut in d: d = d.split(cut)[0] + cut.replace(' (got', '').replace(': the app answered', ': app error')
    return '%s | %s' % (r['action'], d[:160])


def summarize(recs):
    by = collections.OrderedDict()
    for n in sorted(catalog.ACTIONS): by[n] = {'attempted': 0, 'ok': 0, 'fail': 0, 'not_built': 0, 'limited': 0, 'skip': 0, 'sim_error': 0, 'ms': [], 'req_ms': []}
    for r in recs:
        s = by.setdefault(r['action'], {'attempted': 0, 'ok': 0, 'fail': 0, 'not_built': 0, 'limited': 0, 'skip': 0, 'sim_error': 0, 'ms': [], 'req_ms': []})
        s[r['status']] = s.get(r['status'], 0) + 1
        if r['status'] in ('ok', 'fail', 'sim_error'): s['attempted'] += 1
        if r['status'] in ('ok', 'fail'): s['ms'].append(r['ms']); s['req_ms'].extend(r.get('req_ms') or [])
    fails = collections.OrderedDict()
    for r in recs:
        if r['status'] not in ('fail', 'sim_error'): continue
        k = signature(r) if r['status'] == 'fail' else 'SIM | ' + signature(r)
        f = fails.setdefault(k, {'count': 0, 'action': r['action'], 'status': r['status'], 'journeys': r.get('journeys'), 'path': r.get('path'), 'first': r})
        f['count'] += 1
    return by, fails


def write(recs, meta, before, after, out_md, out_json, slow=None, ui=None):
    by, fails = summarize(recs)
    tot = collections.Counter(r['status'] for r in recs)
    js = {'meta': meta, 'totals': dict(tot), 'actions': {}, 'failures': [], 'db_before': before, 'db_after': after, 'slow_queries': slow, 'ui': ui}
    for n, s in by.items():
        a = catalog.ACTIONS.get(n)
        js['actions'][n] = {k: s[k] for k in ('attempted', 'ok', 'fail', 'not_built', 'limited', 'skip', 'sim_error')}
        js['actions'][n].update(p50_ms=pct(s['ms'], 50), p95_ms=pct(s['ms'], 95), req_p50_ms=pct(s['req_ms'], 50), req_p95_ms=pct(s['req_ms'], 95),
                                area=a.area if a else '', path=a.path if a else '', journeys=a.journeys if a else [])
    for k, f in fails.items():
        r = f['first']
        js['failures'].append({'signature': k, 'count': f['count'], 'status': f['status'], 'action': f['action'], 'journeys': f['journeys'], 'path': f['path'],
                               'detail': r.get('detail'), 'actor': r.get('actor'), 'target': r.get('target'), 'repro': r.get('repro')})
    with open(out_json, 'w') as fh: json.dump(js, fh, ensure_ascii=False, indent=1, default=str)

    L = []
    L.append('# Drugbox activity simulator — report %s%s' % (meta['date'], (' (' + meta['tag'] + ')') if meta.get('tag') else ''))
    L.append('')
    L.append('Synthetic accounts only (`@sim.drugbox.test`) on the **%s** stack `%s` — never production. Seed `%s`, %d accounts + 1 sim admin, '
             'speed %s (a %s day in %.0f s of wall time), API concurrency %d, at most %s requests/s, head `%s`.' %
             (meta['target_kind'], meta['target'], meta['seed'], meta['accounts'], meta['speed'], 'compressed' if meta['speed'] else 'real-time', meta['wall_s'], meta['concurrency'], meta['rps'], meta.get('head', '?')))
    L.append('')
    att = sum(s['attempted'] for s in by.values()); ok = tot.get('ok', 0)
    L.append('**Totals:** %d events · %d attempted · **%d ok** · **%d failed** · %d simulator errors · %d not built (known gaps) · %d hit an app flood limit · %d skipped (nothing to do).' %
             (len(recs), att, ok, tot.get('fail', 0), tot.get('sim_error', 0), tot.get('not_built', 0), tot.get('limited', 0), tot.get('skip', 0)))
    allms = [r['ms'] for r in recs if r['status'] in ('ok', 'fail')]
    netms = [r.get('net_ms', r['ms']) for r in recs if r['status'] in ('ok', 'fail')]
    allreq = [m for r in recs if r['status'] in ('ok', 'fail') for m in (r.get('req_ms') or [])]
    L.append('Latency: an action (all its requests + database checks) p50 %s ms / p95 %s ms — of which the simulator\'s own rate limit (--rps) is excluded: p50 %s ms / p95 %s ms; '
             'a single request p50 %s ms / p95 %s ms (%d requests).' % (pct(allms, 50), pct(allms, 95), pct(netms, 50), pct(netms, 95), pct(allreq, 50), pct(allreq, 95), len(allreq)))
    if meta.get('lag_p95') is not None: L.append('Schedule lag (how late actions started vs. their planned time): p50 %s s, p95 %s s, max %s s.' % (meta['lag_p50'], meta['lag_p95'], meta['lag_max']))
    L.append('')
    L.append('## Failures (%d distinct, %d events)' % (len(fails), sum(f['count'] for f in fails.values())))
    L.append('')
    if not fails: L.append('None.')
    for i, (k, f) in enumerate(fails.items(), 1):
        r = f['first']; rp = r.get('repro') or {}
        L.append('### %d. `%s` × %d%s' % (i, f['action'], f['count'], ' — SIMULATOR ERROR' if f['status'] == 'sim_error' else ''))
        L.append('- journeys: %s · path: %s' % (', '.join(f['journeys'] or []), f['path']))
        L.append('- what: %s' % (r.get('detail') or '').replace('\n', ' ')[:600])
        L.append('- reproduce: as `%s` (password in the registry) — target `%s`' % (r.get('actor'), r.get('target')))
        for q in (rp.get('requests') or [])[-4:]: L.append('  - `%s`' % q.replace('`', "'")[:500])
        for c in (rp.get('checks') or [])[-2:]: L.append('  - check: %s — `%s` → `%s`' % (c.get('check'), c.get('sql', '')[:300].replace('`', "'"), c.get('got')))
        L.append('')
    L.append('## Per action')
    L.append('')
    L.append('| action | area | path | attempted | ok | failed | not built | limited | skipped | p50 ms | p95 ms | req p95 ms | journeys |')
    L.append('|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|')
    for n, s in by.items():
        a = js['actions'][n]
        if not any(s[k] for k in ('attempted', 'not_built', 'limited', 'skip')): continue
        L.append('| `%s` | %s | %s | %d | %d | %d | %d | %d | %d | %s | %s | %s | %s |' % (n, a['area'], a['path'], s['attempted'], s['ok'], s['fail'] + s['sim_error'], s['not_built'], s['limited'], s['skip'],
                                                                       a['p50_ms'] or '', a['p95_ms'] or '', a['req_p95_ms'] or '', ' '.join(j.replace('J-', '') for j in a['journeys'])))
    L.append('')
    covered = sorted({j for n, s in by.items() if s['ok'] for j in js['actions'][n]['journeys']} | {j for r in ((ui or {}).get('records') or []) if r['status'] == 'ok' for j in r.get('journeys', [])}
                     | ({'J-SOCIAL-01'} if (meta.get('bootstrap') or {}).get('signed_up') else set()))
    nb = sorted({j for n, s in by.items() if s['not_built'] and not s['ok'] for j in js['actions'][n]['journeys']} - set(covered))
    L.append('Journeys exercised with a verified result (API, UI driver, sign-up): %d of 150 (%s).' % (len(covered), ', '.join(j.replace('J-', '') for j in covered)))
    L.append('Journeys whose feature has no live backend yet (not built): %s.' % (', '.join(j.replace('J-', '') for j in nb) or 'none'))
    L.append('')
    if ui:
        L.append('## UI driver (Playwright, real clicks)')
        L.append('')
        nb = sum(1 for r in ui.get('records', []) if r['status'] == 'not_built')
        L.append('%d actions in %s (%.0f s, at most 4 browsers): %d ok, %d failed, %d known gaps, %d skipped; JavaScript errors: %d.' % (ui['total'], ', '.join(ui['configs']), ui.get('wall_s', 0), ui['ok'], ui['fail'], nb, ui['skip'], ui['js_errors']))
        L.append('')
        L.append('| UI action | ok | failed | known gap | skipped | p50 ms |'); L.append('|---|---:|---:|---:|---:|---:|')
        for k, v in sorted(ui.get('by_action', {}).items()): L.append('| `%s` | %d | %d | %d | %d | %s |' % (k, v['ok'], v['fail'], v.get('not_built', 0), v['skip'], v.get('p50_ms')))
        L.append('')
        for f in ui.get('failures', [])[:30]: L.append('- `%s` %s %s: %s' % (f['action'], f['config'], f['actor'], f['detail'][:300]))
        L.append('')
    L.append('## Database growth')
    L.append('')
    L.append('| table | before | after | Δ |')
    L.append('|---|---:|---:|---:|')
    for t in sorted(after['exact']):
        b = before['exact'].get(t, 0); a2 = after['exact'][t]; L.append('| %s | %d | %d | %+d |' % (t, b, a2, a2 - b))
    L.append('| storage objects | %d | %d | %+d |' % (before['storage_objects'], after['storage_objects'], after['storage_objects'] - before['storage_objects']))
    L.append('| database size | %.1f MB | %.1f MB | %+.1f MB |' % (before['db_bytes'] / 1e6, after['db_bytes'] / 1e6, (after['db_bytes'] - before['db_bytes']) / 1e6))
    L.append('')
    if slow:
        L.append('## Hot queries at this size (tools/scale/timings.py, with row-level security, as a heavy sim account)')
        L.append('')
        L.append('```'); L.append(slow.get('text', '').strip()[:6000]); L.append('```')
        L.append('')
    if meta.get('db_slow'):
        L.append('Simulator-side database checks slower than 0.5 s: %d (first: %s).' % (len(meta['db_slow']), meta['db_slow'][:3]))
    with open(out_md, 'w') as fh: fh.write('\n'.join(L) + '\n')
    return js
