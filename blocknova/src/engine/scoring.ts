/** game-design.md §4 — scoring.
 *
 *  Placement: 1 point per cell.
 *  Clear: 10 per line × simultaneity multiplier (1 line ×1 / 2 lines ×2.5 / 3+ ×4),
 *  then × combo multiplier (1 + combo × 0.5), rounded once at the end.
 *
 *  Combo semantics: `combo` counts consecutive clearing placements *before* the
 *  current one (a non-clearing placement resets it to 0). So the first clear in
 *  a chain scores ×1.0 and the display badge shows combo+1 afterwards.
 */

export function simultaneityMultiplier(lines: number): number {
  if (lines >= 3) return 4;
  if (lines === 2) return 2.5;
  if (lines === 1) return 1;
  return 0;
}

export function placementScore(cells: number): number {
  return cells;
}

export function clearScore(lines: number, comboBefore: number): number {
  if (lines <= 0) return 0;
  const base = 10 * lines * simultaneityMultiplier(lines);
  return Math.round(base * (1 + comboBefore * 0.5));
}
