import { describe, expect, it } from 'vitest';
import { clearScore, placementScore, simultaneityMultiplier } from '../src/engine/scoring';
import { Game } from '../src/engine/game';
import { pieceByName } from '../src/engine/pieces';
import { emptyBoard } from '../src/engine/board';
import { fillCells } from './helpers';

describe('scoring (game-design §4)', () => {
  it('placement scores 1 per cell', () => {
    expect(placementScore(1)).toBe(1);
    expect(placementScore(9)).toBe(9);
  });

  it('simultaneity multiplier: ×1 / ×2.5 / ×4', () => {
    expect(simultaneityMultiplier(1)).toBe(1);
    expect(simultaneityMultiplier(2)).toBe(2.5);
    expect(simultaneityMultiplier(3)).toBe(4);
    expect(simultaneityMultiplier(5)).toBe(4);
  });

  it('clear score = 10 × lines × multiplier × combo factor, rounded', () => {
    expect(clearScore(1, 0)).toBe(10);
    expect(clearScore(2, 0)).toBe(50);
    expect(clearScore(3, 0)).toBe(120);
    expect(clearScore(1, 1)).toBe(15); // 2nd consecutive clear ×1.5
    expect(clearScore(1, 3)).toBe(25); // 10 × 2.5
    expect(clearScore(2, 1)).toBe(75);
  });

  it('combo builds on consecutive clears and resets on a quiet placement', () => {
    // Rows 4 and 5 each filled up to col 7 — two dots clear them in sequence.
    const board = emptyBoard();
    fillCells(board, Array.from({ length: 8 }, (_, c) => [4, c] as [number, number]));
    fillCells(board, Array.from({ length: 8 }, (_, c) => [5, c] as [number, number]));
    const dot = pieceByName('dot');
    const game = new Game({ board, tray: [dot, dot, dot] });

    const first = game.placeAt(0, 4, 8)!;
    expect(first.combo).toBe(1);
    expect(first.gained).toBe(1 + 10);

    const second = game.placeAt(1, 5, 8)!;
    expect(second.combo).toBe(2);
    expect(second.gained).toBe(1 + 15); // ×1.5 combo factor

    const quiet = game.placeAt(2, 0, 0)!;
    expect(quiet.combo).toBe(0);
    expect(quiet.gained).toBe(1);
  });

  it('best score updates live', () => {
    const board = emptyBoard();
    fillCells(board, Array.from({ length: 8 }, (_, c) => [4, c] as [number, number]));
    const dot = pieceByName('dot');
    const game = new Game({ board, tray: [dot, dot, dot], best: 5 });
    const move = game.placeAt(0, 4, 8)!;
    expect(move.newBest).toBe(true);
    expect(game.best).toBe(11);
  });
});
