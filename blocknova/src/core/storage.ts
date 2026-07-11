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
