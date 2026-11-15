// The fixes the program makes by itself (Part 2, step 2.6) and the drafts it writes. A fix never changes what a page shows: a PDF
// saved again at a current version, an outline made from the document's own table of contents, a picture made a PDF page. The
// original stays in the dossier; the fixed file is a new version beside it. A draft is a company paper the board requires and the
// program can write (workshop/generators.js), written again whenever the dossier's data change.
import { fold } from '../core/fold.js';
import { withOutline, withTitle, picturesToPdf, pdfInfo } from './pdfops.js';
import { draftFor, GENERATORS } from './generators.js';
import { docxOf, gapsOf } from './docx.js';
import { sha256 } from './store.js';
import { log } from './pipeline.js';

// The outline a table of contents gives: its lines that end in a page number ( «2.3 Stability ........ 14» ), within the document.
export function outlineFromToc(pages) {
  const out = [];
  const total = pages.length;
  for (const p of pages.slice(0, 4)) {
    for (const line of String(p.text || '').split('\n')) {
      const m = /^\s*(.{3,90}?)[\s.·…_-]{2,}(\d{1,4})\s*$/.exec(line);
      if (!m) continue;
      const title = m[1].replace(/[.·…_\s-]+$/, '').trim(), page = Number(m[2]);
      if (page >= 1 && page <= total && /[\p{L}]/u.test(title) && !fold(title).match(/^(page|صفحه)$/)) out.push({ title, page });
    }
  }
  return out.filter((x, i, a) => a.findIndex(y => y.title === x.title) === i).slice(0, 200);
}

// The automatic fixes the findings allow. env: {getBlob, putBlob}. → [{doc, fix}]
export async function fixAll(d, findings, env) {
  const done = [];
  for (const f of findings) {
    if (!f.fix?.auto || f.accepted || f.fix.auto === 'create') continue;
    const doc = d.docs.find(x => x.id === f.doc);
    if (!doc || doc.fixes?.some(x => x.id === f.fix.auto && x.from === (doc.fixed || doc.sha))) continue;
    try {
      const bytes = await env.getBlob(d.id, doc.fixed || doc.sha);
      let out = null, ar = '';
      if (f.fix.auto === 'version') { out = await withTitle(bytes, `${doc.name}`); ar = 'اتحفظ PDF نسخة 1.7 من غير تغيير في الصفحات'; }
      else if (f.fix.auto === 'outline') {
        const items = outlineFromToc(doc.pages);
        if (!items.length) { f.fixFailed = 'مالقاش سطور في الفهرس فيها أرقام صفحات'; continue; }
        out = await withOutline(bytes, items); ar = `اتعمله ${items.length} bookmark من الفهرس`;
      } else if (f.fix.auto === 'picture') {
        out = await picturesToPdf([{ bytes, kind: ['png', 'psd'].includes(doc.kind) ? doc.kind : 'jpeg' }]); ar = 'الصورة بقت صفحة PDF';
      }
      if (!out) continue;
      const sha = await sha256(out);
      await env.putBlob(d.id, sha, out);
      doc.fixes = [...(doc.fixes || []), { id: f.fix.auto, ar, from: doc.fixed || doc.sha, to: sha, at: new Date().toISOString() }];
      doc.fixed = sha;
      if (f.fix.auto === 'picture') { doc.picture = doc.kind; doc.kind = 'pdf'; }   // a PDF now; the picture it was (doc.sha) opens in the photo program
      delete doc.info;
      log(d, 'fixed', { doc: doc.id, fix: f.fix.auto });
      done.push({ doc: doc.id, fix: f.fix.auto });
    } catch (e) { f.fixFailed = String(e.message || e).slice(0, 200); }
  }
  return done;
}

// The drafts of every required place that is empty and has a generator (and those already written, written again).
// → {placeId: {doc, gaps, ar}}
export async function writeDrafts(d, board, env, { only = null } = {}) {
  const drafts = {};
  const filledByPeople = new Set(d.docs.filter(x => x.place && !x.dup && !x.split && x.madeBy !== 'program').map(x => x.place));
  for (const place of board.places) {
    if (!GENERATORS[place.id] || place.level === 'NA' || place.level === 'NR' || filledByPeople.has(place.id)) continue;
    if (only && !only.includes(place.id)) continue;
    const existing = d.docs.find(x => x.place === place.id && x.madeBy === 'program');
    if (!existing && place.level !== 'R' && !only) continue;           // an optional place: only when asked
    if (existing?.editedBy) { drafts[place.id] = { doc: existing.id, gaps: [], ar: GENERATORS[place.id].ar }; continue; }   // edited by the person: theirs now
    const draft = draftFor(place.id, d);
    const bytes = await docxOf(draft.model);
    const sha = await sha256(bytes);
    const text = draft.model.blocks.map(b => (b.t === 'table' ? [...(b.head || []), ...b.rows.flat()] : [b.parts]).flat()
      .map(p => (typeof p === 'string' ? p : p?.gap ? `[${p.gap}]` : p?.value ?? '')).join(' ')).join('\n');
    if (existing && existing.sha === sha) { drafts[place.id] = { doc: existing.id, gaps: gapsOf(draft.model), ar: draft.ar }; continue; }
    await env.putBlob(d.id, sha, bytes);
    if (existing) {
      existing.versions = [...(existing.versions || []), { sha: existing.sha, at: existing.made }];
      Object.assign(existing, { sha, size: bytes.length, pages: [{ n: 1, text, by: 'program' }], made: new Date().toISOString() });
      drafts[place.id] = { doc: existing.id, gaps: gapsOf(draft.model), ar: draft.ar };
    } else {
      const doc = { id: `D${++d.seq}`, name: `${draft.ar} (مسودة).docx`, kind: 'docx', madeBy: 'program', generator: draft.generator, sha, size: bytes.length,
                    pages: [{ n: 1, text, by: 'program' }], place: place.id, sure: true, placeBy: 'program', party: 'company', state: 'placed', facts: [],
                    made: new Date().toISOString() };
      d.docs.push(doc);
      log(d, 'created', { doc: doc.id, place: place.id, generator: draft.generator });
      drafts[place.id] = { doc: doc.id, gaps: gapsOf(draft.model), ar: draft.ar };
    }
  }
  return drafts;
}
