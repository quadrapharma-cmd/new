// The workshop's line of work (docs/PART-2-PLAN.md §3.3): a new dossier → its files received and opened → each document read and
// understood → a file holding several documents cut → each document named and placed on the board → facts into the product's data.
// The checks, the fixes, the documents the program writes and «needs you» follow in their own modules. Every step works on the
// dossier object the store keeps, logs what it did, and can be run again: what was done is not done twice.
import { readFiles } from '../prep/read.js';
import { typeAndPlace, segmentsOf, factsByRules, onPage } from './understand.js';
import { boardOf, partyOf } from './board.js';
import { cutPdf } from './pdfops.js';
import { sha256 } from './store.js';
import { askJson, STOP } from './claude.js';

const now = () => new Date().toISOString();
export function log(d, what, extra = {}) { d.log.push({ n: d.log.length + 1, at: now(), what, ...extra }); }

export function newDossier({ country = 'EG', profile = {}, name = '' } = {}) {
  const t = Date.now().toString(36);
  const d = { id: `dz-${t}`, name: name || 'ملف جديد', created: now(), updated: now(), country, profile, product: {}, docs: [], decisions: {}, log: [], seq: 0 };
  log(d, 'new', { country });
  return d;
}
const nextId = d => `D${++d.seq}`;

const EDA_TYPES = new Set(['registration_licence', 'transfer_approval', 'stability_approval', 'fee_receipt', 'eda_letter']);
export function partyFor(doc, board) {
  if (doc.madeBy === 'program') return 'company';
  const place = board.places.find(p => p.id === doc.place);
  if (place) return partyOf(place.doc_class);
  if (EDA_TYPES.has(doc.type)) return 'eda';
  if (doc.type === 'coa') return 'third';
  return 'company';
}

// ---------------------------------------------------------------------------------------------------------------- receiving
// files: [{name, bytes}] (the viewer's files, folders flattened, archives as they are). env: {read: env of prep/read.js,
// putBlob(dossierId, key, bytes)}. Every document found (archives opened, as deep as they go) becomes one record with its pages read.
export async function addFiles(d, files, env) {
  const docs = await readFiles(files, { ...env.read, keepBytes: true });
  const known = new Map(d.docs.filter(x => !x.from).map(x => [x.sha, x.id]));
  const added = [];
  for (const r of docs) {
    const bytes = r.bytes || new Uint8Array();
    const sha = bytes.length ? await sha256(bytes) : `empty-${d.seq + 1}`;
    const doc = { id: nextId(d), name: r.name, kind: r.kind, sha, size: bytes.length, pages: r.pages || [], added: now(), state: 'read',
                  ...(r.unread ? { unread: r.unread } : {}), ...(r.note ? { note: r.note } : {}), ...(r.error ? { error: r.error } : {}) };
    if (known.has(sha)) { doc.dup = known.get(sha); doc.state = 'dup'; }
    else { known.set(sha, doc.id); if (bytes.length) await env.putBlob(d.id, sha, bytes); }
    d.docs.push(doc);
    added.push(doc);
  }
  log(d, 'received', { files: files.length, docs: added.length, dups: added.filter(x => x.dup).length, ocrFailed: env.read?.ocrFailed ? String(env.read.ocrFailed.why || env.read.ocrFailed.message || '') : null });
  return added;
}

// ---------------------------------------------------------------------------------------------------------------- understanding
const visible = d => d.docs.filter(x => !x.dup && !x.split);
const pagesText = (pages, from = 1, to = pages.length) => pages.filter(p => p.n >= from && p.n <= to);

// The documents not yet understood: cut where a file holds several, typed and placed, their facts read.
// env: {knowledge, getBlob, putBlob, claude?: {sample}, onProgress?}
export async function understand(d, env) {
  const board = boardOf(env.knowledge, { countryId: d.country, profile: d.profile });
  const open = new Set(board.places.filter(p => p.level !== 'NA').map(p => p.id));
  const recognition = Object.assign({}, ...board.country.sets.map(s => env.knowledge.recognition?.[s] || {}));
  const opts = { recognition: d.country === 'EG' ? recognition : {}, places: open };
  for (const doc of [...visible(d)]) {
    if (doc.state !== 'read') continue;
    env.onProgress?.({ stage: 'understand', name: doc.name });
    if (doc.unread || !doc.pages.length) { doc.state = 'placed'; doc.place = null; doc.party = 'company'; continue; }
    // 1. a PDF holding several documents is cut, each part read on its own
    if (doc.kind === 'pdf' && doc.pages.length > 1 && !doc.from) {
      const segs = segmentsOf(doc.pages, opts);
      if (segs.length > 1) {
        const bytes = await env.getBlob(d.id, doc.sha);
        doc.split = true;
        doc.cut = { sure: segs.every(s => s.sure), segments: segs.map(s => [s.from, s.to]), by: 'rules' };
        for (const s of segs) {
          const part = await cutPdf(bytes, s.from, s.to);
          const sha = await sha256(part);
          await env.putBlob(d.id, sha, part);
          const child = { id: nextId(d), name: `${doc.name} (ص ${s.from}–${s.to})`, kind: 'pdf', sha, size: part.length, added: now(), state: 'read',
                          from: { doc: doc.id, pages: [s.from, s.to] },
                          pages: pagesText(doc.pages, s.from, s.to).map(p => ({ ...p, n: p.n - s.from + 1 })), ...(doc.note ? { note: doc.note } : {}) };
          d.docs.push(child);
          place(child, board, opts);
        }
        log(d, 'cut', { doc: doc.id, segments: doc.cut.segments, sure: doc.cut.sure });
        continue;
      }
    }
    place(doc, board, opts);
  }
  // 2. what the rules could not place: Claude, where the viewer gave it
  if (env.claude?.sample) await placeByClaude(d, board, env);
  for (const doc of visible(d)) doc.party = partyFor(doc, board);
  log(d, 'understood', { placed: visible(d).filter(x => x.place).length, unplaced: visible(d).filter(x => !x.place && !x.unread).length });
  return board;
}

function place(doc, board, opts) {
  const t = typeAndPlace(doc.pages, opts);
  Object.assign(doc, { type: t.type, type_ar: t.type_ar, doctype: t.doctype, place: t.place, sure: t.sure, placeBy: t.place ? 'rules' : null,
                       ...(t.words ? { words: t.words } : {}), ...(t.maybe ? { maybe: t.maybe } : {}) });
  doc.facts = factsByRules(doc.pages);
  doc.state = 'placed';
}

const PLACE_ASK = (board, doc) => [
  `You sort the documents of a medicine's registration dossier for ${board.country.en} (${board.country.authority}). Below is one document: its file name and the text of its first pages (read from the file or from its scan).`,
  'Decide which place of the dossier it belongs to. Choose only from this list (id | CTD number | title):',
  board.places.filter(p => p.level !== 'NA').map(p => `${p.id} | ${p.ctd} | ${p.title.en}`).join('\n'),
  '',
  `File: ${doc.name}`,
  ...doc.pages.slice(0, 3).map(p => `--- page ${p.n} ---\n${String(p.text || '').slice(0, 2500)}`),
  '',
  'Answer as JSON: {"place": "<an id from the list, or \\"\\" if none fits>", "type": "<the kind of document, in English>", "type_ar": "<the same in Arabic>",',
  '"party": "company" | "third" | "eda" (who issued it: the applicant company, another party such as a manufacturer or a foreign authority, or the Egyptian Drug Authority),',
  '"sure": true | false, "why": "<one short sentence in Arabic: the words on the pages that show it>"}',
].join('\n');

async function placeByClaude(d, board, env) {
  const ids = new Set(board.places.map(p => p.id));
  for (const doc of visible(d)) {
    if (doc.unread || !doc.pages.length || (doc.place && doc.sure) || doc.placeBy === 'you' || doc.claudeAsked) continue;
    env.onProgress?.({ stage: 'claude-place', name: doc.name });
    try {
      const { value } = await askJson(env.claude.sample, PLACE_ASK(board, doc), { maxTokens: 1500, effort: 'low' });
      doc.claudeAsked = true;
      if (value?.place && ids.has(value.place)) {
        Object.assign(doc, { place: value.place, sure: !!value.sure, placeBy: 'claude', claudeWhy: String(value.why || '').slice(0, 300),
                             type_ar: doc.type_ar && doc.type !== 'unknown' && doc.type !== 'place' ? doc.type_ar : String(value.type_ar || '').slice(0, 80) || doc.type_ar });
        log(d, 'placed-by-claude', { doc: doc.id, place: value.place });
      } else if (value) { doc.claudeWhy = String(value.why || '').slice(0, 300); }
    } catch (e) {
      log(d, 'claude-failed', { doc: doc.id, code: e.code || 'error' });
      if (STOP.has(e.code)) { env.claudeOff = e.code; break; }
    }
  }
}

// Facts Claude reads from a document for the fields its rule card asks, each kept only if its words are on the page it names.
export async function factsByClaude(doc, fields, sample) {
  const ask = [
    'Read this document of a medicine registration dossier and give the facts asked for, each with the exact words of the page that hold it.',
    `Facts asked: ${fields.join(', ')}.`,
    ...doc.pages.slice(0, 6).map(p => `--- page ${p.n} ---\n${String(p.text || '').slice(0, 4000)}`),
    'Answer as JSON: {"facts": [{"field": "<one of the fields>", "value": "<the value>", "page": <page number>, "quote": "<the words of that page, copied exactly>"}]}. Leave out what the pages do not say.',
  ].join('\n');
  const { value } = await askJson(sample, ask, { maxTokens: 3000, effort: 'low' });
  const out = [];
  for (const f of Array.isArray(value?.facts) ? value.facts.slice(0, 40) : []) {
    const page = Number(f.page), quote = String(f.quote || '');
    if (fields.includes(f.field) && f.value && onPage(doc.pages, page, quote)) out.push({ field: f.field, value: String(f.value).slice(0, 300), page, quote: quote.slice(0, 400), by: 'claude' });
  }
  return out;
}

// The viewer's own decisions: a document moved to another place, a cut confirmed or changed.
export function moveDoc(d, docId, placeId) {
  const doc = d.docs.find(x => x.id === docId);
  if (!doc) return;
  log(d, 'moved', { doc: docId, from: doc.place || null, to: placeId || null });
  Object.assign(doc, { place: placeId || null, sure: true, placeBy: 'you' });
}
