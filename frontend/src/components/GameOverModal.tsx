import React, { useEffect } from 'react';
import { GameStatus, GameResult, Color } from '../types/chess';
import { Trophy, Clock, Scale, BarChart2, PlusCircle, AlertCircle } from 'lucide-react';

export interface GameOverModalProps {
  isOpen: boolean;
  status: GameStatus;
  result: GameResult;
  turn: Color;
  onAnalyze: () => void;
  onNewGame: () => void;
}

export const GameOverModal: React.FC<GameOverModalProps> = ({
  isOpen,
  status,
  result,
  turn,
  onAnalyze,
  onNewGame,
}) => {
  // Support Escape key to close the modal and enter review mode
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onAnalyze();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onAnalyze]);

  if (!isOpen) return null;

  let title = 'Game Over';
  let explanation = 'The game has concluded.';
  let icon = <Trophy className="w-8 h-8 text-amber-400" />;

  switch (status) {
    case 'checkmate':
      title = 'Checkmate';
      if (result === '1-0') {
        explanation = 'White wins by checkmate!';
      } else if (result === '0-1') {
        explanation = 'Black wins by checkmate!';
      } else {
        explanation = turn === 'white' ? 'Black wins by checkmate!' : 'White wins by checkmate!';
      }
      icon = <Trophy className="w-8 h-8 text-amber-400" />;
      break;

    case 'timeout':
      title = "Time's Up";
      if (result === '1/2-1/2') {
        explanation = 'Draw on time — opponent has insufficient material to checkmate';
        icon = <Scale className="w-8 h-8 text-cyan-400" />;
      } else if (result === '1-0') {
        explanation = 'White wins on time!';
        icon = <Clock className="w-8 h-8 text-amber-400" />;
      } else if (result === '0-1') {
        explanation = 'Black wins on time!';
        icon = <Clock className="w-8 h-8 text-amber-400" />;
      } else {
        explanation = turn === 'white' ? 'Black wins on time!' : 'White wins on time!';
        icon = <Clock className="w-8 h-8 text-amber-400" />;
      }
      break;

    case 'stalemate':
      title = 'Stalemate';
      explanation = 'The game is a draw by stalemate.';
      icon = <Scale className="w-8 h-8 text-cyan-400" />;
      break;

    case 'draw_insufficient_material':
      title = 'Draw';
      explanation = 'Draw by insufficient mating material.';
      icon = <Scale className="w-8 h-8 text-cyan-400" />;
      break;

    case 'draw_75_moves':
      title = 'Draw';
      explanation = 'Draw by 75-move rule (automatic).';
      icon = <Scale className="w-8 h-8 text-cyan-400" />;
      break;

    case 'draw_fivefold_repetition':
      title = 'Draw';
      explanation = 'Draw by fivefold repetition (automatic).';
      icon = <Scale className="w-8 h-8 text-cyan-400" />;
      break;

    case 'draw_50_moves':
      title = 'Draw';
      explanation = 'Draw by 50-move rule (claimed).';
      icon = <Scale className="w-8 h-8 text-cyan-400" />;
      break;

    case 'draw_repetition':
    case 'draw_claimed':
      title = 'Draw';
      explanation = 'Draw by threefold repetition (claimed).';
      icon = <Scale className="w-8 h-8 text-cyan-400" />;
      break;

    default:
      if (result === '1-0') {
        title = 'White Wins';
        explanation = 'White wins the game.';
        icon = <Trophy className="w-8 h-8 text-amber-400" />;
      } else if (result === '0-1') {
        title = 'Black Wins';
        explanation = 'Black wins the game.';
        icon = <Trophy className="w-8 h-8 text-amber-400" />;
      } else if (result === '1/2-1/2') {
        title = 'Draw';
        explanation = 'The game is a draw.';
        icon = <Scale className="w-8 h-8 text-cyan-400" />;
      } else {
        icon = <AlertCircle className="w-8 h-8 text-amber-400" />;
      }
      break;
  }

  // Display score (e.g. 1-0, 0-1, ½–½)
  const displayResult = result === '1/2-1/2' ? '½–½' : result || '*';

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="game-over-title"
      data-testid="game-over-modal"
      className="absolute inset-0 z-30 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-[2px] rounded-xl animate-in fade-in duration-200"
    >
      <div
        data-testid="game-over-banner"
        className="w-full max-w-[320px] sm:max-w-[340px] p-5 sm:p-6 bg-[#21201d]/95 backdrop-blur-md rounded-2xl border border-stone-700/80 shadow-2xl flex flex-col items-center text-center gap-3.5 ring-1 ring-white/10"
      >
        {/* Outcome Icon */}
        <div className="w-12 h-12 rounded-full bg-stone-900/80 border border-stone-700/80 flex items-center justify-center shadow-inner">
          {icon}
        </div>

        {/* Heading & Explanation */}
        <div className="space-y-1">
          <h2
            id="game-over-title"
            data-testid="game-over-title"
            className="text-xl sm:text-2xl font-bold tracking-tight text-white"
          >
            {title}
          </h2>
          <p
            data-testid="game-over-explanation"
            className="text-xs sm:text-sm text-stone-300 font-medium leading-snug px-1"
          >
            {explanation}
          </p>
        </div>

        {/* Result Badge */}
        <div
          data-testid="game-over-score"
          className="px-3.5 py-1 rounded-md font-mono text-sm font-bold bg-stone-900 border border-stone-700/70 text-emerald-400 shadow-sm"
        >
          {displayResult}
          {result && result !== '1/2-1/2' && (
            <span className="sr-only"> {result}</span>
          )}
        </div>

        {/* Actions */}
        <div className="grid grid-cols-2 gap-2.5 w-full pt-1">
          <button
            type="button"
            data-testid="modal-analyze-game"
            onClick={onAnalyze}
            className="h-10 flex items-center justify-center gap-1.5 px-3 rounded-lg text-xs font-semibold bg-stone-800 hover:bg-stone-700 active:bg-stone-800 text-stone-200 hover:text-white border border-stone-600/70 transition-all shadow-sm"
            title="Inspect moves and analyze position"
          >
            <BarChart2 className="w-4 h-4 text-cyan-400 shrink-0" />
            <span>Analyze Game</span>
          </button>

          <button
            type="button"
            data-testid="modal-new-game"
            onClick={onNewGame}
            className="h-10 flex items-center justify-center gap-1.5 px-3 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white transition-all shadow-md shadow-emerald-950/60 border border-emerald-500"
            title="Start a new chess game"
          >
            <PlusCircle className="w-4 h-4 text-white shrink-0" />
            <span>New Game</span>
          </button>
        </div>
      </div>
    </div>
  );
};
