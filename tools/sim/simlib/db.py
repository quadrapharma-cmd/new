"""The database the simulator checks results in (as the owner — read checks, set-up of the sim admin, clean-up).
Local: DB_NAME / PGHOST / PGPORT / PGUSER (the tests' defaults). Staging: STAGING_DB_URL.
psycopg2 (pip install psycopg2-binary) keeps a pool of connections; without it every query runs through psql (slower)."""
import os, json, subprocess, threading, time

try:
    import psycopg2, psycopg2.pool, psycopg2.extras
except ImportError:  # pragma: no cover
    psycopg2 = None


def dsn_from_env(kind='local'):
    if kind == 'staging': return os.environ.get('STAGING_DB_URL', '')
    host = os.environ.get('PGHOST', '/tmp'); port = os.environ.get('PGPORT', '5433')
    user = os.environ.get('PGUSER', 'postgres'); db = os.environ.get('DB_NAME', 'drugbox_live')
    return 'host=%s port=%s user=%s dbname=%s' % (host, port, user, db)


class DB:
    def __init__(self, dsn, size=8):
        self.dsn = dsn; self.lock = threading.Lock(); self.slow = []
        self.pool = psycopg2.pool.ThreadedConnectionPool(1, size, dsn) if psycopg2 else None
        if self.pool is None: self._psql = self._psql_args(dsn)

    def _psql_args(self, dsn):
        if dsn.startswith('postgres'): return ['psql', dsn, '-tA', '-v', 'ON_ERROR_STOP=1']
        kv = dict(p.split('=', 1) for p in dsn.split())
        return ['psql', '-h', kv['host'], '-p', kv['port'], '-U', kv['user'], '-d', kv['dbname'], '-tA', '-v', 'ON_ERROR_STOP=1']

    def q(self, sql, args=None):
        """Rows as tuples (autocommit)."""
        t0 = time.time()
        if self.pool is None:
            if args: sql = _inline(sql, args)
            r = subprocess.run(self._psql + ['-F', '\x1f', '-c', sql], capture_output=True, text=True)
            if r.returncode: raise RuntimeError(r.stderr.strip()[:400])
            return [tuple(l.split('\x1f')) for l in r.stdout.splitlines() if l]
        c = self.pool.getconn()
        try:
            c.autocommit = True
            with c.cursor() as cur:
                cur.execute(sql, args)
                rows = cur.fetchall() if cur.description else []
            return rows
        finally:
            self.pool.putconn(c)
            dt = time.time() - t0
            if dt > 0.5:
                with self.lock: self.slow.append((round(dt, 3), sql[:160]))

    def one(self, sql, args=None):
        r = self.q(sql, args); return r[0] if r else None

    def val(self, sql, args=None):
        r = self.one(sql, args); return r[0] if r else None

    def close(self):
        if self.pool: self.pool.closeall()


def _inline(sql, args):  # psql fallback only: simple literal substitution
    def lit(v):
        if v is None: return 'null'
        if isinstance(v, bool): return 'true' if v else 'false'
        if isinstance(v, (int, float)): return str(v)
        if isinstance(v, (list, dict)): v = json.dumps(v)
        return "'" + str(v).replace("'", "''") + "'"
    return sql % tuple(lit(a) for a in args)
