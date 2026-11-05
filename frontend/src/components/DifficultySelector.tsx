import React from 'react';
import { DifficultyLevel } from '../types/chess';
import { Gauge } from 'lucide-react';

interface DifficultySelectorProps {
  currentDifficulty: DifficultyLevel;
  onSelectDifficulty: (difficulty: DifficultyLevel) => void;
  disabled?: boolean;
}

interface DifficultyOption {
  level: DifficultyLevel;
  label: string;
  badge: string;
  description: string;
  activeColor: string;
}

const DIFFICULTY_OPTIONS: DifficultyOption[] = [
  {
    level: 'beginner',
    label: 'Beginner',
    badge: 'Depth 1',
    description: 'Fast 1-ply tactical moves with minimal node budget.',
    activeColor: 'bg-emerald-600/90 text-white border-emerald-500 shadow-emerald-600/20',
  },
  {
    level: 'easy',
    label: 'Easy',
    badge: 'Depth 2',
    description: '2-ply search with shallow quiescence and move ordering.',
    activeColor: 'bg-teal-600/90 text-white border-teal-500 shadow-teal-600/20',
  },
  {
    level: 'medium',
    label: 'Medium',
    badge: 'Depth 3',
    description: 'Balanced 3-ply iterative deepening with 4-ply quiescence and TT.',
    activeColor: 'bg-indigo-600/90 text-white border-indigo-500 shadow-indigo-600/20',
  },
  {
    level: 'hard',
    label: 'Hard',
    badge: 'Depth 4',
    description: '4-ply search with 6-ply quiescence extensions and move ordering.',
    activeColor: 'bg-purple-600/90 text-white border-purple-500 shadow-purple-600/20',
  },
  {
    level: 'expert',
    label: 'Expert',
    badge: 'Depth 5',
    description: 'Full 5-ply search with 8-ply quiescence and 64MB transposition table.',
    activeColor: 'bg-rose-600/90 text-white border-rose-500 shadow-rose-600/20',
  },
];

export const DifficultySelector: React.FC<DifficultySelectorProps> = ({
  currentDifficulty,
  onSelectDifficulty,
  disabled = false,
}) => {
  return (
    <div
      data-testid="difficulty-selector"
      className="p-2.5 sm:p-3 bg-[#21201d] rounded-lg border border-stone-800 shadow-sm text-xs space-y-2"
    >
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-stone-300 flex items-center gap-1.5">
          <Gauge className="w-3.5 h-3.5 text-stone-400" />
          <span className="uppercase text-[11px] tracking-wide">AI Difficulty Level</span>
        </label>
      </div>

      {/* 5 Difficulty Options */}
      <div className="grid grid-cols-5 gap-1.5" role="radiogroup" aria-label="Engine Difficulty Presets">
        {DIFFICULTY_OPTIONS.map((opt) => {
          const isSelected = currentDifficulty === opt.level;
          return (
            <button
              key={opt.level}
              data-testid={`difficulty-option-${opt.level}`}
              role="radio"
              aria-checked={isSelected}
              disabled={disabled}
              onClick={() => onSelectDifficulty(opt.level)}
              title={`${opt.label} (${opt.badge}): ${opt.description}`}
              className={`flex flex-col items-center justify-center p-1.5 rounded-md border transition-all duration-150 ${
                isSelected
                  ? `${opt.activeColor} shadow-sm font-semibold ring-1 ring-white/20`
                  : 'bg-stone-900 border-stone-800 text-stone-400 hover:text-stone-200 hover:bg-stone-800'
              } disabled:opacity-40 disabled:cursor-not-allowed`}
            >
              <span className="text-[11px] font-medium leading-tight">{opt.label}</span>
              <span
                className={`text-[9px] mt-0.5 px-1 py-0.2 rounded font-mono ${
                  isSelected ? 'bg-black/30 text-white' : 'text-stone-500'
                }`}
              >
                {opt.badge}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
