// One dossier being prepared, as the tools see it: its files (by content, never by name), the facts read from them (each with the
// words on its page that hold it), and the log of every tool call. The same code in the browser and on the desktop: nothing here
// touches a disk or the network — the page or the bridge hands the files in, either their bytes or, for a folder on a computer, a
// way to read them when a tool needs them (a dossier folder can hold gigabytes) with a sample of their first and last bytes.
export const KINDS = ['pdf', 'docx', 'xlsx', 'pptx', 'zip', 'rar', '7z', 'png', 'jpeg', 'tiff', 'gif', 'webp', 'heic', 'text', 'unknown'];

const starts = (b, ...sig) => sig.every((v, i) => b[i] === v);
const ascii = s => [...s].map(c => c.charCodeAt(0));
function has(bytes, text, limit = bytes.length) {
  const t = ascii(text);
  outer: for (let i = 0, n = Math.min(bytes.length, limit) - t.length; i <= n; i++) {
    for (let k = 0; k < t.length; k++) if (bytes[i + k] !== t[k]) continue outer;
    return true;
  }
  return false;
}

// What a file is, read from its first bytes (and, for an Office file, the names inside the zip) — never from its name.
export function kindOf(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  if (has(b, '%PDF-', 1024)) return 'pdf';
  if (starts(b, 0x50, 0x4b, 0x03, 0x04) || starts(b, 0x50, 0x4b, 0x05, 0x06)) {
    if (has(b, 'word/')) return 'docx';
    if (has(b, 'xl/')) return 'xlsx';
    if (has(b, 'ppt/')) return 'pptx';
    return 'zip';
  }
  if (starts(b, ...ascii('Rar!\x1a\x07'))) return 'rar';
  if (starts(b, 0x37, 0x7a, 0xbc, 0xaf, 0x27, 0x1c)) return '7z';
  if (starts(b, 0x89, 0x50, 0x4e, 0x47)) return 'png';
  if (starts(b, 0xff, 0xd8, 0xff)) return 'jpeg';
  if (starts(b, 0x49, 0x49, 0x2a, 0x00) || starts(b, 0x4d, 0x4d, 0x00, 0x2a)) return 'tiff';
  if (starts(b, ...ascii('GIF8'))) return 'gif';
  if (starts(b, ...ascii('RIFF')) && b[8] === 0x57 && b[9] === 0x45) return 'webp';
  if (b.length > 12 && has(b.subarray(4, 12), 'ftyp') && /^(heic|heix|mif1|msf1|hevc)$/.test(String.fromCharCode(...b.subarray(8, 12)))) return 'heic';
  const head = b.subarray(0, 4096);
  if (head.length && !head.some(x => x === 0) && new TextDecoder('utf-8', { fatal: false }).decode(head).indexOf('�') < 0) return 'text';
  return 'unknown';
}

async function sha256(bytes) {
  const d = await globalThis.crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(d)].map(x => x.toString(16).padStart(2, '0')).join('');
}

export async function createWorkspace({ files = [], now = () => new Date().toISOString() } = {}) {
  const list = [];
  for (const f of files) {
    let bytes = f.bytes ? (f.bytes instanceof Uint8Array ? f.bytes : new Uint8Array(f.bytes)) : null;
    const entry = { id: `f${list.length + 1}`, name: f.name, path: f.path || f.name, size: bytes ? bytes.length : f.size,
                    kind: kindOf(bytes || f.sample), sha256: bytes ? await sha256(bytes) : null };
    // read when a tool first needs it (never part of what is saved or listed)
    Object.defineProperty(entry, 'bytes', { enumerable: false, get() { if (!bytes) bytes = f.read(); return bytes; } });
    list.push(entry);
  }
  const facts = [];
  const log = [];
  const undo = [];
  const cache = new Map();       // what a tool worked out once about a file (pages, text): never worked out twice
  return {
    files: list,
    facts,
    log,
    now,
    cache,
    file(id) {
      const f = list.find(x => x.id === id) || list.find(x => x.name === id || x.path === id);
      if (!f) throw new Error(`no file «${id}» in this dossier (the files are listed by list_files)`);
      return f;
    },
    addFact(fact) {
      const f = { id: `fact${facts.length + 1}`, ...fact, at: now() };
      facts.push(f);
      undo.push(() => facts.splice(facts.indexOf(f), 1));
      return f;
    },
    // Takes back the last change a tool made (a recorded fact so far).
    undoLast() { const u = undo.pop(); if (!u) return false; u(); return true; },
    record(entry) { log.push({ n: log.length + 1, at: now(), ...entry }); },
    toJSON() {
      return { files: list.map(f => ({ ...f })), facts, log };
    },
  };
}
