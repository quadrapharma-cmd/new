// Seeded PRNG (mulberry32) for reproducible property-style tests. No external dependency.
export function makeRng(seed = 1) {
  let a = seed >>> 0;
  const next = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const rng = {
    /** float in [0,1) */
    next,
    /** integer in [0,n) */
    int: (n) => Math.floor(next() * n),
    /** integer in [lo,hi] inclusive */
    range: (lo, hi) => lo + Math.floor(next() * (hi - lo + 1)),
    /** random element */
    pick: (arr) => arr[Math.floor(next() * arr.length)],
    /** true with probability p */
    chance: (p) => next() < p,
    /** Fisher-Yates shuffle (returns a new array) */
    shuffle(arr) {
      const out = arr.slice();
      for (let i = out.length - 1; i > 0; i--) {
        const j = Math.floor(next() * (i + 1));
        [out[i], out[j]] = [out[j], out[i]];
      }
      return out;
    },
  };
  return rng;
}
