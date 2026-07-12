import { PET_ART, type PetArt } from './petart';

/** Cosmic Friends — the pixel-art puzzle collection (publisher request).
 *
 *  A puzzle card on the board corner uncovers one tile at a time in real
 *  time as cells are cleared. Completing the picture zooms it up for a
 *  short cinematic, then adds the friend to the gallery. All artwork is
 *  original in-repo pixel data (see petart.ts) — zero asset files. */

export interface PetDef {
  emoji: string; // for toasts / compact UI
  key: string; // i18n name key (pet_N); flavor text key is flavor_N
  art: PetArt;
}

const EMOJI = ['🐶', '🐱', '🐰', '🦊', '🐼', '🐹', '🐧', '👽'];

export const PETS: PetDef[] = PET_ART.map((art, i) => ({
  emoji: EMOJI[i],
  key: `pet_${i}`,
  art,
}));

/** The reveal grid is 4×4 = 16 puzzle tiles per picture. */
export const PET_TILES = 16;

/** Cumulative cleared cells required to complete picture `index`.
 *  The first friend arrives within the first game or two (hook). */
export function petThreshold(index: number): number {
  return Math.round(80 + 140 * index + 15 * index * index);
}

export interface PetProgress {
  /** Completed pictures at this cell count. */
  unlocked: number;
  /** 0..1 fill of the current puzzle (1 when all are collected). */
  ratio: number;
  /** Uncovered tiles (0..PET_TILES) of the current puzzle. */
  tiles: number;
  /** Cells still needed for the next completion (0 when done). */
  needed: number;
  complete: boolean;
}

export function petProgress(cells: number): PetProgress {
  let unlocked = 0;
  while (unlocked < PETS.length && cells >= petThreshold(unlocked)) unlocked++;
  if (unlocked >= PETS.length) {
    return { unlocked, ratio: 1, tiles: PET_TILES, needed: 0, complete: true };
  }
  const base = unlocked === 0 ? 0 : petThreshold(unlocked - 1);
  const next = petThreshold(unlocked);
  const ratio = Math.max(0, Math.min(1, (cells - base) / (next - base)));
  return {
    unlocked,
    ratio,
    tiles: Math.min(PET_TILES - 1, Math.floor(ratio * PET_TILES)),
    needed: next - cells,
    complete: false,
  };
}
