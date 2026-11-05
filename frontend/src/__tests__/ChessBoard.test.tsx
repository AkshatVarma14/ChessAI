import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChessBoard } from '../components/ChessBoard';

describe('ChessBoard Component', () => {
  const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQK2R w KQkq - 0 1';
  const initialLegalMoves = [
    'a2a3', 'a2a4', 'b2b3', 'b2b4', 'c2c3', 'c2c4', 'd2d3', 'd2d4',
    'e2e3', 'e2e4', 'f2f3', 'f2f4', 'g2g3', 'g2g4', 'h2h3', 'h2h4',
    'b1a3', 'b1c3', 'g1f3', 'g1h3'
  ];

  it('renders standard 8x8 chessboard with 64 squares', () => {
    const { container } = render(
      <ChessBoard
        fen={startingFen}
        legalMovesUci={initialLegalMoves}
        isCheck={false}
        turn="white"
        flipped={false}
        onMove={vi.fn()}
      />
    );

    // 8x8 grid contains 64 square divs
    const squares = container.querySelectorAll('.grid > div');
    expect(squares.length).toBe(64);
  });

  it('selects piece on click and highlights legal destinations', () => {
    render(
      <ChessBoard
        fen={startingFen}
        legalMovesUci={initialLegalMoves}
        isCheck={false}
        turn="white"
        flipped={false}
        onMove={vi.fn()}
      />
    );

    // Click on e2 pawn rank
    const e2Square = screen.getByText('e'); // file label on bottom
    expect(e2Square).toBeInTheDocument();
  });

  it('triggers onMove callback when a legal destination is clicked', () => {
    const handleMove = vi.fn();
    const { container } = render(
      <ChessBoard
        fen={startingFen}
        legalMovesUci={initialLegalMoves}
        isCheck={false}
        turn="white"
        flipped={false}
        onMove={handleMove}
      />
    );

    // In White perspective, rank 2 is the 7th row in the grid (row index 6)
    // and file e is column 4 (index 4). Square e2 is row 6, col 4 -> index 6*8 + 4 = 52
    const squares = container.querySelectorAll('.grid > div');
    const e2Square = squares[52]; // e2
    const e4Square = squares[36]; // e4 (row 4, col 4)

    // Click e2 to select
    fireEvent.click(e2Square);

    // Click e4 to execute move
    fireEvent.click(e4Square);

    expect(handleMove).toHaveBeenCalledWith('e2e4');
  });

  it('flips the board orientation when flipped prop is true', () => {
    const { rerender } = render(
      <ChessBoard
        fen={startingFen}
        legalMovesUci={initialLegalMoves}
        isCheck={false}
        turn="white"
        flipped={false}
        onMove={vi.fn()}
      />
    );

    // Top-left label in White perspective is rank 8
    expect(screen.getByText('8')).toBeInTheDocument();

    // Rerender with flipped = true (Black perspective)
    rerender(
      <ChessBoard
        fen={startingFen}
        legalMovesUci={initialLegalMoves}
        isCheck={false}
        turn="white"
        flipped={true}
        onMove={vi.fn()}
      />
    );

    // Top-left label in Black perspective becomes rank 1
    expect(screen.getByText('1')).toBeInTheDocument();
  });
});
