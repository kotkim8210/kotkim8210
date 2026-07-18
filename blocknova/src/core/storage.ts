/** game-design.md §9 — all persistence under the `bn:` prefix.
 *  localStorage can throw inside sandboxed iframes; every access is guarded. */

const PREFIX = 'bn:';

export interface BestState {
  classic: number;
}
export interface FlagsState {
  firstRunDone: boolean;
  mute: boolean;
  /** 'auto' lets the frame sampler decide; 'lite' forces reduced effects. */
  fx: 'auto' | 'lite';
}
export interface StatsState {
  games: number;
  totalScore: number;
  novaTotal: number;
  linesTotal: number;
}
export interface DailyState {
  /** kstDayNumber of the recorded run; -9999 = never played. */
  day: number;
  score: number;
  stars: number;
  novaCount: number;
  retried: boolean;
}
export interface StreakStore {
  current: number;
  max: number;
  lastDay: number;
  shields: number;
}
export interface MetaStore {
  xp: number;
  level: number;
}
export interface QuestsStore {
  week: number;
  progress: [number, number, number];
  done: [boolean, boolean, boolean];
}
export interface PetsStore {
  /** Cumulative cleared cells feeding the cosmic egg. */
  cells: number;
}

function read<T extends object>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    if (!raw) return { ...fallback };
    return { ...fallback, ...(JSON.parse(raw) as Partial<T>) };
  } catch {
    return { ...fallback };
  }
}

function write(key: string, value: object): void {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    /* storage unavailable — play on without persistence */
  }
}

export const store = {
  best(): BestState {
    return read('best', { classic: 0 });
  },
  setBest(patch: Partial<BestState>): void {
    write('best', { ...store.best(), ...patch });
  },
  flags(): FlagsState {
    return read('flags', { firstRunDone: false, mute: false, fx: 'auto' });
  },
  setFlags(patch: Partial<FlagsState>): void {
    write('flags', { ...store.flags(), ...patch });
  },
  daily(): DailyState {
    return read('daily', { day: -9999, score: 0, stars: 0, novaCount: 0, retried: false });
  },
  setDaily(patch: Partial<DailyState>): void {
    write('daily', { ...store.daily(), ...patch });
  },
  streak(): StreakStore {
    return read('streak', { current: 0, max: 0, lastDay: -9999, shields: 0 });
  },
  setStreak(patch: Partial<StreakStore>): void {
    write('streak', { ...store.streak(), ...patch });
  },
  meta(): MetaStore {
    // L1 starts 30% pre-charged (game-design §12 endowed progress)
    return read('meta', { xp: 30, level: 1 });
  },
  setMeta(patch: Partial<MetaStore>): void {
    write('meta', { ...store.meta(), ...patch });
  },
  quests(): QuestsStore {
    return read('quests', { week: 0, progress: [0, 0, 0], done: [false, false, false] });
  },
  setQuests(patch: Partial<QuestsStore>): void {
    write('quests', { ...store.quests(), ...patch });
  },
  pets(): PetsStore {
    return read('pets', { cells: 0 });
  },
  addPetCells(n: number): void {
    write('pets', { cells: store.pets().cells + n });
  },
  stats(): StatsState {
    return read('stats', { games: 0, totalScore: 0, novaTotal: 0, linesTotal: 0 });
  },
  addStats(delta: Partial<StatsState>): void {
    const s = store.stats();
    write('stats', {
      games: s.games + (delta.games ?? 0),
      totalScore: s.totalScore + (delta.totalScore ?? 0),
      novaTotal: s.novaTotal + (delta.novaTotal ?? 0),
      linesTotal: s.linesTotal + (delta.linesTotal ?? 0),
    });
  },
};
