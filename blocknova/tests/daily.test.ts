import { describe, expect, it } from 'vitest';
import {
  DAILY_EPOCH_UTC,
  DAILY_PIECE_COUNT,
  dailyPieces,
  dailySeed,
  kstDayNumber,
  shareText,
  starsFor,
  STAR_THRESHOLDS,
} from '../src/engine/daily';
import { Game } from '../src/engine/game';
import { pieceByName } from '../src/engine/pieces';
import { boardFrom } from './helpers';

describe('daily challenge (game-design §6)', () => {
  it('dayNumber is KST-midnight based with epoch 2026-08-01T00:00+09', () => {
    expect(kstDayNumber(DAILY_EPOCH_UTC)).toBe(0);
    expect(kstDayNumber(DAILY_EPOCH_UTC - 1)).toBe(-1);
    // 2026-08-01T12:00 KST → still day 0
    expect(kstDayNumber(Date.UTC(2026, 7, 1, 3, 0))).toBe(0);
    // 2026-08-02T00:00 KST → day 1
    expect(kstDayNumber(Date.UTC(2026, 7, 1, 15, 0))).toBe(1);
    // 2026-08-01T23:59 KST (= 14:59 UTC) → still day 0
    expect(kstDayNumber(Date.UTC(2026, 7, 1, 14, 59))).toBe(0);
  });

  it('piece sequence is deterministic per day (50 pieces, seed 20260801+n)', () => {
    expect(dailySeed(0)).toBe(20260801);
    const a = dailyPieces(7).map((p) => p.id);
    const b = dailyPieces(7).map((p) => p.id);
    expect(a).toEqual(b);
    expect(a).toHaveLength(DAILY_PIECE_COUNT);
    const other = dailyPieces(8).map((p) => p.id);
    expect(a).not.toEqual(other);
  });

  it('star thresholds 800/1600/2600/3800/5200', () => {
    expect(STAR_THRESHOLDS).toEqual([800, 1600, 2600, 3800, 5200]);
    expect(starsFor(0)).toBe(0);
    expect(starsFor(799)).toBe(0);
    expect(starsFor(800)).toBe(1);
    expect(starsFor(1600)).toBe(2);
    expect(starsFor(2600)).toBe(3);
    expect(starsFor(3800)).toBe(4);
    expect(starsFor(5199)).toBe(4);
    expect(starsFor(5200)).toBe(5);
  });

  it('share text follows the §7 format', () => {
    const text = shareText(12, 1875, 2, 3, 'https://example.com/');
    expect(text).toBe('Block Nova Daily #12\n⭐⭐☆☆☆ 1875점\nNOVA ×3\nhttps://example.com/');
  });
});

describe('daily queue mode (survival run)', () => {
  it('consumes the fixed sequence and reports survival when all pieces land', () => {
    const dot = pieceByName('dot');
    const game = new Game({ queue: [dot, dot, dot, dot] });
    expect(game.remainingPieces()).toBe(4);
    expect(game.placeAt(0, 0, 0)).not.toBeNull();
    expect(game.placeAt(1, 2, 2)).not.toBeNull();
    expect(game.placeAt(2, 4, 4)).not.toBeNull();
    // refill pulled the 4th and final piece
    expect(game.tray.filter(Boolean)).toHaveLength(1);
    const last = game.placeAt(0, 6, 6)!;
    expect(last.gameOver).toBe(true);
    expect(game.survived).toBe(true);
    expect(game.remainingPieces()).toBe(0);
  });

  it('a jammed board ends the run without survival', () => {
    // Checkerboard: single free cells only — dots fit, sq3 never does,
    // and no row/column can ever complete.
    const rows = Array.from({ length: 9 }, (_, r) =>
      Array.from({ length: 9 }, (_, c) => ((r + c) % 2 === 1 ? '#' : '.')).join(''),
    );
    const sq3 = pieceByName('sq3');
    const dot = pieceByName('dot');
    const game = new Game({ board: boardFrom(rows), queue: [dot, sq3, sq3] });
    const move = game.placeAt(0, 0, 0)!;
    expect(move.gameOver).toBe(true);
    expect(game.survived).toBe(false);
    expect(game.remainingPieces()).toBe(2);
  });
});
