import type { Board } from './board';
import { hasAnyPlacement } from './board';
import type { PieceDef } from './pieces';
import type { Rng } from './rng';

/** game-design.md §2 — weighted spawn from the 19-piece pool. */
export function drawWeighted(pieces: PieceDef[], rng: Rng): PieceDef {
  let total = 0;
  for (const p of pieces) total += p.weight;
  let roll = rng() * total;
  for (const p of pieces) {
    roll -= p.weight;
    if (roll < 0) return p;
  }
  return pieces[pieces.length - 1];
}

export function sameCombination(a: number[], b: number[]): boolean {
  if (a.length !== b.length) return false;
  const sa = [...a].sort((x, y) => x - y);
  const sb = [...b].sort((x, y) => x - y);
  return sa.every((v, i) => v === sb[i]);
}

export const MAX_REDRAWS = 20;

export interface RefillOptions {
  pieces: PieceDef[];
  rng: Rng;
  board: Board;
  /** Piece ids of the previous refill (the exact same 3-piece combination is
   *  forbidden). Pass null for the very first fill. */
  prevIds: number[] | null;
  count?: number;
}

/** Refill the tray: draw `count` weighted pieces from a single RNG stream.
 *  Constraints (game-design.md §2): the multiset of ids must differ from the
 *  previous refill, and at least one piece must be placeable on the current
 *  board. The whole set is redrawn up to MAX_REDRAWS times from the same RNG
 *  stream; if no draw satisfies the constraints the last draw is kept (a tray
 *  with no placeable piece then simply triggers game over). */
export function refillTray(opts: RefillOptions): PieceDef[] {
  const { pieces, rng, board, prevIds } = opts;
  const count = opts.count ?? 3;
  let draw: PieceDef[] = [];
  for (let attempt = 0; attempt <= MAX_REDRAWS; attempt++) {
    draw = [];
    for (let i = 0; i < count; i++) draw.push(drawWeighted(pieces, rng));
    const ids = draw.map((p) => p.id);
    if (prevIds && sameCombination(ids, prevIds)) continue;
    if (!draw.some((p) => hasAnyPlacement(board, p.shape))) continue;
    return draw;
  }
  return draw;
}
