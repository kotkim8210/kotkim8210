import type { Game } from '../engine/game';
import { SIZE, idx } from '../engine/board';
import { isCoarsePointer } from '../core/device';
import type { View } from './view';
import { renderPieceGrid } from './view';

export interface DragCallbacks {
  getGame(): Game;
  /** Returns true when the move was accepted. */
  tryPlace(trayIndex: number, row: number, col: number): boolean;
  /** Tap-tap selection changed (null = deselected). */
  onSelect(trayIndex: number | null): void;
  getSelected(): number | null;
  invalidFeedback(): void;
  isLocked(): boolean;
  /** Piece lifted off the tray (cute pickup blip). */
  onPickup(): void;
  /** Ghost snapped onto a new valid anchor (tiny tick). */
  onSnap(): void;
}

const TAP_SLOP_PX = 8;

/** Pointer-event controller: one code path covers mouse drag and touch drag;
 *  short presses fall through to tap-tap (select piece → tap board). */
export class DragController {
  private pointerId: number | null = null;
  private trayIndex = -1;
  private startX = 0;
  private startY = 0;
  private dragging = false;
  private clone: HTMLElement | null = null;
  private cloneW = 0;
  private cloneH = 0;
  private anchor: { row: number; col: number } | null = null;
  private anchorValid = false;

  constructor(
    private readonly view: View,
    private readonly cb: DragCallbacks,
  ) {
    view.slots.forEach((slot, i) => {
      slot.addEventListener('pointerdown', (e) => this.onDown(e, i));
    });
    window.addEventListener('pointermove', (e) => this.onMove(e));
    window.addEventListener('pointerup', (e) => this.onUp(e));
    window.addEventListener('pointercancel', (e) => this.onCancel(e));
    view.boardEl.addEventListener('pointerup', (e) => this.onBoardTap(e));
    for (const node of [view.boardEl, ...view.slots]) {
      node.addEventListener('contextmenu', (e) => e.preventDefault());
    }
  }

  private onDown(e: PointerEvent, trayIndex: number): void {
    if (this.cb.isLocked() || this.pointerId !== null) return;
    const game = this.cb.getGame();
    if (!game.tray[trayIndex]) return;
    this.pointerId = e.pointerId;
    this.trayIndex = trayIndex;
    this.startX = e.clientX;
    this.startY = e.clientY;
    this.dragging = false;
    e.preventDefault();
  }

  private beginDrag(): void {
    const game = this.cb.getGame();
    const piece = game.tray[this.trayIndex];
    if (!piece) return;
    this.dragging = true;
    // deselect first — this re-renders the tray, which would wipe classes
    // added to the slot afterwards
    this.cb.onSelect(null);
    const { cell } = this.view.boardMetrics();
    const gap = 3;
    const w = piece.shape[0].length;
    const h = piece.shape.length;
    this.cloneW = w * cell + (w - 1) * gap;
    this.cloneH = h * cell + (h - 1) * gap;
    const clone = renderPieceGrid(piece, cell, gap);
    clone.classList.add('drag-clone', 'pop-in');
    document.body.appendChild(clone);
    this.clone = clone;
    this.view.slots[this.trayIndex].classList.add('drag-src');
    this.cb.onPickup();
  }

  private lastTrail = 0;

  /** Sparkle trail behind the dragged piece (skipped in lite/reduced modes). */
  private dropTrail(x: number, y: number): void {
    const doc = document.documentElement;
    if (doc.classList.contains('fx-lite') || doc.classList.contains('reduced-motion')) return;
    const now = performance.now();
    if (now - this.lastTrail < 90) return;
    this.lastTrail = now;
    const star = document.createElement('div');
    star.className = 'trail-star';
    star.textContent = '✦';
    star.style.color = 'var(--color-nova-hi)';
    star.style.left = `${x + (Math.random() * 14 - 7)}px`;
    star.style.top = `${y + 6}px`;
    document.body.appendChild(star);
    setTimeout(() => star.remove(), 600);
  }

  private onMove(e: PointerEvent): void {
    if (e.pointerId !== this.pointerId) return;
    if (!this.dragging) {
      const dist = Math.hypot(e.clientX - this.startX, e.clientY - this.startY);
      if (dist < TAP_SLOP_PX) return;
      this.beginDrag();
      if (!this.dragging) return;
    }
    const lift = isCoarsePointer() ? 48 : 10;
    const left = e.clientX - this.cloneW / 2;
    const top = e.clientY - this.cloneH - lift;
    if (this.clone) this.clone.style.transform = `translate(${left}px, ${top}px)`;
    this.dropTrail(left + this.cloneW / 2, top + this.cloneH);
    this.updateGhost(left, top);
  }

  private updateGhost(cloneLeft: number, cloneTop: number): void {
    const game = this.cb.getGame();
    const piece = game.tray[this.trayIndex];
    if (!piece) return;
    const m = this.view.boardMetrics();
    const row = Math.round((cloneTop - m.top) / m.pitch);
    const col = Math.round((cloneLeft - m.left) / m.pitch);
    const h = piece.shape.length;
    const w = piece.shape[0].length;
    if (row < -1 || col < -1 || row > SIZE - h + 1 || col > SIZE - w + 1) {
      // far off the board — no ghost, dropping returns the piece
      this.anchor = null;
      this.view.clearGhost();
      this.clone?.classList.remove('bad');
      return;
    }
    const r = Math.max(0, Math.min(SIZE - h, row));
    const c = Math.max(0, Math.min(SIZE - w, col));
    const moved = !this.anchor || this.anchor.row !== r || this.anchor.col !== c;
    this.anchor = { row: r, col: c };
    this.anchorValid = game.canPlaceTray(this.trayIndex, r, c);
    if (moved && this.anchorValid) this.cb.onSnap();
    const cells: number[] = [];
    for (let sr = 0; sr < h; sr++) {
      for (let sc = 0; sc < w; sc++) {
        if (piece.shape[sr][sc]) cells.push(idx(r + sr, c + sc));
      }
    }
    this.view.setGhost(cells, this.anchorValid);
    if (this.anchorValid) this.view.setGhostColor(piece.color);
    this.clone?.classList.toggle('bad', !this.anchorValid);
  }

  private onUp(e: PointerEvent): void {
    if (e.pointerId !== this.pointerId) return;
    const wasDragging = this.dragging;
    const trayIndex = this.trayIndex;
    const anchor = this.anchor;
    const anchorValid = this.anchorValid;
    this.cleanup();

    if (wasDragging) {
      if (anchor && anchorValid) {
        this.cb.tryPlace(trayIndex, anchor.row, anchor.col);
      } else if (anchor) {
        this.cb.invalidFeedback();
      }
      return;
    }
    // Short press on a slot = tap-tap selection toggle.
    const game = this.cb.getGame();
    if (game.tray[trayIndex]) {
      const next = this.cb.getSelected() === trayIndex ? null : trayIndex;
      this.cb.onSelect(next);
    }
  }

  private onCancel(e: PointerEvent): void {
    if (e.pointerId !== this.pointerId) return;
    this.cleanup();
  }

  private cleanup(): void {
    this.clone?.remove();
    this.clone = null;
    if (this.trayIndex >= 0) this.view.slots[this.trayIndex]?.classList.remove('drag-src');
    this.view.clearGhost();
    this.pointerId = null;
    this.trayIndex = -1;
    this.dragging = false;
    this.anchor = null;
    this.anchorValid = false;
  }

  /** Tap-tap second half: tap a board cell with a piece selected. The piece is
   *  anchored so its footprint centers on the tapped cell (clamped in-bounds). */
  private onBoardTap(e: PointerEvent): void {
    if (this.cb.isLocked() || this.dragging || this.pointerId !== null) return;
    const selected = this.cb.getSelected();
    if (selected === null) return;
    const game = this.cb.getGame();
    const piece = game.tray[selected];
    if (!piece) return;
    const m = this.view.boardMetrics();
    const col = Math.floor((e.clientX - m.left) / m.pitch);
    const row = Math.floor((e.clientY - m.top) / m.pitch);
    if (row < 0 || row >= SIZE || col < 0 || col >= SIZE) return;
    const h = piece.shape.length;
    const w = piece.shape[0].length;
    const r = Math.max(0, Math.min(SIZE - h, row - Math.floor((h - 1) / 2)));
    const c = Math.max(0, Math.min(SIZE - w, col - Math.floor((w - 1) / 2)));
    if (!this.cb.tryPlace(selected, r, c)) {
      // brief invalid footprint flash
      const cells: number[] = [];
      for (let sr = 0; sr < h; sr++) {
        for (let sc = 0; sc < w; sc++) {
          if (piece.shape[sr][sc]) cells.push(idx(r + sr, c + sc));
        }
      }
      this.view.setGhost(cells, false);
      setTimeout(() => this.view.clearGhost(), 220);
      this.cb.invalidFeedback();
    }
  }
}
