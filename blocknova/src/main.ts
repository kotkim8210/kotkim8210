import './style.css';
import { Game, type MoveResult } from './engine/game';
import { randomSeed } from './engine/rng';
import { idx } from './engine/board';
import { goldenBoard, goldenTray, GOLDEN_PRECHARGE } from './engine/golden';
import { kstDayNumber, dailyPieces, dailySeed, starsFor, shareText } from './engine/daily';
import { store } from './core/storage';
import { SoundEngine } from './core/audio';
import { vibrate } from './core/device';
import { t } from './core/i18n';
import { ads } from './ads/adapter';
import { View } from './ui/view';
import { DragController } from './ui/drag';
import { KeyboardController } from './ui/keyboard';
import { Coach } from './ui/coach';

ads.init();
ads.loadingStart();

type Mode = 'classic' | 'daily';

const sound = new SoundEngine(store.flags().mute);
const view = new View(document.getElementById('app')!);

let mode: Mode = 'classic';
let dailyDay = 0;
let startingBest = store.best().classic;
let paused = false;
let selected: number | null = null;
let movesThisRun = 0;

/* ---------- golden first move (game-design §11) ---------- */

let coach: Coach | null = null;
let coachStep = 0; // 0 = inactive

const isGoldenRun = () => !store.flags().firstRunDone && mode === 'classic';

function newClassicGame(): Game {
  startingBest = store.best().classic;
  if (isGoldenRun()) {
    return new Game({
      board: goldenBoard(),
      tray: goldenTray(),
      gauge: GOLDEN_PRECHARGE,
      seed: randomSeed(),
      best: startingBest,
    });
  }
  return new Game({ seed: randomSeed(), best: startingBest });
}

function positionCoach(): void {
  if (!coach || coachStep === 0) return;
  if (coachStep === 1) {
    coach.show(view.slotRect(0), t('coach_drag'));
  } else if (coachStep === 2) {
    const a = view.cellRect(idx(7, 8));
    const b = view.cellRect(idx(8, 8));
    coach.show(new DOMRect(a.left, a.top, a.width, b.bottom - a.top), t('coach_drop'));
  } else {
    coach.show(view.novaTrackRect(), t('coach_nova'));
  }
}

function startCoach(): void {
  if (coach) return;
  coach = new Coach(endCoach);
  coachStep = 1;
  positionCoach();
  window.addEventListener('resize', positionCoach);
}

function advanceCoach(step: number): void {
  if (coachStep > 0 && step > coachStep) {
    coachStep = step;
    positionCoach();
  }
}

function endCoach(): void {
  coachStep = 0;
  coach?.destroy();
  coach = null;
  store.setFlags({ firstRunDone: true });
  view.setBonusChip(false);
  window.removeEventListener('resize', positionCoach);
}

let game = newClassicGame();
view.setMuted(store.flags().mute);
view.setFxLite(store.flags().fx === 'lite');
if (isGoldenRun()) view.setBonusChip(true);

/* ---------- rendering ---------- */

function updateDailySubline(): void {
  view.setSubline(
    mode === 'daily'
      ? `${t('daily_title', { n: dailyDay })} · ${t('daily_left', { k: game.remainingPieces() })}`
      : null,
  );
}

function renderAll(): void {
  view.renderBoard(game.board);
  view.renderTray(game.tray, game.placeablePieces(), selected);
  view.setScore(game.score, false);
  view.setBest(game.best);
  view.setCombo(game.combo);
  view.setNova(game.gauge, game.gaugeIsFull());
  updateDailySubline();
  keyboard.refresh();
}

function setSelected(i: number | null): void {
  selected = i;
  if (i !== null) advanceCoach(2);
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
  movesThisRun += 1;
  view.renderBoard(game.board);
  view.renderTray(game.tray, game.placeablePieces(), selected);
  keyboard.refresh();
  view.markPlaced(move.placed);

  sound.place();
  vibrate(15);

  view.setScore(game.score);
  view.setCombo(move.combo);
  view.setNova(game.gauge, move.gaugeFull);
  updateDailySubline();

  const removed = [...move.clearedCells, ...move.novaCells];
  if (removed.length > 0) {
    view.setBonusChip(false);
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
    if (lines >= 2 && !move.nova) {
      view.edgeGlow();
      sound.bigClear();
    }
  }

  if (move.nova && move.novaCenter) {
    view.novaFx(move.novaCenter.row * 9 + move.novaCenter.col);
    sound.nova();
    vibrate([20, 30, 60]);
    ads.happytime(); // §adapter: happytime on nova explosion
  }

  if (mode === 'classic' && move.newBest && startingBest > 0) {
    view.setBest(game.best, true);
    sound.fanfare();
    ads.happytime(); // new record
  } else {
    view.setBest(game.best);
  }
  if (mode === 'classic' && game.best > store.best().classic) {
    store.setBest({ classic: game.best });
  }

  if (move.perfectClear) {
    view.floatScore(t('perfect'), true);
    view.confetti();
    ads.happytime(); // perfect clear
  }

  // coach: after the first (double-clear) move point at the nova bar,
  // and end after the 3rd move (game-design §11)
  if (coachStep > 0) {
    if (movesThisRun >= 3) endCoach();
    else if (movesThisRun >= 1) advanceCoach(3);
  }

  if (move.gameOver) {
    setTimeout(finishGame, 450);
  }
}

function finishGame(): void {
  ads.gameplayStop();
  store.addStats({
    games: 1,
    totalScore: game.score,
    novaTotal: game.novaCount,
    linesTotal: game.linesTotal,
  });

  if (mode === 'daily') {
    const rec = store.daily();
    const first = rec.day !== dailyDay;
    const stars = starsFor(game.score);
    if (first) {
      store.setDaily({
        day: dailyDay,
        score: game.score,
        stars,
        novaCount: game.novaCount,
        retried: false,
      });
    }
    if (game.survived) {
      sound.fanfare();
      view.confetti();
    } else {
      sound.gameOver();
    }
    const recNow = store.daily();
    view.showGameOver({
      title: t('daily_title', { n: dailyDay }),
      score: game.score,
      metaLine: `NOVA ×${game.novaCount}`,
      isNewBest: false,
      stars,
      banner: game.survived ? t('daily_survived') : '',
      note: first ? '' : t('daily_recorded'),
      buttons: { share: true, retry: true, retryDisabled: recNow.retried, classic: true },
    });
    return;
  }

  sound.gameOver();
  store.setBest({ classic: game.best });
  const isNewBest = game.score > startingBest;
  if (isNewBest && startingBest > 0) view.confetti();
  view.showGameOver({
    title: t('game_over'),
    score: game.score,
    metaLine: `${t('best')} ${game.best}`,
    isNewBest,
    buttons: { playAgain: true },
  });
}

function restart(): void {
  if (mode === 'daily') {
    backToClassic();
    return;
  }
  game = newClassicGame();
  selected = null;
  paused = false;
  movesThisRun = 0;
  view.showGameOver(null);
  view.showPause(false);
  if (isGoldenRun()) view.setBonusChip(true);
  renderAll();
  ads.gameplayStart();
}

/* ---------- daily mode (game-design §6) ---------- */

function beginDailyRun(): void {
  mode = 'daily';
  dailyDay = kstDayNumber();
  movesThisRun = 0;
  selected = null;
  paused = false;
  if (coachStep > 0) endCoach();
  game = new Game({ queue: dailyPieces(dailyDay), seed: dailySeed(dailyDay) });
  view.showGameOver(null);
  view.showPause(false);
  view.setModeChip(t('daily_title', { n: dailyDay }));
  renderAll();
  ads.gameplayStart();
}

function enterDaily(): void {
  const day = kstDayNumber();
  const rec = store.daily();
  if (rec.day === day) {
    // official run already recorded today — show the result card
    view.setModeChip(t('daily_title', { n: day }));
    dailyDay = day;
    view.showGameOver({
      title: t('daily_title', { n: day }),
      score: rec.score,
      metaLine: `NOVA ×${rec.novaCount}`,
      isNewBest: false,
      stars: rec.stars,
      note: t('daily_recorded'),
      buttons: { share: true, retry: true, retryDisabled: rec.retried, classic: true },
    });
    return;
  }
  beginDailyRun();
}

function backToClassic(): void {
  mode = 'classic';
  view.setModeChip(null);
  view.setSubline(null);
  view.showGameOver(null);
  restart();
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch {
      return false;
    }
  }
}

function shareDaily(): void {
  const rec = store.daily();
  const url = `${location.origin}${location.pathname}`;
  const text = shareText(rec.day, rec.score, rec.stars, rec.novaCount, url);
  void copyText(text).then((ok) => view.toast(ok ? t('copied') : text));
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

// coach step 1 → 2 as soon as the piece is picked up
view.slots.forEach((slot) => {
  slot.addEventListener('pointerdown', () => advanceCoach(2), { capture: true });
});

view.pauseBtn.addEventListener('click', () => setPaused(true));
view.muteBtn.addEventListener('click', toggleMute);
view.dailyBtn.addEventListener('click', enterDaily);
view.resumeBtn.addEventListener('click', () => setPaused(false));
view.restartBtn.addEventListener('click', restart);
view.playAgainBtn.addEventListener('click', restart);
view.shareBtn.addEventListener('click', shareDaily);
view.retryBtn.addEventListener('click', () => {
  // §8: daily retry is a rewarded hook, once per day; the record stays first-run
  ads.showRewarded((ok) => {
    if (!ok) return;
    store.setDaily({ retried: true });
    beginDailyRun();
  });
});
view.classicBtn.addEventListener('click', () => {
  if (mode === 'daily') backToClassic();
  else {
    view.showGameOver(null);
    view.setModeChip(null);
  }
});
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
    if (isGoldenRun()) startCoach();
    startFrameSampler();
  });
});
