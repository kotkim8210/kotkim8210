import type { Board } from './board';
import { emptyBoard, idx, SIZE } from './board';
import type { PieceDef } from './pieces';
import { pieceByName } from './pieces';

/** game-design.md §11 — golden first move (first-run hooking script).
 *
 *  Preset board + fixed tray [v2, sq2, l3]: dropping v2 vertically at (7,8)
 *  completes row 7 AND column 8 in one move — a 17-cell double clear
 *  (9 + 9 − 1 shared intersection).
 *
 *  Note on the spec wording: §11 says "row 7 filled except (7,8), row 8
 *  filled except (8,8)" — two full ROWS would remove 18 cells, but the same
 *  section states the mandated result twice as 17 cells, which is only
 *  possible with a row×column intersection. We therefore read the second
 *  line as COLUMN 8 (filled except (7,8) and (8,8)); the v2 move then yields
 *  exactly the specified 17-cell double clear.
 */

export function goldenBoard(): Board {
  const board = emptyBoard();
  // row 7 filled except (7,8) — gem colors varied for a lively first frame
  for (let c = 0; c < SIZE - 1; c++) board[idx(7, c)] = (c % 6) + 1;
  // column 8 filled except (7,8) and (8,8)
  for (let r = 0; r < SIZE - 2; r++) board[idx(r, 8)] = (r % 6) + 1;
  return board;
}

export function goldenTray(): PieceDef[] {
  return [pieceByName('v2'), pieceByName('sq2'), pieceByName('l3')];
}

/** The double-clear drop target for v2 (top-left anchor). */
export const GOLDEN_TARGET = { row: 7, col: 8 };

/** §11: nova gauge starts pre-charged at 50% ("bonus charge ⚡"). */
export const GOLDEN_PRECHARGE = 30;
