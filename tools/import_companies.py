"""Import companies from a PUBLIC list into the directory as unclaimed pages (B-01, migration 0052).

  python3 tools/import_companies.py companies.csv --admin admin@drugbox.app            # dry run: what would happen, nothing written
  python3 tools/import_companies.py companies.csv --admin admin@drugbox.app --commit   # write

The database decides (admin_import_companies, 0052): every row is validated, compared with the companies already in the
directory (same commercial registry number, or the same English / Arabic name once spelling, case, punctuation and legal
suffixes are set aside) and with the rows before it, and created as status 'unclaimed', source 'public_list', no owner —
a page its company can claim (with its registry document) from Companies → Add or claim. Nothing is invented: a row
without a `source` (the public list it comes from, e.g. "EDA licensed manufacturers list, 2026-09") is refused.

CSV columns (UTF-8, header row; only name, sectors and source are required):
  name, name_ar, sectors (";"-separated: Manufacturer; Cosmetics; CMO / Toll; API & excipients; Packaging; Labs & testing;
  Distribution; Regulatory & consulting; Supplements), governorate, city, address, phone, email, website, registry,
  site (a plant's name), dosage_forms (";"-separated), certificates (";"-separated, listed as "Public industry list" —
  never shown as checked by Drugbox), source
The import runs as a Drugbox admin's account (--admin: their e-mail), so the database records who did it.
Connection: PGHOST / PGPORT / PGUSER / DB_NAME (local defaults), or DATABASE_URL. Up to 2,000 rows per call (larger files
are sent in parts). Exit code 1 when any row is invalid (with --strict) or the database refuses the import."""
import argparse, csv, json, os, subprocess, sys

COLS = ['name', 'name_ar', 'sectors', 'governorate', 'city', 'address', 'phone', 'email', 'website', 'registry', 'site', 'dosage_forms', 'certificates', 'source']

def psql_cmd():
    if os.environ.get('DATABASE_URL'): return ['psql', os.environ['DATABASE_URL'], '-X', '-tA', '-v', 'ON_ERROR_STOP=1']
    return ['psql', '-X', '-tA', '-v', 'ON_ERROR_STOP=1', '-h', os.environ.get('PGHOST', '/tmp'), '-p', os.environ.get('PGPORT', '5433'),
            '-U', os.environ.get('PGUSER', 'postgres'), '-d', os.environ.get('DB_NAME', 'drugbox_live')]

def run_sql(sql):
    r = subprocess.run(psql_cmd(), input=sql, capture_output=True, text=True)
    if r.returncode: raise SystemExit('the database refused the import: ' + next((l.split('ERROR:', 1)[1].strip() for l in r.stderr.splitlines() if 'ERROR:' in l), r.stderr.strip()[-200:]))
    return r.stdout.strip()

def lit(s):   # a SQL literal with dollar quoting that cannot be closed by the data
    tag = 'imp'
    while ('$%s$' % tag) in s: tag += 'x'
    return '$%s$%s$%s$' % (tag, s, tag)

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('csv'); ap.add_argument('--admin', required=True, help="the Drugbox admin's e-mail (their account runs the import)")
    ap.add_argument('--commit', action='store_true', help='write (default: dry run)'); ap.add_argument('--strict', action='store_true', help='exit 1 when any row is invalid')
    ap.add_argument('--json', action='store_true', help='print the full result as JSON')
    a = ap.parse_args()
    with open(a.csv, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        unknown = [c for c in (rd.fieldnames or []) if c and c.strip().lower() not in COLS]
        if unknown: raise SystemExit('unknown column(s): %s (allowed: %s)' % (', '.join(unknown), ', '.join(COLS)))
        rows = [{k.strip().lower(): (v or '').strip() for k, v in r.items() if k} for r in rd]
    if not rows: raise SystemExit('the file has no rows')
    total = {'created': 0, 'duplicates': 0, 'invalid': 0, 'results': []}
    for i in range(0, len(rows), 2000):
        part = rows[i:i + 2000]
        sql = ("begin;\n"
               "select set_config('request.jwt.claims', json_build_object('sub', u.id, 'role', 'authenticated')::text, true), set_config('request.jwt.claim.sub', u.id::text, true)\n"
               "  from auth.users u where lower(u.email) = lower(%s);\n"
               "select public.admin_import_companies(%s::jsonb, %s);\ncommit;\n") % (lit(a.admin), lit(json.dumps(part, ensure_ascii=False)), 'false' if a.commit else 'true')
        out = [l for l in run_sql(sql).splitlines() if l.startswith('{')]
        if not out: raise SystemExit('no result from the database (is %s a Drugbox admin?)' % a.admin)
        res = json.loads(out[-1])
        for r in res['results']: r['row'] += i
        for k in ('created', 'duplicates', 'invalid'): total[k] += res[k]
        total['results'] += res['results']
    if a.json: print(json.dumps(total, ensure_ascii=False, indent=1))
    else:
        for r in total['results']:
            if r['status'] != 'created' and r['status'] != 'would create':
                print('row %4d  %-10s %s%s' % (r['row'], r['status'], r.get('name') or '', ' — ' + r['reason'] if r.get('reason') else ' (already in the directory: %s)' % r.get('slug') if r.get('slug') else ''))
        print('%s: %d %s, %d already in the directory, %d invalid' % ('import' if a.commit else 'dry run', total['created'], 'created' if a.commit else 'would be created', total['duplicates'], total['invalid']))
    sys.exit(1 if (a.strict and total['invalid']) else 0)

if __name__ == '__main__': main()
