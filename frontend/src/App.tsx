import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  GameState,
  DifficultyLevel,
  AnalysisResponse,
  GameMode,
  PlayerColor,
  TimeControl,
} from './types/chess';
import { chessApi } from './services/api';
import { ChessBoard } from './components/ChessBoard';
import { GameControls } from './components/GameControls';
import { GameModeSelector } from './components/GameModeSelector';
import { TimeControlSelector } from './components/TimeControlSelector';
import { DifficultySelector } from './components/DifficultySelector';
import { MoveHistory } from './components/MoveHistory';
import { EvaluationBar } from './components/EvaluationBar';
import { AnalysisPanel } from './components/AnalysisPanel';
import { PlayerCard } from './components/PlayerCard';
import { GameOverModal } from './components/GameOverModal';
import { calculateMaterialFromFen } from './utils/chessUtils';
import {
  AlertCircle,
  Copy,
  Check,
  RefreshCw,
  CheckCircle2,
  Swords,
  BarChart2,
  Info,
  Flag,
} from 'lucide-react';

export const App: React.FC = () => {
  // Game & Match State
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [selectedDifficulty, setSelectedDifficulty] = useState<DifficultyLevel>('medium');
  const [selectedTimeControl, setSelectedTimeControl] = useState<TimeControl>('rapid');
  const [gameMode, setGameMode] = useState<GameMode>('player_vs_ai');
  const [playerColor, setPlayerColor] = useState<PlayerColor>('white');
  const [flipped, setFlipped] = useState<boolean>(false);
  const [sidebarTab, setSidebarTab] = useState<'play' | 'analysis' | 'info'>('play');
  const [isGameOverModalDismissed, setIsGameOverModalDismissed] = useState<boolean>(false);

  // Clock State
  const [whiteClock, setWhiteClock] = useState<number | null>(600);
  const [blackClock, setBlackClock] = useState<number | null>(600);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback((msg: string) => {
    if (toastTimerRef.current) {
      clearTimeout(toastTimerRef.current);
    }
    setInfoToast(msg);
    toastTimerRef.current = setTimeout(() => {
      setInfoToast(null);
      toastTimerRef.current = null;
    }, 2800);
  }, []);

  // Sync clocks with authoritative backend state
  useEffect(() => {
    if (gameState) {
      setWhiteClock(gameState.white_time_remaining ?? null);
      setBlackClock(gameState.black_time_remaining ?? null);
    }
  }, [gameState]);

  // Smooth local countdown between authoritative server responses
  useEffect(() => {
    if (
      !gameState ||
      gameState.is_terminal ||
      !gameState.is_timed ||
      !gameState.clock_started
    ) {
      return;
    }

    const interval = setInterval(() => {
      if (gameState.turn === 'white') {
        setWhiteClock((prev) => {
          if (prev === null) return null;
          const next = Math.max(0, prev - 0.1);
          if (next === 0 && !gameState.is_terminal) {
            chessApi.getGameState(gameState.session_id).then(setGameState).catch(() => {});
          }
          return next;
        });
      } else {
        setBlackClock((prev) => {
          if (prev === null) return null;
          const next = Math.max(0, prev - 0.1);
          if (next === 0 && !gameState.is_terminal) {
            chessApi.getGameState(gameState.session_id).then(setGameState).catch(() => {});
          }
          return next;
        });
      }
    }, 100);

    return () => clearInterval(interval);
  }, [gameState?.is_terminal, gameState?.is_timed, gameState?.clock_started, gameState?.turn, gameState?.session_id]);

  // Synchronize state on demand via custom event
  useEffect(() => {
    const handleSync = () => {
      const current = gameStateRef.current;
      if (current) {
        chessApi
          .getGameState(current.session_id)
          .then((state) => {
            setGameState(state);
            gameStateRef.current = state;
            setWhiteClock(state.white_time_remaining ?? null);
            setBlackClock(state.black_time_remaining ?? null);
          })
          .catch(() => {});
      }
    };
    window.addEventListener('sync-game-state', handleSync);
    return () => window.removeEventListener('sync-game-state', handleSync);
  }, []);

  // Differentiated Loading Flags
  const [isInitializing, setIsInitializing] = useState<boolean>(true);
  const [isAiThinking, setIsAiThinking] = useState<boolean>(false);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);

  // User Notifications & Board Details
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [infoToast, setInfoToast] = useState<string | null>(null);
  const [lastMoveUci, setLastMoveUci] = useState<string | undefined>(undefined);
  const [copiedFen, setCopiedFen] = useState<boolean>(false);

  // Analysis & Engine Telemetry State
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [autoAnalyze, setAutoAnalyze] = useState<boolean>(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const analysisRequestIdRef = useRef<number>(0);

  // Position Review / History Navigation State
  const [reviewingPly, setReviewingPly] = useState<number | null>(null);

  // Refs for stable identity & race condition prevention
  const gameStateRef = useRef<GameState | null>(null);
  const hasInitializedRef = useRef<boolean>(false);
  const isSubmittingRef = useRef<boolean>(false);

  // Derived overall busy state
  const isBusy = isInitializing || isAiThinking || isActionLoading;

  // Safely cancel any pending in-flight analysis request
  const cancelPendingAnalysis = useCallback(() => {
    analysisRequestIdRef.current++;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsAnalyzing(false);
  }, []);

  // Analyze arbitrary FEN or active board state with generation ID protection
  const runAnalysis = useCallback(
    async (fenToAnalyze?: string, depth: number = 3) => {
      const current = gameStateRef.current;
      if (!current && !fenToAnalyze) return;

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      const controller = new AbortController();
      abortControllerRef.current = controller;

      const reqId = ++analysisRequestIdRef.current;
      setIsAnalyzing(true);
      setAnalysisError(null);

      try {
        const payload = fenToAnalyze
          ? { fen: fenToAnalyze, depth }
          : { session_id: current!.session_id, depth };

        const result = await chessApi.analyzePosition(payload, controller.signal);
        if (analysisRequestIdRef.current === reqId) {
          setAnalysis(result);
        }
      } catch (err: unknown) {
        if (analysisRequestIdRef.current === reqId) {
          if (err instanceof Error && err.name === 'AbortError') {
            return;
          }
          setAnalysisError(err instanceof Error ? err.message : 'Position analysis failed.');
        }
      } finally {
        if (analysisRequestIdRef.current === reqId) {
          setIsAnalyzing(false);
        }
      }
    },
    []
  );

  // Initialize new game session
  const initGame = useCallback(
    async (
      initialDifficulty?: DifficultyLevel,
      color?: PlayerColor,
      timeControl?: TimeControl
    ) => {
      if (isSubmittingRef.current) return;
      isSubmittingRef.current = true;
      setIsInitializing(true);
      setIsAiThinking(false);
      setIsActionLoading(false);
      setErrorMessage(null);
      setIsGameOverModalDismissed(false);
      cancelPendingAnalysis();
      setReviewingPly(null);
      setAnalysis(null);

      const targetColor = color || playerColor;
      const diff = initialDifficulty || selectedDifficulty;
      const tc = timeControl || selectedTimeControl;

      try {
        const state = await chessApi.createNewGame(undefined, diff, tc);
        setGameState(state);
        gameStateRef.current = state;
        setSelectedDifficulty(state.difficulty || diff);
        setSelectedTimeControl((state.time_control as TimeControl) || tc);
        setWhiteClock(state.white_time_remaining ?? null);
        setBlackClock(state.black_time_remaining ?? null);
        setLastMoveUci(undefined);

        // If playing as Black against AI, computer makes opening move as White
        if (gameMode === 'player_vs_ai' && targetColor === 'black' && !state.is_terminal) {
          setIsAiThinking(true);
          try {
            const aiState = await chessApi.makeAIMove(state.session_id);
            setGameState(aiState);
            gameStateRef.current = aiState;
            setWhiteClock(aiState.white_time_remaining ?? null);
            setBlackClock(aiState.black_time_remaining ?? null);
            const remainingUci = aiState.uci_history;
            setLastMoveUci(remainingUci.length > 0 ? remainingUci[remainingUci.length - 1] : undefined);
          } catch (aiErr: unknown) {
            setErrorMessage(aiErr instanceof Error ? aiErr.message : 'AI opening move failed.');
          } finally {
            setIsAiThinking(false);
          }
        }
      } catch (err: unknown) {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : 'Unable to connect to backend. Please ensure FastAPI server is running on http://127.0.0.1:8000.'
        );
      } finally {
        isSubmittingRef.current = false;
        setIsInitializing(false);
      }
    },
    [selectedDifficulty, selectedTimeControl, playerColor, gameMode, cancelPendingAnalysis]
  );

  // Guaranteed single mount initialization
  useEffect(() => {
    if (!hasInitializedRef.current) {
      hasInitializedRef.current = true;
      initGame();
    }
  }, [initGame]);

  const handleSelectGameMode = (newMode: GameMode) => {
    setGameMode(newMode);
    showToast(
      newMode === 'player_vs_ai'
        ? 'Switched to Player vs Computer: Engine will automatically respond to your moves.'
        : 'Switched to Pass & Play: 2 players alternate moves locally.'
    );
  };

  const handleSelectPlayerColor = (newColor: PlayerColor) => {
    setPlayerColor(newColor);
    setFlipped(newColor === 'black');
    // If the game hasn't started yet, reinitialize to let AI play White if needed
    if (!gameState || gameState.san_history.length === 0) {
      initGame(selectedDifficulty, newColor);
    } else {
      showToast(`Playing as ${newColor === 'white' ? 'White' : 'Black'}.`);
    }
  };

  const handleSelectDifficulty = async (newDifficulty: DifficultyLevel) => {
    setSelectedDifficulty(newDifficulty);
    const current = gameStateRef.current;
    if (current && !current.is_terminal && !isSubmittingRef.current) {
      isSubmittingRef.current = true;
      setIsActionLoading(true);
      try {
        const updated = await chessApi.setDifficulty(current.session_id, newDifficulty);
        setGameState(updated);
        gameStateRef.current = updated;
        showToast(`Difficulty changed to ${newDifficulty.toUpperCase()}`);
      } catch (err: unknown) {
        setErrorMessage(err instanceof Error ? err.message : 'Failed to update difficulty.');
      } finally {
        isSubmittingRef.current = false;
        setIsActionLoading(false);
      }
    } else {
      showToast(`Difficulty set to ${newDifficulty.toUpperCase()}`);
    }
  };

  const handleSelectTimeControl = (tc: TimeControl) => {
    setSelectedTimeControl(tc);
    if (!gameState || gameState.san_history.length === 0) {
      initGame(selectedDifficulty, playerColor, tc);
    } else {
      showToast(`Time control changed to ${tc.toUpperCase()}. Applies on New Game.`);
    }
  };

  const handleMakeMove = async (moveUci: string) => {
    const current = gameStateRef.current;
    if (!current || isBusy || current.is_terminal || isSubmittingRef.current) return;

    cancelPendingAnalysis();
    setReviewingPly(null);
    setIsGameOverModalDismissed(false);
    isSubmittingRef.current = true;
    setIsActionLoading(true);
    setErrorMessage(null);

    let nextState: GameState;
    try {
      nextState = await chessApi.makeMove(current.session_id, moveUci);
      setGameState(nextState);
      gameStateRef.current = nextState;
      setWhiteClock(nextState.white_time_remaining ?? null);
      setBlackClock(nextState.black_time_remaining ?? null);
      setLastMoveUci(moveUci);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to execute move.');
      isSubmittingRef.current = false;
      setIsActionLoading(false);
      return;
    } finally {
      setIsActionLoading(false);
    }

    if (autoAnalyze) {
      runAnalysis(nextState.fen, 3);
    }

    // In Player vs Computer mode, automatically request AI reply
    if (gameMode === 'player_vs_ai' && !nextState.is_terminal) {
      setIsAiThinking(true);
      try {
        const aiState = await chessApi.makeAIMove(nextState.session_id);
        setGameState(aiState);
        gameStateRef.current = aiState;
        setWhiteClock(aiState.white_time_remaining ?? null);
        setBlackClock(aiState.black_time_remaining ?? null);
        const remainingUci = aiState.uci_history;
        setLastMoveUci(remainingUci.length > 0 ? remainingUci[remainingUci.length - 1] : undefined);

        if (autoAnalyze) {
          runAnalysis(aiState.fen, 3);
        }
      } catch (aiErr: unknown) {
        const msg = aiErr instanceof Error ? aiErr.message : 'AI move calculation failed.';
        // If position was modified concurrently (HTTP 409 Conflict), resync state cleanly
        if (
          msg.toLowerCase().includes('position changed') ||
          msg.toLowerCase().includes('409') ||
          msg.toLowerCase().includes('stale')
        ) {
          try {
            const syncedState = await chessApi.getGameState(nextState.session_id);
            setGameState(syncedState);
            gameStateRef.current = syncedState;
            setWhiteClock(syncedState.white_time_remaining ?? null);
            setBlackClock(syncedState.black_time_remaining ?? null);
            showToast('Board position synchronized.');
          } catch {
            // Keep existing state
          }
        } else {
          setErrorMessage(msg);
        }
      } finally {
        setIsAiThinking(false);
        isSubmittingRef.current = false;
      }
    } else {
      isSubmittingRef.current = false;
    }
  };

  const handleAIMove = async () => {
    const current = gameStateRef.current;
    if (!current || isBusy || current.is_terminal || isSubmittingRef.current) return;

    cancelPendingAnalysis();
    setReviewingPly(null);
    setIsGameOverModalDismissed(false);
    isSubmittingRef.current = true;
    setIsAiThinking(true);
    setErrorMessage(null);

    try {
      const updatedState = await chessApi.makeAIMove(current.session_id);
      setGameState(updatedState);
      gameStateRef.current = updatedState;
      setWhiteClock(updatedState.white_time_remaining ?? null);
      setBlackClock(updatedState.black_time_remaining ?? null);
      const remainingUci = updatedState.uci_history;
      setLastMoveUci(remainingUci.length > 0 ? remainingUci[remainingUci.length - 1] : undefined);

      if (autoAnalyze) {
        runAnalysis(updatedState.fen, 3);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'AI move calculation failed.');
    } finally {
      isSubmittingRef.current = false;
      setIsAiThinking(false);
    }
  };

  const handleUndo = async () => {
    const current = gameStateRef.current;
    if (!current || !current.can_undo || isBusy || isSubmittingRef.current) return;

    cancelPendingAnalysis();
    setReviewingPly(null);
    setIsGameOverModalDismissed(false);
    isSubmittingRef.current = true;
    setIsActionLoading(true);
    setErrorMessage(null);

    try {
      // Undo must remove exactly ONE most recently played move (one ply)
      const updatedState = await chessApi.undoMove(current.session_id, 1);
      setGameState(updatedState);
      gameStateRef.current = updatedState;
      setWhiteClock(updatedState.white_time_remaining ?? null);
      setBlackClock(updatedState.black_time_remaining ?? null);
      const remainingUci = updatedState.uci_history;
      setLastMoveUci(remainingUci.length > 0 ? remainingUci[remainingUci.length - 1] : undefined);

      if (autoAnalyze) {
        runAnalysis(updatedState.fen, 3);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Undo failed.');
    } finally {
      isSubmittingRef.current = false;
      setIsActionLoading(false);
    }
  };

  const handleRestart = async () => {
    const current = gameStateRef.current;
    if (!current || isBusy || isSubmittingRef.current) return;

    cancelPendingAnalysis();
    setReviewingPly(null);
    setIsGameOverModalDismissed(false);
    isSubmittingRef.current = true;
    setIsActionLoading(true);
    setErrorMessage(null);

    try {
      const updatedState = await chessApi.restartGame(current.session_id);
      setGameState(updatedState);
      gameStateRef.current = updatedState;
      setWhiteClock(updatedState.white_time_remaining ?? null);
      setBlackClock(updatedState.black_time_remaining ?? null);
      setLastMoveUci(undefined);
      setAnalysis(null);

      // If playing as Black vs AI, computer moves first
      if (gameMode === 'player_vs_ai' && playerColor === 'black' && !updatedState.is_terminal) {
        setIsAiThinking(true);
        try {
          const aiState = await chessApi.makeAIMove(updatedState.session_id);
          setGameState(aiState);
          gameStateRef.current = aiState;
          setWhiteClock(aiState.white_time_remaining ?? null);
          setBlackClock(aiState.black_time_remaining ?? null);
          const remainingUci = aiState.uci_history;
          setLastMoveUci(remainingUci.length > 0 ? remainingUci[remainingUci.length - 1] : undefined);
        } catch (aiErr: unknown) {
          setErrorMessage(aiErr instanceof Error ? aiErr.message : 'AI opening move failed.');
        } finally {
          setIsAiThinking(false);
        }
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Restart failed.');
    } finally {
      isSubmittingRef.current = false;
      setIsActionLoading(false);
    }
  };

  const handleFlipBoard = () => {
    setFlipped((prev) => !prev);
  };

  const handleCopyFen = () => {
    if (!currentDisplayedFen) return;
    navigator.clipboard.writeText(currentDisplayedFen);
    setCopiedFen(true);
    setTimeout(() => setCopiedFen(false), 2000);
  };

  const handleClaimDraw = async () => {
    const current = gameStateRef.current;
    if (!current || !current.can_claim_draw || isBusy || isSubmittingRef.current) return;

    cancelPendingAnalysis();
    isSubmittingRef.current = true;
    setIsActionLoading(true);
    try {
      const updatedState = await chessApi.claimDraw(current.session_id);
      setGameState(updatedState);
      gameStateRef.current = updatedState;
      setWhiteClock(updatedState.white_time_remaining ?? null);
      setBlackClock(updatedState.black_time_remaining ?? null);
      showToast('Draw successfully claimed!');
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to claim draw.');
    } finally {
      isSubmittingRef.current = false;
      setIsActionLoading(false);
    }
  };

  // PGN Export Handlers
  const handleCopyPGN = async () => {
    const current = gameStateRef.current;
    if (!current) return;
    try {
      const pgnData = await chessApi.getPGN(current.session_id);
      await navigator.clipboard.writeText(pgnData.pgn);
      setInfoToast('Game PGN copied to clipboard!');
      setTimeout(() => setInfoToast(null), 3000);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to export PGN.');
    }
  };

  const handleDownloadPGN = async () => {
    const current = gameStateRef.current;
    if (!current) return;
    try {
      const pgnData = await chessApi.getPGN(current.session_id);
      const blob = new Blob([pgnData.pgn], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `chessai_game_${current.session_id.slice(0, 8)}.pgn`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : 'Failed to export PGN.');
    }
  };

  // Select historical ply to inspect
  const handleSelectPly = (ply: number) => {
    const current = gameStateRef.current;
    if (!current) return;
    cancelPendingAnalysis();
    const clampedPly = Math.max(0, Math.min(current.san_history.length, ply));
    setReviewingPly(clampedPly);

    const targetFen = current.fen_history?.[clampedPly] || current.fen;
    if (autoAnalyze) {
      runAnalysis(targetFen, 3);
    }
  };

  const handleReturnToLive = () => {
    const current = gameStateRef.current;
    cancelPendingAnalysis();
    setReviewingPly(null);
    if (autoAnalyze && current) {
      runAnalysis(current.fen, 3);
    }
  };

  const handleAnalyzeGame = () => {
    setIsGameOverModalDismissed(true);
    const current = gameStateRef.current;
    if (autoAnalyze && current) {
      runAnalysis(current.fen, 3);
    }
  };

  const activeDifficulty = gameState?.difficulty || selectedDifficulty;

  // Determine current displayed FEN and review state
  const isReviewing =
    reviewingPly !== null &&
    gameState !== null &&
    reviewingPly < gameState.san_history.length;

  const currentDisplayedFen =
    isReviewing && gameState?.fen_history?.[reviewingPly!]
      ? gameState.fen_history[reviewingPly!]
      : gameState?.fen || '';

  const displayedCheck = isReviewing
    ? reviewingPly! > 0 && !!gameState?.san_history[reviewingPly! - 1]?.match(/[+#]/)
    : gameState?.is_check || false;

  const displayedLastMoveUci = isReviewing
    ? reviewingPly! > 0
      ? gameState?.uci_history[reviewingPly! - 1]
      : undefined
    : lastMoveUci;

  // Material and captures calculation
  const materialStatus = useMemo(
    () => calculateMaterialFromFen(currentDisplayedFen),
    [currentDisplayedFen]
  );

  // Top and Bottom Player determination based on board orientation & game mode
  const topColor = flipped ? 'white' : 'black';
  const bottomColor = flipped ? 'black' : 'white';

  const isTopAi = gameMode === 'player_vs_ai' && topColor !== playerColor;
  const isBottomAi = gameMode === 'player_vs_ai' && bottomColor !== playerColor;

  const topName = isTopAi
    ? 'Computer'
    : gameMode === 'player_vs_ai'
    ? 'You'
    : `${topColor === 'white' ? 'White' : 'Black'} Player`;

  const bottomName = isBottomAi
    ? 'Computer'
    : gameMode === 'player_vs_ai'
    ? 'You'
    : `${bottomColor === 'white' ? 'White' : 'Black'} Player`;

  return (
    <div className="min-h-screen bg-[#161512] text-stone-200 flex flex-col font-sans selection:bg-emerald-500/30">
      {/* Top Navigation Bar */}
      <header className="px-4 md:px-8 py-3 bg-[#1e1c18] border-b border-stone-800 shadow-md flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-emerald-600/90 flex items-center justify-center font-bold text-white shadow-md shadow-emerald-950">
            ♟
          </div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold tracking-tight text-stone-100">Chess AI</h1>
            <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
              Custom Adversarial Engine
            </span>
          </div>
        </div>

        {/* Status Indicator (Only rendered when AI is computing or initial connection is in progress) */}
        {(isAiThinking || isInitializing) && (
          <div className="flex items-center gap-2.5">
            {isAiThinking ? (
              <div
                data-testid="ai-thinking-indicator"
                className="flex items-center gap-1.5 text-xs text-amber-300 animate-pulse bg-amber-950/60 px-3 py-1 rounded-md border border-amber-800/80 font-medium"
              >
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
                <span>Computer Thinking ({activeDifficulty})...</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 text-xs text-stone-300 bg-stone-800 px-3 py-1 rounded-md border border-stone-700 font-medium">
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-stone-400" />
                <span>Starting Game...</span>
              </div>
            )}
          </div>
        )}
      </header>

      {/* Main Play Area */}
      <main className="flex-1 max-w-[1440px] 2xl:max-w-[1536px] w-full mx-auto px-3 sm:px-4 lg:px-6 xl:px-8 py-3 sm:py-5 flex flex-col lg:flex-row gap-4 xl:gap-6 2xl:gap-8 items-start justify-center">
        {/* Error notification banner */}
        {errorMessage && (
          <div className="w-full lg:col-span-2 p-3 rounded-lg bg-red-950/80 border border-red-800 text-red-300 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button
              onClick={() => setErrorMessage(null)}
              className="text-red-400 hover:text-red-200 text-xs font-bold px-2 py-0.5"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Floating toast notification (no layout shift) */}
        {infoToast && (
          <div
            data-testid="toast-notification"
            role="status"
            onClick={() => {
              if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
              setInfoToast(null);
            }}
            className="fixed top-5 right-5 z-50 max-w-sm px-4 py-2.5 rounded-lg bg-[#21201d]/95 backdrop-blur border border-emerald-500/70 text-emerald-300 text-xs shadow-xl shadow-black/60 flex items-center gap-2 cursor-pointer transition-all duration-300 select-none animate-in fade-in"
          >
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span className="font-medium text-stone-200">{infoToast}</span>
          </div>
        )}

        {/* Chess Playing Area (Left Column: Player Bars + Evaluation Bar + Chessboard) */}
        <div className="w-full max-w-[500px] xl:max-w-[640px] 2xl:max-w-[680px] flex flex-col gap-2 mx-auto lg:mx-0 shrink-0">
          {/* Top Player Bar (Opponent) */}
          <PlayerCard
            name={topName}
            color={topColor}
            isAi={isTopAi}
            difficultyName={isTopAi ? activeDifficulty : undefined}
            isCurrentTurn={!gameState?.is_terminal && gameState?.turn === topColor}
            isThinking={isAiThinking && isTopAi}
            capturedPieces={
              topColor === 'white' ? materialStatus.whiteCaptures : materialStatus.blackCaptures
            }
            materialAdvantage={
              topColor === 'white' ? materialStatus.whiteAdvantage : materialStatus.blackAdvantage
            }
            isCheck={gameState?.is_check && gameState?.turn === topColor}
            isCheckmate={gameState?.status === 'checkmate' && gameState?.turn === topColor}
            isTimeout={gameState?.status === 'timeout' && gameState?.turn === topColor}
            timeRemaining={topColor === 'white' ? whiteClock : blackClock}
            isTimed={gameState?.is_timed ?? true}
            isClockActive={
              !gameState?.is_terminal &&
              gameState?.turn === topColor &&
              (gameState?.clock_started ?? false)
            }
          />

          {/* Board Row: Evaluation Bar + Interactive ChessBoard */}
          <div className="flex items-stretch gap-2.5">
            <EvaluationBar
              scoreCp={analysis ? analysis.score_cp : null}
              isMate={analysis?.is_mate}
              mateInPlies={analysis?.mate_in_plies}
              isAnalyzing={isAnalyzing}
              orientation={flipped ? 'black' : 'white'}
            />

            <div className="flex-1">
              {gameState ? (
                <ChessBoard
                  fen={currentDisplayedFen}
                  legalMovesUci={isReviewing ? [] : gameState.legal_moves_uci}
                  isCheck={displayedCheck}
                  turn={
                    isReviewing
                      ? currentDisplayedFen.split(' ')[1] === 'w'
                        ? 'white'
                        : 'black'
                      : gameState.turn
                  }
                  flipped={flipped}
                  lastMoveUci={displayedLastMoveUci}
                  onMove={handleMakeMove}
                  disabled={
                    isBusy ||
                    gameState.is_terminal ||
                    isReviewing ||
                    (gameMode === 'player_vs_ai' && gameState.turn !== playerColor)
                  }
                >
                  <GameOverModal
                    isOpen={gameState.is_terminal && !isGameOverModalDismissed}
                    status={gameState.status}
                    result={gameState.result}
                    turn={gameState.turn}
                    onAnalyze={handleAnalyzeGame}
                    onNewGame={handleRestart}
                  />
                </ChessBoard>
              ) : (
                <div className="w-full aspect-square rounded-xl bg-stone-900 border border-stone-800 flex flex-col items-center justify-center text-stone-500 gap-3">
                  <RefreshCw className="w-8 h-8 animate-spin text-emerald-500" />
                  <span className="text-sm">Connecting to backend game service...</span>
                </div>
              )}
            </div>
          </div>

          {/* Bottom Player Bar (You) */}
          <PlayerCard
            name={bottomName}
            color={bottomColor}
            isAi={isBottomAi}
            difficultyName={isBottomAi ? activeDifficulty : undefined}
            isCurrentTurn={!gameState?.is_terminal && gameState?.turn === bottomColor}
            isThinking={isAiThinking && isBottomAi}
            capturedPieces={
              bottomColor === 'white'
                ? materialStatus.whiteCaptures
                : materialStatus.blackCaptures
            }
            materialAdvantage={
              bottomColor === 'white'
                ? materialStatus.whiteAdvantage
                : materialStatus.blackAdvantage
            }
            isCheck={gameState?.is_check && gameState?.turn === bottomColor}
            isCheckmate={gameState?.status === 'checkmate' && gameState?.turn === bottomColor}
            isTimeout={gameState?.status === 'timeout' && gameState?.turn === bottomColor}
            timeRemaining={bottomColor === 'white' ? whiteClock : blackClock}
            isTimed={gameState?.is_timed ?? true}
            isClockActive={
              !gameState?.is_terminal &&
              gameState?.turn === bottomColor &&
              (gameState?.clock_started ?? false)
            }
          />

          {/* Subtle Post-Game Review Strip (Only displayed when modal is dismissed during post-game review) */}
          {gameState?.is_terminal && isGameOverModalDismissed && (
            <div
              data-testid="post-game-review-strip"
              className="flex items-center justify-between px-3.5 py-2 rounded-lg bg-stone-900/90 border border-stone-800 text-xs shadow-sm animate-in fade-in duration-150"
            >
              <div className="flex items-center gap-2 text-stone-300">
                <span className="font-semibold text-stone-200">
                  {gameState.status === 'checkmate'
                    ? `Checkmate • ${gameState.turn === 'white' ? 'Black' : 'White'} won`
                    : gameState.status === 'timeout'
                    ? `Timeout • ${gameState.result === '1/2-1/2' ? 'Draw' : `${gameState.turn === 'white' ? 'Black' : 'White'} won`}`
                    : gameState.status === 'stalemate'
                    ? 'Draw • Stalemate'
                    : gameState.status === 'draw_insufficient_material'
                    ? 'Draw • Insufficient Material'
                    : `Draw • ${gameState.result}`}
                </span>
                <span className="text-stone-600">|</span>
                <span className="text-[11px] text-stone-400 font-medium">Review Mode</span>
              </div>
              <button
                type="button"
                data-testid="reopen-game-over-modal"
                onClick={() => setIsGameOverModalDismissed(false)}
                className="text-[11px] font-semibold text-emerald-400 hover:text-emerald-300 hover:underline cursor-pointer transition-colors"
                title="View game over summary"
              >
                Show Summary
              </button>
            </div>
          )}

          {/* Claim Draw Action Banner if Eligible */}
          {gameState && gameState.can_claim_draw && !gameState.is_terminal && (
            <div className="p-2.5 rounded-lg bg-amber-950/60 border border-amber-800/80 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-amber-300">
                <Flag className="w-4 h-4 text-amber-400 shrink-0" />
                <span className="font-semibold text-xs">
                  {gameState.claimable_draw === 'threefold_repetition'
                    ? 'Threefold Repetition Claimable'
                    : '50-Move Draw Claimable'}
                </span>
              </div>
              <button
                onClick={handleClaimDraw}
                disabled={isBusy}
                className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-stone-950 font-bold text-xs transition-colors shadow"
              >
                Claim Draw
              </button>
            </div>
          )}
        </div>

        {/* Sidebar: Tabbed Game Hub (Play, Analysis, Info) */}
        <div className="w-full lg:w-[430px] xl:w-[470px] 2xl:w-[500px] flex flex-col gap-2.5 shrink-0">
          {/* Primary Quick Controls Toolbar (placed above tabs) */}
          <GameControls
            onNewGame={() => initGame()}
            onRestart={handleRestart}
            onUndo={handleUndo}
            onFlipBoard={handleFlipBoard}
            onAIMove={handleAIMove}
            canUndo={gameState ? gameState.can_undo && !isReviewing : false}
            isLoading={isBusy}
            isTerminal={gameState ? gameState.is_terminal : false}
          />

          {/* Navigation Tabs Header */}
          <div className="flex items-center p-1 bg-[#1e1c18] rounded-lg border border-stone-800">
            <button
              data-testid="tab-play"
              onClick={() => setSidebarTab('play')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                sidebarTab === 'play'
                  ? 'bg-stone-800 text-stone-100 shadow-sm'
                  : 'text-stone-400 hover:text-stone-200'
              }`}
            >
              <Swords className="w-3.5 h-3.5" />
              <span>Play & Moves</span>
            </button>

            <button
              data-testid="tab-analysis"
              onClick={() => setSidebarTab('analysis')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                sidebarTab === 'analysis'
                  ? 'bg-stone-800 text-stone-100 shadow-sm'
                  : 'text-stone-400 hover:text-stone-200'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5 text-cyan-400" />
              <span>Analysis</span>
            </button>

            <button
              data-testid="tab-info"
              onClick={() => setSidebarTab('info')}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-md transition-colors ${
                sidebarTab === 'info'
                  ? 'bg-stone-800 text-stone-100 shadow-sm'
                  : 'text-stone-400 hover:text-stone-200'
              }`}
            >
              <Info className="w-3.5 h-3.5 text-amber-400" />
              <span>Info & Rules</span>
            </button>
          </div>

          {/* TAB 1: PLAY & MOVES */}
          {sidebarTab === 'play' && (
            <div className="flex flex-col gap-3">
              {/* Gameplay Mode Selection */}
              <GameModeSelector
                gameMode={gameMode}
                playerColor={playerColor}
                onSelectMode={handleSelectGameMode}
                onSelectPlayerColor={handleSelectPlayerColor}
                disabled={isBusy || isReviewing}
              />

              {/* Time Control Selection */}
              <TimeControlSelector
                currentTimeControl={selectedTimeControl}
                onSelectTimeControl={handleSelectTimeControl}
                disabled={isBusy || isReviewing}
              />

              {/* Difficulty Preset Selection */}
              <DifficultySelector
                currentDifficulty={activeDifficulty}
                onSelectDifficulty={handleSelectDifficulty}
                disabled={isBusy || isReviewing || gameMode === 'pass_and_play'}
              />

              {/* Move History Table */}
              <MoveHistory
                sanHistory={gameState ? gameState.san_history : []}
                selectedPly={reviewingPly}
                onSelectPly={handleSelectPly}
                onCopyPGN={handleCopyPGN}
                onDownloadPGN={handleDownloadPGN}
                onReturnToLive={handleReturnToLive}
              />
            </div>
          )}

          {/* TAB 2: ENGINE ANALYSIS */}
          {sidebarTab === 'analysis' && (
            <div className="flex flex-col gap-3">
              <AnalysisPanel
                analysis={analysis}
                isAnalyzing={isAnalyzing}
                onAnalyze={(depth) => runAnalysis(currentDisplayedFen, depth)}
                autoAnalyze={autoAnalyze}
                onToggleAutoAnalyze={setAutoAnalyze}
                error={analysisError}
              />
            </div>
          )}

          {/* TAB 3: GAME INFO, FEN & RULES */}
          {sidebarTab === 'info' && gameState && (
            <div className="p-4 bg-[#21201d] rounded-lg border border-stone-800 text-xs space-y-3.5 shadow-md">
              <div className="flex items-center justify-between text-stone-400 pb-2 border-b border-stone-800">
                <span className="font-semibold uppercase text-[10px] tracking-wider text-stone-500">
                  Session
                </span>
                <span className="font-mono text-[11px] text-stone-300" title={gameState.session_id}>
                  {gameState.session_id.slice(0, 13)}...
                </span>
              </div>

              {/* FEN Box */}
              <div>
                <div className="flex items-center justify-between text-stone-400 mb-1">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-stone-500">
                    {isReviewing ? `Reviewing FEN (Ply ${reviewingPly})` : 'Current FEN'}
                  </span>
                  <button
                    onClick={handleCopyFen}
                    className="flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300 transition-colors"
                    title="Copy FEN to clipboard"
                  >
                    {copiedFen ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="p-2 rounded bg-stone-900 font-mono text-[10px] text-stone-300 break-all select-all border border-stone-800">
                  {currentDisplayedFen}
                </div>
              </div>

              {/* Turn & Status Meta */}
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 rounded bg-stone-900/60 border border-stone-800">
                  <span className="text-stone-500 block text-[10px]">Fullmoves</span>
                  <span className="font-semibold text-stone-200">{gameState.fullmove_number}</span>
                </div>
                <div className="p-2 rounded bg-stone-900/60 border border-stone-800">
                  <span className="text-stone-500 block text-[10px]">Halfmove Clock</span>
                  <span className="font-semibold text-stone-200">{gameState.halfmove_clock}</span>
                </div>
              </div>

              {/* Claim Draw Button if eligible */}
              {gameState.can_claim_draw && !gameState.is_terminal && (
                <div className="p-2.5 rounded-lg bg-amber-950/60 border border-amber-800/80 flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-amber-300">
                    <Flag className="w-4 h-4 text-amber-400 shrink-0" />
                    <span className="font-semibold">
                      {gameState.claimable_draw === 'threefold_repetition'
                        ? 'Threefold Repetition Claimable'
                        : '50-Move Draw Claimable'}
                    </span>
                  </div>
                  <button
                    onClick={handleClaimDraw}
                    disabled={isBusy}
                    className="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-stone-950 font-bold text-xs transition-colors shadow"
                  >
                    Claim Draw
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-2.5 px-6 text-center text-[11px] text-stone-500 border-t border-stone-800/60 bg-[#161512]">
        Chess AI • Custom Adversarial Engine • Heuristic Evaluation
      </footer>
    </div>
  );
};
