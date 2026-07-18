import type { Board } from './board';
import { emptyBoard, idx } from './board';
import type { Rng } from './rng';

/** Warm-start board (early-boredom fix, Block Blast-style).
 *
 *  An empty 9×9 needs ~15+ placements before the first clear — the dead
 *  stretch the publisher flagged. Every run now opens with 2-3 bottom rows
 *  partially pre-filled (5-7 of 9 cells), so the first clear lands within a
 *  few moves and the terrain gives early decisions meaning.
 *
 *  Safety: rows are never filled past 7/9 (the win stays with the player),
 *  columns collect at most 3 stray cells, and only rows 6-8 are touched, so
 *  no pre-completed lines and no early game-over pressure are possible.
 *  Fully deterministic from the provided RNG (daily stays fair). */
export function warmStartBoard(rng: Rng): Board {
  const board = emptyBoard();
  const rowCount = 2 + Math.floor(rng() * 2); // 2-3 rows
  const rows = [8, 7, 6].slice(0, rowCount);
  for (const r of rows) {
    const fillCount = 5 + Math.floor(rng() * 3); // 5-7 cells
    const cols = Array.from({ length: 9 }, (_, c) => c);
    for (let i = cols.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [cols[i], cols[j]] = [cols[j], cols[i]];
    }
    for (const c of cols.slice(0, fillCount)) {
      board[idx(r, c)] = 1 + Math.floor(rng() * 6);
    }
  }
  return board;
}
