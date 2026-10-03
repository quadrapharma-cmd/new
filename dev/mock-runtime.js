// In-memory implementation of the claude.use('db' | 'user' | 'downloads' | 'assets') contracts
// (see artifact-capabilities db.d.ts, user.d.ts, downloads.d.ts, assets.d.ts).
// Works in the browser (via dev/mock-install.js) and in Node tests. Faithful where it matters to this app:
//  - db: paths/grammar, set (replace) / update (merge objects, REPLACE arrays, requires existence) / delete,
//    acquire leases (holder-based), where/orderBy/limit queries, onSnapshot with docChanges, frozen shared data,
//    256 KiB / 32 levels per doc, 5,000 docs per artifact, 64 live subscriptions, last-writer-wins, no transactions.
//  - user: id/me/canEdit/isOwner/can/profiles; read-only through flags.readOnly (live window var __STRIFA_MOCK__).
//  - downloads: extension allowlist, records every call; assets: writer-only, type/size rules, in memory.

const DOC_BYTES = 256 * 1024;
const MAX_DEPTH = 32;
const MAX_DOCS = 5000;
const MAX_SUBS = 64;
const SEG_RE = /^[A-Za-z0-9_\-.~:@+]+$/;
const enc = typeof TextEncoder !== 'undefined' ? new TextEncoder() : null;
const bytesOf = (s) => (enc ? enc.encode(s).length : s.length * 2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const err = (code, message) => Object.assign(new Error(message || code), { code, message: message || code });

function checkPath(path, wantDocument) {
  if (typeof path !== 'string' || !path) throw new TypeError('path must be a non-empty string');
  const segs = path.split('/');
  if (segs.length > 16) throw new TypeError('path has more than 16 segments');
  if (bytesOf(path) > 1000) throw new TypeError('path longer than 1000 bytes');
  for (const s of segs) {
    if (!s || s === '.' || s === '..' || !SEG_RE.test(s) || bytesOf(s) > 200) throw new TypeError(`bad path segment "${s}"`);
  }
  const even = segs.length % 2 === 0;
  if (wantDocument && !even) throw new TypeError(`document path needs an even number of segments (got ${segs.length}): ${path}`);
  if (!wantDocument && even) throw new TypeError(`collection path needs an odd number of segments (got ${segs.length}): ${path}`);
  return segs;
}

function depthOf(v, d = 1) {
  if (v === null || typeof v !== 'object') return d;
  let m = d;
  for (const k of Object.keys(v)) m = Math.max(m, depthOf(v[k], d + 1));
  return m;
}
function checkJson(v, path = '') {
  if (typeof v === 'number' && !Number.isFinite(v)) throw err('invalid_argument', `non-finite number at ${path}`);
  if (v === undefined || typeof v === 'function' || typeof v === 'symbol' || typeof v === 'bigint') throw err('invalid_argument', `non-JSON value at ${path}`);
  if (v && typeof v === 'object') for (const k of Object.keys(v)) checkJson(v[k], `${path}/${k}`);
}
function deepFreeze(o) {
  if (o && typeof o === 'object' && !Object.isFrozen(o)) {
    Object.freeze(o);
    for (const k of Object.keys(o)) deepFreeze(o[k]);
  }
  return o;
}
const clone = (o) => JSON.parse(JSON.stringify(o));
function mergeInto(target, patch) {
  const out = { ...target };
  for (const k of Object.keys(patch)) {
    const pv = patch[k];
    const tv = out[k];
    if (pv && typeof pv === 'object' && !Array.isArray(pv) && tv && typeof tv === 'object' && !Array.isArray(tv)) out[k] = mergeInto(tv, pv);
    else out[k] = pv;
  }
  return out;
}
function prepareBody(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw err('invalid_argument', 'document body must be a plain object');
  checkJson(data);
  const copy = clone(data);
  if (depthOf(copy) > MAX_DEPTH) throw err('invalid_argument', 'document deeper than 32 levels');
  return copy;
}
function checkSize(body) {
  if (bytesOf(JSON.stringify(body)) > DOC_BYTES) throw err('invalid_argument', 'document larger than 256 KiB');
}

function cmp(a, b) {
  if (a === b) return 0;
  if (typeof a === 'string' && typeof b === 'string') return a < b ? -1 : 1;
  if (typeof a === 'number' && typeof b === 'number') return a < b ? -1 : 1;
  if (typeof a === 'boolean' && typeof b === 'boolean') return a === b ? 0 : a ? 1 : -1;
  const ra = rank(a);
  const rb = rank(b);
  return ra === rb ? 0 : ra < rb ? -1 : 1;
}
const rank = (v) => (v === null ? 0 : typeof v === 'boolean' ? 1 : typeof v === 'number' ? 2 : typeof v === 'string' ? 3 : 4);
const OPS = new Set(['==', '!=', '<', '<=', '>', '>=', 'in', 'not-in', 'array-contains']);
function matches(doc, f) {
  const v = doc[f.field];
  switch (f.op) {
    case '==': return v !== undefined && cmp(v, f.value) === 0;
    case '!=': return v !== undefined && cmp(v, f.value) !== 0;
    case '<': return v != null && rank(v) === rank(f.value) && cmp(v, f.value) < 0;
    case '<=': return v != null && rank(v) === rank(f.value) && cmp(v, f.value) <= 0;
    case '>': return v != null && rank(v) === rank(f.value) && cmp(v, f.value) > 0;
    case '>=': return v != null && rank(v) === rank(f.value) && cmp(v, f.value) >= 0;
    case 'in': return v !== undefined && f.value.some((x) => cmp(v, x) === 0);
    case 'not-in': return v !== undefined && !f.value.some((x) => cmp(v, x) === 0);
    case 'array-contains': return Array.isArray(v) && v.some((x) => cmp(x, f.value) === 0);
    default: return false;
  }
}

export function createMockRuntime(options = {}) {
  const flags = options.flags || globalThis.__STRIFA_MOCK__ || {};
  if (globalThis && !globalThis.__STRIFA_MOCK__ && !options.flags) globalThis.__STRIFA_MOCK__ = flags;
  const cfg = {
    latencyMs: 0,
    acquireCreatesDoc: false,
    userId: 'u_mock_owner',
    userName: 'مستخدم تجريبي',
    ...options,
  };
  const live = () => ({ ...cfg, ...flags });

  const docs = new Map(); // path -> { data (frozen), version, snap (cached DocumentSnapshot) }
  const leases = new Map();
  const subs = new Set();
  const injected = [];
  const calls = { downloads: [], uploads: [], writes: [] };
  let notifyQueued = false;
  let ready = Promise.resolve();

  const lag = async () => {
    const ms = live().latencyMs;
    if (ms) await sleep(ms);
  };
  function inject(op) {
    const i = injected.findIndex((x) => (x.op === op || x.op === '*') && x.count > 0);
    if (i >= 0) {
      injected[i].count -= 1;
      throw err(injected[i].code, `injected ${injected[i].code}`);
    }
  }
  const writable = () => {
    if (live().readOnly) throw err('invalid_argument', 'write below the required sharing level');
  };

  function snapOf(path) {
    const e = docs.get(path);
    const id = path.split('/').pop();
    if (!e) return deepFreeze({ id, exists: false, data: () => undefined, metadata: { fromCache: false, hasPendingWrites: false } });
    if (!e.snap) {
      const data = e.data;
      e.snap = Object.freeze({ id, exists: true, data: () => data, metadata: { fromCache: false, hasPendingWrites: false } });
    }
    return e.snap;
  }
  function putDoc(path, body) {
    const prev = docs.get(path);
    if (!prev && docs.size >= MAX_DOCS) throw err('quota_exceeded', 'artifact database holds at most 5,000 documents');
    docs.set(path, { data: deepFreeze(body), version: (prev?.version || 0) + 1, snap: null });
    calls.writes.push({ op: 'put', path });
    queueNotify();
  }
  function evalQuery(q) {
    const parent = q.path;
    const depth = parent.split('/').length + 1;
    let rows = [];
    for (const [p, e] of docs) {
      if (p.startsWith(`${parent}/`) && p.split('/').length === depth) rows.push({ id: p.split('/').pop(), path: p, e });
    }
    for (const f of q.filters) rows = rows.filter((r) => matches(r.e.data, f));
    if (q.order) {
      const { field, dir } = q.order;
      rows.sort((a, b) => {
        const av = a.e.data[field];
        const bv = b.e.data[field];
        const am = av === undefined;
        const bm = bv === undefined;
        if (am || bm) return am && bm ? (a.id < b.id ? -1 : 1) : am ? 1 : -1;
        const c = cmp(av, bv);
        return c !== 0 ? (dir === 'desc' ? -c : c) : a.id < b.id ? -1 : 1;
      });
    } else rows.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
    if (q.limit) rows = rows.slice(0, q.limit);
    return rows.map((r) => snapOf(r.path));
  }
  function querySnapshot(list, prevList) {
    const prevIdx = new Map((prevList || []).map((d, i) => [d.id, i]));
    const curIdx = new Map(list.map((d, i) => [d.id, i]));
    return Object.freeze({
      docs: list,
      size: list.length,
      empty: list.length === 0,
      metadata: { fromCache: false, hasPendingWrites: false },
      docChanges() {
        const out = [];
        list.forEach((d, i) => {
          if (!prevIdx.has(d.id)) out.push({ type: 'added', doc: d, oldIndex: -1, newIndex: i });
          else if (prevList[prevIdx.get(d.id)].data() !== d.data()) out.push({ type: 'modified', doc: d, oldIndex: prevIdx.get(d.id), newIndex: i });
        });
        (prevList || []).forEach((d, i) => {
          if (!curIdx.has(d.id)) out.push({ type: 'removed', doc: d, oldIndex: i, newIndex: -1 });
        });
        return out;
      },
    });
  }

  function queueNotify() {
    if (notifyQueued) return;
    notifyQueued = true;
    queueMicrotask(async () => {
      notifyQueued = false;
      await lag();
      for (const s of [...subs]) deliver(s);
    });
  }
  function deliver(s) {
    if (!s.active) return;
    if (s.kind === 'doc') {
      const sn = snapOf(s.path);
      if (s.last && s.last.data() === sn.data() && s.last.exists === sn.exists) return;
      s.last = sn;
      s.next(sn);
    } else {
      const list = evalQuery(s.q);
      if (s.last && s.last.length === list.length && s.last.every((d, i) => d === list[i])) return;
      const snap = querySnapshot(list, s.last);
      s.last = list;
      s.next(snap);
    }
  }
  function subscribe(s, next, error) {
    s.next = next;
    s.active = true;
    s.last = null;
    if (subs.size >= MAX_SUBS) {
      setTimeout(() => error && error(err('resource_exhausted', 'subscription cap (64 per view) reached')), 0);
      return () => {};
    }
    subs.add(s);
    (async () => {
      await ready;
      await lag();
      if (!s.active) return;
      try {
        if (s.invalid) throw err('invalid_argument', s.invalid);
        deliver(s);
        if (!s.last) {
          // first delivery of an empty / missing result still has to happen
          if (s.kind === 'doc') {
            s.last = snapOf(s.path);
            s.next(s.last);
          } else {
            s.last = [];
            s.next(querySnapshot([], null));
          }
        }
      } catch (e) {
        s.active = false;
        subs.delete(s);
        error && error(e);
      }
    })();
    return () => {
      s.active = false;
      subs.delete(s);
    };
  }

  // ---------- references ----------
  function docRef(path) {
    checkPath(path, true);
    const ref = {
      id: path.split('/').pop(),
      path,
      async get() {
        await ready;
        await lag();
        inject('get');
        return snapOf(path);
      },
      async set(data) {
        await ready;
        await lag();
        inject('set');
        writable();
        const body = prepareBody(data);
        checkSize(body);
        putDoc(path, body);
      },
      async update(data) {
        await ready;
        await lag();
        inject('update');
        writable();
        const patch = prepareBody(data);
        const cur = docs.get(path);
        if (!cur) throw err('invalid_argument', 'update requires an existing document');
        const body = mergeInto(cur.data, patch);
        if (depthOf(body) > MAX_DEPTH) throw err('invalid_argument', 'document deeper than 32 levels');
        checkSize(body);
        putDoc(path, body);
      },
      async delete() {
        await ready;
        await lag();
        inject('delete');
        writable();
        if (docs.delete(path)) {
          calls.writes.push({ op: 'delete', path });
          queueNotify();
        }
      },
      async acquire(opts) {
        await ready;
        await lag();
        inject('acquire');
        writable();
        if (!opts || typeof opts.holder !== 'string' || !opts.holder) throw err('invalid_argument', 'holder required');
        const ttl = Math.min(600000, Math.max(1000, opts.ttlMs || 30000));
        const now = Date.now();
        const l = leases.get(path);
        if (l && l.expiresAt > now && l.holder !== opts.holder) return { acquired: false, expiresAt: new Date(l.expiresAt).toISOString() };
        leases.set(path, { holder: opts.holder, expiresAt: now + ttl });
        const cur = docs.get(path);
        if (opts.data || (!cur && live().acquireCreatesDoc)) {
          const body = mergeInto(cur ? cur.data : {}, prepareBody(opts.data || {}));
          checkSize(body);
          putDoc(path, body);
        }
        return { acquired: true, version: docs.get(path)?.version ?? 0, expiresAt: new Date(now + ttl).toISOString(), holder: opts.holder };
      },
      onSnapshot(next, error) {
        return subscribe({ kind: 'doc', path }, next, error);
      },
      collection(sub) {
        return collRef(`${path}/${sub}`);
      },
    };
    return ref;
  }

  function makeQuery(path, state) {
    const q = { path, filters: [], order: null, limit: 0, invalid: null, ...state };
    const next = (patch) => makeQuery(path, { ...q, ...patch });
    return {
      where(field, op, value) {
        const filters = [...q.filters, { field, op, value }];
        let invalid = q.invalid;
        if (!OPS.has(op)) invalid = `unknown operator ${op}`;
        else if (filters.length > 10) invalid = 'more than 10 filters';
        else if ((op === 'in' || op === 'not-in') && (!Array.isArray(value) || value.length > 30)) invalid = 'in/not-in need an array of at most 30';
        return next({ filters, invalid });
      },
      orderBy(field, dir = 'asc') {
        return next({ order: { field, dir }, invalid: q.order ? 'only one orderBy allowed' : q.invalid });
      },
      limit(n) {
        return next({ limit: n, invalid: !(n >= 1 && n <= 1000) ? 'limit must be 1-1000' : q.invalid });
      },
      async get() {
        await ready;
        await lag();
        inject('query');
        if (q.invalid) throw err('invalid_argument', q.invalid);
        return querySnapshot(evalQuery(q), null);
      },
      onSnapshot(nextFn, error) {
        return subscribe({ kind: 'query', q, invalid: q.invalid }, nextFn, error);
      },
    };
  }
  function collRef(path) {
    checkPath(path, false);
    const base = makeQuery(path, {});
    return {
      ...base,
      path,
      doc(id) {
        const did = id || `auto_${Math.random().toString(36).slice(2, 12)}`;
        return docRef(`${path}/${did}`);
      },
      async add(data) {
        const ref = this.doc();
        await ref.set(data);
        return ref;
      },
    };
  }
  const dbNs = Object.freeze({ doc: docRef, collection: collRef });

  // ---------- user ----------
  const isOwnerNow = () => !!(live().owner ?? true) && !live().readOnly;
  const canEditNow = () => !live().readOnly;
  const me = async () => ({
    id: live().userId,
    name: live().userName,
    avatarUrl: 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>',
    color: '#5b7bc4',
    email: null,
    isOwner: isOwnerNow(),
    canEdit: canEditNow(),
  });
  const userNs = Object.freeze({
    isOwner: async () => isOwnerNow(),
    canEdit: async () => canEditNow(),
    can: async (name) => (name === 'data.write' || name === 'files.write' || name === 'assets.write' ? canEditNow() : false),
    me,
    id: async () => live().userId,
    name: async () => live().userName,
    avatarUrl: async () => (await me()).avatarUrl,
    email: async () => null,
    profiles: async (ids) => {
      const list = Array.isArray(ids) ? ids : [ids];
      const out = {};
      for (const id of list) out[id] = { id, name: id === live().userId ? live().userName : '', avatarUrl: '', color: '#888888', email: null, isMe: id === live().userId };
      return out;
    },
    search: async () => [],
  });

  // ---------- downloads ----------
  const DL_EXT = new Set('gif png jpg jpeg webp mp4 webm txt json md docx pptx epub csv ttf html svg pdf xlsx zip'.split(' '));
  const downloadsNs = Object.freeze({
    async save({ filename, data, request } = {}) {
      await lag();
      const ext = String(filename || '').split('.').pop().toLowerCase();
      if (typeof filename !== 'string' || !filename || filename.length > 512) throw err('bad_request', 'bad filename');
      if (!DL_EXT.has(ext) || !filename.includes('.')) throw err('rejected_extension', `extension .${ext} not allowed`);
      const size = typeof data === 'string' ? bytesOf(data) : data?.byteLength ?? data?.size ?? 0;
      if (!size) throw err('bad_request', 'empty data');
      if (live().declineDownloads) throw err('declined', 'viewer declined');
      calls.downloads.push({ filename, ext, size, data, request, at: Date.now() });
      return { status: request ? 'delivered' : 'saved' };
    },
  });

  // ---------- assets ----------
  const ASSET_TYPES = new Set(['image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/svg+xml', 'video/mp4', 'video/webm', 'application/pdf', 'font/woff2', 'font/woff', 'font/ttf', 'font/otf', 'text/csv', 'text/markdown', 'application/json', 'text/plain', 'text/css', 'text/javascript']);
  const assetStore = new Map();
  const hex32 = () => Array.from({ length: 32 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
  const assetsNs = Object.freeze({
    async upload(blob, opts = {}) {
      await lag();
      if (typeof Blob === 'undefined' || !(blob instanceof Blob)) throw err('invalid_request', 'first argument must be a Blob');
      if (!blob.size) throw err('invalid_request', 'empty blob');
      const type = opts.type || blob.type;
      if (!type) throw err('invalid_request', 'type required');
      if (!ASSET_TYPES.has(type)) throw err('unsupported_type', `type ${type} not accepted`);
      const limit = type === 'image/svg+xml' ? 2 * 1048576 : type === 'text/css' || type === 'text/javascript' ? 16 * 1048576 : 20 * 1048576;
      if (blob.size > limit) throw err('too_large', 'over the per-file limit');
      const id = hex32();
      assetStore.set(id, { id, blob, contentType: type, sizeBytes: blob.size, createdAt: new Date().toISOString() });
      calls.uploads.push({ id, type, size: blob.size });
      return { id, url: `/_blob/${id}`, sizeBytes: blob.size, contentType: type };
    },
    async list() {
      return { assets: [...assetStore.values()].map((a) => ({ id: a.id, url: `/_blob/${a.id}`, contentType: a.contentType, sizeBytes: a.sizeBytes, createdAt: a.createdAt })), usage: { files: assetStore.size, bytes: [...assetStore.values()].reduce((n, a) => n + a.sizeBytes, 0), maxFiles: 1000, maxBytes: 1024 * 1048576 } };
    },
    async delete(ref) {
      const id = String(ref).replace('/_blob/', '');
      return { deleted: assetStore.delete(id) };
    },
  });

  // ---------- claude.use ----------
  const memo = new Map();
  const claude = Object.freeze({
    use(name) {
      if (!memo.has(name)) {
        memo.set(
          name,
          (async () => {
            await ready;
            const f = live();
            if (name === 'db') return f.noDb ? null : dbNs;
            if (name === 'user') return f.noUser ? null : userNs;
            if (name === 'downloads') return f.noDownloads ? null : downloadsNs;
            if (name === 'assets') return f.readOnly || f.noAssets ? null : assetsNs;
            return null;
          })(),
        );
      }
      return memo.get(name);
    },
  });

  function load(seed) {
    for (const [coll, map] of Object.entries(seed || {})) {
      for (const [id, body] of Object.entries(map)) {
        const b = clone(body);
        docs.set(`${coll}/${id}`, { data: deepFreeze(b), version: 1, snap: null });
      }
    }
    queueNotify();
  }
  if (options.seed) ready = Promise.resolve(options.seed).then((s) => load(s));

  return {
    claude,
    flags,
    calls,
    db: {
      namespace: dbNs,
      get size() { return docs.size; },
      dump: () => Object.fromEntries([...docs].map(([p, e]) => [p, e.data])),
      listeners: () => subs.size,
      load,
      version: (path) => docs.get(path)?.version ?? 0,
      expireLeases: () => leases.clear(),
    },
    assets: { store: assetStore },
    /** Make the next `count` calls of `op` ('get' | 'set' | 'update' | 'delete' | 'acquire' | 'query' | '*') reject with `code`. */
    failNext(op, code = 'unavailable', count = 1) {
      injected.push({ op, code, count });
    },
    whenReady: () => ready,
  };
}
