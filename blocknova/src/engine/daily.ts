import { drawWeighted } from './bag';
import type { PieceDef } from './pieces';
import { PIECES } from './pieces';
import { mulberry32 } from './rng';

/** game-design.md §6 — daily challenge.
 *
 *  dayNumber = floor((KST today 00:00 − 2026-08-01T00:00+09:00) / 86400000)
 *  Piece sequence = mulberry32(20260801 + dayNumber), 50-piece survival.
 *  The sequence is generated up-front with plain weighted draws (no tray
 *  constraints) so every player gets the identical run for a given day.
 */

const KST_OFFSET_MS = 9 * 3600_000;
/** 2026-08-01T00:00+09:00 expressed in UTC ms. */
export const DAILY_EPOCH_UTC = Date.UTC(2026, 6, 31, 15, 0, 0);

/** UTC ms of KST midnight for the day containing `now`. */
export function kstStartOfDay(now: number): number {
  const kst = now + KST_OFFSET_MS;
  return Math.floor(kst / 86400_000) * 86400_000 - KST_OFFSET_MS;
}

export function kstDayNumber(now: number = Date.now()): number {
  return Math.floor((kstStartOfDay(now) - DAILY_EPOCH_UTC) / 86400_000);
}

export function dailySeed(dayNumber: number): number {
  return 20260801 + dayNumber;
}

export const DAILY_PIECE_COUNT = 50;

export function dailyPieces(dayNumber: number): PieceDef[] {
  const rng = mulberry32(dailySeed(dayNumber));
  return Array.from({ length: DAILY_PIECE_COUNT }, () => drawWeighted(PIECES, rng));
}

/** §6 star thresholds (hypothesis — changes must be documented). */
export const STAR_THRESHOLDS = [800, 1600, 2600, 3800, 5200];

export function starsFor(score: number): number {
  let stars = 0;
  for (const t of STAR_THRESHOLDS) if (score >= t) stars++;
  return stars;
}

/** game-design.md §7 — share text. */
export function shareText(dayNumber: number, score: number, stars: number, novaCount: number, url: string): string {
  const starBar = '⭐'.repeat(stars) + '☆'.repeat(5 - stars);
  return `Block Nova Daily #${dayNumber}\n${starBar} ${score}점\nNOVA ×${novaCount}\n${url}`;
}
