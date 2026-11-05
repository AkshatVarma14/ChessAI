import React from 'react';
import { Color, GameResult, GameStatus as GameStatusType, GameMode, PlayerColor } from '../types/chess';
import { AlertCircle, CheckCircle2, ShieldAlert, Bot, User } from 'lucide-react';

interface GameStatusProps {
  turn: Color;
  isCheck: boolean;
  isTerminal: boolean;
  status: GameStatusType;
  result: GameResult;
  gameMode?: GameMode;
  playerColor?: PlayerColor;
  isAiThinking?: boolean;
}

export const GameStatus: React.FC<GameStatusProps> = ({
  turn,
  isCheck,
  isTerminal,
  status,
  result,
  gameMode,
  playerColor = 'white',
  isAiThinking = false,
}) => {
  const getStatusContent = () => {
    if (status === 'checkmate') {
      const winner = result === '1-0' ? 'White' : 'Black';
      return {
        badge: 'bg-red-500/20 text-red-400 border-red-500/40',
        badgeText: 'Checkmate',
        title: 'Checkmate!',
        subtitle: `${winner} wins the game (${result})`,
        icon: <ShieldAlert className="w-5 h-5 text-red-400" />,
      };
    }

    if (status === 'stalemate') {
      return {
        badge: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
        badgeText: 'Stalemate',
        title: 'Draw — Stalemate',
        subtitle: 'The active player has no legal moves (1/2-1/2)',
        icon: <CheckCircle2 className="w-5 h-5 text-amber-400" />,
      };
    }

    if (status === 'draw_repetition') {
      return {
        badge: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
        badgeText: 'Repetition',
        title: 'Draw — Threefold Repetition',
        subtitle: 'Position repeated three times (1/2-1/2)',
        icon: <CheckCircle2 className="w-5 h-5 text-amber-400" />,
      };
    }

    if (status === 'draw_50_moves') {
      return {
        badge: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
        badgeText: '50-Move Draw',
        title: 'Draw — 50-Move Rule',
        subtitle: '50 full moves without capture or pawn move (1/2-1/2)',
        icon: <CheckCircle2 className="w-5 h-5 text-amber-400" />,
      };
    }

    if (status === 'draw_75_moves') {
      return {
        badge: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
        badgeText: '75-Move Draw',
        title: 'Draw — 75-Move Rule',
        subtitle: '75 full moves without capture or pawn move (1/2-1/2)',
        icon: <CheckCircle2 className="w-5 h-5 text-amber-400" />,
      };
    }

    if (status === 'draw_fivefold_repetition') {
      return {
        badge: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
        badgeText: 'Fivefold Repetition',
        title: 'Draw — Fivefold Repetition',
        subtitle: 'Position repeated five times (1/2-1/2)',
        icon: <CheckCircle2 className="w-5 h-5 text-amber-400" />,
      };
    }

    if (status === 'draw_insufficient_material') {
      return {
        badge: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
        badgeText: 'Insufficient Material',
        title: 'Draw — Insufficient Material',
        subtitle: 'Neither side has sufficient checkmating material (1/2-1/2)',
        icon: <CheckCircle2 className="w-5 h-5 text-amber-400" />,
      };
    }

    // Active in-progress game
    const isWhite = turn === 'white';
    const isPlayerTurn = gameMode === 'player_vs_ai' && turn === playerColor;
    const isComputerTurn = gameMode === 'player_vs_ai' && turn !== playerColor;

    if (gameMode === 'player_vs_ai') {
      if (isAiThinking) {
        return {
          badge: 'bg-purple-500/20 text-purple-300 border-purple-500/40 animate-pulse',
          badgeText: 'AI Thinking',
          title: 'Computer is thinking...',
          subtitle: isCheck ? 'Active King is in check!' : 'Searching optimal adversarial move...',
          icon: <Bot className="w-5 h-5 text-purple-400 animate-spin" />,
        };
      }

      if (isPlayerTurn) {
        return {
          badge: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-bold',
          badgeText: 'Your Turn',
          title: `Your Turn (${isWhite ? 'White' : 'Black'})`,
          subtitle: isCheck ? 'Your King is in check! Evade check.' : 'Select a piece and make your move',
          icon: isCheck ? (
            <AlertCircle className="w-5 h-5 text-red-400 animate-bounce" />
          ) : (
            <User className="w-5 h-5 text-emerald-400" />
          ),
        };
      }

      if (isComputerTurn) {
        return {
          badge: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40',
          badgeText: 'AI Turn',
          title: `Computer's Turn (${isWhite ? 'White' : 'Black'})`,
          subtitle: isCheck ? 'Computer King is in check!' : 'Waiting for computer move',
          icon: <Bot className="w-5 h-5 text-indigo-400" />,
        };
      }
    }

    // Pass & Play Mode
    return {
      badge: isWhite ? 'bg-white/10 text-white border-white/20' : 'bg-slate-700/60 text-slate-200 border-slate-600',
      badgeText: turn,
      title: `${isWhite ? 'White' : 'Black'} to move`,
      subtitle: isCheck ? 'King is in check!' : 'Game in progress',
      icon: isCheck ? (
        <AlertCircle className="w-5 h-5 text-red-400 animate-bounce" />
      ) : (
        <div
          className={`w-3.5 h-3.5 rounded-full border ${
            isWhite ? 'bg-white border-slate-300' : 'bg-slate-900 border-slate-600'
          }`}
        />
      ),
    };
  };

  const { badge, badgeText, title, subtitle, icon } = getStatusContent();

  return (
    <div className="flex items-center justify-between p-3 bg-[#21201d] rounded-lg border border-stone-800 shadow-sm">
      <div className="flex items-center gap-2.5">
        <div className="flex items-center justify-center p-1.5 rounded-md bg-stone-900 border border-stone-800">
          {icon}
        </div>
        <div>
          <h3 className="text-xs md:text-sm font-semibold text-stone-100 flex items-center gap-2">
            {title}
            {isCheck && !isTerminal && (
              <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-full bg-red-950/80 text-red-400 border border-red-800/60">
                Check
              </span>
            )}
          </h3>
          <p className="text-[11px] text-stone-400">{subtitle}</p>
        </div>
      </div>

      <div
        className={`px-2.5 py-0.5 text-xs font-semibold rounded-md border capitalize tracking-wide ${badge}`}
      >
        {isTerminal ? 'Concluded' : badgeText}
      </div>
    </div>
  );
};
