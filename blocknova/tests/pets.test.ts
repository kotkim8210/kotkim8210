import { describe, expect, it } from 'vitest';
import { PETS, PET_TILES, petProgress, petThreshold } from '../src/engine/pets';
import { PET_ART } from '../src/engine/petart';

describe('cosmic friends (pixel puzzle collection)', () => {
  it('has 8 pixel pets with strictly increasing thresholds', () => {
    expect(PETS).toHaveLength(8);
    for (let i = 1; i < PETS.length; i++) {
      expect(petThreshold(i)).toBeGreaterThan(petThreshold(i - 1));
    }
    // the first friend arrives fast (hook) — within roughly one game
    expect(petThreshold(0)).toBeLessThanOrEqual(100);
  });

  it('progress tracks tiles and completion boundaries', () => {
    expect(petProgress(0)).toEqual({
      unlocked: 0,
      ratio: 0,
      tiles: 0,
      needed: petThreshold(0),
      complete: false,
    });
    const justBefore = petProgress(petThreshold(0) - 1);
    expect(justBefore.unlocked).toBe(0);
    expect(justBefore.needed).toBe(1);
    // the final tile only opens at completion (suspense)
    expect(justBefore.tiles).toBeLessThanOrEqual(PET_TILES - 1);
    const done = petProgress(petThreshold(0));
    expect(done.unlocked).toBe(1);
    expect(done.ratio).toBe(0); // fresh puzzle starts for the next friend
  });

  it('completes after the last threshold and stays complete', () => {
    const last = petThreshold(PETS.length - 1);
    const done = petProgress(last);
    expect(done).toEqual({ unlocked: 8, ratio: 1, tiles: PET_TILES, needed: 0, complete: true });
    expect(petProgress(last + 5000).complete).toBe(true);
  });

  it('every pet has an i18n key, emoji and artwork', () => {
    for (const [i, p] of PETS.entries()) {
      expect(p.key).toBe(`pet_${i}`);
      expect(p.emoji.length).toBeGreaterThan(0);
      expect(p.art).toBe(PET_ART[i]);
    }
  });

  it('pixel art integrity: 16×16 grids, all chars in each palette', () => {
    for (const art of PET_ART) {
      expect(art.rows).toHaveLength(16);
      for (const row of art.rows) {
        expect(row).toHaveLength(16);
        for (const ch of row) {
          if (ch === '.') continue;
          expect(art.palette[ch], `missing palette entry '${ch}'`).toMatch(/^#[0-9a-f]{6}$/i);
        }
      }
      // every sprite has an outline and at least 4 colors (readable pixel art)
      expect(Object.keys(art.palette).length).toBeGreaterThanOrEqual(4);
    }
  });
});
