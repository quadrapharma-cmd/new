"""Another validator's report beside ours (updates list, item 27): read from PDF, Excel, CSV or HTML; matched criterion by criterion;
every difference explained."""
import io
from fastapi.testclient import TestClient
from fixtures_pdf import make_pdf
from dossier_engine.app.api import create_app
from dossier_engine.validators import compare_report as cr
from test_api import new
from test_lifecycle_api import fill_all

OURS = {'results': [
    {'rule': 'EU-14.5', 'status': 'pass', 'text': 'An envelope for each country', 'failures': []},
    {'rule': 'EU-15.BP3', 'status': 'not_run', 'reason': 'not automated yet (manual/visual check)', 'text': 'Recommended file names', 'failures': []},
    {'rule': 'EU-1.1', 'status': 'fail', 'text': 'The specified filename is used', 'failures': ['util/dtd/ich-ectd-3-2.dtd missing']},
    {'rule': 'EU-2.3', 'status': 'pass', 'text': 'x', 'failures': []},
    {'rule': 'EG-PF-11.2', 'status': 'fail', 'text': 'A leaf points to a file that exists', 'failures': ['m3/a.pdf']}]}


def test_their_report_is_read_from_html_and_every_difference_explained():
    their = (b'<table><tr><th>Criterion</th><th>Result</th></tr>'
             b'<tr><td>14.5</td><td>Failed</td><td>No envelope for de</td></tr>'
             b'<tr><td>15.BP3</td><td>Error</td></tr><tr><td>1.1</td><td>Passed</td></tr>'
             b'<tr><td>2.3</td><td>Passed</td></tr><tr><td>99.9</td><td>Failed</td></tr></table>')
    t = cr.read('report.html', their)
    assert t['14.5']['status'] == 'fail' and t['1.1']['status'] == 'pass' and t['99.9']['status'] == 'fail'
    res = cr.compare(t, OURS)
    by = {r['rule']: r for r in res['rows']}
    assert by['2.3']['agree'] and not by['14.5']['agree'] and 'We pass it' in by['14.5']['why']
    assert 'do not run it automatically' in by['15.BP3']['why']
    assert 'We fail it' in by['1.1']['why'] and 'ich-ectd-3-2.dtd' in by['1.1']['why']
    assert 'Not one of our criteria' in by['99.9']['why']
    assert 'does not name it' in by['EG-PF-11.2']['why']                                  # we fail it, their report is silent
    assert res['counts'] == {'agree': 1, 'differ': 5, 'theirs': 5}


def test_a_csv_report_and_the_worst_result_of_a_rule():
    t = cr.read('r.csv', b'rule,result\n14.5,passed\n14.5,failed\n15.BP3,warning\n')
    assert t['14.5']['status'] == 'fail' and t['15.BP3']['status'] == 'warning'


def test_compare_with_the_report_of_an_export(tmp_path):
    c = TestClient(create_app(tmp_path / 'ws'))
    pdf = make_pdf(tmp_path / 'd.pdf', 'doc').read_bytes()
    did = new(c)
    fill_all(c, did, pdf)
    e = c.post(f'/api/dossiers/{did}/export', json={'acknowledge_provisional': True, 'outputs': ['ectd32']})
    assert e.status_code == 201, e.text
    their = b'Validation report\nEG-PF-1.1 The specified filename is used Passed\nEG-PF-11.2 leaf file exists Failed: m3/x.pdf\n'
    r = c.post(f"/api/dossiers/{did}/exports/{e.json()['id']}/compare-report", files={'file': ('their.txt', io.BytesIO(their), 'text/plain')})
    assert r.status_code == 200, r.text
    rows = {x['rule']: x for x in r.json()['rows']}
    assert rows['EG-PF-1.1']['agree'] and not rows['EG-PF-11.2']['agree'] and rows['EG-PF-11.2']['ours'] == 'pass'
    bad = c.post(f"/api/dossiers/{did}/exports/{e.json()['id']}/compare-report", files={'file': ('x.txt', io.BytesIO(b'nothing here'), 'text/plain')})
    assert bad.status_code == 422 and bad.json()['detail']['code'] == 'E-REPORT-UNREAD'
