import React, { useState, useMemo } from 'react';
import { Color, PieceSymbol } from '../types/chess';
import { ChessSquare } from './ChessSquare';
import { PromotionDialog } from './PromotionDialog';

interface ChessBoardProps {
  fen: string;
  legalMovesUci: string[];
  isCheck: boolean;
  turn: Color;
  flipped: boolean;
  lastMoveUci?: string;
  onMove: (moveUci: string) => void;
  disabled?: boolean;
  children?: React.ReactNode;
}

export const ChessBoard: React.FC<ChessBoardProps> = ({
  fen,
  legalMovesUci,
  isCheck,
  turn,
  flipped,
  lastMoveUci,
  onMove,
  disabled = false,
  children,
}) => {
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [pendingPromotion, setPendingPromotion] = useState<{ from: string; to: string } | null>(
    null
  );

  // Parse FEN piece placement string into a mapping of square -> PieceSymbol
  const squarePieceMap = useMemo(() => {
    const map = new Map<string, PieceSymbol>();
    const placement = fen.split(' ')[0] || '';
    const ranks = placement.split('/');

    ranks.forEach((rankStr, rankIndex) => {
      const rankNum = 8 - rankIndex;
      let fileIndex = 0;

      for (let i = 0; i < rankStr.length; i++) {
        const char = rankStr[i];
        if (char >= '1' && char <= '8') {
          fileIndex += parseInt(char, 10);
        } else {
          const fileLetter = String.fromCharCode(97 + fileIndex);
          const square = `${fileLetter}${rankNum}`;
          map.set(square, char as PieceSymbol);
          fileIndex += 1;
        }
      }
    });

    return map;
  }, [fen]);

  // Find checked king's square if in check
  const checkedKingSquare = useMemo(() => {
    if (!isCheck) return null;
    const targetKing = turn === 'white' ? 'K' : 'k';
    for (const [sq, piece] of squarePieceMap.entries()) {
      if (piece === targetKing) return sq;
    }
    return null;
  }, [isCheck, turn, squarePieceMap]);

  // Compute legal destination squares for the currently selected piece
  const legalDestinations = useMemo(() => {
    if (!selectedSquare) return new Set<string>();
    const destinations = new Set<string>();

    for (const move of legalMovesUci) {
      if (move.startsWith(selectedSquare)) {
        // e.g. "e2e4" -> destination is "e4"
        const dest = move.slice(2, 4);
        destinations.add(dest);
      }
    }
    return destinations;
  }, [selectedSquare, legalMovesUci]);

  // Extract from and to of the last executed move
  const lastMoveSquares = useMemo(() => {
    if (!lastMoveUci || lastMoveUci.length < 4) return new Set<string>();
    return new Set([lastMoveUci.slice(0, 2), lastMoveUci.slice(2, 4)]);
  }, [lastMoveUci]);

  // Handle square clicks
  const handleSquareClick = (square: string) => {
    if (disabled) return;

    const piece = squarePieceMap.get(square);
    const isOwnPiece =
      piece && (turn === 'white' ? piece === piece.toUpperCase() : piece === piece.toLowerCase());

    if (selectedSquare) {
      if (selectedSquare === square) {
        // Deselect current square
        setSelectedSquare(null);
        return;
      }

      if (legalDestinations.has(square)) {
        // Check if this move requires a pawn promotion dialog
        const isPromotion = legalMovesUci.some(
          (m) => m.startsWith(selectedSquare + square) && m.length === 5
        );

        if (isPromotion) {
          setPendingPromotion({ from: selectedSquare, to: square });
          return;
        }

        // Execute standard move
        const moveUci = `${selectedSquare}${square}`;
        onMove(moveUci);
        setSelectedSquare(null);
        return;
      }

      // If user clicked another of their own pieces, switch selection
      if (isOwnPiece) {
        setSelectedSquare(square);
        return;
      }

      // Clicked on illegal destination
      setSelectedSquare(null);
    } else {
      // No square selected yet
      if (isOwnPiece) {
        setSelectedSquare(square);
      }
    }
  };

  const handlePromotionSelect = (promotedPiece: 'q' | 'r' | 'b' | 'n') => {
    if (pendingPromotion) {
      const moveUci = `${pendingPromotion.from}${pendingPromotion.to}${promotedPiece}`;
      onMove(moveUci);
      setPendingPromotion(null);
      setSelectedSquare(null);
    }
  };

  const handlePromotionCancel = () => {
    setPendingPromotion(null);
    setSelectedSquare(null);
  };

  // Files and Ranks ordering based on board orientation
  const files = flipped ? ['h', 'g', 'f', 'e', 'd', 'c', 'b', 'a'] : ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
  const ranks = flipped ? [1, 2, 3, 4, 5, 6, 7, 8] : [8, 7, 6, 5, 4, 3, 2, 1];

  return (
    <div
      data-testid="chess-board"
      aria-disabled={disabled}
      className={`relative w-full max-w-[560px] aspect-square rounded-xl overflow-hidden shadow-2xl border-4 border-slate-700 bg-slate-800 select-none ${
        disabled ? 'cursor-not-allowed' : ''
      }`}
    >
      <div className="grid grid-cols-8 grid-rows-8 w-full h-full">
        {ranks.map((rank, rankIdx) =>
          files.map((file, fileIdx) => {
            const square = `${file}${rank}`;
            const piece = squarePieceMap.get(square);
            const isLight = (file.charCodeAt(0) - 97 + rank) % 2 !== 0;

            const isSelected = selectedSquare === square;
            const isLegalTarget = legalDestinations.has(square);
            const isLastMove = lastMoveSquares.has(square);
            const isInCheck = checkedKingSquare === square;

            // Labels on board edge squares
            const showRankLabel = fileIdx === 0 ? String(rank) : undefined;
            const showFileLabel = rankIdx === 7 ? file : undefined;

            return (
              <ChessSquare
                key={square}
                square={square}
                isLight={isLight}
                piece={piece}
                isSelected={isSelected}
                isLegalTarget={isLegalTarget}
                isLastMove={isLastMove}
                isInCheck={isInCheck}
                showFileLabel={showFileLabel}
                showRankLabel={showRankLabel}
                onClick={() => handleSquareClick(square)}
              />
            );
          })
        )}
      </div>

      <PromotionDialog
        isOpen={pendingPromotion !== null}
        color={turn}
        onSelect={handlePromotionSelect}
        onCancel={handlePromotionCancel}
      />

      {children}
    </div>
  );
};
