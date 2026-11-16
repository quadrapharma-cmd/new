/* Compressed files: an archive among the files a person gives is opened and what is inside it is taken like any other file.
   ZIP, TAR and GZ are unpacked by the engine everywhere. RAR is opened here in the page, in every edition, by the program's own
   reader (rar.js: RAR 2.9 to RAR5, solid archives, archives split in parts, names in any language; every file checked against its
   CRC); what the reader does not open — an archive older than RAR 2.9, one the page's memory cannot hold — goes to the machine's own
   unpacker where there is one (desktop, server). 7z is opened here in the page too, in every edition, by the program's own reader
   (sevenz.js: LZMA2 and LZMA, the x86 and delta filters, solid archives, names in any language; every file checked against its
   CRC); what it does not read — another compression method (PPMd, BZip2…), a password, an archive split in parts — goes to the
   machine's own unpacker where there is one (desktop, server), and is refused with its reason in the browser edition. There is no
   limit of the program's own on an archive's size or on the files in it. An archive found inside an archive is opened too. */
(function () {
  const ARCH_RX = /\.(zip|rar|7z|tar|tgz|tbz2?|txz|gz|bz2|xz|[rs]\d\d)$/i;
  const RAR_RX = /\.(rar|[rs]\d\d)$/i;
  const SEVENZ_RX = /\.7z$/i;
  const AR = () => (document.documentElement.lang || 'ar') !== 'en';
  const say = (ar, en) => AR() ? ar : en;
  const SYSTEM = /(^|\/)(__MACOSX\/|\.DS_Store$|Thumbs\.db$|desktop\.ini$|~\$[^/]*$|\._[^/]*$|\.~lock\.[^/]*$)/i;

  async function head(file, n) { return String.fromCharCode.apply(null, new Uint8Array(await file.slice(0, n || 8).arrayBuffer())); }
  /* 'rar' | '7z' | 'archive' | null — by its name, or by its first bytes when the name has no extension (a Drive title) */
  async function kindOf(file) {
    const name = (file && file.name) || '';
    if (!file) return null;
    if (RAR_RX.test(name)) return 'rar';
    if (SEVENZ_RX.test(name)) return '7z';
    if (ARCH_RX.test(name)) return 'archive';
    if (/\.[A-Za-z0-9]{1,6}$/.test(name)) return null;
    const s = await head(file);
    return s.startsWith('Rar!\x1a\x07') ? 'rar' : s.startsWith("7z\xbc\xaf'\x1c") ? '7z' : null;
  }
  async function isArchive(file) { return !!(await kindOf(file)); }

  function fail(code, ar, en) { const e = new Error(say(ar, en)); e.code = code; return e; }
  /* names for the files: the name alone, with its folder in front when two files of one name sit in different folders */
  function named(entries) {
    const seen = {}; entries.forEach(e => { const b = e.name.split('/').pop(); seen[b] = (seen[b] || 0) + 1; });
    return entries.map(e => { const parts = e.name.split('/'), base = parts.pop();
      const f = new File(e.parts, seen[base] > 1 && parts.length ? parts.join(' - ') + ' - ' + base : base, { type: '' }); f.dbPath = e.name; return f; });
  }

  /* ---------------- the engine: ZIP, TAR, GZ everywhere; RAR and 7z where the machine has an unpacker */
  async function unpack(file) {
    const fd = new FormData(); fd.append('file', file, file.name || 'archive');
    const r = await fetch('/api/archives/unpack', { method: 'POST', body: fd, headers: { 'X-DB': '1' } });
    if (!r.ok) {
      const d = ((await r.json().catch(() => ({}))).detail) || {};
      const e = new Error(d[AR() ? 'ar' : 'en'] || d.en || r.statusText); e.code = d.code; throw e;
    }
    const buf = await r.arrayBuffer(), u = new Uint8Array(buf);
    if (String.fromCharCode.apply(null, u.subarray(0, 5)) !== 'DBAR1') throw new Error('unexpected answer');
    const n = new DataView(buf).getUint32(5), meta = JSON.parse(new TextDecoder().decode(u.subarray(9, 9 + n)));
    let pos = 9 + n;
    const files = named(meta.files.map(f => { const e = { name: f.name, parts: [buf.slice(pos, pos + f.size)] }; pos += f.size; return e; }));
    return { kind: meta.kind, files, skipped: meta.skipped || [], deep: true };
  }

  /* ---------------- RAR in the page: the program's own reader, in a worker */
  /* no limit of the program's own on an archive's size or on the number of files in it: only the memory the browser gives the page */
  const noMemory = () => fail('E-ARCHIVE-BIG', 'لم تكفِ ذاكرة المتصفح لفك هذا الأرشيف كله دفعة واحدة: فُكَّه على جهازك وارفع الملفات نفسها.', 'The browser does not have the memory to unpack this archive at once: unpack it on your computer and upload the files themselves.');
  function rarError(e) {
    const code = e && e.rar;
    if (code === 'password') return fail('E-ARCHIVE-PASSWORD', 'الأرشيف محمي بكلمة مرور: فُكَّه أولًا.', 'The archive is protected with a password: unpack it first.');
    if (code === 'big' && e.why === 'bomb') return Object.assign(fail('E-ARCHIVE-BIG', 'يتمدد الأرشيف عند فكه إلى حجم كبير جدًا (مئات أضعاف حجمه): فُكَّه على جهازك واختر ما يحتاج إليه الملف.', 'The archive expands hundreds of times its size: unpack it on your computer and choose what the dossier needs.'), { bomb: true });
    if (code === 'big' || code === 'memory') return noMemory();
    if (code === 'damaged') return fail('E-ARCHIVE', 'ملف RAR تالف أو غير مكتمل.', 'The RAR file is damaged or incomplete.');
    return fail('E-ARCHIVE', 'تعذّر فتح ملف RAR.', 'The RAR file could not be opened.');
  }
  /* vols: the parts of ONE archive in order ({file}); opts.keep: a RegExp of the names worth taking (the others are not unpacked) */
  async function unrar(vols, opts) {
    opts = opts || {};
    if (!window.DBRAR) throw fail('E-ARCHIVE-TOOL', 'فك RAR غير متاح في هذه الصفحة: فُكَّ الأرشيف على جهازك، أو اضغط الملفات بصيغة ZIP.', 'RAR cannot be opened in this page: unpack the archive on your computer, or pack the files as ZIP.');
    let r;
    try {
      r = await window.DBRAR.extract(vols.map(v => v.file), { skipRx: SYSTEM.source,
        keepRx: opts.keep ? '(' + opts.keep.source + ')|(' + ARCH_RX.source + ')' : null }, name => { if (opts.onStatus) opts.onStatus(say('جارٍ فك ', 'Unpacking ') + name.split('/').pop() + '…'); });
    } catch (e) { throw rarError(e); }
    if (!r.files.length && r.skipped.some(s => s.why === 'password')) throw rarError({ rar: 'password' });
    return { kind: 'rar', files: named(r.files), skipped: r.skipped, left: r.left || 0 };
  }

  /* ---------------- 7z in the page: the program's own reader (sevenz.js), in a worker */
  function sevenzError(e) {
    const code = e && e.z7, how = e && e.why && !/^(bomb|files|total)$/.test(e.why) ? ' (' + e.why + ')' : '';
    if (code === 'password') return fail('E-ARCHIVE-PASSWORD', 'الأرشيف محمي بكلمة مرور: فُكَّه أولًا.', 'The archive is protected with a password: unpack it first.');
    if (code === 'big' && e.why === 'bomb') return Object.assign(fail('E-ARCHIVE-BIG', 'يتمدد الأرشيف عند فكه إلى حجم كبير جدًا (مئات أضعاف حجمه): فُكَّه على جهازك واختر ما يحتاج إليه الملف.', 'The archive expands hundreds of times its size: unpack it on your computer and choose what the dossier needs.'), { bomb: true });
    if (code === 'big' || code === 'memory') return noMemory();
    if (code === 'volume') return fail('E-ARCHIVE-VOLUME', 'هذا أرشيف 7z مقسَّم إلى أجزاء أو ناقص: فُكَّه على جهازك وارفع الملفات نفسها.', 'This 7z archive is split in parts or incomplete: unpack it on your computer and upload the files themselves.');
    if (code === 'unsupported') return fail('E-ARCHIVE-METHOD', 'الأرشيف مضغوط بطريقة لا تقرؤها الصفحة' + how + ': فُكَّه على جهازك، أو اضغط الملفات بصيغة ZIP أو 7z بالطريقة المعتادة.', 'The archive uses a compression method this page does not read' + how + ': unpack it on your computer, or pack the files as ZIP or a standard 7z.');
    if (code === 'damaged' || code === 'unreadable') return fail('E-ARCHIVE', 'أرشيف 7z هذا تالف أو غير مكتمل: افتحه على جهازك، وإن فُتح فاضغط الملفات بصيغة ZIP وارفعها.', 'This 7z archive is damaged or incomplete: open it on your computer; if it opens there, pack the files as ZIP and add that.');
    return fail('E-ARCHIVE', 'تعذّر فتح أرشيف 7z هذا: فُكَّه على جهازك، أو اضغط الملفات بصيغة ZIP.', 'This 7z archive could not be opened: unpack it on your computer, or pack the files as ZIP.');
  }
  /* opts.keep: a RegExp of the names worth taking (the others are unpacked only where they share a solid block with one) */
  async function un7z(file, opts) {
    opts = opts || {};
    if (!window.DB7Z) throw fail('E-ARCHIVE-TOOL', 'فك 7z غير متاح في هذه الصفحة: فُكَّ الأرشيف على جهازك، أو اضغط الملفات بصيغة ZIP.', '7z cannot be opened in this page: unpack the archive on your computer, or pack the files as ZIP.');
    let r;
    try {
      r = await window.DB7Z.extract([file], { skipRx: SYSTEM.source,
        keepRx: opts.keep ? '(' + opts.keep.source + ')|(' + ARCH_RX.source + ')' : null }, name => { if (opts.onStatus) opts.onStatus(say('جارٍ فك ', 'Unpacking ') + name.split('/').pop() + '…'); });
    } catch (e) { throw sevenzError(e); }
    const skipped = r.skipped.map(x => x.why === 'unsupported' ? { name: x.name, why: 'method' } : { name: x.name, why: x.why });
    const real = r.files.filter(f => f.parts.some(x => (x.byteLength || 0) > 0));                  // an empty file is not a document
    if (!real.length && skipped.some(x => x.why === 'password')) throw sevenzError({ z7: 'password' });
    if (!real.length && skipped.length && skipped.every(x => x.why === 'method')) throw sevenzError({ z7: 'unsupported', why: r.skipped[0].method });
    return { kind: '7z', files: named(r.files), skipped, left: r.left || 0 };
  }
  async function un7zSet(file, opts) {
    let mine = null, err = null;
    try { mine = await un7z(file, opts); } catch (e) { err = e; }
    const weak = err ? !err.bomb && /^E-ARCHIVE(-TOOL|-BIG|-METHOD|-VOLUME)?$/.test(err.code || '') : !mine.files.length || mine.skipped.some(x => x.why === 'method');
    if (weak && !window.DBWEB) {                                     // desktop, server: the machine's own unpacker may know the method
      try { const theirs = await unpack(file); if (!mine || theirs.files.length > mine.files.length) return theirs; } catch (e) {}
    }
    if (err) throw err;
    return mine;
  }

  /* the parts of an archive split by WinRAR: name.part1.rar, name.part2.rar … or name.rar, name.r00, name.r01 … */
  function volume(name) {
    const m = /(\.part(\d+))?\.(rar|[rs]\d\d)$/i.exec(name || '');
    if (!m) return { key: String(name).toLowerCase(), first: true, order: 0 };
    const ext = m[3].toLowerCase(), part = m[2] ? +m[2] : null, old = ext !== 'rar';
    return { key: name.slice(0, m.index).toLowerCase() + (part !== null ? '.part' : ''), first: part !== null ? part <= 1 && !old : !old,
      order: part !== null ? part : old ? (ext.charCodeAt(0) - 113) * 100 + +ext.slice(1) : 0 };
  }
  async function unrarSet(set, opts) {
    let mine = null, err = null;
    try { mine = await unrar(set, opts); } catch (e) { err = e; }
    const weak = err ? !err.bomb && /^E-ARCHIVE(-TOOL|-BIG)?$/.test(err.code || '') : !mine.files.length || mine.skipped.some(s => s.why === 'unsupported');      // a «bomb» is not handed on to another unpacker
    if (weak && set.length === 1 && !window.DBWEB) {                 // desktop, server: the machine's own unpacker may know an older or a larger archive
      try { const theirs = await unpack(set[0].file); if (!mine || theirs.files.length > mine.files.length) return theirs; } catch (e) {}
    }
    if (err) throw err;
    return mine;
  }

  /* files → the same list with every archive replaced by the documents inside it; notes say what each archive gave */
  async function expand(files, opts, depth) {
    opts = opts || {}; depth = depth || 0;
    const out = [], notes = [], sets = {}, kinds = [];
    for (const f of files) kinds.push(await kindOf(f));
    files.forEach((f, i) => { if (kinds[i] === 'rar') { const v = Object.assign(volume(f.name), { file: f }); (sets[v.key] = sets[v.key] || []).push(v); f.dbVol = v; } });
    for (const [i, f] of files.entries()) {
      if (!kinds[i]) { out.push(f); continue; }
      let r;
      try {
        if (kinds[i] === 'rar') {
          const set = sets[f.dbVol.key];
          if (!f.dbVol.first) {                                      // a later part: taken with its first part
            if (!set.some(v => v.first) && !set.noted) { set.noted = true; throw fail('E-ARCHIVE-VOLUME', 'هذا جزء من أرشيف مقسَّم، والجزء الأول ليس ضمن الملفات: اختر كل الأجزاء معًا.', 'This is one part of a split archive and the first part is not among the files: choose all the parts together.'); }
            continue;
          }
          if (opts.onStatus) opts.onStatus(say('جارٍ فك ', 'Unpacking ') + f.name + '…');
          r = await unrarSet(set.slice().sort((a, b) => a.order - b.order), opts);
        } else if (kinds[i] === '7z') {
          if (opts.onStatus) opts.onStatus(say('جارٍ فك ', 'Unpacking ') + f.name + '…');
          r = await un7zSet(f, opts);
        } else {
          if (opts.onStatus) opts.onStatus(say('جارٍ فك ', 'Unpacking ') + f.name + '…');
          r = await unpack(f);
        }
      } catch (e) { notes.push({ archive: f.name, error: String(e && e.message || e) }); continue; }
      let inside = r.files, skipped = r.skipped.slice();
      if (!r.deep && depth < 2 && inside.some(x => ARCH_RX.test(x.name))) {      // an archive inside the archive (the engine opens those itself)
        const inner = await expand(inside, opts, depth + 1);
        inside = inner.files; inner.notes.forEach(n => { if (n.error) skipped.push({ name: n.archive, why: 'unreadable' }); else skipped.push(...n.skipped); });
      }
      const docs = inside.filter(x => !opts.accept || opts.accept(x.name));
      docs.forEach(d => { if (!d.dbPath) d.dbPath = d.name; });
      out.push(...docs);
      notes.push({ archive: f.name, taken: docs.length, left: inside.length - docs.length + (r.left || 0), skipped });
    }
    return { files: out, notes };
  }

  function summary(notes) {
    const why = { password: say('كلمة مرور', 'password'), 'too large': say('كبير جدًا', 'too large'), link: say('رابط', 'a link'), unreadable: say('تالف', 'damaged'),
      volume: say('جزء من الأرشيف ناقص', 'a part of the archive is missing'), unsupported: say('نسخة RAR قديمة جدًا', 'a very old RAR version'),
      memory: say('ذاكرة المتصفح لم تكفِ', 'the browser ran out of memory'), method: say('طريقة ضغط لا تقرؤها الصفحة', 'a compression method this page does not read') };
    return notes.map(n => n.error ? `${n.archive}: ${n.error}`
      : say(`فُكَّ «${n.archive}»: ${n.taken} مستند`, `«${n.archive}» unpacked: ${n.taken} document(s)`)
        + (n.left ? say(`، وتُرك ${n.left} ملف آخر`, `, ${n.left} other file(s) left out`) : '')
        + (n.skipped.length ? say(`، و${n.skipped.length} تعذّر فتحه`, `, ${n.skipped.length} not opened`) + ' (' + n.skipped.slice(0, 3).map(s => s.name.split('/').pop() + ': ' + (why[s.why] || s.why)).join('، ') + ')' : '')).join(' · ');
  }

  window.DBARCH = { ARCH_RX, isArchive, kindOf, unpack, unrar, un7z, expand, summary };
})();
