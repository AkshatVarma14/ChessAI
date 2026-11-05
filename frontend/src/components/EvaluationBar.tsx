import React from 'react';

export interface EvaluationBarProps {
  scoreCp: number | null;
  isMate?: boolean;
  mateInPlies?: number | null;
  isAnalyzing?: boolean;
  orientation?: 'white' | 'black';
}

/**
 * Visual vertical evaluation bar displaying engine advantage.
 * Scores are integer centipawns from White's perspective (+ White advantage, - Black advantage).
 * White fill height maps dynamically via a standard chess sigmoid curve.
 */
export const EvaluationBar: React.FC<EvaluationBarProps> = ({
  scoreCp,
  isMate = false,
  mateInPlies = null,
  isAnalyzing = false,
  orientation = 'white',
}) => {
  // Compute percentage of the bar that should be colored White
  let whitePercent = 50;

  if (scoreCp !== null) {
    if (isMate) {
      whitePercent = scoreCp > 0 ? 96 : 4;
    } else {
      // Sigmoid mapping centered at 0 cp, scale tuned to reach ~88% at +500 cp
      const sigmoid = 1 / (1 + Math.exp(-0.0035 * scoreCp));
      whitePercent = Math.min(96, Math.max(4, sigmoid * 100));
    }
  }

  // Format the numerical display text
  let labelText = '0.0';
  if (scoreCp === null) {
    labelText = '-';
  } else if (isMate) {
    const mateMoves = Math.max(1, Math.ceil(Math.abs(mateInPlies ?? 1) / 2));
    labelText = scoreCp > 0 ? `M${mateMoves}` : `-M${mateMoves}`;
  } else {
    const pawns = (scoreCp / 100).toFixed(1);
    if (scoreCp > 0) {
      labelText = `+${pawns}`;
    } else if (pawns === '-0.0') {
      labelText = '0.0';
    } else {
      labelText = pawns;
    }
  }

  // Determine top/bottom fill based on orientation
  const isWhiteOrientation = orientation === 'white';
  const fillStyle: React.CSSProperties = isWhiteOrientation
    ? { height: `${whitePercent}%`, bottom: 0 }
    : { height: `${whitePercent}%`, top: 0 };

  const isWhiteAhead = (scoreCp ?? 0) >= 0;

  // In standard (white) orientation: top represents Black, bottom represents White
  // In flipped (black) orientation: top represents White, bottom represents Black
  const topShowsScore = isWhiteOrientation ? !isWhiteAhead : isWhiteAhead;
  const bottomShowsScore = isWhiteOrientation ? isWhiteAhead : !isWhiteAhead;

  const topTextColor = isWhiteOrientation ? 'text-slate-100 font-extrabold' : 'text-slate-900 font-extrabold';
  const bottomTextColor = isWhiteOrientation ? 'text-slate-900 font-extrabold' : 'text-slate-100 font-extrabold';

  return (
    <div
      className="relative flex flex-col items-center justify-between w-7 sm:w-8 h-full min-h-[300px] max-h-[560px] bg-slate-900 rounded-lg overflow-hidden border border-slate-700/80 shadow-inner select-none transition-all"
      role="meter"
      aria-label={`Position evaluation: ${labelText}`}
      aria-valuenow={scoreCp ?? 0}
      title={`Evaluation: ${labelText} (${scoreCp !== null ? `${scoreCp} cp` : 'uncalculated'})`}
    >
      {/* Black background represents Black's advantage */}
      <div className="absolute inset-0 bg-slate-800" />

      {/* White filled bar with smooth height transition */}
      <div
        className="absolute left-0 right-0 bg-slate-100 transition-[height] duration-500 ease-out"
        style={fillStyle}
      />

      {/* Top score label */}
      <div
        className={`relative z-10 pt-1.5 px-0.5 text-center text-[10px] font-mono transition-opacity ${
          topShowsScore ? topTextColor : 'text-transparent opacity-0'
        }`}
      >
        {topShowsScore ? labelText : ''}
      </div>

      {/* Center indicator pulse when actively computing */}
      {isAnalyzing && (
        <div
          className="relative z-20 w-2 h-2 rounded-full bg-cyan-400 animate-ping"
          title="Analyzing..."
        />
      )}

      {/* Bottom score label */}
      <div
        className={`relative z-10 pb-1.5 px-0.5 text-center text-[10px] font-mono transition-opacity ${
          bottomShowsScore ? bottomTextColor : 'text-transparent opacity-0'
        }`}
      >
        {bottomShowsScore ? labelText : ''}
      </div>
    </div>
  );
};
