import type { Game } from '../engine/game';
import { SIZE, idx } from '../engine/board';
import type { View } from './view';

export interface KeyboardCallbacks {
  getGame(): Game;
  tryPlace(trayIndex: number, row: number, col: number): boolean;
  onSelect(trayIndex: number | null): void;
  getSelected(): number | null;
  togglePause(): void;
  toggleMute(): void;
  invalidFeedback(): void;
  isLocked(): boolean;
}

/** Keyboard input (CLAUDE.md absolute rules): arrows move the cell cursor,
 *  1/2/3 pick a tray piece, Enter places, P pauses (ESC also works but is not
 *  the only binding), M mutes. */
export class KeyboardController {
  row = 4;
  col = 4;
  /** Cursor/ghost only shows after the first keyboard interaction. */
  active = false;

  constructor(
    private readonly view: View,
    private readonly cb: KeyboardCallbacks,
  ) {
    window.addEventListener('keydown', (e) => this.onKey(e));
  }

  private selectedIndex(): number {
    const sel = this.cb.getSelected();
    if (sel !== null) return sel;
    // default to the first placeable piece
    const game = this.cb.getGame();
    const placeable = game.placeablePieces();
    const first = placeable.findIndex(Boolean);
    return first >= 0 ? first : 0;
  }

  private clamp(): void {
    const game = this.cb.getGame();
    const piece = game.tray[this.selectedIndex()];
    const h = piece ? piece.shape.length : 1;
    const w = piece ? piece.shape[0].length : 1;
    this.row = Math.max(0, Math.min(SIZE - h, this.row));
    this.col = Math.max(0, Math.min(SIZE - w, this.col));
  }

  /** Repaint cursor + ghost (also called after re-renders). */
  refresh(): void {
    if (!this.active || this.cb.isLocked()) {
      this.view.setCursor(null);
      return;
    }
    const game = this.cb.getGame();
    const sel = this.selectedIndex();
    const piece = game.tray[sel];
    this.clamp();
    this.view.setCursor(idx(this.row, this.col));
    if (!piece) {
      this.view.clearGhost();
      return;
    }
    const cells: number[] = [];
    for (let r = 0; r < piece.shape.length; r++) {
      for (let c = 0; c < piece.shape[r].length; c++) {
        if (piece.shape[r][c]) cells.push(idx(this.row + r, this.col + c));
      }
    }
    const ok = game.canPlaceTray(sel, this.row, this.col);
    this.view.setGhost(cells, ok);
    if (ok) this.view.setGhostColor(piece.color);
  }

  hide(): void {
    this.active = false;
    this.view.setCursor(null);
    this.view.clearGhost();
  }

  private onKey(e: KeyboardEvent): void {
    const { code } = e;
    // Pause / mute always respond (P is required; ESC is a bonus binding).
    if (code === 'KeyP' || code === 'Escape') {
      e.preventDefault();
      this.cb.togglePause();
      return;
    }
    if (code === 'KeyM') {
      e.preventDefault();
      this.cb.toggleMute();
      return;
    }
    if (this.cb.isLocked()) return;

    const move = (dr: number, dc: number) => {
      e.preventDefault();
      this.active = true;
      this.row += dr;
      this.col += dc;
      this.refresh();
    };

    switch (code) {
      case 'ArrowLeft':
        move(0, -1);
        break;
      case 'ArrowRight':
        move(0, 1);
        break;
      case 'ArrowUp':
        move(-1, 0);
        break;
      case 'ArrowDown':
        move(1, 0);
        break;
      case 'Digit1':
      case 'Digit2':
      case 'Digit3':
      case 'Numpad1':
      case 'Numpad2':
      case 'Numpad3': {
        e.preventDefault();
        this.active = true;
        const i = Number(code.slice(-1)) - 1;
        if (this.cb.getGame().tray[i]) this.cb.onSelect(i);
        this.refresh();
        break;
      }
      case 'Enter':
      case 'Space': {
        if (!this.active) return;
        e.preventDefault();
        const sel = this.selectedIndex();
        this.clamp();
        if (!this.cb.tryPlace(sel, this.row, this.col)) {
          this.cb.invalidFeedback();
        }
        break;
      }
      default:
        break;
    }
  }
}
