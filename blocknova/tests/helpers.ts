import type { Board } from '../src/engine/board';
import { emptyBoard, idx, SIZE } from '../src/engine/board';

/** Build a board from 9 strings of 9 chars — '#' filled, '.' empty. */
export function boardFrom(rows: string[]): Board {
  if (rows.length !== SIZE) throw new Error('need 9 rows');
  const b = emptyBoard();
  rows.forEach((row, r) => {
    if (row.length !== SIZE) throw new Error(`row ${r} needs 9 chars`);
    for (let c = 0; c < SIZE; c++) {
      if (row[c] === '#') b[idx(r, c)] = 1;
    }
  });
  return b;
}

export function fillCells(board: Board, cells: [number, number][]): Board {
  for (const [r, c] of cells) board[idx(r, c)] = 1;
  return board;
}
