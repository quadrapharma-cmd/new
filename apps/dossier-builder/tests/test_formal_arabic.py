"""The interface speaks formal Arabic (فصحى), never Egyptian colloquial (the owner, 16/11/2026: «اللغة هتبقي عربيه فصحي مش لهجة عاميه»).
Every text a person reads — the pages, the engine's messages, the rule packs' notes and titles — is searched for the colloquial
words that had been there. Not searched: comments (they quote the owner as he wrote), the words the program looks for inside his
documents (the reading rules: those are his documents' own words), the prompts to the model, and the desktop edition's read-me."""
import io, pathlib, re, tokenize
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
TASHKEEL = re.compile(r'[ً-ْٰـ]')
WORD = re.compile(r'[ء-ي]+')
COLLOQUIAL = set('''مش ومش مفيش مافيش اللي بتاع بتاعة بتاعت بتوع بتاعه بتاعها بتاعته بتاعتها لسه ولسه عشان علشان كده كدا ليه ازاي إزاي فين دلوقتي دلوقت
تاني تانية التاني التانية للتانية برضه برضو كمان وكمان عايز عاوز عايزة ايه إيه شوية اكتر أكتر كتير زي بس ده دي دا اوي أوي خالص معلش ماشي امشي
شوف خلي هات جوه بره برا ليها ليهم بتوعهم مينفعش ماينفعش مالوش ملوش ملهاش مفهاش هنعمل هيبقى هتبقى'''.split())
# «ما …ش» and the colloquial verb shapes that carried most of the old texts
SHAPES = [re.compile(r'(?<![\u0621-\u064A])ما\s*[\u0621-\u064A]{2,}ش(?![\u0621-\u064A])'),
          re.compile(r'(?<![\u0621-\u064A])بي(?:قر|كتب|عمل|تحط|تعمل|تكتب|تقر|تفك|تنسخ|ترفع|تنزل|تحفظ|تغير|تعدل|فضل|اخد|دي|لاقي|سمي|حذر|حصل|قول|غير|شيل|حفظ|فتح|ذكر|نزل|رفع)[\u0621-\u064A]*'),
          re.compile(r'(?<![\u0621-\u064A])بت(?:تحدد|تملا|تغير|تعدل|تحط|تكتب|تعمل|تفك|ختلف|طلبها|حددها|قول|اخد|فضل)[\u0621-\u064A]*'),
          re.compile(r'(?<![\u0621-\u064A])(?:هي|هت)(?:نتهي|ستلم|بقى|ظهر|فتح|عمل|كون|حصل|رجع|لاقي|صدر|تحط|تعمل)[\u0621-\u064A]*'),
          re.compile(r'(?<![\u0621-\u064A])ات(?:قر[ىيت]|كتب|عمل|حط|شال|قفل|نزل|رفع|حفظ|غير|ملا|ملت|بدل|ضاف|رفض|وقف|حدثت|سمح|راجع)[\u0621-\u064A]*')]
READING = {'arabic.py', 'intake_eda.py', 'extract.py', 'absorb.py', 'vocab.py', 'paddle_rec.py', 'msdoc.py', 'officefiles.py', 'imagefiles.py', 'textlayer.py',
           'search.py', 'suite_m2.py', 'letters.py', 'm3tables.py', 'ai.py', 'runner.py', 'tools.py'}      # his documents' words, the letters' fixed wording, the prompts


def colloquial(text):
    plain = TASHKEEL.sub('', text)
    hit = [w for w in WORD.findall(plain) if w in COLLOQUIAL]
    for rx in SHAPES:
        hit += [m.group(0) for m in rx.finditer(plain)]
    return hit


def page_texts(path):
    """A page's or script's text without its comments (a «//» inside a string only cuts that line short)."""
    s = path.read_text(encoding='utf-8')
    s = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), s, flags=re.S)
    s = re.sub(r'<!--.*?-->', lambda m: '\n' * m.group(0).count('\n'), s, flags=re.S)
    for n, line in enumerate(s.split('\n'), 1):
        yield n, re.sub(r'(^|[\s;{}(),])//(?!/).*$', r'\1', line)


def python_texts(path):
    src = path.read_text(encoding='utf-8')
    for t in tokenize.generate_tokens(io.StringIO(src).readline):
        if t.type in (tokenize.STRING, tokenize.FSTRING_MIDDLE) and not (t.type == tokenize.STRING and t.string.lstrip('rRbBuUfF').startswith(('"""', "'''")) and t.start[1] <= 8):
            yield t.start[0], t.string                                      # (a docstring is a comment)


def pack_texts(path):
    def walk(node, key=None):
        if isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, k)
        elif isinstance(node, list):
            for v in node:
                yield from walk(v, key)
        elif isinstance(node, str) and key == 'ar':
            yield node
    for text in walk(yaml.safe_load(path.read_text(encoding='utf-8'))):
        yield 0, text


def test_no_colloquial_wording_in_what_a_person_reads():
    found = []
    pages = [ROOT / 'ui' / 'index.html', ROOT / 'ui' / 'login.html', ROOT / 'ui' / 'suite' / 'index.html', ROOT / 'web' / 'boot.js', ROOT / 'web' / 'engine.worker.js',
             ROOT / 'web' / 'build.py', ROOT / 'desktop' / 'launcher.py'] + sorted((ROOT / 'ui' / 'assets').glob('*.js'))
    for path in pages:
        for n, text in (python_texts(path) if path.suffix == '.py' else page_texts(path)):
            for w in colloquial(text):
                found.append(f'{path.relative_to(ROOT)}:{n} «{w}»')
    for path in sorted((ROOT / 'engine' / 'dossier_engine').rglob('*.py')) + [ROOT / 'web' / 'pybridge.py']:
        if path.name in READING:
            continue
        for n, text in python_texts(path):
            for w in colloquial(text):
                found.append(f'{path.relative_to(ROOT)}:{n} «{w}»')
    for path in sorted((ROOT / 'rulepacks').rglob('*.yaml')):
        if path.name == 'classify.yaml':                                    # the words looked for in his documents
            continue
        for _, text in pack_texts(path):
            for w in colloquial(text):
                found.append(f'{path.relative_to(ROOT)} «{w}» in: {text[:80]}')
    assert not found, '\n'.join(found[:60]) + (f'\n… {len(found)} in all' if len(found) > 60 else '')


def test_one_name_for_a_module():
    """A CTD module is «Module N» in Arabic text, everywhere (not «موديول», not «الوحدة N»)."""
    found = []
    for path in [ROOT / 'ui' / 'index.html', ROOT / 'ui' / 'suite' / 'index.html'] + sorted((ROOT / 'rulepacks').rglob('*.yaml')) + sorted((ROOT / 'engine' / 'dossier_engine').rglob('*.py')):
        if path.name in READING or path.name == 'classify.yaml':
            continue
        text = path.read_text(encoding='utf-8')
        for m in re.finditer(r'موديول|الموديولات|الوحدة [1-5١-٥](?![0-9])', text):
            found.append(f'{path.relative_to(ROOT)}: {text[max(0, m.start() - 30):m.end() + 20]!r}')
    assert not found, '\n'.join(found[:30])
