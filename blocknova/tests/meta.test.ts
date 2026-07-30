import { describe, expect, it } from 'vitest';
import { applyXp, FRESH_META, L1_PRECHARGE, rankFor, xpThreshold } from '../src/engine/meta';
import { advanceStreak, FRESH_STREAK, reconcileStreak, recordPlay } from '../src/engine/streak';
import { isoWeekId, weeklyQuests } from '../src/engine/quests';
import { Game, PERFECT_BONUS, REVIVE_CELLS } from '../src/engine/game';
import { pieceByName } from '../src/engine/pieces';
import { boardFrom } from './helpers';

describe('XP / level / rank (game-design §12·§13)', () => {
  it('threshold samples: L1→2=100, L2→3=264, L5→6=952', () => {
    expect(xpThreshold(1)).toBe(100);
    expect(xpThreshold(2)).toBe(264);
    expect(xpThreshold(5)).toBe(952);
  });

  it('L1 starts 30% pre-charged and levels carry over remainder', () => {
    expect(FRESH_META).toEqual({ xp: 30, level: 1 });
    expect(L1_PRECHARGE).toBe(30);
    const up = applyXp(FRESH_META, 75); // 30+75=105 ≥ 100 → L2, xp 5
    expect(up.meta).toEqual({ xp: 5, level: 2 });
    expect(up.levelsGained).toBe(1);
    // big grant can skip multiple levels: 5+264+100... L2 needs 264
    const jump = applyXp(up.meta, 264 + 100);
    expect(jump.meta.level).toBe(3);
    expect(jump.meta.xp).toBe(105);
  });

  it('rank ladder: Spark/Comet/Star/Supernova/Quasar/Nova Master', () => {
    expect(rankFor(1)).toBe('Spark');
    expect(rankFor(4)).toBe('Spark');
    expect(rankFor(5)).toBe('Comet');
    expect(rankFor(10)).toBe('Star');
    expect(rankFor(20)).toBe('Supernova');
    expect(rankFor(35)).toBe('Quasar');
    expect(rankFor(50)).toBe('Nova Master');
    expect(rankFor(99)).toBe('Nova Master');
  });
});

describe('streak + shields (game-design §12·§13)', () => {
  it('grows daily and grants a shield every 7 days (cap 2)', () => {
    let s = { ...FRESH_STREAK };
    for (let day = 1; day <= 7; day++) {
      const r = advanceStreak(s, day);
      s = r.state;
      if (day === 7) expect(r.shieldEarned).toBe(true);
    }
    expect(s).toEqual({ current: 7, max: 7, lastDay: 7, shields: 1 });
    // same-day replay is a no-op
    const again = advanceStreak(s, 7);
    expect(again.state).toEqual(s);
    expect(again.extended).toBe(false);
  });

  it('one missed day consumes one shield and keeps the streak', () => {
    const s = { current: 7, max: 7, lastDay: 10, shields: 1 };
    const r = advanceStreak(s, 12); // day 11 missed
    expect(r.shieldsUsed).toBe(1);
    expect(r.streakLost).toBe(false);
    expect(r.state).toEqual({ current: 8, max: 8, lastDay: 12, shields: 0 });
  });

  it('with no shields the streak resets to 0 (next play starts at 1)', () => {
    const s = { current: 9, max: 9, lastDay: 10, shields: 0 };
    const rec = reconcileStreak(s, 12);
    expect(rec.streakLost).toBe(true);
    expect(rec.state.current).toBe(0);
    const play = recordPlay(rec.state, 12);
    expect(play.state.current).toBe(1);
    expect(play.state.max).toBe(9);
  });

  it('two missed days eat two shields; three missed days break through', () => {
    const survives = advanceStreak({ current: 14, max: 14, lastDay: 10, shields: 2 }, 13);
    expect(survives.shieldsUsed).toBe(2);
    expect(survives.state.current).toBe(15);
    const breaks = advanceStreak({ current: 14, max: 14, lastDay: 10, shields: 2 }, 14);
    expect(breaks.shieldsUsed).toBe(2);
    expect(breaks.streakLost).toBe(true);
    expect(breaks.state.current).toBe(1);
  });
});

describe('weekly quests (game-design §12·§13)', () => {
  it('same ISO week → same 3 quests; template targets in range', () => {
    const monday = Date.UTC(2026, 6, 6); // 2026-07-06 (Mon)
    const friday = Date.UTC(2026, 6, 10);
    expect(isoWeekId(monday)).toBe(isoWeekId(friday));
    const a = weeklyQuests(isoWeekId(monday));
    const b = weeklyQuests(isoWeekId(friday));
    expect(a).toEqual(b);
    expect(a.map((q) => q.key)).toEqual(['lines', 'nova', 'daily']);
    expect([50, 60, 70, 80]).toContain(a[0].target);
    expect([3, 4, 5]).toContain(a[1].target);
    expect([2, 3, 4]).toContain(a[2].target);
  });

  it('week id changes across Sunday→Monday (KST) boundary', () => {
    // 2026-07-12 is a Sunday; 2026-07-13 a Monday (KST dates)
    const sunday = Date.UTC(2026, 6, 12, 3); // 12:00 KST Sunday
    const monday = Date.UTC(2026, 6, 13, 3);
    expect(isoWeekId(monday)).toBe(isoWeekId(sunday) + 1);
  });
});

describe('revive (monetization §2)', () => {
  it('clears 12 random cells and the run continues', () => {
    // Full board except (0,0) → tray unplaceable → over
    const rows = Array.from({ length: 9 }, (_, r) => (r === 0 ? '.########' : '#########'));
    const sq2 = pieceByName('sq2');
    const game = new Game({ board: boardFrom(rows), tray: [sq2, sq2, sq2], seed: 5 });
    expect(game.over).toBe(true);
    const removed = game.revive();
    expect(removed).toHaveLength(REVIVE_CELLS);
    expect(game.board.filter((v) => v === 0)).toHaveLength(1 + REVIVE_CELLS);
    expect(PERFECT_BONUS).toBe(1000);
  });
});
