// Browser entry for the dev server: installs window.claude backed by the in-memory mock BEFORE the app script runs.
// Query flags: ?ro=1 read-only | ?nodb=1 db unavailable | ?nouser=1 | ?empty=1 no seed | ?dirty=1 broken books | ?seed=private | ?latency=ms
import { createMockRuntime } from './mock-runtime.js';
import { buildSyntheticSeed } from './synthetic-seed.js';

const q = new URLSearchParams(location.search);
const flags = {
  readOnly: q.has('ro'),
  noDb: q.has('nodb'),
  noUser: q.has('nouser'),
  latencyMs: Number(q.get('latency')) || 0,
};
window.__STRIFA_MOCK__ = flags;

async function pickSeed() {
  if (q.has('empty') || q.get('seed') === 'none') return null;
  if (q.get('seed') === 'private') {
    try {
      const r = await fetch('/__dev/seed.json');
      if (r.ok) return await r.json();
    } catch {
      /* fall through to synthetic */
    }
  }
  const seed = buildSyntheticSeed();
  if (q.has('dirty')) {
    // deliberately broken books so the integrity panel has something to show
    seed.entries.e000099 = { ...seed.entries.e000004, no: 99, desc: 'قيد غير متوازن للتجربة', lines: seed.entries.e000004.lines.map((l, i) => (i ? { ...l, cr: l.cr - 10 } : l)) };
    seed.fiscalYears['2023'] = { ...seed.fiscalYears['2023'], snapshot: null };
  }
  return seed;
}

const mock = createMockRuntime({ flags, seed: pickSeed() });
window.claude = mock.claude;
window.__MOCK__ = mock;
