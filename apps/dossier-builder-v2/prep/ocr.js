// The scan reader in the page: the reader measured best on the 16 made-up pages (94 % of their facts; tools/measure/paddle_reader.py
// `lines`, readers.mjs `paddle-lines`), the same steps in the browser:
//   1. the page turned upright when it lies on its side (its columns of ink sharper than its rows; of the two quarter turns, the one
//      Tesseract reads surer), then straightened: the small angle (±5°) at which its rows of ink are sharpest;
//   2. Tesseract 5 (tesseract.js, WebAssembly; the «best» Arabic model and English) finds the lines and their words;
//   3. every line holding Arabic is read by PaddleOCR's Arabic model (PP-OCRv5 mobile, onnxruntime-web), its numbers and dates read
//      again on their own (three cuts each; the reading most cuts agree on, a date or a «number/year» read with confidence);
//      a line without Arabic keeps Tesseract's reading (the Arabic model takes 0 for o in English); a line with both keeps
//      Tesseract's reading of the Latin words it is sure of (the Arabic model drops them) and the model's of the rest.
// Nothing leaves the browser. Its files come from `base` (written there by prep/build.mjs: the scripts, and the models, the runtime's
// WebAssembly and the language data as gzip in base64 text, which the artifact host serves).
//   createOcr({base, onLoad}) → {page(canvas, {dpi}) → text, load()}   (dpi when known: a PDF page drawn at 300 dpi)
const HEIGHT = 48, MIN_WIDTH = 320, SURE = 0.8;

const rtl = c => { const o = c.codePointAt(0); return (o >= 0x0590 && o <= 0x08ff) || (o >= 0xfb1d && o <= 0xfdff) || (o >= 0xfe70 && o <= 0xfeff); };
const ltr = c => /\p{Nd}/u.test(c) || /[a-z]/.test(c.toLowerCase()) || '%°µ'.includes(c);
// The model reads left to right as the line is drawn: an Arabic word comes out reversed, a number in its own order. Back to reading
// order: the line reversed, then each run of digits and Latin letters (with the / . , : - between them) put back.
export function toLogical(s) {
  const a = [...s];
  if (!a.some(rtl)) return s;
  const r = a.reverse(), out = [];
  for (let i = 0; i < r.length;) {
    if (ltr(r[i])) {
      let k = i;
      while (k < r.length && (ltr(r[k]) || ('/.,:-+ '.includes(r[k]) && k + 1 < r.length && ltr(r[k + 1])))) k++;
      out.push(r.slice(i, k).reverse().join(''));
      i = k;
    } else { out.push(r[i]); i++; }
  }
  return out.join('');
}
// Python's round (halves to even), for the picture's width as the measure computed it
export function pyRound(x) { const f = Math.floor(x), d = x - f; return d > 0.5 ? f + 1 : d < 0.5 ? f : (f % 2 === 0 ? f : f + 1); }
// Pillow's bilinear resampling (precompute_coeffs), so a cut is the picture the model saw in the measure
function coeffs(inSize, outSize) {
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
const clip8 = v => (v <= 0 ? 0 : v >= 255 ? 255 : Math.floor(v + 0.5));
export function resize(rgb, w0, h0, w1, h1) {                       // RGB bytes w0×h0 → w1×h1, as Image.resize(…, BILINEAR)
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

// The readings of a number most of the cuts agree on (a date or a «number/year» read so with confidence first); at a tie the surer.
export const SHAPES = [/^\p{Nd}{1,2}[/.\-]\p{Nd}{1,2}[/.\-](\p{Nd}{2}|\p{Nd}{4})$/u, /^\p{Nd}{4}[/.\-]\p{Nd}{1,2}[/.\-]\p{Nd}{1,2}$/u, /^\p{Nd}+\/\p{Nd}{4}$/u];
export function vote(readings, sure = SURE) {
  const shaped = readings.filter(([t, c]) => t && c >= sure && SHAPES.some(m => m.test(t)));
  const tally = new Map();
  for (const [t, c] of (shaped.length ? shaped : readings)) if (t) { const v = tally.get(t) || [0, 0]; tally.set(t, [v[0] + 1, v[1] + c]); }
  let best = null;
  for (const [t, [n, c]] of tally) if (!best || n > best[1] || (n === best[1] && c / n > best[2])) best = [t, n, c / n];
  return best ? [best[0], best[2]] : ['', 0];
}
const held = (run, found) => { const it = [...found].filter(c => /\p{Nd}/u.test(c)); let i = 0; for (const c of run) { while (i < it.length && it[i] !== c) i++; if (i++ >= it.length) return false; } return true; };

// ---- the page straightened (paddle_reader.straight): the angle in ±5° (steps of 0.25°) at which the rows of ink are sharpest
export function skewOf(gray, w, h) {
  const xs = [], ys = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) if (gray[y * w + x] < 128) { xs.push(x - w / 2); ys.push(y - h / 2); }
  let best = -1, angle = 0;
  const rows = new Float64Array(h);
  for (let a = -5; a <= 5.001; a += 0.25) {
    const r = a * Math.PI / 180, s = Math.sin(r), c = Math.cos(r);
    rows.fill(0);
    for (let i = 0; i < xs.length; i++) { const y = Math.round(-xs[i] * s + ys[i] * c + h / 2); if (y >= 0 && y < h) rows[y]++; }
    let m = 0; for (let y = 0; y < h; y++) m += rows[y]; m /= h;
    let v = 0; for (let y = 0; y < h; y++) v += (rows[y] - m) ** 2;
    if (v > best) { best = v; angle = Math.round(a * 100) / 100; }
  }
  return angle;
}

// Can this page run WebAssembly? (A page whose security policy forbids it cannot read scans: tesseract.js would wait for ever.)
export async function wasmAllowed() {
  try { await WebAssembly.instantiate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0])); return true; } catch { return false; }
}
const failed = (why, text) => Object.assign(new Error(text), { why });
const within = (ms, p, why) => Promise.race([p, new Promise((_, no) => setTimeout(() => no(failed(why, `no answer in ${ms / 1000} s`)), ms))]);

export function createOcr({ base = 'ocr/', onLoad = () => {} } = {}) {
  const url = rel => new URL(base + rel, document.baseURI).href;
  const canvasOf = (w, h) => { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; };
  const fromB64 = t => { const bin = atob(t.replace(/\s+/g, '')), out = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i); return out; };
  async function packed(rel) {                                       // <rel>.gz.b64.txt → the file's bytes
    const r = await fetch(url(rel + '.gz.b64.txt'));
    if (!r.ok) throw new Error(`${rel}: HTTP ${r.status}`);
    const gz = fromB64(await r.text());
    return new Uint8Array(await new Response(new Blob([gz]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
  }
  const script = src => new Promise((ok, no) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => no(new Error(`could not load ${src}`)); document.head.appendChild(s); });
  const simd = () => { try { return WebAssembly.validate(new Uint8Array([0, 97, 115, 109, 1, 0, 0, 0, 1, 5, 1, 96, 0, 1, 123, 3, 2, 1, 0, 10, 10, 1, 8, 0, 65, 0, 253, 15, 253, 98, 11])); } catch { return false; } };

  const stats = { pages: 0, tesseract: 0, paddle: 0, paddleRuns: 0, upright: 0 };   // where the time goes (ms), for the measure
  let loading = null;
  function load() {
    return loading || (loading = (async () => {
      if (!(await wasmAllowed())) throw failed('wasm', 'this view does not let a page run WebAssembly, which the scan reader needs');
      onLoad({ part: 'tesseract' });
      await script(url('tess/tesseract.min.js'));
      const tess = await within(180000, window.Tesseract.createWorker(['ara', 'eng'], 1, {
        workerPath: url('tess/worker.boot.js'), corePath: url(simd() ? 'tess/tesseract-core-simd-lstm.wasm.js' : 'tess/tesseract-core-lstm.wasm.js'),
        langPath: url('tess').replace(/\/$/, ''), gzip: true, workerBlobURL: false, cacheMethod: 'none' }), 'timeout');
      await tess.setParameters({ tessedit_pageseg_mode: '3' });                // automatic page layout, as the tesseract command
      onLoad({ part: 'paddle' });
      const ort = await import(/* @vite-ignore */ url('ort/ort.wasm.bundle.min.js'));
      ort.env.wasm.numThreads = 1; ort.env.wasm.proxy = false;
      ort.env.wasm.wasmBinary = await packed('ort/ort-wasm-simd-threaded.wasm');
      const sess = await ort.InferenceSession.create(await packed('paddle/arabic_PP-OCRv5_rec_mobile.onnx'), { executionProviders: ['wasm'] });
      const chars = await (await fetch(url('paddle/characters.json'))).json();
      onLoad({ part: 'ready' });
      return { tess, ort, sess, chars: ['\u0000', ...chars, ' '] };   // index 0: the blank; the last: the space
    })().catch(e => { loading = null; throw e; }));
  }

  // one cut of the page (RGB bytes) → [text in reading order, confidence 0–1]
  async function read(m, rgb, cw, ch) {
    const w = Math.max(1, pyRound(cw * HEIGHT / Math.max(1, ch))), W = Math.max(w, MIN_WIDTH);
    const px = resize(rgb, cw, ch, w, HEIGHT), x = new Float32Array(3 * HEIGHT * W), plane = HEIGHT * W;
    for (let y = 0; y < HEIGHT; y++) for (let i = 0; i < w; i++) {
      const s = (y * w + i) * 3, o = y * W + i;
      x[o] = (px[s + 2] / 255 - 0.5) / 0.5; x[plane + o] = (px[s + 1] / 255 - 0.5) / 0.5; x[2 * plane + o] = (px[s] / 255 - 0.5) / 0.5;   // BGR
    }
    const t0 = performance.now();
    const res = await m.sess.run({ [m.sess.inputNames[0]]: new m.ort.Tensor('float32', x, [1, 3, HEIGHT, W]) });
    stats.paddle += performance.now() - t0; stats.paddleRuns++;
    const out = res[m.sess.outputNames[0]], T = out.dims[1], C = out.dims[2], v = out.data, text = [], conf = [];
    let prev = 0;
    for (let t = 0; t < T; t++) {
      let best = 0, p = v[t * C];
      for (let j = 1; j < C; j++) if (v[t * C + j] > p) { p = v[t * C + j]; best = j; }
      if (best && best !== prev && best < m.chars.length) { text.push(m.chars[best]); conf.push(p); }
      prev = best;
    }
    return [toLogical(text.join('').trim()), conf.length ? conf.reduce((a, b) => a + b, 0) / conf.length : 0];
  }
  function cut(pix, l, t, r, b) {                                    // a part of the page as RGB bytes
    l = Math.max(0, Math.trunc(l)); t = Math.max(0, Math.trunc(t)); r = Math.min(pix.width, Math.trunc(r)); b = Math.min(pix.height, Math.trunc(b));
    const w = Math.max(1, r - l), h = Math.max(1, b - t), rgb = new Uint8Array(w * h * 3), d = pix.data;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) { const s = ((t + y) * pix.width + l + x) * 4, o = (y * w + x) * 3; rgb[o] = d[s]; rgb[o + 1] = d[s + 1]; rgb[o + 2] = d[s + 2]; }
    return [rgb, w, h];
  }
  const NUM = /\p{Nd}[\p{Nd}/.\-]*\p{Nd}/gu;
  // the line's numbers read again on their own (paddle_reader.numbers): its words that hold digits, side by side, cut out at the
  // line's height with three side margins; the reading most cuts agree on replaces the run of digits it holds in the line's reading
  // a run of digits worth reading again: one that can be a date or a «number/year» (four digits or more, or three around / or -);
  // a table's «10.0» or «36» cannot become either, and three cuts of it cost a second
  const worth = t => { const d = (t.match(/\p{Nd}/gu) || []).length; return d >= 4 || (d >= 3 && /\p{Nd}[/\-]\p{Nd}/u.test(t)); };
  async function numbers(m, pix, line, words, text) {
    const groups = [];
    let cur = null;
    for (const wd of words) {
      if (/\p{Nd}/u.test(wd.text)) {
        if (!cur) { cur = Object.assign([...wd.box], { text: wd.text }); groups.push(cur); }
        else { cur.splice(0, 4, Math.min(cur[0], wd.box[0]), Math.min(cur[1], wd.box[1]), Math.max(cur[2], wd.box[2]), Math.max(cur[3], wd.box[3])); cur.text += ' ' + wd.text; }
      } else cur = null;
    }
    const h = line[3] - line[1];
    for (const box of groups) {
      if (!worth(box.text)) continue;
      const readings = [];
      for (const mg of [0.3, 0.6, 0.9]) {
        const [rgb, w, hh] = cut(pix, box[0] - mg * h, line[1] - 0.15 * h, box[2] + mg * h, line[3] + 0.15 * h);
        const [t, c] = await read(m, rgb, w, hh);
        const found = t.match(NUM) || [];
        readings.push([found.length ? found.reduce((a, b) => (b.length > a.length ? b : a)) : '', c]);
      }
      const [found, conf] = vote(readings);
      if (conf < SURE || !SHAPES.some(s => s.test(found))) continue;
      for (const run of text.matchAll(/\p{Nd}+/gu)) {
        const around = text.slice(Math.max(0, run.index - 1), run.index + run[0].length + 1);
        if ([...run[0]].length >= 4 && !around.includes('/') && held(run[0], found)) { text = text.slice(0, run.index) + ' ' + found + ' ' + text.slice(run.index + run[0].length); break; }
      }
    }
    return text;
  }

  // a page turned a quarter: its lines run down the page, so its columns of ink, not its rows, are sharply uneven
  function grayOf(src, sw = 800) {
    const sh = Math.max(1, Math.round(sw * src.height / src.width)), small = canvasOf(sw, sh), g = small.getContext('2d', { willReadFrequently: true });
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(src, 0, 0, sw, sh);
    const d = g.getImageData(0, 0, sw, sh).data, gray = new Uint8Array(sw * sh);
    for (let i = 0; i < gray.length; i++) gray[i] = (d[i * 4] * 299 + d[i * 4 + 1] * 587 + d[i * 4 + 2] * 114) / 1000;
    return { gray, sw, sh };
  }
  function sideways(src) {
    const { gray, sw, sh } = grayOf(src, 600), rows = new Float64Array(sh), cols = new Float64Array(sw);
    for (let y = 0; y < sh; y++) for (let x = 0; x < sw; x++) if (gray[y * sw + x] < 128) { rows[y]++; cols[x]++; }
    const cv = a => { let m = 0; for (const v of a) m += v; m /= a.length; let q = 0; for (const v of a) q += (v - m) ** 2; return q / a.length; };
    // normalised by the length of each line of pixels, so a tall page is not taken for one with long lines
    return cv(cols) / (sh * sh) > 1.5 * (cv(rows) / (sw * sw));
  }
  function turned(src, rot) {                                        // the picture turned clockwise by 90, 180 or 270 degrees
    const side = rot % 180 !== 0, c = canvasOf(side ? src.height : src.width, side ? src.width : src.height), g = c.getContext('2d');
    g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
    g.translate(c.width / 2, c.height / 2); g.rotate(rot * Math.PI / 180); g.drawImage(src, -src.width / 2, -src.height / 2);
    return c;
  }
  async function sureness(m, src) {                                  // how sure Tesseract is of its words of three letters or more, at half size
    const half = canvasOf(src.width / 2, src.height / 2), g = half.getContext('2d');
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high'; g.drawImage(src, 0, 0, half.width, half.height);
    const { data } = await m.tess.recognize(half, {}, { text: false, tsv: true });
    const words = layout(data.tsv).flatMap(l => l.words).filter(w => [...w.text].length >= 3);
    return words.length ? words.reduce((a, w) => a + w.conf, 0) / words.length * Math.min(1, words.length / 20) : 0;
  }
  async function upright(m, src) {
    if (!sideways(src)) return { canvas: src, rot: 0 };
    const [a, b] = [turned(src, 90), turned(src, 270)];
    return (await sureness(m, a)) >= (await sureness(m, b)) ? { canvas: a, rot: 90 } : { canvas: b, rot: 270 };
  }

  function straightened(src) {
    const { gray, sw, sh } = grayOf(src);
    const angle = skewOf(gray, sw, sh);
    if (!angle) return { canvas: src, angle };
    const c = canvasOf(src.width, src.height), x = c.getContext('2d');
    x.fillStyle = '#fff'; x.fillRect(0, 0, c.width, c.height);
    x.translate(c.width / 2, c.height / 2); x.rotate(-angle * Math.PI / 180); x.translate(-c.width / 2, -c.height / 2);
    x.imageSmoothingEnabled = true; x.imageSmoothingQuality = 'high'; x.drawImage(src, 0, 0);
    return { canvas: c, angle };
  }
  // Tesseract's lines and words, in its reading order, from its TSV: boxes [x0, y0, x1, y1] in pixels
  function layout(tsv) {
    const lines = new Map();
    for (const row of String(tsv || '').split('\n')) {
      const f = row.split('\t');
      if (f.length < 12) continue;
      const level = +f[0], key = `${f[2]}/${f[3]}/${f[4]}`, box = [+f[6], +f[7], +f[6] + +f[8], +f[7] + +f[9]];
      if (level === 4) lines.set(key, { box, words: [] });
      else if (level === 5) { const text = f.slice(11).join('\t').trim(); if (text && lines.has(key)) lines.get(key).words.push({ text, conf: +f[10], box }); }
    }
    return [...lines.values()];
  }

  // A line holding Arabic and a Latin name («رسوم نقل تصنيع إلى Sinai Test Industries»): the Arabic model drops the Latin words, so the
  // line is read in parts, by Tesseract's words: each run of Latin words Tesseract is sure of keeps Tesseract's reading, each run of
  // the rest is cut out and read by the Arabic model (its numbers again on their own); the parts in the line's order, right to left.
  const LATIN = /^[A-Za-z][A-Za-z.,&()'’\-]*$/;
  const sureLatin = wd => LATIN.test(wd.text) && wd.conf >= 70 && wd.text.replace(/[^A-Za-z]/g, '').length >= 2;
  async function mixed(m, pix, l) {
    const [, y0, , y1] = l.box, h = y1 - y0, runs = [];
    for (const wd of [...l.words].sort((a, b) => b.box[0] - a.box[0])) {
      const latin = sureLatin(wd), last = runs[runs.length - 1];
      if (last && last.latin === latin) last.words.push(wd); else runs.push({ latin, words: [wd] });
    }
    const parts = [];
    for (const run of runs) {
      if (run.latin) { parts.push(run.words.sort((a, b) => a.box[0] - b.box[0]).map(wd => wd.text).join(' ')); continue; }
      const x0 = Math.min(...run.words.map(wd => wd.box[0])), x1 = Math.max(...run.words.map(wd => wd.box[2])), mg = 0.2 * h;
      const [rgb, w, hh] = cut(pix, x0 - mg, y0 - mg, x1 + mg, y1 + mg);
      const [text] = await read(m, rgb, w, hh);
      parts.push(await numbers(m, pix, [x0, y0, x1, y1], run.words.sort((a, b) => a.box[0] - b.box[0]), text));
    }
    return parts.filter(t => t.trim()).join(' ');
  }

  async function page(source, { dpi = 0 } = {}) {
    const m = await load();
    await m.tess.setParameters({ user_defined_dpi: String(dpi || 0) });
    let t0 = performance.now();
    const { canvas } = straightened((await upright(m, source)).canvas);
    stats.upright += performance.now() - t0; t0 = performance.now();
    const { data } = await m.tess.recognize(canvas, {}, { text: false, tsv: true });
    stats.tesseract += performance.now() - t0; stats.pages++;
    const pix = canvas.getContext('2d', { willReadFrequently: true }).getImageData(0, 0, canvas.width, canvas.height);
    const out = [];
    for (const l of layout(data.tsv)) {
      const [x0, y0, x1, y1] = l.box, mg = 0.2 * (y1 - y0);
      const [rgb, w, h] = cut(pix, x0 - mg, y0 - mg, x1 + mg, y1 + mg);
      const [text] = await read(m, rgb, w, h);
      // a line without Arabic: Tesseract's own reading; with Arabic: the model's, its numbers read again — in parts when it holds
      // Latin words Tesseract is sure of
      out.push(l.words.length && ![...text].some(rtl) ? l.words.map(wd => wd.text).join(' ')
        : l.words.some(sureLatin) && l.words.some(wd => !sureLatin(wd)) ? await mixed(m, pix, l) : await numbers(m, pix, l.box, l.words, text));
      await new Promise(r => setTimeout(r, 0));
    }
    return out.filter(s => s.trim()).join('\n');
  }
  return { load, page, stats };
}
