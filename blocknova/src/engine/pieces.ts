import piecesData from '../../data/pieces.json';

export interface PieceDef {
  id: number;
  name: string;
  /** Row-major matrix of 0/1. */
  shape: number[][];
  cells: number;
  weight: number;
  /** Index into the gem color palette (0..5). */
  color: number;
}

export const GRID = piecesData.grid; // 9
export const TRAY_SIZE = piecesData.traySize; // 3
export const PIECES: PieceDef[] = piecesData.pieces;

const byName = new Map(PIECES.map((p) => [p.name, p]));

export function pieceByName(name: string): PieceDef {
  const p = byName.get(name);
  if (!p) throw new Error(`unknown piece: ${name}`);
  return p;
}

export function pieceById(id: number): PieceDef {
  const p = PIECES[id];
  if (!p || p.id !== id) {
    const found = PIECES.find((x) => x.id === id);
    if (!found) throw new Error(`unknown piece id: ${id}`);
    return found;
  }
  return p;
}
