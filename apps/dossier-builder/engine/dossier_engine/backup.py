"""Backups of the company's workspace and their restore drill (updates list, item 28).

A backup is one ZIP: the database copied with SQLite's own online backup (consistent while the program runs), every stored file
(blobs/, content-addressed), the lifecycle folders of the submitted sequences and the suite's files. Secrets are not in it (the Drive
key or service account, the users' passwords): they are set again after a restore. The program makes one by itself when the newest is
more than a day old and keeps the last seven. The restore drill opens a backup in a fresh folder exactly as a restore would and checks
it: the database is sound (integrity check), every document's file is there with the SHA-256 it was stored under, and the activity log's
chain is unbroken — a backup is only called good after that."""
import hashlib, json, os, shutil, sqlite3, tempfile, time, zipfile
from pathlib import Path

KEEP = 7
EVERY = 24 * 3600
SECRET = {'drive.json', 'users.json', 'secret.key', 'session.key'}
FOLDERS = ('blobs', 'lifecycle', 'suite')


def folder(root):
    return Path(root) / 'backups'


def make(root, dest=None):
    """A backup ZIP of the workspace at `root` → its path."""
    root = Path(root)
    dest = Path(dest or folder(root))
    dest.mkdir(parents=True, exist_ok=True)
    name = time.strftime('backup-%Y%m%d-%H%M%S') + '.zip'
    n = 2
    while (dest / name).exists():                         # two in the same second: the second one gets its own name
        name = time.strftime('backup-%Y%m%d-%H%M%S') + f'-{n}.zip'
        n += 1
    tmp = Path(tempfile.mkdtemp())
    try:
        db = tmp / 'workspace.sqlite'
        src = sqlite3.connect(str(root / 'workspace.sqlite'))
        out = sqlite3.connect(str(db))
        with out:
            src.backup(out)                              # SQLite's online backup: a consistent copy while the program writes
        src.close()
        out.close()
        manifest = {'made': time.strftime('%Y-%m-%dT%H:%M:%S'), 'program': 'dossier-builder', 'files': 0,
                    'left_out': sorted(n for n in SECRET if (root / n).exists())}
        path = dest / name
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as z:
            z.write(db, 'workspace.sqlite')
            for sub in FOLDERS:
                base = root / sub
                if not base.exists():
                    continue
                for p in sorted(base.rglob('*')):
                    if p.is_file():
                        z.write(p, p.relative_to(root).as_posix())
                        manifest['files'] += 1
            z.writestr('MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=1))
        return path
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


NAME = __import__('re').compile(r'^backup-\d{8}-\d{6}(-\d+)?\.zip$')


def path_of(root, name):
    """The backup called `name` in this workspace's backups folder, or None (no other path is ever opened)."""
    p = folder(root) / name
    return p if NAME.match(name or '') and p.is_file() else None


def start_auto(root, ready, every=3600, delay=120):
    """The automatic backup on a background thread: a first look after `delay` seconds, then every `every`; a backup is made when the
    newest is a day old and `ready()` says the workspace has work in it."""
    import threading

    def run():
        time.sleep(delay)
        while True:
            try:
                if ready():
                    auto(root)
            except Exception:                            # a failed attempt is tried again at the next look; the program goes on
                pass
            time.sleep(every)
    th = threading.Thread(target=run, name='auto-backup', daemon=True)
    th.start()
    return th


def listing(root):
    out = []
    for p in sorted(folder(root).glob('backup-*.zip'), reverse=True):
        out.append({'name': p.name, 'size': p.stat().st_size, 'made': p.stat().st_mtime})
    return out


def prune(root, keep=KEEP):
    for p in sorted(folder(root).glob('backup-*.zip'), reverse=True)[keep:]:
        p.unlink(missing_ok=True)


def auto(root, every=EVERY, keep=KEEP):
    """One backup when the newest is older than `every` seconds (or there is none); the last `keep` kept. → the new path or None."""
    have = sorted(folder(root).glob('backup-*.zip'))
    if have and time.time() - have[-1].stat().st_mtime < every:
        return None
    if not (Path(root) / 'workspace.sqlite').exists():
        return None
    p = make(root)
    prune(root, keep)
    return p


def drill(zip_path):
    """Restore the backup into a fresh folder and check it: {'ok', 'documents', 'missing', 'altered', 'integrity', 'audit_ok'}."""
    tmp = Path(tempfile.mkdtemp())
    try:
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                name = info.filename
                if name.startswith('/') or '..' in Path(name).parts:
                    continue                             # never written outside the drill's folder
                z.extract(info, tmp)
        con = sqlite3.connect(str(tmp / 'workspace.sqlite'))
        integrity = con.execute('pragma integrity_check').fetchone()[0]
        rows = con.execute('select id, sha256 from document').fetchall()
        missing, altered = [], []
        for doc_id, sha in rows:
            f = tmp / 'blobs' / sha
            if not f.is_file():
                missing.append(doc_id)
            elif hashlib.sha256(f.read_bytes()).hexdigest() != sha:
                altered.append(doc_id)
        con.close()
        from .app.store import Store
        ok_audit, bad = Store(tmp).verify_audit()        # the same check the program makes on its own log
        ok = integrity == 'ok' and not missing and not altered and ok_audit
        return {'ok': ok, 'documents': len(rows), 'missing': missing[:20], 'altered': altered[:20], 'integrity': integrity,
                'audit_ok': ok_audit, 'audit_first_bad': bad}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
