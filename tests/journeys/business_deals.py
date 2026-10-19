"""Business journeys — requests & deals between companies: one RFQ to several suppliers, supplier qualification, licensing a
dossier, a job application, a purchase from RFQ to rated order, declining and withdrawing, a consulting service, documents
inside a deal, deal privacy (J-BUSINESS-03, 07, 08, 11, 26, 27, 28, 29, 30).
Run: python3 tests/journeys/business_deals.py --target demo|live --lang en|ar --width 1440|390 --out DIR"""
import re, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _j import journey, main, PW
from _biz import *
import _dx

@journey('J-BUSINESS-26')
def purchase_lifecycle(j):
    """Buyer and supplier take a purchase from request for quotation to delivered, closed and rated order inside Drugbox."""
    b, s, sup, prod = buyer_and_supplier(j, 'Supplier API', 'Metformin HCl')
    pg = b['page']; title = prod or 'Paracetamol 500 mg'
    with j.step("Buyer: supplier page → 'Request a quote' (500 kg, Cairo, CIF, needed-by, message) → 'Send request'"):
        said = request_quote(j, pg, sup, prod)
        j.check(any(re.search(r'Sent to|أُرسل|تم الإرسال', t) for t in said), 'no confirmation that the request was sent')
        if j.live:
            j.check(live_deal(j, title, 'type||status') == 'quotesent', 'no quote deal (sent) in the database')
        ui_ok(j, pg, 'after sending')
    with j.step("Supplier is notified; 'Your move' in Received; 'Send quote' (US$ 5.40 per kg, 14 days, CIF, 3 weeks)"):
        if j.live:
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='deal'" % s['id'], 6) not in ('', '0'), 'the supplier got no notification')
            sp = s['page']; j.reload(sp); t = deals_centre(j, sp, r'Received|الواردة')
            j.check(title in t and re.search(r'Your move|دورك', t), "the supplier's Received list does not show the request as 'Your move'")
            close_dialogs(sp)
        their_move(j, pg, s, title, 'Send quote', {r'Price|السعر': 'US$ 5.40 per kg', r'Valid for|صالح': '14 days', r'Lead time|مدة': '3 weeks'})
        t = status_of(j, pg, title)
        j.check(re.search(r'Quote received|وصل العرض|عرض', t) and re.search(r'US\$\s*\d', t), 'the buyer does not see the quote with its price')
        if j.live: j.check(live_deal(j, title) == 'quoted', 'the deal is not quoted in the database')
    with j.step("Buyer: 'Counter-offer' (target price, note) → the supplier sees it and revises"):
        open_deal(j, pg, title); deal_act(j, pg, 'Counter-offer', {r'target price|السعر المستهدف|سعرك': 'US$ 4.90 per kg', r'Note|ملاحظة': 'Volume order, 6 lots/year'}); close_dialogs(pg)
        if j.live: j.check(live_deal(j, title) == 'countered', 'the counter-offer is not recorded (status %s)' % live_deal(j, title))
        their_move(j, pg, s, title, 'Send quote', {r'Price|السعر': 'US$ 5.10 per kg', r'Valid for|صالح': '14 days'})
        t = status_of(j, pg, title); j.check(re.search(r'5\.10|4\.90|20\.', t) or j.demo, 'the revised price is not shown to the buyer')
    with j.step("Buyer: 'Accept quote'; supplier: 'Confirm order' → 'Mark shipped' (AWB)"):
        open_deal(j, pg, title); deal_act(j, pg, 'Accept quote'); close_dialogs(pg)
        if j.live: j.check(live_deal(j, title) == 'accepted', 'accept did not reach the database (%s)' % live_deal(j, title))
        their_move(j, pg, s, title, 'Confirm order')
        their_move(j, pg, s, title, 'Mark shipped', {r'tracking|الشحنة|التتبع': 'AWB 4412-99'})
        t = status_of(j, pg, title); j.check(re.search(r'Shipped|تم الشحن|شُحن', t), 'the buyer does not see the order as shipped')
    with j.step("Buyer: 'Confirm received' (on time) → 'Rate supplier' (5 stars, comment): the deal is Closed for both"):
        open_deal(j, pg, title); deal_act(j, pg, 'Confirm received', {r'on time|في الموعد': r'yes|نعم'}); close_dialogs(pg)
        open_deal(j, pg, title); deal_act(j, pg, 'Rate supplier', {r'Rating|التقييم': '5', r'Comment|تعليق': 'Full CEP, on time %s' % j.tag}); close_dialogs(pg)
        t = status_of(j, pg, title); j.check(re.search(r'Closed|مغلق|مكتمل', t), 'the deal is not Closed for the buyer')
        if j.live:
            j.check(live_deal(j, title) == 'closed', 'the deal is not closed in the database')
            j.check(j.sql1("select string_agg(e.action,'>' order by e.id) from public.deal_events e join public.deals d on d.id=e.deal_id where d.title like $q$%%%s%%$q$" % title).startswith('sent>quote>counter>'), 'the deal history is incomplete')
    with j.step('The thread shows the full history (who, what, when, price per round)'):
        t = open_deal(j, pg, title); close_dialogs(pg)
        j.check(len(re.findall(r'\d{1,2} \S+ \d{4}|\d{4}-\d{2}-\d{2}', t.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')))) >= 6, 'the thread does not list every step with its date')
        j.check(re.search(r'4\.90', t), 'the counter-offer price is missing from the history')
    with j.step("After reload, the supplier's Reviews tab shows the review and the track record counts the order"):
        reopen(j, pg); directory(j, pg); open_card(j, pg, sup)
        t = company_tab(j, pg, 'Reviews|%s' % ar('Reviews'), 'Reviews')
        j.check(('Full CEP, on time %s' % j.tag) in t, "the review does not appear on the supplier's Reviews tab")
        j.check(re.search(r'1 (completed )?orders?|طلب', j.text(pg)), 'the track record does not count the completed order')
    with j.step('Live: a direct UPDATE of the deal by the buyer is refused; a third company cannot read it'):
        if j.demo: j.skip('database checks are live only')
        r = pg.evaluate("t=>dxLive.sb.from('deals').update({status:'quoted',title:'forged'}).like('title','%'+t+'%')" + _dx.ERR, title)
        j.check(live_deal(j, title) == 'closed', 'the buyer changed the deal directly: %s' % r)
        x = j.person('Third Company'); n = x['page'].evaluate("t=>dxLive.sb.from('deals').select('id').like('title','%'+t+'%').then(r=>(r.data||[]).length)", title)
        j.check(n == 0, 'a third account can read the deal')

@journey('J-BUSINESS-27')
def decline_and_withdraw(j):
    """Either side can end a negotiation cleanly (decline with a reason or withdraw) and both know why."""
    b, s, sup, prod = buyer_and_supplier(j, 'Out Of Stock API', 'Atorvastatin calcium')
    pg = b['page']
    with j.step('Two open quote requests between buyer and supplier'):
        if j.live:
            request_quote(j, pg, sup, prod, qty='200'); request_quote(j, pg, sup, 'Something else', qty='50', msg='Second request — samples')
            j.check(j.sql1("select count(*) from public.deals where to_company_id=%s" % s['co']['id']) == '2', 'the two requests are not both in the database')
            t1, t2 = j.sql("select title from public.deals where to_company_id=%s order by id" % s['co']['id']).split('\n')
            sp = s['page']
        else:
            # the demo account is the supplier of the requests Quadra Pharm received, and the buyer of the one it sends
            request_quote(j, pg, sup, None, qty='50', msg='Second request — samples')
            t1 = pg.evaluate("(dxDeals.all().find(d=>d.type==='quote'&&d.to&&d.to.slug==='quadra-pharm'&&d.status==='sent')||{}).title")
            t2 = pg.evaluate("(dxDeals.all().filter(d=>d.type==='quote'&&d.to&&d.to.slug==='medsinia-industries').pop()||{}).title")
            j.check(t1 and t2, 'the demo has no received request to decline and sent request to withdraw')
            sp = pg
    with j.step("Supplier: 'Decline' request 1 with reason 'Out of stock until March'"):
        if j.live: j.reload(sp)
        open_deal(j, sp, t1, r'Received|الواردة'); deal_act(j, sp, 'Decline', {r'Reason|السبب': 'Out of stock until March'}); close_dialogs(sp)
        if j.live: j.check(j.wait_db("select status from public.deals where to_company_id=%s and title=$q$%s$q$" % (s['co']['id'], t1), 6) == 'declined', 'request 1 is not declined in the database')
    with j.step("Buyer: 'Withdraw' request 2"):
        if j.live: j.reload(pg)
        open_deal(j, pg, t2, r'Sent|المرسلة'); deal_act(j, pg, 'Withdraw'); close_dialogs(pg)
        if j.live: j.check(j.wait_db("select status from public.deals where to_company_id=%s and title=$q$%s$q$ order by id desc limit 1" % (s['co']['id'], t2), 6) == 'cancelled', 'request 2 is not cancelled in the database')
    with j.step('Both see the final status and the reason, with no further action buttons; the other side is notified'):
        reopen(j, sp); t = open_deal(j, sp, t1, r'Received|الواردة'); close_dialogs(sp)
        j.check(re.search(r'Declined|مرفوض|تم الرفض', t) and 'Out of stock until March' in t, 'the declined request does not show its status and reason')
        reopen(j, sp); open_deal(j, sp, t1, r'Received|الواردة'); bs = dlg_buttons(sp); close_dialogs(sp)
        j.check(not [x for x in bs if re.search(r'^(Send quote|Revise quote|Decline|أرسل عرضًا|عدّل العرض|رفض)$', x)], 'a declined deal still offers actions: %s' % bs)
        reopen(j, pg); t = open_deal(j, pg, t2, r'Sent|المرسلة'); bs = dlg_buttons(pg); close_dialogs(pg)
        j.check(re.search(r'Cancelled|Withdrawn|ملغ|سُحب', t), 'the withdrawn request does not show as withdrawn')
        j.check(not [x for x in bs if re.search(r'^(Withdraw|Accept quote|Counter-offer|اسحب الطلب|اقبل العرض)$', x)], 'a withdrawn deal still offers actions: %s' % bs)
        if j.live:
            j.check(j.sql1("select count(*) from public.notifications where user_id='%s' and type='deal'" % b['id']) not in ('', '0'), 'the buyer was not notified of the decline')
            j.reload(sp); t = open_deal(j, sp, t2, r'Received|الواردة'); close_dialogs(sp)
            j.check(re.search(r'Cancelled|Withdrawn|ملغ|سُحب', t), 'the supplier does not see request 2 as withdrawn')
    with j.step("'Waiting for you' counts drop; a later step on a closed deal is refused by the database"):
        deals_centre(j, sp, r'Received|الواردة'); row = deal_row_text(sp, t1); close_dialogs(sp)
        j.check(row and not re.search(r'Your move|دورك', row), 'the declined request still says Your move (%s)' % row.replace('\n', ' ')[:100])
        if j.live:
            ref = j.sql1("select ref from public.deals where to_company_id=%s and status='declined' limit 1" % s['co']['id'])
            r = sp.evaluate("r=>dxLive.sb.rpc('deal_act',{p_ref:r,p_action:'quote',p_data:{price:'1'},p_side:'to'})" + _dx.ERR, ref)
            j.check(r and j.sql1("select status from public.deals where ref='%s'" % ref) == 'declined', 'deal_act on a declined deal was not refused')

@journey('J-BUSINESS-03')
def rfq_many_suppliers(j):
    """A buyer sends one request for quotation to several suppliers at once and compares the answers side by side."""
    if j.live:
        b = live_company_person(j, 'Eng. Multi Buyer', 'Multi Buyer Pharma %s' % j.tag, sectors=('Manufacturer',))
        sups = []
        for n in ('Alpha API', 'Beta API', 'Gamma API'):
            s = live_company_person(j, '%s Sales' % n, '%s %s' % (n, j.tag), sectors=('API & excipients',)); seed_route(j, s['co']['id'], 'quote', s['id']); sups.append(s)
        for i in range(9): seed_company(j, None, 'Filler API %d %s' % (i, j.tag), sectors=('API & excipients',), status='unclaimed', source='public_list')
        pg = b['page']; j.reload(pg); names = [s['co']['name'] for s in sups]
    else:
        pg = j.demo_signin(j.new_page()); names = None
    with j.step("Filter 'API & excipients'; 'Select' three cards; an 11th selection is refused ('Up to 10 companies per request')"):
        directory(j, pg)
        if j.live: search_dir(j, pg, j.tag)
        boxes = pg.locator('#dxDir .dr-card input[type=checkbox]:visible')
        j.check(boxes.count() >= 11, 'fewer than 11 companies can be selected (%d)' % boxes.count())
        pg.wait_for_timeout(1500)                                     # the directory may still redraw as the database answers
        mark = j.toast_mark(pg)
        for i in range(11):
            bx = pg.locator('#dxDir .dr-card input[type=checkbox]:visible').nth(i)
            bx.scroll_into_view_if_needed(); bx.click(); pg.wait_for_timeout(150)
        j.check(any(re.search(r'Up to 10|10 شركات', t) for t in j.toasts_since(pg, mark)), "selecting an 11th company does not say 'Up to 10 companies per request'")
        j.check(not boxes.nth(10).is_checked(), 'the 11th company was selected')
        clr = pg.locator('.tr-x:visible'); j.check(clr.count(), 'the selection bar has no Clear'); clr.click(); pg.wait_for_timeout(300)
        chip_el = j.find(pg, L('API & excipients'), scope='#dxDir'); j.check(chip_el, "no 'API & excipients' filter"); chip_el.click(); pg.wait_for_timeout(900)
        if j.live: search_dir(j, pg, j.tag)
        cards = pg.locator('#dxDir .dr-card:visible')
        picked = []
        for i in range(cards.count()):
            nm = cards.nth(i).locator('.dr-name').inner_text().split('\n')[0].strip()
            if (names and nm in names) or (not names and len(picked) < 3):
                cards.nth(i).locator('input[type=checkbox]').check(force=True); picked.append(nm); pg.wait_for_timeout(150)
            if len(picked) == 3: break
        j.check(len(picked) == 3, 'could not select three API suppliers (%s)' % picked)
        j.data['picked'] = picked
    with j.step("The selection bar's 'Request quotes from 3' sends one RFQ (product, quantity, unit, deliver to, incoterm, message)"):
        j.click(pg, r'Request quotes from 3|اطلب عروض', scope='body', what='Request quotes from 3')
        fill_by_label(j, pg, r'What do you need|ماذا تحتاج', 'Microcrystalline cellulose PH-102 %s' % j.tag)
        fill_by_label(j, pg, r'Quantity|الكمية', '2000'); fill_by_label(j, pg, r'Message|الرسالة', 'Pharma grade, CoA per lot')
        mark = j.toast_mark(pg); dlg_click(j, pg, r'Send to 3', 'Send to 3 companies'); j.settle(pg, 1500)
        title = 'Microcrystalline cellulose PH-102 %s' % j.tag
        if j.live:
            j.check(j.wait_db("select count(*) from public.deals where title like $q$%%%s%%$q$" % title, 8) == '3', 'not one deal per supplier in the database')
    with j.step("The Sent list shows one request per supplier, each with its own status"):
        t = deals_centre(j, pg, r'Sent|المرسلة'); close_dialogs(pg)
        j.check(t.count(title) >= 3 or t.count('Microcrystalline cellulose PH-102') >= 3, 'the Sent list does not show three requests')
    with j.step("Each supplier sees only its own request and sends a quote"):
        if j.demo:
            open_deal(j, pg, title, r'Sent|المرسلة'); dlg_click(j, pg, r'Compare all quotes|قارن', 'Compare all quotes')
            for _ in range(3):
                s_ = pg.locator('.dbk-ov [data-simq]:visible')
                if not s_.count(): break
                s_.first.click(); pg.wait_for_timeout(700)
        else:
            for i, s in enumerate(sups):
                sp = s['page']; j.reload(sp); t = deals_centre(j, sp, r'Received|الواردة')
                others = [n for n in names if n != s['co']['name']]
                j.check(not any(o in t for o in others), "supplier %s sees another supplier's name" % s['co']['name'])
                close_dialogs(sp); open_deal(j, sp, title, r'Received|الواردة')
                deal_act(j, sp, 'Send quote', {r'Price|السعر': 'US$ %.2f per kg' % (3.1 - i * 0.2), r'Lead time|مدة': '%d weeks' % (2 + i)}); close_dialogs(sp)
            a_ref = j.sql1("select ref from public.deals where title like $q$%%%s%%$q$ and to_company_id=%s" % (title, sups[1]['co']['id']))
            n = sups[0]['page'].evaluate("r=>dxLive.sb.from('deals').select('id').eq('ref',r).then(x=>(x.data||[]).length)", a_ref)
            j.check(n == 0, "supplier A can read supplier B's deal through the API")
    with j.step('The buyer compares the quotes side by side (price, validity, terms, lead time) and accepts the best'):
        reopen(j, pg); open_deal(j, pg, title, r'Sent|المرسلة'); dlg_click(j, pg, r'Compare all quotes|قارن', 'Compare all quotes')
        t = dlg_text(pg); prices = re.findall(r'US\$\s*[\d.]+', t)
        j.check(len(prices) >= 3, 'the comparison does not show three quoted prices (%s)' % prices)
        j.check(re.search(r'week|أسبوع', t), 'the comparison shows no lead time')
        acc = pg.locator('.dbk-ov [data-accq]:visible'); j.check(acc.count(), 'no Accept in the comparison')
        acc.first.click(); j.settle(pg, 1500); close_dialogs(pg)
        if j.live:
            j.check(j.wait_db("select count(*) from public.deals where title like $q$%%%s%%$q$ and status='accepted'" % title, 6) == '1', 'no quote is accepted in the database')
            win = j.sql1("select to_company_id from public.deals where title like $q$%%%s%%$q$ and status='accepted'" % title)
            wuser = [s for s in sups if s['co']['id'] == win][0]['id']
            j.check(j.wait_db("select count(*) from public.notifications where user_id='%s' and type='deal'" % wuser, 5) not in ('', '0'), 'the accepted supplier is not notified')

@journey('J-BUSINESS-07')
def qualify_supplier(j):
    """A QA specialist qualifies a new supplier with a standard questionnaire and adds it to the approved supplier list."""
    b, s, sup, prod = buyer_and_supplier(j, 'Qualified API', 'Metformin HCl')
    pg = b['page']
    if j.live: seed_route(j, s['co']['id'], 'questionnaire', s['id'])
    with j.step("Supplier page → 'Questionnaire': it says how many answers are prefilled; 'Send questionnaire'"):
        directory(j, pg); open_card(j, pg, sup)
        j.click(pg, L('Questionnaire'), scope='#content', what='Questionnaire')
        t = dlg_text(pg); j.check(re.search(r'(\d+) of (\d+) answers', t) or re.search(r'\d+ من \d+', t), 'the questionnaire does not say how many answers are prefilled')
        mark = j.toast_mark(pg); dlg_click(j, pg, r'Send questionnaire|أرسل الاستبيان', 'Send questionnaire'); j.settle(pg, 1200)
        title = None
        if j.live:
            j.check(j.wait_db("select type||status from public.deals where to_company_id=%s order by id desc limit 1" % s['co']['id'], 6) == 'questionnairesent', 'no questionnaire deal in the database')
            title = j.sql1("select title from public.deals where to_company_id=%s order by id desc limit 1" % s['co']['id'])
        else:
            title = pg.evaluate("(dxDeals.all().filter(d=>d.type==='questionnaire').pop()||{}).title")
            j.check(title, 'no questionnaire was sent')
    with j.step("Supplier: opens it from Received, completes the missing answers, attaches a document, 'Answer questionnaire'"):
        if j.demo: their_move(j, pg, s, title, 'Answer questionnaire')
        else:
            sp = s['page']; j.reload(sp); open_deal(j, sp, title, r'Received|الواردة')
            dlg_click(j, sp, L('Answer questionnaire'), 'Answer questionnaire')
            req = sp.locator('.dbk-ov input[data-req]:visible')
            for i in range(req.count()):
                if not req.nth(i).input_value(): req.nth(i).fill('Yes — see attached SOP')
            j.check(sp.locator('.dbk-ov input[type=file]:visible').count(), 'not built: the questionnaire answer has no document upload')
            sp.locator('.dbk-ov input[type=file]').first.set_input_files(PDF)
            dlg_click(j, sp, r'Send answers|أرسل الإجابات', 'Send answers'); j.settle(sp, 1200); close_dialogs(sp)
            j.check(j.wait_db("select status from public.deals where to_company_id=%s and type='questionnaire' order by id desc limit 1" % s['co']['id'], 6) == 'answered', 'the answers did not reach the database')
    with j.step("QA: opens the answered questionnaire → 'Approve supplier'"):
        reopen(j, pg); t = open_deal(j, pg, title, r'Sent|المرسلة')
        j.check(re.search(r'Answered|تمت الإجابة|أجاب', t), 'the buyer does not see the questionnaire as Answered')
        deal_act(j, pg, 'Approve supplier'); close_dialogs(pg)
        if j.live: j.check(j.wait_db("select status from public.deals where to_company_id=%s and type='questionnaire' order by id desc limit 1" % s['co']['id'], 6) == 'approved', 'the approval did not reach the database')
    with j.step("Buyer workspace → Suppliers lists the approved supplier with date and approver after reload"):
        reopen(j, pg); t = workspace(j, pg, 'Suppliers|%s' % (ar('Suppliers') or 'الموردون'))
        j.check(sup in t, 'the approved supplier is not in the Suppliers tab')
        j.check(re.search(r'Approved|معتمد', t) and re.search(r'\d{1,2} \w{3} \d{4}|\d{4}-\d{2}-\d{2}', t), 'the Suppliers tab shows no approval date')
        if j.live: j.check(j.sql1("select status from public.approved_suppliers where buyer_company_id=%s and supplier_company_id=%s" % (b['co']['id'], s['co']['id'])) == 'approved', 'no approved_suppliers row')
    with j.step('Each side was notified at each step'):
        if j.demo: j.skip('the other party exists only in live')
        j.check(int(j.sql1("select count(*) from public.notifications where user_id='%s' and type='deal'" % s['id']) or 0) >= 2, 'the supplier was not notified of the questionnaire and the decision')
        j.check(int(j.sql1("select count(*) from public.notifications where user_id='%s' and type='deal'" % b['id']) or 0) >= 1, 'the buyer was not notified of the answers')

@journey('J-BUSINESS-08')
def license_dossier(j):
    """A company licenses-in a ready registration dossier: requests details, signs the NDA, receives the data, agrees terms."""
    if j.live:
        b, s, sup, _ = buyer_and_supplier(j, 'Dossier Owner')
        prod = 'Vitamin D3 50,000 IU %s' % j.tag
        j.sql("insert into public.company_listings (ref, company_id, kind, product, reg_status, deal_kind, markets, created_by, active) values ('L%s', %s, 'dossier', $q$%s$q$, 'EDA registered', 'License out', 'Egypt', '%s', true)" % (j.tag, s['co']['id'], prod, s['id']))
        j.reload(b['page']); pg = b['page']
    else:
        b, s, sup, _ = buyer_and_supplier(j, '', None); pg = b['page']; prod = 'Vitamin D3 50,000 IU capsules'
    with j.step("Owner's page → Listings tab → 'Request details' on the dossier"):
        directory(j, pg); open_card(j, pg, sup)
        t = company_tab(j, pg, 'Listings|%s' % ar('Listings'), 'Listings'); j.check(prod in t, 'the dossier is not on the Listings tab')
        row = pg.locator('#content *', has_text=prod).last
        el = j.find(pg, r'Request details|اطلب التفاصيل', scope='#content'); j.check(el, "no 'Request details' on the dossier")
        el.click(); pg.wait_for_timeout(800)
        j.check(dlg_open(pg), "'Request details' opens no request form")
        nda = pg.locator('.dbk-ov input[type=checkbox]:visible')
        if nda.count(): nda.first.check()
        fill_by_label(j, pg, r'Message|الرسالة|dMsg', 'Egypt and KSA, 2 M packs/year, exclusive', required=False)
        dlg_click(j, pg, L('Send request'), 'Send request'); j.settle(pg, 1000)
        title = prod
        if j.live: j.check(j.wait_db("select type||status from public.deals where to_company_id=%s order by id desc limit 1" % s['co']['id'], 6) == 'dossierrequested', 'no dossier deal (requested) in the database')
        else: j.check(pg.evaluate("dxDeals.all().some(d=>d.type==='dossier'&&d.status==='requested')"), 'no dossier request was created')
    with j.step("Owner: 'Sign NDA' then 'Share details' with a data-room note"):
        if j.demo:
            title = pg.evaluate("(dxDeals.all().filter(d=>d.type==='dossier').pop()||{}).title")
            their_move(j, pg, s, title, 'Sign NDA'); their_move(j, pg, s, title, 'Share details')
        else:
            title = j.sql1("select title from public.deals where to_company_id=%s order by id desc limit 1" % s['co']['id'])
            their_move(j, pg, s, title, 'Sign NDA')
            their_move(j, pg, s, title, 'Share details', {r'Shared|مشترك|شارك': 'Data room: stability Zone IVa, registration certificate %s' % j.tag}, attach=PDF)
        t = open_deal(j, pg, title, r'Sent|المرسلة')
        j.check(re.search(r'Details shared|تمت مشاركة', t), "the licensee does not see 'Details shared'")
    with j.step("Licensee: 'Agree terms' — status Agreed for both"):
        deal_act(j, pg, 'Agree terms'); t = dlg_text(pg); close_dialogs(pg)
        j.check(re.search(r'Agreed|تم الاتفاق', t), 'the deal is not Agreed')
        if j.live: j.check(j.wait_db("select status from public.deals where to_company_id=%s order by id desc limit 1" % s['co']['id'], 6) == 'agreed', 'the agreement did not reach the database')
    with j.step('Shared details are visible only to the two parties; a file can be shared in the data room'):
        t = open_deal(j, pg, title, r'Sent|المرسلة'); close_dialogs(pg)
        j.check(pg.evaluate("(()=>{return false})()") or re.search(r'\.pdf|Download|تنزيل', t), 'not built: no file can be shared in the dossier deal (only a text note)')

@journey('J-BUSINESS-11')
def apply_to_company_job(j):
    """A job seeker applies to a company's open position from its page and follows the application."""
    if j.live:
        hr = live_company_person(j, 'Rania HR', 'Hiring Pharma %s' % j.tag)
        seed_route(j, hr['co']['id'], 'job', hr['id'])
        j.sql("insert into public.jobs (user_id, title, company, location, country, type, description, active) values ('%s','QC Analyst %s',$q$%s$q$,'Giza','EG','Full-time','HPLC, dissolution',true)" % (hr['id'], j.tag, hr['co']['name']))
        me = j.person('Sara Seeker'); pg = me['page']; co = hr['co']['name']; job = 'QC Analyst %s' % j.tag
    else:
        pg = j.demo_signin(j.new_page()); co = 'Medsinia Industries'; job = 'Production Supervisor'; hr = None
    with j.step("Company page → Jobs tab → 'Apply' on a position; attach CV; send"):
        directory(j, pg); open_card(j, pg, co)
        t = company_tab(j, pg, 'Jobs|%s' % ar('Jobs'), 'Jobs'); j.check(job in t, 'the open position "%s" is not on the Jobs tab' % job)
        card = pg.locator('#content .cp-job', has_text=job).first
        ap = card.locator('button').first; j.check(ap.count(), 'no Apply on the position'); ap.click(); j.settle(pg, 1000)
        if not dlg_open(pg):
            j.check(pg.evaluate("document.body.getAttribute('data-page')") == 'jobs', "'Apply' neither opens an application form nor the job")
            j.notbuilt("'Apply' on the company page only opens the Jobs page — no application from the company page")
        f = pg.locator('.dbk-ov input[type=file]:visible'); j.check(f.count(), 'the application has no CV upload'); f.first.set_input_files(PDF)
        fill_by_label(j, pg, r'Why you|لماذا', 'Four years of HPLC and dissolution in a WHO-GMP plant.')
        dlg_click(j, pg, r'Send application|أرسل الطلب', 'Send application'); j.settle(pg, 1200)
    with j.step("The application reaches HR (deals centre Received) with the CV link; the applicant sees it with its status"):
        if j.live:
            j.check(j.wait_db("select count(*) from public.deals where type='job' and to_company_id=%s" % hr['co']['id'], 6) == '1' or j.wait_db("select count(*) from public.job_applications a join public.jobs b on b.id=a.job_id where b.title like '%%%s%%'" % j.tag, 2) == '1', 'the application is in neither deals nor job_applications')
            hp = hr['page']; j.reload(hp); t = deals_centre(j, hp, r'Received|الواردة'); close_dialogs(hp)
            j.check(job in t, "the application is not in HR's Received list")
            t = open_deal(j, hp, job, r'Received|الواردة'); close_dialogs(hp)
            j.check(re.search(r'\.pdf|CV', t) and pg.locator('a[href*="cv"]').count() >= 0, 'no CV link in the application')
        else:
            j.check(pg.evaluate("dxDeals.all().some(d=>d.type==='job'&&d.to&&d.to.slug==='medsinia-industries')"), 'no job application was created')
    with j.step("HR: 'Shortlist' → 'Invite to interview' (date) → 'Make offer'; the seeker is notified each time"):
        title = job if j.live else pg.evaluate("(dxDeals.all().filter(d=>d.type==='job'&&d.to&&d.to.slug==='medsinia-industries').pop()||{}).title")
        if j.demo:
            open_deal(j, pg, title, r'Sent|المرسلة')
            if not pg.locator('.dbk-ov [data-sim]:visible').count(): j.notbuilt('the demo cannot play the employer (no Simulate on a job application)')
            for _ in range(3): simulate(j, pg); close_dialogs(pg); open_deal(j, pg, title, r'Sent|المرسلة')
            close_dialogs(pg)
        else:
            their_move(j, pg, hr, title, 'Shortlist'); their_move(j, pg, hr, title, 'Invite to interview', {r'Interview date|موعد': '2026-11-02'})
            their_move(j, pg, hr, title, 'Make offer', {r'Salary|الراتب': 'EGP 28,000 / month'})
            j.check(int(j.sql1("select count(*) from public.notifications where user_id='%s' and type='deal'" % me['id']) or 0) >= 3, 'the seeker was not notified at each step')
    with j.step("Seeker: 'Accept job offer' — Hired; reload keeps it"):
        reopen(j, pg); open_deal(j, pg, title, r'Sent|المرسلة'); deal_act(j, pg, 'Accept job offer'); close_dialogs(pg)
        reopen(j, pg); t = open_deal(j, pg, title, r'Sent|المرسلة'); close_dialogs(pg)
        j.check(re.search(r'Hired|تم التوظيف|تعيين', t), 'the application is not Hired after reload')

@journey('J-BUSINESS-28')
def consulting_service(j):
    """A factory hires a regulatory consultant for a service and the work is proposed, accepted, delivered and rated."""
    if j.live:
        b = live_company_person(j, 'Factory Manager', 'Factory Hiring %s' % j.tag)
        c = live_company_person(j, 'Dr. Consultant', 'RegPath Consulting %s' % j.tag, sectors=('Regulatory & consulting',))
        seed_route(j, c['co']['id'], 'service', c['id']); seed_route(j, c['co']['id'], 'quote', c['id'])
        j.sql("update public.companies set profile = coalesce(profile,'{}'::jsonb) || '{\"services\":[\"EDA variation — site transfer\"]}' where id=%s" % c['co']['id'])
        j.reload(b['page']); pg = b['page']; cons = c['co']['name']
    else:
        pg = j.demo_signin(j.new_page()); cons = 'RegPath Consulting'; c = None
    with j.step("Factory: consultant page → request the service (scope), not a goods quotation"):
        directory(j, pg); open_card(j, pg, cons)
        el = j.find(pg, r'Request (this )?service|Request a proposal|اطلب الخدمة|اطلب عرضًا', scope='#content')   # not 'اطلب عرض سعر' (Request a quote)
        if not el: el = j.find(pg, L('Request a quote'), scope='#content')
        j.check(el, 'no way to request a service on the consultant page')
        el.click(); pg.wait_for_timeout(800)
        t = dlg_text(pg)
        j.check(re.search(r'^Service|\nService|الخدمة|^خدمة|\nخدمة', t) and not re.search(r'Quantity \*|الكمية \*', t), "not built: the consultant's page has no service request — 'Request a quote' opens a goods quotation (Quantity, Deliver to)")
        fill_by_label(j, pg, r'Message|الرسالة|Scope', 'EDA variation for site transfer of 3 products')
        dlg_click(j, pg, L('Send request'), 'Send request'); j.settle(pg, 1000)
        title = pg.evaluate("n=>(dxDeals.all().filter(d=>d.type==='service'&&d.to&&d.to.name===n).pop()||{}).title", cons)   # the request this journey sent to the consultant
        j.check(title, 'no service request was created')
    with j.step("Consultant: 'Send proposal' (EGP 85,000, 6 weeks, scope); factory: 'Accept'"):
        their_move(j, pg, c, title, 'Send proposal', {r'Fee|الأتعاب': 'EGP 85,000', r'Timeline|المدة': '6 weeks', r'Scope|النطاق': 'Gap analysis, dossier update, EDA follow-up'})
        open_deal(j, pg, title, r'Sent|المرسلة'); deal_act(j, pg, r'^\W*(Accept|Accept quote|قبول|اقبل)\W*$'); close_dialogs(pg)
    with j.step("Consultant: 'Start work' → 'Mark delivered' (attaching the deliverable)"):
        their_move(j, pg, c, title, 'Start work'); their_move(j, pg, c, title, 'Mark delivered', attach=PDF)   # the deliverable goes with the step
        t = open_deal(j, pg, title, r'Sent|المرسلة'); close_dialogs(pg)
        j.check(re.search(r'Delivered|تم التسليم', t), 'the factory does not see Delivered')
        j.check(re.search(r'\.pdf|Download|تنزيل', t), 'not built: the delivered service carries no deliverable attachment')
    with j.step("Factory: 'Rate supplier' — Closed; the review appears on the consultant's page"):
        open_deal(j, pg, title, r'Sent|المرسلة'); deal_act(j, pg, 'Rate supplier', {r'Rating|التقييم': '5', r'Comment|تعليق': 'Fast EDA approval %s' % j.tag}); close_dialogs(pg)
        directory(j, pg); open_card(j, pg, cons); t = company_tab(j, pg, 'Reviews|%s' % ar('Reviews'), 'Reviews')
        j.check(('Fast EDA approval %s' % j.tag) in t, "the review is not on the consultant's page")

@journey('J-BUSINESS-29')
def deal_documents(j):
    """Parties exchange the documents a pharma deal needs (CoA, specification, PO, invoice) inside the deal."""
    b, s, sup, prod = buyer_and_supplier(j, 'Document API', 'Ibuprofen')
    pg = b['page']; title = prod or 'Paracetamol 500 mg'
    with j.step('An accepted quote deal between buyer and supplier'):
        request_quote(j, pg, sup, prod)
        their_move(j, pg, s, title, 'Send quote', {r'Price|السعر': 'US$ 7.10 per kg'})
        open_deal(j, pg, title, r'Sent|المرسلة'); deal_act(j, pg, 'Accept quote'); close_dialogs(pg)
    with j.step('Buyer attaches a PO (PDF) in the deal thread'):
        open_deal(j, pg, title, r'Sent|المرسلة')
        f = pg.locator('.dbk-ov input[type=file]')
        att = j.find(pg, r'Attach|Add (a )?(file|document)|إرفاق|أرفق', scope='body')
        j.check(f.count() or att, 'not built: the deal thread has no way to attach a document (PO, CoA, invoice)')
        if att and not f.count(): att.click(); pg.wait_for_timeout(500)
        pg.locator('.dbk-ov input[type=file]').last.set_input_files(PDF); j.settle(pg, 1500)
        j.check('spec.pdf' in dlg_text(pg), 'the attached PO is not listed in the thread')
    with j.step("Supplier attaches CoA and invoice; each side opens the other's file; a third user cannot"):
        if j.demo: j.skip('the other party exists only in live')
        sp = s['page']; j.reload(sp); t = open_deal(j, sp, title, r'Received|الواردة')
        j.check('spec.pdf' in t, "the supplier does not see the buyer's PO")

@journey('J-BUSINESS-30', applies='live')
def deal_privacy(j):
    """Deal data stays private to the two companies in it."""
    b, s, sup, prod = buyer_and_supplier(j, 'Private API', 'Losartan')
    pg = b['page']; title = prod
    with j.step('A quote deal exists between buyer and supplier (with a quote)'):
        request_quote(j, pg, sup, prod)
        their_move(j, pg, s, title, 'Send quote', {r'Price|السعر': 'US$ 9.99 per kg'})
        ref = live_deal(j, title, 'ref'); j.check(ref, 'no deal in the database')
    x = j.person('Nosy Third User'); xp = x['page']
    with j.step("Third user's deals centre and the supplier's page show nothing of the deal"):
        t = deals_centre(j, xp); close_dialogs(xp)
        j.check(title not in t and '9.99' not in t, "the third user's deals centre shows the deal")
        directory(j, xp); open_card(j, xp, sup); j.check(title not in j.text(xp) and '9.99' not in j.text(xp), "the supplier's public page shows the deal")
    with j.step('Opening the deal by id in the console shows nothing'):
        xp.evaluate("r=>{try{dxDeals.thread(r)}catch(e){}}", ref); xp.wait_for_timeout(800)
        j.check('9.99' not in dlg_text(xp) and title not in dlg_text(xp), 'dxDeals.thread(<id>) shows the deal to a third user')
        close_dialogs(xp)
    with j.step('Database: select on deals/deal_events as the third user returns 0 rows; deal_act is refused'):
        did = int(live_deal(j, title, 'id'))
        n = xp.evaluate("([r,i])=>Promise.all([dxLive.sb.from('deals').select('id').eq('ref',r),dxLive.sb.from('deal_events').select('id').eq('deal_id',i)]).then(a=>[(a[0].data||[]).length,(a[1].data||[]).length])", [ref, did])
        j.check(n[0] == 0, 'the third user can select the deal')
        j.check(n[1] == 0, "the third user can read the deal's events")
        r = xp.evaluate("r=>dxLive.sb.rpc('deal_act',{p_ref:r,p_action:'accept',p_data:{},p_side:'from'})" + _dx.ERR, ref)
        j.check(r and live_deal(j, title) == 'quoted', 'deal_act by a third user was not refused')

if __name__ == '__main__': main(__file__)
