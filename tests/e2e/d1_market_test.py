"""D1 end-to-end: the marketplace's supply and demand cards come from the database (the approved cards as templates), no demo listings or sponsors,
Contact/Quote reach the real person, publishing from the wizard saves the listing, and the ticker shows real listings."""
from playwright.sync_api import sync_playwright
import subprocess, time, os
from _dx import APP_URL as U, DB, R, T, sql, ST, FIXTURES, fn_env, refused, ERR, wait_for, done   # shared settings: tests/e2e/_dx.py

st = ST
seller = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('seller{st}@x.test', crypt('x', gen_salt('bf')), '{{\"name\":\"Dr. Real Seller {st}\"}}') returning id").split('\n')[0]
buyer = sql(f"insert into auth.users (email, encrypted_password, raw_user_meta_data) values ('buyer{st}@x.test', crypt('x', gen_salt('bf')), '{{\"name\":\"Dr. Real Buyer {st}\"}}') returning id").split('\n')[0]
sql(f"update public.profiles set country='EG', verified=true where id='{seller}'")
sql(f"insert into public.products (user_id, name, category, type, price, unit, moq, description, emoji, docs, active) values ('{seller}','Paracetamol DC 90% {st}','api','supply','US$ 4.20','kg','1 MT','Direct compression grade, CEP','💊','{{CEP,WHO-GMP}}',true)")
time.sleep(0.05)   # a separate, later statement: Amoxicillin is the newer listing
sql(f"insert into public.products (user_id, name, category, type, price, unit, moq, description, emoji, docs, active) values ('{seller}','Amoxicillin trihydrate {st}','api','supply','US$ 21','kg','500 kg','Compacted','⚗️','{{DMF}}',true)")
sql(f"insert into public.enquiries (user_id, type, category, country, title, body, urgent, status) values ('{buyer}','demand','api','EG','Need Omeprazole pellets 8.5% {st}','Monthly 500 kg, EU-GMP',true,'active')")
with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox"]); pg = b.new_page(viewport={'width': 1440, 'height': 900}); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:150])); pg.on("dialog", lambda d: d.accept())
    pg.goto(U, wait_until='load'); pg.wait_for_timeout(400); pg.evaluate('endSplash()'); pg.wait_for_timeout(700)
    pg.evaluate("showSignup()"); pg.fill('#suName', 'Dr. Market Visitor'); pg.fill('#suEmail', f'visitor{st}@x.test'); pg.fill('#suPw', 'Strong-pass-2026'); pg.click('#signupPage button.f-btn'); wait_for(lambda: pg.evaluate("window.dxLive && window.ME && !!dxLive.uuidOf(ME.id)"), 20); pg.wait_for_timeout(2000)
    pg.evaluate("goto('market')"); pg.wait_for_timeout(3500)
    sup = pg.evaluate("[...document.querySelectorAll('#mkx .supply-grid .lcard .lc-title')].map(e=>e.textContent)")
    pos = lambda name: next((i for i, x in enumerate(sup) if x.startswith(name)), -1)
    T('supply cards are the real listings, not the demo ones', pos(f'Paracetamol DC 90% {st}') >= 0 and pos(f'Amoxicillin trihydrate {st}') >= 0 and not any('Metformin HCl BP/USP' in x for x in sup), sup[:4])
    T('…newest first', 0 <= pos(f'Amoxicillin trihydrate {st}') < pos(f'Paracetamol DC 90% {st}'), sup[:6])
    card = pg.evaluate(f"(()=>{{var c=[...document.querySelectorAll('#mkx .lcard')].find(x=>x.querySelector('.lc-title').textContent.indexOf('Paracetamol DC 90% {st}')===0);return c?{{price:c.querySelector('.price').textContent,moq:c.querySelector('.moq').textContent,certs:[...c.querySelectorAll('.cert-p')].map(x=>x.textContent),trust:c.querySelector('.trust-bar').innerText}}:null}})()")
    T('a card shows price, MOQ, seller, certificates and the verified seller badge', card and card['price'].startswith('US$ 4.20/kg') and 'MOQ: 1 MT' in card['moq'] and f'Dr. Real Seller {st}' in card['moq'] and 'CEP' in card['certs'] and 'Verified seller' in card['trust'], card)
    dem = pg.evaluate("[...document.querySelectorAll('#mkx .dcard')].map(c=>c.innerText.replace(/\\s+/g,' '))")
    T('demand cards are real buy requests with the buyer and URGENT', any(f'Need Omeprazole pellets 8.5% {st}' in x and f'Dr. Real Buyer {st}' in x and 'URGENT' in x for x in dem), dem[:2])
    # the "Structure" label is drawn by CSS (UI2), so the chip is looked for as an element on the real card's title
    mol = pg.evaluate(f"(()=>{{var c=[...document.querySelectorAll('#mkx .supply-grid .lcard[data-live]')].find(x=>x.querySelector('.lc-title').textContent.indexOf('Paracetamol DC 90% {st}')===0);var b=c&&c.querySelector('.lc-title .dx-molchip');return b?b.dataset.mol:null}})()")
    T('the chemical-structure button appears on real API listings', mol == 'paracetamol', mol)
    T('no demo demand cards', not any('Ciprofloxacin HCl 2MT/month' in x for x in dem))
    # a real paid featured listing (e.g. one bought by an earlier e4b run on the same stack) may fill the sponsored strip; the demo samples never
    T('demo sponsored listings are not shown', not pg.evaluate("[...document.querySelectorAll('#mkx .sponsored-card:not([data-live]),#mkx .sp-mini:not([data-live])')].some(e=>e.offsetWidth>0)"))
    tick = pg.evaluate("(document.getElementById('tickerInner')||{}).innerText||''")
    T('the ticker shows real listings', f'Paracetamol DC 90% {st}' in tick and 'Metformin HCl GMP $5.80/kg' not in tick, tick[:160])
    pg.evaluate(f"(()=>{{var c=[...document.querySelectorAll('#mkx .lcard')].find(x=>x.querySelector('.lc-title').textContent.indexOf('Paracetamol DC 90% {st}')===0);c.querySelector('.btn-contact').click()}})()"); pg.wait_for_timeout(3000)
    T('Contact opens a conversation with the real seller', pg.evaluate("document.body.getAttribute('data-page')") == 'messages' and f'Dr. Real Seller {st}' in pg.inner_text('.chat-head'))
    pg.evaluate("goto('market')"); pg.wait_for_timeout(1500)
    pg.evaluate(f"(()=>{{var c=[...document.querySelectorAll('#mkx .dcard')].find(x=>x.innerText.indexOf('Need Omeprazole pellets 8.5% {st}')>=0);c.querySelector('.qt-btn').click()}})()"); pg.wait_for_timeout(3000)
    T('Quote on a buy request opens a conversation with the real buyer', f'Dr. Real Buyer {st}' in pg.inner_text('.chat-head'))
    # publish through the wizard's own hook path
    pg.evaluate("goto('market')"); pg.wait_for_timeout(1200)
    pg.evaluate(f"dxLiveHook('listing',{{type:'supply',title:'Metformin HCl EP {st}',price:'US$ 5.60',moq:'500 kg',where:'Egypt',lead:'2 weeks',desc:'Fresh batch',certs:['CEP']}})"); pg.wait_for_timeout(2500)
    T('publishing a supply listing saves it under my account', sql(f"select type||'|'||category||'|'||price from public.products where name='Metformin HCl EP {st}'") == 'supply|api|US$ 5.60')
    T('…and it appears in the supply grid', f'Metformin HCl EP {st}' in pg.evaluate("[...document.querySelectorAll('#mkx .supply-grid .lc-title')].map(e=>e.textContent).join('|')"))
    pg.evaluate(f"dxLiveHook('listing',{{type:'demand',title:'Looking for Sitagliptin {st}',desc:'1 MT, DMF required',moq:'1 MT',where:'Egypt',certs:[]}})"); pg.wait_for_timeout(2500)
    T('publishing a buy request saves it as a demand enquiry', sql(f"select type||'|'||status from public.enquiries where title='Looking for Sitagliptin {st}'") == 'demand|active')
    # F-03: boost / featured are paid products — the owner of a listing cannot switch them on through the API
    # (FAILS before migration 0020_security_core.sql — the products own-manage policy let the owner write boosted_until)
    r = pg.evaluate(f"dxLive.sb.from('products').update({{boosted_until:'2099-01-01T00:00:00Z',featured_until:'2099-01-01T00:00:00Z'}}).eq('name','Metformin HCl EP {st}')" + ERR)
    T('the owner cannot boost or feature their own listing without paying', refused(r) and sql(f"select boosted_until is null and featured_until is null from public.products where name='Metformin HCl EP {st}'") == 't', (r, sql(f"select boosted_until, featured_until from public.products where name='Metformin HCl EP {st}'")))
    r = pg.evaluate(f"dxLive.sb.from('products').insert({{user_id:dxLive.uuidOf(ME.id),name:'Free boost {st}',category:'api',type:'supply',active:true,boosted_until:'2099-01-01T00:00:00Z'}})" + ERR)
    T('…nor create a listing that starts boosted', refused(r) and sql(f"select count(*) from public.products where name='Free boost {st}' and boosted_until is not null") == '0', r)
    r = pg.evaluate(f"dxLive.sb.from('products').update({{price:'US$ 0.01'}}).eq('name','Paracetamol DC 90% {st}').select().then(r=>(r.data||[]).length)")
    T("cannot change someone else's listing", r == 0 and sql(f"select price from public.products where name='Paracetamol DC 90% {st}'") == 'US$ 4.20')
    T('no errors in the page', not errs, errs)
    b.close()
done()
