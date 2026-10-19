"""Community journeys — running a group: deal-room listings, managing members, reports, settings / archive / delete,
pinning, per-group notifications (J-COMMUNITY-13 … 18).
Run: python3 tests/journeys/community_groupadmin.py --target demo|live --lang en|ar --width 1440|390"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _community import *
import _dx

def admin_world(j, gname, private=False, deal=False, members=(), desc='A group for the journey', rules=None):
    """Live: X (signed up through the UI) is the admin of a new group; members are people signed up through the UI."""
    x = j.person('Xavier Admin'); gid = seed_group(j, gname, x['id'], private=private, deal=deal, desc=desc, rules=rules)
    ms = []
    for n in members:
        p = j.person(n); add_member(j, gid, p['id']); ms.append(p)
    j.reload(x['page'])
    return x, gid, ms

def member_row(pg, name):
    return pg.locator('#tab-members .member-row, #managePanel .member-row').filter(has_text=name).first

def row_action(j, pg, row, pattern, what):
    j.check(row.count(), 'no member row')
    b = row.locator('.action-btn, button:has-text("⋯")').first
    j.check(b.count(), 'not built: no ⋯ on the member row (%s)' % what); b.click(); pg.wait_for_timeout(400)
    it = row.locator('.dd-item, .ctx-item').filter(has_text=re.compile(pattern, re.I))
    if not (it.count() and it.first.is_visible()):
        names = [t.strip() for t in row.locator('.dd-item, .ctx-item').all_inner_texts()]
        j.notbuilt('no "%s" in the member menu (items: %s)' % (what, ', '.join(names)))
    mark = j.toast_mark(pg); it.first.click(); pg.wait_for_timeout(700); j.dead_end(pg, mark, what)

@journey('J-COMMUNITY-13')
def deal_room_listings(j):
    """In a deal room, members trade: a supplier lists an offer and buyers enquire, so deals start from the group."""
    t = j.tag[:4]; title = 'Metformin HCl USP %s' % t
    if j.live:
        v = j.person('Vivian Zhou'); h = j.person('Hany Buyer'); o = j.person('Omar Outsider')
        cv = seed_company(j, v['id'], 'Shandong Hexa Biotech %s' % t, sectors=('API & excipients',))
        ch = seed_company(j, h['id'], 'Haytham Buyers %s' % t)
        xx = seed_user(j, 'Dr. Xena Admin'); gname = 'API Sourcing Deal Room %s' % t
        gid = seed_group(j, gname, xx, deal=True, desc='Buyers and suppliers of APIs')
        add_member(j, gid, v['id']); add_member(j, gid, h['id'])
        pg = v['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); gname = 'API Sourcing & Supply'
    with j.step("V opens the deal room → Listings → 'Post RFQ / offer': Supply, Metformin HCl USP, 500 kg, price, CEP — it appears in Listings"):
        groups_page(j, pg); open_card(j, pg, gname); gd_tab(j, pg, 'listings', 'Listings')
        b = j.find(pg, r'Post RFQ|Add listing|offer|إضافة|نشر', scope='#gpBox', kinds='button,[data-gpa]'); j.check(b, 'no way to add a listing')
        b.click(); pg.wait_for_timeout(700); j.check(dlg_open(pg), 'Add listing opens nothing')
        fill_by_label(j, pg, r'Type|النوع', r'sale|For sale|للبيع')
        fill_by_label(j, pg, r'Product|المنتج', title)
        fill_by_label(j, pg, r'Details|التفاصيل', '500 kg, CIF Alexandria, CEP available, CoA with each batch')
        fill_by_label(j, pg, r'Price|السعر', '$5.80/kg', required=False)
        dlg_click(j, pg, r'Post to the group|Post|نشر', 'Post to the group'); j.settle(pg, 1200)
        j.check(title in gd_pane(pg, 'listings'), 'the new listing does not appear in Listings')
    with j.step('Reload: the listing is still in the Listings tab'):
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname); txt = gd_tab(j, pg, 'listings')
        j.check(title in txt, 'after reload the listing is gone')
        if j.live: j.check(cv['name'] in txt, "the listing does not show V's company")
    with j.step("H opens Listings and enquires on V's listing: a deal starts in the Deals center"):
        if j.live:
            ph = h['page']; j.reload(ph); groups_page(j, ph); open_card(j, ph, gname); gd_tab(j, ph, 'listings')
        else:
            ph = pg; mine_title, title = title, 'Neomycin Sulfate EP'
        card = ph.locator('#gpBox [data-pane=listings] .lcard, #gpBox [data-pane=listings] [class*=card]').filter(has_text=title).first
        j.check(card.count(), 'the listing is not in the buyer\'s Listings tab')
        q = card.locator('button').filter(has_text=re.compile(r'Contact|Quote|Enquir|Request|تواصل|عرض سعر|استفسار', re.I))
        j.check(q.count(), 'no enquiry button on the listing'); q.first.click(); j.settle(ph, 1200)
        if dlg_open(ph):
            ta = ph.locator('.dbk-ov textarea, .modal-bg.show textarea')
            if ta.count(): ta.first.fill('Please quote 500 kg CIF Alexandria')
            dlg_click(j, ph, r'Send|Request|إرسال|أرسل|طلب', 'Send enquiry'); j.settle(ph, 1200)
        page = ph.evaluate("document.body.getAttribute('data-page')")
        j.check(page != 'messages', 'the enquiry only opens Messages — no deal (request / quote) is started')
        if j.live: j.check(j.wait_db("select count(*) from public.deals where title ilike '%%Metformin%%%s%%'" % t, 6) >= '1', 'no deals row for the enquiry')
    with j.step('V is notified and sees the enquiry in the Deals center'):
        if j.demo: j.skip('the supplier exists only in live')
        j.reload(pg); open_notif(j, pg, r'quote|request|enquir|طلب|عرض', 'enquiry')
    with j.step("An outsider cannot enquire without joining (public room: reads, Join to enquire)"):
        if j.demo: j.skip('checked in live with a second account')
        po = o['page']; j.reload(po); groups_page(j, po); open_card(j, po, gname)
        txt = gd_tab(j, po, 'listings') if 'listings' in gd_tabs(po) else ''
        j.check(not re.search(r'Contact|Quote|تواصل', txt) or re.search(r'Join to|انضم', txt), 'an outsider can enquire without joining')
    with j.step('V closes the listing: it leaves the tab'):
        groups_page(j, pg); open_card(j, pg, gname); gd_tab(j, pg, 'listings')
        if j.demo: title = mine_title                                    # the listing V posted in step 1
        card = pg.locator('#gpBox [data-pane=listings] .lcard, #gpBox [data-pane=listings] [class*=card]').filter(has_text=title).first
        c = card.locator('button, [data-gpa]').filter(has_text=re.compile(r'Close|Remove|Delete|إغلاق|حذف', re.I))
        j.check(c.count(), 'not built: no Close on my own listing'); c.first.click(); pg.wait_for_timeout(500); confirm(j, pg); j.settle(pg, 900)
        j.check(title not in gd_pane(pg, 'listings'), 'the closed listing is still listed')

@journey('J-COMMUNITY-14')
def manage_members(j):
    """A group admin keeps the member list healthy: promote helpers, demote, remove bad actors."""
    t = j.tag[:4]
    if j.live:
        gname = 'Managed Group %s' % t
        x, gid, (m1, m2) = admin_world(j, gname, members=('Mariam Helper', 'Maged Spammer')); pg = x['page']
        n1, n2 = 'Mariam Helper', 'Maged Spammer'
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'; n1, n2 = 'Sara El-Amin', 'Omar Khaled'
    with j.step("X opens G → Manage → Members: G's real members, with search"):
        groups_page(j, pg); open_card(j, pg, gname); txt = manage(j, pg, 'members')
        j.check(n1 in txt and n2 in txt, 'the Manage member list does not show the members %s, %s' % (n1, n2))
        if j.live: j.check(not re.search(r'412|Alia Mourad|Vivian', txt), 'the Manage member list shows sample members')
        hn = gd_members_n(pg); mt = re.search(r'Members \(([\d,]+)\)|الأعضاء \(([\d,]+)\)', txt)
        j.check(not mt or num(mt.group(0)) == hn, 'Manage says %s members, the header %s' % (mt.group(0) if mt else '', hn))
        s = pg.locator('#tab-members input:visible')
        j.check(s.count(), 'not built: no member search in Manage (only a "Search members" label)')
    with j.step('Promote M1 to admin: the role badge changes now and after reload'):
        row_action(j, pg, member_row(pg, n1), r'Promote|ترقية', 'Promote')
        j.check(re.search(r'Admin|مشرف|مدير', member_row(pg, n1).inner_text(), re.I) and not re.search(r'Sub-Admin|^\W*Member', member_row(pg, n1).inner_text(), re.I | re.M), 'the role badge did not change')   # the pill is shown in capitals
        if j.live: j.check(j.wait_db("select role from public.group_members where group_id=%d and user_id='%s'" % (gid, m1['id']), 5, want='admin') == 'admin', 'group_members.role is not admin')
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname); manage(j, pg, 'members')
        j.check(re.search(r'Admin|مشرف|مدير', member_row(pg, n1).inner_text(), re.I) and not re.search(r'^\W*Member', member_row(pg, n1).inner_text(), re.I | re.M), 'after reload M1 is not admin')
    with j.step('M1 sees Manage while admin'):
        if j.demo: j.skip('M1 exists only in live')
        p1 = m1['page']; j.reload(p1); groups_page(j, p1); open_card(j, p1, gname)
        j.check(p1.locator('#groupDetail .btn-manage:visible').count(), 'the promoted admin has no Manage')
    with j.step('Demote M1: back to member (now and after reload); M1 loses Manage'):
        row_action(j, pg, member_row(pg, n1), r'Demote|تخفيض|إلغاء الإشراف', 'Demote')
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname); manage(j, pg, 'members')
        j.check(not re.search(r'Admin|مشرف عام', member_row(pg, n1).inner_text(), re.I), 'after reload M1 is still admin')
        if j.live:
            j.check(j.wait_db("select role from public.group_members where group_id=%d and user_id='%s'" % (gid, m1['id']), 5, want='member') == 'member', 'group_members.role is not member')
            j.reload(p1); groups_page(j, p1); open_card(j, p1, gname); j.check(not p1.locator('#groupDetail .btn-manage:visible').count(), 'the demoted member still has Manage')
    with j.step('Remove M2 (confirm): gone from the list, count -1'):
        hn = gd_members_n(pg); row_action(j, pg, member_row(pg, n2), r'Remove|إزالة', 'Remove from group'); confirm(j, pg); j.settle(pg, 900)
        j.check(not member_row(pg, n2).count(), 'the removed member is still listed')
        j.check(gd_members_n(pg) == hn - 1, 'the header count went %s → %s' % (hn, gd_members_n(pg)))
        if j.live: j.check(j.wait_db("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, m2['id']), 5, want='0') == '0', 'the group_members row is still there')
    with j.step('M2 opens G: no composer, and is told'):
        if j.demo: j.skip('M2 exists only in live')
        p2 = m2['page']; j.reload(p2); groups_page(j, p2); open_card(j, p2, gname)
        j.check(not has_composer(p2), 'the removed member can still post')
        j.check(notif_rows(j, m2['id'], extra=' and group_id=%d' % gid) >= 1, 'the removed member is not told')
    with j.step('A non-admin (M1) cannot remove anyone; the database refuses'):
        if j.demo: j.skip('M1 exists only in live')
        manage_btn = p1.locator('#groupDetail .btn-manage:visible').count(); j.check(not manage_btn, 'a non-admin has Manage')
        err = p1.evaluate("([g,u])=>dxLive.sb.from('group_members').delete().eq('group_id',g).eq('user_id',u).select()" + ".then(r=>r.error?{code:r.error.code,message:r.error.message}:((r.data||[]).length?null:{code:'0rows',message:'0 rows'}))", [gid, x['id']])
        j.check(err and j.sql1("select count(*) from public.group_members where group_id=%d and user_id='%s'" % (gid, x['id'])) == '1', 'a non-admin removed the admin')
    with j.step('The last admin cannot be removed or demoted (clear message)'):
        if j.demo: j.skip('checked in live (the demo group has a sub-admin)')
        me_row = member_row(pg, 'Xavier'); items = []
        if me_row.count() and me_row.locator('.action-btn').count():
            me_row.locator('.action-btn').first.click(); pg.wait_for_timeout(300); items = me_row.locator('.dd-item').all_inner_texts()
        j.check(not any(re.search(r'Demote|Remove|إزالة', i) for i in items), 'the last admin can demote / remove themself')
        err = pg.evaluate("([g,u])=>dxLive.sb.from('group_members').update({role:'member'}).eq('group_id',g).eq('user_id',u).select()" + ".then(r=>r.error?{code:r.error.code,message:r.error.message}:null)", [gid, x['id']])
        j.check(err and j.sql1("select role from public.group_members where group_id=%d and user_id='%s'" % (gid, x['id'])) == 'admin', 'the database lets the last admin demote themself')

@journey('J-COMMUNITY-15')
def group_reports(j):
    """Members flag harmful posts and the admin deals with them so the group stays useful."""
    t = j.tag[:4]; spam = 'Ready-made CTD dossiers 50%% off %s' % t; spam2 = 'Cheap consultancy ad %s' % t
    if j.live:
        gname = 'Reported Group %s' % t
        x, gid, (m,) = admin_world(j, gname, members=('Mona Member',))
        z = seed_user(j, 'Zaki Spammer'); add_member(j, gid, z)
        s1 = seed_gpost(j, z, gid, spam, 600); s2 = seed_gpost(j, z, gid, spam2, 300)
        pm = m['page']; j.reload(pm); pg = x['page']
    else:
        pm = pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'; spam = 'For teams filing in Egypt and Saudi Arabia'; spam2 = None
    with j.step("M opens S's menu → Report → reason → send: 'Reported — the admins will check it'"):
        groups_page(j, pm); open_card(j, pm, gname)
        menu(j, pm, gpost(j, pm, spam), r'Report|إبلاغ', 'Report')
        if dlg_open(pm):
            r = pm.locator('.dbk-ov input[type=radio], .dbk-ov [role=radio], .dbk-ov label').first
            if r.count(): r.click()
            ta = pm.locator('.dbk-ov textarea'); ta.count() and ta.first.fill('Selling dossiers that are not theirs')
            dlg_click(j, pm, r'Report|Send|Submit|إبلاغ|إرسال|أرسل', 'Send report')
        pm.wait_for_timeout(600)
        ts = ' '.join(pm.evaluate('window.__jt||[]')[-3:]); j.check(re.search(r'Report|admin|إبلاغ|بلاغ|مشرف|شكر', ts), 'no "reported" confirmation (%s)' % ts[:100])
        if j.live: j.check(j.wait_db("select count(*) from public.group_post_reports where post_id=%d and reporter='%s'" % (s1, m['id']), 5) == '1', 'no group_post_reports row')
    with j.step('M reports S again: refused politely'):
        items = menu_items(pm, gpost(j, pm, spam))
        if not any(re.search(r'Reported|تم الإبلاغ', i) for i in items):
            cut = toast_cut(pm); menu(j, pm, gpost(j, pm, spam), r'Report|إبلاغ', 'Report again')
            if dlg_open(pm): dlg_click(j, pm, r'Report|Send|Submit|إبلاغ|إرسال|أرسل', 'Send report')
            pm.wait_for_timeout(600); ts = ' '.join(toasts_after(pm, cut))
            j.check(re.search(r'already|before|سبق|بالفعل', ts, re.I), 'a second report gives no "already reported" message (menu: %s; toasts: %s)' % (', '.join(items), ts[:80]))
        if j.live: j.check(j.sql1("select count(*) from public.group_post_reports where post_id=%d and reporter='%s'" % (s1, m['id'])) == '1', 'a second report row was stored')
    with j.step('X opens Manage → Reports: the report with post text, author, reason and count; a badge shows it'):
        if j.live: j.reload(pg)
        groups_page(j, pg); open_card(j, pg, gname); txt = manage(j, pg, 'reports')
        j.check(spam[:25] in txt, 'the reported post is not in Reports')
        j.check(re.search(r'Zaki|Faisal', txt), 'Reports does not show the author')
        badge = pg.evaluate("((document.querySelector('#managePanel .ptab-badge')||{}).innerText||'').trim()")
        j.check(badge and badge != '0', 'no unread-reports badge')
    with j.step('X removes S: gone for every member and from the list; Z is told'):
        r = pg.locator('#tab-reports .mod-item, #tab-reports [class*=mod-]').filter(has_text=spam[:25]).first
        b = r.locator('.mod-btn.remove, button').filter(has_text=re.compile(r'Remove|إزالة|حذف', re.I))
        j.check(b.count(), 'no Remove on the report'); b.first.click(); pg.wait_for_timeout(500); confirm(j, pg); j.settle(pg, 1000)
        j.check(spam[:25] not in manage(j, pg, 'reports'), 'the report stays in the list')
        gd_tab(j, pg, 'disc'); j.check(not any(spam[:25] in p['text'] for p in gposts(pg)), 'the removed post is still in the Discussion')
        if j.live:
            j.check(j.wait_db("select count(*) from public.posts where id=%d" % s1, 5, want='0') == '0', 'the posts row is still there')
            j.reload(pm); groups_page(j, pm); open_card(j, pm, gname); j.check(not any(spam[:25] in p['text'] for p in gposts(pm)), 'M still sees the removed post')
            j.check(notif_rows(j, z, extra=" and created_at > now() - interval '5 minutes'") >= 1, 'Z is not told the post was removed')
    with j.step('Another report → Dismiss: the post stays, the report closes'):
        if j.demo: j.skip('the demo has one report queue; checked in live')
        menu(j, pm, gpost(j, pm, spam2), r'Report|إبلاغ', 'Report')
        if dlg_open(pm): dlg_click(j, pm, r'Report|Send|Submit|إبلاغ|إرسال|أرسل', 'Send report')
        j.reload(pg); groups_page(j, pg); open_card(j, pg, gname); manage(j, pg, 'reports')
        r = pg.locator('#tab-reports .mod-item, #tab-reports [class*=mod-]').filter(has_text=spam2[:20]).first
        b = r.locator('button').filter(has_text=re.compile(r'Dismiss|تجاهل|رفض', re.I)); j.check(b.count(), 'no Dismiss'); b.first.click(); j.settle(pg, 900)
        j.check(j.wait_db("select status from public.group_post_reports where post_id=%d" % s2, 5) == 'dismissed', 'the report is not dismissed')
        j.check(j.sql1("select count(*) from public.posts where id=%d" % s2) == '1', 'dismissing removed the post')

@journey('J-COMMUNITY-16')
def group_settings(j):
    """A group admin can change what the group is and close it when it is done."""
    t = j.tag[:4]; newdesc = 'Updated scope: EDA variations and renewals %s' % t
    if j.live:
        gname = 'Settings Group %s' % t
        x, gid, (m,) = admin_world(j, gname, members=('Mona Member',)); pg = x['page']
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'
    with j.step('Manage → Settings: change the description and save — it persists after reload and members see it in About'):
        groups_page(j, pg); open_card(j, pg, gname); manage(j, pg, 'settings')
        ta = pg.locator('#tab-settings textarea:visible').first; j.check(ta.count(), 'no description field in Settings')
        ta.fill(newdesc); b = pg.locator('#tab-settings button:visible').filter(has_text=re.compile(r'Save|حفظ')).first
        mark = j.toast_mark(pg); b.click(); j.settle(pg, 1000); j.dead_end(pg, mark, 'Save Changes')
        if j.live: j.check(j.wait_db("select count(*) from public.groups where id=%d and description=$q$%s$q$" % (gid, newdesc), 5) == '1', 'the description is not saved in the database')
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname)
        j.check(newdesc in gd_tab(j, pg, 'about'), 'after reload About does not show the new description')
        if j.live:
            pm = m['page']; j.reload(pm); groups_page(j, pm); open_card(j, pm, gname)
            j.check(newdesc in gd_tab(j, pm, 'about'), 'a member does not see the new description')
    with j.step('Settings can change the rules, the privacy (Public → Private) and who may post'):
        txt = manage(j, pg, 'settings')
        missing = [w for w, p in (('rules', r'Rules|قواعد'), ('privacy', r'Privacy|Private|الخصوصية|خاصة'), ('posting permission', r'post|النشر'))
                   if not re.search(p, txt.replace('Save Changes', ''), re.I)]
        j.check(not missing, 'not built: Settings has no %s' % ', '.join(missing))
    with j.step('Archive the group (confirm): read-only, marked Archived, hidden from discovery; members still read'):
        manage(j, pg, 'members')
        b = j.find(pg, r'Archive|أرشفة', scope='#managePanel', kinds='button'); j.check(b, 'no Archive')
        mark = j.toast_mark(pg); b.click(); pg.wait_for_timeout(600); confirm(j, pg, r'Archive|Yes|Confirm|أرشفة|نعم|تأكيد'); j.settle(pg, 1000); j.dead_end(pg, mark, 'Archive')
        if j.live: j.check(j.has_column('groups', 'archived') or j.has_column('groups', 'archived_at') or j.has_column('groups', 'status'), 'not built: groups has no archived state in the database')
        groups_page(j, pg); c = next((c for c in cards(pg) if c['title'] == gname), None)
        j.check(c and re.search(r'Archived|مؤرشف', c['text'], re.I), 'the archived group is not marked Archived')
        open_card(j, pg, gname); j.check(not has_composer(pg), 'an archived group still has a composer')
    with j.step('Delete a test group after a strong confirmation: gone for everyone'):
        if j.live:
            dname = 'Delete Me %s' % t; did = seed_group(j, dname, x['id']); j.reload(pg)
        else: dname = 'Regulatory Affairs Egypt'
        groups_page(j, pg); open_card(j, pg, dname); manage(j, pg, 'members')
        b = j.find(pg, r'Delete Forever|Delete|حذف', scope='#managePanel', kinds='button'); j.check(b, 'no Delete')
        b.click(); pg.wait_for_timeout(600)
        inp = pg.locator('#deleteConfirmInput:visible, #deleteModal input:visible')
        j.check(inp.count(), 'Delete asks for no strong confirmation'); inp.first.fill(dname); pg.wait_for_timeout(300)
        go = pg.locator('#deleteModal button:visible').filter(has_text=re.compile(r'Delete|حذف')).last
        mark = j.toast_mark(pg); go.click(); j.settle(pg, 1200); j.dead_end(pg, mark, 'Delete Forever')
        groups_page(j, pg); j.check(dname not in card_titles(pg), 'the deleted group is still listed')
        if j.live: j.check(j.wait_db("select count(*) from public.groups where id=%d" % did, 5, want='0') == '0', 'the groups row is still there')

@journey('J-COMMUNITY-17')
def pin_post(j):
    """An admin pins an important post (rules, upcoming EDA deadline) so every member sees it first."""
    t = j.tag[:4]
    if j.live:
        gname = 'Pinned Group %s' % t
        x, gid, (m,) = admin_world(j, gname, members=('Mona Member',)); pg = x['page']
        p1 = seed_gpost(j, x['id'], gid, 'EDA deadline 30 November %s' % t, 3600); p2 = seed_gpost(j, m['id'], gid, 'Second notice %s' % t, 1800)
        seed_gpost(j, m['id'], gid, 'Newest chatter %s' % t, 60)
        a, b = 'EDA deadline 30 November %s' % t, 'Second notice %s' % t
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'
        a, b = 'For teams filing in Egypt and Saudi Arabia', 'Zone IVb stability for a cosmetic serum'
    with j.step('X opens a post menu → Pin: the post shows first with a Pinned label'):
        groups_page(j, pg); open_card(j, pg, gname)
        menu(j, pg, gpost(j, pg, a), r'Pin|ثب\u0651?ت|تثبيت', 'Pin'); j.settle(pg, 900)
        ps = gposts(pg); j.check(a in ps[0]['text'] and re.search(r'Pinned|مثب', ps[0]['all']), 'the pinned post is not first with a Pinned label')
        j.check(sum(1 for p in ps if re.search(r'📌 Pinned|📌 مثب', p['all'])) == 1, 'more than one post is pinned')
        if j.live: j.check(j.wait_db("select pinned_post_id from public.groups where id=%d" % gid, 5) == str(p1), 'groups.pinned_post_id is not the post')
    with j.step('After reload, and for a member, the pinned post is first'):
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname)
        j.check(a in gposts(pg)[0]['text'], 'after reload the pinned post is not first')
        if j.live:
            pm = m['page']; j.reload(pm); groups_page(j, pm); open_card(j, pm, gname)
            j.check(a in gposts(pm)[0]['text'], 'a member does not see the pinned post first')
    with j.step('X pins another post: only that one is pinned'):
        menu(j, pg, gpost(j, pg, b), r'Pin|ثب\u0651?ت|تثبيت', 'Pin'); j.settle(pg, 900)
        ps = gposts(pg); j.check(b in ps[0]['text'], 'the newly pinned post is not first')
        j.check(sum(1 for p in ps if re.search(r'📌 Pinned|📌 مثب', p['all'])) == 1, 'two posts are pinned')
    with j.step('X unpins: no post is pinned'):
        menu(j, pg, gpost(j, pg, b), r'Unpin|ألغ|إلغاء التثبيت', 'Unpin'); j.settle(pg, 900)
        j.check(not any(re.search(r'📌 Pinned|📌 مثب', p['all']) for p in gposts(pg)), 'a post is still pinned')
        if j.live: j.check(j.wait_db("select coalesce(pinned_post_id::text,'none') from public.groups where id=%d" % gid, 5, want='none') == 'none', 'groups.pinned_post_id is not cleared')
    with j.step('A non-admin has no Pin, and the RPC refuses them'):
        if j.demo:
            groups_page(j, pg); open_card(j, pg, 'API Sourcing & Supply')
            items = menu_items(pg, pg.locator('#gpBox .post').nth(1))
            j.check(not any(re.search(r'^\W*(Pin|📌 ثب)', i) for i in items), 'a non-admin member has Pin (%s)' % ', '.join(items)); return
        pm = m['page']; j.reload(pm); groups_page(j, pm); open_card(j, pm, gname)
        items = menu_items(pm, gpost(j, pm, b)); j.check(not any(re.search(r'^\W*(Pin|📌 ثب)', i) for i in items), 'a member has Pin (%s)' % ', '.join(items))
        err = pm.evaluate("([g,p])=>dxLive.sb.rpc('group_pin_post',{p_group:g,p_post:p})" + _dx.ERR, [gid, p2])
        j.check(err and j.sql1("select coalesce(pinned_post_id::text,'none') from public.groups where id=%d" % gid) == 'none', 'a member pinned a post through the RPC')

@journey('J-COMMUNITY-18')
def group_notifications(j):
    """A member controls how much a group interrupts her, so she keeps groups that matter without noise."""
    t = j.tag[:4]
    if j.live:
        gname = 'Noisy Group %s' % t
        x, gid, (m, o) = admin_world(j, gname, members=('Mona Member', 'Ola Poster')); pg = m['page']; j.reload(pg)
    else:
        pg = j.demo_signin(j.new_page()); gname = 'Regulatory Affairs Egypt'
    def nbtn():
        b = pg.locator('#groupDetail .group-actionbar button:visible').filter(has_text=re.compile(r'Notifications|الإشعارات|إشعارات'))
        j.check(b.count(), 'no Notifications control in the group'); return b.first
    with j.step('Open G → Notifications → off: the control shows off'):
        groups_page(j, pg); open_card(j, pg, gname); before = nbtn().inner_text()
        j.act(pg, nbtn(), 'Notifications', lambda: nbtn().inner_text() != before, expect='the control to show notifications off')
        j.check(re.search(r'off|🔕|إيقاف|متوقفة', nbtn().inner_text(), re.I), 'the control does not say off (%s)' % nbtn().inner_text())
    with j.step('The setting persists after reload (stored server-side in live)'):
        reopen(j, pg); groups_page(j, pg); open_card(j, pg, gname)
        j.check(re.search(r'off|🔕|إيقاف|متوقفة', nbtn().inner_text(), re.I), 'after reload notifications are on again')
        if j.live:
            cols = j.sql1("select string_agg(table_name||'.'||column_name, ',') from information_schema.columns where table_schema='public' and column_name ~ '(notif|mute)' and table_name ~ 'group'")
            j.check(cols, 'not built: no per-group notification setting in the database')
    with j.step('With off, a new post by another member gives no notification; with on, one that opens the post'):
        if j.demo: j.skip('the other member exists only in live')
        po = o['page']; j.reload(po); groups_page(j, po); open_card(j, po, gname); gcompose(j, po, 'Muted post %s' % t)
        time.sleep(2); j.check(notif_rows(j, m['id'], extra=' and group_id=%d' % gid) == 0, 'a notification arrived while off')
        nbtn().click(); pg.wait_for_timeout(800); gcompose(j, po, 'Loud post %s' % t)
        j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and group_id=%d" % (m['id'], gid), 6) >= '1', 'no notification for a new post while on')

if __name__ == '__main__': main(__file__)
