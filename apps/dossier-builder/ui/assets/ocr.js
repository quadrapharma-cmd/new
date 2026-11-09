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

  /* file: File/Blob (PDF or image) → {text, pages, chars, pdfs?}. onProgress(status, 0..1, pageNo, pageCount).
     opts.pdfPages: also return, per page, a text-only PDF (invisible OCR text at the right places) that the engine lays over the
     original page to make the scan searchable without touching its image. */
  async function readFile(file, opts) {
    opts = opts || {};
    const maxPages = opts.maxPages || 4;
    const isPdf = /\.pdf$/i.test(file.name || '') || file.type === 'application/pdf';
    const images = isPdf ? await pageImages(file, maxPages, opts.scale || 2.8, 'png') : [file];
    const w = await worker((status, p) => opts.onProgress && opts.onProgress(status, p));
    await w.setParameters({ tessedit_pageseg_mode: '6', preserve_interword_spaces: '1' });
    const texts = [], pdfs = [];
    for (let i = 0; i < images.length; i++) {
      if (opts.onProgress) opts.onProgress('recognizing text', 0, i + 1, images.length);
      const { data } = await w.recognize(images[i], opts.pdfPages ? { pdfTitle: file.name || 'scan', pdfTextOnly: true } : {}, opts.pdfPages ? { text: true, pdf: true } : { text: true });
      texts.push(data.text || '');
      if (opts.pdfPages) pdfs.push(data.pdf ? new Uint8Array(data.pdf) : null);
      if (opts.onProgress) opts.onProgress('recognizing text', 1, i + 1, images.length);
    }
    const text = texts.join('\n\f\n');
    const out = { text, pages: images.length, chars: text.replace(/\s/g, '').length };
    if (opts.pdfPages) out.pdfs = pdfs;
    return out;
  }

  /* how many pages a PDF has (to OCR all of them when making a readable copy) */
  async function pageCount(file) {
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()) }).promise;
    return doc.numPages;
  }

  window.DBOCR = { available, readFile, pageImages, pageCount, pdfjs };
})();
