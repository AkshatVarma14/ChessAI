import React from 'react';
import { PieceSymbol } from '../types/chess';
import { ChessPiece } from './ChessPiece';

interface ChessSquareProps {
  square: string;
  isLight: boolean;
  piece?: PieceSymbol;
  isSelected: boolean;
  isLegalTarget: boolean;
  isLastMove: boolean;
  isInCheck: boolean;
  showFileLabel?: string;
  showRankLabel?: string;
  onClick: () => void;
}

export const ChessSquare: React.FC<ChessSquareProps> = ({
  square,
  isLight,
  piece,
  isSelected,
  isLegalTarget,
  isLastMove,
  isInCheck,
  showFileLabel,
  showRankLabel,
  onClick,
}) => {
  // Classic board palette: warm wood / tournaments
  const baseBg = isLight ? 'bg-[#eeeed2]' : 'bg-[#769656]';
  const labelColor = isLight ? 'text-[#769656]' : 'text-[#eeeed2]';

  return (
    <div
      data-square={square}
      data-testid={`square-${square}`}
      onClick={onClick}
      className={`relative w-full h-full flex items-center justify-center cursor-pointer select-none transition-colors duration-150 ${baseBg}`}
    >
      {/* Last move highlight */}
      {isLastMove && (
        <div className="absolute inset-0 bg-yellow-300 bg-opacity-40 pointer-events-none" />
      )}

      {/* Selected square highlight */}
      {isSelected && (
        <div className="absolute inset-0 bg-yellow-400 bg-opacity-60 ring-2 ring-yellow-500 ring-inset pointer-events-none" />
      )}

      {/* Check indicator on King */}
      {isInCheck && (
        <div className="absolute inset-0 bg-radial from-red-600 to-transparent opacity-80 animate-pulse pointer-events-none" />
      )}

      {/* Rank and File Labels */}
      {showRankLabel && (
        <span
          className={`absolute top-0.5 left-1 text-[10px] md:text-xs font-bold leading-none pointer-events-none ${labelColor}`}
        >
          {showRankLabel}
        </span>
      )}
      {showFileLabel && (
        <span
          className={`absolute bottom-0.5 right-1 text-[10px] md:text-xs font-bold leading-none pointer-events-none ${labelColor}`}
        >
          {showFileLabel}
        </span>
      )}

      {/* Chess Piece */}
      {piece && (
        <div className="w-4/5 h-4/5 flex items-center justify-center z-10 hover:scale-105 transition-transform duration-100">
          <ChessPiece piece={piece} />
        </div>
      )}

      {/* Legal Move Indicator */}
      {isLegalTarget && (
        <div className="absolute inset-0 flex items-center justify-center z-20 pointer-events-none">
          {piece ? (
            // Capture ring around target piece
            <div className="w-4/5 h-4/5 rounded-full border-4 border-black/25 dark:border-white/30 animate-pulse" />
          ) : (
            // Small subtle dot on empty destination
            <div className="w-3.5 h-3.5 md:w-4 md:h-4 rounded-full bg-black/20 dark:bg-black/30 shadow-inner" />
          )}
        </div>
      )}
    </div>
  );
};
