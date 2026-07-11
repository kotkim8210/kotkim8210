import type { PieceDef } from './pieces';
import { GRID } from './pieces';

export const SIZE = GRID; // 9

/** Flat 81-cell board. 0 = empty, 1..6 = gem color index + 1. */
export type Board = number[];

export function emptyBoard(): Board {
  return new Array<number>(SIZE * SIZE).fill(0);
}

export function idx(row: number, col: number): number {
  return row * SIZE + col;
}

export function rowOf(i: number): number {
  return Math.floor(i / SIZE);
}

export function colOf(i: number): number {
  return i % SIZE;
}

export function inBounds(row: number, col: number): boolean {
  return row >= 0 && row < SIZE && col >= 0 && col < SIZE;
}

export function shapeSize(shape: number[][]): { h: number; w: number } {
  return { h: shape.length, w: shape[0].length };
}

/** True if the shape fits with its top-left at (row, col) on empty cells only. */
export function canPlace(board: Board, shape: number[][], row: number, col: number): boolean {
  for (let r = 0; r < shape.length; r++) {
    for (let c = 0; c < shape[r].length; c++) {
      if (!shape[r][c]) continue;
      const br = row + r;
      const bc = col + c;
      if (!inBounds(br, bc) || board[idx(br, bc)] !== 0) return false;
    }
  }
  return true;
}

/** Writes the piece onto the board. Caller must have checked canPlace.
 *  Returns the filled cell indices. */
export function placeOnBoard(board: Board, piece: PieceDef, row: number, col: number): number[] {
  const filled: number[] = [];
  for (let r = 0; r < piece.shape.length; r++) {
    for (let c = 0; c < piece.shape[r].length; c++) {
      if (!piece.shape[r][c]) continue;
      const i = idx(row + r, col + c);
      board[i] = piece.color + 1;
      filled.push(i);
    }
  }
  return filled;
}

/** Fully-filled rows and columns (judged simultaneously). */
export function fullLines(board: Board): { rows: number[]; cols: number[] } {
  const rows: number[] = [];
  const cols: number[] = [];
  for (let r = 0; r < SIZE; r++) {
    let full = true;
    for (let c = 0; c < SIZE; c++) {
      if (board[idx(r, c)] === 0) {
        full = false;
        break;
      }
    }
    if (full) rows.push(r);
  }
  for (let c = 0; c < SIZE; c++) {
    let full = true;
    for (let r = 0; r < SIZE; r++) {
      if (board[idx(r, c)] === 0) {
        full = false;
        break;
      }
    }
    if (full) cols.push(c);
  }
  return { rows, cols };
}

/** Union of cells covered by the given lines — an intersection cell counts once. */
export function lineCells(rows: number[], cols: number[]): Set<number> {
  const cells = new Set<number>();
  for (const r of rows) for (let c = 0; c < SIZE; c++) cells.add(idx(r, c));
  for (const c of cols) for (let r = 0; r < SIZE; r++) cells.add(idx(r, c));
  return cells;
}

export function removeCells(board: Board, cells: Iterable<number>): void {
  for (const i of cells) board[i] = 0;
}

/** True if the shape can be placed anywhere on the board. */
export function hasAnyPlacement(board: Board, shape: number[][]): boolean {
  const { h, w } = shapeSize(shape);
  for (let r = 0; r <= SIZE - h; r++) {
    for (let c = 0; c <= SIZE - w; c++) {
      if (canPlace(board, shape, r, c)) return true;
    }
  }
  return false;
}

/** 3×3 nova blast footprint centered at (row, col), clamped to the board.
 *  Returns only currently-occupied cells. */
export function novaBlastCells(board: Board, row: number, col: number): number[] {
  const out: number[] = [];
  for (let r = row - 1; r <= row + 1; r++) {
    for (let c = col - 1; c <= col + 1; c++) {
      if (!inBounds(r, c)) continue;
      const i = idx(r, c);
      if (board[i] !== 0) out.push(i);
    }
  }
  return out;
}

export function isBoardEmpty(board: Board): boolean {
  return board.every((v) => v === 0);
}
