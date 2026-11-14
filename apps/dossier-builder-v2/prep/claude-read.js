// Claude reads a scanned page, on the viewer's own claude.ai account (the page's `sample` capability, with images): the page drawn
// and cut in two halves along its long side, overlapping a little — the platform brings every picture down to about 1.2 megapixels,
// so a whole A4 page would reach Claude at about 110 dpi and small Arabic print would be lost — sent with the instruction the
// owner's own measure used on the 16 made-up pages (97–98 % of their facts; tools/measure/claude-page.mjs). Claude's text is the
// page's text: the same rules read it, and every fact keeps the words it was found in.
//   createClaudeReader(sample) → {page(canvas, {name, page, pages}) → {text, by: 'claude', truncated}}
//   a failure rejects with {code} as claude.ai gives it (not_granted, rate_limited, upstream_error…)
export const ASK_HALVES = 'The two images are the two halves of ONE scanned page of a pharmaceutical regulatory document, cut along its long side; they overlap a little. The page may be rotated, skewed or faint. Read it in its correct orientation and transcribe every word of the whole page once, exactly as written, in reading order: Arabic as Arabic, English as English, and every digit as it is drawn (keep Arabic-Indic digits as they are). Include headings, table cells and the text of stamps. Output only the transcription.';

const KEEP = 0.55;                  // each half: 55 % of the page, so the two overlap by a tenth and no line is cut in both
const MEGAPIXELS = 1.2e6;           // what the platform brings a picture to: each half is drawn at that size, no larger

function canvasOf(w, h) { const c = document.createElement('canvas'); c.width = Math.max(1, Math.round(w)); c.height = Math.max(1, Math.round(h)); return c; }
const png = c => new Promise((ok, no) => c.toBlob(b => (b ? ok(b) : no(Object.assign(new Error('the page could not be drawn'), { code: 'draw' }))), 'image/png'));

// the page's two halves along its long side, each about 1.2 megapixels → [Blob, Blob]
export async function halvesOf(src) {
  const wide = src.width > src.height;
  const [W, H] = wide ? [src.width * KEEP, src.height] : [src.width, src.height * KEEP];
  const k = Math.min(1, Math.sqrt(MEGAPIXELS / (W * H)));
  const out = [];
  for (const part of [0, 1]) {
    const c = canvasOf(W * k, H * k), g = c.getContext('2d');
    g.fillStyle = '#fff'; g.fillRect(0, 0, c.width, c.height);
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = 'high';
    const sx = wide && part ? src.width - W : 0, sy = !wide && part ? src.height - H : 0;
    g.drawImage(src, sx, sy, W, H, 0, 0, c.width, c.height);
    out.push(await png(c));
  }
  return out;
}

// Claude's answer as a page's text: a code fence or a sentence before the transcription taken away, nothing else changed
export function transcriptOf(text) {
  let t = String(text || '').replace(/\r\n?/g, '\n').trim();
  const fenced = t.match(/^```[a-z]*\n([\s\S]*?)\n```\s*$/i);
  if (fenced) t = fenced[1];
  t = t.replace(/^(here is|here's|below is|the transcription)[^\n]*:\s*\n/i, '');
  return t.split('\n').map(l => l.replace(/\s+$/, '')).join('\n').trim();
}

export function createClaudeReader(sample) {
  return {
    async page(canvas, { name = '', page = 1, pages = 1, signal } = {}) {
      const images = await halvesOf(canvas);
      const ask = `Page ${page} of ${pages} of the file «${name}».\n${ASK_HALVES}`;
      const opts = { images, cache: false };
      if (signal) opts.signal = signal;
      const res = await sample(ask, opts);
      return { text: transcriptOf(res.text), by: 'claude', truncated: !!res.truncated };
    },
  };
}
