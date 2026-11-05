import React, { useEffect, useRef, useState } from 'react';

export interface MoveHistoryProps {
  sanHistory: string[];
  selectedPly?: number | null;
  onSelectPly?: (ply: number) => void;
  onCopyPGN?: () => Promise<void> | void;
  onDownloadPGN?: () => void;
  onReturnToLive?: () => void;
}

export const MoveHistory: React.FC<MoveHistoryProps> = ({
  sanHistory,
  selectedPly = null,
  onSelectPly,
  onCopyPGN,
  onDownloadPGN,
  onReturnToLive,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [copySuccess, setCopySuccess] = useState<boolean>(false);

  const currentPly = selectedPly !== null && selectedPly !== undefined ? selectedPly : sanHistory.length;
  const isReviewing = currentPly < sanHistory.length;

  // Auto-scroll to the bottom when moves are added in live play
  useEffect(() => {
    if (!isReviewing && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [sanHistory.length, isReviewing]);

  const handleCopy = async () => {
    if (onCopyPGN) {
      await onCopyPGN();
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    }
  };

  // Group linear ply array into logical pairs: [ { moveNum: 1, white: 'e4', black: 'e5', whitePly: 1, blackPly: 2 }, ... ]
  const movePairs: Array<{
    moveNum: number;
    white: string;
    black?: string;
    whitePly: number;
    blackPly?: number;
  }> = [];

  for (let i = 0; i < sanHistory.length; i += 2) {
    movePairs.push({
      moveNum: Math.floor(i / 2) + 1,
      white: sanHistory[i],
      black: sanHistory[i + 1],
      whitePly: i + 1,
      blackPly: sanHistory[i + 1] ? i + 2 : undefined,
    });
  }

  return (
    <div className="flex flex-col bg-[#21201d] rounded-lg border border-stone-800 shadow-md overflow-hidden">
      {/* Header */}
      <div className="px-3.5 py-2 bg-stone-900 border-b border-stone-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-400">
            Move History
          </h4>
          <span className="text-[11px] text-stone-500 font-medium font-mono">
            {sanHistory.length} {sanHistory.length === 1 ? 'ply' : 'plies'}
          </span>
        </div>

        {/* PGN Export Controls */}
        <div className="flex items-center gap-1.5">
          {onCopyPGN && (
            <button
              onClick={handleCopy}
              disabled={sanHistory.length === 0}
              className="px-2 py-0.5 rounded text-[11px] font-medium bg-stone-800 hover:bg-stone-700 disabled:opacity-40 text-stone-300 transition-colors border border-stone-700/60"
              title="Copy PGN to clipboard"
            >
              {copySuccess ? '✓ Copied' : 'Copy PGN'}
            </button>
          )}
          {onDownloadPGN && (
            <button
              onClick={onDownloadPGN}
              disabled={sanHistory.length === 0}
              className="px-2 py-0.5 rounded text-[11px] font-medium bg-stone-800 hover:bg-stone-700 disabled:opacity-40 text-stone-300 transition-colors border border-stone-700/60"
              title="Download PGN file"
            >
              Export
            </button>
          )}
        </div>
      </div>

      {/* Review Mode Banner */}
      {isReviewing && (
        <div className="px-3 py-1 bg-amber-950/60 border-b border-amber-800/60 flex items-center justify-between text-xs text-amber-300">
          <span>
            Viewing ply <strong className="font-mono">{currentPly}</strong> of {sanHistory.length}
          </span>
          {onReturnToLive && (
            <button
              onClick={onReturnToLive}
              className="text-[11px] font-semibold underline hover:text-amber-200"
            >
              Return to Live
            </button>
          )}
        </div>
      )}

      {/* Horizontal Flowing Move List with Natural Wrapping */}
      <div
        ref={containerRef}
        data-testid="move-history-container"
        className="p-2.5 overflow-y-auto min-h-[72px] max-h-[160px] sm:max-h-[190px] flex flex-wrap items-center content-start gap-x-2 gap-y-1.5 text-xs font-mono scrollbar-thin scrollbar-thumb-stone-700"
      >
        {movePairs.length === 0 ? (
          <div className="w-full flex items-center justify-center py-5 text-stone-500 text-xs italic">
            No moves played yet.
          </div>
        ) : (
          movePairs.map(({ moveNum, white, black, whitePly, blackPly }) => {
            const isWhiteSelected = currentPly === whitePly;
            const isBlackSelected = currentPly === blackPly;

            return (
              <div
                key={moveNum}
                className="inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 bg-stone-900/50 border border-stone-800/60 hover:border-stone-700/80 transition-colors"
              >
                <span className="text-stone-500 select-none font-semibold text-[11px] mr-0.5">
                  {moveNum}.
                </span>

                {/* White Move */}
                <button
                  type="button"
                  data-ply={whitePly}
                  onClick={() => onSelectPly?.(whitePly)}
                  className={`px-1.5 py-0.5 rounded font-medium text-xs transition-all ${
                    isWhiteSelected
                      ? 'bg-emerald-950 text-emerald-300 font-bold border border-emerald-600/70 shadow-sm ring-1 ring-emerald-500/30'
                      : 'text-stone-200 hover:bg-stone-800 hover:text-white'
                  }`}
                  title={`Move ${moveNum} White: ${white}`}
                >
                  {white}
                </button>

                {/* Black Move (rendered only if played, no empty box) */}
                {black && (
                  <button
                    type="button"
                    data-ply={blackPly}
                    onClick={() => blackPly && onSelectPly?.(blackPly)}
                    className={`px-1.5 py-0.5 rounded font-medium text-xs transition-all ${
                      isBlackSelected
                        ? 'bg-emerald-950 text-emerald-300 font-bold border border-emerald-600/70 shadow-sm ring-1 ring-emerald-500/30'
                        : 'text-stone-300 hover:bg-stone-800 hover:text-white'
                    }`}
                    title={`Move ${moveNum} Black: ${black}`}
                  >
                    {black}
                  </button>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* History Navigation Bar */}
      <div className="px-3 py-1.5 bg-stone-900 border-t border-stone-800 flex items-center justify-center gap-1">
        <button
          onClick={() => onSelectPly?.(0)}
          disabled={sanHistory.length === 0 || currentPly === 0}
          className="px-2.5 py-1 rounded bg-stone-800 hover:bg-stone-700 disabled:opacity-30 text-stone-300 text-xs font-mono font-bold transition-colors border border-stone-700/50"
          title="Initial Position (Start)"
          aria-label="First move"
        >
          |&lt;
        </button>
        <button
          onClick={() => onSelectPly?.(Math.max(0, currentPly - 1))}
          disabled={sanHistory.length === 0 || currentPly === 0}
          className="px-3 py-1 rounded bg-stone-800 hover:bg-stone-700 disabled:opacity-30 text-stone-300 text-xs font-mono font-bold transition-colors border border-stone-700/50"
          title="Previous Move"
          aria-label="Previous move"
        >
          &lt;
        </button>
        <button
          onClick={() => onSelectPly?.(Math.min(sanHistory.length, currentPly + 1))}
          disabled={sanHistory.length === 0 || currentPly === sanHistory.length}
          className="px-3 py-1 rounded bg-stone-800 hover:bg-stone-700 disabled:opacity-30 text-stone-300 text-xs font-mono font-bold transition-colors border border-stone-700/50"
          title="Next Move"
          aria-label="Next move"
        >
          &gt;
        </button>
        <button
          onClick={() => onSelectPly?.(sanHistory.length)}
          disabled={sanHistory.length === 0 || currentPly === sanHistory.length}
          className="px-2.5 py-1 rounded bg-stone-800 hover:bg-stone-700 disabled:opacity-30 text-stone-300 text-xs font-mono font-bold transition-colors border border-stone-700/50"
          title="Current Position (Live)"
          aria-label="Latest move"
        >
          &gt;|
        </button>
      </div>
    </div>
  );
};
