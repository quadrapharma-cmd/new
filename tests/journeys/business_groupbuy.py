"""Business journeys — group buying: starting a buying group, joining it, the supplier confirming the group price
(J-BUSINESS-31, 32, 33).
Run: python3 tests/journeys/business_groupbuy.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

def market(j, pg):
    close_dialogs(pg); j.nav(pg, 'market'); j.settle(pg, 1200); return pg

def groups_panel(j, pg):
    """Market → 'Company listings' → the 'Group buying' tab (rows inline, with 'Start a group')."""
    market(j, pg)
    chip = pg.locator('.hb-mk [data-mkt=groups]:visible')
    j.check(chip.count(), "no 'Group buying' in the marketplace"); chip.first.click(); pg.wait_for_timeout(700)
    return pg.evaluate("(document.querySelector('.hb-mk')||{}).innerText||''")

def groups_dialog(j, pg):
    """The full Group buying list (progress, Join), opened from a group row or 'See all'."""
    groups_panel(j, pg)
    b = pg.locator('.hb-mk [data-mkall]:visible, .hb-mk [data-mkg]:visible').first
    j.check(b.count(), 'no group is listed under Group buying'); b.click(); pg.wait_for_timeout(900)
    j.check(re.search(r'Group buying|الشراء الجماعي', dlg_text(pg)[:80]), "the group row opens no Group buying list")
    return dlg_text(pg)

def group_card(pg, product):
    return pg.evaluate("p=>{const c=[...document.querySelectorAll('.dbk-ov .gb-card')].find(c=>c.innerText.includes(p));return c?c.innerText:''}", product)

def start_group(j, pg, product, supplier, target='2000', share='500', price='US$ 2.90/kg'):
    groups_panel(j, pg)
    b = pg.locator('.hb-mk [data-mkpost]:visible'); j.check(b.count(), "no 'Start a group' under Group buying"); b.first.click(); pg.wait_for_timeout(800)
    j.check(dlg_open(pg), "'Start a group' opens no form")
    fill_by_label(j, pg, r'Product|المنتج', product); fill_by_label(j, pg, r'Supplier|المورد', re.escape(supplier))
    fill_by_label(j, pg, r'^Target\b|الكمية المستهدفة|الهدف', target); fill_by_label(j, pg, r'Your share|حصتك', share); fill_by_label(j, pg, r'Target price|السعر', price)
    mark = j.toast_mark(pg); dlg_click(j, pg, L('Start group'), 'Start group'); j.settle(pg, 1500)
    return j.toasts_since(pg, mark)

def join_group(j, pg, product, qty):
    t = groups_dialog(j, pg)
    card = pg.locator('.dbk-ov .gb-card', has_text=product).first
    j.check(card.count(), 'the group for %s is not listed in Group buying' % product)
    inp = card.locator('input[type=number]'); j.check(inp.count(), "the group offers no 'Your quantity' to join")
    inp.fill(str(qty)); mark = j.toast_mark(pg)
    card.locator('[data-gjoin]').click(); j.settle(pg, 1500)
    return j.toasts_since(pg, mark)

def parties(j):
    """Live: organiser company, a second factory, the supplier (each a fresh account). Demo: the demo account and a sample supplier."""
    if j.demo:
        pg = j.demo_signin(j.new_page()); return {'page': pg}, None, None, 'Alex Excipients Trading'
    org = live_company_person(j, 'Small Factory One', 'Small Factory One %s' % j.tag)
    mem = live_company_person(j, 'Small Factory Two', 'Small Factory Two %s' % j.tag)
    sup = live_company_person(j, 'Excipient Supplier', 'Alex Excipients %s' % j.tag, sectors=('API & excipients',))
    seed_route(j, sup['co']['id'], 'group_order', sup['id'])
    for p in (org, mem): j.reload(p['page'])
    return org, mem, sup, sup['co']['name']

@journey('J-BUSINESS-31')
def start_buying_group(j):
    """Small factories combine orders to reach a supplier's minimum order and a better price — starting a group."""
    org, mem, sup, supn = parties(j); pg = org['page']; product = 'MCC PH-102 %s' % j.tag
    with j.step("Market → 'Group buying' → 'Start a group': product, supplier, target 2,000 kg, my share 500, target price → 'Start group'"):
        said = start_group(j, pg, product, supn)
        j.check(any(re.search(r'Group started|بدأت المجموعة', t) for t in said), "no 'Group started' confirmation")
        if j.live:
            j.check(j.wait_db("select count(*) from public.deals where type='group' and title like '%%%s%%'" % j.tag, 8) == '1', 'no group deal in the database')
            j.check(j.sql1("select qty from public.deal_members m join public.deals d on d.id=m.deal_id where d.title like '%%%s%%'" % j.tag) in ('500', '500.0', '500.00'), "no deal_members row for the organiser's share")
    with j.step("After reload the group shows product, supplier, organiser, closing date, '500 of 2,000 kg', price and 'Join'"):
        reopen(j, pg); groups_dialog(j, pg); t = group_card(pg, product)
        j.check(t, 'after reload the group is not listed')
        for want, what in ((supn, 'supplier'), ('500', 'progress'), ('2,000', 'target'), ('2.90', 'price'), ('closes', 'closing date')):
            j.check(want in t or (what == 'closing date' and re.search(r'يغلق|closes', t)), 'the group card does not show the %s' % what)
        ui_ok(j, pg, 'Group buying')
    with j.step("Another company sees it with 'Join'"):
        if j.demo: j.skip('the other party exists only in live')
        j.reload(mem['page']); groups_dialog(j, mem['page']); t = group_card(mem['page'], product)
        j.check(t and re.search(r'Join|انضم', t), "another company does not see the group with 'Join'")
        close_dialogs(mem['page'])
    with j.step('The supplier is notified and sees the group as a pending group order'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and type='deal'" % sup['id']) not in ('', '0'), 'the supplier is not notified of the new group')
        sp = sup['page']; j.reload(sp); t = deals_centre(j, sp, r'Received|الواردة'); close_dialogs(sp)
        j.check(product in t, "the group is not in the supplier's Requests & deals")
    with j.step("The organiser sees it in My Listings / the workspace Listings tab"):
        t = workspace(j, pg, 'Listings|%s' % ar('Listings'))
        market(j, pg); pg.locator('.master-tab[data-tab=manage]').click(); pg.wait_for_timeout(800)
        t += pg.evaluate("(document.querySelector('#tab-manage')||{}).innerText||''")
        j.check(product in t, "the organiser's group is in neither the workspace Listings tab nor My Listings")

@journey('J-BUSINESS-32')
def join_buying_group(j):
    """A factory joins an existing buying group with its own quantity."""
    org, mem, sup, supn = parties(j); product = 'MCC PH-102 %s' % j.tag
    if j.live:
        start_group(j, org['page'], product, supn); pg = mem['page']; j.reload(pg)
    else:
        pg = org['page']; start_group(j, pg, product, supn)
    with j.step("'Join' with 'Your quantity (kg)' 700: progress and member count update"):
        said = join_group(j, pg, product, 700)
        j.check(any(re.search(r'joined|انضم', t) for t in said), 'no confirmation of joining')
        groups_dialog(j, pg); t = group_card(pg, product)
        if j.live: j.check('1,200' in t and '2 companies' in t, "progress is not '1,200 of 2,000' with 2 companies: %s" % t[:120])
        else: j.check('1,200' in t, 'progress did not grow by 700: %s' % t[:120])
    with j.step('Change the quantity; then leave the group before the target'):
        card = pg.locator('.dbk-ov .gb-card', has_text=product).first
        j.check(card.locator('button', has_text=re.compile(r'Leave|Change|Edit|غادر|غيّر|عدّل')).count(), "not built: a member can only add more — there is no way to change the quantity or leave the group")
    with j.step("Join with 1,500 so the target is reached: 'Target reached'; the supplier and members are notified"):
        said = join_group(j, pg, product, 1500)
        j.check(any(re.search(r'Target reached|اكتمل الهدف', t) for t in said), "reaching the target does not say 'Target reached'")
        if j.live: j.check(j.wait_db("select status from public.deals where type='group' and title like '%%%s%%'" % j.tag, 6) == 'target_reached', 'the group is not target_reached in the database')

@journey('J-BUSINESS-33')
def confirm_group_price(j):
    """When the target is reached the supplier confirms the group price and every member gets its own order to fulfil."""
    org, mem, sup, supn = parties(j); product = 'MCC PH-102 %s' % j.tag
    pg = org['page']
    with j.step('A group at target (organiser 500 + member 1,500 of 2,000 kg)'):
        start_group(j, pg, product, supn)
        if j.live: j.reload(mem['page']); join_group(j, mem['page'], product, 1500)
        else: join_group(j, pg, product, 1500)
        reopen(j, pg); groups_dialog(j, pg); t = group_card(pg, product); close_dialogs(pg)
        j.check(re.search(r'Target reached|اكتمل', t), 'the group is not at target')
    with j.step("Supplier: 'Confirm group price'"):
        if j.demo:
            groups_dialog(j, pg); card = pg.locator('.dbk-ov .gb-card', has_text=product).first
            b = card.locator('[data-gsim], [data-gconf]'); j.check(b.count(), "the demo cannot play the supplier confirming the group price")
            b.first.click(); j.settle(pg, 1200)
        else:
            sp = sup['page']; j.reload(sp); groups_dialog(j, sp)
            card = sp.locator('.dbk-ov .gb-card', has_text=product).first
            b = card.locator('[data-gconf]'); j.check(b.count(), "the supplier has no 'Confirm group price'")
            b.click(); j.settle(sp, 1500)
            j.check(j.wait_db("select status from public.deals where type='group' and title like '%%%s%%'" % j.tag, 6) == 'confirmed', 'the group is not confirmed in the database')
    with j.step('Every member has its own order with its quantity and the group price; the organiser sees the group as Confirmed'):
        reopen(j, pg); groups_dialog(j, pg); t = group_card(pg, product); close_dialogs(pg)
        j.check(re.search(r'confirmed|تأكيد', t, re.I), 'the organiser does not see the group as confirmed')
        c = deals_centre(j, pg, r'Sent|المرسلة'); close_dialogs(pg)
        if j.live:
            n = j.sql1("select count(*) from public.deals where group_of=(select id from public.deals where type='group' and title like '%%%s%%')" % j.tag)
            j.check(n == '2', 'not one order per member linked to the group (%s)' % n)
        j.check(re.search(L('Order confirmed', 'Accepted', exact=False, extra='مؤكد'), c) and product in c, "the member's own order is not in its Requests & deals")
    with j.step('A group that passes its closing date below target notifies the members and creates no orders'):
        if j.demo: j.skip('the clock cannot be moved in the demo')
        g2 = 'Lactose %s' % j.tag; start_group(j, pg, g2, supn)
        j.sql("update public.deals set lines = jsonb_set(lines,'{by}','\"2026-01-01\"') where type='group' and title like '%%Lactose %s%%'" % j.tag)
        reopen(j, pg); groups_dialog(j, pg); t = group_card(pg, g2)
        j.check(re.search(r'Closed|expired|انتهت|أُغلقت', t), 'a group past its closing date below target is still open to join')

if __name__ == '__main__': main(__file__)
