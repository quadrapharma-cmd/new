"""Fixed-asset register seed.

Originals come from sheet 7 (cost, rate, start date). Additions that were never put in a register are INFERRED from the
journal's own depreciation descriptions ("<cost> × <rate>% × <fraction>") exactly as the accountant keyed them, then
verified: the charge implied by the inferred convention must equal the amount posted (otherwise the asset note says so).
Non-depreciating balances (land is an original; licences and work in progress are added) get convention 'none'.
"""
import re
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from common import from_cents, iso, to_cents, to_western
from datetime import date, timedelta

# accumulated-depreciation account -> cost account (chart configuration, codes only)
ACCUM_TO_COST = {'1191': '1120', '1192': '1130', '1193': '1140', '1194': '1170', '1195': '1131', '1196': '1150'}
COST_TO_ACCUM = {v: k for k, v in ACCUM_TO_COST.items()}
NON_DEPRECIATING = ('1170', '1180')   # licences and work in progress are listed with convention 'none'

_MEMO = re.compile(
    r'(?P<cost>\d[\d,]*(?:\.\d+)?)\s*[×xX*]\s*(?P<rate>\d+(?:\.\d+)?)\s*%'
    r'(?:\s*[×xX*]?\s*(?P<frac>نصف سنة|سنة كاملة|(?P<num>\d+)\s*/\s*(?P<den>\d+)))?')
_NAME = re.compile(r'إهلاك\s+(.*?)(?:\s+من\s+\d|\s+[—–-]\s|\s+\d[\d,]*(?:\.\d+)?\s*[×xX*]|$)')


def charge_cents(cost_c, rate, convention, year, in_service):
    """First-year/full-year charge in cents (ROUND_HALF_UP on the exact decimal product)."""
    r = Decimal(str(rate))
    base = Decimal(cost_c) * r
    if convention == 'half_year':
        base = base / 2
    elif convention == 'day_count':
        days = (date(year, 12, 31) - date.fromisoformat(in_service)).days + 1
        base = base * min(days, 365) / 365
    elif convention == 'none':
        return 0
    return int(base.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _cap_line(lines, cost_acct, cost_c, first_year):
    """The capitalising debit(s) on the cost account: a single line equal to the cost, else the debits of the first-charge
    year when they add up to the cost (a bundled purchase). -> dict(no, date, entries) or None."""
    hits = [l for l in lines if l['acct'] == cost_acct and l['dr'] == cost_c and first_year - 1 <= l['date'].year <= first_year]
    if not hits:
        hits = [l for l in lines if l['acct'] == cost_acct and l['dr'] == cost_c]
    if hits:
        h = min(hits, key=lambda l: (l['date'], l['no'], l['row']))
        return {'no': h['no'], 'date': h['date'], 'entries': [h['no']]}
    yr = [l for l in lines if l['acct'] == cost_acct and l['dr'] > 0 and l['date'].year == first_year]
    if yr and sum(l['dr'] for l in yr) == cost_c:
        big = max(yr, key=lambda l: (l['dr'], -l['no']))
        return {'no': big['no'], 'date': min(l['date'] for l in yr), 'entries': sorted({l['no'] for l in yr})}
    return None


def _clean_name(text):
    t = re.sub(r'\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{4}', ' ', text or '')
    t = re.sub(r'\s*(المرسملة|المرسمل)\s*', ' ', t)
    return re.sub(r'\s+', ' ', t).strip(' —-')


def infer_additions(lines, chart_by_code, entry_dates):
    """lines: journal lines (cents). Returns a list of inferred asset dicts (no ids yet), oldest first."""
    exp_accts = {c for c, a in chart_by_code.items()
                 if a['cls'] in ('مصروفات', 'تكلفة مبيعات') and 'إهلاك' in a['name']}
    accum = set(ACCUM_TO_COST)
    by_entry = defaultdict(list)
    for l in lines:
        by_entry[l['no']].append(l)
    found = {}
    for no in sorted(by_entry, key=lambda n: (entry_dates[n], n)):
        ls = sorted(by_entry[no], key=lambda l: l['row'])
        for i, l in enumerate(ls):
            if l['acct'] not in exp_accts or l['dr'] <= 0:
                continue
            nxt = next((m for m in ls[i + 1:] if m['acct'] in accum and m['cr'] == l['dr']), None)
            m = _MEMO.search(to_western(l['memo']))
            if not nxt or not m:
                continue
            cost_c = to_cents(m.group('cost').replace(',', ''))
            rate = Decimal(m.group('rate')) / 100
            key = (nxt['acct'], cost_c, str(rate))
            if key in found:
                continue
            year = entry_dates[no].year
            frac, memo = m.group('frac'), to_western(l['memo'])
            conv, in_service, note = None, None, ''
            dates = [(int(d), int(mo), int(y)) for d, mo, y in re.findall(r'(\d{1,2})/(\d{1,2})/(\d{4})', memo)]
            if frac == 'نصف سنة':
                conv = 'half_year'
            elif frac == 'سنة كاملة':
                conv = 'full_year'
            elif frac and m.group('num') and m.group('den') in ('365', '366'):
                conv = 'day_count'
                days = int(m.group('num'))
                in_service = iso(date(year, 12, 31) - timedelta(days=days - 1))
                for d, mo, y in dates:
                    if (d, mo, y) != (31, 12, y) and y == year:
                        in_service = iso(date(y, mo, d))
            else:
                ye = [(d, mo, y) for d, mo, y in dates if (d, mo) == (31, 12) and y < year]
                if ye:
                    conv, in_service = 'full_next_year', iso(date(ye[0][2], 12, 31))
                else:
                    conv = 'full_year'
            cost_acct = ACCUM_TO_COST[nxt['acct']]
            cap = _cap_line(lines, cost_acct, cost_c, year)
            if cap and len(cap['entries']) > 1:
                note += 'التكلفة مجمّعة من القيود ' + '، '.join(str(n) for n in cap['entries']) + '. '
            if in_service is None:
                if cap:
                    in_service = iso(cap['date'])
                else:
                    in_service = iso(date(year, 12, 31) if conv == 'half_year' else date(year, 1, 1))
            if conv == 'half_year' and date.fromisoformat(in_service).year != year:
                in_service = iso(date(year, 12, 31))
                note = 'تاريخ التشغيل غير محدد — اعتُمد نهاية سنة أول إهلاك. '
            expected = charge_cents(cost_c, rate, conv, year, in_service) if conv != 'full_next_year' else None
            if conv == 'full_next_year':
                expected = charge_cents(cost_c, rate, 'full_year', year, in_service)
            if expected is not None and expected != l['dr']:
                note += 'المبلغ المرحَّل لا يطابق احتساب الطريقة المستنتجة — تُراجع. '
            nm = _NAME.search(l['memo'])
            name = _clean_name(nm.group(1) if nm else '') or f'أصل {cost_acct}'
            found[key] = {
                'name': name, 'acct': cost_acct, 'accumAcct': nxt['acct'], 'cost_c': cost_c, 'rate': float(rate),
                'convention': conv, 'inServiceDate': in_service, 'firstChargeYear': year, 'firstChargeEntry': no,
                'sourceEntryNo': cap['no'] if cap else no, 'note': note.strip(),
                'capFound': bool(cap),
            }
    return list(found.values())


def build_assets(sheet7, lines, chart_by_code, entry_dates, expense_acct):
    """Assemble the asset register docs (list of dicts without ids)."""
    out = []
    start = sheet7.get('startDate')
    for it in sheet7['items']:
        cost_c = to_cents(it['cost'])
        acct = it['acct']
        land = not it['rate']
        src = [l for l in lines if l['acct'] == acct and l['dr'] == cost_c]
        src_no = min(src, key=lambda l: (l['date'], l['no']))['no'] if src else None
        out.append({
            'name': it['name'], 'acct': acct, 'accumAcct': COST_TO_ACCUM.get(acct) if not land else None,
            'expenseAcct': expense_acct if not land else None, 'cost_c': cost_c, 'rate': float(it['rate'] or 0),
            'convention': 'none' if land else 'half_year', 'inServiceDate': start or '', 'sourceEntryNo': src_no,
            'notes': 'من جدول الأصول والإهلاك (الورقة ٧)' + (' — لا يُهلك' if land else ''),
            'order': (0, it['row']),
        })
    for a in infer_additions(lines, chart_by_code, entry_dates):
        out.append({
            'name': a['name'], 'acct': a['acct'], 'accumAcct': a['accumAcct'], 'expenseAcct': expense_acct,
            'cost_c': a['cost_c'], 'rate': a['rate'], 'convention': a['convention'],
            'inServiceDate': a['inServiceDate'], 'sourceEntryNo': a['sourceEntryNo'],
            'notes': ('استُنتج من وصف قيد الإهلاك رقم %d — يلزم اعتماد المحاسب. %s' % (a['firstChargeEntry'], a['note'])).strip(),
            'order': (1, a['firstChargeYear'], a['firstChargeEntry']),
        })
    originals = {o['acct'] for o in out}
    for code in NON_DEPRECIATING:
        a = chart_by_code.get(code)
        if not a or code in originals:
            continue
        by_year = defaultdict(list)
        for l in lines:
            if l['acct'] == code:
                by_year[l['date'].year].append(l)
        for yr in sorted(by_year):
            ls = by_year[yr]
            net = sum(l['dr'] - l['cr'] for l in ls)
            if net == 0:
                continue
            big = max(ls, key=lambda l: (abs(l['dr'] - l['cr']), -l['no']))
            out.append({
                'name': f"{a['name']} — {yr}", 'acct': code, 'accumAcct': COST_TO_ACCUM.get(code),
                'expenseAcct': expense_acct if COST_TO_ACCUM.get(code) else None,
                'cost_c': net, 'rate': 0.0, 'convention': 'none', 'inServiceDate': iso(max(l['date'] for l in ls)),
                'sourceEntryNo': big['no'],
                'notes': f'حركة سنة {yr} على رصيد غير مهلك (حق غير ملموس أو مشروع تحت التنفيذ) — القرار للمحاسب بشأن الإطفاء أو التحويل',
                'order': (2, code, yr),
            })
    # credits on a depreciable cost account (returns, disposals) that the original register never knew: a negative-cost row
    # keeps register cost = ledger cost (the depreciation already posted is NOT corrected here, only flagged by the tie).
    for l in sorted(lines, key=lambda x: (x['date'], x['no'], x['row'])):
        if l['acct'] in COST_TO_ACCUM and l['cr'] > 0:
            out.append({
                'name': ('مرتجع/استبعاد — ' + (l['memo'] or '')).strip(' —')[:80], 'acct': l['acct'], 'accumAcct': None,
                'expenseAcct': None, 'cost_c': -l['cr'], 'rate': 0.0, 'convention': 'none',
                'inServiceDate': iso(l['date']), 'sourceEntryNo': l['no'],
                'notes': 'تسوية بالسالب لتكلفة الأصل: دائن على حساب الأصل في القيد %d لم يكن في سجل الأصول. '
                         'لا يُصحَّح الإهلاك المرحَّل — يُراجع مع المحاسب.' % l['no'],
                'order': (3, l['date'].toordinal(), l['no'], l['row']),
            })
    out.sort(key=lambda x: x['order'])
    for x in out:
        x.pop('order')
    return out
