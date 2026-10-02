// Local stand-in for Supabase (tests only): Auth endpoints used by supabase-js + a /rest/v1 proxy to PostgREST + the built app at /.
// Passwords: bcrypt via pgcrypto. Tokens: HS256 JWT with the same secret PostgREST verifies, so RLS applies exactly as on Supabase.
import http from 'node:http'; import crypto from 'node:crypto'; import fs from 'node:fs'; import pg from 'pg';
const PORT = +process.env.PORT || 54321, REST = process.env.REST_URL || 'http://127.0.0.1:3001';
const SECRET = process.env.JWT_SECRET, APP_DIR = process.env.APP_DIR, STORE = process.env.STORE_DIR || '/tmp/drugbox-storage';
const require_dirname = (p) => p.slice(0, p.lastIndexOf('/'));
if (!SECRET || SECRET.length < 32) throw new Error('JWT_SECRET (32+ chars) required');
const db = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: 5 });
const b64u = b => Buffer.from(b).toString('base64url');
function sign(payload) { const h = b64u(JSON.stringify({ alg: 'HS256', typ: 'JWT' })), p = b64u(JSON.stringify(payload)); return `${h}.${p}.${crypto.createHmac('sha256', SECRET).update(`${h}.${p}`).digest('base64url')}`; }
function verify(t) { const [h, p, s] = String(t || '').split('.'); if (!s) return null; const ok = crypto.createHmac('sha256', SECRET).update(`${h}.${p}`).digest('base64url'); if (!crypto.timingSafeEqual(Buffer.from(ok), Buffer.from(s.padEnd(ok.length).slice(0, ok.length)))) return null; const c = JSON.parse(Buffer.from(p, 'base64url')); return c.exp * 1000 > Date.now() ? c : null; }
const refresh = new Map();                                      // refresh_token → user id (memory; tests only)
function session(u) { const now = Math.floor(Date.now() / 1000), rt = crypto.randomBytes(24).toString('hex'); refresh.set(rt, u.id);
  const user = { id: u.id, aud: 'authenticated', role: 'authenticated', email: u.email, user_metadata: u.raw_user_meta_data || {}, app_metadata: { provider: 'email' }, created_at: u.created_at };
  return { access_token: sign({ sub: u.id, role: 'authenticated', aud: 'authenticated', email: u.email, iat: now, exp: now + 3600 }), token_type: 'bearer', expires_in: 3600, expires_at: now + 3600, refresh_token: rt, user }; }
const send = (res, code, body, extra = {}) => { res.writeHead(code, { 'content-type': 'application/json', ...cors, ...extra }); res.end(body === undefined ? '' : JSON.stringify(body)); };
const cors = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS', 'access-control-expose-headers': 'content-range,content-profile' };
const readBody = req => new Promise(r => { let d = ''; req.on('data', c => d += c); req.on('end', () => { try { r(d ? JSON.parse(d) : {}); } catch { r({}); } }); });
const authErr = (res, code, msg) => send(res, code, { error: 'invalid_grant', error_description: msg, msg, code });
http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://x');
    if (req.method === 'OPTIONS') return send(res, 204);
    if (url.pathname === '/' || url.pathname === '/index.html') { res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' }); return fs.createReadStream(APP_DIR + '/index.html').pipe(res); }
    if (/^\/js\/[\w.-]+\.js$/.test(url.pathname) && fs.existsSync(APP_DIR + url.pathname)) { res.writeHead(200, { 'content-type': 'text/javascript; charset=utf-8', 'cache-control': 'public, max-age=31536000, immutable' }); return fs.createReadStream(APP_DIR + url.pathname).pipe(res); }
    if (url.pathname === '/auth/v1/signup' && req.method === 'POST') {
      const b = await readBody(req); const email = String(b.email || '').trim().toLowerCase(), pw = String(b.password || '');
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return authErr(res, 400, 'Invalid email');
      if (pw.length < 8) return authErr(res, 422, 'Password should be at least 8 characters');
      const ex = await db.query('select 1 from auth.users where email=$1', [email]); if (ex.rowCount) return authErr(res, 422, 'User already registered');
      const r = await db.query("insert into auth.users (email, encrypted_password, raw_user_meta_data) values ($1, crypt($2, gen_salt('bf', 10)), $3) returning *", [email, pw, b.data || {}]);
      return send(res, 200, session(r.rows[0]));
    }
    if (url.pathname === '/auth/v1/token' && req.method === 'POST') {
      const b = await readBody(req), gt = url.searchParams.get('grant_type');
      if (gt === 'password') { const r = await db.query('select * from auth.users where email=$1 and encrypted_password = crypt($2, encrypted_password)', [String(b.email || '').trim().toLowerCase(), String(b.password || '')]);
        return r.rowCount ? send(res, 200, session(r.rows[0])) : authErr(res, 400, 'Invalid login credentials'); }
      if (gt === 'refresh_token') { const id = refresh.get(b.refresh_token); if (!id) return authErr(res, 400, 'Invalid Refresh Token'); refresh.delete(b.refresh_token);
        const r = await db.query('select * from auth.users where id=$1', [id]); return send(res, 200, session(r.rows[0])); }
      return authErr(res, 400, 'Unsupported grant type');
    }
    if (url.pathname === '/auth/v1/user') { const c = verify((req.headers.authorization || '').replace(/^Bearer /i, '')); if (!c) return authErr(res, 401, 'Invalid token');
      const r = await db.query('select * from auth.users where id=$1', [c.sub]); if (!r.rowCount) return authErr(res, 404, 'User not found'); return send(res, 200, session(r.rows[0]).user); }
    if (url.pathname === '/auth/v1/logout') return send(res, 204);

    /* ── Storage (tests only): the object row is inserted AS the user, so the bucket's row-level policies decide; then the file is written ── */

    /* Edge Functions (tests): forwarded to the local function server */
    if (url.pathname.startsWith('/functions/v1/')) {
      const target = 'http://127.0.0.1:' + (process.env.FN_PORT || 54400) + url.pathname.replace('/functions/v1', '') + url.search;
      const body = ['GET', 'HEAD'].includes(req.method) ? undefined : await new Promise(r => { const c = []; req.on('data', d => c.push(d)); req.on('end', () => r(Buffer.concat(c))); });
      try { const fr = await fetch(target, { method: req.method, headers: { 'content-type': req.headers['content-type'] || 'application/json', authorization: req.headers.authorization || '' }, body });
        const buf = Buffer.from(await fr.arrayBuffer()); res.writeHead(fr.status, { ...cors, 'content-type': fr.headers.get('content-type') || 'text/plain' }); return res.end(buf); }
      catch (e) { return send(res, 502, { error: 'functions not running' }); }
    }
    if (url.pathname.startsWith('/storage/v1/object/')) {
      const rest = decodeURIComponent(url.pathname.slice('/storage/v1/object/'.length));
      if (req.method === 'GET' && rest.startsWith('public/')) {
        const [bucket, ...pp] = rest.slice(7).split('/'), name = pp.join('/');
        const b = await db.query('select public from storage.buckets where id=$1', [bucket]); if (!b.rowCount || !b.rows[0].public) return send(res, 404, { error: 'not found' });
        const o = await db.query("select metadata from storage.objects where bucket_id=$1 and name=$2", [bucket, name]); const f = STORE + '/' + bucket + '/' + name;
        if (!o.rowCount || !fs.existsSync(f)) return send(res, 404, { error: 'not found' });
        const size = fs.statSync(f).size, type = (o.rows[0].metadata || {}).mimetype || 'application/octet-stream', range = /bytes=(\d*)-(\d*)/.exec(req.headers.range || '');
        if (range) { const start = range[1] ? +range[1] : 0, end = range[2] ? Math.min(+range[2], size - 1) : size - 1;
          res.writeHead(206, { ...cors, 'content-type': type, 'accept-ranges': 'bytes', 'content-range': `bytes ${start}-${end}/${size}`, 'content-length': end - start + 1 }); return fs.createReadStream(f, { start, end }).pipe(res); }
        res.writeHead(200, { ...cors, 'content-type': type, 'accept-ranges': 'bytes', 'content-length': size }); return fs.createReadStream(f).pipe(res);
      }

      /* signed links for private files: issued only if the user may read the object (policies decide), valid for expiresIn seconds */
      if (rest.startsWith('sign/')) {
        const tail = rest.slice(5), parts = tail.split('/'), bucket = parts[0], name = parts.slice(1).join('/');
        const mk = (n, exp) => { const payload = Buffer.from(JSON.stringify({ b: bucket, n, exp })).toString('base64url'); return payload + '.' + crypto.createHmac('sha256', SECRET).update(payload).digest('base64url'); };
        if (req.method === 'GET') {
          const tok = url.searchParams.get('token') || '', [pl, sg] = tok.split('.');
          if (!pl || !sg || crypto.createHmac('sha256', SECRET).update(pl).digest('base64url') !== sg) return send(res, 400, { error: 'Invalid signature' });
          const t = JSON.parse(Buffer.from(pl, 'base64url')); if (t.b !== bucket || t.n !== name || t.exp < Date.now() / 1000) return send(res, 400, { error: 'Link expired' });
          const o = await db.query('select metadata from storage.objects where bucket_id=$1 and name=$2', [bucket, name]); const f = STORE + '/' + bucket + '/' + name;
          if (!o.rowCount || !fs.existsSync(f)) return send(res, 404, { error: 'not found' });
          res.writeHead(200, { ...cors, 'content-type': (o.rows[0].metadata || {}).mimetype || 'application/octet-stream', 'content-length': fs.statSync(f).size }); return fs.createReadStream(f).pipe(res);
        }
        if (req.method === 'POST') {
          const cl = verify((req.headers.authorization || '').replace(/^Bearer /i, '')); if (!cl) return send(res, 401, { error: 'Sign in first', statusCode: '401' });
          const body = await readBody(req), exp = Math.floor(Date.now() / 1000) + Math.min(+body.expiresIn || 3600, 7 * 86400);
          const names = name ? [name] : (body.paths || []);
          const c = await db.connect(); let seen = [];
          try { await c.query('begin'); await c.query("select set_config('request.jwt.claim.sub',$1,true)", [cl.sub]); await c.query('set local role authenticated');
            seen = (await c.query('select name from storage.objects where bucket_id=$1 and name = any($2)', [bucket, names])).rows.map(r => r.name); await c.query('commit'); }
          catch (e) { await c.query('rollback').catch(() => {}); } finally { c.release(); }
          const out = names.map(n => seen.includes(n) ? { path: n, signedURL: `/object/sign/${bucket}/${n}?token=${mk(n, exp)}`, error: null } : { path: n, signedURL: null, error: 'Either the object does not exist or you do not have access to it' });
          if (name) return out[0].error ? send(res, 400, { error: out[0].error, statusCode: '400' }) : send(res, 200, { signedURL: out[0].signedURL });
          return send(res, 200, out);
        }
      }
      const claims = verify((req.headers.authorization || '').replace(/^Bearer /i, '')); if (!claims || claims.role !== 'authenticated') return send(res, 401, { error: 'Sign in first', statusCode: '401' });
      const asUser = async (fn) => { const c = await db.connect(); try { await c.query('begin'); await c.query("select set_config('request.jwt.claim.sub',$1,true)", [claims.sub]); await c.query('set local role authenticated'); const out = await fn(c); await c.query('commit'); return out; } catch (e) { await c.query('rollback').catch(() => {}); throw e; } finally { c.release(); } };
      if (req.method === 'DELETE') { const bucket = rest.split('/')[0], body = await readBody(req), names = body.prefixes || [];
        try { const gone = await asUser(c => c.query('delete from storage.objects where bucket_id=$1 and name = any($2) returning name', [bucket, names]));
          gone.rows.forEach(r => { try { fs.unlinkSync(STORE + '/' + bucket + '/' + r.name); } catch {} }); return send(res, 200, gone.rows.map(r => ({ name: r.name }))); }
        catch (e) { return send(res, 403, { error: e.message, statusCode: '403' }); } }
      if (req.method === 'POST' || req.method === 'PUT') {
        const [bucket, ...pp] = rest.split('/'), name = pp.join('/'), upsert = req.method === 'PUT' || /true/i.test(req.headers['x-upsert'] || '');
        const raw = await new Promise(r => { const c = []; req.on('data', d => c.push(d)); req.on('end', () => r(Buffer.concat(c))); });
        let data = raw, type = req.headers['content-type'] || 'application/octet-stream';
        const mb = /multipart\/form-data;\s*boundary=(.+)$/i.exec(type);
        if (mb) { const bnd = Buffer.from('--' + mb[1]); let i = raw.indexOf(bnd); while (i >= 0) { const j = raw.indexOf(bnd, i + bnd.length); if (j < 0) break;
            const part = raw.slice(i + bnd.length + 2, j - 2), h = part.indexOf('\r\n\r\n'), head = part.slice(0, h).toString();
            if (/filename=/i.test(head)) { data = part.slice(h + 4); type = (/content-type:\s*([^\r\n]+)/i.exec(head) || [])[1] || 'application/octet-stream'; break; } i = j; } }
        const b = await db.query('select file_size_limit, allowed_mime_types from storage.buckets where id=$1', [bucket]); if (!b.rowCount) return send(res, 404, { error: 'Bucket not found', statusCode: '404' });
        if (b.rows[0].file_size_limit && data.length > +b.rows[0].file_size_limit) return send(res, 413, { error: 'The object exceeded the maximum allowed size', statusCode: '413' });
        if (b.rows[0].allowed_mime_types && !b.rows[0].allowed_mime_types.includes(type)) return send(res, 415, { error: 'mime type ' + type + ' is not supported', statusCode: '415' });
        try { await asUser(async c => { if (upsert) await c.query('delete from storage.objects where bucket_id=$1 and name=$2', [bucket, name]);
            await c.query('insert into storage.objects (bucket_id, name, owner, metadata) values ($1,$2,$3,$4)', [bucket, name, claims.sub, { mimetype: type, size: data.length }]); }); }
        catch (e) { return send(res, /duplicate/.test(e.message) ? 409 : 403, { error: /row-level security/.test(e.message) ? 'new row violates row-level security policy' : e.message, statusCode: '403' }); }
        fs.mkdirSync(require_dirname(STORE + '/' + bucket + '/' + name), { recursive: true }); fs.writeFileSync(STORE + '/' + bucket + '/' + name, data);
        return send(res, 200, { Key: bucket + '/' + name });
      }
    }
    if (url.pathname.startsWith('/rest/v1/')) {                       // → PostgREST, same headers (apikey is ignored locally; the JWT decides the role)
      const target = REST + url.pathname.slice(8) + url.search, h = { ...req.headers }; delete h.host; delete h.apikey;
      if (!/^Bearer /i.test(h.authorization || '') || !verify(h.authorization.slice(7))) delete h.authorization;   // anon
      const body = ['GET', 'HEAD'].includes(req.method) ? undefined : await new Promise(r => { const c = []; req.on('data', d => c.push(d)); req.on('end', () => r(Buffer.concat(c))); });
      const up = await fetch(target, { method: req.method, headers: h, body }); const out = Buffer.from(await up.arrayBuffer());
      const hh = { ...cors }; up.headers.forEach((v, k) => { if (!['content-encoding', 'transfer-encoding', 'connection'].includes(k)) hh[k] = v; });
      res.writeHead(up.status, hh); return res.end(out);
    }
    send(res, 404, { error: 'not found' });
  } catch (e) { console.error(e); send(res, 500, { error: String(e.message || e) }); }
}).listen(PORT, () => console.log('local supabase on :' + PORT));
