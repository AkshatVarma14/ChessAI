import React from 'react';
import { Timer, Zap, Flame, Clock, Coffee } from 'lucide-react';
import { TimeControl } from '../types/chess';

interface TimeControlSelectorProps {
  currentTimeControl: TimeControl;
  onSelectTimeControl: (mode: TimeControl) => void;
  disabled?: boolean;
}

interface TimeControlOption {
  id: TimeControl;
  label: string;
  timeText: string;
  icon: React.ReactNode;
}

const TIME_CONTROLS: TimeControlOption[] = [
  { id: 'bullet', label: 'Bullet', timeText: '1 min', icon: <Zap className="w-3.5 h-3.5 text-amber-400" /> },
  { id: 'blitz', label: 'Blitz', timeText: '3 min', icon: <Flame className="w-3.5 h-3.5 text-orange-400" /> },
  { id: 'rapid', label: 'Rapid', timeText: '10 min', icon: <Clock className="w-3.5 h-3.5 text-emerald-400" /> },
  { id: 'classic', label: 'Classic', timeText: '30 min', icon: <Timer className="w-3.5 h-3.5 text-cyan-400" /> },
  { id: 'casual', label: 'Casual', timeText: 'Untimed', icon: <Coffee className="w-3.5 h-3.5 text-stone-400" /> },
];

export const TimeControlSelector: React.FC<TimeControlSelectorProps> = ({
  currentTimeControl,
  onSelectTimeControl,
  disabled = false,
}) => {
  return (
    <div className="flex flex-col gap-1.5 p-2.5 sm:p-3 bg-[#21201d] rounded-lg border border-stone-800 shadow-sm">
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold text-stone-300 flex items-center gap-1.5">
          <Timer className="w-3.5 h-3.5 text-stone-400" />
          <span className="uppercase text-[11px] tracking-wide">Time Control</span>
        </label>
      </div>

      <div className="grid grid-cols-5 gap-1.5 pt-0.5">
        {TIME_CONTROLS.map((tc) => {
          const isSelected = currentTimeControl === tc.id;
          return (
            <button
              key={tc.id}
              type="button"
              data-testid={`time-control-${tc.id}`}
              onClick={() => onSelectTimeControl(tc.id)}
              disabled={disabled}
              className={`flex flex-col items-center justify-center py-1.5 px-1 rounded-md transition-all text-xs ${
                isSelected
                  ? 'bg-emerald-700 text-white font-bold shadow-md shadow-emerald-950/50 border border-emerald-500/60 ring-1 ring-emerald-400/40'
                  : 'bg-stone-800/80 hover:bg-stone-700/80 text-stone-300 border border-stone-700/50 hover:text-white'
              } disabled:opacity-40 disabled:cursor-not-allowed`}
              title={`${tc.label} (${tc.timeText})`}
            >
              <div className="mb-0.5">{tc.icon}</div>
              <span className="text-[11px] leading-tight truncate w-full text-center">
                {tc.label}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
