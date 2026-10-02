from playwright.sync_api import sync_playwright
R=[]
def T(n,ok,d=''): R.append(ok); print(('✅ ' if ok else '❌ ')+n+('' if ok else '  → '+str(d)))
def pdf(n): return {'name':n,'mimeType':'application/pdf','buffer':b'%PDF'}
with sync_playwright() as p:
    b=p.chromium.launch(args=["--no-sandbox"]); pg=b.new_page(viewport={'width':1440,'height':900}); errs=[]; warns=[]
    pg.on("pageerror",lambda e:errs.append(str(e)[:200])); pg.on("console",lambda m: warns.append(m.text[:200]) if '[drugbox]' in m.text else None)
    pg.goto('file:///tmp/drugbox_brand.html',wait_until='networkidle',timeout=60000); pg.evaluate('endSplash()'); pg.wait_for_timeout(600)
    pg.click('.lg-demo'); pg.click('#loginPage .f-btn'); pg.wait_for_timeout(3300)
    if pg.locator('.tour-skip').count(): pg.click('.tour-skip')
    pg.evaluate("goto('companies')"); pg.wait_for_timeout(300)
    # create a company (after checking it does not exist)
    pg.click('#dxDir [data-hadd]'); pg.wait_for_timeout(200); pg.fill('#acQ','Zeta Pharma'); pg.wait_for_timeout(300); pg.click('.dbk-ov [data-acnew]'); pg.wait_for_timeout(300)
    T('create wizard starts from "not listed"', pg.locator('.dbk-ov .pl-card').count()==2)
    pg.locator('.dbk-ov input[name=plPick][value=free]').check(force=True); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(200)
    pg.fill('#ccN','Zeta Pharma Industries'); pg.select_option('#ccS','Manufacturer'); pg.select_option('#ccG','Giza'); pg.fill('#ccC','Giza'); pg.fill('#ccP','+20 2 5'); pg.fill('#ccE','z@z.example'); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(250)
    pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(500)
    if pg.is_visible('#dxEditor'): pg.click('#dxEditor .ed-x'); pg.wait_for_timeout(200)
    T('new company is mine and in the switcher', 'Zeta Pharma Industries' in pg.inner_text('#dxCoSwitch'))
    pg.evaluate("dxHub.workspace('zeta-pharma-industries')"); pg.wait_for_timeout(300)
    T('its workspace shows low completeness with next steps', int(pg.inner_text('#dxDir .hb-pct').rstrip('%'))<60)
    # VIP = sponsored only
    pg.locator('#dxDir [data-wtab=plan]').click(); pg.wait_for_timeout(250); pg.click('#dxDir [data-wvip]'); pg.wait_for_timeout(250); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(250); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(400)
    pg.evaluate("goto('companies')"); pg.wait_for_timeout(300)
    T('VIP appears in the Sponsored row', 'Zeta Pharma' in pg.inner_text('#dxDir .dr-vipstrip'))
    first=pg.evaluate("document.querySelector('#dxDir .dr-grid .hb-card .dr-name').childNodes[0].textContent")
    T('VIP does not jump the results order', first!='Zeta Pharma Industries', first)
    # verification from the workspace (documents only there)
    pg.evaluate("dxHub.workspace('zeta-pharma-industries','plan')"); pg.wait_for_timeout(300); pg.click('#dxDir [data-wverify]'); pg.wait_for_timeout(200)
    pg.fill('#vfRN','778899'); pg.set_input_files('#vfR',files=[pdf('r.pdf')]); pg.set_input_files('#vfT',files=[pdf('t.pdf')]); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(300)
    T('get verified (free) → under review', pg.evaluate("dxDir.bySlug('zeta-pharma-industries').status")=='pending')
    # acting as different companies
    pg.click('#dxCoSwitch'); pg.wait_for_timeout(150); pg.locator('#dxCoMenu [data-cs=quadra-pharm]').click(); pg.wait_for_timeout(200)
    T('switch acting company', 'Quadra Pharm' in pg.inner_text('#dxCoSwitch'))
    # bulk request from the directory + comparison
    pg.evaluate("goto('companies')"); pg.wait_for_timeout(300)
    for s in ['cairo-api-trading','alex-excipients','nile-valley-pharma']:
        pg.locator(f'#dxDir .hb-card[data-slug="{s}"] [data-hpick] input').check(); pg.wait_for_timeout(100)
    T('select several companies → tray', pg.is_visible('#dxRfqTray.on') and '3' in pg.inner_text('#dxRfqTray'))
    pg.click('#dxRfqTray .tr-go'); pg.wait_for_timeout(250); pg.fill('#bqWhat','Metformin HCl BP'); pg.fill('#bqQty','1'); pg.select_option('#bqUnit','MT'); pg.fill('#bqMsg','CEP required'); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(300)
    gid=pg.evaluate("dxDeals.all().find(d=>d.title==='Metformin HCl BP').group")
    T('one request → 3 routed deals', pg.evaluate(f"dxDeals.all().filter(d=>d.group==={gid}&&d.assignee).length")==3)
    pg.evaluate(f"dxCompareQuotes({gid})"); pg.wait_for_timeout(250)
    for i in range(3): pg.locator('.dbk-ov [data-simq]').first.click(); pg.wait_for_timeout(300)
    pg.locator('.dbk-ov [data-accq]').first.click(); pg.wait_for_timeout(300)
    T('compare + accept best → others declined', pg.evaluate(f"dxDeals.all().filter(d=>d.group==={gid}).map(d=>d.status).sort().join(',')")=='accepted,declined,declined')
    # QR
    pg.evaluate("dxHub.page('medsinia-industries')"); pg.wait_for_timeout(300); pg.click('#dxDir [data-hqr]'); pg.wait_for_timeout(250)
    T('QR for any company page', pg.locator('.dbk-ov .qr-box > svg').count()==1); pg.keyboard.press('Escape')
    # claim an unclaimed page through add-or-claim
    pg.evaluate("goto('companies')"); pg.wait_for_timeout(300); pg.click('#dxDir [data-hadd]'); pg.wait_for_timeout(200); pg.fill('#acQ','Suez'); pg.wait_for_timeout(300)
    pg.click('.dbk-ov [data-acclaim=suez-pharma-packaging]'); pg.wait_for_timeout(300)
    pg.fill('#clRole','Owner'); pg.fill('#clPhone','0100'); pg.fill('#clMail','a@suez.example'); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(300)
    code=pg.evaluate("document.querySelector('.cl-demo b').textContent"); pg.fill('#clCode',code); pg.click('.dbk-ov [data-a=ok]'); pg.wait_for_timeout(400)
    T('claim → I manage it and land in its workspace', pg.evaluate("dxDir.bySlug('suez-pharma-packaging').owner")==pg.evaluate("ME.id") and pg.locator('#dxDir.ws').count()==1 and 'Suez Pharma Packaging' in pg.inner_text('#dxDir .ws-h'))
    print('\nJS errors:',errs or 'none','| feature warnings:',warns or 'none'); print(sum(R),'/',len(R)); b.close()
