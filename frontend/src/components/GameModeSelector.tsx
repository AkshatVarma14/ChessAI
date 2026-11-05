import React from 'react';
import { GameMode, PlayerColor } from '../types/chess';
import { Bot, Users, User } from 'lucide-react';

interface GameModeSelectorProps {
  gameMode: GameMode;
  playerColor: PlayerColor;
  onSelectMode: (mode: GameMode) => void;
  onSelectPlayerColor: (color: PlayerColor) => void;
  disabled?: boolean;
}

export const GameModeSelector: React.FC<GameModeSelectorProps> = ({
  gameMode,
  playerColor,
  onSelectMode,
  onSelectPlayerColor,
  disabled = false,
}) => {
  return (
    <div
      data-testid="game-mode-selector"
      className="p-2.5 sm:p-3 bg-[#21201d] rounded-lg border border-stone-800 shadow-sm text-xs space-y-2"
    >
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-stone-300 flex items-center gap-1.5">
          <User className="w-3.5 h-3.5 text-stone-400" />
          <span className="uppercase text-[11px] tracking-wide">Game Mode</span>
        </label>
      </div>

      {/* Main Mode Toggle Buttons */}
      <div className="grid grid-cols-2 gap-2" role="radiogroup" aria-label="Game Mode Options">
        <button
          type="button"
          data-testid="mode-player-vs-ai"
          role="radio"
          aria-checked={gameMode === 'player_vs_ai'}
          disabled={disabled}
          onClick={() => onSelectMode('player_vs_ai')}
          className={`flex items-center justify-center gap-2 p-2 rounded-md border transition-all duration-150 ${
            gameMode === 'player_vs_ai'
              ? 'bg-stone-700 text-white border-stone-500 shadow-sm font-semibold'
              : 'bg-stone-900/80 border-stone-800 text-stone-400 hover:text-stone-200 hover:bg-stone-800'
          } disabled:opacity-40 disabled:cursor-not-allowed`}
          title="Play against custom Adversarial Chess AI engine"
        >
          <Bot className="w-4 h-4 shrink-0 text-emerald-400" />
          <span className="text-xs font-medium">Player vs Computer</span>
        </button>

        <button
          type="button"
          data-testid="mode-pass-and-play"
          role="radio"
          aria-checked={gameMode === 'pass_and_play'}
          disabled={disabled}
          onClick={() => onSelectMode('pass_and_play')}
          className={`flex items-center justify-center gap-2 p-2 rounded-md border transition-all duration-150 ${
            gameMode === 'pass_and_play'
              ? 'bg-stone-700 text-white border-stone-500 shadow-sm font-semibold'
              : 'bg-stone-900/80 border-stone-800 text-stone-400 hover:text-stone-200 hover:bg-stone-800'
          } disabled:opacity-40 disabled:cursor-not-allowed`}
          title="Two human players take turns on the same device"
        >
          <Users className="w-4 h-4 shrink-0 text-amber-400" />
          <span className="text-xs font-medium">Pass & Play (2 Players)</span>
        </button>
      </div>

      {/* Side Selection Sub-options when playing vs Computer */}
      {gameMode === 'player_vs_ai' && (
        <div className="pt-1.5 border-t border-stone-800/80 flex items-center justify-between text-[11px]">
          <span className="text-stone-400 font-medium">Play as:</span>
          <div className="flex items-center gap-1.5" role="radiogroup" aria-label="Player Side">
            <button
              type="button"
              data-testid="color-select-white"
              role="radio"
              aria-checked={playerColor === 'white'}
              disabled={disabled}
              onClick={() => onSelectPlayerColor('white')}
              className={`px-2.5 py-1 rounded-md border flex items-center gap-1.5 transition-all ${
                playerColor === 'white'
                  ? 'bg-stone-200 text-stone-900 font-bold border-stone-300 shadow-sm'
                  : 'bg-stone-900 text-stone-400 border-stone-800 hover:text-stone-200'
              } disabled:opacity-40 disabled:cursor-not-allowed`}
              title="Play as White (Move first, AI plays Black)"
            >
              <div className="w-2.5 h-2.5 rounded-full bg-white border border-stone-400" />
              <span>White (1st)</span>
            </button>

            <button
              type="button"
              data-testid="color-select-black"
              role="radio"
              aria-checked={playerColor === 'black'}
              disabled={disabled}
              onClick={() => onSelectPlayerColor('black')}
              className={`px-2.5 py-1 rounded-md border flex items-center gap-1.5 transition-all ${
                playerColor === 'black'
                  ? 'bg-stone-800 text-white font-bold border-stone-600 shadow-sm ring-1 ring-emerald-500/40'
                  : 'bg-stone-900 text-stone-400 border-stone-800 hover:text-stone-200'
              } disabled:opacity-40 disabled:cursor-not-allowed`}
              title="Play as Black (AI moves first as White, board flipped)"
            >
              <div className="w-2.5 h-2.5 rounded-full bg-stone-950 border border-stone-600" />
              <span>Black (AI 1st)</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
