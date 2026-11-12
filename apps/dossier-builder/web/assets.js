/* The runtime's own files — the Python engine, its libraries, the rule packs: about 30 MB — are kept in the browser's storage after
   the first download. Opening again reads them from the device, with nothing fetched, and a new version of the program fetches
   only the files that changed. Each file is known by a tag written at build time (DB_MANIFEST: path → [bytes on the wire, tag,
   needed at start, bytes once decoded]); what is stored and does not match is fetched again. Anything wrong with the storage
   falls back to the network: the cache can make an opening faster, never stop one.
   DB_ASSETS(manifest, fetch, report) → { get(path, url) → Promise<Uint8Array>, tidy(), state }
   report({loaded, total, net, file}) is called as bytes arrive: `loaded` of `total` for the files a start needs, `net` the part
   of it that came over the network (0: everything was on the device). */
function DB_ASSETS(manifest, realFetch, report) {
  const st = { loaded: 0, net: 0, file: '', total: Object.keys(manifest).reduce((a, k) => a + (manifest[k][2] ? manifest[k][0] : 0), 0) };
  let dbp = null;
  const open = () => dbp || (dbp = new Promise(res => {
    try {
      const q = indexedDB.open('db-runtime', 1);
      q.onupgradeneeded = () => { try { q.result.createObjectStore('files'); } catch (e) {} };
      q.onsuccess = () => res(q.result); q.onerror = q.onblocked = () => res(null);
    } catch (e) { res(null); }
  }));
  const ask = (mode, what) => open().then(db => db ? new Promise(res => {
    try { const q = what(db.transaction('files', mode).objectStore('files')); q.onsuccess = () => res(q.result); q.onerror = () => res(undefined); }
    catch (e) { res(undefined); }
  }) : undefined);
  const tell = () => { try { if (report) report(st); } catch (e) {} };
  function decode64(text) {
    const bin = atob(text), out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  async function text(r, counted) {                                    // the answer's text, counted as it arrives
    const count = n => { if (counted) { st.loaded += n; st.net += n; tell(); } };
    if (!r.body || !r.body.getReader) { const t = await r.text(); count(t.length); return t; }
    const reader = r.body.getReader(), dec = new TextDecoder(), parts = [];
    for (;;) { const { done, value } = await reader.read(); if (done) break; parts.push(dec.decode(value, { stream: true })); count(value.length); }
    parts.push(dec.decode());
    return parts.join('');
  }
  /* path: as the manifest names the file ('assets/pyodide/pyodide.asm.wasm'); url: where its base64 text is */
  async function get(path, url) {
    const m = manifest[path];
    st.file = path;
    if (m) {
      const rec = await ask('readonly', s => s.get(path));
      if (rec && rec.tag === m[1] && rec.data && rec.data.byteLength === m[3]) { if (m[2]) { st.loaded += m[0]; tell(); } return new Uint8Array(rec.data); }
    }
    const r = await realFetch(url);
    if (!r.ok) { const e = new Error(path + ': HTTP ' + r.status); e.status = r.status; throw e; }
    const bytes = decode64(await text(r, !!(m && m[2])));
    if (m && bytes.length === m[3]) { const keep = bytes.buffer.slice(0); ask('readwrite', s => s.put({ tag: m[1], data: keep }, path)); }      // for the next opening; not waited for
    return bytes;
  }
  /* what is stored and is no part of this version goes */
  const tidy = () => ask('readonly', s => s.getAllKeys()).then(keys => { (keys || []).forEach(k => { if (!manifest[k]) ask('readwrite', s => s.delete(k)); }); }).catch(() => {});
  return { get, tidy, state: st };
}
