import { mulberry32 } from './rng';

/** game-design.md §12 — 3 weekly quests, deterministic per ISO week
 *  (Zeigarnik + goal setting). Templates: clear N lines / trigger N novas /
 *  play N dailies, each scaled by the week's seed. */

export interface QuestDef {
  key: 'lines' | 'nova' | 'daily';
  target: number;
  /** 'shield' grants +1 shield (cap applies); 'badge' is a cosmetic check. */
  reward: 'shield' | 'badge';
}

/** ISO-8601 week of the KST calendar day containing `nowMs`,
 *  encoded as isoYear*100 + week (e.g. 202628). */
export function isoWeekId(nowMs: number): number {
  const kst = new Date(nowMs + 9 * 3600_000);
  const d = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7)); // nearest Thursday
  const yearStart = Date.UTC(d.getUTCFullYear(), 0, 1);
  const week = Math.ceil(((d.getTime() - yearStart) / 86400_000 + 1) / 7);
  return d.getUTCFullYear() * 100 + week;
}

/** Deterministic 3-quest set for a week id — same week, same quests. */
export function weeklyQuests(weekId: number): QuestDef[] {
  const rng = mulberry32(weekId >>> 0);
  const lines = 50 + Math.floor(rng() * 4) * 10; // 50/60/70/80
  const nova = 3 + Math.floor(rng() * 3); // 3/4/5
  const daily = 2 + Math.floor(rng() * 3); // 2/3/4
  return [
    { key: 'lines', target: lines, reward: 'shield' },
    { key: 'nova', target: nova, reward: 'badge' },
    { key: 'daily', target: daily, reward: 'shield' },
  ];
}
