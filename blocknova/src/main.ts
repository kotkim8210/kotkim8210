import './style.css';
import { Game, type MoveResult } from './engine/game';
import { randomSeed } from './engine/rng';
import { store } from './core/storage';
import { SoundEngine } from './core/audio';
import { vibrate } from './core/device';
import { t } from './core/i18n';
import { ads } from './ads/adapter';
import { View } from './ui/view';
import { DragController } from './ui/drag';
import { KeyboardController } from './ui/keyboard';

ads.init();
ads.loadingStart();

const flags = store.flags();
const sound = new SoundEngine(flags.mute);
const view = new View(document.getElementById('app')!);

let game = new Game({ seed: randomSeed(), best: store.best().classic });
let startingBest = store.best().classic;
let paused = false;
let selected: number | null = null;

view.setMuted(flags.mute);
view.setFxLite(flags.fx === 'lite');

/* ---------- rendering ---------- */

function renderAll(): void {
  view.renderBoard(game.board);
  view.renderTray(game.tray, game.placeablePieces(), selected);
  view.setScore(game.score, false);
  view.setBest(game.best);
  view.setCombo(game.combo);
  view.setNova(game.gauge, game.gaugeIsFull());
  keyboard.refresh();
}

function setSelected(i: number | null): void {
  selected = i;
  view.renderTray(game.tray, game.placeablePieces(), selected);
}

/* ---------- move pipeline ---------- */

function tryPlace(trayIndex: number, row: number, col: number): boolean {
  if (paused || game.over) return false;
  const piece = game.tray[trayIndex];
  if (!piece) return false;
  const prevBoard = [...game.board];
  const move = game.placeAt(trayIndex, row, col);
  if (!move) return false;
  handleMove(move, prevBoard, piece.color);
  return true;
}

function handleMove(move: MoveResult, prevBoard: number[], pieceColor: number): void {
  selected = null;
  view.renderBoard(game.board);
  view.renderTray(game.tray, game.placeablePieces(), selected);
  keyboard.refresh();

  sound.place();
  vibrate(15);

  view.setScore(game.score);
  view.setCombo(move.combo);
  view.setNova(game.gauge, move.gaugeFull);

  const removed = [...move.clearedCells, ...move.novaCells];
  if (removed.length > 0) {
    // colors as they were before removal (placed cells take the piece color)
    const colorLookup = new Map<number, number>();
    for (const i of removed) {
      const v = prevBoard[i];
      colorLookup.set(i, v > 0 ? v - 1 : pieceColor);
    }
    view.popCells(removed, colorLookup);
    sound.clear(move.combo);
    vibrate(30);
    view.floatScore(`+${move.gained}`, move.nova);
    const lines = move.clearedRows.length + move.clearedCols.length;
    if (lines >= 2 && !move.nova) view.edgeGlow();
  }

  if (move.nova && move.novaCenter) {
    view.novaFx(move.novaCenter.row * 9 + move.novaCenter.col);
    sound.nova();
    vibrate([20, 30, 60]);
    ads.happytime(); // §adapter: happytime on nova explosion
  }

  if (move.newBest && move.gained > 0 && store.best().classic > 0) {
    view.setBest(game.best, true);
    sound.fanfare();
    ads.happytime(); // new record
  } else {
    view.setBest(game.best);
  }
  if (game.best > store.best().classic) store.setBest({ classic: game.best });

  if (move.perfectClear) view.floatScore(t('perfect'), true);

  if (move.gameOver) {
    setTimeout(finishGame, 450);
  }
}

function finishGame(): void {
  ads.gameplayStop();
  sound.gameOver();
  store.addStats({
    games: 1,
    totalScore: game.score,
    novaTotal: game.novaCount,
    linesTotal: game.linesTotal,
  });
  store.setBest({ classic: game.best });
  view.showGameOver({
    score: game.score,
    best: game.best,
    isNewBest: game.score > startingBest,
  });
}

function restart(): void {
  startingBest = store.best().classic;
  game = new Game({ seed: randomSeed(), best: startingBest });
  selected = null;
  paused = false;
  view.showGameOver(null);
  view.showPause(false);
  renderAll();
  ads.gameplayStart();
}

/* ---------- pause ---------- */

function setPaused(next: boolean): void {
  if (game.over) return;
  if (paused === next) return;
  paused = next;
  view.showPause(next);
  if (next) ads.gameplayStop();
  else ads.gameplayStart();
}

function toggleMute(): void {
  const muted = !sound.muted;
  sound.setMuted(muted);
  store.setFlags({ mute: muted });
  view.setMuted(muted);
}

/* ---------- input controllers ---------- */

const inputCallbacks = {
  getGame: () => game,
  tryPlace,
  onSelect: setSelected,
  getSelected: () => selected,
  invalidFeedback: () => sound.invalid(),
  isLocked: () => paused || game.over,
};

const drag = new DragController(view, inputCallbacks);
void drag;
const keyboard = new KeyboardController(view, {
  ...inputCallbacks,
  togglePause: () => setPaused(!paused),
  toggleMute,
});

view.pauseBtn.addEventListener('click', () => setPaused(true));
view.muteBtn.addEventListener('click', toggleMute);
view.resumeBtn.addEventListener('click', () => setPaused(false));
view.restartBtn.addEventListener('click', restart);
view.playAgainBtn.addEventListener('click', restart);
view.soundToggleBtn.addEventListener('click', toggleMute);
view.fxToggleBtn.addEventListener('click', () => {
  const lite = store.flags().fx !== 'lite';
  store.setFlags({ fx: lite ? 'lite' : 'auto' });
  view.setFxLite(lite);
});

// keyboard focus inside portal iframes
document.body.tabIndex = -1;
window.addEventListener('pointerdown', () => window.focus(), { passive: true });

/* ---------- perf guard (ui-spec §6) ----------
   Sample frame times for the first seconds; two consecutive sub-45fps windows
   switch on the effects-lite mode automatically (manual toggle in pause). */
function startFrameSampler(): void {
  if (store.flags().fx === 'lite') return;
  let frames = 0;
  let windowStart = performance.now();
  let badWindows = 0;
  let samples = 0;
  const tick = (now: number) => {
    frames++;
    if (now - windowStart >= 1000) {
      const fps = (frames * 1000) / (now - windowStart);
      badWindows = fps < 45 ? badWindows + 1 : 0;
      frames = 0;
      windowStart = now;
      samples++;
      if (badWindows >= 2) {
        view.setFxLite(true);
        return;
      }
      if (samples >= 10) return; // decided: device is fine
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/* ---------- boot ---------- */

renderAll();
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    document.getElementById('splash')?.classList.add('done');
    setTimeout(() => document.getElementById('splash')?.remove(), 350);
    ads.loadingStop();
    ads.gameplayStart();
    document.body.focus();
    startFrameSampler();
  });
});
