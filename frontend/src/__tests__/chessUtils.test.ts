import { describe, it, expect } from 'vitest';
import { calculateMaterialFromFen } from '../utils/chessUtils';

describe('calculateMaterialFromFen', () => {
  it('calculates initial board material with 0 differential and no captured pieces', () => {
    const startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    const result = calculateMaterialFromFen(startFen);

    expect(result.whiteMaterial).toBe(39); // 8*1 + 2*3 + 2*3 + 2*5 + 9 = 8 + 6 + 6 + 10 + 9 = 39
    expect(result.blackMaterial).toBe(39);
    expect(result.whiteAdvantage).toBe(0);
    expect(result.blackAdvantage).toBe(0);
    expect(result.whiteCaptures).toEqual([]);
    expect(result.blackCaptures).toEqual([]);
  });

  it('correctly calculates captured pieces and material advantage after White captures a queen', () => {
    // Black is missing queen (q)
    const fen = 'rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    const result = calculateMaterialFromFen(fen);

    expect(result.whiteMaterial).toBe(39);
    expect(result.blackMaterial).toBe(30);
    expect(result.whiteAdvantage).toBe(9);
    expect(result.blackAdvantage).toBe(0);
    expect(result.whiteCaptures).toEqual(['q']);
    expect(result.blackCaptures).toEqual([]);
  });

  it('correctly tracks multiple captured pieces ordered by piece value', () => {
    // Black missing 2 pawns, 1 knight, 1 queen
    const fen = 'r1bqkbnr/ppp1pp1p/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    const result = calculateMaterialFromFen(fen);

    expect(result.whiteMaterial).toBe(39);
    expect(result.blackMaterial).toBe(39 - 2 - 3); // 34 (queen is still there 'q', b8 knight missing, d7/g7 pawns missing)
    expect(result.whiteAdvantage).toBe(5);
    expect(result.whiteCaptures).toEqual(['n', 'p', 'p']);
  });

  it('handles empty or malformed FEN gracefully without throwing', () => {
    const result = calculateMaterialFromFen('');
    expect(result.whiteMaterial).toBe(0);
    expect(result.blackMaterial).toBe(0);
    expect(result.whiteAdvantage).toBe(0);
    expect(result.blackAdvantage).toBe(0);
  });
});
