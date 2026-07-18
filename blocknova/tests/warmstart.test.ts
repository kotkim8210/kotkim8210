import { describe, expect, it } from 'vitest';
import { warmStartBoard } from '../src/engine/warmstart';
import { Game } from '../src/engine/game';
import { mulberry32 } from '../src/engine/rng';
import { idx, SIZE, fullLines } from '../src/engine/board';

describe('warm-start board (early-clear pacing)', () => {
  it('is deterministic for a given rng seed', () => {
    expect(warmStartBoard(mulberry32(42))).toEqual(warmStartBoard(mulberry32(42)));
    expect(warmStartBoard(mulberry32(42))).not.toEqual(warmStartBoard(mulberry32(43)));
  });

  it('fills only rows 6-8, never completes a line, stays modest', () => {
    for (let seed = 1; seed <= 40; seed++) {
      const board = warmStartBoard(mulberry32(seed));
      let total = 0;
      for (let r = 0; r < SIZE; r++) {
        let rowFill = 0;
        for (let c = 0; c < SIZE; c++) {
          if (board[idx(r, c)] !== 0) {
            expect(r).toBeGreaterThanOrEqual(6);
            rowFill++;
            total++;
          }
        }
        expect(rowFill).toBeLessThanOrEqual(7); // the win stays with the player
      }
      for (let c = 0; c < SIZE; c++) {
        let colFill = 0;
        for (let r = 0; r < SIZE; r++) if (board[idx(r, c)] !== 0) colFill++;
        expect(colFill).toBeLessThanOrEqual(3);
      }
      expect(total).toBeGreaterThanOrEqual(10);
      expect(total).toBeLessThanOrEqual(21);
      const { rows, cols } = fullLines(board);
      expect(rows).toHaveLength(0);
      expect(cols).toHaveLength(0);
    }
  });

  it('Game with warmStart opens playable and reproducible per seed', () => {
    const a = new Game({ seed: 7, warmStart: true });
    const b = new Game({ seed: 7, warmStart: true });
    expect(a.board).toEqual(b.board);
    expect(a.tray.map((p) => p?.id)).toEqual(b.tray.map((p) => p?.id));
    expect(a.board.some((v) => v !== 0)).toBe(true);
    expect(a.over).toBe(false);
    expect(a.anyMoves()).toBe(true);
  });

  it('daily mode with warmStart stays deterministic per day seed', () => {
    const mk = () => new Game({ seed: 20260801, warmStart: true, queue: [] });
    expect(mk().board).toEqual(mk().board);
  });
});
