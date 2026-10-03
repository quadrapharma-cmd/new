#!/usr/bin/env python3
"""Workbook -> private seed JSON (one file per db document), following docs/DATA_MODEL.md.

    python3 tools/seed/make_seed.py [--xlsx PATH] [--out DIR] [--imported-at ISO] [--overrides FILE]

Output goes to <out>/seed/<collection path>/<doc id>.json (default <out> = /home/user/.strifa-private) plus review CSVs
in <out>/review/. Deterministic (sorted keys, stable ids, no wall-clock stamps) and idempotent: the seed directory is
rebuilt from scratch on every run. Real data never goes inside the repository.

Default decisions applied (owner has not overridden them):
  * chart: all accounts kept with their codes; 6 sections + 2-digit groups derived from the codes (non-postable, stored in
    meta/groups); notes moved out of names; contra links; party rules; fsLine per account.
  * ACTIVE-UNTIL-USED: an account is active only if it is used in the journal or is on the explicit allow-list
    ACTIVE_ALLOW (retained-earnings anchors 3150/3160, settlement liability 2150 (landing account if the settlement
    reverts to a liability), payroll tax / insurance 2210/2250 (disclosed, never booked), licence amortisation 1194 and
    inventory provision 1240). Accounts whose note says "closed" (مغلق) are inactive even when used.
  * parties: placeholders and trade words -> no party (legacy text kept on the line); group strings -> kind 'group';
    only safe spelling clusters are merged (identical normalised name; or >= 2-token containment with the same title);
    look-alikes stay separate and are flagged in the review CSV; funding / payroll account lines with a placeholder party
    take the account owner as party; owners and manual decisions come from the optional private overrides file.
  * documents 1:1 from the strings (status 'expected', legacyUseCount), no '+' splitting.
  * entries: posted + isLegacy, line order by Excel row, header date = most common line date (ties: latest) and a line on
    another date keeps it in valueDate; header dimensions = most common value, a differing line overrides.
"""
import argparse
import csv
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date

sys.dont_write_bytecode = True      # keep the repository free of __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import assets_infer  # noqa: E402
import parties as P  # noqa: E402
import reader  # noqa: E402
import registers as R  # noqa: E402
import templates_seed  # noqa: E402
import xref  # noqa: E402
from common import (SeedError, assert_outside_repo, clean, eprint, from_cents, iso, parse_dmy, private_dir,  # noqa: E402
                    write_json, xlsx_path)

# --------------------------------------------------------------------------- configuration (codes and Arabic labels only)
CLS_TABLE = {
    'أصول': ('asset', 'D', False, 'ASSET'),
    'مجمع إهلاك': ('asset', 'C', True, 'ACCUM_DEP'),
    'التزامات': ('liability', 'C', False, 'LIABILITY'),
    'حقوق ملكية': ('equity', 'C', False, 'CAPITAL'),
    'حقوق ملكية مدين': ('equity', 'D', True, 'CAPITAL_CALLED'),
    'إيرادات': ('revenue', 'C', False, 'REVENUE'),
    'إيرادات مدين': ('revenue', 'D', True, 'REVENUE_CONTRA'),
    'تكلفة مبيعات': ('expense', 'D', False, 'COGS'),
    'مصروفات': ('expense', 'D', False, 'OPEX'),
    'مصروفات غير واجبة الخصم': ('expense', 'D', False, 'NONDEDUCTIBLE'),
    'وسيط': ('suspense', 'C', False, 'SUSPENSE'),
}
PL_FS = {'REVENUE', 'REVENUE_CONTRA', 'COGS', 'OPEX', 'NONDEDUCTIBLE'}
CONTRA_OF = {'1191': '1120', '1192': '1130', '1193': '1140', '1194': '1170', '1195': '1131', '1196': '1150',
             '1240': '1210', '3120': '3110', '4130': '4110'}
# Accounts that stay ACTIVE although no journal line uses them yet (every other unused account is inactive until first used):
#   3150, 3160  retained-earnings anchors (the balance sheet derives retained earnings; adjustments may land here)
#   2150        settlement creditors: the landing account if the settlement is reclassified from equity to a liability
#   2210, 2250  payroll tax and social insurance payable (disclosed in the registers, never booked so far)
#   1194        accumulated amortisation of licences (the owner/accountant may decide to amortise licence balances)
#   1240        inventory impairment provision
ACTIVE_ALLOW = ('3150', '3160', '2150', '2210', '2250', '1194', '1240')
PARTY_REQUIRED = {'1250', '1270', '1290', '1410', '1420', '2110', '2151', '2160', '3120'}
PARTY_REQUIRED_RANGES = (('2310', '2340'), ('3211', '3217'))
PARTY_RECOMMENDED = {'1310', '1320', '1330', '1340', '2130'}
OWNED_ACCOUNTS = ('2310', '2311', '2320', '2321', '2322', '2324', '2330', '2340')   # party comes from the account owner
FUNDING_CASH = ('2310', '2320', '2330', '2340')
GROUP_NAMES = {
    '11': 'الأصول الثابتة', '12': 'المخزون والأرصدة المدينة', '13': 'النقدية والبنوك', '14': 'عهد وجاري الشركاء',
    '21': 'الموردون والمستحقات', '22': 'مستحقات جهات حكومية', '23': 'ذمم الممولين والشركاء',
    '24': 'قروض طويلة الأجل', '31': 'رأس المال والاحتياطيات', '32': 'حصص مقابل عقد التسوية', '41': 'إيرادات النشاط',
    '42': 'إيرادات أخرى', '51': 'تكلفة المبيعات', '52': 'مصروفات تشغيلية وإدارية', '53': 'مصروفات غير واجبة الخصم',
    '54': 'مصروفات بنكية', '61': 'حسابات وسيطة',
}
NEW_SECTORS = ('خارج ق.72',)
FIDUCIARY_WORD = 'أمانة'
OPEN_STATUS = {'مفتوح': 'open', 'جزئي': 'partial', 'مغلق': 'closed', 'قيد الاستفسار': 'inquiry'}
SEED_ACTOR = None   # legacy rows carry no user


def iso_z(stamp):
    """Workbook property stamp (naive ISO) -> '...Z' (deterministic default for baseline.importedAt)."""
    stamp = re.sub(r'(\.\d+)?(\+00:00)?$', '', str(stamp))
    return stamp + 'Z'


def in_range(code, rngs):
    return any(a <= code <= b for a, b in rngs)


def split_notes(name):
    """Long business notes leave the account name: trailing parenthesis, and a '— مغلق ...' tail."""
    notes = []
    n = name
    m = re.search(r'\s*[\(（]([^\)）]*)[\)）]\s*$', n)
    if m and re.search(r'[؀-ۿ0-9]', m.group(1)):
        notes.append(clean(m.group(1)))
        n = n[:m.start()]
    m = re.search(r'\s*[—–-]\s*(مغلق.*)$', n)
    if m:
        notes.insert(0, clean(m.group(1)))
        n = n[:m.start()]
    return clean(n), '؛ '.join(notes)


def doc_type_of(comp):
    c = comp
    if 'كشوف' in c:
        return 'كشف حسابات'
    if 'كشف' in c and any(w in c for w in ('كريدي', 'بنك', 'حساب')) and 'مصروفات' not in c:
        return 'كشف بنك'
    if 'دفتر' in c and 'خزينة' in c.replace('الخزينة', 'خزينة'):
        return 'دفتر خزينة'
    if 'يومية' in c:
        return 'يومية المحاسب'
    if 'جدول' in c:
        return 'جدول'
    if 'عقد' in c:
        return 'عقد'
    if 'محضر' in c:
        return 'محضر'
    if 'إقرار' in c:
        return 'إقرار ضريبي'
    if 'إفادة' in c or 'تعليمات' in c:
        return 'إفادة الإدارة'
    if 'تحليل' in c:
        return 'تحليل'
    if 'قائمة' in c or 'قوائم' in c:
        return 'قوائم'
    if 'شهادة' in c:
        return 'شهادة'
    if 'فواتير' in c or 'فاتورة' in c:
        return 'فواتير'
    if 'كشف' in c:
        return 'كشف'
    return 'مستند'


def classify_doc(ref):
    """(type, grade): type of the first component; grade = best evidence among components (A bank statement,
    B hand-kept cash book, C management statement) or None when unknown."""
    comps = [x.strip() for x in ref.split('+') if x.strip()] or [ref]
    types = [doc_type_of(c) for c in comps]
    grades = []
    for c, t in zip(comps, types):
        if t == 'كشف بنك':
            grades.append('A')
        elif t == 'دفتر خزينة' and ('بخط اليد' in c or 'اليدوي' in c):
            grades.append('B')
        elif t == 'إفادة الإدارة':
            grades.append('C')
    return types[0], (min(grades) if grades else None)


EMPTY_OVERRIDES = {'merge': [], 'separate': [], 'kinds': {}, 'owners': {}, 'null_parties': [], 'group_parties': []}


def load_overrides(path):
    if path and os.path.exists(path):
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        for k in ('merge', 'separate', 'null_parties', 'group_parties'):
            data.setdefault(k, [])
        data.setdefault('kinds', {})
        data.setdefault('owners', {})
        return data, True
    return dict(EMPTY_OVERRIDES, merge=[], separate=[], null_parties=[], group_parties=[], kinds={}, owners={}), False


# --------------------------------------------------------------------------- the build
def build(xlsx, imported_at=None, overrides=None):
    wb = reader.open_workbook(xlsx)
    overrides = dict(EMPTY_OVERRIDES, **(overrides or {}))
    warnings = []
    docs = {}          # 'collection/id' -> doc
    report = {}

    company = reader.read_company(wb)
    chart = reader.read_chart(wb)
    jr = reader.read_journal(wb)
    lines = jr['lines']
    if not lines:
        raise SeedError('journal has no lines')
    if jr['skippedRows']:
        warnings.append(f'{jr["skippedRows"]} صف في اليومية بلا كود حساب لم يُستورد')
    imported_at = imported_at or iso_z(wb.modified or wb.created or '1970-01-01T00:00:00')
    incorporated = company['incorporated']

    chart_by_code = {a['code']: a for a in chart['accounts']}
    for l in lines:
        if l['acct'] not in chart_by_code:
            raise SeedError(f'journal row {l["row"]}: account code is not in the chart')
        if l['status'] and l['status'] != 'سليم':
            warnings.append(f'سطر اليومية {l["row"]} حالته «{l["status"]}» في الملف الأصلي')

    # ---- entries grouping, balance check, header dates
    by_no = defaultdict(list)
    for l in lines:
        by_no[l['no']].append(l)
    for ls in by_no.values():
        ls.sort(key=lambda x: x['row'])
    entry_dates, total_dr, total_cr = {}, 0, 0
    for no, ls in by_no.items():
        d = sum(l['dr'] for l in ls)
        c = sum(l['cr'] for l in ls)
        if d != c or len(ls) < 2:
            raise SeedError(f'entry {no} is not a balanced entry of at least two lines')
        total_dr += d
        total_cr += c
        cnt = Counter(l['date'] for l in ls)
        top = max(cnt.values())
        entry_dates[no] = max(dt for dt, k in cnt.items() if k == top)   # most common, ties -> latest
    used_accts = Counter(l['acct'] for l in lines)

    # ---- accounts + groups
    accounts = {}
    for a in chart['accounts']:
        if a['cls'] not in CLS_TABLE:
            raise SeedError(f'account {a["code"]}: unknown classification')
        typ, normal, contra, fs = CLS_TABLE[a['cls']]
        code = a['code']
        name, notes = split_notes(a['name'])
        if a['cls'] == 'حقوق ملكية':
            if code in ('3150', '3160'):
                fs = 'RETAINED'
            elif code.startswith('32'):
                fs = 'SETTLEMENT_SHARES'
        closed = notes.startswith('مغلق')
        active = (code in used_accts or code in ACTIVE_ALLOW) and not closed
        rule = 'none'
        if code in PARTY_REQUIRED or in_range(code, PARTY_REQUIRED_RANGES):
            rule = 'required'
        elif code in PARTY_RECOMMENDED:
            rule = 'recommended'
        doc = {'code': code, 'name': name, 'notes': notes, 'cls': a['cls'], 'type': typ, 'normal': normal,
               'contra': contra, 'contraOf': CONTRA_OF.get(code) if contra and CONTRA_OF.get(code) in chart_by_code else None,
               'fsLine': fs, 'parent': code[:2], 'postable': True, 'active': active, 'partyRule': rule,
               'everUsed': code in used_accts}
        accounts[code] = doc
        docs[f'accounts/{code}'] = doc
    sections = []
    for s in chart['sections']:
        nxt = chart['accounts'][s['before']]['code'] if s['before'] < len(chart['accounts']) else None
        if nxt:
            sections.append({'code': nxt[0], 'name': s['title'], 'level': 1})
    groups = list({(g['code']): g for g in sections}.values())
    for pre in sorted({a['code'][:2] for a in chart['accounts']}):
        groups.append({'code': pre, 'name': GROUP_NAMES.get(pre, f'مجموعة {pre}'), 'level': 2})
    docs['meta/groups'] = {'groups': sorted(groups, key=lambda g: g['code'])}

    # ---- dimensions
    cc_count = Counter(l['cc'] for l in lines)
    sec_count = Counter(l['sector'] for l in lines)
    cc_names = sorted(cc_count, key=lambda n: (-cc_count[n], n))
    sec_names = sorted(sec_count, key=lambda n: (-sec_count[n], n))
    for extra in NEW_SECTORS:
        if extra not in sec_names:
            sec_names.append(extra)
    cc_id = {n: f'cc{i}' for i, n in enumerate(cc_names, start=1)}
    sec_id = {n: f's{i}' for i, n in enumerate(sec_names, start=1)}
    for n, i in cc_id.items():
        docs[f'costCenters/{i}'] = {'id': i, 'name': n, 'kind': 'fiduciary' if FIDUCIARY_WORD in n else 'own', 'active': True}
    for n, i in sec_id.items():
        docs[f'sectors/{i}'] = {'id': i, 'name': n, 'active': True}
    shared_sector = sec_id.get('مشترك')

    # ---- parties
    raw_class = {r: P.classify(r, overrides['null_parties'], overrides['group_parties']) for r in {l['party'] for l in lines}}
    raw_stats = defaultdict(lambda: {'lines': 0, 'years': set(), 'accts': Counter(), 'first_row': 10 ** 9})
    for l in lines:
        c = raw_class[l['party']]
        if c in ('party', 'group'):
            s = raw_stats[l['party']]
            s['lines'] += 1
            s['years'].add(l['date'].year)
            s['accts'][l['acct']] += 1
            s['first_row'] = min(s['first_row'], l['row'])
    person_raws = {r: s for r, s in raw_stats.items() if raw_class[r] == 'party'}
    group_raws = sorted(r for r in raw_stats if raw_class[r] == 'group')
    clusters, review = P.cluster_parties(person_raws, overrides)
    clusters = [dict(c, group=False) for c in clusters] + [
        {'raws': [r], 'confidence': 'single', 'group': True} for r in group_raws]
    for r in group_raws:
        review[r] = {'confidence': 'single', 'identity_sensitive': False}
    clusters.sort(key=lambda c: min(raw_stats[r]['first_row'] for r in c['raws']))
    cluster_of = {r: i for i, c in enumerate(clusters) for r in c['raws']}
    party_id = {i: f'p{i + 1:04d}' for i in range(len(clusters))}
    keys = {r: P.key_tokens(r) for r in raw_stats}
    # line counts per account per cluster (owner tie-break)
    acct_cluster_lines = defaultdict(Counter)
    for l in lines:
        if l['party'] in cluster_of:
            acct_cluster_lines[l['acct']][cluster_of[l['party']]] += 1
    owners, owner_rows = {}, []
    for code in sorted(set(OWNED_ACCOUNTS) | {c for c in chart_by_code if c.startswith('32')}):
        a = chart_by_code.get(code)
        if not a:
            continue
        forced = overrides['owners'].get(code)
        method = 'override'
        ci = cluster_of.get(forced) if forced else None
        if ci is None:
            method = 'name'
            ci = P.find_account_owner(a['name'], clusters, keys, acct_cluster_lines[code])
        if ci is None and acct_cluster_lines[code]:
            method = 'dominant-line-party'
            top, cnt = acct_cluster_lines[code].most_common(1)[0]
            if cnt * 2 >= sum(acct_cluster_lines[code].values()):
                ci = top
        if ci is not None:
            owners[code] = ci
            owner_rows.append({'account': code, 'party': party_id[ci], 'method': method})
        elif code in OWNED_ACCOUNTS:
            warnings.append(f'لم يُحدَّد مالك الحساب {code} — تبقى أسطره بلا طرف')
    owned_by_cluster = defaultdict(list)
    for code, ci in owners.items():
        owned_by_cluster[ci].append(code)

    party_docs = {}
    for ci, c in enumerate(clusters):
        raws = c['raws']
        accts = Counter()
        owned = set(owned_by_cluster.get(ci, []))
        for r in raws:
            for a, n in raw_stats[r]['accts'].items():
                if (a in OWNED_ACCOUNTS or a.startswith('32')) and a not in owned:
                    continue                           # a stray line on someone else's account says nothing about the kind
                accts[a] += n
        for code in owned:
            accts[code] += 1                           # owning an account counts as being used on it
        kind = P.infer_kind(raws, accts, group=c['group'],
                            forced=next((overrides['kinds'][r] for r in raws if r in overrides['kinds']), None))
        name = P.pick_name(raws, raw_stats)
        own = sorted(x for x in owned_by_cluster.get(ci, []) if x in OWNED_ACCOUNTS)
        default_acct = None
        accrual_acct = None
        if own:
            cnt = Counter({x: sum(1 for l in lines if l['acct'] == x and l['party'] in raws) for x in own})
            default_acct = sorted(own, key=lambda x: (-cnt[x], x))[0]
            accr = [x for x in own if 'استحقاقات' in chart_by_code[x]['name']]
            accrual_acct = accr[0] if accr else None
        roles = []
        for code in sorted(owned_by_cluster.get(ci, [])):
            if code.startswith('32'):
                note_date = parse_dmy(accounts[code]['notes'])
                first = min((l['date'] for l in lines if l['acct'] == code), default=None)
                frm = note_date or (incorporated if incorporated and first and first.year == int(incorporated[:4])
                                    else (iso(first) if first else None))
                roles.append({'role': 'shareholder', 'from': frm, 'to': None})
        roles.sort(key=lambda r: (r['role'], r['from'] or ''))
        pdoc = {'id': party_id[ci], 'name': name, 'kind': kind, 'aliases': sorted(r for r in raws if r != name),
                'roles': roles, 'taxId': '', 'active': True, 'mergedInto': None, 'defaultAccount': default_acct,
                'legacyTexts': sorted(raws)}
        if own:
            pdoc['boundAccounts'] = own
        if accrual_acct:
            pdoc['accrualAccount'] = accrual_acct
        party_docs[ci] = pdoc
        docs[f'parties/{party_id[ci]}'] = pdoc

    def party_of_line(l):
        raw = l['party']
        if raw in cluster_of:
            return party_id[cluster_of[raw]], False
        if l['acct'] in OWNED_ACCOUNTS and l['acct'] in owners:
            return party_id[owners[l['acct']]], True
        return None, False

    # ---- documents
    first_row_doc = {}
    use_count = Counter(l['doc'] for l in lines if l['doc'])
    for l in lines:
        if l['doc']:
            first_row_doc.setdefault(l['doc'], l['row'])
    doc_id = {}
    for i, ref in enumerate(sorted(first_row_doc, key=lambda r: (first_row_doc[r], r)), start=1):
        did = f'D{i:04d}'
        doc_id[ref] = did
        typ, grade = classify_doc(ref)
        docs[f'documents/{did}'] = {'id': did, 'ref': ref, 'type': typ, 'date': None, 'grade': grade, 'status': 'expected',
                                    'note': '', 'files': [], 'legacyUseCount': use_count[ref]}

    # ---- registers: open items and assumptions
    oi = reader.read_open_items(wb)['items']
    asm = reader.read_assumptions(wb)['items']
    open_nums, asm_nums = {i['n'] for i in oi}, {i['n'] for i in asm}
    open_docs, asm_docs = {}, {}
    for it in oi:
        yr = it['yearRaw']
        text = str(yr) if yr is not None else ''
        years = [int(y) for y in re.findall(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)', text)]
        frm = years[0] if years else None
        to = years[-1] if len(years) > 1 else (frm if years and '+' not in text else None)
        if isinstance(yr, str) and re.fullmatch(r'\d{4}', yr.strip()):
            yr = int(yr)
        if it['statusText'] not in OPEN_STATUS:
            warnings.append(f'حالة البند {it["n"]} غير معروفة: «{it["statusText"]}» — عُيّنت «مفتوح»')
        open_docs[it['n']] = {'n': it['n'], 'year': yr, 'from': frm, 'to': to, 'item': it['item'], 'effect': it['effect'],
                              'docRequired': it['docRequired'], 'status': OPEN_STATUS.get(it['statusText'], 'open'),
                              'linkedEntries': [], 'closedDocId': None, 'closedAt': None, 'createdBy': None, 'createdAt': None}
    for it in asm:
        asm_docs[it['n']] = {'n': it['n'], 'text': it['text'], 'effect': it['effect'], 'docRequired': it['docRequired'],
                             'ifNotReceived': it['ifNotReceived'], 'status': 'pending', 'linkedEntries': [],
                             'closedDocId': None, 'closedAt': None}

    # ---- entries
    sig_groups = defaultdict(list)
    for no, ls in by_no.items():
        sig = tuple(sorted((l['date'].isoformat(), l['acct'], l['dr'], l['cr'], l['memo'], l['party'], l['doc'], l['cc'],
                            l['sector']) for l in ls))
        sig_groups[sig].append(no)
    dup_of = {}
    for nos in sig_groups.values():
        if len(nos) > 1:
            for n in nos:
                dup_of[n] = sorted(x for x in nos if x != n)
    pre_inc = {}
    if incorporated:
        for no, d in entry_dates.items():
            if iso(d) < incorporated:
                dstr = f'{d.day}/{d.month}/{d.year}'
                hits = [it['n'] for it in oi if dstr in (it['item'] or '') and 'تأسيس' in ((it['item'] or '') + (it['effect'] or ''))]
                pre_inc[no] = hits[0] if len(hits) == 1 else None
    stats = Counter()
    link_rows = []
    substituted = 0
    entry_docs = {}
    for no in sorted(by_no):
        ls = by_no[no]
        hdate = entry_dates[no]
        hdoc = Counter(l['doc'] for l in ls if l['doc'])
        hcc, hsec = Counter(l['cc'] for l in ls), Counter(l['sector'] for l in ls)

        def top(counter, ls_key):
            if not counter:
                return None
            best = max(counter.values())
            for l in ls:                       # ties -> first line by row
                v = l[ls_key]
                if v and counter[v] == best:
                    return v
            return None
        h_doc, h_cc, h_sec = top(hdoc, 'doc'), top(hcc, 'cc'), top(hsec, 'sector')
        out_lines = []
        for i, l in enumerate(ls, start=1):
            pid, subst = party_of_line(l)
            substituted += 1 if subst else 0
            reasons = []
            links = []
            a_nums, o_nums = xref.parse_links(l['memo'], l['doc'], l['party'])
            bad = []
            for n in a_nums:
                (links.append({'t': 'a', 'n': n}) if n in asm_nums else bad.append(f'افتراض {n}'))
            for n in o_nums:
                (links.append({'t': 'o', 'n': n}) if n in open_nums else bad.append(f'بند {n}'))
            if links:
                label = '، '.join(('افتراض ' if k['t'] == 'a' else 'بند ') + str(k['n']) for k in links)
                reasons.append(f'مرتبط بـ {label} (ربط تلقائي من النص — يلزم التأكيد)')
                stats['lines_with_links'] += 1
                stats['links'] += len(links)
                link_rows.append({'entry': no, 'row': l['row'], 'links': label})
            if bad:
                reasons.append('إشارة إلى سجل غير موجود: ' + '، '.join(bad))
                stats['lines_bad_links'] += 1
            if xref.has_inquiry_tag(l['memo'], l['doc'], l['party']):
                reasons.append('قيد الاستفسار')
                stats['lines_inquiry'] += 1
            if no in pre_inc:
                reasons.append(f'التاريخ يسبق تأسيس الشركة ({iso(hdate)[8:]}/{iso(hdate)[5:7]}/{iso(hdate)[:4]})')
                stats['lines_pre_incorporation'] += 1
                if pre_inc[no] and {'t': 'o', 'n': pre_inc[no]} not in links:
                    links.append({'t': 'o', 'n': pre_inc[no]})
            if no in dup_of:
                reasons.append('تكرار محتمل — مطابق للقيد رقم ' + '، '.join(str(x) for x in dup_of[no]))
                stats['lines_possible_duplicate'] += 1
            if pid is None and accounts[l['acct']]['partyRule'] == 'required':
                reasons.append('سطر قديم بلا طرف رغم أن الحساب يشترطه')
                stats['lines_party_required_missing'] += 1
            links.sort(key=lambda k: (k['t'], k['n']))
            out_lines.append({
                'n': i, 'acct': l['acct'], 'dr': from_cents(l['dr']), 'cr': from_cents(l['cr']), 'memo': l['memo'],
                'partyId': pid,
                'docIds': [doc_id[l['doc']]] if l['doc'] and l['doc'] != h_doc else [],
                'cc': cc_id[l['cc']] if l['cc'] and l['cc'] != h_cc else None,
                'sector': sec_id[l['sector']] if l['sector'] and l['sector'] != h_sec else None,
                'valueDate': iso(l['date']) if l['date'] != hdate else None,
                'needsReview': bool(reasons), 'reviewReason': '؛ '.join(reasons), 'links': links,
                'legacy': {'partyText': l['party'], 'docText': l['doc'], 'row': l['row']},
            })
            if reasons:
                stats['lines_flagged'] += 1
            if l['date'] != hdate:
                stats['lines_value_date'] += 1
            if pid is None:
                stats['lines_null_party'] += 1
        eid = f'e{no:06d}'
        entry_docs[no] = {
            'no': no, 'date': iso(hdate), 'fy': hdate.year, 'status': 'posted', 'desc': ls[0]['memo'],
            'docIds': [doc_id[h_doc]] if h_doc else [], 'cc': cc_id[h_cc] if h_cc else None,
            'sector': sec_id[h_sec] if h_sec else None, 'source': 'legacy', 'isLegacy': True,
            'legacyRow': ls[0]['row'], 'version': 1, 'voidReason': None, 'reversalOf': None, 'createdBy': SEED_ACTOR,
            'createdAt': imported_at, 'postedBy': SEED_ACTOR, 'postedAt': imported_at, 'lines': out_lines, 'history': [],
        }
        docs[f'entries/{eid}'] = entry_docs[no]
        stats['entries_flagged'] += 1 if any(x['needsReview'] for x in out_lines) else 0
        for x in out_lines:
            for k in x['links']:
                (open_docs if k['t'] == 'o' else asm_docs)[k['n']]['linkedEntries'].append(no)
    for d in list(open_docs.values()) + list(asm_docs.values()):
        d['linkedEntries'] = sorted(set(d['linkedEntries']))
    for n, d in open_docs.items():
        docs[f'openItems/{n}'] = d
    for n, d in asm_docs.items():
        docs[f'assumptions/{n}'] = d

    # ---- fiscal years (+ baseline snapshots of the closed years)
    close = reader.read_close_status(wb)
    years = {y['year']: y for y in close['years']}
    status_rows = {s['year']: s for s in close['statusRows']}
    journal_years = sorted({d.year for d in entry_dates.values()})
    cum = defaultdict(int)
    by_year_acct = defaultdict(lambda: defaultdict(int))
    for l in lines:
        by_year_acct[entry_dates[l['no']].year][l['acct']] += l['dr'] - l['cr']
    net_by_year = {}
    snap_tb = {}
    run = defaultdict(int)
    for y in journal_years:
        for acct, v in by_year_acct[y].items():
            run[acct] += v
        net_by_year[y] = -sum(v for acct, v in by_year_acct[y].items() if accounts[acct]['fsLine'] in PL_FS)
        snap_tb[y] = {a: v for a, v in run.items() if v != 0}
    for y in sorted(set(years) | set(status_rows) | set(journal_years)):
        rec = years.get(y)
        st_row = status_rows.get(y)
        closed = bool(rec and 'مقفلة' in rec['statusText'])
        text = rec['text'] if rec else (st_row['text'] if st_row else '')
        doc = {'year': y, 'state': 'closed_reserved' if closed else 'open', 'startDate': f'{y}-01-01',
               'endDate': f'{y}-12-31', 'legalStart': incorporated if incorporated and incorporated[:4] == str(y) else None,
               'reservation': {'sources': rec['sources'] if rec else '', 'notRecorded': rec['notRecorded'] if rec else '',
                               'text': text, 'lastUpdate': rec['lastUpdate'] if rec else None,
                               'statusText': rec['statusText'] if rec else (st_row['text'].split('—')[0].strip() if st_row else '')},
               'revision': 0, 'snapshot': None,
               'neededDocs': [{'text': n['text']} for n in close['needed'] if n['scope'] == str(y)],
               'closedAt': None, 'closedBy': None}
        if closed and y in snap_tb:
            tb = sorted(snap_tb[y].items())
            doc['snapshot'] = {'takenAt': imported_at, 'revision': 0,
                               'totals': {'dr': from_cents(sum(v for _, v in tb if v > 0)),
                                          'cr': from_cents(sum(-v for _, v in tb if v < 0))},
                               'tb': [{'acct': a, 'dr': from_cents(max(v, 0)), 'cr': from_cents(max(-v, 0))} for a, v in tb],
                               'netResult': from_cents(net_by_year[y])}
        docs[f'fiscalYears/{y}'] = doc

    # ---- assets
    exp_candidates = sorted(c for c, a in chart_by_code.items()
                            if a['cls'] in ('مصروفات', 'تكلفة مبيعات') and 'إهلاك' in a['name'])
    used_exp = [c for c in exp_candidates if c in used_accts]
    expense_acct = (used_exp or exp_candidates or [None])[0]
    s7 = reader.read_assets_sheet(wb)
    asset_list = assets_infer.build_assets(s7, lines, chart_by_code, entry_dates, expense_acct) if expense_acct else []
    for i, a in enumerate(asset_list, start=1):
        aid = f'A{i:03d}'
        docs[f'assets/{aid}'] = {'id': aid, 'name': a['name'], 'acct': a['acct'], 'accumAcct': a['accumAcct'],
                                 'expenseAcct': a['expenseAcct'], 'cost': from_cents(a['cost_c']),
                                 'inServiceDate': a['inServiceDate'], 'rate': a['rate'], 'convention': a['convention'],
                                 'residual': 0, 'sourceEntryNo': a['sourceEntryNo'], 'active': True,
                                 'notes': a.get('notes', '')}

    # ---- templates, registers, meta
    for tid, t in templates_seed.templates().items():
        docs[f'templates/{tid}'] = t
    reg_docs, notes = R.build_registers(wb, chart['accounts'])
    notes += R.sheet11_notes(wb, close)
    notes.sort(key=lambda n: (n['sheet'], n['row']))
    reg_docs['workbookNotes'] = {'items': notes, 'source': {'sheet': None, 'title': 'ملاحظات وتحفظات الملف الأصلي'}}
    for name, d in reg_docs.items():
        docs[f'registers/{name}'] = d

    fund_rule = [c for c in FUNDING_CASH if c in chart_by_code]
    accrual_of = {}
    for pdoc in party_docs.values():
        for c in pdoc.get('boundAccounts', []):
            if c in FUNDING_CASH and pdoc.get('accrualAccount'):
                accrual_of[c] = pdoc['accrualAccount']
    next_no = max(by_no) + 1
    counts = {
        'accounts': len(accounts), 'groups': len(docs['meta/groups']['groups']), 'costCenters': len(cc_id),
        'sectors': len(sec_id), 'parties': len(party_docs), 'documents': len(doc_id), 'entries': len(by_no),
        'lines': len(lines), 'fiscalYears': len([k for k in docs if k.startswith('fiscalYears/')]),
        'openItems': len(open_docs), 'assumptions': len(asm_docs), 'assets': len(asset_list),
        'templates': len(templates_seed.TEMPLATES), 'registers': len(reg_docs),
    }
    docs['meta/config'] = {
        'schemaVersion': 1,
        'company': {'name': company['name'], 'formerName': company['formerName'], 'taxNo': company['taxNo'],
                    'crNo': company['crNo'], 'incorporated': incorporated},
        'baseline': {'file': os.path.basename(xlsx), 'sha256': wb.sha256, 'wbCreated': wb.created,
                     'wbModified': wb.modified, 'importedAt': imported_at, 'counts': counts},
        'settings': {'digits': 'western'},
        'defaults': {'sector': shared_sector},
        'rules': {'fundingAccounts': fund_rule, 'evidenceGrades': ['A', 'B'], 'sharedSectorNames': ['مشترك'],
                  'draftMaxAgeDays': 7, 'accrualAccountOf': accrual_of},
    }
    docs['meta/counters'] = {'nextEntryNo': next_no}
    n_multi_clusters = sum(1 for c in clusters if len(c['raws']) > 1)
    sens_raws = [r for r, v in review.items() if v['identity_sensitive']]
    warnings.extend([
        f'{stats["lines_flagged"]} سطر عُلِّم للمراجعة ({stats["entries_flagged"]} قيد)',
        f'{stats["lines_with_links"]} سطر يشير إلى افتراض أو بند ({stats["links"]} رابط) — الربط تلقائي ويحتاج تأكيداً',
        f'{len(dup_of)} قيد متطابق بالتاريخ والأسطر — تكرار محتمل (لم يُدمج)',
        f'{len(pre_inc)} قيد مؤرخ قبل تأسيس الشركة',
        f'{len(sens_raws)} كتابة اسم متشابهة تُركت منفصلة للمراجعة (identity_sensitive)',
    ])
    docs['importRuns/r0001'] = {'at': imported_at, 'by': 'seed', 'fileSha256': wb.sha256, 'counts': counts,
                                'warnings': warnings, 'differences': []}

    # ---- review rows (party alias CSV)
    review_rows = []
    cluster_name = {}
    for ci, c in enumerate(clusters):
        for r in c['raws']:
            cluster_name[r] = party_docs[ci]['name']
    for raw in sorted({l['party'] for l in lines}, key=lambda r: (cluster_name.get(r, '~'), r)):
        cls = raw_class[raw]
        subset = [l for l in lines if l['party'] == raw]
        accts = Counter(l['acct'] for l in subset)
        row = {'raw': raw, 'lines': len(subset), 'years': ','.join(str(y) for y in sorted({l['date'].year for l in subset})),
               'top_accounts': ';'.join(f'{a}({n})' for a, n in sorted(accts.items(), key=lambda kv: (-kv[1], kv[0]))[:3])}
        if cls in ('placeholder', 'trade'):
            row.update({'proposed_party': '', 'kind': cls, 'confidence': 'n/a', 'identity_sensitive': 0})
        else:
            ci = cluster_of[raw]
            row.update({'proposed_party': party_docs[ci]['name'], 'kind': party_docs[ci]['kind'],
                        'confidence': review[raw]['confidence'], 'identity_sensitive': 1 if review[raw]['identity_sensitive'] else 0})
        review_rows.append(row)

    merged_by_rule = sum(1 for c in clusters if len(c['raws']) > 1 and c['confidence'] in ('high', 'medium'))
    merged_by_override = sum(1 for c in clusters if len(c['raws']) > 1 and c['confidence'] == 'override')
    report.update({
        'counts': counts, 'totalDebitCents': total_dr, 'totalCreditCents': total_cr, 'stats': dict(stats),
        'partyRaw': len(raw_class), 'partyPlaceholderRaws': sum(1 for c in raw_class.values() if c in ('placeholder', 'trade')),
        'partyClustersMultiMember': n_multi_clusters, 'partyMergedByRule': merged_by_rule,
        'partyMergedByOverride': merged_by_override, 'partyIdentitySensitiveRaws': len(sens_raws),
        'partyOwnerSubstitutedLines': substituted, 'duplicateEntries': len(dup_of), 'preIncorporationEntries': len(pre_inc),
        'warnings': warnings, 'assetsInferred': sum(1 for a in asset_list if a['notes'].startswith('استُنتج')),
    })
    link_rows.sort(key=lambda r: (r['entry'], r['row']))
    return {'docs': docs, 'review_rows': review_rows, 'owner_rows': owner_rows, 'link_rows': link_rows,
            'asset_rows': [{'id': f'A{i:03d}', **{k: v for k, v in a.items() if k != 'cost_c'}, 'cost': from_cents(a['cost_c'])}
                           for i, a in enumerate(asset_list, start=1)], 'report': report}


# --------------------------------------------------------------------------- output
def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})


def write_outputs(result, out_dir):
    assert_outside_repo(out_dir)
    seed_dir = os.path.join(out_dir, 'seed')
    if os.path.isdir(seed_dir):
        shutil.rmtree(seed_dir)
    sizes = {}
    for path, doc in result['docs'].items():
        sizes[path] = write_json(os.path.join(seed_dir, path + '.json'), doc)
    review = os.path.join(out_dir, 'review')
    write_csv(os.path.join(review, 'party_alias_review.csv'), result['review_rows'],
              ['raw', 'lines', 'years', 'top_accounts', 'proposed_party', 'kind', 'confidence', 'identity_sensitive'])
    write_csv(os.path.join(review, 'funding_account_owners.csv'), result['owner_rows'], ['account', 'party', 'method'])
    write_csv(os.path.join(review, 'crossref_proposed.csv'), result['link_rows'], ['entry', 'row', 'links'])
    write_csv(os.path.join(review, 'asset_additions_seed.csv'), result['asset_rows'],
              ['id', 'name', 'acct', 'accumAcct', 'cost', 'rate', 'convention', 'inServiceDate', 'sourceEntryNo', 'notes'])
    return sizes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--xlsx')
    ap.add_argument('--out', default=None, help='private directory (default STRIFA_PRIVATE_DIR or /home/user/.strifa-private)')
    ap.add_argument('--imported-at', default=None, help='ISO stamp for baseline.importedAt (default: workbook modified time)')
    ap.add_argument('--overrides', default=None, help='private party overrides JSON (default <out>/config/party_overrides.json)')
    args = ap.parse_args(argv)
    out = args.out or private_dir()
    try:
        ov_path = args.overrides or os.path.join(out, 'config', 'party_overrides.json')
        overrides, found = load_overrides(ov_path)
        result = build(xlsx_path(args.xlsx), args.imported_at, overrides)
        sizes = write_outputs(result, out)
    except SeedError as e:
        eprint(f'make_seed: {e}')
        return 2
    rep = result['report']
    per = Counter(p.split('/')[0] for p in result['docs'])
    print('make_seed: OK  (overrides file: %s)' % ('found' if found else 'not found'))
    print('docs per collection:', json.dumps(dict(sorted(per.items())), ensure_ascii=False))
    print('total docs:', len(result['docs']), ' largest doc bytes:', max(sizes.values()))
    print('debit == credit:', rep['totalDebitCents'] == rep['totalCreditCents'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
