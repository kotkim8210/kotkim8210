import type { Board } from './board';
import {
  canPlace,
  emptyBoard,
  fullLines,
  hasAnyPlacement,
  isBoardEmpty,
  lineCells,
  novaBlastCells,
  placeOnBoard,
  removeCells,
  rowOf,
  colOf,
  idx,
  SIZE,
} from './board';
import { refillTray } from './bag';
import type { PieceDef } from './pieces';
import { PIECES, TRAY_SIZE } from './pieces';
import { clearScore, placementScore } from './scoring';
import type { Rng } from './rng';
import { mulberry32 } from './rng';

/** game-design.md §5 — nova gauge is full at 60 cleared cells. */
export const NOVA_FULL = 60;

export interface MoveResult {
  /** Cells filled by the placement. */
  placed: number[];
  clearedRows: number[];
  clearedCols: number[];
  /** Cells removed by line clears (intersections counted once). */
  clearedCells: number[];
  /** True when a nova explosion fired on this move. */
  nova: boolean;
  novaCenter: { row: number; col: number } | null;
  /** Extra cells removed by the 3×3 blast (beyond the line clears). */
  novaCells: number[];
  placeScore: number;
  clearScorePart: number;
  /** Total score gained this move (×3 already applied on a nova turn). */
  gained: number;
  /** Combo counter after this move (0 when the placement cleared nothing). */
  combo: number;
  gauge: number;
  gaugeFull: boolean;
  newBest: boolean;
  perfectClear: boolean;
  refilled: boolean;
  gameOver: boolean;
}

export interface GameOptions {
  seed?: number;
  rng?: Rng;
  pieces?: PieceDef[];
  best?: number;
  /** Preset board / tray (used by tests and the Phase 2 golden first move). */
  board?: Board;
  tray?: (PieceDef | null)[];
}

export class Game {
  board: Board;
  tray: (PieceDef | null)[];
  score = 0;
  best: number;
  combo = 0;
  gauge = 0;
  linesTotal = 0;
  novaCount = 0;
  maxCombo = 0;
  over = false;
  private readonly rng: Rng;
  private readonly pieces: PieceDef[];
  private lastRefillIds: number[] | null = null;
  private bestBeaten = false;

  constructor(opts: GameOptions = {}) {
    this.rng = opts.rng ?? mulberry32(opts.seed ?? 1);
    this.pieces = opts.pieces ?? PIECES;
    this.best = opts.best ?? 0;
    this.board = opts.board ? [...opts.board] : emptyBoard();
    if (opts.tray) {
      this.tray = [...opts.tray];
      this.lastRefillIds = opts.tray.filter((p): p is PieceDef => !!p).map((p) => p.id);
    } else {
      this.tray = this.refill();
    }
    this.over = !this.anyMoves();
  }

  private refill(): PieceDef[] {
    const draw = refillTray({
      pieces: this.pieces,
      rng: this.rng,
      board: this.board,
      prevIds: this.lastRefillIds,
      count: TRAY_SIZE,
    });
    this.lastRefillIds = draw.map((p) => p.id);
    return draw;
  }

  gaugeIsFull(): boolean {
    return this.gauge >= NOVA_FULL;
  }

  canPlaceTray(trayIndex: number, row: number, col: number): boolean {
    const piece = this.tray[trayIndex];
    return !!piece && canPlace(this.board, piece.shape, row, col);
  }

  /** True while at least one tray piece has a legal placement. */
  anyMoves(): boolean {
    return this.tray.some((p) => p && hasAnyPlacement(this.board, p.shape));
  }

  placeablePieces(): boolean[] {
    return this.tray.map((p) => !!p && hasAnyPlacement(this.board, p.shape));
  }

  /** game-design.md §5 — blast center: the row×col intersection when both line
   *  kinds cleared; otherwise the cleared line at the placed piece's center. */
  private novaCenter(
    rows: number[],
    cols: number[],
    piece: PieceDef,
    row: number,
    col: number,
  ): { row: number; col: number } {
    const midR = Math.min(SIZE - 1, row + Math.floor((piece.shape.length - 1) / 2));
    const midC = Math.min(SIZE - 1, col + Math.floor((piece.shape[0].length - 1) / 2));
    if (rows.length && cols.length) return { row: rows[0], col: cols[0] };
    if (rows.length) return { row: rows[0], col: midC };
    return { row: midR, col: cols[0] };
  }

  /** Execute a move. Returns null when the placement is illegal. */
  placeAt(trayIndex: number, row: number, col: number): MoveResult | null {
    if (this.over) return null;
    const piece = this.tray[trayIndex];
    if (!piece || !canPlace(this.board, piece.shape, row, col)) return null;

    const placed = placeOnBoard(this.board, piece, row, col);
    const placeScore = placementScore(piece.cells);

    const { rows, cols } = fullLines(this.board);
    const lines = rows.length + cols.length;
    const cleared = lines > 0 ? lineCells(rows, cols) : new Set<number>();
    const gaugeWasFull = this.gaugeIsFull();

    let clearPart = 0;
    let nova = false;
    let novaCenter: { row: number; col: number } | null = null;
    let novaCells: number[] = [];

    if (lines > 0) {
      clearPart = clearScore(lines, this.combo);
      this.combo += 1;
      this.maxCombo = Math.max(this.maxCombo, this.combo);
      this.linesTotal += lines;
      removeCells(this.board, cleared);
      if (gaugeWasFull) {
        // §5: with a full gauge, the next clear detonates — 3×3 extra removal,
        // the turn's score ×3, gauge back to 0.
        nova = true;
        this.novaCount += 1;
        novaCenter = this.novaCenter(rows, cols, piece, row, col);
        novaCells = novaBlastCells(this.board, novaCenter.row, novaCenter.col);
        removeCells(this.board, novaCells);
        this.gauge = 0;
      } else {
        this.gauge = Math.min(NOVA_FULL, this.gauge + cleared.size);
      }
    } else {
      this.combo = 0;
    }

    let gained = placeScore + clearPart;
    if (nova) gained *= 3;
    this.score += gained;

    let newBest = false;
    if (this.score > this.best) {
      this.best = this.score;
      if (!this.bestBeaten) {
        this.bestBeaten = true;
        newBest = true;
      }
    }

    this.tray[trayIndex] = null;
    let refilled = false;
    if (this.tray.every((p) => p === null)) {
      this.tray = this.refill();
      refilled = true;
    }

    this.over = !this.anyMoves();

    return {
      placed,
      clearedRows: rows,
      clearedCols: cols,
      clearedCells: [...cleared],
      nova,
      novaCenter,
      novaCells,
      placeScore,
      clearScorePart: clearPart,
      gained,
      combo: this.combo,
      gauge: this.gauge,
      gaugeFull: this.gaugeIsFull(),
      newBest,
      perfectClear: lines > 0 && isBoardEmpty(this.board),
      refilled,
      gameOver: this.over,
    };
  }
}

export { rowOf, colOf, idx };
