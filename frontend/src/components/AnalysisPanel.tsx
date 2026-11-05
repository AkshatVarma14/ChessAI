import React, { useState } from 'react';
import { AnalysisResponse } from '../types/chess';

export interface AnalysisPanelProps {
  analysis: AnalysisResponse | null;
  isAnalyzing: boolean;
  onAnalyze: (depth: number) => void;
  autoAnalyze: boolean;
  onToggleAutoAnalyze: (enabled: boolean) => void;
  error?: string | null;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  analysis,
  isAnalyzing,
  onAnalyze,
  autoAnalyze,
  onToggleAutoAnalyze,
  error,
}) => {
  const [selectedDepth, setSelectedDepth] = useState<number>(3);

  const formatScore = (analysis: AnalysisResponse) => {
    if (analysis.is_mate) {
      const plies = Math.abs(analysis.mate_in_plies ?? 1);
      const moves = Math.max(1, Math.ceil(plies / 2));
      return analysis.score_cp > 0 ? `#+M${moves}` : `#-M${moves}`;
    }
    const pawns = (analysis.score_cp / 100).toFixed(2);
    const sign = analysis.score_cp > 0 ? '+' : '';
    return `${sign}${pawns} (${analysis.score_cp > 0 ? '+' : ''}${analysis.score_cp} cp)`;
  };

  return (
    <div className="flex flex-col bg-slate-800/80 backdrop-blur-md rounded-xl border border-slate-700/80 shadow-lg overflow-hidden">
      {/* Header with Title & Controls */}
      <div className="px-4 py-3 bg-slate-900/60 border-b border-slate-700/80 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Engine Analysis & Search Telemetry
          </h4>
        </div>

        <div className="flex items-center gap-3">
          {/* Auto-analyze Toggle */}
          <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none hover:text-slate-300">
            <input
              type="checkbox"
              checked={autoAnalyze}
              onChange={(e) => onToggleAutoAnalyze(e.target.checked)}
              className="w-3.5 h-3.5 rounded border-slate-600 text-cyan-500 focus:ring-cyan-400 focus:ring-offset-slate-900 bg-slate-700"
            />
            <span>Auto</span>
          </label>

          {/* Depth Selector */}
          <div className="flex items-center gap-1 text-xs">
            <span className="text-slate-400">Depth:</span>
            <select
              value={selectedDepth}
              onChange={(e) => setSelectedDepth(Number(e.target.value))}
              disabled={isAnalyzing}
              className="bg-slate-700/80 text-slate-200 border border-slate-600 rounded px-1.5 py-0.5 text-xs focus:outline-none focus:border-cyan-400 disabled:opacity-50"
            >
              <option value={2}>2 plies</option>
              <option value={3}>3 plies</option>
              <option value={4}>4 plies</option>
              <option value={5}>5 plies</option>
              <option value={6}>6 plies</option>
            </select>
          </div>

          {/* Manual Analyze Button */}
          <button
            onClick={() => onAnalyze(selectedDepth)}
            disabled={isAnalyzing}
            className="flex items-center gap-1.5 px-3 py-1 bg-cyan-600 hover:bg-cyan-500 active:bg-cyan-700 disabled:opacity-50 text-white rounded text-xs font-medium transition-all shadow"
          >
            {isAnalyzing ? (
              <>
                <svg
                  className="animate-spin h-3.5 w-3.5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z"
                  />
                </svg>
                <span>Analyzing...</span>
              </>
            ) : (
              <span>Analyze</span>
            )}
          </button>
        </div>
      </div>

      {/* Main Analysis Body */}
      <div className="p-4 space-y-3">
        {error && (
          <div className="p-2 rounded bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {analysis ? (
          <div className="space-y-3">
            {/* Top Stat Banner: Score & Recommended Move */}
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/60">
                <div className="text-[11px] font-medium text-slate-400">Evaluation</div>
                <div className="text-base font-bold font-mono text-cyan-300 mt-0.5">
                  {formatScore(analysis)}
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/60">
                <div className="text-[11px] font-medium text-slate-400">Best Move</div>
                <div className="text-base font-bold font-mono text-yellow-300 mt-0.5">
                  {analysis.best_move_san || analysis.best_move_uci || 'None'}
                  {analysis.best_move_uci && analysis.best_move_san && (
                    <span className="text-xs font-normal text-slate-400 ml-1.5 font-sans">
                      ({analysis.best_move_uci})
                    </span>
                  )}
                </div>
              </div>
            </div>

            {/* Principal Variation (PV) Line */}
            <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-700/60">
              <div className="text-[11px] font-medium text-slate-400 mb-1.5 flex items-center justify-between">
                <span>Principal Variation (PV)</span>
                <span className="text-[10px] text-slate-500">
                  {analysis.pv_san.length > 0 ? `${analysis.pv_san.length} moves` : 'Immediate'}
                </span>
              </div>
              {analysis.pv_san.length > 0 ? (
                <div className="flex flex-wrap gap-1.5 font-mono text-xs">
                  {analysis.pv_san.map((move, idx) => (
                    <span
                      key={idx}
                      className={`px-2 py-0.5 rounded border text-xs font-medium ${
                        idx === 0
                          ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300 font-bold'
                          : 'bg-slate-800 border-slate-700 text-slate-300'
                      }`}
                    >
                      {idx === 0 && <span className="text-[10px] text-yellow-500 mr-1">★</span>}
                      {move}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-slate-500 italic">No extended PV line stored.</div>
              )}
            </div>

            {/* Telemetry Metrics Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="p-2 rounded bg-slate-900/40 border border-slate-700/40">
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Depth</div>
                <div className="font-mono text-slate-200 mt-0.5 font-semibold">
                  {analysis.depth} plies
                </div>
              </div>
              <div className="p-2 rounded bg-slate-900/40 border border-slate-700/40">
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Nodes Searched</div>
                <div className="font-mono text-slate-200 mt-0.5">
                  {analysis.nodes_searched.toLocaleString()}
                </div>
              </div>
              <div className="p-2 rounded bg-slate-900/40 border border-slate-700/40">
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Quiescence Nodes</div>
                <div className="font-mono text-slate-200 mt-0.5">
                  {analysis.quiescence_nodes.toLocaleString()}
                </div>
              </div>
              <div className="p-2 rounded bg-slate-900/40 border border-slate-700/40">
                <div className="text-[10px] uppercase text-slate-500 font-semibold">Speed / Time</div>
                <div className="font-mono text-slate-200 mt-0.5">
                  {analysis.nodes_per_second > 0
                    ? `${(analysis.nodes_per_second / 1000).toFixed(1)}k NPS`
                    : '0 NPS'}
                  <span className="text-[10px] text-slate-400 ml-1">
                    ({analysis.elapsed_ms.toFixed(0)}ms)
                  </span>
                </div>
              </div>
            </div>

            {/* TT Statistics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
              <div className="p-1.5 rounded bg-slate-900/30 border border-slate-700/30">
                <span className="text-[10px] text-slate-500">TT Hits: </span>
                <span className="font-mono font-medium text-slate-300">{analysis.tt_hits}</span>
              </div>
              <div className="p-1.5 rounded bg-slate-900/30 border border-slate-700/30">
                <span className="text-[10px] text-slate-500">TT Probes: </span>
                <span className="font-mono font-medium text-slate-300">{analysis.tt_probes}</span>
              </div>
              <div className="p-1.5 rounded bg-slate-900/30 border border-slate-700/30">
                <span className="text-[10px] text-slate-500">TT Cutoffs: </span>
                <span className="font-mono font-medium text-slate-300">{analysis.tt_cutoffs}</span>
              </div>
              <div className="p-1.5 rounded bg-slate-900/30 border border-slate-700/30">
                <span className="text-[10px] text-slate-500">TT Stores: </span>
                <span className="font-mono font-medium text-slate-300">{analysis.tt_stores}</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-6 text-center text-slate-400 space-y-1">
            <div className="text-sm font-medium">No Analysis Available</div>
            <div className="text-xs text-slate-500 max-w-xs">
              Click &quot;Analyze&quot; above to search the current position with Alpha-Beta and Quiescence search.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
