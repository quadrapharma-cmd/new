"""The browser's trade text rules (web/src/trade_terms.js) and the database's (0071) give the same answers on a corpus,
and no written word reaches two canonical words. Run: python3 tools/trade/norm_parity.py [--db drugbox_live]
Exit 1 on any difference (prints the first 20)."""
import os, sys, json, subprocess, random
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB = sys.argv[sys.argv.index('--db') + 1] if '--db' in sys.argv else os.environ.get('DB_NAME', 'drugbox_live')
PG = ['psql', '-h', os.environ.get('PGHOST', '/tmp'), '-p', os.environ.get('PGPORT', '5433'), '-U', 'postgres', '-d', DB, '-At', '-v', 'ON_ERROR_STOP=1']
terms = [l.rstrip('\n').split('\t') for l in open(os.path.join(ROOT, 'tools/trade/terms.tsv'), encoding='utf-8') if l.strip() and not l.startswith('#')]
words = [v for _, c, vs in terms for v in vs.split('|') + [c]]
corpus = list(words) + [
    'بانادول إكسترا ٥٠٠ ملجم أقراص 20علبة، خصم 30٪ Exp 5/26', 'Metformin HCl 850mg tab — 1,200 box (exp 03/2027)',
    'أوجمنتين 1 جم ١٤ قرص', 'كونكور 5مجم 30 قرص متوفر كمية', 'Ventolin inhaler 100 mcg', 'فيتامين د ٥٠٠٠٠ وحدة دولية',
    'Dr. Ahmed\'s list...', '[12/10/2025, 10:15 PM] Ali: متوفر بنادول', 'ـــكونكورــــ', 'سِيبروفلوكساسين ٥٠٠ مجم',
    'cream 1.5% 30 g', '.5mg', '2.0 ml', '٣٫٥ ملي جرام', 'ﻻ تفوت', 'AUGMENTIN 625MG TAB', 'O\'Reilly-Smith', 'ک ی گ', '%%30%', '']
rnd = random.Random(7)
for _ in range(400):
    corpus.append(' '.join(rnd.choice(words + ['500', '٢٠', '30%', 'x', '/', '—', '1.5']) for _ in range(rnd.randint(1, 6))))
inp = json.dumps(corpus, ensure_ascii=False)
js = ("global.window={};require(%s);var T=window.dxTradeText,c=JSON.parse(require('fs').readFileSync(0,'utf8'));"
      "process.stdout.write(JSON.stringify(c.map(function(s){return [T.norm(s),T.tokens(s).join(' '),T.root(s),T.key(s),T.searchText(s)];})));") % json.dumps(os.path.join(ROOT, 'web/src/trade_terms.js'))
jout = json.loads(subprocess.run(['node', '-e', js], input=inp, capture_output=True, text=True, check=True).stdout)
sql = ("select coalesce(json_agg(json_build_array(public.trade_norm(s), array_to_string(public.trade_tokens(s), ' '), public.trade_root(s), public.trade_key(s), public.trade_search_text(s)) order by o), '[]') "
       "from json_array_elements_text(%s::json) with ordinality as x(s, o)") % ("'" + inp.replace("'", "''") + "'")
sout = json.loads(subprocess.run(PG + ['-c', sql], capture_output=True, text=True, check=True).stdout)
bad = [(corpus[i], a, b) for i, (a, b) in enumerate(zip(jout, sout)) if a != b]
# a written word that two canonical words claim (the database keeps one of them, the browser the first): never
nj = json.loads(subprocess.run(['node', '-e', "global.window={};require(%s);var T=window.dxTradeText;var o={};T.terms.forEach(function(r){r[2].concat([r[1]]).forEach(function(v){var n=T.norm(v);(o[n]=o[n]||{})[r[1]]=1;});});process.stdout.write(JSON.stringify(o));" % json.dumps(os.path.join(ROOT, 'web/src/trade_terms.js'))], capture_output=True, text=True, check=True).stdout)
clash = [(n, list(c)) for n, c in nj.items() if len(c) > 1]
for b in bad[:20]: print('DIFF', json.dumps(b, ensure_ascii=False))
for c in clash: print('CLASH', json.dumps(c, ensure_ascii=False))
print('trade text parity: %d strings, %d differences, %d clashes' % (len(corpus), len(bad), len(clash)))
sys.exit(1 if bad or clash else 0)
