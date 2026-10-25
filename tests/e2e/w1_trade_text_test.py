"""W-trade: the trade words and text rules are generated from tools/trade/terms.tsv and the browser's copy answers as the database
does (Arabic ⇄ English names and forms, Arabic-Indic digits, strengths): gen_terms --check and norm_parity on the live database."""
import os, subprocess, sys
from _dx import DB, T, done
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
r = subprocess.run([sys.executable, ROOT + '/tools/trade/gen_terms.py', '--check'], capture_output=True, text=True)
T('the generated database and browser copies match tools/trade/terms.tsv', r.returncode == 0, r.stdout + r.stderr)
r = subprocess.run([sys.executable, ROOT + '/tools/trade/norm_parity.py', '--db', DB], capture_output=True, text=True)
T('the browser and the database normalise, tokenise and key every string alike (no word claimed twice)', r.returncode == 0, (r.stdout + r.stderr)[-600:])
done()
