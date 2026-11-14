// Where the dossiers being prepared are kept: in the browser's own database (IndexedDB) on this computer, each dossier as one
// record and every file as a blob beside it, so closing the page loses nothing. A browser can wipe its data (a private window,
// «clear site data»), so a dossier can also be saved as one file (a ZIP: dossier.json and the files) and opened again from it.
// Where the browser gives no database, the dossiers live in memory only, and the page says so.
import { zipOf } from './zipw.js';
import { unzip } from '../prep/zip.js';

const NAME = 'dossier-builder-workshop', VERSION = 1;
let dbp = null;
const memory = { dossiers: new Map(), blobs: new Map() };
export let persistent = true;

function open() {
  if (dbp) return dbp;
  dbp = new Promise(ok => {
    try {
      const r = indexedDB.open(NAME, VERSION);
      r.onupgradeneeded = () => { r.result.createObjectStore('dossiers', { keyPath: 'id' }); r.result.createObjectStore('blobs'); };
      r.onsuccess = () => ok(r.result);
      r.onerror = () => { persistent = false; ok(null); };
      r.onblocked = () => { persistent = false; ok(null); };
    } catch { persistent = false; ok(null); }
  });
  return dbp;
}
async function tx(store, mode, work) {
  const db = await open();
  if (!db) return work(null);
  return new Promise((ok, no) => {
    const t = db.transaction(store, mode);
    let out;
    Promise.resolve(work(t.objectStore(store))).then(v => { out = v; });
    t.oncomplete = () => ok(out);
    t.onerror = () => no(t.error);
    t.onabort = () => no(t.error || new Error('the browser refused to save'));
  });
}
const req = r => new Promise((ok, no) => { r.onsuccess = () => ok(r.result); r.onerror = () => no(r.error); });

export async function listDossiers() {
  const all = await tx('dossiers', 'readonly', s => (s ? req(s.getAll()) : [...memory.dossiers.values()]));
  return all.map(d => ({ id: d.id, name: d.name, country: d.country, updated: d.updated, docs: d.docs?.length || 0 }))
            .sort((a, b) => String(b.updated).localeCompare(String(a.updated)));
}
export const getDossier = id => tx('dossiers', 'readonly', s => (s ? req(s.get(id)) : structuredClone(memory.dossiers.get(id))));
export async function putDossier(d) {
  d.updated = new Date().toISOString();
  const copy = JSON.parse(JSON.stringify(d));
  await tx('dossiers', 'readwrite', s => (s ? req(s.put(copy)) : memory.dossiers.set(d.id, copy)));
  return d;
}
export async function deleteDossier(id) {
  await tx('dossiers', 'readwrite', s => (s ? req(s.delete(id)) : memory.dossiers.delete(id)));
  await tx('blobs', 'readwrite', s => {
    if (!s) { for (const k of [...memory.blobs.keys()]) if (k.startsWith(`${id}/`)) memory.blobs.delete(k); return null; }
    return req(s.delete(IDBKeyRange.bound(`${id}/`, `${id}/￿`)));
  });
}
export const putBlob = (dossierId, key, bytes) =>
  tx('blobs', 'readwrite', s => (s ? req(s.put(new Blob([bytes]), `${dossierId}/${key}`)) : memory.blobs.set(`${dossierId}/${key}`, new Blob([bytes]))));
export async function getBlob(dossierId, key) {
  const b = await tx('blobs', 'readonly', s => (s ? req(s.get(`${dossierId}/${key}`)) : memory.blobs.get(`${dossierId}/${key}`)));
  return b ? new Uint8Array(await b.arrayBuffer()) : null;
}
async function blobKeys(dossierId) {
  return tx('blobs', 'readonly', s => (s ? req(s.getAllKeys(IDBKeyRange.bound(`${dossierId}/`, `${dossierId}/￿`)))
                                          : [...memory.blobs.keys()].filter(k => k.startsWith(`${dossierId}/`))));
}

// The whole dossier as one file, and back.
export async function exportDossier(id) {
  const d = await getDossier(id);
  if (!d) throw new Error('the dossier is not here');
  const files = [{ name: 'dossier.json', bytes: new TextEncoder().encode(JSON.stringify(d, null, 1)) }];
  for (const k of await blobKeys(id)) files.push({ name: `files/${k.slice(id.length + 1)}`, bytes: await getBlob(id, k.slice(id.length + 1)) });
  return zipOf(files);
}
export async function importDossier(bytes) {
  const { files } = await unzip(bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes));
  const main = files.find(f => f.name === 'dossier.json');
  if (!main) throw new Error('this file is not a saved dossier (it holds no dossier.json)');
  const d = JSON.parse(new TextDecoder().decode(main.bytes));
  if (!d?.id || !Array.isArray(d.docs)) throw new Error('this file is not a saved dossier');
  if (await getDossier(d.id)) d.id = `${d.id}-${Date.now().toString(36)}`;     // opened twice: a second dossier, not over the first
  for (const f of files) if (f.name.startsWith('files/') && f.bytes) await putBlob(d.id, f.name.slice(6), f.bytes);
  await putDossier(d);
  return d;
}

export async function sha256(bytes) {
  const h = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(h)].map(x => x.toString(16).padStart(2, '0')).join('');
}
