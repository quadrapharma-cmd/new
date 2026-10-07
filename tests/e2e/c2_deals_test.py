"""C2 end-to-end: two companies in two browsers — RFQ from the supplier's page, quote, accept, confirm, ship, receive, rate
the engine refuses out-of-turn steps and expired offers (the screen returns to the true state); track record from the database."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
from _dx import APP_URL as U, DB, R, T, sql, ST, STN, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST; PW = 'Strong-pass-2026'
def signup(pg, name, email):
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', name); pg.fill('#suEmail', email); pg.fill('#suPw', PW); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    return pg.evaluate("dxLive.uuidOf(ME.id)")
def relogin(pg):
    pg.reload(wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(4000)
def ref_status(ref): return sql(f"select status from public.deals where ref='{ref}'")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); errs = []
    A = b.new_context(viewport={'width': 1440, 'height': 900}).new_page(); B = b.new_context(viewport={'width': 1440, 'height': 900}).new_page()
    for pg in (A, B): pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    a = signup(A, 'Dr. Buyer Manager', f'buyer{st}@x.test'); bb = signup(B, 'Dr. Supplier Sales', f'seller{st}@x.test')
    SA, SB = f'buyer-pharma-{st}', f'supplier-api-{st}'
    sql(f"insert into public.companies (owner_id, name, slug, type, status, registry, sectors, governorate) values ('{a}','Buyer Pharma {st}','{SA}','Manufacturer','verified','11{STN % 100000}','{{Manufacturer}}','Giza')")
    sql(f"insert into public.companies (owner_id, name, slug, type, status, registry, licensed, sectors, governorate) values ('{bb}','Supplier API {st}','{SB}','Supplier','verified','22{STN % 100000}',true,'{{API supplier}}','Cairo')")
    sql(f"insert into public.company_products (company_id, name, active_ingredient, active_ingredient_ar, dosage_form, role) select id, 'Metformin HCl {st}', 'Metformin HCl', 'ميتفورمين', 'API powder', 'supplier' from public.companies where slug='{SB}'")
    for pg, s in ((A, SA), (B, SB)): pg.evaluate(f"localStorage.setItem('dx_acting', JSON.stringify('{s}'))"); relogin(pg)
    # the buyer sends an RFQ from the supplier's page (the real dialog)
    A.evaluate(f"dxHub.page('{SB}','products')"); A.wait_for_timeout(2500)
    A.evaluate("(()=>{var b=document.querySelector('#dxDir [data-hrfq]');b&&b.click()})()"); A.wait_for_timeout(700)
    opts = A.evaluate("(()=>{var o=[...document.querySelectorAll('.dbk-ov')].filter(e=>e.offsetWidth>0).pop();return o?[...o.querySelectorAll('#rqWhat option')].map(x=>x.value||x.textContent):[]})()")
    pick = next((o for o in opts if f'Metformin HCl {st}' in o), None)
    if pick: A.select_option('#rqWhat', pick)
    for sel, val in [('#rqQty', '2'), ('#rqMsg', 'CEP required, CIF Alexandria')]:
        if A.locator(sel).count(): A.fill(sel, val)
    if A.locator('#rqUnit').count(): A.select_option('#rqUnit', index=0)
    A.evaluate("(()=>{var o=[...document.querySelectorAll('.dbk-ov')].filter(e=>e.offsetWidth>0).pop();var b=o&&[...o.querySelectorAll('button')].find(x=>x.textContent.trim()==='Send request');b&&b.click()})()"); A.wait_for_timeout(2500)
    A.evaluate("dxLive.dealsBusy()"); A.wait_for_timeout(800)
    row = sql(f"select d.ref||'|'||d.type||'|'||d.status from public.deals d join public.companies c on c.id=d.to_company_id where c.slug='{SB}' order by d.id desc limit 1")
    T('the RFQ dialog (product picked from the supplier\'s list) creates a real deal: quote, sent', row.endswith('|quote|sent') and f'Metformin HCl {st}' in sql(f"select title from public.deals where ref='{row.split('|')[0]}'"), (row, opts[:4]))
    ref = row.split('|')[0]
    T('it is routed to the supplier and notifies them', sql(f"select count(*) from public.notifications where user_id='{bb}' and type='deal'") == '1')
    relogin(B); B.wait_for_timeout(1000)
    T('the supplier sees the request in its deals', B.evaluate(f"dxDeals.all().some(d=>d.id==='{ref}'&&d.status==='sent')"))
    B.evaluate(f"dxDeals.act('{ref}','quote',{{price:'US$ 5.40 / kg',validity:'14 days',lead:'3 weeks'}},'to')"); B.wait_for_timeout(500); B.evaluate("dxLive.dealsBusy()"); B.wait_for_timeout(1000)
    T('the supplier quotes → the engine records "quoted" with the offer', ref_status(ref) == 'quoted' and sql(f"select offer->>'price' from public.deals where ref='{ref}'") == 'US$ 5.40 / kg')
    # refusal: the buyer tries the supplier's step
    relogin(A)
    A.evaluate(f"dxDeals.act('{ref}','revise',{{price:'US$ 1 / kg'}},'to')"); A.wait_for_timeout(500); A.evaluate("dxLive.dealsBusy()"); A.wait_for_timeout(1500)
    T("the buyer cannot take the supplier's step (engine refuses, offer unchanged)", ref_status(ref) == 'quoted' and sql(f"select offer->>'price' from public.deals where ref='{ref}'") == 'US$ 5.40 / kg')
    T('…and the buyer\'s screen returns to the true state', A.evaluate(f"(()=>{{var d=dxDeals.get('{ref}');return d&&d.offer&&d.offer.price}})()") == 'US$ 5.40 / kg')
    # refusal: expired offer
    sql(f"update public.deals set offer_at = now() - interval '20 days' where ref='{ref}'"); relogin(A)
    A.evaluate(f"dxDeals.act('{ref}','accept',{{}},'from')"); A.wait_for_timeout(500); A.evaluate("dxLive.dealsBusy()"); A.wait_for_timeout(1500)
    T('an expired offer cannot be accepted (engine refuses)', ref_status(ref) == 'quoted')
    sql(f"update public.deals set offer_at = now() where ref='{ref}'"); relogin(A)
    A.evaluate(f"dxDeals.act('{ref}','accept',{{}},'from')"); A.wait_for_timeout(500); A.evaluate("dxLive.dealsBusy()"); A.wait_for_timeout(1000)
    T('the buyer accepts a valid offer', ref_status(ref) == 'accepted')
    relogin(B)
    for step in ('confirm', 'ship'): B.evaluate(f"dxDeals.act('{ref}','{step}',{{}},'to')"); B.wait_for_timeout(400)
    B.evaluate("dxLive.dealsBusy()"); B.wait_for_timeout(1200)
    T('the supplier confirms and ships (in order)', ref_status(ref) == 'shipped')
    relogin(A)
    A.evaluate(f"dxDeals.act('{ref}','receive',{{ontime:'yes'}},'from')"); A.wait_for_timeout(400); A.evaluate(f"dxDeals.act('{ref}','rate',{{stars:5,note:'Full CEP, on time'}},'from')"); A.wait_for_timeout(400)
    A.evaluate("dxLive.dealsBusy()"); A.wait_for_timeout(1500)
    T('the buyer receives and rates → closed', ref_status(ref) == 'closed')
    T('the full trail is recorded in order', sql(f"select string_agg(e.action,'>' order by e.id) from public.deal_events e join public.deals d on d.id=e.deal_id where d.ref='{ref}'") == 'sent>quote>accept>confirm>ship>receive>rate')
    relogin(A); A.wait_for_timeout(1500)
    A.evaluate(f"goto('companies');dxDir.open('{SB}')"); A.wait_for_timeout(3000)   # the directory and the track record load when the pages open
    tr = A.evaluate(f"(()=>{{var t=dxHubData.track('{SB}');return t?[t.orders,t.ontime,t.rating,t.reviews]:null}})()") if A.evaluate("!!(window.dxHubData&&dxHubData.track)") else A.evaluate(f"window.dxLiveTrack('{SB}')&&[dxLiveTrack('{SB}').orders,dxLiveTrack('{SB}').ontime,dxLiveTrack('{SB}').rating,dxLiveTrack('{SB}').reviews]")
    T("the supplier's track record comes from the database: 1 order, 100% on time, ★5.0 from 1 review", tr == [1, 100, 5, 1], tr)
    T('the directory shows the real rating', A.evaluate(f"(()=>{{var c=dxDir.bySlug('{SB}');return c&&c.rating===5&&c.reviews===1}})()"))
    A.evaluate(f"dxDeals.thread('{ref}')"); A.wait_for_timeout(800)
    T('the demo\'s "simulate their reply" button is hidden in the live app', not A.evaluate("[...document.querySelectorAll('[data-sim]')].some(e=>e.offsetWidth>0)"))
    A.evaluate("document.querySelectorAll('.dbk-ov').forEach(o=>o.remove())")
    before = sql(f"select status||'|'||title from public.deals where ref='{ref}'")
    r = A.evaluate(f"dxLive.sb.from('deals').update({{status:'{'open' if before.startswith('closed') else 'closed'}',title:'forged'}}).eq('ref','{ref}')" + ERR)
    T('deals cannot be edited directly through the API', before and refused(r) and sql(f"select status||'|'||title from public.deals where ref='{ref}'") == before, (r, before))
    T('no errors in the page', not errs, errs)
    b.close()
done()
