import { describe, expect, it } from 'vitest';
import { PETS, petProgress, petThreshold } from '../src/engine/pets';

describe('cosmic pets (collection goal system)', () => {
  it('has 12 pets with strictly increasing thresholds', () => {
    expect(PETS).toHaveLength(12);
    for (let i = 1; i < PETS.length; i++) {
      expect(petThreshold(i)).toBeGreaterThan(petThreshold(i - 1));
    }
    // the first friend arrives fast (hook) — within roughly one game
    expect(petThreshold(0)).toBeLessThanOrEqual(100);
  });

  it('progress tracks the egg fill and hatch boundaries', () => {
    expect(petProgress(0)).toEqual({ unlocked: 0, ratio: 0, needed: petThreshold(0), complete: false });
    const justBefore = petProgress(petThreshold(0) - 1);
    expect(justBefore.unlocked).toBe(0);
    expect(justBefore.needed).toBe(1);
    expect(justBefore.ratio).toBeGreaterThan(0.9);
    const hatch = petProgress(petThreshold(0));
    expect(hatch.unlocked).toBe(1);
    expect(hatch.ratio).toBe(0); // fresh egg starts for the next pet
  });

  it('completes after the last threshold and stays complete', () => {
    const last = petThreshold(PETS.length - 1);
    const done = petProgress(last);
    expect(done).toEqual({ unlocked: 12, ratio: 1, needed: 0, complete: true });
    expect(petProgress(last + 5000).complete).toBe(true);
  });

  it('every pet has an i18n key and emoji', () => {
    for (const [i, p] of PETS.entries()) {
      expect(p.key).toBe(`pet_${i}`);
      expect(p.emoji.length).toBeGreaterThan(0);
    }
  });
});
