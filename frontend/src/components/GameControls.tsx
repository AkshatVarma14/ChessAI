import React from 'react';
import { RotateCcw, RotateCw, Undo2, PlusCircle, Bot } from 'lucide-react';

interface GameControlsProps {
  onNewGame: () => void;
  onRestart: () => void;
  onUndo: () => void;
  onFlipBoard: () => void;
  onAIMove?: () => void;
  canUndo: boolean;
  isLoading?: boolean;
  isTerminal?: boolean;
}

export const GameControls: React.FC<GameControlsProps> = ({
  onNewGame,
  onRestart,
  onUndo,
  onFlipBoard,
  onAIMove,
  canUndo,
  isLoading = false,
  isTerminal = false,
}) => {
  return (
    <div
      data-testid="game-controls"
      className="p-2 sm:p-2.5 bg-[#21201d] rounded-lg border border-stone-800 shadow-md"
    >
      <div className="flex flex-wrap xl:flex-nowrap items-center gap-1 sm:gap-1.5">
        {/* Primary Action: New Game */}
        <button
          onClick={onNewGame}
          disabled={isLoading}
          data-testid="control-new-game"
          className="flex-1 min-w-[84px] h-9 flex items-center justify-center gap-1 px-2 text-xs font-semibold rounded-md bg-stone-800 hover:bg-stone-700 active:bg-stone-800 text-stone-100 hover:text-white transition-all border border-emerald-500/50 hover:border-emerald-400 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
          title="Start a new game"
        >
          <PlusCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span className="whitespace-nowrap">New Game</span>
        </button>

        {/* Primary Action: AI Move (when available) */}
        {onAIMove && (
          <button
            onClick={onAIMove}
            disabled={isLoading || isTerminal}
            data-testid="control-ai-move"
            className="flex-1 min-w-[76px] h-9 flex items-center justify-center gap-1 px-2 text-xs font-semibold rounded-md bg-emerald-700 hover:bg-emerald-600 active:bg-emerald-800 text-white transition-all shadow-sm border border-emerald-600/60 disabled:opacity-40 disabled:cursor-not-allowed"
            title="Ask engine to calculate and make a move"
          >
            <Bot className="w-3.5 h-3.5 shrink-0" />
            <span className="whitespace-nowrap">AI Move</span>
          </button>
        )}

        {/* Secondary Action: Undo */}
        <button
          onClick={onUndo}
          disabled={!canUndo || isLoading}
          data-testid="control-undo"
          className="h-9 flex items-center justify-center gap-1 px-2 text-xs font-medium rounded-md bg-stone-800/90 hover:bg-stone-700 text-stone-200 hover:text-white transition-colors border border-stone-700/60 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          title="Undo previous move (1 ply)"
        >
          <Undo2 className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span className="whitespace-nowrap">Undo</span>
        </button>

        {/* Secondary Action: Restart */}
        <button
          onClick={onRestart}
          disabled={isLoading}
          data-testid="control-restart"
          className="h-9 flex items-center justify-center gap-1 px-2 text-xs font-medium rounded-md bg-stone-800/90 hover:bg-stone-700 text-stone-200 hover:text-white transition-colors border border-stone-700/60 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
          title="Reset position to starting game"
        >
          <RotateCcw className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          <span className="whitespace-nowrap">Restart</span>
        </button>

        {/* Secondary Action: Flip Board */}
        <button
          onClick={onFlipBoard}
          data-testid="control-flip-board"
          className="h-9 flex items-center justify-center gap-1 px-2 text-xs font-medium rounded-md bg-stone-800/90 hover:bg-stone-700 text-stone-200 hover:text-white transition-colors border border-stone-700/60 shrink-0"
          title="Flip board view"
        >
          <RotateCw className="w-3.5 h-3.5 text-stone-300 shrink-0" />
          <span className="whitespace-nowrap">Flip Board</span>
        </button>
      </div>
    </div>
  );
};
