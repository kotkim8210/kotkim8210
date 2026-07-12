import type { Board } from '../engine/board';
import { SIZE, rowOf, colOf } from '../engine/board';
import type { PieceDef } from '../engine/pieces';
import type { PetArt } from '../engine/petart';
import { PET_TILES } from '../engine/pets';
import { NOVA_FULL } from '../engine/game';
import { t } from '../core/i18n';
import { prefersReducedMotion } from '../core/device';
import { mulberry32 } from '../engine/rng';

/** Draw a 16×16 pixel-art sprite onto a crisp canvas (px = backing scale). */
export function renderPetCanvas(art: PetArt, px: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = 16 * px;
  canvas.height = 16 * px;
  const g = canvas.getContext('2d');
  if (g) {
    art.rows.forEach((row, y) => {
      for (let x = 0; x < row.length; x++) {
        const ch = row[x];
        if (ch === '.') continue;
        g.fillStyle = art.palette[ch] ?? '#ff00ff';
        g.fillRect(x * px, y * px, px, px);
      }
    });
  }
  return canvas;
}

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
  title: string;
  score: number;
  /** Secondary line under the score (e.g. "BEST 384" or "NOVA ×2"). */
  metaLine: string;
  isNewBest: boolean;
  /** Daily: 0-5 stars; null hides the row. */
  stars?: number | null;
  /** Extra gold line (e.g. "SURVIVED ALL 50!"); empty hides it. */
  banner?: string;
  /** Small dim note (e.g. "기록은 첫 판만 인정"). */
  note?: string;
  /** Near-miss line ("Best −N"); gold when within 15% of best. */
  gapText?: { text: string; gold: boolean };
  /** Reveal of the upcoming pieces ("these were coming next"). */
  nextPieces?: PieceDef[];
  /** Peak-end highlight chips (e.g. "NOVA ×3", "COMBO 5"). */
  highlights?: string[];
  /** Nearest weekly quest teaser line (Zeigarnik at the session seam). */
  questLine?: string;
  /** Cosmic-egg progress line ("Next friend in N cells"). */
  petLine?: string;
  /** Show the ticking next-daily countdown line. */
  countdown?: boolean;
  /** Tag the daily button with NEW (today's daily unplayed). */
  dailyNew?: boolean;
  buttons: {
    playAgain?: boolean;
    share?: boolean;
    retry?: boolean;
    retryDisabled?: boolean;
    classic?: boolean;
    revive?: boolean;
    daily?: boolean;
  };
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
  private novaLogo!: HTMLElement;
  pauseBtn!: HTMLButtonElement;
  muteBtn!: HTMLButtonElement;
  dailyBtn!: HTMLButtonElement;
  private pauseOverlay!: HTMLElement;
  private overOverlay!: HTMLElement;
  resumeBtn!: HTMLButtonElement;
  restartBtn!: HTMLButtonElement;
  soundToggleBtn!: HTMLButtonElement;
  fxToggleBtn!: HTMLButtonElement;
  playAgainBtn!: HTMLButtonElement;
  shareBtn!: HTMLButtonElement;
  retryBtn!: HTMLButtonElement;
  classicBtn!: HTMLButtonElement;
  reviveBtn!: HTMLButtonElement;
  dailyCardBtn!: HTMLButtonElement;
  statsBtn!: HTMLButtonElement;
  statsCloseBtn!: HTMLButtonElement;
  private overTitle!: HTMLElement;
  private overScore!: HTMLElement;
  private overBest!: HTMLElement;
  private overNewBest!: HTMLElement;
  private overStars!: HTMLElement;
  private overBanner!: HTMLElement;
  private overNote!: HTMLElement;
  private overGap!: HTMLElement;
  private overHl!: HTMLElement;
  private overNextLabel!: HTMLElement;
  private overNextRow!: HTMLElement;
  private overQuest!: HTMLElement;
  private overPet!: HTMLElement;
  private overCountdown!: HTMLElement;
  private dailyDot!: HTMLElement;
  eggBtn!: HTMLButtonElement;
  private eggCard!: HTMLElement;
  private eggCovers: HTMLElement[] = [];
  private eggArt: PetArt | null = null;
  private eggCoverOrder: number[] = [];
  private revealEl: HTMLElement | null = null;
  private revealTimer: number | null = null;
  private modeChip!: HTMLElement;
  private bestRow!: HTMLElement;
  private sublineEl!: HTMLElement;
  private bonusChip!: HTMLElement;
  private lvChip!: HTMLElement;
  private lvRing!: HTMLElement;
  private lvText!: HTMLElement;
  private lvRank!: HTMLElement;
  private streakChip!: HTMLElement;
  private paceTrack!: HTMLElement;
  private paceFill!: HTMLElement;
  private questsBox!: HTMLElement;
  private statsOverlay!: HTMLElement;
  private statsGrid!: HTMLElement;
  private toastEl: HTMLElement | null = null;
  private toastTimer: number | null = null;
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
    const logoWrap = el('div', 'flex items-center gap-2 min-w-0');
    const logo = el('div', 'text-lg font-black tracking-wide whitespace-nowrap');
    logo.append('BLOCK ', Object.assign(el('span', 'logo-nova'), { textContent: 'NOVA' }));
    this.modeChip = el('span', 'mode-chip hidden');
    // LevelChip (ui-spec §3): header-left capsule with a conic XP ring
    this.lvChip = el('span', 'lv-chip');
    this.lvRing = el('span', 'lv-ring');
    this.lvText = el('span', '', 'Lv.1');
    this.lvRank = el('span', 'lv-rank', 'Spark');
    this.lvChip.append(this.lvRing, this.lvText, this.lvRank);
    logoWrap.append(logo, this.lvChip, this.modeChip);
    const btns = el('div', 'flex gap-2');
    this.dailyBtn = el('button', 'icon-btn') as HTMLButtonElement;
    this.dailyBtn.textContent = '📅';
    this.dailyBtn.setAttribute('aria-label', t('daily'));
    this.muteBtn = el('button', 'icon-btn') as HTMLButtonElement;
    this.muteBtn.setAttribute('aria-label', t('mute'));
    this.pauseBtn = el('button', 'icon-btn') as HTMLButtonElement;
    this.pauseBtn.textContent = '⏸';
    this.pauseBtn.setAttribute('aria-label', t('pause'));
    btns.append(this.dailyBtn, this.muteBtn, this.pauseBtn);
    header.append(logoWrap, btns);

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
    // PB pace bar (ui-spec §3): thin score/best progress with a gold 100% tick
    this.paceTrack = el('div', 'pace-track hidden');
    this.paceFill = el('div', 'pace-fill');
    this.paceTrack.append(this.paceFill, el('div', 'pace-tick'));
    this.bestRow = el('div', 'text-xs text-dim font-semibold tracking-wider');
    this.bestEl = el('span', 'tabular-nums', '0');
    this.streakChip = el('span', 'streak-chip hidden');
    this.bestRow.append(`${t('best')} `, this.bestEl, this.streakChip);
    this.sublineEl = el('div', 'text-xs text-nova font-bold tracking-wider hidden');
    scoreBox.append(scoreRow, this.paceTrack, this.bestRow, this.sublineEl);

    const novaBox = el('div', 'w-28 flex-none relative');
    const novaHead = el('div', 'flex items-center justify-between');
    this.novaLogo = el('span', 'nova-logo text-[11px] font-black tracking-widest logo-nova', 'NOVA ⚡');
    novaHead.appendChild(this.novaLogo);
    this.novaLabel = el('span', 'nova-ready-label text-[11px] font-black text-nova');
    this.novaLabel.textContent = t('nova_ready');
    this.bonusChip = el('span', 'bonus-chip hidden', t('bonus_charge'));
    novaHead.append(this.novaLabel);
    novaBox.appendChild(this.bonusChip);
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
    // puzzle card — the pixel friend uncovering tile by tile as cells clear
    this.eggBtn = el('button', 'egg') as HTMLButtonElement;
    this.eggBtn.setAttribute('aria-label', t('pets_title'));
    this.eggCard = el('span', 'card');
    const covers = el('span', 'covers');
    for (let i = 0; i < PET_TILES; i++) {
      const tile = el('i');
      this.eggCovers.push(tile);
      covers.appendChild(tile);
    }
    this.eggCard.appendChild(covers);
    this.eggBtn.appendChild(this.eggCard);
    board.appendChild(this.eggBtn);
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
    this.statsOverlay = this.buildStatsOverlay();
    root.append(this.pauseOverlay, this.overOverlay, this.statsOverlay);
  }

  private buildPauseOverlay(): HTMLElement {
    const overlay = el('div', 'overlay');
    const sheet = el('div', 'sheet panel');
    sheet.append(el('h2', 'text-2xl font-black mb-4', t('paused')));
    this.resumeBtn = el('button', 'btn gold mb-2', t('resume')) as HTMLButtonElement;
    this.restartBtn = el('button', 'btn mb-2', t('restart')) as HTMLButtonElement;
    this.soundToggleBtn = el('button', 'btn mb-2') as HTMLButtonElement;
    this.fxToggleBtn = el('button', 'btn mb-2') as HTMLButtonElement;
    this.statsBtn = el('button', 'btn mb-2', `📊 ${t('stats')}`) as HTMLButtonElement;
    // weekly quest pills (game-design §12) — shown while paused
    this.questsBox = el('div', 'mt-3 text-left');
    const kbHint = el('div', 'fine-only text-sm text-dim mt-2', t('keyboard_hint'));
    sheet.append(
      this.resumeBtn,
      this.restartBtn,
      this.soundToggleBtn,
      this.fxToggleBtn,
      this.statsBtn,
      this.questsBox,
      kbHint,
    );
    overlay.appendChild(sheet);
    return overlay;
  }

  private buildGameOverOverlay(): HTMLElement {
    const overlay = el('div', 'overlay');
    const sheet = el('div', 'sheet panel');
    this.overTitle = el('h2', 'text-2xl font-black mb-1', t('game_over'));
    this.overBanner = el('div', 'logo-nova font-black text-base', '');
    this.overNewBest = el('div', 'logo-nova font-black text-sm h-5', '');
    this.overStars = el('div', 'stars-row my-1 hidden');
    this.overScore = el('div', 'hud-score my-2', '0');
    this.overGap = el('div', 'gap-line mb-1 hidden');
    this.overBest = el('div', 'text-sm text-dim font-semibold mb-1', '');
    this.overHl = el('div', 'hl-row hidden');
    this.overNextLabel = el('div', 'text-xs text-dim mt-2 hidden', t('coming_next'));
    this.overNextRow = el('div', 'next-row hidden');
    this.overQuest = el('div', 'text-sm text-dim mb-1 hidden', '');
    this.overPet = el('div', 'text-sm text-dim mb-1 hidden', '');
    this.overCountdown = el('div', 'text-sm font-bold text-nova mb-2 tabular-nums hidden', '');
    this.overNote = el('div', 'text-xs text-dim mb-3', '');
    this.reviveBtn = el('button', 'btn gold mb-2', `▶ ${t('revive')}`) as HTMLButtonElement;
    this.playAgainBtn = el('button', 'btn gold mb-2', t('play_again')) as HTMLButtonElement;
    this.shareBtn = el('button', 'btn gold mb-2', t('share')) as HTMLButtonElement;
    this.retryBtn = el('button', 'btn mb-2', t('retry_ad')) as HTMLButtonElement;
    this.classicBtn = el('button', 'btn mb-2', t('classic')) as HTMLButtonElement;
    this.dailyCardBtn = el('button', 'btn', `📅 ${t('daily')}`) as HTMLButtonElement;
    sheet.append(
      this.overTitle,
      this.overBanner,
      this.overNewBest,
      this.overStars,
      this.overScore,
      this.overGap,
      this.overBest,
      this.overHl,
      this.overNextLabel,
      this.overNextRow,
      this.overQuest,
      this.overPet,
      this.overCountdown,
      this.overNote,
      this.reviveBtn,
      this.playAgainBtn,
      this.shareBtn,
      this.retryBtn,
      this.classicBtn,
      this.dailyCardBtn,
    );
    overlay.appendChild(sheet);
    return overlay;
  }

  private buildStatsOverlay(): HTMLElement {
    const overlay = el('div', 'overlay');
    const sheet = el('div', 'sheet panel');
    sheet.append(el('h2', 'text-2xl font-black mb-2', `📊 ${t('stats')}`));
    this.statsGrid = el('div', 'stats-grid');
    this.statsCloseBtn = el('button', 'btn', t('close')) as HTMLButtonElement;
    sheet.append(this.statsGrid, this.statsCloseBtn);
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

  renderTray(
    tray: (PieceDef | null)[],
    placeable: boolean[],
    selected: number | null,
    spawn = false,
  ): void {
    tray.forEach((piece, i) => {
      const slot = this.slots[i];
      slot.textContent = '';
      slot.className = 'slot panel';
      if (!piece) return;
      const maxDim = Math.max(piece.shape.length, piece.shape[0].length);
      const cellPx = maxDim >= 5 ? 13 : maxDim >= 4 ? 15 : 17;
      const mini = renderPieceGrid(piece, cellPx);
      if (spawn) {
        mini.classList.add('spawn');
        mini.style.animationDelay = `${i * 70}ms`;
      }
      slot.appendChild(mini);
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
    // READY replaces the wordmark — the 112px head row can't fit both
    this.novaLabel.classList.toggle('on', full);
    this.novaLogo.classList.toggle('off', full);
  }

  setMuted(muted: boolean): void {
    this.muteBtn.textContent = muted ? '🔇' : '🔊';
    this.muteBtn.classList.toggle('muted', muted);
    this.soundToggleBtn.textContent = `${t('mute')}: ${muted ? 'OFF' : 'ON'}`;
  }

  /* ---------- cosmic friends (pixel puzzle) ---------- */

  /** Update the corner puzzle card: current picture + uncovered tile count. */
  setPetCard(art: PetArt, artIndex: number, tiles: number, near: boolean, complete: boolean): void {
    if (this.eggArt !== art) {
      this.eggArt = art;
      this.eggCard.querySelector('canvas')?.remove();
      this.eggCard.prepend(renderPetCanvas(art, 4));
      // tiles uncover in a scrambled, per-picture deterministic order
      const rng = mulberry32((artIndex + 7) >>> 0);
      this.eggCoverOrder = Array.from({ length: PET_TILES }, (_, i) => i);
      for (let i = this.eggCoverOrder.length - 1; i > 0; i--) {
        const j = Math.floor(rng() * (i + 1));
        [this.eggCoverOrder[i], this.eggCoverOrder[j]] = [this.eggCoverOrder[j], this.eggCoverOrder[i]];
      }
    }
    const open = complete ? PET_TILES : tiles;
    this.eggCoverOrder.forEach((coverIdx, orderPos) => {
      this.eggCovers[coverIdx].classList.toggle('open', orderPos < open);
    });
    this.eggBtn.classList.toggle('near', near && !complete);
  }

  /** Brief feedback pulses on the card (mote absorbed / puzzle completed). */
  cardBlink(): void {
    this.eggBtn.classList.remove('blink');
    void this.eggBtn.offsetWidth;
    this.eggBtn.classList.add('blink');
    setTimeout(() => this.eggBtn.classList.remove('blink'), 300);
  }

  cardHatch(): void {
    this.eggBtn.classList.remove('hatch');
    void this.eggBtn.offsetWidth;
    this.eggBtn.classList.add('hatch');
    setTimeout(() => this.eggBtn.classList.remove('hatch'), 600);
  }

  /** Puzzle-complete cinematic: zoom the finished art center-screen and hold
   *  (~2.6s, click to skip) so the player can actually appreciate it. */
  revealPet(art: PetArt, name: string, flavor: string, holdMs = 2600): void {
    if (!this.revealEl) {
      this.revealEl = el('div', 'reveal');
      this.revealEl.addEventListener('click', () => this.hideReveal());
      document.body.appendChild(this.revealEl);
    }
    const frame = el('div', 'frame');
    frame.append(
      renderPetCanvas(art, 16),
      el('div', 'r-title', `✨ ${t('puzzle_done')} ✨`),
      el('div', 'r-name', name),
      el('div', 'r-flavor', flavor),
    );
    this.revealEl.textContent = '';
    this.revealEl.appendChild(frame);
    this.revealEl.classList.add('on');
    this.cardHatch();
    this.confetti();
    if (this.revealTimer) clearTimeout(this.revealTimer);
    this.revealTimer = window.setTimeout(() => this.hideReveal(), holdMs);
  }

  hideReveal(): void {
    this.revealEl?.classList.remove('on');
    if (this.revealTimer) {
      clearTimeout(this.revealTimer);
      this.revealTimer = null;
    }
  }

  /** Energy motes: cleared cells fly into the puzzle card (goal linkage). */
  motes(cellIndices: number[]): void {
    if (this.reducedMotion || cellIndices.length === 0) return;
    const budget = this.fxLiteActive() ? 1 : 3;
    const target = this.eggCard.getBoundingClientRect();
    const tx = target.left + target.width / 2;
    const ty = target.top + target.height / 2;
    const picks = cellIndices.filter((_, i) => i % Math.ceil(cellIndices.length / budget) === 0).slice(0, budget);
    picks.forEach((cellIdx, i) => {
      const rect = this.cellRect(cellIdx);
      const mote = el('div', 'mote');
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      mote.style.left = `${x - 4}px`;
      mote.style.top = `${y - 4}px`;
      document.body.appendChild(mote);
      setTimeout(() => {
        mote.classList.add('fly');
        mote.style.transform = `translate(${tx - x}px, ${ty - y}px) scale(0.5)`;
      }, 30 + i * 60);
      setTimeout(() => {
        mote.remove();
        if (i === picks.length - 1) this.cardBlink();
      }, 650 + i * 60);
    });
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

  popCells(indices: number[], colorLookup: Map<number, number>, withSparks = true): void {
    const boardRect = this.boardEl.getBoundingClientRect();
    // a nova turn owns the particle budget — the blast brings its own sparks
    const sparkBudget = withSparks ? (this.fxLiteActive() ? 12 : 24) : 0;
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

  floatScore(text: string, gold = false, opts: { px?: number; topPct?: number } = {}): void {
    const node = el('div', 'float-score' + (gold ? ' logo-nova' : ''));
    node.textContent = text;
    node.style.fontSize = `${opts.px ?? (gold ? 20 : 16)}px`;
    const rect = this.boardEl.getBoundingClientRect();
    node.style.left = '50%';
    node.style.top = `${rect.height * (opts.topPct ?? 0.28)}px`;
    // centering lives in the keyframes — an inline transform would be
    // overridden by the animation
    this.boardEl.appendChild(node);
    setTimeout(() => node.remove(), 800);
  }

  /** Big center word punch (nova, rank-ups). */
  wordPunch(text: string, px = 44): void {
    const word = el('div', 'nova-word', text);
    word.style.fontSize = `${px}px`;
    this.boardEl.appendChild(word);
    setTimeout(() => word.remove(), 950);
  }

  edgeGlow(): void {
    if (this.reducedMotion || this.fxLiteActive()) return;
    const glow = el('div', 'edge-glow');
    document.body.appendChild(glow);
    setTimeout(() => glow.remove(), 200);
  }

  novaFx(centerIndex: number): void {
    if (this.reducedMotion) {
      // ui-spec §5: reduced-motion fallback is a gentle gold fade only
      const fade = el('div', 'nova-fade');
      document.body.appendChild(fade);
      setTimeout(() => fade.remove(), 700);
      this.floatScore(t('nova_boom'), true);
      return;
    }
    const lite = this.fxLiteActive();
    const rect = this.cellRect(centerIndex);
    const boardRect = this.boardEl.getBoundingClientRect();
    const cx = rect.left - boardRect.left + rect.width / 2;
    const cy = rect.top - boardRect.top + rect.height / 2;
    const rng = mulberry32((performance.now() | 0) >>> 0);

    // 1) impact: white flash + gold afterglow + board punch
    for (const cls of ['flash', 'flash gold']) {
      const flash = el('div', cls);
      document.body.appendChild(flash);
      setTimeout(() => flash.remove(), 700);
    }
    this.boardEl.classList.remove('board-punch');
    void this.boardEl.offsetWidth;
    this.boardEl.classList.add('board-punch');
    setTimeout(() => this.boardEl.classList.remove('board-punch'), 320);

    // 2) gold bloom wave from the blast center
    const bloomSize = boardRect.width * 0.8;
    const bloom = el('div', 'nova-bloom');
    bloom.style.width = `${bloomSize}px`;
    bloom.style.height = `${bloomSize}px`;
    bloom.style.left = `${cx - bloomSize / 2}px`;
    bloom.style.top = `${cy - bloomSize / 2}px`;
    this.boardEl.appendChild(bloom);
    setTimeout(() => bloom.remove(), 650);

    // 3) triple shockwave rings
    const size = boardRect.width * 1.15;
    for (const cls of ['nova-ring', 'nova-ring late', 'nova-ring late violet']) {
      const ring = el('div', cls);
      if (cls.endsWith('violet')) {
        ring.style.borderColor = 'var(--gem-1)';
        ring.style.boxShadow = '0 0 24px var(--gem-1)';
        ring.style.animationDelay = '0.16s';
      }
      ring.style.width = `${size}px`;
      ring.style.height = `${size}px`;
      ring.style.left = `${cx - size / 2}px`;
      ring.style.top = `${cy - size / 2}px`;
      this.boardEl.appendChild(ring);
      setTimeout(() => ring.remove(), 900);
    }

    // 4) radial sparks + light streaks (gold-heavy with gem accents)
    const sparkCount = lite ? 10 : 20;
    const reach = boardRect.width * 0.72;
    for (let i = 0; i < sparkCount; i++) {
      const spark = el('div', 'nova-spark');
      const angle = (i / sparkCount) * Math.PI * 2 + rng() * 0.5;
      const dist = reach * (0.45 + rng() * 0.55);
      spark.style.left = `${cx - 3}px`;
      spark.style.top = `${cy - 3}px`;
      spark.style.setProperty(
        '--gem',
        i % 3 === 0 ? `var(${GEM_VARS[Math.floor(rng() * 6)]})` : 'var(--color-nova)',
      );
      spark.style.setProperty('--dx', `${Math.cos(angle) * dist}px`);
      spark.style.setProperty('--dy', `${Math.sin(angle) * dist}px`);
      spark.style.setProperty('--dur', `${0.55 + rng() * 0.4}s`);
      this.boardEl.appendChild(spark);
      setTimeout(() => spark.remove(), 1100);
    }
    if (!lite) {
      for (let i = 0; i < 6; i++) {
        const streak = el('div', 'nova-streak');
        streak.style.left = `${cx}px`;
        streak.style.top = `${cy - 1.5}px`;
        streak.style.setProperty('--ang', `${Math.round(i * 60 + rng() * 30)}deg`);
        streak.style.animationDelay = `${i * 0.02}s`;
        this.boardEl.appendChild(streak);
        setTimeout(() => streak.remove(), 600);
      }
    }

    // 5) big NOVA word punch
    this.wordPunch(t('nova_boom'));

    // 6) meter detonation flash + harder shake
    this.novaTrack.classList.add('detonate');
    setTimeout(() => this.novaTrack.classList.remove('detonate'), 250);
    this.appCol.classList.remove('shake-hard');
    void this.appCol.offsetWidth;
    this.appCol.classList.add('shake-hard');
    setTimeout(() => this.appCol.classList.remove('shake-hard'), 260);
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
    this.overTitle.textContent = data.title;
    this.overScore.textContent = String(data.score);
    this.overBest.textContent = data.metaLine;
    this.overNewBest.textContent = data.isNewBest ? t('new_best') : '';
    this.overBanner.textContent = data.banner ?? '';
    this.overBanner.classList.toggle('hidden', !data.banner);
    this.overNote.textContent = data.note ?? '';
    this.overNote.classList.toggle('hidden', !data.note);
    if (data.stars !== undefined && data.stars !== null) {
      this.overStars.textContent = '';
      for (let i = 0; i < 5; i++) {
        this.overStars.appendChild(el('span', i < data.stars ? '' : 'off', '⭐'));
      }
      this.overStars.classList.remove('hidden');
    } else {
      this.overStars.classList.add('hidden');
    }
    this.overGap.textContent = data.gapText?.text ?? '';
    this.overGap.classList.toggle('hidden', !data.gapText);
    this.overGap.classList.toggle('gold', !!data.gapText?.gold);

    this.overHl.textContent = '';
    if (data.highlights && data.highlights.length > 0) {
      for (const h of data.highlights) this.overHl.appendChild(el('span', 'hl-chip', h));
      this.overHl.classList.remove('hidden');
    } else {
      this.overHl.classList.add('hidden');
    }

    this.overNextRow.textContent = '';
    const showNext = !!data.nextPieces && data.nextPieces.length > 0;
    if (showNext) {
      for (const p of data.nextPieces!) this.overNextRow.appendChild(renderPieceGrid(p, 9, 1));
    }
    this.overNextLabel.classList.toggle('hidden', !showNext);
    this.overNextRow.classList.toggle('hidden', !showNext);

    this.overNewBest.classList.toggle('hidden', !data.isNewBest);
    this.overQuest.textContent = data.questLine ?? '';
    this.overQuest.classList.toggle('hidden', !data.questLine);
    this.overPet.textContent = data.petLine ?? '';
    this.overPet.classList.toggle('hidden', !data.petLine);
    this.overCountdown.classList.toggle('hidden', !data.countdown);

    // exactly ONE gold CTA per sheet (ui-spec §3: gold = the primary action)
    const hiddenIf = (show: boolean | undefined) => (show ? '' : ' hidden');
    this.reviveBtn.className = 'btn gold mb-2' + hiddenIf(data.buttons.revive);
    this.playAgainBtn.className =
      (data.buttons.revive ? 'btn mb-2' : 'btn gold mb-2') + hiddenIf(data.buttons.playAgain);
    this.shareBtn.className =
      (!data.buttons.revive && !data.buttons.playAgain ? 'btn gold mb-2' : 'btn mb-2') +
      hiddenIf(data.buttons.share);
    this.retryBtn.classList.toggle('hidden', !data.buttons.retry);
    this.retryBtn.disabled = !!data.buttons.retryDisabled;
    this.retryBtn.textContent = data.buttons.retryDisabled ? t('retry_used') : t('retry_ad');
    this.classicBtn.classList.toggle('hidden', !data.buttons.classic);
    this.dailyCardBtn.classList.toggle('hidden', !data.buttons.daily);
    this.dailyCardBtn.textContent = `📅 ${t('daily')}${data.dailyNew ? ` · ${t('new_tag')}` : ''}`;
    this.overOverlay.classList.add('on');
  }

  setCountdown(text: string): void {
    this.overCountdown.textContent = text;
  }

  /** Gold dot on the header daily button while today's daily is unplayed. */
  setDailyBadge(show: boolean): void {
    if (!this.dailyDot) {
      this.dailyDot = el('span', 'badge-dot hidden');
      this.dailyBtn.style.position = 'relative';
      this.dailyBtn.appendChild(this.dailyDot);
    }
    this.dailyDot.classList.toggle('hidden', !show);
  }

  /* ---------- Phase 3: retention meta ---------- */

  setLevel(level: number, rank: string, progress: number): void {
    this.lvText.textContent = `Lv.${level}`;
    this.lvRank.textContent = rank;
    this.lvRing.style.setProperty('--p', progress.toFixed(3));
  }

  setStreak(current: number, shields: number): void {
    if (current <= 0 && shields <= 0) {
      this.streakChip.classList.add('hidden');
      return;
    }
    this.streakChip.classList.remove('hidden');
    this.streakChip.textContent = `🔥${current}`;
    if (shields > 0) {
      const s = el('span', 'shield', '🛡'.repeat(shields));
      this.streakChip.appendChild(s);
    }
  }

  /** PB pace bar: ratio 0..1 of score vs best (null hides), gold flash on PB. */
  setPace(ratio: number | null, flash = false): void {
    if (ratio === null) {
      this.paceTrack.classList.add('hidden');
      return;
    }
    this.paceTrack.classList.remove('hidden');
    this.paceFill.style.transform = `scaleX(${Math.max(0, Math.min(1, ratio)).toFixed(3)})`;
    if (flash) {
      this.paceTrack.classList.remove('flash');
      void this.paceTrack.offsetWidth;
      this.paceTrack.classList.add('flash');
      setTimeout(() => this.paceTrack.classList.remove('flash'), 250);
    }
  }

  renderQuests(
    items: { label: string; progress: number; target: number; done: boolean }[],
  ): void {
    this.questsBox.textContent = '';
    this.questsBox.appendChild(
      el('div', 'text-xs font-black text-dim tracking-widest mb-2', t('quests').toUpperCase()),
    );
    for (const q of items) {
      const ratio = Math.min(1, q.progress / q.target);
      const pill = el('div', 'quest-pill' + (q.done ? ' done' : ratio >= 0.9 ? ' near' : ''));
      const row = el('div', 'q-row');
      const label = el('span', '', q.label);
      const count = el(
        'span',
        'q-count',
        q.done ? '' : `${q.progress}/${q.target}`,
      );
      if (q.done) {
        const check = el('span', 'q-check', '✔');
        count.appendChild(check);
      }
      row.append(label, count);
      const track = el('div', 'q-track');
      const fill = el('div', 'q-fill');
      fill.style.transform = `scaleX(${ratio.toFixed(3)})`;
      track.appendChild(fill);
      pill.append(row, track);
      this.questsBox.appendChild(pill);
    }
  }

  showStats(
    rows: { label: string; value: string }[] | null,
    pets?: { art: PetArt; name: string; unlocked: boolean; fresh: boolean }[],
  ): void {
    if (!rows) {
      this.statsOverlay.classList.remove('on');
      return;
    }
    this.statsGrid.textContent = '';
    for (const r of rows) {
      const tile = el('div', 'stat-tile');
      tile.append(el('div', 'v', r.value), el('div', 'k', r.label));
      this.statsGrid.appendChild(tile);
    }
    if (pets && pets.length > 0) {
      const title = el(
        'div',
        'pets-span text-xs font-black text-dim tracking-widest mt-2',
        `🧩 ${t('pets_title').toUpperCase()}`,
      );
      const grid = el('div', 'pets-grid pets-span');
      for (const p of pets) {
        const cell = el('div', 'pet-cell' + (p.unlocked ? (p.fresh ? ' fresh' : '') : ' locked'));
        if (p.unlocked) {
          const canvas = renderPetCanvas(p.art, 2);
          canvas.style.width = '26px';
          canvas.style.height = '26px';
          canvas.style.imageRendering = 'pixelated';
          cell.appendChild(canvas);
        } else {
          cell.textContent = '❓';
        }
        cell.title = p.unlocked ? p.name : '???';
        grid.appendChild(cell);
      }
      this.statsGrid.append(title, grid);
    }
    this.statsOverlay.classList.add('on');
  }

  /* ---------- Phase 2 additions ---------- */

  /** Squash & stretch on freshly placed cells (ui-spec §5). */
  markPlaced(indices: number[]): void {
    for (const i of indices) {
      const cell = this.cells[i];
      if (!cell) continue;
      cell.classList.remove('placed');
      void cell.offsetWidth;
      cell.classList.add('placed');
    }
  }

  /** Confetti burst — gold + gem mix, capped at 24 (12 in lite mode). */
  confetti(): void {
    if (this.reducedMotion) return;
    const count = this.fxLiteActive() ? 12 : 24;
    const palette = ['var(--color-nova)', 'var(--color-nova-hi)', ...GEM_VARS.map((v) => `var(${v})`)];
    const rng = mulberry32((performance.now() | 0) >>> 0);
    for (let i = 0; i < count; i++) {
      const c = el('div', 'confetto');
      c.style.left = `${5 + rng() * 90}vw`;
      c.style.background = palette[i % palette.length];
      c.style.setProperty('--dur', `${1.1 + rng() * 0.9}s`);
      c.style.setProperty('--spin', `${Math.round(360 + rng() * 540)}deg`);
      c.style.animationDelay = `${rng() * 0.25}s`;
      document.body.appendChild(c);
      setTimeout(() => c.remove(), 2400);
    }
  }

  toast(text: string): void {
    if (!this.toastEl) {
      this.toastEl = el('div', 'toast');
      document.body.appendChild(this.toastEl);
    }
    this.toastEl.textContent = text;
    this.toastEl.classList.add('on');
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toastTimer = window.setTimeout(() => this.toastEl?.classList.remove('on'), 1800);
  }

  setBonusChip(show: boolean): void {
    this.bonusChip.classList.toggle('hidden', !show);
  }

  setModeChip(label: string | null): void {
    this.modeChip.textContent = label ?? '';
    this.modeChip.classList.toggle('hidden', !label);
  }

  /** Daily HUD line (replaces the BEST row while in daily mode). */
  setSubline(text: string | null): void {
    this.sublineEl.textContent = text ?? '';
    this.sublineEl.classList.toggle('hidden', !text);
    this.bestRow.classList.toggle('hidden', !!text);
  }

  novaTrackRect(): DOMRect {
    return this.novaTrack.getBoundingClientRect();
  }

  slotRect(i: number): DOMRect {
    return this.slots[i].getBoundingClientRect();
  }
}
