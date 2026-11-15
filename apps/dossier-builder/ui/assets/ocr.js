/* Reading scans in the browser edition — the same reading as the desktop and company editions (engine/dossier_engine/pdfcraft.py
   ocr() and paddle_rec.py), done in the page (the owner, 13/11/2026: «all the improvements must work in the browser»):
     1. each page drawn at 300 dpi (pdf.js; an image file as it is, a TIFF page by page) and read by Tesseract 5 (tesseract.js, in
        WebAssembly) with the accurate Arabic model and English, as the desktop's Tesseract reads it (automatic page layout);
     2. each run of words it read with low confidence (< 70) cut out of the page — three margins, from the 300 and the 400 dpi
        drawing: six cuts — and read again by PaddleOCR's Arabic model (onnxruntime-web); the reading most cuts agree on, a date or
        a «number/year» first, is kept where it is sure (≥ 0.8): the Arabic-Indic numbers and dates Tesseract misreads;
     3. a page still hard to read (more than 3 % of its words doubtful) read again turned upright and straightened, and the better
        of the two readings kept. A page far harder (more than 25 % doubtful: most likely turned) is straightened before step 2, and
        the second reader reads the upright page — the desktop reads such a page again too, but its second reader does not.
   Nothing leaves the browser. The files (assets/ocr/, web/ocr_assets.py) are fetched the first time a scan is read and kept on
   the device. Where claude.ai's model is there (the sample capability), the model reads a scan from its page pictures
   (pageImages) and this reading only writes the invisible text layer, quickly: `quick` reads the pages two or three at a time with
   Tesseract alone, and turns a page only when it is most likely sideways. window.DBOCR = {
     available(), sha256(blob) → hex,
     pageImages(file, {max = 3, pick: [1, 2, -1], budget, quality = 0.85}) → [{blob: JPEG, page, pages, part}] — pages as pictures for the model,
     read(file, {maxPages = 12, quick = false, onProgress({stage: load|read|check|straighten|done, page, pages, part})}) →
       {pages: [{page, text, words: [{text, conf, box: [x, y, w, h] in points from the top left}], read, rotated?}],
        rep: {words, pages, quality: {page: {words, low, mean, numbers, read, second?}}, second_reader, weak, models}, tag} } */
(function () {
  'use strict';
  const BASE = () => window.DB_OCR_BASE || '';
  const TAG = () => window.DB_OCR_TAG || 'dev';
  const LANGS = ['ara', 'eng'];
  const DPI = 300, DPI2 = 400, PROBE = 150, LOW = 70, SURE = 0.8, WEAK = 3.0, HARD = 25;
  const HEIGHT = 48, MIN_WIDTH = 320, PADS = [0.15, 0.25, 0.35], MAX_PIXELS = 30e6;
  const abs = u => new URL(u, document.baseURI).href;
  const yieldNow = () => new Promise(r => setTimeout(r, 0));

  function available() { return !!BASE() && typeof WebAssembly === 'object' && typeof Worker === 'function'; }

  async function sha256(blob) {
    const d = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
    return [...new Uint8Array(d)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /* ---- the files: scripts by tag; the runtime and the model as gzip in base64 text, kept on the device (IndexedDB «db-ocr») */
  const scripts = {};
  function script(rel) {
    const url = abs(BASE() + rel);
    return scripts[url] || (scripts[url] = new Promise((res, rej) => {
      const s = document.createElement('script'); s.src = url;
      s.onload = () => res(); s.onerror = () => { delete scripts[url]; rej(new Error('could not load ' + rel)); };
      document.head.appendChild(s);
    }));
  }
  let dbp = null;
  const idb = () => dbp || (dbp = new Promise(res => {
    try { const q = indexedDB.open('db-ocr', 1); q.onupgradeneeded = () => { try { q.result.createObjectStore('files'); } catch (e) {} };
      q.onsuccess = () => res(q.result); q.onerror = q.onblocked = () => res(null); } catch (e) { res(null); }
  }));
  const idbDo = (mode, f) => idb().then(db => db ? new Promise(res => {
    try { const q = f(db.transaction('files', mode).objectStore('files')); q.onsuccess = () => res(q.result); q.onerror = () => res(undefined); }
    catch (e) { res(undefined); } }) : undefined);
  async function tidy() {                                         // files of an older build go: the device keeps one copy
    const keys = await idbDo('readonly', s => s.getAllKeys()) || [];
    for (const k of keys) if (typeof k === 'string' && !k.endsWith('@' + TAG())) await idbDo('readwrite', s => s.delete(k));
  }
  function fromB64(text) { const bin = atob(text.replace(/\s+/g, '')), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; }
  async function packed(rel, tell) {
    const key = rel + '@' + TAG();
    const hit = await idbDo('readonly', s => s.get(key));
    if (hit) return new Uint8Array(hit);
    if (typeof DecompressionStream !== 'function') throw new Error('this browser cannot unpack ' + rel);
    if (tell) tell();
    const r = await fetch(abs(BASE() + rel + '.gz.b64.txt'));
    if (!r.ok) throw new Error(rel + ': HTTP ' + r.status);
    const raw = new Uint8Array(await new Response(new Blob([fromB64(await r.text())]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
    idbDo('readwrite', s => s.put(raw.buffer.slice(0), key)).then(tidy, () => {});
    return raw;
  }

  /* ---- pages: a PDF's drawn by pdf.js at any dpi and turn; an image's as they are (a TIFF page by page) */
  let pdfP = null;
  const pdfjs = () => pdfP || (pdfP = import(abs(BASE() + 'pdfjs/pdf.min.mjs')).then(m => { m.GlobalWorkerOptions.workerSrc = abs(BASE() + 'pdfjs/pdf.worker.min.mjs'); return m; }, e => { pdfP = null; throw e; }));
  const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h));
    c.getContext('2d', { willReadFrequently: true }); return c; };                     // the pixels are read back (Tesseract, the cuts): kept in memory
  function turned(src, rot) {                                     // the picture turned clockwise by 0/90/180/270 degrees
    if (!rot) return src;
    const side = rot % 180 !== 0, c = canvas(side ? src.height : src.width, side ? src.width : src.height), g = c.getContext('2d');
    g.translate(c.width / 2, c.height / 2); g.rotate(rot * Math.PI / 180); g.drawImage(src, -src.width / 2, -src.height / 2);
    c.dpi = src.dpi;
    return c;
  }
  function scaled(src, k) {
    const c = canvas(src.width * k, src.height * k), g = c.getContext('2d');
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(src, 0, 0, c.width, c.height);
    return c;
  }
  function white(c) {                                             // a transparent background read as paper, not as black
    const w = canvas(c.width, c.height), g = w.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, w.width, w.height); g.drawImage(c, 0, 0); return w;
  }
  const isPdf = f => /\.pdf$/i.test(f.name || '') || f.type === 'application/pdf';
  const isTiff = f => /\.tiff?$/i.test(f.name || '') || f.type === 'image/tiff';
  async function images(file) {                                   // an image file → its pages as canvases, about 2000–4200 pixels long
    const fit = c => { const L = Math.max(c.width, c.height); return L < 2000 ? scaled(c, Math.min(3, 2000 / L)) : L > 4200 ? scaled(c, 4200 / L) : c; };
    if (isTiff(file)) {
      await script('img/pako_inflate.min.js'); await script('img/UTIF.js');
      const buf = await file.arrayBuffer(), ifds = window.UTIF.decode(buf), out = [];
      for (const ifd of ifds) {
        window.UTIF.decodeImage(buf, ifd, ifds);
        if (!ifd.width || !ifd.height) continue;
        const rgba = window.UTIF.toRGBA8(ifd), c = canvas(ifd.width, ifd.height);
        c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(rgba.buffer, rgba.byteOffset, ifd.width * ifd.height * 4), ifd.width, ifd.height), 0, 0);
        out.push(fit(white(c)));
      }
      return out;
    }
    let bmp;
    try { bmp = await createImageBitmap(file); } catch (e) { throw new Error('this browser cannot open this kind of image (' + (file.type || file.name) + ')'); }
    const c = canvas(bmp.width, bmp.height), g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height); g.drawImage(bmp, 0, 0);
    return [fit(c)];
  }
  async function open(file, maxPages) {
    if (!isPdf(file)) {
      const pics = await images(file);
      return { count: Math.min(pics.length, maxPages || pics.length), close() {},
        draw: async (i, dpi, rot) => { const c = dpi === DPI ? pics[i - 1] : scaled(pics[i - 1], dpi / DPI); c.dpi = dpi; return turned(c, rot || 0); } };
    }
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()), isEvalSupported: false }).promise;
    return { count: Math.min(doc.numPages, maxPages || doc.numPages), close() { try { doc.destroy(); } catch (e) {} },
      draw: async (i, dpi, rot) => {
        const p = await doc.getPage(i), turn = (p.rotate + (rot || 0)) % 360, v1 = p.getViewport({ scale: 1, rotation: turn });
        const k = Math.min(dpi / 72, Math.sqrt(MAX_PIXELS / Math.max(1, v1.width * v1.height)));
        const vp = p.getViewport({ scale: k, rotation: turn });
        const c = canvas(vp.width, vp.height), g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
        await p.render({ canvasContext: g, viewport: vp }).promise;
        p.cleanup();
        c.dpi = k * 72;
        return c;
      } };
  }

  /* ---- Tesseract 5 (tesseract.js 7): one worker, or two on a processor with cores to spare; read as the desktop reads */
  let tessP = null, tessTell = null;
  const simd = () => { try { return WebAssembly.validate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123, 3, 2, 1, 0, 10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11])); } catch (e) { return false; } };
  function tesseract() {
    if (!tessP) tessP = (async () => {
      await script('tess/tesseract.min.js');
      const T = window.Tesseract, base = abs(BASE() + 'tess/');
      const opts = { workerPath: base + 'worker.boot.js', corePath: base + (simd() ? 'tesseract-core-simd-lstm.wasm.js' : 'tesseract-core-lstm.wasm.js'),
        langPath: base.replace(/\/$/, ''), gzip: true, workerBlobURL: false, cachePath: 'dbocr-' + TAG(),
        logger: m => { if (tessTell && m && /loading|initializ/i.test(m.status || '')) tessTell(m.progress || 0); } };
      const n = Math.min(3, Math.max(1, Math.floor((navigator.hardwareConcurrency || 2) / 2))), sched = T.createScheduler();   // a page each, at once
      sched.size = n;
      for (let i = 0; i < n; i++) {
        const w = await T.createWorker(LANGS, 1, opts);
        await w.setParameters({ tessedit_pageseg_mode: '3', user_defined_dpi: String(DPI) });   // automatic page layout, as the tesseract command
        sched.addWorker(w);
      }
      return sched;
    })().catch(e => { tessP = null; throw e; });
    return tessP;
  }
  /* Tesseract's TSV → the page's words in reading order: {text, conf, px: [x, y, w, h], line} */
  function words(tsv) {
    const out = [];
    for (const row of (tsv || '').split('\n')) {
      const f = row.split('\t');
      if (f.length < 12 || f[0] !== '5') continue;
      const text = f.slice(11).join('\t').trim();
      if (!text) continue;
      out.push({ text, conf: Math.max(0, parseFloat(f[10]) || 0), px: [+f[6], +f[7], +f[8], +f[9]], line: f[2] + '/' + f[3] + '/' + f[4] });
    }
    return out;
  }
  async function tess(pic, deskew) {                              // → {ws, angle}: straightened, Tesseract turns the picture by angle first
    const s = await tesseract();
    const { data } = await s.addJob('recognize', pic, deskew ? { rotateAuto: true } : {}, { text: false, tsv: true });
    return { ws: words(data.tsv), angle: deskew ? (data.rotateRadians || 0) : 0 };
  }
  function deskewed(src, angle) {                                 // the picture as Tesseract read it: turned about its centre, same size
    if (!angle) return src;
    const c = canvas(src.width, src.height), g = c.getContext('2d');
    g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
    g.translate(c.width / 2, c.height / 2); g.rotate(angle); g.translate(-c.width / 2, -c.height / 2); g.drawImage(src, 0, 0);
    c.dpi = src.dpi;
    return c;
  }
  const round1 = x => Math.round(x * 10) / 10;
  function quality(ws) {                                          // pdfcraft._quality, for one page
    const low = ws.filter(w => w.conf < LOW);
    return { words: ws.length, low: ws.length ? round1(100 * low.length / ws.length) : 0, mean: round1(ws.length ? ws.reduce((a, w) => a + w.conf, 0) / ws.length : 0),
             numbers: low.map(w => w.text).filter(t => /\p{Nd}/u.test(t)).slice(0, 20) };
  }
  const weak = q => q.words === 0 || q.low > WEAK;
  const good = q => q.words - Math.round(q.words * q.low / 100);
  /* Tesseract also reads text lying on its side (it takes it for vertical writing), almost as well as upright text: the turn that
     is upright is the one whose words lie flat — wider than tall (words of three characters or more) */
  function flat(ws) {
    const long = ws.filter(w => [...(w.text || '')].length >= 3), box = w => w.px || w.box;
    return long.length ? long.filter(w => box(w)[2] >= box(w)[3]).length / long.length : 0;
  }
  const upright = q => good(q) * q.flat;
  function better(nu, old) {                                      // pdfcraft._better
    if (!nu || !nu.words) return false;
    if (!old.words) return true;
    if (Math.abs(nu.low - old.low) > 0.5) return nu.low < old.low;
    return nu.mean > old.mean + 1.0;
  }

  /* ---- the second reader: PaddleOCR's Arabic model (PP-OCRv5 mobile) in onnxruntime-web — paddle_rec.py, line by line */
  let padP = null;
  function paddle(tell) {
    if (!padP) padP = (async () => {
      const ort = await import(abs(BASE() + 'ort/ort.wasm.bundle.min.mjs'));
      ort.env.wasm.numThreads = 1; ort.env.wasm.proxy = false;
      ort.env.wasm.wasmBinary = await packed('ort/ort-wasm-simd-threaded.wasm', tell);
      const model = await packed('paddle/arabic_PP-OCRv5_rec_mobile.onnx', tell);
      const sess = await ort.InferenceSession.create(model, { executionProviders: ['wasm'] });
      const chars = await (await fetch(abs(BASE() + 'paddle/characters.json'))).json();
      return { ort, sess, chars: ['\u0000', ...chars, ' '] };                  // index 0: the blank; the last: the space
    })().catch(e => { padP = null; throw e; });
    return padP;
  }
  const rtl = c => { const o = c.codePointAt(0); return (o >= 0x0590 && o <= 0x08FF) || (o >= 0xFB1D && o <= 0xFDFF) || (o >= 0xFE70 && o <= 0xFEFF); };
  const ltr = c => /\p{Nd}/u.test(c) || /[a-z]/.test(c.toLowerCase()) || '%°µ'.includes(c);
  function toLogical(s) {                                         // drawn right to left, read left to right: back to reading order
    const a = [...s];
    if (!a.some(rtl)) return s;
    const r = a.reverse(), out = [];
    for (let i = 0; i < r.length;) {
      if (ltr(r[i])) {
        let k = i;
        while (k < r.length && (ltr(r[k]) || ('/.,:-+ '.includes(r[k]) && k + 1 < r.length && ltr(r[k + 1])))) k++;
        out.push(r.slice(i, k).reverse().join('')); i = k;
      } else { out.push(r[i]); i++; }
    }
    return out.join('');
  }
  function pyRound(x) { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : (f % 2 === 0 ? f : f + 1); }
  function coeffs(inSize, outSize) {                              // Pillow's bilinear resampling weights (precompute_coeffs)
    const scale = inSize / outSize, fs = Math.max(scale, 1), support = fs, ks = Math.ceil(support) * 2 + 1;
    const lo = new Int32Array(outSize), n = new Int32Array(outSize), k = new Float64Array(outSize * ks);
    for (let xx = 0; xx < outSize; xx++) {
      const center = (xx + 0.5) * scale;
      let xmin = Math.trunc(center - support + 0.5); if (xmin < 0) xmin = 0;
      let xmax = Math.trunc(center + support + 0.5); if (xmax > inSize) xmax = inSize; xmax -= xmin;
      let ww = 0;
      for (let x = 0; x < xmax; x++) { const t = Math.abs((x + xmin - center + 0.5) / fs), w = t < 1 ? 1 - t : 0; k[xx * ks + x] = w; ww += w; }
      if (ww) for (let x = 0; x < xmax; x++) k[xx * ks + x] /= ww;
      lo[xx] = xmin; n[xx] = xmax;
    }
    return { lo, n, k, ks };
  }
  const clip8 = v => v <= 0 ? 0 : v >= 255 ? 255 : Math.floor(v + 0.5);
  function resize(rgb, w0, h0, w1, h1) {                          // RGB bytes w0×h0 → w1×h1, as PIL's Image.resize(…, BILINEAR)
    let src = rgb, w = w0;
    if (w1 !== w0) {
      const c = coeffs(w0, w1), out = new Uint8Array(w1 * h0 * 3);
      for (let y = 0; y < h0; y++) for (let x = 0; x < w1; x++) {
        let r = 0, g = 0, b = 0;
        for (let j = 0; j < c.n[x]; j++) { const kk = c.k[x * c.ks + j], o = (y * w0 + c.lo[x] + j) * 3; r += src[o] * kk; g += src[o + 1] * kk; b += src[o + 2] * kk; }
        const o = (y * w1 + x) * 3; out[o] = clip8(r); out[o + 1] = clip8(g); out[o + 2] = clip8(b);
      }
      src = out; w = w1;
    }
    if (h1 !== h0) {
      const c = coeffs(h0, h1), out = new Uint8Array(w * h1 * 3);
      for (let y = 0; y < h1; y++) for (let x = 0; x < w; x++) {
        let r = 0, g = 0, b = 0;
        for (let j = 0; j < c.n[y]; j++) { const kk = c.k[y * c.ks + j], o = ((c.lo[y] + j) * w + x) * 3; r += src[o] * kk; g += src[o + 1] * kk; b += src[o + 2] * kk; }
        const o = (y * w + x) * 3; out[o] = clip8(r); out[o + 1] = clip8(g); out[o + 2] = clip8(b);
      }
      src = out;
    }
    return src;
  }
  async function readCrop(pd, rgb, cw, ch) {                      // paddle_rec.read: one cut → [text in reading order, confidence 0–1]
    const { ort, sess, chars } = pd;
    const w = Math.max(1, pyRound(cw * HEIGHT / Math.max(1, ch))), W = Math.max(w, MIN_WIDTH);
    const px = resize(rgb, cw, ch, w, HEIGHT), x = new Float32Array(3 * HEIGHT * W), plane = HEIGHT * W;
    for (let y = 0; y < HEIGHT; y++) for (let i = 0; i < w; i++) {
      const s = (y * w + i) * 3, o = y * W + i;
      x[o] = (px[s + 2] / 255 - 0.5) / 0.5; x[plane + o] = (px[s + 1] / 255 - 0.5) / 0.5; x[2 * plane + o] = (px[s] / 255 - 0.5) / 0.5;   // BGR
    }
    const res = await sess.run({ [sess.inputNames[0]]: new ort.Tensor('float32', x, [1, 3, HEIGHT, W]) });
    const out = res[sess.outputNames[0]], T = out.dims[1], C = out.dims[2], v = out.data, text = [], conf = [];
    let prev = 0;
    for (let t = 0; t < T; t++) {
      let best = 0, p = v[t * C];
      for (let j = 1; j < C; j++) if (v[t * C + j] > p) { p = v[t * C + j]; best = j; }
      if (best && best !== prev && best < chars.length) { text.push(chars[best]); conf.push(p); }
      prev = best;
    }
    return [toLogical(text.join('').trim()), conf.length ? conf.reduce((a, b) => a + b, 0) / conf.length : 0];
  }
  function spans(ws, low) {                                       // paddle_rec.spans, on the page's words in points
    const out = []; let cur = null;
    ws.forEach((w, i0) => {
      const i = i0 + 1, [x, y, bw, bh] = w.box || [0, 0, 0, 0];
      if ((w.conf || 0) >= low || !(w.text || '').trim() || bw <= 0 || bh <= 0) { cur = null; return; }
      const box = [x, y, x + bw, y + bh];
      if (cur && i === cur[1] + 1) {
        const b = cur[2], over = Math.min(b[3], box[3]) - Math.max(b[1], box[1]), gap = Math.max(box[0] - b[2], b[0] - box[2], 0);
        if (over > 0.5 * Math.min(b[3] - b[1], box[3] - box[1]) && gap < 2.0 * Math.max(b[3] - b[1], box[3] - box[1])) {
          cur[1] = i; cur[2] = [Math.min(b[0], box[0]), Math.min(b[1], box[1]), Math.max(b[2], box[2]), Math.max(b[3], box[3])]; return;
        }
      }
      cur = [i, i, box]; out.push(cur);
    });
    return out;
  }
  const SHAPES = [/^\p{Nd}{1,2}[\/.\-]\p{Nd}{1,2}[\/.\-](\p{Nd}{2}|\p{Nd}{4})$/u, /^\p{Nd}+\/\p{Nd}{4}$/u];
  function vote(readings, sure) {                                 // paddle_rec.vote
    sure = sure == null ? SURE : sure;
    const shaped = readings.filter(([t, c]) => t && c >= sure && SHAPES.some(m => m.test(t)));
    const tally = new Map();
    for (const [t, c] of (shaped.length ? shaped : readings)) if (t) { const v = tally.get(t) || [0, 0]; tally.set(t, [v[0] + 1, v[1] + c]); }
    let best = null;
    for (const [t, [n, c]] of tally) if (!best || n > best[1] || (n === best[1] && c / n > best[2])) best = [t, n, c / n];
    return best ? [best[0], best[2]] : ['', 0];
  }
  function cut(pic, l, t, r, b) {                                 // a part of a drawn page as RGB bytes
    const w = r - l, h = b - t, d = pic.getContext('2d').getImageData(l, t, w, h).data, rgb = new Uint8Array(w * h * 3);
    for (let i = 0, j = 0; i < d.length; i += 4, j += 3) { rgb[j] = d[i]; rgb[j + 1] = d[i + 1]; rgb[j + 2] = d[i + 2]; }
    return rgb;
  }
  async function secondReading(pd, pics, ws) {                    // paddle_rec.second_reading: pics = [[canvas, dpi], …]
    const fixes = [], seen = [];
    for (const [first, last, [x0, y0, x1, y1]] of spans(ws, LOW)) {
      const h = y1 - y0, readings = [];
      for (const [pic, dpi] of pics) {
        const k = dpi / 72;
        for (const m of PADS) {
          const l = Math.max(0, Math.trunc((x0 - m * h) * k)), t = Math.max(0, Math.trunc((y0 - m * h) * k));
          const r = Math.min(pic.width, Math.trunc((x1 + m * h) * k)), b = Math.min(pic.height, Math.trunc((y1 + m * h) * k));
          if (r - l >= 4 && b - t >= 4) readings.push(await readCrop(pd, cut(pic, l, t, r, b), r - l, b - t));
        }
        await yieldNow();
      }
      const [text, conf] = vote(readings, SURE);
      const old = ws.slice(first - 1, last).map(w => w.text || '').join(' ');
      const agree = readings.filter(([t]) => t === text).length;
      seen.push({ tesseract: old, paddle: text, confidence: Math.round(conf * 1000) / 1000, agree: agree + '/' + readings.length });
      if (conf >= SURE && text && text !== old) {
        fixes.push({ word: first, text, box: [x0, y0, Math.round((x1 - x0) * 100) / 100, Math.round((y1 - y0) * 100) / 100] });   // the run's place
        for (let i = first + 1; i <= last; i++) fixes.push({ word: i, text: '' });
      }
    }
    return [fixes, seen];
  }

  /* ---- one file */
  const inPoints = (ws, dpi) => ws.map(w => ({ text: w.text, conf: w.conf, line: w.line, box: w.px.map(v => Math.round(v * 7200 / dpi) / 100) }));
  /* A page's text in reading order, line by line as Tesseract found the lines. Within a line the words go by their place on the page,
     as the desktop's text comes from the words written on the page: a line with Arabic words reads right to left, a run of numbers or
     Latin words inside it left to right («التاريخ: ١٥/٠٣/٢٠٢٥», never the date first when Tesseract took the line for left-to-right). */
  const arabicLetter = /(?=\p{Script=Arabic})\p{L}/u;
  function inReadingOrder(ws) {                                   // one line's words
    const mid = w => w.box[0] + w.box[2] / 2;
    if (!ws.some(w => arabicLetter.test(w.text))) return ws.slice().sort((a, b) => mid(a) - mid(b));
    const rtl = ws.slice().sort((a, b) => mid(b) - mid(a)), out = [];
    for (let i = 0; i < rtl.length;) {
      if (arabicLetter.test(rtl[i].text)) { out.push(rtl[i]); i++; continue; }
      let k = i; while (k < rtl.length && !arabicLetter.test(rtl[k].text)) k++;
      out.push(...rtl.slice(i, k).reverse()); i = k;
    }
    return out;
  }
  function lines(ws) {                                            // the page's lines as Tesseract found them, each in reading order
    const out = [], at = new Map();
    for (const w of ws) { if (!w.text) continue; if (!at.has(w.line)) { at.set(w.line, out.length); out.push([]); } out[at.get(w.line)].push(w); }
    return out.map(inReadingOrder);
  }
  const pageText = ws => lines(ws).map(l => l.map(w => w.text).join(' ')).join('\n');
  let queue = Promise.resolve();
  function read(file, opts) {                                     // one file at a time: two readings at once only share the processor
    const run = queue.then(() => readNow(file, opts || {}));
    queue = run.catch(() => {});
    return run;
  }
  async function check(pg, doc, pd, tell) {                       // 2) the runs of one reading Tesseract is unsure of, read again
    if (!pd || !pg.q.words || !pg.words.some(w => w.conf < LOW)) return;
    tell('check', pg.page, doc.count, (pg.page - 0.5) / doc.count);
    try {
      const one = deskewed(pg.pic, pg.angle), two = deskewed(await doc.draw(pg.page, DPI2, pg.rot), pg.angle);
      const [found, seen] = await secondReading(pd, [[one, one.dpi || DPI], [two, two.dpi || DPI2]], pg.words);
      const settled = new Set(found.map(f => f.word));
      const still = pg.words.map((w, k) => [w, k + 1]).filter(([w, k]) => w.conf < LOW && !settled.has(k));
      pg.fixes = found;
      Object.assign(pg.q, { low: round1(100 * still.length / pg.words.length), numbers: still.map(([w]) => w.text).filter(t => /\p{Nd}/u.test(t)).slice(0, 20),
        second: { read: seen.length, changed: seen.filter(x => x.paddle && x.paddle !== x.tesseract && x.confidence >= SURE).map(x => ({ was: x.tesseract, now: x.paddle })) } });
    } catch (e) { pg.q.second = { error: String(e && e.message || e).slice(0, 200) }; }
  }
  async function readNow(file, opts) {
    const tell = (stage, page, pages, part) => { try { if (opts.onProgress) opts.onProgress({ stage, page, pages, part }); } catch (e) {} };
    const quick = !!opts.quick;
    tell('load', 0, 0, 0);
    tessTell = p => tell('load', 0, 0, p);
    let sched;
    try { sched = await tesseract(); } finally { tessTell = null; }
    let pd = null;
    if (!quick) { try { pd = await paddle(() => tell('load', 0, 0, 0.5)); } catch (e) { console.warn('second reader', e); } }
    const doc = await open(file, opts.maxPages || 12);
    try {
      const pages = new Array(doc.count);
      let next = 1, done = 0;
      const one = async i => {                                    // 1) read as scanned
        const pic = await doc.draw(i, DPI, 0), { ws } = await tess(pic, false);
        const pg = { page: i, pic, rot: 0, angle: 0, words: inPoints(ws, pic.dpi || DPI), fixes: [] };
        pg.q = Object.assign(quality(pg.words), { read: 'as scanned' });
        if (pg.q.low <= HARD) await check(pg, doc, pd, tell);       // a page this hard is most likely turned: straightened first
        if (!weak(pg.q) || (quick && pg.q.low <= HARD)) pg.pic = null;
        pages[i - 1] = pg;
        tell('read', ++done, doc.count, done / doc.count);
        await yieldNow();
      };
      const lanes = quick ? Math.max(1, sched.size || 1) : 1;     // quick: as many pages at once as Tesseract has workers
      tell('read', 0, doc.count, 0);
      await Promise.all(Array.from({ length: Math.min(lanes, doc.count) }, async () => { while (next <= doc.count) await one(next++); }));
      for (const pg of pages) {                                   // 3) the pages still weak, turned upright and straightened
        if (!weak(pg.q) || (quick && pg.q.low <= HARD)) continue; // quick: only a page most likely turned
        tell('straighten', pg.page, doc.count, pg.page / doc.count);
        let best = null;
        for (const rot of [90, 270, 180]) {                       // which way up: a quick reading of each turn at 150 dpi
          const pic = await doc.draw(pg.page, PROBE, rot), { ws } = await tess(pic, false), qq = Object.assign(quality(ws), { flat: flat(ws) });
          if (qq.words && (!best || upright(qq) > upright(best.q) || (upright(qq) === upright(best.q) && qq.mean > best.q.mean + 1))) best = { rot, q: qq };
        }
        const rot = best && upright(best.q) > 1.5 * upright(Object.assign({}, pg.q, { flat: flat(pg.words) })) + 3 ? best.rot : 0;
        const pic = rot ? await doc.draw(pg.page, DPI, rot) : pg.pic, { ws, angle } = await tess(pic, true);
        const st = { page: pg.page, pic, rot, angle, words: inPoints(ws, pic.dpi || DPI), fixes: [] };
        st.q = Object.assign(quality(st.words), { read: 'straightened' });
        if (better(st.q, pg.q)) { await check(st, doc, pd, tell); Object.assign(pg, st); }
        else if (pg.q.low > HARD) await check(pg, doc, pd, tell);  // not better turned: the second reader on the page as scanned, as the desktop
        pg.pic = null;
      }
      for (const pg of pages) {                                   // the second reader's words written in
        for (const f of pg.fixes) Object.assign(pg.words[f.word - 1], f.box ? { text: f.text, box: f.box } : { text: f.text });
        pg.words = lines(pg.words).flatMap((l, i) => l.map(w => Object.assign(w, { line: i })));       // in reading order, numbered by line
        pg.text = pageText(pg.words);
      }
      tell('done', doc.count, doc.count, 1);
      const quality_ = {};
      for (const pg of pages) quality_[pg.page] = pg.q;
      return { pages: pages.map(pg => Object.assign({ page: pg.page, text: pg.text, words: pg.words, read: pg.q.read }, pg.rot ? { rotated: pg.rot } : {}, pg.angle ? { deskew: pg.angle } : {})),
        tag: LANGS.join('+') + '+best' + (pd ? '+paddle' : '') + (quick ? '+quick' : ''),
        rep: { words: pages.reduce((a, pg) => a + pg.q.words, 0), pages: pages.map(pg => ({ page: pg.page, words: pg.q.words })), quality: quality_,
               second_reader: pages.reduce((a, pg) => a + pg.fixes.length, 0), weak: pages.filter(pg => weak(pg.q)).map(pg => pg.page), models: 'best 4.1.0' } };
    } finally { doc.close(); }
  }

  /* the first pages of a scan or an image as JPEG pictures for claude.ai's model (boot.js DBAI.extract). The platform brings every
     picture down to about 1.2 megapixels, so a whole A4 page would reach the model at about 110 dpi — small Arabic print in a licence's
     tables is lost at that. Each page goes as two halves, top and bottom, overlapping by a tenth so no line is cut: about 160 dpi each.
     pdf.js and the image decoders only — no reader to load. → [{blob, page, pages, part: 'top' | 'bottom'}] */
  async function pageImages(file, o) {
    o = o || {};
    const max = o.max || 3, budget = o.budget || 2 * max, quality = o.quality || 0.85, MP = 1.2e6, OVER = 0.1;
    const which = n => [...new Set((o.pick || Array.from({ length: max }, (_, i) => i + 1)).map(k => k < 0 ? n + 1 + k : k).filter(k => k >= 1 && k <= n))].sort((a, b) => a - b);   // pick: page numbers, -1 the last
    const jpeg = c => new Promise((res, rej) => c.toBlob(b => b ? res(b) : rej(new Error('the page could not be drawn')), 'image/jpeg', quality));
    const halves = async (src, page, pages, out) => {
      const h = Math.round(src.height * (0.5 + OVER / 2));
      for (const [part, y] of [['top', 0], ['bottom', src.height - h]]) {
        if (out.length >= budget) return;
        const k = Math.min(1, Math.sqrt(MP / (src.width * h)));
        const c = document.createElement('canvas'); c.width = Math.round(src.width * k); c.height = Math.round(h * k);
        const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
        g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
        g.drawImage(src, 0, y, src.width, h, 0, 0, c.width, c.height);
        out.push({ blob: await jpeg(c), page, pages, part });
      }
    };
    const out = [];
    if (!isPdf(file)) {
      const pics = await images(file);
      for (const k of which(pics.length)) { if (out.length >= budget) break; await halves(pics[k - 1], k, pics.length, out); }
      return out;
    }
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()), isEvalSupported: false }).promise;
    try {
      for (const i of which(doc.numPages)) {
        if (out.length >= budget) break;
        const p = await doc.getPage(i), v1 = p.getViewport({ scale: 1 });
        const vp = p.getViewport({ scale: Math.min(4, Math.sqrt(2.2 * MP / (v1.width * v1.height))) });   // enough pixels for two halves
        const c = document.createElement('canvas'); c.width = Math.round(vp.width); c.height = Math.round(vp.height);
        const g = c.getContext('2d'); g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
        await p.render({ canvasContext: g, viewport: vp }).promise;
        p.cleanup();
        await halves(c, i, doc.numPages, out);
      }
      return out;
    } finally { try { doc.destroy(); } catch (e) {} }
  }

  /* every page of a PDF as small numbered pictures, several to a sheet: what claude.ai's model looks at to find where the separate
     documents of a combined file start (boot.js DBAI.bundle) — titles, letterheads and «page 1 of …» read at that size. At most
     `budget` sheets (the model takes that many pictures a call); 4 to 12 pages a sheet. → [{blob, from, to, pages}] */
  async function contactSheets(file, o) {
    o = o || {};
    const budget = Math.max(1, o.budget || 8), TW = 400, TH = 566, PAD = 8, HEAD = 30;
    const lib = await pdfjs();
    const doc = await lib.getDocument({ data: new Uint8Array(await file.arrayBuffer()), isEvalSupported: false }).promise;
    try {
      const n = doc.numPages, per = Math.min(12, Math.max(4, Math.ceil(n / budget))), cols = per <= 6 ? 2 : 3, out = [];
      for (let from = 1; from <= n && out.length < budget; from += per) {
        const to = Math.min(n, from + per - 1), rows = Math.ceil((to - from + 1) / cols);
        const c = document.createElement('canvas'); c.width = cols * (TW + PAD) + PAD; c.height = rows * (TH + PAD + HEAD) + PAD;
        const g = c.getContext('2d'); g.fillStyle = '#c8c8c8'; g.fillRect(0, 0, c.width, c.height);
        for (let i = from; i <= to; i++) {
          const k = i - from, x = PAD + (k % cols) * (TW + PAD), y = PAD + Math.floor(k / cols) * (TH + PAD + HEAD);
          const p = await doc.getPage(i), v1 = p.getViewport({ scale: 1 }), sc = Math.min(TW / v1.width, TH / v1.height), vp = p.getViewport({ scale: sc });
          const pc = document.createElement('canvas'); pc.width = Math.round(vp.width); pc.height = Math.round(vp.height);
          const pg = pc.getContext('2d'); pg.fillStyle = '#fff'; pg.fillRect(0, 0, pc.width, pc.height);
          await p.render({ canvasContext: pg, viewport: vp }).promise; p.cleanup();
          g.fillStyle = '#fff'; g.fillRect(x, y + HEAD, TW, TH); g.drawImage(pc, x + Math.round((TW - pc.width) / 2), y + HEAD);
          g.fillStyle = '#000'; g.font = 'bold 24px sans-serif'; g.fillText('Page ' + i, x + 4, y + 24);
        }
        out.push({ blob: await new Promise((res, rej) => c.toBlob(b => b ? res(b) : rej(new Error('the pages could not be drawn')), 'image/jpeg', 0.85)), from, to, pages: n });
      }
      return out;
    } finally { try { doc.destroy(); } catch (e) {} }
  }

  window.DBOCR = { available, read, pageImages, contactSheets, sha256, _toLogical: toLogical, _vote: vote, _spans: spans, _resize: resize, _pyRound: pyRound };
})();
