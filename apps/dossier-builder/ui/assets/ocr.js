/* In-browser OCR for scanned documents (tesseract.js, Arabic + English), used when the server has no tesseract (the browser
   edition, or a desktop without it). Pages of a PDF are rendered with pdf.js; images are read directly. Nothing leaves the
   browser. The page sets window.DB_TESS_BASE and window.DB_PDFJS_BASE (directory URLs) when the assets are served. */
(function () {
  const abs = u => new URL(u, document.baseURI).href;
  let tessP = null, pdfP = null, okP = null;

  async function available() {
    if (!window.DB_TESS_BASE) return false;
    if (!okP) okP = fetch(abs(window.DB_TESS_BASE + 'tesseract.min.js'), { method: 'HEAD' }).then(r => r.ok).catch(() => false);
    return okP;
  }

  function loadTess() {
    if (!tessP) tessP = new Promise((res, rej) => {
      if (window.Tesseract) return res(window.Tesseract);
      const s = document.createElement('script');
      s.src = abs(window.DB_TESS_BASE + 'tesseract.min.js');
      s.onload = () => res(window.Tesseract);
      s.onerror = () => rej(new Error('tesseract.js failed to load'));
      document.head.appendChild(s);
    });
    return tessP;
  }

  function pdfjs() {
    if (!pdfP) {
      const base = abs(window.DB_PDFJS_BASE || 'assets/pdfjs/');
      pdfP = import(base + 'pdf.min.mjs').then(m => { m.GlobalWorkerOptions.workerSrc = base + 'pdf.worker.min.mjs'; return m; });
    }
    return pdfP;
  }

  /* pages → images. For OCR the page is rendered at ~200 dpi (scale 2.8 of a 72-dpi point page) as PNG: resolution decides
     what tesseract reads; for Claude's eyes a lighter JPEG at scale 1.4 is enough. */
  async function pageImages(file, max, scale, type) {
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
    const out = [];
    for (let i = 1; i <= Math.min(doc.numPages, max); i++) {
      const page = await doc.getPage(i), vp = page.getViewport({ scale: scale || 1.4 });
      const c = document.createElement('canvas'); c.width = Math.round(vp.width); c.height = Math.round(vp.height);
      const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
      await page.render({ canvasContext: g, viewport: vp }).promise;
      out.push(await new Promise(r => type === 'png' ? c.toBlob(r, 'image/png') : c.toBlob(r, 'image/jpeg', 0.88)));
    }
    return out;
  }

  async function simd() {
    try {   // a 1-instruction SIMD module: valid only where WebAssembly SIMD is supported
      return WebAssembly.validate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123, 3, 2, 1, 0, 10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11]));
    } catch (e) { return false; }
  }

  let workerP = null;
  async function worker(onProgress) {
    if (!workerP) workerP = (async () => {
      const T = await loadTess();
      const base = abs(window.DB_TESS_BASE);
      const core = base + (await simd() ? 'tesseract-core-simd-lstm.wasm.js' : 'tesseract-core-lstm.wasm.js');
      return T.createWorker(['ara', 'eng'], 1, {
        workerPath: base + 'worker.boot.js', corePath: core, langPath: base.replace(/\/$/, ''), gzip: true, workerBlobURL: false,
        logger: m => { if (onProgress && m && typeof m.progress === 'number') onProgress(m.status, m.progress); },
      });
    })();
    return workerP;
  }

  /* ---- images of every kind → pages the OCR engine opens (PNG or JPEG blobs).
     JPEG and PNG go as they are (a phone photo that its EXIF says is on its side is turned first); what the browser decodes by itself
     (GIF, BMP, WebP, AVIF, ICO, SVG, and HEIC or TIFF in Safari) goes through its decoder; a TIFF is decoded here, page by page
     (UTIF.js: LZW, PackBits, CCITT fax G3/G4, JPEG, Deflate); a HEIC/HEIF photo through libheif (WebAssembly). */
  const imgBase = () => abs(window.DB_IMG_BASE || (window.DB_TESS_BASE || 'assets/tess/').replace(/tess\/?$/, 'img/'));
  /* the image decoders: the copy served with the program (desktop, server, local builds); where there is none (the page published on
     claude.ai carries no copy of them), the same releases from jsDelivr, checked against their hashes */
  const IMG_LIBS = {
    utif: ['UTIF.js', 'https://cdn.jsdelivr.net/npm/utif@3.1.0/UTIF.js', 'sha384-RyBmXHdfZ/Uon+ud+/AqSyWpUWnKYt2tkRG/P4gWoRUGDU+qIAV3tGBPNlYTBZEF', () => !!window.UTIF],
    pako: ['pako_inflate.min.js', 'https://cdn.jsdelivr.net/npm/pako@2.1.0/dist/pako_inflate.min.js', 'sha384-taEjHL+GUvC8IhXeCaTNUxz3O8ItsajGFLDFj4v/VJvM24HU36qP/6sRpuAGGfeT', () => !!window.pako],
    heif: ['libheif-bundle.js', 'https://cdn.jsdelivr.net/npm/libheif-js@1.23.5/libheif-wasm/libheif-bundle.js', 'sha384-QYMUACFeOR9DQlmZGsI+VXolKAMA0hYyiOXLSyd8o5rgrg9L+aKyRZCiiY7RNhPF', () => typeof window.libheif === 'function'],
  };
  const scripts = {};
  function loadScript(url, integrity) {
    return scripts[url] || (scripts[url] = new Promise((res, rej) => {
      const s = document.createElement('script'); s.src = url;
      if (integrity) { s.integrity = integrity; s.crossOrigin = 'anonymous'; }
      s.onload = () => res(); s.onerror = () => { delete scripts[url]; rej(new Error('could not load ' + url.split('/').pop())); };
      document.head.appendChild(s);
    }));
  }
  async function loadLib(k) {
    const [file, cdn, integrity, there] = IMG_LIBS[k];
    if (there()) return;
    await loadScript(imgBase() + file).catch(() => {});
    if (!there()) await loadScript(cdn, integrity).catch(() => {});
    if (!there()) await loadScript(cdn.replace('https://cdn.jsdelivr.net/npm/', 'https://unpkg.com/'), integrity).catch(() => {});   // the same file from a second public mirror
    if (!there()) throw new Error('could not load ' + file);
  }
  const AR = () => (document.documentElement.lang || 'ar') !== 'en';
  function imageKind(h) {
    const s = String.fromCharCode.apply(null, h.subarray(0, 64));
    if (h[0] === 0xFF && h[1] === 0xD8) return 'jpeg';
    if (s.startsWith('\x89PNG')) return 'png';
    if (/^GIF8[79]a/.test(s)) return 'gif';
    if (/^(II\*\0|MM\0\*|II\+\0|MM\0\+)/.test(s)) return 'tiff';
    if (s.slice(0, 4) === 'RIFF' && s.slice(8, 12) === 'WEBP') return 'webp';
    if (s.slice(4, 8) === 'ftyp') return /avi[fs]/.test(s.slice(8, 48)) ? 'avif' : /hei[cxms]|hev[cx]|mif1|msf1/.test(s.slice(8, 48)) ? 'heic' : 'other';
    if (s.slice(0, 2) === 'BM') return 'bmp';
    return 'other';
  }
  function jpegTurned(b) {                                   // EXIF orientation other than «as stored»
    let p = 2;
    while (p + 4 <= b.length) {
      if (b[p] !== 0xFF) return false;
      const m = b[p + 1], size = (b[p + 2] << 8) | b[p + 3];
      if (m === 0xE1 && String.fromCharCode.apply(null, b.subarray(p + 4, p + 10)) === 'Exif\0\0') {
        const t = p + 10, le = b[t] === 0x49, u16 = o => le ? b[o] | (b[o + 1] << 8) : (b[o] << 8) | b[o + 1], u32 = o => le ? (u16(o) | (u16(o + 2) << 16)) >>> 0 : ((u16(o) << 16) | u16(o + 2)) >>> 0;
        const ifd = t + u32(t + 4), n = u16(ifd);
        for (let i = 0; i < n; i++) { const e = ifd + 2 + 12 * i; if (e + 12 > b.length) return false; if (u16(e) === 0x0112) return u16(e + 8) > 1; }
        return false;
      }
      if (m === 0xDA || m === 0xD9) return false;
      p += 2 + size;
    }
    return false;
  }
  function canvasBlob(source, w, h, lossy) {
    const k = Math.min(1, 4400 / Math.max(w, h));            // a very large photo is brought down to what OCR needs
    const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w * k)); c.height = Math.max(1, Math.round(h * k));
    const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.drawImage(source, 0, 0, c.width, c.height);
    return new Promise((res, rej) => c.toBlob(b => b ? res(b) : rej(new Error('canvas')), lossy ? 'image/jpeg' : 'image/png', 0.92));
  }
  async function viaBrowser(file, lossy) {
    if (typeof createImageBitmap === 'function') {
      try { const bmp = await createImageBitmap(file); const b = await canvasBlob(bmp, bmp.width, bmp.height, lossy); if (bmp.close) bmp.close(); return b; } catch (e) { /* try <img> */ }
    }
    const url = URL.createObjectURL(file);                   // <img> opens what createImageBitmap does not (SVG, ICO)
    try { const img = new Image(); img.src = url; await img.decode(); if (!img.naturalWidth) throw new Error('empty image'); return await canvasBlob(img, img.naturalWidth, img.naturalHeight, lossy); }
    finally { URL.revokeObjectURL(url); }
  }
  async function tiffPages(file, maxPages) {
    await loadLib('pako').catch(() => {});                     // Deflate-compressed TIFFs; the others decode without it
    await loadLib('utif');
    const buf = await file.arrayBuffer();
    const ifds = window.UTIF.decode(buf).filter(d => !(d.t254 && (d.t254[0] & 1)));   // reduced-resolution copies of a page are not pages
    const out = [];
    for (const ifd of ifds.slice(0, maxPages)) {
      window.UTIF.decodeImage(buf, ifd, ifds);
      if (!ifd.width || !ifd.height) continue;
      const rgba = window.UTIF.toRGBA8(ifd);
      const c = document.createElement('canvas'); c.width = ifd.width; c.height = ifd.height;
      c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(rgba.buffer, rgba.byteOffset, rgba.byteLength), ifd.width, ifd.height), 0, 0);
      out.push(await canvasBlob(c, ifd.width, ifd.height, false));
    }
    if (!out.length) throw new Error('no page in the TIFF');
    out.total = ifds.length;
    return out;
  }
  let heifP = null;
  async function heicPage(file) {
    await loadLib('heif');
    if (!heifP) heifP = Promise.resolve(window.libheif());
    const lib = await heifP;
    const imgs = new lib.HeifDecoder().decode(new Uint8Array(await file.arrayBuffer()));
    if (!imgs || !imgs.length) throw new Error('not a HEIF image');
    const im = imgs[0], w = im.get_width(), h = im.get_height(), id = new ImageData(w, h);
    await new Promise((res, rej) => im.display(id, d => d ? res() : rej(new Error('HEIF decoding failed'))));
    const c = document.createElement('canvas'); c.width = w; c.height = h; c.getContext('2d').putImageData(id, 0, 0);
    return canvasBlob(c, w, h, true);
  }
  /* file → its pages as images the OCR engine, the model and the PDF maker take */
  async function images(file, maxPages) {
    maxPages = maxPages || 4;
    const head = new Uint8Array(await file.slice(0, 131072).arrayBuffer());
    const kind = imageKind(head);
    if (kind === 'tiff') { try { return await tiffPages(file, maxPages); } catch (e) { console.warn('tiff decoder', e); } }
    if (kind === 'png' || (kind === 'jpeg' && !jpegTurned(head))) return [file];
    try { return [await viaBrowser(file, kind !== 'gif' && kind !== 'bmp' && kind !== 'tiff')]; } catch (e) { /* the browser cannot decode it */ }
    if (kind === 'heic' || kind === 'avif' || kind === 'other') {
      try { return [await heicPage(file)]; }
      catch (e) { if (kind === 'heic') throw new Error(AR() ? 'صورة HEIC ما اتفتحتش هنا: ' + (e && e.message || e) : 'This HEIC photo could not be opened here: ' + (e && e.message || e)); }
    }
    if (kind === 'jpeg') return [file];
    try {                                                    // JPEG 2000, PSD, PCX, PNM…: the machine behind the page may have a converter (not in the browser edition)
      const fd = new FormData(); fd.append('file', file, file.name || 'image');
      const r = await fetch('/api/images/png', { method: 'POST', body: fd, headers: { 'X-DB': '1' } });
      if (r.ok) return [await r.blob()];
    } catch (e) { /* no converter */ }
    throw new Error(AR() ? 'نوع الصورة ده المتصفح مش بيفتحه: حوّلها JPG أو PDF' : 'The browser cannot open this kind of image: convert it to JPG or PDF');
  }
  /* any page image as a JPEG on white (what a PDF page takes) */
  async function jpeg(blob) {
    if ((blob.type || '') === 'image/jpeg') return blob;
    return viaBrowser(blob, true);
  }
  /* an image file → the PDF the dossier takes: its pages decoded here, wrapped by the engine without re-compressing them. A plain
     JPEG is returned as it is (the engine wraps it itself); so is a file this page cannot open. */
  async function asPdf(file, isImage) {
    try {
      if (!file || !isImage) return file;
      const pages = await images(file, 200);
      if (pages.length === 1 && pages[0] === file && (file.type === 'image/jpeg' || /\.(jpe?g|jfif|jpe)$/i.test(file.name || ''))) return file;
      const fd = new FormData();
      for (let i = 0; i < pages.length; i++) fd.append('files', await jpeg(pages[i]), 'p' + (i + 1) + '.jpg');
      fd.append('title', file.name || '');
      const r = await fetch('/api/images/pdf', { method: 'POST', body: fd, headers: { 'X-DB': '1' } });
      if (!r.ok) return file;
      return new File([await r.blob()], (file.name || 'image').replace(/\.[A-Za-z0-9]{1,5}$/, '') + '.pdf', { type: 'application/pdf' });
    } catch (e) { console.warn('image → PDF', e); return file; }
  }

  /* file: File/Blob (PDF or image) → {text, pages, chars, pdfs?}. onProgress(status, 0..1, pageNo, pageCount).
     opts.pdfPages: also return, per page, a text-only PDF (invisible OCR text at the right places) that the engine lays over the
     original page to make the scan searchable without touching its image. */
  async function readFile(file, opts) {
    opts = opts || {};
    const maxPages = opts.maxPages || 4;
    const head = new Uint8Array(await file.slice(0, 5).arrayBuffer());
    const isPdf = /\.pdf$/i.test(file.name || '') || file.type === 'application/pdf' || String.fromCharCode(...head) === '%PDF-';      // by its bytes too: a Drive file may have no extension
    const pages = isPdf ? await pageImages(file, maxPages, opts.scale || 2.8, 'png') : await images(file, maxPages);
    const w = await worker((status, p) => opts.onProgress && opts.onProgress(status, p));
    await w.setParameters({ tessedit_pageseg_mode: '6', preserve_interword_spaces: '1' });
    const texts = [], pdfs = [];
    for (let i = 0; i < pages.length; i++) {
      if (opts.onProgress) opts.onProgress('recognizing text', 0, i + 1, pages.length);
      const { data } = await w.recognize(pages[i], opts.pdfPages ? { pdfTitle: file.name || 'scan', pdfTextOnly: true } : {}, opts.pdfPages ? { text: true, pdf: true } : { text: true });
      texts.push(data.text || '');
      if (opts.pdfPages) pdfs.push(data.pdf ? new Uint8Array(data.pdf) : null);
      if (opts.onProgress) opts.onProgress('recognizing text', 1, i + 1, pages.length);
    }
    const text = texts.join('\n\f\n');
    const out = { text, pages: pages.length, chars: text.replace(/\s/g, '').length };
    if (opts.pdfPages) out.pdfs = pdfs;
    return out;
  }

  /* how many pages a PDF has (to OCR all of them when making a readable copy) */
  async function pageCount(file) {
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
    return doc.numPages;
  }

  window.DBOCR = { available, readFile, pageImages, pageCount, pdfjs, images, jpeg, asPdf };
})();
