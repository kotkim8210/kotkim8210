import { describe, expect, it } from 'vitest';
import { Game } from '../src/engine/game';
import { pieceByName } from '../src/engine/pieces';
import { emptyBoard, idx, isBoardEmpty } from '../src/engine/board';
import { boardFrom, fillCells } from './helpers';

/** game-design.md §3 — the three mandated vitest cases. */
describe('line clear judgement (game-design §3)', () => {
  it('case ①: dot completes a row of 8 → 9 cells removed', () => {
    const board = emptyBoard();
    fillCells(board, Array.from({ length: 8 }, (_, c) => [4, c] as [number, number]));
    const game = new Game({
      board,
      tray: [pieceByName('dot'), pieceByName('i2'), pieceByName('sq2')],
    });

    const move = game.placeAt(0, 4, 8);
    expect(move).not.toBeNull();
    expect(move!.clearedRows).toEqual([4]);
    expect(move!.clearedCols).toEqual([]);
    expect(move!.clearedCells).toHaveLength(9);
    expect(move!.gained).toBe(1 + 10); // 1 cell placed + 10 per line ×1
    expect(game.board[idx(4, 0)]).toBe(0);
  });

  it('case ②: row + column simultaneously, intersection removed once → 17 cells', () => {
    const board = emptyBoard();
    // Row 4 filled except (4,8); column 8 filled except (4,8).
    fillCells(board, Array.from({ length: 8 }, (_, c) => [4, c] as [number, number]));
    fillCells(
      board,
      Array.from({ length: 9 }, (_, r) => [r, 8] as [number, number]).filter(([r]) => r !== 4),
    );
    const game = new Game({
      board,
      tray: [pieceByName('dot'), pieceByName('i2'), pieceByName('sq2')],
    });

    const move = game.placeAt(0, 4, 8);
    expect(move).not.toBeNull();
    expect(move!.clearedRows).toEqual([4]);
    expect(move!.clearedCols).toEqual([8]);
    // 9 + 9 − 1 shared intersection cell = 17
    expect(move!.clearedCells).toHaveLength(17);
    // 1 placed cell + round(10 × 2 lines × 2.5) = 51
    expect(move!.gained).toBe(51);
    expect(isBoardEmpty(game.board)).toBe(true);
    expect(move!.perfectClear).toBe(true);
  });

  it('case ③: no tray piece has a legal placement → game over', () => {
    // Empty cells: all of row 0, all of column 0, and a single 3×3 hole at
    // rows 3-5 × cols 3-5. No initial full lines.
    const rows = [
      '.........',
      '.########',
      '.########',
      '.##...###',
      '.##...###',
      '.##...###',
      '.########',
      '.########',
      '.########',
    ];
    const sq3 = pieceByName('sq3');

    // The only 3×3 spot is the hole; once used, the two remaining sq3 have
    // nowhere to go → game over is reported on the move.
    const game = new Game({ board: boardFrom(rows), tray: [sq3, sq3, sq3] });
    expect(game.over).toBe(false);
    const move = game.placeAt(0, 3, 3);
    expect(move).not.toBeNull();
    expect(move!.clearedCells).toHaveLength(0);
    expect(move!.gameOver).toBe(true);
    expect(game.over).toBe(true);

    // And a board with no room at all is over from the start.
    const jammed = boardFrom(rows.map((r, i) => (i === 3 ? '.##.#.###' : r)));
    const dead = new Game({ board: jammed, tray: [sq3, sq3, sq3] });
    expect(dead.over).toBe(true);
  });
});
