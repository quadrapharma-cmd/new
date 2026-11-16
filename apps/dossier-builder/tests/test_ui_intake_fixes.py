"""Review fixes in the page (Playwright): a refresh keeps what the user typed and chose, a file refused by the kind rule never fills the
form (the model reads only the accepted files), another document with the same file name is kept under a free name, the page's copy of
the active-substance cleaning matches the engine, a scan without text is refused on its line (and its searchable copy takes its place)
while the other files go on, and a leaflet placed
from the «not placed yet» box asks for its type and language, a file the kind rule refused waits in that box after «Create» (never lost),
a typed API cell never stops later readings, a file moved to its card by «move it» gets its model reading, and a resumed placement runs once
and writes the data once. Fictional product «Dermacure» / «Cardiolol»."""
import io, json
import httpx
import pytest
from fixtures_pdf import make_pdf, make_pdf_lines
from wizard_steps import to_upload, to_card, confirm_card
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
    to_upload(page)                                                                     # «ملف جديد» opens on the country: on to the upload station
    return page, errors


def _back_to_upload(page):
    """From the product card (or the reading station) back to the upload station."""
    for _ in range(3):
        if page.locator('#intakeBtn').count():
            return
        page.click('#wizBack')
    page.wait_for_selector('#intakeBtn')


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
    to_card(page)
    assert page.input_value('[data-in=trade]') == 'Cardiolol 10 mg'                     # read from the CPP
    page.fill('[data-in=trade]', 'Cardiolol Plus')                                      # the user corrects it
    assert page.locator('[data-k=origin][data-v=imported].on').count() == 1
    page.click('[data-k=origin][data-v=local]')                                         # and chooses another origin
    _saved(page)
    page.reload()
    page.wait_for_selector('[data-k=origin]', timeout=60000)
    page.wait_for_timeout(1500)                                                         # the restored readings are merged again
    assert page.locator('[data-k=origin][data-v=local].on').count() == 1 and page.locator('[data-k=licence][data-v=own].on').count() == 1
    assert page.input_value('[data-in=trade]') == 'Cardiolol Plus'                      # before the fix: «Cardiolol 10 mg» and «imported» came back
    assert errors == [], errors
    page.click('#wizRestart'); page.click('#wizRestart')                      # «start over» asks once more before it deletes the draft
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
    page.click('#wizRestart'); page.click('#wizRestart')                      # «start over» asks once more before it deletes the draft
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
    page.wait_for_function("() => !document.querySelector('#upList .c-wait') && !S.wiz.busyN && document.querySelectorAll('[data-card=\"pricing_certificate\"].ok').length === 1", timeout=120000)   # read under the pricing card (the card is drawn once the reading is in it)
    assert page.evaluate("() => S.wiz.docs['scan (2).pdf'].kind") == 'pricing_certificate'
    _upload(page, '[data-updoc="registration_licence"]', [a])                            # the very same file again: still «already uploaded»
    page.wait_for_selector('#toast:has-text("already uploaded")')
    assert page.locator('[data-docline]').count() == 2
    assert errors == [], errors
    page.click('#wizRestart'); page.click('#wizRestart')                      # «start over» asks once more before it deletes the draft
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


def test_a_scan_without_text_is_refused_and_the_others_go_on(server, browser, tmp_path):
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    price = make_pdf_lines(tmp_path / 'price.pdf', EDA_PRICING, 'Pricing')               # an EDA pricing letter: no «pricing certificate» phrase
    PIL = pytest.importorskip('PIL.Image')
    blank = tmp_path / 'scan001.pdf'
    PIL.new('RGB', (800, 1100), 'white').save(blank, 'PDF', resolution=100.0)          # an image-only scan: no text of its own
    page, errors = _page(browser, server)
    _upload(page, '[data-updoc="registration_licence"]', [cpp])
    page.wait_for_selector('#intakeReview', timeout=120000)
    _upload(page, '[data-updoc="pricing_certificate"]', [price])
    page.wait_for_selector('[data-docline="price.pdf"] .c-ok', timeout=120000)
    _upload(page, '#intakeBtn', [blank])
    page.wait_for_selector('[data-docline="scan001.pdf"] [data-notext]', timeout=120000)   # refused on its line …
    why = page.inner_text('[data-docline="scan001.pdf"]')
    assert 'no text' in why and 'searchable PDF' in why and 'NP.CAPP.065' in why            # … with the reason and what to do
    page.wait_for_function("() => !document.querySelector('#upList .c-wait')", timeout=120000)
    to_card(page)
    page.fill('[data-api="0"][data-f=manufacturer]', 'Unichem Laboratories')
    page.fill('[data-in=tracking]', 'P-MAA-0002')
    confirm_card(page, files=2, approve=True, then='board')                               # the two read files wait in the proposed tree; approved, each goes into its item
    page.wait_for_selector('h1:has-text("Dossier tree and what is missing")')
    did = page.url.split('/d/')[1].split('/')[0]
    placed, unplaced = _board_when(server, did, lambda p, u: 'price.pdf' in p and 'cpp.pdf' in p)
    assert placed.get('price.pdf') == 'M1-05' and placed.get('cpp.pdf') == 'M1-14'
    assert 'scan001.pdf' not in placed and 'scan001.pdf' not in unplaced                   # never sent to the dossier
    assert errors == [], errors
    page.close()


def test_a_refused_scan_is_replaced_by_its_searchable_copy(server, browser, tmp_path):
    PIL = pytest.importorskip('PIL.Image')
    (tmp_path / 'scan').mkdir()
    blank = tmp_path / 'scan' / 'gmp.pdf'
    PIL.new('RGB', (800, 1100), 'white').save(blank, 'PDF', resolution=100.0)
    good = make_pdf_lines(tmp_path / 'gmp.pdf', ['Certificate of GMP Compliance of a Manufacturer', 'Medis S.A., Nabeul, Tunisia',
                                                 'The manufacturer complies with Good Manufacturing Practice'], 'GMP')
    page, errors = _page(browser, server)
    _upload(page, '#intakeBtn', [blank])
    page.wait_for_selector('[data-docline="gmp.pdf"] [data-notext]', timeout=120000)
    _upload(page, '#intakeBtn', [good])                                            # the same name, now searchable
    page.wait_for_selector('[data-docline="gmp.pdf"] .c-ok', timeout=120000)
    assert page.locator('[data-docline="gmp.pdf"]').count() == 1 and page.locator('[data-notext]').count() == 0
    assert errors == [], errors
    page.close()


def test_a_leaflet_placed_from_the_proposed_tree_asks_its_type_and_language(server, browser, tmp_path):
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
    # a file waiting for a place: said once on the board, with the way to the proposed tree — where it is placed (stage 3: the
    # board's own box of waiting files is gone)
    page.wait_for_selector('#unplacedNote')
    assert 'Waiting for a place' in page.inner_text('#unplacedNote') and page.locator('#unplacedBox').count() == 0 and page.locator('text=Unassigned documents').count() == 0
    page.click('#unplacedNote a')
    page.wait_for_selector('[data-pw] [data-tplace]', timeout=60000)
    assert page.locator('[data-pw]').count() == 1                                        # listed once
    page.select_option('[data-pw] [data-tplace]', 'M1-09')
    page.wait_for_function("() => (document.querySelector('[data-pw]') || {dataset: {}}).dataset.tplaceof === 'M1-09' && !S.prepWaitP && !!document.getElementById('treeGo')", timeout=60000)
    page.click('#treeGo')
    page.wait_for_selector('#mType')                                                     # the item's details first, as an upload there asks
    page.select_option('#mType', 'spc'); page.select_option('#mLang', 'en')
    page.click('#mGo')
    page.wait_for_function("() => location.hash.endsWith('/prepare')", timeout=60000)      # all in their items: on to preparing them
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
    to_card(page)
    page.fill('[data-api="0"][data-f=manufacturer]', 'Unichem Laboratories')
    page.fill('[data-in=tracking]', 'P-MAA-0003')
    held = []
    page.route('**/unplaced', lambda r: held.append(r) if r.request.method == 'POST' else r.continue_())   # the files' way into the dossier hangs here: the user refreshes in the middle of it
    page.click('#wizCreate')
    page.wait_for_selector('h1:has-text("Proposed tree")')
    page.wait_for_function("() => /Bringing your documents into the dossier/.test(document.getElementById('view').innerText)", timeout=30000)   # said while they are on their way — never «nothing is waiting»
    assert 'No document is waiting' not in page.inner_text('#view')
    for _ in range(200):
        if held:
            break
        page.wait_for_timeout(100)
    assert held, 'the placement never started'
    did = page.url.split('/d/')[1].split('/')[0]
    page.unroute('**/unplaced')
    page.reload()
    placed, waiting = _board_when(server, did, lambda p, u: len(u) >= 2, timeout=120)    # before the fix: nothing resumed, the files never reached the dossier
    assert placed == {} and sorted(waiting) == ['cpp.pdf', 'gmp certificate.pdf']         # each in the waiting box once, nothing placed before the tree is approved
    page.wait_for_function("() => location.hash.endsWith('/tree') && document.querySelectorAll('#treeOut [data-pw]').length === 2", timeout=60000)
    assert page.locator('[data-titem="M1-14"] [data-pw]').count() == 1                   # and the tree proposes each its place
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
    """From the upload station to the confirmed card, with the two fields the card still asks for: the proposed tree opens."""
    to_card(page)
    if not page.input_value('[data-api="0"][data-f=manufacturer]'):
        page.fill('[data-api="0"][data-f=manufacturer]', 'Unichem Laboratories')
    page.fill('[data-in=tracking]', tracking)
    page.click('#wizCreate')
    page.wait_for_selector('h1:has-text("Proposed tree")')
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
    placed, unplaced = _board_when(server, did, lambda p, u: len(u) >= 2)
    assert placed == {} and sorted(unplaced) == ['cpp.pdf', 'price letter.pdf']           # before the fix: dropped with the draft, nowhere in the dossier
    box = {x['filename']: x for x in httpx.get(f'{server}/api/dossiers/{did}/unplaced').json()}
    assert box['price letter.pdf']['kind'] == 'pricing' and box['price letter.pdf']['auto'] == 'M1-05'   # and the box knows where it belongs: by what it is, not by the place it was given
    assert box['cpp.pdf']['auto'] == 'M1-14'
    page.wait_for_function("() => document.querySelectorAll('#treeOut [data-pw]').length === 2", timeout=60000)
    assert page.locator('[data-titem="M1-05"] [data-pw]').count() == 1 and 'price letter.pdf' in page.inner_text('[data-titem="M1-05"]')   # the tree shows it at its own item
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
    to_card(page)
    assert page.input_value('[data-api="0"][data-f=name]') == 'Bisoprolol fumarate'
    page.fill('[data-api="0"][data-f=manufacturer]', 'Unichem Laboratories')             # the CPP prints no API manufacturer: the user types it
    _back_to_upload(page)
    _upload(page, '[data-updoc="registration_licence"]', [lic])                           # a licence read later lists two more actives with their manufacturers
    page.wait_for_selector('[data-docline="licence.pdf"] .c-ok', timeout=120000)
    page.wait_for_function("() => !document.querySelector('#upList .c-wait')", timeout=120000)
    to_card(page)
    rows = page.evaluate("() => [...document.querySelectorAll('[data-api][data-f=name]')].map((i,k) => [i.value, document.querySelector(`[data-api=\"${k}\"][data-f=manufacturer]`).value])")
    assert rows[0] == ['Bisoprolol fumarate', 'Unichem Laboratories']                    # the user's cell stays
    assert [r[0] for r in rows[1:]] == ['Neomycin Sulphate', 'Bacitracin Zinc'] and 'Sichuan' in rows[1][1]   # before the fix: the whole reading was dropped
    page.click('[data-rmapi="2"]')                                                       # the user removes one; the re-merge after a refresh does not bring it back
    page.click('#wizBack')
    _saved(page)
    page.reload()
    page.wait_for_selector('#wizNext', timeout=60000)
    page.wait_for_timeout(1500)
    to_card(page)
    assert page.evaluate("() => [...document.querySelectorAll('[data-api][data-f=name]')].map(i => i.value)") == ['Bisoprolol fumarate', 'Neomycin Sulphate']
    assert page.input_value('[data-api="0"][data-f=manufacturer]') == 'Unichem Laboratories'
    assert errors == [], errors
    page.click('#wizRestart'); page.click('#wizRestart')                      # «start over» asks once more before it deletes the draft
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
    page.click('#wizRestart'); page.click('#wizRestart')                      # «start over» asks once more before it deletes the draft
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
    a.goto(server + '/#/new'); to_upload(a)
    _upload(a, '[data-updoc="registration_licence"]', [cpp])
    a.wait_for_selector('#intakeReview', timeout=120000)
    _upload(a, '[data-updoc="gmp_certificate"]', [gmp])
    a.wait_for_selector('[data-docline="gmp certificate.pdf"] .c-ok', timeout=120000)
    held = []
    a.route('**/unplaced', lambda r: held.append(r) if r.request.method == 'POST' and not held else r.continue_())   # tab A hangs with its first file on its way into the dossier
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
    held[0].continue_()                                                                  # tab A goes on; tab B waited for it and finds nothing left to bring
    placed, _ = _board_when(server, did, lambda p, u: len(u) >= 2, timeout=120)
    b.wait_for_timeout(3000)
    board = httpx.get(f'{server}/api/dossiers/{did}/board').json()
    names = [d['filename'] for d in board['unassigned']]
    assert sorted(names) == ['cpp.pdf', 'gmp certificate.pdf'] and placed == {}, names    # each file in the waiting box once: before the fix tab B brought them again
    assert c.get(f'/api/dossiers/{did}/data').json()['product']['name_ar'] == 'كارديولول'  # before the fix: overwritten by the resumed run's second write
    assert not any((d['state'] or {}).get('created') == did for d in httpx.get(f'{server}/api/intake/drafts').json())
    assert errors == [], errors
    ctx.close()


def test_the_card_is_not_confirmed_before_what_was_read_is_in_it(server, browser, tmp_path):
    """Found running the owner's real files through the wizard with the machine busy (16/11/2026): each file's line says «read» as soon
    as its own reading ends, and what was read is merged into the card a moment later. In that moment «اعتماد البطاقة» could be
    pressed — the dossier made from a card not yet filled. The button now waits for the reading to be in the card."""
    cpp = make_pdf_lines(tmp_path / 'cpp.pdf', CPP, 'WHO Certification Scheme')
    page, errors = _page(browser, server)
    held = []
    page.route('**/api/extract/text?target=dossier', lambda r: held.append(r) if not held else r.continue_())   # the merge into the card takes its time
    with page.expect_file_chooser() as fc:
        page.click('#intakeBtn')
    fc.value.set_files([str(cpp)])
    for _ in range(300):
        if held:
            break
        page.wait_for_timeout(100)
    assert held, 'the reading was never merged'
    assert page.evaluate("() => (S.wiz.prog['cpp.pdf'] || {}).stage") == 'done'          # the file itself is read…
    to_card(page)
    assert page.is_disabled('#wizCreate') and page.locator('#cardBusy').count() == 1     # …and the card still waits for what it gave
    assert page.input_value('[data-in=trade]') == ''
    held[0].continue_()
    page.wait_for_function("() => { const b = document.getElementById('wizCreate'); return b && !b.disabled; }", timeout=60000)
    assert page.input_value('[data-in=trade]') == 'Cardiolol 10 mg' and page.locator('#cardBusy').count() == 0
    assert not errors, errors
    page.close()
