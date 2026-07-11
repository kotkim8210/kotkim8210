import { describe, expect, it } from 'vitest';
import { Game, NOVA_FULL } from '../src/engine/game';
import { pieceByName } from '../src/engine/pieces';
import { emptyBoard, idx } from '../src/engine/board';
import { fillCells } from './helpers';

const dot = pieceByName('dot');

function rowOf8(board: number[], row: number): void {
  fillCells(board, Array.from({ length: 8 }, (_, c) => [row, c] as [number, number]));
}

describe('nova gauge (game-design §5)', () => {
  it('charges by cleared cell count and caps at 60', () => {
    const board = emptyBoard();
    rowOf8(board, 4);
    const game = new Game({ board, tray: [dot, dot, dot] });
    const move = game.placeAt(0, 4, 8)!;
    expect(move.clearedCells).toHaveLength(9);
    expect(game.gauge).toBe(9);
    expect(move.nova).toBe(false);

    game.gauge = 58;
    const b2 = game.board;
    rowOf8(b2, 6);
    game.tray[0] = dot;
    game.placeAt(0, 6, 8)!;
    expect(game.gauge).toBe(NOVA_FULL); // 58 + 9 capped at 60
  });

  it('a full gauge detonates on the NEXT clear, not the charging one', () => {
    const board = emptyBoard();
    rowOf8(board, 4);
    rowOf8(board, 5);
    const game = new Game({ board, tray: [dot, dot, dot] });
    game.gauge = 51;

    const charging = game.placeAt(0, 4, 8)!;
    expect(charging.nova).toBe(false);
    expect(game.gauge).toBe(60);
    expect(charging.gaugeFull).toBe(true);

    const boom = game.placeAt(1, 5, 8)!;
    expect(boom.nova).toBe(true);
    expect(game.gauge).toBe(0);
    // Turn score ×3: (1 place + 15 combo clear) × 3.
    expect(boom.gained).toBe(48);
  });

  it('explosion removes an extra 3×3 around the row×col intersection', () => {
    const board = emptyBoard();
    // Row 4 and column 8 both one short of full, intersecting at (4,8).
    rowOf8(board, 4);
    fillCells(
      board,
      Array.from({ length: 9 }, (_, r) => [r, 8] as [number, number]).filter(([r]) => r !== 4),
    );
    // Neighbours inside the blast zone but outside the cleared lines.
    fillCells(board, [
      [3, 7],
      [5, 7],
    ]);
    const game = new Game({ board, tray: [dot, dot, dot] });
    game.gauge = NOVA_FULL;

    const move = game.placeAt(0, 4, 8)!;
    expect(move.nova).toBe(true);
    expect(move.novaCenter).toEqual({ row: 4, col: 8 });
    expect(move.clearedCells).toHaveLength(17);
    expect(new Set(move.novaCells)).toEqual(new Set([idx(3, 7), idx(5, 7)]));
    expect(game.board[idx(3, 7)]).toBe(0);
    expect(game.board[idx(5, 7)]).toBe(0);
    // (place 1 + clear 50) × 3
    expect(move.gained).toBe(153);
    // Gauge resets and does not re-charge from the detonating clear.
    expect(game.gauge).toBe(0);
  });

  it('random seeded game runs to game over without breaking invariants', () => {
    const game = new Game({ seed: 12345 });
    let moves = 0;
    outer: while (!game.over && moves < 2000) {
      for (let t = 0; t < 3; t++) {
        const piece = game.tray[t];
        if (!piece) continue;
        for (let r = 0; r < 9; r++) {
          for (let c = 0; c < 9; c++) {
            if (game.canPlaceTray(t, r, c)) {
              const before = game.score;
              const move = game.placeAt(t, r, c)!;
              expect(move.gained).toBeGreaterThan(0);
              expect(game.score).toBe(before + move.gained);
              expect(game.gauge).toBeGreaterThanOrEqual(0);
              expect(game.gauge).toBeLessThanOrEqual(NOVA_FULL);
              moves++;
              continue outer;
            }
          }
        }
      }
      break;
    }
    expect(moves).toBeGreaterThan(10);
    expect(game.score).toBeGreaterThan(0);
  });
});
