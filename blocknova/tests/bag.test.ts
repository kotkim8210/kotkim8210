import { describe, expect, it } from 'vitest';
import { drawWeighted, refillTray, sameCombination, MAX_REDRAWS } from '../src/engine/bag';
import { PIECES, pieceByName } from '../src/engine/pieces';
import { emptyBoard, hasAnyPlacement } from '../src/engine/board';
import { mulberry32 } from '../src/engine/rng';
import { boardFrom } from './helpers';

describe('weighted spawn bag (game-design §2)', () => {
  it('draw frequencies track piece weights', () => {
    const rng = mulberry32(20260801);
    const draws = 30000;
    const counts = new Map<number, number>();
    for (let i = 0; i < draws; i++) {
      const p = drawWeighted(PIECES, rng);
      counts.set(p.id, (counts.get(p.id) ?? 0) + 1);
    }
    const totalWeight = PIECES.reduce((s, p) => s + p.weight, 0);
    for (const p of PIECES) {
      const expected = (draws * p.weight) / totalWeight;
      const observed = counts.get(p.id) ?? 0;
      // ~4σ band on the smallest weight — deterministic under the fixed seed.
      expect(Math.abs(observed - expected)).toBeLessThan(expected * 0.15);
    }
  });

  it('never repeats the previous 3-piece combination', () => {
    const rng = mulberry32(7);
    const board = emptyBoard();
    let prev: number[] | null = null;
    for (let i = 0; i < 300; i++) {
      const tray = refillTray({ pieces: PIECES, rng, board, prevIds: prev });
      const ids = tray.map((p) => p.id);
      if (prev) expect(sameCombination(ids, prev)).toBe(false);
      prev = ids;
    }
  });

  it('combination check ignores order', () => {
    expect(sameCombination([1, 2, 3], [3, 1, 2])).toBe(true);
    expect(sameCombination([1, 2, 3], [1, 2, 2])).toBe(false);
    expect(sameCombination([5, 5, 1], [5, 1, 5])).toBe(true);
  });

  it('guarantees at least one placeable piece on a tight board', () => {
    // Only a 2×2 hole at the top-left corner is free, so most of the 19 pieces
    // don't fit — every refill must still deliver at least one that does.
    // (The guarantee is bounded by 20 redraws; with 6 small pieces placeable
    // the fixed seed satisfies it on every iteration.)
    const rows = [
      '..#######',
      '..#######',
      '#########',
      '#########',
      '#########',
      '#########',
      '#########',
      '#########',
      '#########',
    ];
    const board = boardFrom(rows);
    const rng = mulberry32(42);
    let prev: number[] | null = null;
    for (let i = 0; i < 50; i++) {
      const tray = refillTray({ pieces: PIECES, rng, board, prevIds: prev });
      expect(tray.some((p) => hasAnyPlacement(board, p.shape))).toBe(true);
      prev = tray.map((p) => p.id);
    }
  });

  it('falls back to the last draw after MAX_REDRAWS failed attempts', () => {
    // A constant RNG always draws the first piece (dot), so the "different
    // combination" constraint can never be met — the draw is still returned.
    const constantRng = () => 0;
    const dotId = pieceByName('dot').id;
    const tray = refillTray({
      pieces: PIECES,
      rng: constantRng,
      board: emptyBoard(),
      prevIds: [dotId, dotId, dotId],
    });
    expect(tray.map((p) => p.id)).toEqual([dotId, dotId, dotId]);
    expect(MAX_REDRAWS).toBe(20);
  });
});
