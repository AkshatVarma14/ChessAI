import React from 'react';
import { Bot, User, Brain, Clock } from 'lucide-react';
import { PieceSymbol } from '../types/chess';
import { ChessPiece } from './ChessPiece';

interface PlayerCardProps {
  name: string;
  color: 'white' | 'black';
  isAi: boolean;
  difficultyName?: string;
  isCurrentTurn: boolean;
  isThinking?: boolean;
  capturedPieces: PieceSymbol[];
  materialAdvantage?: number;
  isCheck?: boolean;
  isCheckmate?: boolean;
  isTimeout?: boolean;
  timeRemaining?: number | null; // seconds
  isTimed?: boolean;
  isClockActive?: boolean;
}

export const PlayerCard: React.FC<PlayerCardProps> = ({
  name,
  color,
  isAi,
  difficultyName,
  isCurrentTurn,
  isThinking = false,
  capturedPieces,
  materialAdvantage = 0,
  isCheck = false,
  isCheckmate = false,
  isTimeout = false,
  timeRemaining = null,
  isTimed = false,
  isClockActive = false,
}) => {
  // Group captured pieces for tidy display: e.g. 2 pawns, 1 bishop
  const pieceCounts = React.useMemo(() => {
    const counts: { [key: string]: number } = {};
    const sortOrder = color === 'white' ? ['q', 'r', 'b', 'n', 'p'] : ['Q', 'R', 'B', 'N', 'P'];
    capturedPieces.forEach((p) => {
      counts[p] = (counts[p] || 0) + 1;
    });
    return sortOrder
      .filter((p) => counts[p] > 0)
      .map((p) => ({ symbol: p as PieceSymbol, count: counts[p] }));
  }, [capturedPieces, color]);

  // Format time remaining (MM:SS)
  const formattedTime = React.useMemo(() => {
    if (!isTimed || timeRemaining === null || timeRemaining === undefined) {
      return null;
    }
    const clamped = Math.max(0, timeRemaining);
    const m = Math.floor(clamped / 60);
    const s = Math.floor(clamped % 60);
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  }, [isTimed, timeRemaining]);

  const isLowTime = isTimed && timeRemaining !== null && timeRemaining <= 30.0;
  const isCriticalTime = isTimed && timeRemaining !== null && timeRemaining <= 10.0;

  return (
    <div
      data-testid={`player-card-${color}`}
      className={`flex items-center justify-between px-3.5 py-2.5 rounded-lg transition-all duration-200 border ${
        isCurrentTurn
          ? 'bg-[#262421] border-emerald-500/80 shadow-md ring-1 ring-emerald-500/40 text-stone-100'
          : 'bg-[#1e1c18]/90 border-stone-800 text-stone-400'
      }`}
    >
      {/* Left: Player Avatar, Name, Difficulty, and Captured Pieces */}
      <div className="flex items-center gap-2.5 min-w-0">
        <div
          className={`relative w-8 h-8 rounded-md flex items-center justify-center font-bold text-xs shrink-0 ${
            color === 'white'
              ? 'bg-stone-200 text-stone-900 border border-stone-300'
              : 'bg-stone-800 text-stone-100 border border-stone-700'
          }`}
        >
          {isAi ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
          {isCurrentTurn && (
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-500 rounded-sm ring-2 ring-[#262421] animate-pulse" />
          )}
        </div>

        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-stone-200 truncate">{name}</span>
            {isAi && difficultyName && (
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded-md bg-stone-700/80 text-stone-300 border border-stone-600/50">
                {difficultyName}
              </span>
            )}
          </div>

          {/* Captured Pieces & Material Advantage */}
          <div className="flex items-center gap-1.5 h-4 mt-0.5">
            <div className="flex items-center -space-x-1">
              {pieceCounts.map(({ symbol, count }) => (
                <div key={symbol} className="flex items-center" title={`${count}x ${symbol}`}>
                  <div className="w-4 h-4">
                    <ChessPiece piece={symbol} />
                  </div>
                  {count > 1 && (
                    <span className="text-[10px] text-stone-400 font-mono -ml-0.5 mr-1 font-bold">
                      {count}
                    </span>
                  )}
                </div>
              ))}
            </div>

            {materialAdvantage > 0 && (
              <span className="text-[11px] font-bold text-emerald-400 font-mono leading-none ml-1">
                +{materialAdvantage}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Right: Turn / Thinking / Check / Checkmate / Clock */}
      <div className="flex items-center gap-2.5 shrink-0">
        {/* Status Indicators (Solid Rounded Rectangles) */}
        {isThinking && (
          <div
            data-testid="status-thinking"
            className="flex items-center gap-1.5 text-xs text-amber-300 bg-amber-950/80 border border-amber-700/80 px-2.5 py-1 rounded-md font-semibold animate-pulse"
          >
            <Brain className="w-3.5 h-3.5 animate-spin text-amber-400" />
            <span>Thinking...</span>
          </div>
        )}

        {!isThinking && isCheckmate && (
          <span
            data-testid="status-checkmate"
            className="text-xs font-bold px-2.5 py-1 rounded-md bg-red-950/90 border border-red-600 text-red-300"
          >
            Checkmate
          </span>
        )}

        {!isThinking && isTimeout && (
          <span
            data-testid="status-timeout"
            className="text-xs font-bold px-2.5 py-1 rounded-md bg-red-950/90 border border-red-600 text-red-300"
          >
            Time Out
          </span>
        )}

        {!isThinking && !isCheckmate && !isTimeout && isCheck && isCurrentTurn && (
          <span
            data-testid="status-check"
            className="text-xs font-bold px-2.5 py-1 rounded-md bg-amber-950/90 border border-amber-600 text-amber-300 animate-pulse"
          >
            Check
          </span>
        )}

        {!isThinking && !isCheck && !isCheckmate && !isTimeout && isCurrentTurn && (
          <span
            data-testid="status-your-turn"
            className="text-xs font-semibold px-2.5 py-1 rounded-md bg-emerald-950/80 border border-emerald-600/80 text-emerald-400"
          >
            To move
          </span>
        )}

        {/* Integrated Player Clock */}
        <div
          data-testid={`player-clock-${color}`}
          className={`flex items-center gap-1.5 px-3 py-1 rounded-md font-mono text-sm tracking-wider border transition-colors ${
            !isTimed
              ? 'bg-stone-800/60 text-stone-400 border-stone-700/50 text-xs font-sans'
              : isCriticalTime
              ? 'bg-red-950/90 text-red-200 border-red-500 font-bold shadow-md shadow-red-950/80 animate-pulse'
              : isLowTime
              ? 'bg-amber-950/80 text-amber-200 border-amber-600 font-bold shadow-sm'
              : isClockActive
              ? 'bg-stone-900 text-emerald-300 border-emerald-500/70 font-bold shadow-sm'
              : 'bg-stone-900/60 text-stone-400 border-stone-800 font-medium'
          }`}
          title={isTimed ? `${name} clock: ${formattedTime}` : 'Untimed match'}
        >
          <Clock className={`w-3.5 h-3.5 ${isClockActive ? 'text-emerald-400 animate-pulse' : 'text-stone-500'}`} />
          <span>{isTimed ? formattedTime : 'Casual'}</span>
        </div>
      </div>
    </div>
  );
};
