import { describe, expect, it } from 'vitest';
import { Game, NOVA_FULL } from '../src/engine/game';
import { goldenBoard, goldenTray, GOLDEN_PRECHARGE, GOLDEN_TARGET } from '../src/engine/golden';
import { idx } from '../src/engine/board';

/** game-design.md §11 — mandated vitest: with the preset board and the fixed
 *  tray, dropping v2 at (7,8) is a double clear removing exactly 17 cells. */
describe('golden first move (game-design §11)', () => {
  it('preset + fixed tray: v2 @ (7,8) removes exactly 17 cells', () => {
    const game = new Game({
      board: goldenBoard(),
      tray: goldenTray(),
      gauge: GOLDEN_PRECHARGE,
    });
    expect(game.tray[0]?.name).toBe('v2');
    expect(game.tray[1]?.name).toBe('sq2');
    expect(game.tray[2]?.name).toBe('l3');

    const move = game.placeAt(0, GOLDEN_TARGET.row, GOLDEN_TARGET.col);
    expect(move).not.toBeNull();
    expect(move!.clearedRows).toEqual([7]);
    expect(move!.clearedCols).toEqual([8]);
    expect(move!.clearedCells).toHaveLength(17);
    expect(move!.combo).toBe(1);
    // double clear: 2 placed + round(10 × 2 × 2.5) = 52, and the board is
    // emptied so the §12 perfect-clear bonus lands on the very first move
    expect(move!.perfectClear).toBe(true);
    expect(move!.gained).toBe(1052);
  });

  it('pre-charges the nova gauge to 50% and keeps charging normally', () => {
    expect(GOLDEN_PRECHARGE).toBe(NOVA_FULL / 2);
    const game = new Game({
      board: goldenBoard(),
      tray: goldenTray(),
      gauge: GOLDEN_PRECHARGE,
    });
    expect(game.gauge).toBe(30);
    const move = game.placeAt(0, GOLDEN_TARGET.row, GOLDEN_TARGET.col)!;
    expect(move.nova).toBe(false); // gauge was not full yet
    expect(game.gauge).toBe(30 + 17); // charged by cleared cells
  });

  it('preset board has no pre-completed lines and no stray cells', () => {
    const board = goldenBoard();
    // row 7 misses only (7,8); column 8 misses (7,8) and (8,8)
    for (let c = 0; c < 8; c++) expect(board[idx(7, c)]).toBeGreaterThan(0);
    expect(board[idx(7, 8)]).toBe(0);
    for (let r = 0; r < 7; r++) expect(board[idx(r, 8)]).toBeGreaterThan(0);
    expect(board[idx(8, 8)]).toBe(0);
    const filled = board.filter((v) => v > 0).length;
    expect(filled).toBe(8 + 7);
  });
});
