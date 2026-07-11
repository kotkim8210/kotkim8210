import { describe, expect, it } from 'vitest';
import { PIECES, GRID, TRAY_SIZE } from '../src/engine/pieces';

describe('piece pool v2 (variety expansion)', () => {
  it('has 33 pieces with sequential ids', () => {
    expect(GRID).toBe(9);
    expect(TRAY_SIZE).toBe(3);
    expect(PIECES).toHaveLength(33);
    PIECES.forEach((p, i) => expect(p.id).toBe(i));
  });

  it('every cells count matches its shape and shapes are rectangular', () => {
    for (const p of PIECES) {
      const w = p.shape[0].length;
      let sum = 0;
      for (const row of p.shape) {
        expect(row).toHaveLength(w);
        for (const v of row) {
          expect([0, 1]).toContain(v);
          sum += v;
        }
      }
      expect(sum).toBe(p.cells);
      expect(p.weight).toBeGreaterThan(0);
      expect(p.color).toBeGreaterThanOrEqual(0);
      expect(p.color).toBeLessThanOrEqual(5);
      expect(p.shape.length).toBeLessThanOrEqual(5);
      expect(w).toBeLessThanOrEqual(5);
    }
  });

  it('names are unique and orientation variants exist', () => {
    const names = PIECES.map((p) => p.name);
    expect(new Set(names).size).toBe(names.length);
    // every T orientation, both S/Z axes, all four 3-cell corners
    for (const required of ['t4', 't4u', 't4l', 't4r', 's4', 's4v', 'z4', 'z4v', 'l3', 'j3', 'l3b', 'j3b']) {
      expect(names).toContain(required);
    }
  });

  it('weighted average piece size stays near the §10 balance target', () => {
    const totalW = PIECES.reduce((s, p) => s + p.weight, 0);
    const avg = PIECES.reduce((s, p) => s + p.cells * p.weight, 0) / totalW;
    // spec target 3.78; documented post-expansion tolerance band
    expect(avg).toBeGreaterThan(3.6);
    expect(avg).toBeLessThan(4.0);
  });
});
