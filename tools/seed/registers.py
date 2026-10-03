"""Read-only aggregated registers (values only; formulas never copied): registers/<name> = {items, source, ...}.

Documents stay below 200 KiB; if a register would be larger it is split into `<name>` + `<name>-2` ... (never silently cut).
"""
import re

import reader
from common import SeedError, norm_text


def _src(wb, idx):
    return {'sheet': idx, 'title': wb.title(idx)}


def _match_account(holder, accounts):
    """Settlement-holder name -> the equity account (32xx) whose name contains the whole holder name."""
    h = norm_text(holder or '')
    if not h:
        return None
    hits = [a['code'] for a in accounts if a['code'].startswith('32') and h in norm_text(a['name'])]
    return hits[0] if len(hits) == 1 else None


def build_registers(wb, chart_accounts):
    """-> ({name: doc}, notes list for workbookNotes, consumed rows per sheet)"""
    docs, notes = {}, []

    def add_notes(idx, ws_notes, kind='text'):
        for n in ws_notes:
            notes.append({'sheet': idx, 'sheetTitle': wb.title(idx), 'row': n['row'], 'marker': n['marker'],
                          'text': n['text'], 'kind': kind})

    # sheet 0: operating guide
    comp = reader.read_company(wb)
    add_notes(0, [{'row': g['row'], 'marker': g['marker'], 'text': g['text']} for g in comp['guide']], 'guide')

    # sheet 8: settlement creditors (codes 235x are workbook aliases of 321x; kept as legacyCode, never as accounts)
    s8 = reader.read_settlement(wb)
    items = []
    for it in s8['items']:
        items.append({'holder': it['holder'], 'acct': _match_account(it['holder'], chart_accounts),
                      'legacyCode': it['legacyCode'], 'pct': it['pct'], 'credit': it['credit'], 'paid': it['paid'],
                      'balance': it['balance']})
    docs['settlementCreditors'] = {'items': items, 'total': s8['total'], 'columns': s8['columns'], 'source': _src(wb, 8)}
    add_notes(8, reader.notes_of(wb.sheet(8), s8['consumed']))

    # sheet 12: contingent claims
    s12 = reader.read_contingent(wb)
    docs['contingentClaims'] = {'items': s12['items'], 'total': s12['total'], 'columns': s12['columns'], 'source': _src(wb, 12)}
    add_notes(12, reader.notes_of(wb.sheet(12), s12['consumed']))

    # sheet 14: financier funding trace
    s14 = reader.read_financier_uses(wb)
    docs['financierFunding'] = {'items': s14['items'], 'columns': s14['columns'], 'source': _src(wb, 14)}
    add_notes(14, reader.notes_of(wb.sheet(14), s14['consumed']))

    # sheet 15: legal expenses
    s15 = reader.read_legal(wb)
    docs['legalExpenses'] = {'items': s15['items'], 'summary': s15['summary'], 'total': s15['total'], 'source': _src(wb, 15)}
    add_notes(15, reader.notes_of(wb.sheet(15), s15['consumed']))

    # sheet 16: payroll exposure
    s16 = reader.read_payroll(wb)
    docs['payrollExposure'] = {'items': s16['items'], 'groupLabels': s16['groupLabels'], 'total': s16['total'],
                               'columns': s16['columns'], 'source': _src(wb, 16)}
    add_notes(16, reader.notes_of(wb.sheet(16), s16['consumed']))

    # sheet 17: accountant reconciliation (typed snapshots)
    s17 = reader.read_reconciliation(wb)
    docs['accountantReconciliation'] = {'items': s17['sections'], 'typed': True, 'source': _src(wb, 17)}
    add_notes(17, reader.notes_of(wb.sheet(17), s17['consumed']))

    # sheet 18: allocation scenarios (inputs, scenario rows, deposit rows)
    s18 = reader.read_allocation(wb)
    flat = []
    for sc in s18['scenarios']:
        for r in sc['rows']:
            row = dict(r)
            row['scenario'] = sc['id']
            flat.append(row)
    docs['fundingAllocation'] = {'items': flat, 'inputs': s18['inputs'], 'scenarios': [
        {'id': sc['id'], 'title': sc['title'], 'total': sc['total'], 'price': sc['price']} for sc in s18['scenarios']],
        'deposits': s18['deposits'], 'depositsTitle': s18['depositTitle'], 'source': _src(wb, 18)}
    add_notes(18, reader.notes_of(wb.sheet(18), s18['consumed']))

    # sheet 19: funding evidence (grades normalised to A/B/C)
    s19 = reader.read_evidence(wb)
    docs['fundingEvidence'] = {'items': s19['items'], 'summary': s19['summary'], 'source': _src(wb, 19)}
    add_notes(19, reader.notes_of(wb.sheet(19), s19['consumed']))

    # sheet 20: cash sources and uses
    s20 = reader.read_sources_uses(wb)
    docs['cashSourcesUses'] = {'items': s20['items'], 'columns': s20['columns'], 'source': _src(wb, 20)}
    add_notes(20, reader.notes_of(wb.sheet(20), s20['consumed']))

    return docs, notes


def sheet11_notes(wb, close):
    """Narrative of sheet 11 that is not part of the per-year records: general reservations and general needed documents."""
    out = []
    for g in close['general']:
        out.append({'sheet': 11, 'sheetTitle': wb.title(11), 'row': g['row'], 'marker': '•', 'text': g['text'],
                    'kind': 'reservation'})
    for n in close['needed']:
        if not re.fullmatch(r'\d{4}', n['scope']):
            out.append({'sheet': 11, 'sheetTitle': wb.title(11), 'row': n['row'], 'marker': n['scope'], 'text': n['text'],
                        'kind': 'neededDocument'})
    return out
