import React from 'react';
import { Color, PieceSymbol } from '../types/chess';
import { ChessPiece } from './ChessPiece';

interface PromotionDialogProps {
  isOpen: boolean;
  color: Color;
  onSelect: (piece: 'q' | 'r' | 'b' | 'n') => void;
  onCancel: () => void;
}

export const PromotionDialog: React.FC<PromotionDialogProps> = ({
  isOpen,
  color,
  onSelect,
  onCancel,
}) => {
  if (!isOpen) return null;

  const choices: Array<{ type: 'q' | 'r' | 'b' | 'n'; label: string; symbol: PieceSymbol }> = [
    { type: 'q', label: 'Queen', symbol: color === 'white' ? 'Q' : 'q' },
    { type: 'r', label: 'Rook', symbol: color === 'white' ? 'R' : 'r' },
    { type: 'b', label: 'Bishop', symbol: color === 'white' ? 'B' : 'b' },
    { type: 'n', label: 'Knight', symbol: color === 'white' ? 'N' : 'n' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 shadow-2xl max-w-sm w-full mx-4 text-center">
        <h3 className="text-lg font-semibold text-white mb-2">Pawn Promotion</h3>
        <p className="text-sm text-slate-400 mb-6">Select a piece to promote your pawn to:</p>

        <div className="grid grid-cols-4 gap-3 mb-6">
          {choices.map(({ type, label, symbol }) => (
            <button
              key={type}
              onClick={() => onSelect(type)}
              className="flex flex-col items-center justify-center p-3 rounded-lg bg-slate-700/60 hover:bg-indigo-600 hover:text-white border border-slate-600 hover:border-indigo-500 transition-all duration-150 group"
              title={label}
            >
              <div className="w-12 h-12 flex items-center justify-center group-hover:scale-110 transition-transform">
                <ChessPiece piece={symbol} />
              </div>
              <span className="text-xs font-medium text-slate-300 group-hover:text-white mt-1">
                {label}
              </span>
            </button>
          ))}
        </div>

        <button
          onClick={onCancel}
          className="text-xs text-slate-400 hover:text-slate-200 underline transition-colors"
        >
          Cancel move
        </button>
      </div>
    </div>
  );
};
