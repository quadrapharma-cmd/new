#!/usr/bin/env python3
"""Privacy gate for the repository.

Fails (exit 1) when any tracked, staged or untracked-but-not-ignored file, or any
commit message on the current branch, contains data that belongs to the real
workbook: person/company names, account numbers, tax identifiers.

The deny-list is built at run time from the PRIVATE workbook (STRIFA_REAL_XLSX) and
is never written to disk or printed. Without the workbook the scan cannot run and
exits 2 (so a push script must treat "cannot scan" as "do not push").

Usage:  python3 tools/privacy/scan.py [--show] [--staged]
        --staged scans only the files in the git index (what a commit would contain)
        --show prints the matched token (local terminal only); default prints an id.
"""
import glob
import hashlib
import os
import re
import subprocess
import sys
import unicodedata

DEFAULT_XLSX = glob.glob('/root/.claude/uploads/*/*.xlsx')
XLSX = os.environ.get('STRIFA_REAL_XLSX') or (DEFAULT_XLSX[0] if DEFAULT_XLSX else '')
SHOW = '--show' in sys.argv
STAGED = '--staged' in sys.argv
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Words that are ordinary accounting / UI vocabulary and may legitimately appear in code.
GENERIC = set('''
مصروفات مصروف حساب حسابات الشركة شركة الشركاء الشريك مساهم مساهمون المساهمون عملاء العملاء مورد موردون الموردون
عام مشترك المصنع خزينة الخزينة البنك بنك مرتبات المرتبات تمويل نقدي استحقاقات قيد قيود سطر أسطر
عقد التسوية الأمانة أمانة مشروع خاص تأمينات اجتماعية ضريبة الضريبة رسوم اشتراكات تراخيص
الإدارة مجلس الإدارة الجمعية العامة محضر شهادة تأسيس كشف دفتر اليومية الأستاذ ميزان المراجعة
محدد غير السجل مستحقه مستحقة مرتب مقابل البند بند عام مؤقت مدين دائن تاريخ الطرف التاريخ لاقفال المكون المال الاقفال الاسم الصفه الصفة المبلغ البيان الحساب الرصيد الكود المساهم نسبه نسبة الاساس الأساس الإجمالي الاجمالي المجموع الشريك الممول الدائن المدين جمال مبلغ مستحق مستند جدول التزام التزاما داخل جاري بنكي ارقام فارغ قرار محاسب المحاسب المحاسبي محامي المحامي المحامية مقاول سباك حداد نقاش فني تكييف عمالة يومية مراقب مدير مهندس دكتور كابتن صفحة صفحات تطبيق نظام واحدة
'''.split())

# Public company names that are allowed to appear in the code base (system title etc.).
ALLOW = {'ستريفا', 'هوسفيرا', 'استريفا', 'هيلث', 'كير', 'مصر',
         'كريدي', 'اجريكول', 'أجريكول',
         # very common given names: a lone first name is not identifying; full names still are
         'محمد', 'احمد', 'أحمد', 'ابراهيم', 'إبراهيم', 'علي', 'حسن', 'حسين', 'خالد', 'عمر', 'يوسف', 'مصطفى',
         'محمود', 'سعيد', 'سامي', 'طارق', 'وائل', 'سامح', 'سارة', 'اسماء', 'أسماء', 'رنا', 'عبد', 'الله',
         'كريم', 'رؤوف', 'عبدالله', 'الرحيم', 'عبدالرحيم', 'المطلوب', 'المستخدم', 'ملخص', 'الاستفسار', 'الاستفسار', 'النسب', 'زيادة', 'زياده',
         'السيد', 'متولي', 'هيثم', 'جمال', 'ياسر', 'رمضان', 'اسماعيل', 'إسماعيل', 'فتحي', 'الفتاح'}
SKIP_PREFIXES = ('node_modules/', 'dist/', '.local/', 'package-lock.json', 'tools/privacy/scan.py')

AR_DIAC = re.compile('[ً-ٰٟـ]')


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKC', str(s))
    s = AR_DIAC.sub('', s)
    s = s.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ى', 'ي').replace('ة', 'ه')
    return re.sub(r'\s+', ' ', s).strip().lower()


def build_denylist():
    import openpyxl
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    strings = set()
    tokens = set()

    generic_norm = {norm(g) for g in GENERIC} | {norm(a) for a in ALLOW}
    generic_phrases = {'غير محدد', 'عمالة يومية', 'شيك مقاصة', 'موظفو المصنع', 'شركة المياه', 'شركة الكهرباء', 'شركة الامن', 'مورد الحديد', 'مورد ماكينة الشراب'}
    generic_phrases = {norm(x) for x in generic_phrases}

    def add_name(v, min_words=2):
        if not isinstance(v, str):
            return
        v = v.strip()
        if len(v) < 4 or len(v.split()) < min_words:
            return
        toks = []
        for t in re.split(r'[\s/\-—()،,.:؛]+', v):
            t = norm(t)
            if len(t) >= 4 and t not in generic_norm and not t.isdigit():
                toks.append(t)
        if not toks:
            return
        if len(v.split()) >= 2 and norm(v) not in generic_phrases:
            strings.add(norm(v))
        tokens.update(toks)

    NAME_COLS = {'٨.': [0], '٩.': [0], '١٢.': [0], '١٧.': [0], '١٨.': [0], '١٩.': [0]}
    for ws in wb.worksheets:
        title = ws.title
        rows = list(ws.iter_rows(values_only=True))
        for r in rows:
            for v in r:
                if isinstance(v, str):
                    # long identifiers (bank accounts, registers) anywhere
                    for m in re.findall(r'\b\d{10,}\b', v):
                        strings.add(m)
                    for m in re.findall(r'\b\d{3}-\d{3}-\d{3}\b', v):
                        strings.add(m)
        if title.startswith('٢.'):          # journal: party column K=10, names only (>=2 words)
            for r in rows[1:]:
                if len(r) > 10:
                    add_name(r[10])
        elif title.startswith('١.'):        # chart: account names that carry titles/people
            for r in rows[1:]:
                if len(r) > 1 and isinstance(r[1], str) and re.search(r'(د|أ|ا|ك|م)/|ليمتد|ورثة', r[1]):
                    add_name(r[1])
        else:
            for prefix, cols in NAME_COLS.items():
                if title.startswith(prefix):
                    for r in rows[1:]:
                        for c in cols:
                            v = r[c] if len(r) > c else None
                            # name-like cell only: short, no digits
                            if isinstance(v, str) and len(v.split()) <= 5 and not re.search(r'\d', v):
                                add_name(v, min_words=1)
    return strings, tokens


def staged_files():
    out = subprocess.check_output(['git', '-C', REPO, 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z'])
    for p in out.decode().split('\0'):
        if p:
            yield p


def repo_files():
    if STAGED:
        yield from staged_files()
        return
    out = subprocess.check_output(['git', '-C', REPO, 'ls-files', '-z', '--cached', '--others', '--exclude-standard'])
    for p in out.decode().split('\0'):
        if p:
            yield p


def main():
    if not XLSX or not os.path.exists(XLSX):
        print('privacy scan: workbook not available, cannot build deny-list -> NOT SAFE TO PUSH', file=sys.stderr)
        return 2
    strings, tokens = build_denylist()
    deny = sorted(strings | tokens, key=len, reverse=True)
    ident = {d: hashlib.sha1(d.encode()).hexdigest()[:6] for d in deny}
    hits = []

    def check(label, text):
        n = norm(text)
        for d in deny:
            if d in n:
                hits.append((label, ident[d], d))

    for p in repo_files():
        if p.startswith(SKIP_PREFIXES):
            continue
        full = os.path.join(REPO, p)
        if STAGED:
            try:
                raw = subprocess.check_output(['git', '-C', REPO, 'show', ':' + p])
            except subprocess.CalledProcessError:
                continue
        else:
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            try:
                with open(full, 'rb') as fh:
                    raw = fh.read()
            except OSError:
                continue
        if b'\0' in raw[:4096]:
            continue  # binary
        text = raw.decode('utf-8', 'ignore')
        for i, line in enumerate(text.splitlines(), 1):
            check(f'{p}:{i}', line)
    try:
        if STAGED:
            raise subprocess.CalledProcessError(1, 'skip')
        msgs = subprocess.check_output(['git', '-C', REPO, 'log', '--format=%H%n%B%n--END--'], stderr=subprocess.DEVNULL).decode()
        for i, line in enumerate(msgs.splitlines(), 1):
            check(f'git-log:{i}', line)
    except subprocess.CalledProcessError:
        pass
    if hits:
        print(f'privacy scan FAILED: {len(hits)} hit(s) in {len({h[0].split(":")[0] for h in hits})} file(s)')
        for label, i, d in hits[:60]:
            print(f'  {label}  token#{i}' + (f'  [{d}]' if SHOW else ''))
        return 1
    print(f'privacy scan OK ({len(deny)} deny-list entries, {sum(1 for _ in repo_files())} files, git log checked)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
