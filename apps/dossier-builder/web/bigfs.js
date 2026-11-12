/* Large files in the browser's storage. IndexedDB refuses one value over about 127 MB, and a refused value stops the whole save: a
   single large document in the workspace would leave everything written after it unsaved. A large file is therefore stored as a
   Blob — which the browser keeps on disk, with no such ceiling — and read back into the engine's file system when the page opens.
   What was stored before (bytes in the value itself) is read as it always was.
   A Blob is handed to the storage by reference and its bytes follow it: a save is called done only once every Blob it wrote reads
   back from the storage (a page closed at that very moment would otherwise leave a file that cannot be read). One that does not
   read back is taken out again, so the next save writes it afresh.
   DB_BIGFS(IDBFS) → sync(FS, populate): a promise that ends when everything is in place (the large files included). */
function DB_BIGFS(IDBFS, limit) {
  limit = limit || 32 * 1048576;
  let waiting = [], unread = [];                                       // large files being read at start · Blobs written and not read back yet
  const put = IDBFS.storeRemoteEntry, get = IDBFS.loadRemoteEntry;
  IDBFS.storeRemoteEntry = (store, path, entry, callback) => {
    const c = entry && entry.contents;
    if (c && c.byteLength > limit) {
      try { entry = { timestamp: entry.timestamp, mode: entry.mode, contents: new Blob([c]) }; } catch (e) { return callback(e); }
      unread.push({ db: store.transaction.db, name: store.name, path });
    }
    return put(store, path, entry, callback);
  };
  IDBFS.loadRemoteEntry = (store, path, callback) => get(store, path, (err, entry) => {
    if (err || !entry || !(entry.contents instanceof Blob)) return callback(err, entry);
    waiting.push(entry.contents.arrayBuffer()                         // after the transaction: reading a Blob is not a database request
      .then(buf => new Promise((ok, bad) => IDBFS.storeLocalEntry(path, { timestamp: entry.timestamp, mode: entry.mode, contents: new Uint8Array(buf) }, e => e ? bad(e) : ok())))
      .catch(e => console.warn('a large file could not be read back from the browser storage', path, e)));
  });
  const request = (s, mode, what) => new Promise((ok, bad) => {
    let q; try { q = what(s.db.transaction([s.name], mode).objectStore(s.name)); } catch (e) { return bad(e); }
    q.onsuccess = () => ok(q.result); q.onerror = () => bad(q.error);
  });
  const readBack = s => request(s, 'readonly', st => st.get(s.path))
    .then(e => { const b = e && e.contents; return b instanceof Blob ? b.slice(Math.max(0, b.size - 1)).arrayBuffer() : null; })       // its last byte: all of it is in the storage
    .catch(e => request(s, 'readwrite', st => st.delete(s.path)).catch(() => {}).then(() => { throw e; }));
  return (FS, populate) => new Promise((res, rej) => { waiting = [];
    FS.syncfs(populate, e => e ? rej(e) : Promise.all(waiting.concat(unread.splice(0).map(readBack))).then(() => res(), rej)); });
}
