"""PdfCraft in the browser (Playwright): an item's document opens in the page viewer, a search lights its place on the page, a real
redaction makes a new version, the comparison with the version before shows the change in its line with a marked copy, and a page
turned the right way makes another."""
import json
import pytest
from dossier_engine import pdfcraft

pw = pytest.importorskip('playwright.sync_api')
pytestmark = pytest.mark.skipif(not pdfcraft.available(), reason='PdfCraft is not built here (tools/pdfcraft/build.sh)')
from fixtures_pdf import make_pdf_lines
from test_ui_priority2 import server, dossier, upload, page_of          # noqa: F401 — the shared server fixture


def test_pages_search_redaction_and_comparison(server, tmp_path):
    did = dossier(server)
    data = make_pdf_lines(tmp_path / 'stab.pdf', ['Stability summary', 'Shelf life: 24 months', 'Confidential price: EGP 45.00'], 'Stability').read_bytes()
    upload(server, did, 'P-16', 'stability.pdf', data)
    errors = []
    with pw.sync_playwright() as p:
        b = p.chromium.launch()
        page = page_of(b, server)
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(f'{server}/#/d/{did}/board')
        page.wait_for_function("() => typeof S !== 'undefined' && S.board && S.caps && S.caps.pdf_engine && S.caps.pdf_engine.available")
        page.evaluate("openWhy('P-16')")
        page.click('[data-pgv]')
        page.wait_for_function("() => { const i = document.querySelector('#pgImg'); return i && i.complete && i.naturalWidth > 0; }")
        page.fill('#pgQ', 'shelf life')
        page.dispatch_event('#pgQ', 'change')
        page.wait_for_selector('.pghit')
        assert '1' in page.inner_text('#pgHits')
        box = page.locator('.pghit').first.bounding_box()
        img = page.locator('#pgImg').bounding_box()
        assert box['y'] < img['y'] + img['height'] * 0.25                     # near the top of the page, where the line is
        page.click('#pgBack')
        page.click('[data-red]')
        page.fill('#redW', 'EGP 45.00')
        page.click('#redGo')
        page.wait_for_function("() => S.board && S.board.slots.find(s => s.slot_id === 'P-16').documents[0].version === 2", timeout=60000)
        page.evaluate("openWhy('P-16')")
        page.click('[data-cmpv]')
        page.wait_for_selector('#dBody mark')
        body = page.inner_text('#dBody')
        assert 'EGP 45.00' in body and 'Confidential price' in body
        assert page.locator('#dBody a[href$="/compare.pdf"]').count() == 1
        page.click('#cmpBack')
        page.click('[data-pgv]')                                                # a page turned the right way: a new version again
        page.wait_for_selector('#pgTurn')
        page.click('#pgTurn')
        page.wait_for_function("() => S.board && S.board.slots.find(s => s.slot_id === 'P-16').documents[0].version === 3", timeout=60000)
        assert page.locator('#pgNotes').get_attribute('href').endswith('/notes.pdf')
        b.close()
    assert not errors, errors
