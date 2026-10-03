// Null-safe wrappers around claude.use('db' | 'user' | 'downloads' | 'assets').
// Nothing here ever throws because a capability is missing: callers get null / false / result objects.
import { S } from '../lib/i18n.js';

function withTimeout(p, ms) {
  let t;
  const timeout = new Promise((resolve) => {
    t = setTimeout(() => resolve(null), ms);
  });
  return Promise.race([p, timeout]).finally(() => clearTimeout(t));
}

async function use(claude, name, timeoutMs) {
  try {
    if (!claude || typeof claude.use !== 'function') return null;
    return (await withTimeout(Promise.resolve(claude.use(name)), timeoutMs)) ?? null;
  } catch {
    return null;
  }
}

async function safe(fn, fallback) {
  try {
    const v = await fn();
    return v === undefined ? fallback : v;
  } catch {
    return fallback;
  }
}

function makeUser(ns, me) {
  const isOwner = !!(me && me.isOwner);
  const canEdit = !!(me && (me.canEdit || me.isOwner));
  const level = !ns ? 'unknown' : isOwner ? 'owner' : canEdit ? 'editor' : 'viewer';
  const state = { me, isOwner, canEdit, level };
  return {
    /** Opaque per-organisation id or null (never display or parse it). */
    get id() {
      return state.me?.id ?? null;
    },
    get name() {
      return state.me?.name || '';
    },
    get level() {
      return state.level;
    },
    get available() {
      return !!ns;
    },
    canEdit: () => state.canEdit,
    isOwner: () => state.isOwner,
    /** Re-read the viewer (used after the platform changes access while the page is open). */
    async refresh() {
      if (!ns) return state;
      const m = await safe(() => ns.me(), null);
      if (m) {
        state.me = m;
        state.isOwner = !!m.isOwner;
        state.canEdit = !!(m.canEdit || m.isOwner);
        state.level = state.isOwner ? 'owner' : state.canEdit ? 'editor' : 'viewer';
      }
      return state;
    },
    /** Resolve ids to display profiles. Never rejects; unknown ids get an unresolved entry. */
    async profiles(ids) {
      const list = Array.isArray(ids) ? ids : [ids];
      if (ns) {
        const r = await safe(() => ns.profiles(list), null);
        if (r) return r;
      }
      const out = {};
      for (const id of list) out[id] = { id, name: '', avatarUrl: '', color: '', email: null, isMe: id === state.me?.id };
      return out;
    },
  };
}

const DL_MESSAGES = {
  declined: S.downloads.declined,
  rate_limited: S.downloads.rate,
  too_large: S.downloads.tooLarge,
  rejected_extension: S.downloads.badExt,
  extension_not_enabled: S.downloads.badExt,
  unavailable: S.downloads.unavailable,
  not_granted: S.downloads.unavailable,
  capability_disabled: S.downloads.unavailable,
  capability_removed: S.downloads.unavailable,
};

function makeDownloads(ns) {
  return {
    available: !!ns,
    /** Offer a file to the viewer. Resolves { ok, status } or { ok:false, code, message }; never rejects. */
    async save({ filename, data }) {
      if (!ns) return { ok: false, code: 'unavailable', message: S.downloads.unavailable };
      try {
        const r = await ns.save({ filename, data });
        return { ok: true, status: r?.status || 'saved', message: S.downloads.saved };
      } catch (e) {
        const code = e?.code || 'unavailable';
        return { ok: false, code, declined: code === 'declined', message: DL_MESSAGES[code] || S.downloads.failed };
      }
    },
  };
}

function makeAssets(ns) {
  return {
    available: !!ns,
    /** Upload a Blob/File. Resolves { ok:true, id, url, sizeBytes, contentType } or { ok:false, code }; never rejects. */
    async upload(blob, options) {
      if (!ns) return { ok: false, code: 'not_granted' };
      try {
        const r = await ns.upload(blob, options);
        return { ok: true, ...r };
      } catch (e) {
        return { ok: false, code: e?.code || 'upstream_error', message: e?.message };
      }
    },
    async list() {
      if (!ns) return null;
      return safe(() => ns.list(), null);
    },
    async remove(ref) {
      if (!ns) return { ok: false, code: 'not_granted' };
      try {
        return { ok: true, ...(await ns.delete(ref)) };
      } catch (e) {
        return { ok: false, code: e?.code || 'upstream_error' };
      }
    },
  };
}

/**
 * Resolve every capability once. `claude` defaults to window.claude (absent when the page is opened outside
 * claude.ai: then everything is null and the app shows its explanatory empty state).
 */
export async function initRuntime({ claude = globalThis.window?.claude, timeoutMs = 12000 } = {}) {
  const [db, userNs, dlNs, assetNs] = await Promise.all([
    use(claude, 'db', timeoutMs),
    use(claude, 'user', timeoutMs),
    use(claude, 'downloads', timeoutMs),
    use(claude, 'assets', timeoutMs),
  ]);
  const me = userNs ? await safe(() => userNs.me(), null) : null;
  const user = makeUser(userNs, me);
  const downloads = makeDownloads(dlNs);
  const assets = makeAssets(assetNs);
  return {
    db,
    user,
    downloads,
    assets,
    claudePresent: !!(claude && typeof claude.use === 'function'),
    caps: { db: !!db, user: !!userNs, downloads: !!dlNs, assets: !!assetNs },
  };
}
