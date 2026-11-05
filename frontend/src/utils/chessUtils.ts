import { PieceSymbol } from '../types/chess';

export interface MaterialStatus {
  whiteCaptures: PieceSymbol[]; // pieces captured by White (black pieces missing from board)
  blackCaptures: PieceSymbol[]; // pieces captured by Black (white pieces missing from board)
  whiteMaterial: number;
  blackMaterial: number;
  whiteAdvantage: number; // >0 if White leads
  blackAdvantage: number; // >0 if Black leads
}

const PIECE_VALUES: Record<string, number> = {
  p: 1,
  n: 3,
  b: 3,
  r: 5,
  q: 9,
};

const INITIAL_PIECES: Record<string, number> = {
  P: 8,
  N: 2,
  B: 2,
  R: 2,
  Q: 1,
  p: 8,
  n: 2,
  b: 2,
  r: 2,
  q: 1,
};

export function calculateMaterialFromFen(fen: string): MaterialStatus {
  const placement = fen.split(' ')[0] || '';
  const currentCounts: Record<string, number> = {
    P: 0,
    N: 0,
    B: 0,
    R: 0,
    Q: 0,
    p: 0,
    n: 0,
    b: 0,
    r: 0,
    q: 0,
  };

  for (const char of placement) {
    if (char in currentCounts) {
      currentCounts[char] += 1;
    }
  }

  // White captures (Black pieces that are missing)
  const whiteCaptures: PieceSymbol[] = [];
  ['q', 'r', 'b', 'n', 'p'].forEach((p) => {
    const missing = Math.max(0, INITIAL_PIECES[p] - currentCounts[p]);
    for (let i = 0; i < missing; i++) {
      whiteCaptures.push(p as PieceSymbol);
    }
  });

  // Black captures (White pieces that are missing)
  const blackCaptures: PieceSymbol[] = [];
  ['Q', 'R', 'B', 'N', 'P'].forEach((p) => {
    const missing = Math.max(0, INITIAL_PIECES[p] - currentCounts[p]);
    for (let i = 0; i < missing; i++) {
      blackCaptures.push(p as PieceSymbol);
    }
  });

  let whiteMaterial = 0;
  let blackMaterial = 0;

  ['P', 'N', 'B', 'R', 'Q'].forEach((p) => {
    whiteMaterial += currentCounts[p] * PIECE_VALUES[p.toLowerCase()];
  });

  ['p', 'n', 'b', 'r', 'q'].forEach((p) => {
    blackMaterial += currentCounts[p] * PIECE_VALUES[p];
  });

  const diff = whiteMaterial - blackMaterial;

  return {
    whiteCaptures,
    blackCaptures,
    whiteMaterial,
    blackMaterial,
    whiteAdvantage: diff > 0 ? diff : 0,
    blackAdvantage: diff < 0 ? -diff : 0,
  };
}
