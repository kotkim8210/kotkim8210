import type { Board } from '../engine/board';
import { SIZE, rowOf, colOf } from '../engine/board';
import type { PieceDef } from '../engine/pieces';
import { NOVA_FULL } from '../engine/game';
import { t } from '../core/i18n';
import { prefersReducedMotion } from '../core/device';
import { mulberry32 } from '../engine/rng';

export const GEM_VARS = ['--gem-0', '--gem-1', '--gem-2', '--gem-3', '--gem-4', '--gem-5'];

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = '',
  text = '',
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function gemVar(colorIndex: number): string {
  return `var(${GEM_VARS[colorIndex % GEM_VARS.length]})`;
}

/** Deterministic starfield: two box-shadow layers (ui-spec §1). */
function makeStars(count: number, sizeClass: 'a' | 'b'): HTMLElement {
  const rng = mulberry32(sizeClass === 'a' ? 11 : 22);
  const shadows: string[] = [];
  for (let i = 0; i < count; i++) {
    const x = Math.round(rng() * 100);
    const y = Math.round(rng() * 150);
    const alpha = (0.25 + rng() * 0.5).toFixed(2);
    shadows.push(`${x}vw ${y}vh 0 0 rgba(237,234,247,${alpha})`);
  }
  const star = el('div', `stars ${sizeClass}`);
  star.style.boxShadow = shadows.join(',');
  return star;
}

/** Renders a piece as a mini grid. cellPx=0 means tray scale. */
export function renderPieceGrid(piece: PieceDef, cellPx: number, gapPx = 2): HTMLElement {
  const grid = el('div', 'mini');
  const h = piece.shape.length;
  const w = piece.shape[0].length;
  grid.style.gridTemplateColumns = `repeat(${w}, ${cellPx}px)`;
  grid.style.gridTemplateRows = `repeat(${h}, ${cellPx}px)`;
  grid.style.gap = `${gapPx}px`;
  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      const cell = el('div', piece.shape[r][c] ? 'mini-cell gem' : 'mini-cell');
      if (piece.shape[r][c]) cell.style.setProperty('--gem', gemVar(piece.color));
      grid.appendChild(cell);
    }
  }
  return grid;
}

export interface GameOverData {
  score: number;
  best: number;
  isNewBest: boolean;
}

export class View {
  readonly cells: HTMLElement[] = [];
  readonly slots: HTMLElement[] = [];
  boardEl!: HTMLElement;
  appCol!: HTMLElement;
  private scoreEl!: HTMLElement;
  private bestEl!: HTMLElement;
  private comboEl!: HTMLElement;
  private novaTrack!: HTMLElement;
  private novaFill!: HTMLElement;
  private novaLabel!: HTMLElement;
  pauseBtn!: HTMLButtonElement;
  muteBtn!: HTMLButtonElement;
  private pauseOverlay!: HTMLElement;
  private overOverlay!: HTMLElement;
  resumeBtn!: HTMLButtonElement;
  restartBtn!: HTMLButtonElement;
  soundToggleBtn!: HTMLButtonElement;
  fxToggleBtn!: HTMLButtonElement;
  playAgainBtn!: HTMLButtonElement;
  private overTitle!: HTMLElement;
  private overScore!: HTMLElement;
  private overBest!: HTMLElement;
  private overNewBest!: HTMLElement;
  private ghostCells: number[] = [];
  private cursorIdx: number | null = null;
  private displayedScore = 0;
  private scoreTween: number | null = null;
  private readonly reducedMotion = prefersReducedMotion();

  constructor(private readonly root: HTMLElement) {
    if (this.reducedMotion) document.documentElement.classList.add('reduced-motion');
    this.build();
  }

  private build(): void {
    const root = this.root;
    root.append(makeStars(40, 'a'), makeStars(24, 'b'));

    // Desktop ambient side panels (ui-spec §2)
    for (const side of ['left', 'right'] as const) {
      const amb = el('div', `ambient ${side}`);
      const rng = mulberry32(side === 'left' ? 3 : 4);
      for (let i = 0; i < 2; i++) {
        const sil = el('div', 'gem-sil');
        sil.style.setProperty('--gem', gemVar(Math.floor(rng() * 6)));
        sil.style.top = `${15 + rng() * 55}%`;
        sil.style[side] = `${8 + rng() * 30}%`;
        sil.style.transform = `rotate(${Math.round(rng() * 40 - 20)}deg)`;
        amb.appendChild(sil);
      }
      root.appendChild(amb);
    }

    const col = el('div', 'app-col');
    this.appCol = col;

    // Header (48px)
    const header = el('header', 'flex items-center justify-between h-12 flex-none');
    const logo = el('div', 'text-lg font-black tracking-wide');
    logo.append('BLOCK ', Object.assign(el('span', 'logo-nova'), { textContent: 'NOVA' }));
    const btns = el('div', 'flex gap-2');
    this.muteBtn = el('button', 'icon-btn') as HTMLButtonElement;
    this.muteBtn.setAttribute('aria-label', t('mute'));
    this.pauseBtn = el('button', 'icon-btn') as HTMLButtonElement;
    this.pauseBtn.textContent = '⏸';
    this.pauseBtn.setAttribute('aria-label', t('pause'));
    btns.append(this.muteBtn, this.pauseBtn);
    header.append(logo, btns);

    // HUD
    const hud = el('div', 'panel flex items-center gap-3 px-4 py-2 flex-none');
    const scoreBox = el('div', 'flex-1 min-w-0');
    const scoreRow = el('div', 'flex items-baseline gap-2');
    this.scoreEl = el('div', 'hud-score', '0');
    this.comboEl = el(
      'div',
      'combo-badge text-xs font-bold px-2 py-0.5 rounded-full bg-white/10 border border-white/15',
    );
    scoreRow.append(this.scoreEl, this.comboEl);
    const bestRow = el('div', 'text-xs text-dim font-semibold tracking-wider');
    this.bestEl = el('span', 'tabular-nums', '0');
    bestRow.append(`${t('best')} `, this.bestEl);
    scoreBox.append(scoreRow, bestRow);

    const novaBox = el('div', 'w-28 flex-none');
    const novaHead = el('div', 'flex items-center justify-between');
    novaHead.append(
      el('span', 'text-[11px] font-black tracking-widest logo-nova', 'NOVA ⚡'),
    );
    this.novaLabel = el('span', 'nova-ready-label text-[10px] font-bold text-nova');
    this.novaLabel.textContent = t('nova_ready');
    novaHead.appendChild(this.novaLabel);
    this.novaTrack = el('div', 'nova-track mt-1');
    this.novaFill = el('div', 'nova-fill');
    this.novaTrack.appendChild(this.novaFill);
    novaBox.append(novaHead, this.novaTrack);
    hud.append(scoreBox, novaBox);

    // Board
    const wrap = el('div', 'board-wrap');
    const board = el('div', 'board panel');
    board.setAttribute('role', 'grid');
    board.setAttribute('aria-label', 'Block Nova board');
    for (let i = 0; i < SIZE * SIZE; i++) {
      const cell = el('div', 'cell');
      cell.dataset.i = String(i);
      this.cells.push(cell);
      board.appendChild(cell);
    }
    this.boardEl = board;
    wrap.appendChild(board);

    // Tray
    const tray = el('div', 'tray');
    for (let i = 0; i < 3; i++) {
      const slot = el('div', 'slot panel');
      slot.dataset.slot = String(i);
      this.slots.push(slot);
      tray.appendChild(slot);
    }

    // Hints — device-branched (touch vs keyboard); ≥14px font (ui-spec §6)
    const hint = el('div', 'flex-none text-center text-sm text-dim h-5');
    hint.append(
      el('span', 'coarse-only', t('touch_hint')),
      el('span', 'fine-only', t('keyboard_hint')),
    );

    col.append(header, hud, wrap, tray, hint);
    root.appendChild(col);

    this.pauseOverlay = this.buildPauseOverlay();
    this.overOverlay = this.buildGameOverOverlay();
    root.append(this.pauseOverlay, this.overOverlay);
  }

  private buildPauseOverlay(): HTMLElement {
    const overlay = el('div', 'overlay');
    const sheet = el('div', 'sheet panel');
    sheet.append(el('h2', 'text-2xl font-black mb-4', t('paused')));
    this.resumeBtn = el('button', 'btn gold mb-2', t('resume')) as HTMLButtonElement;
    this.restartBtn = el('button', 'btn mb-2', t('restart')) as HTMLButtonElement;
    this.soundToggleBtn = el('button', 'btn mb-2') as HTMLButtonElement;
    this.fxToggleBtn = el('button', 'btn mb-2') as HTMLButtonElement;
    const kbHint = el('div', 'fine-only text-sm text-dim mt-2', t('keyboard_hint'));
    sheet.append(this.resumeBtn, this.restartBtn, this.soundToggleBtn, this.fxToggleBtn, kbHint);
    overlay.appendChild(sheet);
    return overlay;
  }

  private buildGameOverOverlay(): HTMLElement {
    const overlay = el('div', 'overlay');
    const sheet = el('div', 'sheet panel');
    this.overTitle = el('h2', 'text-2xl font-black mb-1', t('game_over'));
    this.overNewBest = el('div', 'logo-nova font-black text-sm h-5', '');
    this.overScore = el('div', 'hud-score my-2', '0');
    this.overBest = el('div', 'text-xs text-dim font-semibold mb-4', '');
    this.playAgainBtn = el('button', 'btn gold', t('play_again')) as HTMLButtonElement;
    sheet.append(this.overTitle, this.overNewBest, this.overScore, this.overBest, this.playAgainBtn);
    overlay.appendChild(sheet);
    return overlay;
  }

  /* ---------- rendering ---------- */

  renderBoard(board: Board): void {
    for (let i = 0; i < board.length; i++) {
      const cell = this.cells[i];
      const v = board[i];
      cell.className = 'cell' + (v ? ' gem' : '');
      if (v) cell.style.setProperty('--gem', gemVar(v - 1));
      else cell.style.removeProperty('--gem');
    }
    this.ghostCells = [];
    if (this.cursorIdx !== null) this.cells[this.cursorIdx]?.classList.add('kb-cursor');
  }

  renderTray(tray: (PieceDef | null)[], placeable: boolean[], selected: number | null): void {
    tray.forEach((piece, i) => {
      const slot = this.slots[i];
      slot.textContent = '';
      slot.className = 'slot panel';
      if (!piece) return;
      const maxDim = Math.max(piece.shape.length, piece.shape[0].length);
      const cellPx = maxDim >= 5 ? 13 : maxDim >= 4 ? 15 : 17;
      slot.appendChild(renderPieceGrid(piece, cellPx));
      if (!placeable[i]) slot.classList.add('dim');
      else slot.classList.add('pulse');
      if (selected === i) slot.classList.add('selected');
    });
  }

  setGhost(indices: number[], ok: boolean): void {
    this.clearGhost();
    this.ghostCells = indices;
    for (const i of indices) {
      const cell = this.cells[i];
      if (!cell || cell.classList.contains('gem')) {
        if (cell) cell.classList.add(ok ? 'ghost-ok' : 'ghost-bad');
        continue;
      }
      cell.classList.add(ok ? 'ghost-ok' : 'ghost-bad');
    }
  }

  setGhostColor(colorIndex: number): void {
    for (const i of this.ghostCells) {
      this.cells[i]?.style.setProperty('--gem', gemVar(colorIndex));
    }
  }

  clearGhost(): void {
    for (const i of this.ghostCells) {
      const cell = this.cells[i];
      if (!cell) continue;
      cell.classList.remove('ghost-ok', 'ghost-bad');
      if (!cell.classList.contains('gem')) cell.style.removeProperty('--gem');
    }
    this.ghostCells = [];
  }

  setCursor(index: number | null): void {
    if (this.cursorIdx !== null) this.cells[this.cursorIdx]?.classList.remove('kb-cursor');
    this.cursorIdx = index;
    if (index !== null) this.cells[index]?.classList.add('kb-cursor');
  }

  setScore(score: number, animate = true): void {
    if (this.scoreTween) cancelAnimationFrame(this.scoreTween);
    if (!animate || this.reducedMotion) {
      this.displayedScore = score;
      this.scoreEl.textContent = String(score);
      return;
    }
    // ui-spec §5: count up over ~300ms, never an instant jump.
    const from = this.displayedScore;
    const start = performance.now();
    const dur = 300;
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / dur);
      const eased = 1 - (1 - p) * (1 - p);
      this.displayedScore = Math.round(from + (score - from) * eased);
      this.scoreEl.textContent = String(this.displayedScore);
      if (p < 1) this.scoreTween = requestAnimationFrame(step);
      else this.scoreTween = null;
    };
    this.scoreTween = requestAnimationFrame(step);
  }

  setBest(best: number, flash = false): void {
    this.bestEl.textContent = String(best);
    if (flash) {
      this.scoreEl.classList.remove('gold-flash');
      void this.scoreEl.offsetWidth;
      this.scoreEl.classList.add('gold-flash');
    }
  }

  setCombo(combo: number): void {
    if (combo >= 2) {
      this.comboEl.textContent = `${t('combo')} ×${combo}`;
      this.comboEl.classList.add('on');
    } else {
      this.comboEl.classList.remove('on');
    }
  }

  setNova(gauge: number, full: boolean): void {
    this.novaFill.style.transform = `scaleX(${(gauge / NOVA_FULL).toFixed(3)})`;
    this.novaTrack.classList.toggle('ready', full);
    this.novaLabel.classList.toggle('on', full);
  }

  setMuted(muted: boolean): void {
    this.muteBtn.textContent = muted ? '🔇' : '🔊';
    this.soundToggleBtn.textContent = `${t('mute')}: ${muted ? 'OFF' : 'ON'}`;
  }

  setFxLite(lite: boolean): void {
    document.documentElement.classList.toggle('fx-lite', lite);
    this.fxToggleBtn.textContent = `${t('effects')}: ${lite ? t('fx_lite') : t('fx_full')}`;
  }

  /* ---------- geometry ---------- */

  cellRect(index: number): DOMRect {
    return this.cells[index].getBoundingClientRect();
  }

  boardMetrics(): { left: number; top: number; pitch: number; cell: number } {
    const first = this.cells[0].getBoundingClientRect();
    const second = this.cells[1].getBoundingClientRect();
    return {
      left: first.left,
      top: first.top,
      pitch: second.left - first.left,
      cell: first.width,
    };
  }

  /* ---------- effects (transform/opacity only) ---------- */

  private fxLiteActive(): boolean {
    return document.documentElement.classList.contains('fx-lite');
  }

  popCells(indices: number[], colorLookup: Map<number, number>): void {
    const boardRect = this.boardEl.getBoundingClientRect();
    const sparkBudget = this.fxLiteActive() ? 12 : 24;
    let sparks = 0;
    indices.forEach((i) => {
      const rect = this.cellRect(i);
      const pop = el('div', 'pop-cell');
      pop.style.left = `${rect.left - boardRect.left}px`;
      pop.style.top = `${rect.top - boardRect.top}px`;
      pop.style.width = `${rect.width}px`;
      pop.style.height = `${rect.height}px`;
      const color = colorLookup.get(i) ?? 0;
      pop.style.setProperty('--gem', gemVar(color));
      // stagger by row (ui-spec §5)
      pop.style.animationDelay = `${rowOf(i) * 18}ms`;
      this.boardEl.appendChild(pop);
      setTimeout(() => pop.remove(), 500);

      if (sparks < sparkBudget && !this.reducedMotion) {
        sparks++;
        const spark = el('div', 'spark');
        spark.style.left = `${rect.left - boardRect.left + rect.width / 2}px`;
        spark.style.top = `${rect.top - boardRect.top + rect.height / 2}px`;
        spark.style.background = gemVar(color);
        const angle = (colOf(i) / SIZE) * Math.PI * 2 + rowOf(i);
        spark.style.setProperty('--dx', `${Math.cos(angle) * 40}px`);
        spark.style.setProperty('--dy', `${Math.sin(angle) * 40 - 20}px`);
        this.boardEl.appendChild(spark);
        setTimeout(() => spark.remove(), 600);
      }
    });
  }

  floatScore(text: string, gold = false): void {
    const node = el('div', 'float-score' + (gold ? ' logo-nova text-xl' : ' text-base'));
    node.textContent = text;
    const rect = this.boardEl.getBoundingClientRect();
    node.style.left = '50%';
    node.style.top = `${rect.height * 0.28}px`;
    node.style.transform = 'translateX(-50%)';
    this.boardEl.appendChild(node);
    setTimeout(() => node.remove(), 800);
  }

  edgeGlow(): void {
    if (this.reducedMotion || this.fxLiteActive()) return;
    const glow = el('div', 'edge-glow');
    document.body.appendChild(glow);
    setTimeout(() => glow.remove(), 200);
  }

  novaFx(centerIndex: number): void {
    if (!this.reducedMotion) {
      const flash = el('div', 'flash');
      document.body.appendChild(flash);
      setTimeout(() => flash.remove(), 300);

      const rect = this.cellRect(centerIndex);
      const boardRect = this.boardEl.getBoundingClientRect();
      const size = boardRect.width * 1.1;
      const ring = el('div', 'nova-ring');
      ring.style.width = `${size}px`;
      ring.style.height = `${size}px`;
      ring.style.left = `${rect.left - boardRect.left + rect.width / 2 - size / 2}px`;
      ring.style.top = `${rect.top - boardRect.top + rect.height / 2 - size / 2}px`;
      this.boardEl.appendChild(ring);
      setTimeout(() => ring.remove(), 520);

      this.appCol.classList.remove('shake');
      void this.appCol.offsetWidth;
      this.appCol.classList.add('shake');
      setTimeout(() => this.appCol.classList.remove('shake'), 200);
    }
    this.floatScore(t('nova_boom'), true);
  }

  /* ---------- overlays ---------- */

  showPause(show: boolean): void {
    this.pauseOverlay.classList.toggle('on', show);
  }

  isPauseShown(): boolean {
    return this.pauseOverlay.classList.contains('on');
  }

  showGameOver(data: GameOverData | null): void {
    if (!data) {
      this.overOverlay.classList.remove('on');
      return;
    }
    this.overScore.textContent = String(data.score);
    this.overBest.textContent = `${t('best')} ${data.best}`;
    this.overNewBest.textContent = data.isNewBest ? t('new_best') : '';
    this.overOverlay.classList.add('on');
  }
}
