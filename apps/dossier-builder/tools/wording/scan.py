"""Find Egyptian colloquial wording left in the given files: prints file:line and the line (cut) for every Arabic line that holds a
marker word or a colloquial verb shape.   python3 scan.py [--max N] <file-or-dir>…"""
import pathlib, re, sys

args = sys.argv[1:]
width = 330
if args and args[0] == '--max':
    width = int(args[1]); args = args[2:]
AR = re.compile(r'[؀-ۿ]')
TASHKEEL = re.compile(r'[ً-ْٰـ]')
WORD = re.compile(r'[ء-ي]+')
MARK = set('''مش مفيش مافيش دي ده دا دول اللي بتاع بتاعة بتاعت بتاعته بتاعتها بتاعها بتوع بتاعه لسه عشان علشان كده كدا ليه ازاي إزاي فين
ايه إيه تاني تانية التاني التانية للتانية لتاني اكتر أكتر كتير شوية حاجة حاجات دلوقتي دلوقت بره جوه زي امشي قول قولنا خلي خلى شوف عايز عاوز عايزة
انهي أنهي مين برضه برضو كمان بس يعني اهو أهو احنا إحنا انت إنت لازم لو فيه مفهاش مالوش ملوش ملهاش مينفعش ماينفعش نفس هيبقى هتبقى يبقى تبقى
بقى بقت هنا? اوي أوي قوي خالص معلش طب طيب ماشي تمام اهي أهي دول ودول وده ودي وكمان ولسه ومش ولو فلو علي حط حطه حطها شيل شيله شغل شغله
اعمل اعمله اعملها اعملي يعمل بيعمل نعمل هات هاتها روح تعال جرب دوس اقفل افتحه خد خده ابعت ابعته بعتلك هبعت ناقصه'''.split())
MARK.discard('هنا?')
OK = set('''بيانات البيانات بيان البيان بين بينها بينهما بينه بنود البنود بند البند بنفس بنسخة بتاريخ بترتيب بنية البنية بيئة البيئة بيع بنك
هيئة الهيئة هيئات الهيئات هيكل الهيكل هيكلة هيكله هيكلها هنا هناك هندسة هندي اتفاق الاتفاق اتفاقية الاتفاقية اتجاه الاتجاه اتصال الاتصال اتحاد
الاتحاد اتباع اتخاذ اتساق الاتساق اتزان اتهام اتساع اتفاقيات اتجاهات اتصالات بيضاء بيولوجي بيولوجية بيطري بيطرية بنسبة بنوع بنص بنصه بنصها
بتوقيع بتحديد بتحديث بتعديل بتغيير بتسجيل بتقديم بتصدير بتجهيز بتوليد بتحويل بتنزيل بتقرير بتوثيق بتنسيق بتسمية بتصميم بتركيز بتشغيلة بتشغيل
بتصنيع بتعبئة بتخزين بتحليل بتقييم بتفويض بترخيص بتجديد بتسعير بتصريح بتعهد بتاريخه بتاريخها بتوريد بتسليم بتطبيق بتنفيذ بتصحيح بتكرار بتحميل
بتفاصيل بتفصيل بتلقائية بتقسيم بتجميع بتمييز بتأكيد بتأكيدك بتوزيع بتسلسل بتسلسله بتثبيت بتدقيق بتوضيح بتقارير بتواريخ بتوقيعه بتوقيعات بتعليمات
بيانه بيانها بياناته بياناتها بينما بيننا بتلك بتاتا بتة هيدروكلوريد هيدروكسيد هيدرات هيدروجين هيبارين هنغاريا هولندا بتصرف بتعاون بتكليف
بنظام بنمط بنهاية بنفسه بنفسها بنفسك بنجاح بنقل بنسخ بنسخته بنسختها بنودها بنوده بتقنية بتوصية بتوجيه بترجمة بترقيم بترميز بتسلسلات بتاريخي'''.split())
VERB = re.compile(r'^(?:و|ف)?(?:بي|بت|بن|هي|هت|هن)[ء-ي]{2,}$')
PASSIVE = re.compile(r'^(?:و|ف|ما)?(?:ات|يت|تت|بيت|بتت|هيت|هتت)[ء-ي]{3,}$')
NEG = re.compile(r'(?:ما\s*|م)[ء-ي]{2,}ش(?![ء-ي])')
hits = 0
for a in args:
    p = pathlib.Path(a)
    files = sorted(f for f in p.rglob('*') if f.is_file() and f.suffix in ('.py', '.js', '.mjs', '.html', '.yaml', '.yml', '.json', '.md', '.txt', '.css')) if p.is_dir() else [p]
    for f in files:
        if '/web/dist/' in str(f) or '/node_modules/' in str(f) or '__pycache__' in str(f) or '/vendor/' in str(f):
            continue
        try:
            text = f.read_text(encoding='utf-8')
        except Exception:
            continue
        for n, line in enumerate(text.split('\n'), 1):
            if not AR.search(line):
                continue
            plain = TASHKEEL.sub('', line)
            why = []
            for w in WORD.findall(plain):
                if w in OK:
                    continue
                if w in MARK:
                    why.append(w)
                elif VERB.match(w) and w not in OK and not w.startswith(('بتا', 'بين', 'بنو', 'هيئ', 'هيك')):
                    why.append(w + '?')
                elif PASSIVE.match(w) and not w.startswith(('اتف', 'اتج', 'اتص', 'اتح', 'اتب', 'اتخ', 'اتس', 'اتز', 'اته', 'يتم', 'تتم', 'يتض', 'تتض', 'يتع', 'تتع', 'يتو', 'تتو', 'يتط', 'تتط', 'يتك', 'تتك', 'يتب', 'تتب', 'يتح', 'تتح', 'يتغ', 'تتغ', 'يتأ', 'تتأ', 'يتج', 'تتج', 'يتر', 'تتر', 'يتس', 'تتس', 'يتق', 'تتق', 'يتف', 'تتف', 'يتن', 'تتن', 'يتل', 'تتل', 'يتم', 'يتد', 'تتد', 'يتخ', 'تتخ', 'يتص', 'تتص', 'يتش', 'تتش', 'يتز', 'يتي', 'تتي', 'يتث', 'تتث', 'يته', 'يتذ')):
                    why.append(w + '?')
            if NEG.search(plain):
                m = NEG.search(plain).group(0)
                if m not in ('مش',) and not m.endswith(('نقاش', 'هامش', 'مناقش')):
                    why.append('NEG:' + m)
            if why:
                hits += 1
                s = line.strip()
                i = min((plain.find(w.rstrip('?').split(':')[-1]) for w in why if plain.find(w.rstrip('?').split(':')[-1]) >= 0), default=0)
                start = max(0, i - 120)
                print(f'{f}:{n} [{" ".join(dict.fromkeys(why))}] ' + line[start:start + width].strip())
print(hits, 'line(s)')
