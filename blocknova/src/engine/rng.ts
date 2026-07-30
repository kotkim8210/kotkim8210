export type Rng = () => number;

/** Deterministic 32-bit PRNG. The daily challenge (Phase 2) relies on this
 *  exact algorithm, so it must never change. */
export function mulberry32(seed: number): Rng {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Non-deterministic seed for classic mode. */
export function randomSeed(): number {
  return (Date.now() ^ (Math.random() * 0xffffffff)) >>> 0;
}
