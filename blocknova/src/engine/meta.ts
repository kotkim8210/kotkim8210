/** game-design.md §12 — level / XP / rank (competence + endowed progress).
 *  1 cleared cell = 1 XP. Threshold L→L+1 = round(100 × L^1.4).
 *  Level 1 starts pre-charged at 30%. */

export function xpThreshold(level: number): number {
  return Math.round(100 * Math.pow(level, 1.4));
}

/** Endowed progress: a fresh profile starts at L1 with 30% of the bar. */
export const L1_PRECHARGE = Math.round(xpThreshold(1) * 0.3); // 30

export interface MetaState {
  xp: number; // progress within the current level
  level: number;
}

export const FRESH_META: MetaState = { xp: L1_PRECHARGE, level: 1 };

export interface XpResult {
  meta: MetaState;
  levelsGained: number;
}

export function applyXp(meta: MetaState, gained: number): XpResult {
  let { xp, level } = meta;
  xp += Math.max(0, gained);
  let levelsGained = 0;
  while (xp >= xpThreshold(level)) {
    xp -= xpThreshold(level);
    level += 1;
    levelsGained += 1;
  }
  return { meta: { xp, level }, levelsGained };
}

const RANKS: [number, string][] = [
  [50, 'Nova Master'],
  [35, 'Quasar'],
  [20, 'Supernova'],
  [10, 'Star'],
  [5, 'Comet'],
  [1, 'Spark'],
];

export function rankFor(level: number): string {
  for (const [min, name] of RANKS) if (level >= min) return name;
  return 'Spark';
}

/** 0..1 progress toward the next level. */
export function xpProgress(meta: MetaState): number {
  return Math.max(0, Math.min(1, meta.xp / xpThreshold(meta.level)));
}
