# Rewording the interface's texts in bulk

The tools that put the whole interface into formal Arabic on 16/11/2026 (eBOX stage 1). Use them when many texts change at once;
a single text is edited by hand. `tests/test_formal_arabic.py` is what keeps the result (it fails on a colloquial word).

Never reworded: the words the program looks for inside the owner's documents (`extract.py`, `arabic.py`, `intake_eda.py`,
`classify.yaml`), the prompts to the model, the letters' fixed wording, and the owner's own words quoted in comments.

## The way

1. **List** every Arabic text with its exact place, then each different text once with a short id:
   - pages and scripts: `node extract.mjs units.json ui/index.html ui/assets/*.js web/boot.js …` (needs `npm i acorn` beside it),
     then `python3 listing.py units.json page` → `page.txt` (id, text) and `page.ids.json`;
   - Python, plain strings: `python3 extract_py.py units.json engine/dossier_engine`, then `listing.py`;
   - Python, f-strings: `python3 fstr.py list engine-f engine/dossier_engine` — **Python 3.12+ tokenizes f-strings apart from plain
     strings**, so the plain pass does not see them (126 messages were missed at first).
2. **Write the new texts** as lines `id ⇒ new text` (`id@@context ⇒ text` where one text has two meanings).
3. **Check the ends**: `python3 edges.py page.ids.json tm1.txt,tm2.txt …` — a text that is one piece of a sentence joined in code
   must keep the spaces at its ends (25 lost theirs at first; `joints.py` finds two adjacent Python pieces with no space between).
4. **Apply**: `node apply.mjs page.ids.json tm1.txt,tm2.txt <files>` · `python3 apply_py.py engine.ids.json tm.txt <dir>` ·
   `python3 fstr.py apply engine-f.ids.json tm.txt <dir>` (each has `--dry`). They refuse a text whose `{placeholders}`, `${…}`
   expressions, tags or quotes differ from the old one's, and a file that no longer parses.
5. **Look for what is left**: `python3 scan.py ui web/boot.js engine/dossier_engine rulepacks` (colloquial words and verb shapes;
   it over-reports — read the lines), then the tests' own wording (`grep` the old texts in `tests/`).

Rule packs are YAML: their few notes were replaced by exact text, and the file loaded before and after to see only `ar` leaves change.
