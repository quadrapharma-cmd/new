#!/usr/bin/env python3
"""Gate between the seed and the oracle: replays the SEED JSON and compares it with oracle.json.

    python3 tools/seed/verify_seed.py [--out DIR] [--seed DIR] [--oracle FILE]

Checks (all printed as counts only): document sizes and ids, referential integrity, balanced posted entries, per-year totals,
net results and per-account closing balances against the oracle, baseline snapshots of closed years, the fixed-asset
register replayed against the depreciation actually posted (by account x year), and register totals. Exit 0 = PASS.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

sys.dont_write_bytecode = True      # keep the repository free of __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import DOC_BYTES_LIMIT, SeedError, eprint, exact_cents, private_dir, to_cents  # noqa: E402

PL_FS = {'REVENUE', 'REVENUE_CONTRA', 'COGS', 'OPEX', 'NONDEDUCTIBLE'}
ISO = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class Checker:
    def __init__(self):
        self.total = 0
        self.failed = Counter()

    def ok(self, label, cond):
        self.total += 1
        if not cond:
            self.failed[label] += 1
        return bool(cond)

    @property
    def mismatches(self):
        return sum(self.failed.values())


def load_seed(seed_dir):
    docs, sizes = {}, {}
    for path in glob.glob(os.path.join(seed_dir, '*', '*.json')):
        coll = os.path.basename(os.path.dirname(path))
        doc_id = os.path.splitext(os.path.basename(path))[0]
        with open(path, 'rb') as fh:
            raw = fh.read()
        sizes[f'{coll}/{doc_id}'] = len(raw)
        docs.setdefault(coll, {})[doc_id] = json.loads(raw.decode('utf-8'))
    return docs, sizes


def cents(v):
    c = exact_cents(v)
    return 0 if c is None else c


def charge(cost_c, rate, conv, year, in_service):
    r = Decimal(str(rate))
    first = int(in_service[:4]) if in_service else year
    base = Decimal(cost_c) * r
    if conv == 'none':
        return 0
    if year < first:
        return 0
    if year == first:
        if conv == 'half_year':
            base = base / 2
        elif conv == 'day_count':
            days = (date(year, 12, 31) - date.fromisoformat(in_service)).days + 1
            base = base * min(days, 365) / 365
        elif conv == 'full_next_year':
            return 0
    return int(base.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def replay_assets(assets, years):
    """-> {year: {accum: cents}} (cap at cost less residual over the asset's life)."""
    out = defaultdict(lambda: defaultdict(int))
    for a in assets.values():
        if a['convention'] == 'none' or not a.get('accumAcct'):
            continue
        cost_c = to_cents(a['cost'])
        cap = cost_c - to_cents(a.get('residual', 0) or 0)
        total = 0
        for y in years:
            c = min(charge(cost_c, a['rate'], a['convention'], y, a['inServiceDate']), max(cap - total, 0))
            total += c
            if c:
                out[y][a['accumAcct']] += c
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--seed')
    ap.add_argument('--oracle')
    args = ap.parse_args(argv)
    out = args.out or private_dir()
    seed = args.seed or os.path.join(out, 'seed')
    oracle_path = args.oracle or os.path.join(out, 'oracle.json')
    try:
        if not os.path.isdir(seed) or not os.path.exists(oracle_path):
            raise SeedError('seed directory or oracle.json missing: run make_seed.py and make_oracle.py first')
        with open(oracle_path, encoding='utf-8') as fh:
            oracle = json.load(fh)
        c = verify(seed, oracle)
    except SeedError as e:
        eprint(f'verify_seed: {e}')
        return 2
    status = 'PASS' if c.mismatches == 0 else 'FAIL'
    print(f'verify_seed: seed vs oracle {status} (checks={c.total}, mismatches={c.mismatches})')
    if c.failed:
        print('failed check groups:', dict(sorted(c.failed.items())))
    return 0 if c.mismatches == 0 else 1


def verify(seed, oracle):
    c = Checker()
    docs, sizes = load_seed(seed)
    for k, n in sizes.items():
        c.ok('doc-size', n <= DOC_BYTES_LIMIT)
    accounts, entries = docs.get('accounts', {}), docs.get('entries', {})
    parties, documents = docs.get('parties', {}), docs.get('documents', {})
    ccs, sectors = docs.get('costCenters', {}), docs.get('sectors', {})
    openi, asm = docs.get('openItems', {}), docs.get('assumptions', {})
    meta = docs.get('meta', {})
    groups = {g['code'] for g in meta.get('groups', {}).get('groups', [])}

    # ---- ids match file names
    for code, a in accounts.items():
        c.ok('id-account', a['code'] == code)
        c.ok('account-parent', a['parent'] in groups)
        c.ok('account-contraof', (not a['contra']) or a['contraOf'] in accounts)
        c.ok('account-class', a['type'] in ('asset', 'liability', 'equity', 'revenue', 'expense', 'suspense'))
    for pid, p in parties.items():
        c.ok('id-party', p['id'] == pid)
        c.ok('party-kind', p['kind'] in ('shareholder', 'financier', 'supplier', 'employee', 'government', 'bank',
                                         'customer', 'professional', 'group', 'other'))
        c.ok('party-default-account', p.get('defaultAccount') in (None, *accounts))
    for did, d in documents.items():
        c.ok('id-document', d['id'] == did)
        c.ok('document-status', d['status'] == 'expected' and d['files'] == [])
    for i, d in {**ccs, **sectors}.items():
        c.ok('id-dimension', d['id'] == i)
    for n, d in openi.items():
        c.ok('id-openitem', str(d['n']) == n and d['status'] in ('open', 'partial', 'closed', 'inquiry'))
    for n, d in asm.items():
        c.ok('id-assumption', str(d['n']) == n and d['status'] == 'pending')

    # ---- entries
    by_year_dr, by_year_cr = Counter(), Counter()
    bal = defaultdict(lambda: defaultdict(int))        # year -> acct -> net movement
    used = set()
    nos = []
    link_back = {'a': defaultdict(set), 'o': defaultdict(set)}
    n_lines = 0
    for eid, e in entries.items():
        nos.append(e['no'])
        c.ok('entry-id', eid == f'e{e["no"]:06d}')
        c.ok('entry-posted', e['status'] == 'posted' and e['isLegacy'] and e['source'] == 'legacy' and e['version'] == 1)
        c.ok('entry-date', bool(ISO.match(e['date'])) and e['fy'] == int(e['date'][:4]))
        ls = e['lines']
        c.ok('entry-lines', len(ls) >= 2 and len({l['n'] for l in ls}) == len(ls))
        dr = sum(cents(l['dr']) for l in ls)
        cr = sum(cents(l['cr']) for l in ls)
        c.ok('entry-balanced', dr == cr)
        c.ok('header-refs', all(d in documents for d in e['docIds']) and (e['cc'] in ccs) and (e['sector'] in sectors))
        for l in ls:
            n_lines += 1
            c.ok('line-sides', (l['dr'] > 0) != (l['cr'] > 0) and l['dr'] >= 0 and l['cr'] >= 0)
            c.ok('line-decimals', exact_cents(l['dr']) is not None and exact_cents(l['cr']) is not None)
            c.ok('line-account', l['acct'] in accounts and accounts[l['acct']]['postable'])
            used.add(l['acct'])
            c.ok('line-party', l['partyId'] is None or l['partyId'] in parties)
            c.ok('line-docs', all(d in documents for d in l['docIds']))
            c.ok('line-dims-resolve', (l['cc'] is None or l['cc'] in ccs) and (l['sector'] is None or l['sector'] in sectors))
            c.ok('line-effective-dims', bool(l['docIds'] or e['docIds']) and bool(l['cc'] or e['cc']) and bool(l['sector'] or e['sector']))
            c.ok('line-legacy', isinstance(l['legacy'], dict) and 'row' in l['legacy'])
            c.ok('line-review-reason', (not l['needsReview']) or bool(l['reviewReason']))
            for k in l['links']:
                reg = openi if k['t'] == 'o' else asm
                c.ok('line-link-resolves', str(k['n']) in reg)
                link_back[k['t']][k['n']].add(e['no'])
            if l['valueDate']:
                c.ok('line-valuedate', bool(ISO.match(l['valueDate'])))
            y = e['fy']
            by_year_dr[y] += cents(l['dr'])
            by_year_cr[y] += cents(l['cr'])
            bal[y][l['acct']] += cents(l['dr']) - cents(l['cr'])
    for kind, reg in (('o', openi), ('a', asm)):
        for n, d in reg.items():
            c.ok('linked-entries-match', set(d['linkedEntries']) == link_back[kind].get(int(n), set()))
    counters = meta.get('counters', {})
    c.ok('counter', counters.get('nextEntryNo') == max(nos) + 1)
    c.ok('entry-numbers-unique', len(set(nos)) == len(nos))
    for a in accounts.values():
        c.ok('account-everused', a['everUsed'] == (a['code'] in used))
        c.ok('account-active-if-used', (a['code'] not in used) or a['active'] or a['notes'].startswith('مغلق'))

    # ---- oracle comparison
    cnt = oracle['counts']
    c.ok('count-entries', len(entries) == cnt['entries'])
    c.ok('count-lines', n_lines == cnt['lines'])
    c.ok('count-accounts', len(accounts) == cnt['accounts'])
    c.ok('count-accounts-used', len(used) == cnt['accountsUsed'])
    c.ok('count-documents', len(documents) == cnt['documentsDistinct'])
    c.ok('count-open-items', len(openi) == cnt['openItems'])
    c.ok('count-assumptions', len(asm) == cnt['assumptions'])
    c.ok('count-cost-centers', len(ccs) == cnt['costCenters'])
    years = sorted(int(y) for y in oracle['years'])
    cum = defaultdict(int)
    for y in years:
        o = oracle['years'][str(y)]
        c.ok('year-debit', by_year_dr[y] == to_cents(o['debit']))
        c.ok('year-credit', by_year_cr[y] == to_cents(o['credit']))
        net = -sum(v for a, v in bal[y].items() if accounts[a]['fsLine'] in PL_FS)
        c.ok('year-net-result', net == to_cents(o['netResult']))
        for a, v in bal[y].items():
            cum[a] += v
        for a in accounts:
            rec = oracle['accounts'][a][str(y)]
            cl = cum[a]
            c.ok('account-closing', to_cents(rec['closeDr']) == max(cl, 0) and to_cents(rec['closeCr']) == max(-cl, 0))
        fy = docs.get('fiscalYears', {}).get(str(y))
        c.ok('fiscal-year-doc', fy is not None and fy['year'] == y)
        if fy and fy.get('snapshot'):
            snap = fy['snapshot']
            c.ok('snapshot-totals', to_cents(snap['totals']['dr']) == to_cents(o['tbCumulative']['debit'])
                 and to_cents(snap['totals']['cr']) == to_cents(o['tbCumulative']['credit']))
            c.ok('snapshot-net', to_cents(snap['netResult']) == to_cents(o['netResult']))
            tb = {r['acct']: to_cents(r['dr']) - to_cents(r['cr']) for r in snap['tb']}
            run = defaultdict(int)
            for yy in years:
                if yy <= y:
                    for a, v in bal[yy].items():
                        run[a] += v
            c.ok('snapshot-rows', tb == {a: v for a, v in run.items() if v != 0})
        if fy and fy['state'] == 'closed_reserved':
            c.ok('closed-year-has-snapshot', fy.get('snapshot') is not None)

    # ---- assets replay vs posted depreciation
    assets = docs.get('assets', {})
    for a in assets.values():
        c.ok('asset-accounts', a['acct'] in accounts and (a['accumAcct'] in (None, *accounts)))
        c.ok('asset-date', bool(ISO.match(a['inServiceDate'] or '')))
        c.ok('asset-convention', a['convention'] in ('half_year', 'day_count', 'full_next_year', 'full_year', 'none'))
    rep = replay_assets(assets, years)
    for y in years:
        posted = {a: to_cents(v) for a, v in oracle['depreciationPosted'][str(y)]['byAccum'].items()}
        mine = {a: v for a, v in rep.get(y, {}).items() if v}
        for acct in set(posted) | set(mine):
            c.ok('asset-replay-vs-posted', posted.get(acct, 0) == mine.get(acct, 0))
    # register cost ties to the ledger for every cost account that has register rows, at every year end
    cost_accts = {a['acct'] for a in assets.values()}
    run_net = defaultdict(int)
    for y in years:
        for a, v in bal[y].items():
            run_net[a] += v
        for acct in cost_accts:
            reg = sum(to_cents(a['cost']) for a in assets.values() if a['acct'] == acct and int(a['inServiceDate'][:4]) <= y)
            c.ok('asset-cost-ties-ledger', reg == run_net[acct])
    # ---- registers
    regs = docs.get('registers', {})
    ev = regs.get('fundingEvidence', {}).get('items', [])
    c.ok('evidence-count', len(ev) == oracle['evidence']['rows'])
    for status in ('included', 'after_close', 'excluded'):
        sub = [i for i in ev if i['status'] == ('after_close' if status == 'after_close' else status)]
        c.ok('evidence-status', len(sub) == oracle['evidence']['status'][status]['count']
             and sum(to_cents(i['amount']) for i in sub) == to_cents(oracle['evidence']['status'][status]['total']))
    for g in ('A', 'B', 'C'):
        sub = [i for i in ev if i['grade'] == g]
        c.ok('evidence-grade', len(sub) == oracle['evidence']['grades'][g]['count']
             and sum(to_cents(i['amount']) for i in sub) == to_cents(oracle['evidence']['grades'][g]['total']))
    le = regs.get('legalExpenses', {})
    c.ok('legal-total', sum(to_cents(i['amount']) for i in le.get('items', [])) == to_cents(oracle['legalExpenses']['sumOfItems']))
    pe = regs.get('payrollExposure', {})
    c.ok('payroll-total', sum(to_cents(i['total']) for i in pe.get('items', [])) == to_cents(oracle['payroll']['sumOfYears']))
    sc = regs.get('settlementCreditors', {})
    if sc.get('items') and oracle['settlementShares'].get('sheet8Total') is not None:
        c.ok('settlement-total', sum(to_cents(i['credit']) for i in sc['items']) == to_cents(oracle['settlementShares']['sheet8Total']))
    fa = regs.get('fundingAllocation', {})
    for s_o in oracle['allocation']['scenarios']:
        sid = 'AB'[oracle['allocation']['scenarios'].index(s_o)]
        rows = [r for r in fa.get('items', []) if r['scenario'] == sid]
        c.ok('allocation-rows', len(rows) == s_o['rowCount'])
        if rows and s_o['total'] and s_o['total']['totalShares'] is not None:
            c.ok('allocation-shares', abs(sum(r['sharesAtClose'] or 0 for r in rows) - s_o['total']['totalShares']) < 1e-6)
    c.ok('parties-count', len(parties) == oracle['counts'].get('seedDerived', {}).get('partiesAfterMerge', len(parties)))
    return c


if __name__ == '__main__':
    sys.exit(main())
