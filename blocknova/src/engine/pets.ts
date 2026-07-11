/** Cosmic Pets — the collectible goal system (publisher request).
 *
 *  A cosmic egg fills in real time as cells are cleared (any mode). When the
 *  cumulative cleared-cell count crosses a threshold, the egg hatches
 *  mid-game into a cute space pet, added to the gallery in the stats modal.
 *  Pure emoji + CSS: zero asset files, zero external requests.
 */

export interface PetDef {
  emoji: string;
  /** i18n key suffix (pet_0 … pet_11). */
  key: string;
}

export const PETS: PetDef[] = [
  { emoji: '🐶', key: 'pet_0' },
  { emoji: '🐱', key: 'pet_1' },
  { emoji: '🐰', key: 'pet_2' },
  { emoji: '🦊', key: 'pet_3' },
  { emoji: '🐼', key: 'pet_4' },
  { emoji: '🐹', key: 'pet_5' },
  { emoji: '🦉', key: 'pet_6' },
  { emoji: '🐢', key: 'pet_7' },
  { emoji: '🐧', key: 'pet_8' },
  { emoji: '🦄', key: 'pet_9' },
  { emoji: '🐉', key: 'pet_10' },
  { emoji: '👽', key: 'pet_11' },
];

/** Cumulative cleared cells required to hatch pet `index`.
 *  Ramp: the first friend arrives within the first game or two (hook),
 *  later ones take progressively longer (collection pacing). */
export function petThreshold(index: number): number {
  return Math.round(80 + 140 * index + 15 * index * index);
}

export interface PetProgress {
  /** How many pets are unlocked at this cell count. */
  unlocked: number;
  /** 0..1 fill of the current egg (1 when all pets are collected). */
  ratio: number;
  /** Cells still needed for the next hatch (0 when complete). */
  needed: number;
  complete: boolean;
}

export function petProgress(cells: number): PetProgress {
  let unlocked = 0;
  while (unlocked < PETS.length && cells >= petThreshold(unlocked)) unlocked++;
  if (unlocked >= PETS.length) {
    return { unlocked, ratio: 1, needed: 0, complete: true };
  }
  const base = unlocked === 0 ? 0 : petThreshold(unlocked - 1);
  const next = petThreshold(unlocked);
  return {
    unlocked,
    ratio: Math.max(0, Math.min(1, (cells - base) / (next - base))),
    needed: next - cells,
    complete: false,
  };
}
