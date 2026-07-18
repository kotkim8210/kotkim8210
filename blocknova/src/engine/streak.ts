/** game-design.md §12 — daily streak with shields (loss aversion + buffer).
 *  A play day = any finished run (KST day granularity, see daily.ts).
 *  Every 7 consecutive days grants 1 shield (max 2); a missed day silently
 *  consumes a shield instead of breaking the streak ("지켜졌어요"). */

export const MAX_SHIELDS = 2;

export interface StreakState {
  current: number;
  max: number;
  /** kstDayNumber of the last played day; -9999 = never played. */
  lastDay: number;
  shields: number;
}

export const FRESH_STREAK: StreakState = { current: 0, max: 0, lastDay: -9999, shields: 0 };

export interface ReconcileResult {
  state: StreakState;
  shieldsUsed: number;
  streakLost: boolean;
}

/** Settle any missed days between lastDay and today (exclusive). Shields are
 *  consumed one per missed day; if misses remain the streak resets to 0.
 *  Idempotent: after settling, lastDay advances to today-1 so a later call
 *  has nothing left to consume. Does NOT mark today as played. */
export function reconcileStreak(s: StreakState, today: number): ReconcileResult {
  if (s.lastDay < -9000 || s.lastDay >= today - 1) {
    return { state: { ...s }, shieldsUsed: 0, streakLost: false };
  }
  let misses = today - 1 - s.lastDay;
  let shields = s.shields;
  let shieldsUsed = 0;
  while (misses > 0 && shields > 0) {
    shields -= 1;
    shieldsUsed += 1;
    misses -= 1;
  }
  const streakLost = misses > 0 && s.current > 0;
  return {
    state: {
      current: streakLost ? 0 : s.current,
      max: s.max,
      lastDay: today - 1,
      shields,
    },
    shieldsUsed,
    streakLost,
  };
}

export interface PlayResult {
  state: StreakState;
  extended: boolean;
  shieldEarned: boolean;
}

/** Mark today as played. Call reconcileStreak first (or use advanceStreak). */
export function recordPlay(s: StreakState, today: number): PlayResult {
  if (s.lastDay === today) {
    return { state: { ...s }, extended: false, shieldEarned: false };
  }
  const current = s.current + 1;
  let shields = s.shields;
  // §12: a shield every 7 consecutive days, capped at 2
  const shieldEarned = current % 7 === 0 && shields < MAX_SHIELDS;
  if (shieldEarned) shields += 1;
  return {
    state: { current, max: Math.max(s.max, current), lastDay: today, shields },
    extended: true,
    shieldEarned,
  };
}

/** Convenience: settle missed days, then mark today as played. */
export function advanceStreak(
  s: StreakState,
  today: number,
): ReconcileResult & PlayResult {
  const rec = reconcileStreak(s, today);
  const play = recordPlay(rec.state, today);
  return { ...rec, ...play, state: play.state };
}
