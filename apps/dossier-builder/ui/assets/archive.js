/* Compressed files: an archive among the files a person gives is opened and what is inside it is taken like any other file.
   The engine unpacks (ZIP, TAR, GZ everywhere; RAR and 7z where the machine has an unpacker) and answers with one body that is cut
   back into files here. A RAR or 7z in the browser edition is refused with the reason: there is no unpacker inside a browser. */
(function () {
  const ARCH_RX = /\.(zip|rar|7z|tar|tgz|tbz2?|txz|gz|bz2|xz)$/i;
  const AR = () => (document.documentElement.lang || 'ar') !== 'en';
  const say = (ar, en) => AR() ? ar : en;

  /* by its name, or by its first bytes when the name has no extension (a Drive title) */
  async function isArchive(file) {
    if (!file) return false;
    if (ARCH_RX.test(file.name || '')) return true;
    if (/\.[A-Za-z0-9]{1,6}$/.test(file.name || '')) return false;
    const h = new Uint8Array(await file.slice(0, 8).arrayBuffer());
    const s = String.fromCharCode.apply(null, h);
    return s.startsWith('Rar!\x1a\x07') || s.startsWith("7z\xbc\xaf'\x1c");
  }

  async function unpack(file) {
    const fd = new FormData(); fd.append('file', file, file.name || 'archive');
    const r = await fetch('/api/archives/unpack', { method: 'POST', body: fd, headers: { 'X-DB': '1' } });
    if (!r.ok) {
      const d = ((await r.json().catch(() => ({}))).detail) || {};
      const e = new Error(d[AR() ? 'ar' : 'en'] || d.en || r.statusText); e.code = d.code; throw e;
    }
    const buf = await r.arrayBuffer(), u = new Uint8Array(buf);
    if (String.fromCharCode.apply(null, u.subarray(0, 5)) !== 'DBAR1') throw new Error('unexpected answer');
    const n = new DataView(buf).getUint32(5), head = JSON.parse(new TextDecoder().decode(u.subarray(9, 9 + n)));
    const seen = {}, files = []; let pos = 9 + n;
    head.files.forEach(f => { const base = f.name.split('/').pop(); seen[base] = (seen[base] || 0) + 1; });
    for (const f of head.files) {
      const parts = f.name.split('/'), base = parts.pop();
      const name = seen[base] > 1 && parts.length ? parts.join(' - ') + ' - ' + base : base;      // two files of one name in different folders keep apart
      const file2 = new File([buf.slice(pos, pos + f.size)], name, { type: '' });
      file2.dbPath = f.name; files.push(file2); pos += f.size;
    }
    return { kind: head.kind, files, skipped: head.skipped || [] };
  }

  /* files → the same list with every archive replaced by the documents inside it; notes say what each archive gave */
  async function expand(files, opts) {
    opts = opts || {};
    const out = [], notes = [];
    for (const f of files) {
      if (!(await isArchive(f))) { out.push(f); continue; }
      if (opts.onStatus) opts.onStatus(say('بيفك ', 'Unpacking ') + f.name + '…');
      try {
        const r = await unpack(f);
        const docs = r.files.filter(x => !opts.accept || opts.accept(x.name));
        out.push(...docs);
        notes.push({ archive: f.name, taken: docs.length, left: r.files.length - docs.length, skipped: r.skipped });
      } catch (e) { notes.push({ archive: f.name, error: String(e && e.message || e) }); }
    }
    return { files: out, notes };
  }

  function summary(notes) {
    return notes.map(n => n.error ? `${n.archive}: ${n.error}`
      : say(`«${n.archive}» اتفك: ${n.taken} مستند`, `«${n.archive}» unpacked: ${n.taken} document(s)`)
        + (n.left ? say(`، و${n.left} ملف تاني اتساب`, `, ${n.left} other file(s) left out`) : '')
        + (n.skipped.length ? say(`، و${n.skipped.length} ما اتفتحش`, `, ${n.skipped.length} not opened`) + ' (' + n.skipped.slice(0, 3).map(s => s.name.split('/').pop() + ': ' + ({ password: say('كلمة سر', 'password'), 'too large': say('كبير جدًا', 'too large'), link: say('رابط', 'link') }[s.why] || say('تالف', 'unreadable'))).join('، ') + ')' : '')).join(' · ');
  }

  window.DBARCH = { ARCH_RX, isArchive, unpack, expand, summary };
})();
