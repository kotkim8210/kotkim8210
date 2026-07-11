import './style.css';
import { Game, type MoveResult } from './engine/game';
import { randomSeed } from './engine/rng';
import { idx } from './engine/board';
import { goldenBoard, goldenTray, GOLDEN_PRECHARGE } from './engine/golden';
import { kstDayNumber, dailyPieces, dailySeed, starsFor, shareText } from './engine/daily';
import { applyXp, rankFor, xpProgress } from './engine/meta';
import { advanceStreak, reconcileStreak, MAX_SHIELDS } from './engine/streak';
import { isoWeekId, weeklyQuests } from './engine/quests';
import { store, type QuestsStore } from './core/storage';
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
let reviveUsed = false;
/** Stats already credited for the current run (revive keeps the run going). */
let runRecorded = { any: false, score: 0, nova: 0, lines: 0 };

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

function updatePace(flash = false): void {
  const show = mode === 'classic' && startingBest > 0;
  view.setPace(show ? Math.min(1, game.score / startingBest) : null, flash);
}

function renderAll(): void {
  view.renderBoard(game.board);
  view.renderTray(game.tray, game.placeablePieces(), selected);
  view.setScore(game.score, false);
  view.setBest(game.best);
  view.setCombo(game.combo);
  view.setNova(game.gauge, game.gaugeIsFull());
  updateDailySubline();
  updatePace();
  keyboard.refresh();
}

/* ---------- retention meta (game-design §12) ---------- */

function currentQuests(): { defs: ReturnType<typeof weeklyQuests>; state: QuestsStore } {
  const week = isoWeekId(Date.now());
  let state = store.quests();
  if (state.week !== week) {
    state = { week, progress: [0, 0, 0], done: [false, false, false] };
    store.setQuests(state);
  }
  return { defs: weeklyQuests(week), state };
}

function questProgress(index: 0 | 1 | 2, delta: number): void {
  const { defs, state } = currentQuests();
  if (state.done[index]) return;
  const progress = [...state.progress] as QuestsStore['progress'];
  const done = [...state.done] as QuestsStore['done'];
  progress[index] = Math.min(defs[index].target, progress[index] + delta);
  if (progress[index] >= defs[index].target) {
    done[index] = true;
    view.toast(t('quest_done'));
    if (defs[index].reward === 'shield') {
      const s = store.streak();
      if (s.shields < MAX_SHIELDS) {
        store.setStreak({ shields: s.shields + 1 });
        view.setStreak(s.current, s.shields + 1);
      }
    }
  }
  store.setQuests({ week: state.week, progress, done });
}

function questLabels(): { label: string; progress: number; target: number; done: boolean }[] {
  const { defs, state } = currentQuests();
  const keys = { lines: 'q_lines', nova: 'q_nova', daily: 'q_daily' } as const;
  return defs.map((d, i) => ({
    label: t(keys[d.key], { n: d.target }),
    progress: state.progress[i],
    target: d.target,
    done: state.done[i],
  }));
}

function recordRunStats(): void {
  store.addStats({
    games: runRecorded.any ? 0 : 1,
    totalScore: game.score - runRecorded.score,
    novaTotal: game.novaCount - runRecorded.nova,
    linesTotal: game.linesTotal - runRecorded.lines,
  });
  runRecorded = { any: true, score: game.score, nova: game.novaCount, lines: game.linesTotal };
}

function refreshMetaChips(): void {
  const meta = store.meta();
  view.setLevel(meta.level, rankFor(meta.level), xpProgress(meta));
  const s = store.streak();
  view.setStreak(s.current, s.shields);
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
    // §12: 1 cleared cell = 1 XP (level-ups roll over)
    const xpRes = applyXp(store.meta(), removed.length);
    store.setMeta(xpRes.meta);
    if (xpRes.levelsGained > 0) {
      view.toast(t('level_up', { n: xpRes.meta.level, rank: rankFor(xpRes.meta.level) }));
    }
    view.setLevel(xpRes.meta.level, rankFor(xpRes.meta.level), xpProgress(xpRes.meta));
    questProgress(0, move.clearedRows.length + move.clearedCols.length);
    if (move.nova) questProgress(1, 1);
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
  updatePace(move.newBest);

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

function highlightChips(): string[] {
  const chips: string[] = [];
  if (game.novaCount > 0) chips.push(`⚡ NOVA ×${game.novaCount}`);
  if (game.maxCombo >= 2) chips.push(`🔗 ${t('combo')} ${game.maxCombo}`);
  return chips;
}

function finishGame(): void {
  ads.gameplayStop();
  recordRunStats();

  // §12: any finished run marks the KST day for the streak
  const streakRes = advanceStreak(store.streak(), kstDayNumber());
  store.setStreak(streakRes.state);
  view.setStreak(streakRes.state.current, streakRes.state.shields);
  if (streakRes.shieldsUsed > 0) view.toast(t('streak_kept'));
  else if (streakRes.shieldEarned) view.toast(t('shield_earned'));

  if (mode === 'daily') {
    questProgress(2, 1);
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
      highlights: highlightChips(),
      nextPieces: game.survived ? [] : game.upcomingPieces(3),
      buttons: { share: true, retry: true, retryDisabled: recNow.retried, classic: true },
    });
    return;
  }

  sound.gameOver();
  store.setBest({ classic: game.best });
  const isNewBest = game.score > startingBest;
  if (isNewBest && startingBest > 0) view.confetti();

  // §12 near-miss: distance to best + reveal of the upcoming pieces
  const gap = startingBest - game.score;
  const close = startingBest > 0 && gap > 0 && gap <= startingBest * 0.15;
  const gapText =
    startingBest > 0 && gap > 0
      ? { text: t('best_gap', { n: gap }) + (close ? ` · ${t('one_more')}` : ''), gold: close }
      : undefined;

  view.showGameOver({
    title: t('game_over'),
    score: game.score,
    metaLine: `${t('best')} ${game.best}`,
    isNewBest,
    gapText,
    highlights: highlightChips(),
    nextPieces: game.upcomingPieces(3),
    buttons: { playAgain: true, revive: !reviveUsed, daily: true },
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
  reviveUsed = false;
  runRecorded = { any: false, score: 0, nova: 0, lines: 0 };
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
  reviveUsed = true; // no revive in daily — the rewarded hook there is retry
  runRecorded = { any: false, score: 0, nova: 0, lines: 0 };
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
  if (next) view.renderQuests(questLabels());
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
view.reviveBtn.addEventListener('click', () => {
  // monetization §2: rewarded revive, once per run, 12 random cells removed
  ads.showRewarded((ok) => {
    if (!ok || reviveUsed) return;
    reviveUsed = true;
    const removed = game.revive();
    if (game.over) {
      // extremely unlucky removal — the run truly ends
      finishGame();
      return;
    }
    view.showGameOver(null);
    renderAll();
    const colorLookup = new Map<number, number>(removed.map((i) => [i, 4]));
    view.popCells(removed, colorLookup);
    sound.clear(0);
    ads.gameplayStart();
  });
});
view.dailyCardBtn.addEventListener('click', () => {
  view.showGameOver(null);
  enterDaily();
});
view.statsBtn.addEventListener('click', () => {
  const s = store.stats();
  const meta = store.meta();
  const streak = store.streak();
  const daily = store.daily();
  view.showStats([
    { label: t('st_best'), value: String(store.best().classic) },
    { label: t('st_games'), value: String(s.games) },
    { label: t('st_total'), value: String(s.totalScore) },
    { label: t('st_lines'), value: String(s.linesTotal) },
    { label: t('st_nova'), value: String(s.novaTotal) },
    { label: t('st_level'), value: `Lv.${meta.level} ${rankFor(meta.level)}` },
    { label: t('st_streak'), value: `🔥${streak.current} (max ${streak.max})` },
    { label: t('st_shields'), value: '🛡'.repeat(streak.shields) || '—' },
    { label: t('st_daily'), value: daily.day > -9000 ? `${'⭐'.repeat(daily.stars) || '0⭐'} ${daily.score}` : '—' },
  ]);
});
view.statsCloseBtn.addEventListener('click', () => view.showStats(null));
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

// settle missed streak days (shield auto-consumption, game-design §12)
const bootStreak = reconcileStreak(store.streak(), kstDayNumber());
store.setStreak(bootStreak.state);
refreshMetaChips();
currentQuests(); // week rollover check

renderAll();
requestAnimationFrame(() => {
  requestAnimationFrame(() => {
    document.getElementById('splash')?.classList.add('done');
    setTimeout(() => document.getElementById('splash')?.remove(), 350);
    ads.loadingStop();
    ads.gameplayStart();
    document.body.focus();
    if (isGoldenRun()) startCoach();
    if (bootStreak.shieldsUsed > 0) view.toast(t('streak_kept'));
    startFrameSampler();
  });
});
