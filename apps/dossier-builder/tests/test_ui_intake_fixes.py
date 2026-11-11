"""Review fixes in the page (Playwright): a refresh keeps what the user typed and chose, a file refused by the kind rule never fills the
form (the model reads only the accepted files), another document with the same file name is kept under a free name, the page's copy of
the active-substance cleaning matches the engine, one unread scan does not switch the kind off for the other files, and a leaflet placed
from the «not placed yet» box asks for its type and language, a file the kind rule refused waits in that box after «Create» (never lost),
a typed API cell never stops later readings, a file moved to its card by «move it» gets its model reading, and a resumed placement runs once,
writes the data once and finishes the «make it readable» conversions. Fictional product «Dermacure» / «Cardiolol»."""
import io, json
import httpx
import pytest
from fixtures_pdf import make_pdf, make_pdf_lines
from test_ui_e2e import server, browser          # noqa: F401  (the module's live server and Chromium)

CPP = ['Certificate of Pharmaceutical Product', 'Certificate No: CPP-2024-0117', 'Trade name: Cardiolol 10 mg', 'Dosage form: film-coated tablet',
       'Active ingredient: Bisoprolol fumarate', 'Manufacturer: Medis S.A., Nabeul, Tunisia', 'Marketing authorisation holder: Medis S.A.',
       'Date of issue: 12 March 2025', 'Valid until: 11 March 2027']
EDA_PRICING = ['Egyptian Drug Authority — Pricing Policies Administration', 'Cardiolol 10 mg tablets', 'Box of 30 tablets 00 45', 'Applicant: Medis S.A.']


def _page(browser, server, init=''):
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en');" + init)
    page.goto(server + '/#/new')
    page.wait_for_selector('#intakeBtn')
    return page, errors


def _upload(page, sel, paths):
    with page.expect_file_chooser() as fc:
        page.click(sel)
    fc.value.set_files([str(p) for p in paths])


def _board_when(server, did, done, timeout=180):
    """The dossier's board once `done(placed, unplaced)` holds (the placement runs in the page after «Create»)."""
    import time
    end = time.time() + timeout
    while True:
        b = httpx.get(f'{server}/api/dossiers/{did}/board').json()
        placed = {d['filename']: s['req_id'] for s in b['slots'] for d in s['documents']}
        unplaced = [d['filename'] for d in b['unassigned']]
        if done(placed, unplaced) or time.time() > end:
            return placed, unplaced
        time.sleep(0.5)


def _saved(page):
    page.wait_for_timeout(800)
    page.wait_for_function("() => /\\d/.test(document.querySelector('#wizSaved').textContent)")


def test_refresh_keeps_what_the_user_typed_and_chose(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    page, errors = _page(browser, server)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    page.click('#wizNext')
    assert page.input_value('[data-in=trade]') == 'Cardiolol 10 mg'                     # read from the CPP
    page.fill('[data-in=trade]', 'Cardiolol Plus')                                      # the user corrects it
    page.click('#wizNext')
    assert page.locator('[data-k=origin][data-v=imported].on').count() == 1
    page.click('[data-k=origin][data-v=local]')                                         # and chooses another origin
    _saved(page)
    page.reload()
    page.wait_for_selector('[data-k=origin]', timeout=60000)
    page.wait_for_timeout(1500)                                                         # the restored readings are merged again
    assert page.locator('[data-k=origin][data-v=local].on').count() == 1 and page.locator('[data-k=licence][data-v=own].on').count() == 1
    page.click('#wizBack')
    assert page.input_value('[data-in=trade]') == 'Cardiolol Plus'                      # before the fix: «Cardiolol 10 mg» and «imported» came back
    assert errors == [], errors
    page.click('#wizRestart')
    page.close()


def test_a_file_refused_by_the_kind_rule_never_fills_the_form(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    wrong = make_pdf_lines(tmp_path / 'price letter.pdf', ['Egyptian Drug Authority', 'Pricing Certificate', 'Trade name: Wrongol 20 mg', 'Public price: 45.00 EGP'], 'Pricing')
    stub = ("window.__seen=[]; window.DBAI={available:async()=>true, extract:async(prompt, files)=>{ window.__seen.push(files.map(f=>f.name));"
            " return files.some(f=>f.name==='price letter.pdf')?{product:{name:'Wrongol 20 mg', manufacturer:'Other Pharma'}, apis:[{name:'Wrongolamide'}]}"
            ":{product:{name:'Cardiolol 10 mg'}}; }};")
    page, errors = _page(browser, server, stub)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    _upload(page, '[data-updoc="gmp_certificate"]', [wrong])                            # a pricing letter under the GMP card: refused
    page.wait_for_selector('[data-rmdoc="price letter.pdf"]', timeout=120000)
    live = page.inner_text('#wizLive')
    assert 'Wrongol' not in live and 'Other Pharma' not in live and 'Cardiolol 10 mg' in live
    assert page.evaluate('window.__seen') == [['cpp.pdf']]                               # the model never read the refused file
    page.click('[data-rmdoc="price letter.pdf"]')
    page.wait_for_function("() => !document.querySelector('[data-rmdoc]')")
    assert 'Wrongol' not in page.inner_text('#wizLive')
    assert errors == [], errors
    page.click('#wizRestart')
    page.close()


def test_another_document_with_the_same_file_name_is_kept(server, browser, tmp_path):
    (tmp_path / 'a').mkdir(); (tmp_path / 'b').mkdir()
    a = make_pdf_lines(tmp_path / 'a' / 'scan.pdf', CPP, 'WHO Certification Scheme')
    b = make_pdf_lines(tmp_path / 'b' / 'scan.pdf', ['Egyptian Drug Authority', 'Pricing Certificate', 'Trade name: Cardiolol 10 mg', 'Public price: 45.00 EGP',
                                                      'Pack: 30 tablets'], 'Pricing')
    page, errors = _page(browser, server)
    _upload(page, '[data-updoc="registration_licence"]', [a])
    page.wait_for_selector('#intakeReview', timeout=120000)
    _upload(page, '[data-updoc="pricing_certificate"]', [b])                            # a different scanner file, same name
    page.wait_for_selector('[data-docline="scan (2).pdf"]', timeout=120000)
    page.wait_for_function("() => !document.querySelector('.doccards .c-wait')", timeout=120000)
    assert 'scan (2).pdf' in page.locator('.doccard').nth(1).inner_text()               # read under the pricing card
    _upload(page, '[data-updoc="registration_licence"]', [a])                            # the very same file again: still «already uploaded»
    page.wait_for_selector('#toast:has-text("already uploaded")')
    assert page.locator('[data-docline]').count() == 2
    assert errors == [], errors
    page.click('#wizRestart')
    page.close()


def test_the_pages_active_substance_cleaning_matches_the_engine(server, browser):
    from dossier_engine import extract
    cases = [[{'name': 'Sodium chloride', 'strength': '2.6 g'}, {'name': 'Potassium chloride'}, {'name': 'Glucose anhydrous'}],
             [{'name': 'Aluminium hydroxide'}, {'name': 'Magnesium hydroxide'}], [{'name': 'Sodium bicarbonate'}, {'name': 'Calcium carbonate'}],
             [{'name': 'Vitamin B1 100 mg'}, {'name': 'Vitamin B6 200 mg'}, {'name': 'Vitamin B12 200 mcg'}],
             [{'name': 'Neomycin sulphate'}, {'name': 'manufactured by Dermacure Pharma'}, {'name': 'Packaging'}, {'name': 'Unichem Laboratories'}, {'name': 'India'}],
             [{'name': 'NEOMYCIN SULPHATE 3.500 mg (3300 unit)'}, {'name': 'Neomycin'}, {'name': '500 mg Paracetamol'}, {'name': 'Paracetamol'}],
             [{'name': 'Co-trimoxazole 480 mg'}, {'name': 'Calcium 500 mg'}, {'name': 'Zinc'}]]
    page, errors = _page(browser, server)
    for c in cases:
        js = page.evaluate('c => cleanApis(c).map(a => [a.name, a.strength || null])', c)
        py = [[a['name'], a.get('strength')] for a in extract.clean_apis(c)]
        assert js == py, (c, js, py)
    js = [page.evaluate('c => cleanApis(c).map(a => a.name)', c) for c in cases[:5]]
    assert js == [['Sodium chloride', 'Potassium chloride', 'Glucose anhydrous'], ['Aluminium hydroxide', 'Magnesium hydroxide'],
                  ['Sodium bicarbonate', 'Calcium carbonate'], ['Vitamin B1', 'Vitamin B6', 'Vitamin B12'], ['Neomycin sulphate']]
    page.close()


def test_one_unread_scan_does_not_switch_the_kind_rule_off_for_the_others(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    price = make_pdf_lines(tmp_path / 'price.pdf', EDA_PRICING, 'Pricing')               # an EDA pricing letter: no «pricing certificate» phrase
    PIL = pytest.importorskip('PIL.Image')
    blank = tmp_path / 'scan001.pdf'
    PIL.new('RGB', (800, 1100), 'white').save(blank, 'PDF', resolution=100.0)          # an image-only scan nobody could read here (no text at all)
    page, errors = _page(browser, server, "window.DBOCR={available:async()=>false};")
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    _upload(page, '[data-updoc="pricing_certificate"]', [price])
    page.wait_for_selector('[data-docline="price.pdf"] .c-ok', timeout=120000)
    _upload(page, '[data-updoc="other"]', [blank])
    page.wait_for_selector('[data-docline="scan001.pdf"]', timeout=120000)
    page.wait_for_function("() => !document.querySelector('.doccards .c-wait')", timeout=120000)
    page.click('#wizNext'); page.click('#wizNext'); page.click('#wizNext')
    page.fill('[data-api="0"][data-f=manufacturer]', 'Unichem Laboratories')
    page.click('#wizNext')
    page.fill('[data-in=tracking]', 'P-MAA-0002')
    page.click('#wizCreate')
    page.wait_for_selector('text=Requirements board')
    did = page.url.split('/d/')[1].split('/')[0]
    placed, unplaced = _board_when(server, did, lambda p, u: 'scan001.pdf' in u)          # the placement is over once the unread scan is kept aside
    assert placed.get('price.pdf') == 'M1-05' and placed.get('cpp.pdf') == 'M1-14'       # before the fix the pricing letter was left «not placed»
    assert errors == [], errors
    page.close()


def test_a_leaflet_placed_from_the_box_asks_its_type_and_language(server, browser, tmp_path):
    prof = dict(dossier_kind='generic', origin='local', licence='own', activity='new', admin_route='topical',
                apis=[dict(name='Neomycin sulphate', manufacturer='Sichuan Example Pharmaceutical', option='FULL')])
    c = httpx.Client(base_url=server, headers={'X-DB': '1'})
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=prof, product=dict(name='Dermacure', dosageform='topical powder', manufacturer='Example'),
                                            envelope={})).json()['id']
    leaflet = make_pdf_lines(tmp_path / 'leaflet.pdf', ['Summary of Product Characteristics', 'Dermacure topical powder'], 'SmPC').read_bytes()
    assert c.post(f'/api/dossiers/{did}/unplaced', files=[('files', ('leaflet.pdf', io.BytesIO(leaflet), 'application/pdf'))], data={'meta': '{}'}).status_code == 201
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/d/{did}/board')
    page.wait_for_selector('#unplacedBox [data-upl]')
    assert page.locator('#unplacedBox [data-unp]').count() == 1 and page.locator('text=Unassigned documents').count() == 0   # listed once
    page.select_option('#unplacedBox select', 'M1-09')
    page.click('#unplacedBox [data-upl]')
    page.wait_for_selector('#mType')                                                     # the item's details first, as an upload there asks
    page.select_option('#mType', 'spc'); page.select_option('#mLang', 'en')
    page.click('#mGo')
    page.wait_for_selector('#toast:has-text("Placed")')
    docs = [d for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['req_id'] == 'M1-09' for d in s['documents']]
    assert len(docs) == 1 and docs[0]['meta']['pi_type'] == 'spc' and docs[0]['meta']['lang'] == 'en'
    assert errors == [], errors
    page.close()


def test_a_refresh_while_the_documents_are_being_placed_finishes_the_placement(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    gmp = make_pdf_lines(tmp_path / 'gmp certificate.pdf', ['GMP Certificate', 'Certificate Number: EG/GMP/2024/55', 'Manufacturer: Medis S.A.',
                                                           'Egyptian Drug Authority', 'Date of issue: 01/06/2024', 'Valid until: 31/05/2027'])
    page, errors = _page(browser, server)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    _upload(page, '[data-updoc="gmp_certificate"]', [gmp])
    page.wait_for_selector('[data-docline="gmp certificate.pdf"] .c-ok', timeout=120000)
    page.click('#wizNext'); page.click('#wizNext'); page.click('#wizNext')
    page.fill('[data-api="0"][data-f=manufacturer]', 'Unichem Laboratories')
    page.click('#wizNext')
    page.fill('[data-in=tracking]', 'P-MAA-0003')
    held = []
    page.route('**/classify/text', lambda r: held.append(r))                            # the placement hangs here: the user refreshes in the middle of it
    page.click('#wizCreate')
    page.wait_for_selector('text=Requirements board')
    for _ in range(200):
        if held:
            break
        page.wait_for_timeout(100)
    assert held, 'the placement never started'
    did = page.url.split('/d/')[1].split('/')[0]
    page.unroute('**/classify/text')
    page.reload()
    placed, _ = _board_when(server, did, lambda p, u: len(p) >= 2, timeout=120)          # before the fix: nothing resumed, the files never reached the dossier
    assert placed.get('cpp.pdf') == 'M1-14' and placed.get('gmp certificate.pdf') in ('M1-37', 'M1-38')
    page.wait_for_timeout(500)
    assert not any((d['state'] or {}).get('created') == did for d in httpx.get(f'{server}/api/intake/drafts').json())   # the draft went at the end
    page.close()


EDA_LICENCE = ['Arab Republic of Egypt', 'Egyptian Drug Authority', 'Final Registration License for Pharmaceutical Product', 'Trade Name: Dermacure',
               'Dosage Form: Topical Powder', 'Active Ingredient(s) & Each 1g contains:', 'Strength(s): NEOMYCIN SULPHATE 3.500 mg ( 3300 unit )', 'Bacitracin Zinc 4.200 mg (250 unit )',
               'Shelf Life: 36 Months', 'Type of License: Toll Type of Marketing: Local', 'Registration No.: 29925/2022 Invalidation Date: 10-11-2032',
               'License Holder : EXAMPLE PHARM-EGYPT,EGYPT', 'Manufacturer : Example Industries for pharmaceutical industries,EGYPT',
               'Manufacturer Of active substance: NEOMYCIN SULPHATE', 'Sichuan Example Pharmaceutical Co.Ltd,CHINA', 'Bacitracin Zinc', 'North Example Pharmaceutical Huasheng Co. LTD,CHINA',
               'Issue Date: 26/7/2022']


def _to_create(page, tracking):
    """From the documents step to «Create» with the two fields the wizard still asks for."""
    page.click('#wizNext'); page.click('#wizNext'); page.click('#wizNext')
    if not page.input_value('[data-api="0"][data-f=manufacturer]'):
        page.fill('[data-api="0"][data-f=manufacturer]', 'Unichem Laboratories')
    page.click('#wizNext')
    page.fill('[data-in=tracking]', tracking)
    page.click('#wizCreate')
    page.wait_for_selector('text=Requirements board')
    return page.url.split('/d/')[1].split('/')[0]


def test_a_file_the_kind_rule_refused_waits_in_the_box_after_create(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    wrong = make_pdf_lines(tmp_path / 'price letter.pdf', ['Egyptian Drug Authority', 'Pricing Certificate', 'Trade name: Cardiolol 10 mg', 'Public price: 45.00 EGP'], 'Pricing')
    page, errors = _page(browser, server)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    _upload(page, '[data-updoc="gmp_certificate"]', [wrong])                            # a pricing certificate under the GMP card: «not this document»
    page.wait_for_selector('[data-rmdoc="price letter.pdf"]', timeout=120000)
    did = _to_create(page, 'P-MAA-0004')                                                 # the user creates the dossier without deciding about it
    placed, unplaced = _board_when(server, did, lambda p, u: 'price letter.pdf' in u)
    assert placed.get('cpp.pdf') == 'M1-14' and unplaced == ['price letter.pdf']         # before the fix: dropped with the draft, nowhere in the dossier
    box = httpx.get(f'{server}/api/dossiers/{did}/unplaced').json()
    assert box[0]['kind'] == 'pricing' and box[0]['auto'] == 'M1-05'                      # and the box knows where it belongs
    page.wait_for_timeout(500)
    assert not any((d['state'] or {}).get('created') == did for d in httpx.get(f'{server}/api/intake/drafts').json())
    assert errors == [], errors
    page.close()


def test_a_typed_api_cell_never_stops_later_readings(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    lic = make_pdf_lines(tmp_path / 'licence.pdf', EDA_LICENCE)
    page, errors = _page(browser, server)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    page.click('#wizNext'); page.click('#wizNext'); page.click('#wizNext')
    assert page.input_value('[data-api="0"][data-f=name]') == 'Bisoprolol fumarate'
    page.fill('[data-api="0"][data-f=manufacturer]', 'Unichem Laboratories')             # the CPP prints no API manufacturer: the user types it
    page.click('#wizBack'); page.click('#wizBack'); page.click('#wizBack')
    _upload(page, '[data-updoc="registration_licence"]', [lic])                           # a licence read later lists two more actives with their manufacturers
    page.wait_for_selector('[data-docline="licence.pdf"] .c-ok', timeout=120000)
    page.wait_for_function("() => !document.querySelector('.doccards .c-wait')", timeout=120000)
    page.click('#wizNext'); page.click('#wizNext'); page.click('#wizNext')
    rows = page.evaluate("() => [...document.querySelectorAll('[data-api][data-f=name]')].map((i,k) => [i.value, document.querySelector(`[data-api=\"${k}\"][data-f=manufacturer]`).value])")
    assert rows[0] == ['Bisoprolol fumarate', 'Unichem Laboratories']                    # the user's cell stays
    assert [r[0] for r in rows[1:]] == ['Neomycin Sulphate', 'Bacitracin Zinc'] and 'Sichuan' in rows[1][1]   # before the fix: the whole reading was dropped
    page.click('[data-rmapi="2"]')                                                       # the user removes one; the re-merge after a refresh does not bring it back
    page.click('#wizBack')
    _saved(page)
    page.reload()
    page.wait_for_selector('#wizNext', timeout=60000)
    page.wait_for_timeout(1500)
    page.click('#wizNext')
    assert page.evaluate("() => [...document.querySelectorAll('[data-api][data-f=name]')].map(i => i.value)") == ['Bisoprolol fumarate', 'Neomycin Sulphate']
    assert page.input_value('[data-api="0"][data-f=manufacturer]') == 'Unichem Laboratories'
    assert errors == [], errors
    page.click('#wizRestart')
    page.close()


def test_a_file_moved_to_its_card_gets_its_model_reading(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    price = make_pdf_lines(tmp_path / 'price letter.pdf', ['Egyptian Drug Authority', 'Pricing Certificate', 'Trade name: Cardiolol 10 mg', 'Public price: 45.00 EGP'], 'Pricing')
    stub = ("window.__seen=[]; window.DBAI={available:async()=>true, extract:async(prompt, files)=>{ window.__seen.push(files.map(f=>f.name));"
            " return files.some(f=>f.name==='price letter.pdf')?{product:{price:'45.00 EGP', pack:'30 tablets'}, apis:[]}:{product:{name:'Cardiolol 10 mg'}}; }};")
    page, errors = _page(browser, server, stub)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    _upload(page, '[data-updoc="gmp_certificate"]', [price])                            # refused on the GMP card: the model does not read it
    page.wait_for_selector('[data-mvdoc="price letter.pdf"]', timeout=120000)
    assert page.evaluate('window.__seen') == [['cpp.pdf']]
    page.click('[data-mvdoc="price letter.pdf"]')                                        # «move it to the pricing card»: now accepted, the model reads it once
    page.wait_for_function("() => window.__seen.length === 2", timeout=120000)
    page.wait_for_function("() => !document.querySelector('[data-mvdoc]')")
    assert page.evaluate('window.__seen') == [['cpp.pdf'], ['price letter.pdf']]
    page.wait_for_timeout(500)
    assert page.evaluate("() => (S.wiz.aiReads||[]).map(b => b.files)") == [['cpp.pdf'], ['price letter.pdf']]
    assert page.evaluate("() => (S.wiz.intakeFill.product||{}).price") == '45.00 EGP'   # before the fix: never read by the model, nothing from it
    assert errors == [], errors
    page.click('#wizRestart')
    page.close()


def test_a_resumed_placement_runs_once_and_keeps_what_was_edited_on_the_board(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    gmp = make_pdf_lines(tmp_path / 'gmp certificate.pdf', ['GMP Certificate', 'Certificate Number: EG/GMP/2024/56', 'Manufacturer: Medis S.A.',
                                                           'Egyptian Drug Authority', 'Date of issue: 01/06/2024', 'Valid until: 31/05/2027'])
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900})                   # two tabs of one browser share the draft pointer
    errors = []
    a = ctx.new_page(); a.on('pageerror', lambda e: errors.append(str(e)))
    a.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    a.add_init_script("localStorage.setItem('db.lang','en');")
    a.goto(server + '/#/new'); a.wait_for_selector('#intakeBtn')
    _upload(a, '[data-updoc="registration_licence"]', [cpp])
    a.wait_for_selector('#intakeReview', timeout=120000)
    _upload(a, '[data-updoc="gmp_certificate"]', [gmp])
    a.wait_for_selector('[data-docline="gmp certificate.pdf"] .c-ok', timeout=120000)
    held = []
    a.route('**/classify/text', lambda r: held.append(r))                               # tab A hangs in the middle of the placement
    did = _to_create(a, 'P-MAA-0005')
    for _ in range(200):
        if held:
            break
        a.wait_for_timeout(100)
    assert held, 'the placement never started'
    c = httpx.Client(base_url=server, headers={'X-DB': '1'})
    data = c.get(f'/api/dossiers/{did}/data').json()
    assert data.get('apis'), 'the read data reached the dossier before the placement'
    data['product'] = dict(data.get('product') or {}, name_ar='كارديولول')                # meanwhile the data is edited on the board
    c.put(f'/api/dossiers/{did}/data', json=data)
    b = ctx.new_page(); b.on('pageerror', lambda e: errors.append(str(e)))
    b.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    b.goto(server + '/#/new')                                                            # tab B opens: the same draft, created already
    b.wait_for_timeout(2000)
    held[0].continue_()                                                                  # tab A goes on; tab B waited for it and finds nothing left to place
    placed, _ = _board_when(server, did, lambda p, u: len(p) >= 2, timeout=120)
    b.wait_for_timeout(3000)
    board = httpx.get(f'{server}/api/dossiers/{did}/board').json()
    names = [d['filename'] for s in board['slots'] for d in s['documents']]
    assert sorted(names) == ['cpp.pdf', 'gmp certificate.pdf'], names                     # each file once: before the fix tab B placed them again
    assert c.get(f'/api/dossiers/{did}/data').json()['product']['name_ar'] == 'كارديولول'  # before the fix: overwritten by the resumed run's second write
    assert not any((d['state'] or {}).get('created') == did for d in httpx.get(f'{server}/api/intake/drafts').json())
    assert errors == [], errors
    ctx.close()


def test_a_resumed_placement_finishes_the_readable_conversions(server, browser, tmp_path):
    prof = dict(dossier_kind='generic', origin='local', licence='own', activity='new', admin_route='topical',
                apis=[dict(name='Neomycin sulphate', manufacturer='Sichuan Example Pharmaceutical', option='FULL')])
    c = httpx.Client(base_url=server, headers={'X-DB': '1'})
    did = c.post('/api/dossiers', json=dict(name='Dermacure', profile=prof, product=dict(name='Dermacure', dosageform='topical powder', manufacturer='Example'),
                                            envelope={})).json()['id']
    scan = make_pdf_lines(tmp_path / 'scan.pdf', ['GMP Certificate', 'Example Pharma'], 'GMP').read_bytes()
    slot = next(s['slot_id'] for s in c.get(f'/api/dossiers/{did}/board').json()['slots'] if s['req_id'] == 'M1-37')
    doc = c.post(f'/api/dossiers/{did}/slots/{slot}/documents', files={'file': ('scan.pdf', io.BytesIO(scan), 'application/pdf')}).json()   # placed before the refresh
    state = {'step': 4, 'created': did, 'dataWritten': True, 'd': {'name': 'Dermacure', 'trade': 'Dermacure', 'apis': []}, 'docs': {'scan.pdf': {'kind': 'gmp_certificate', 'status': 'ok'}},
             'texts': {'scan.pdf': {'filename': 'scan.pdf', 'text': 'GMP Certificate', 'pages': 1, 'scanned': True, 'ocr': True, 'ocr_where': 'browser'}}, 'kinds': {'scan.pdf': 'gmp'}}
    draft = c.post('/api/intake/drafts', json={'state': state}).json()['id']
    c.post(f'/api/intake/drafts/{draft}/files', files={'file': ('scan.pdf', io.BytesIO(scan), 'application/pdf')}, data={'kind': 'gmp_certificate'})
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    page.add_init_script("localStorage.setItem('db.lang','en')")
    page.goto(f'{server}/#/d/{did}/board')
    page.wait_for_selector('text=Requirements board')
    page.evaluate("() => { window.__conv = []; window.makeReadable = async (d, id, name) => { window.__conv.push([id, name]); return {id}; }; }")
    page.evaluate(f"() => {{ localStorage.setItem('db.wizDraft', '{draft}'); return wizResume(); }}")
    assert page.evaluate('window.__conv') == [[doc['id'], 'scan.pdf']]                   # before the fix: nothing left to place, so no conversion and the draft gone
    page.wait_for_timeout(500)
    assert c.get('/api/intake/drafts/' + draft).status_code == 404
    assert errors == [], errors
    page.close()
