/**
 * TypeScript types mirroring backend Pydantic schemas and game models.
 */

export type GameStatus =
  | 'active'
  | 'checkmate'
  | 'stalemate'
  | 'draw_insufficient_material'
  | 'draw_75_moves'
  | 'draw_fivefold_repetition'
  | 'draw_repetition'
  | 'draw_50_moves'
  | 'draw_claimed'
  | 'timeout';

export type GameResult = '1-0' | '0-1' | '1/2-1/2' | '*';

export type Color = 'white' | 'black';

export type PieceType = 'p' | 'n' | 'b' | 'r' | 'q' | 'k';

export type PieceSymbol =
  | 'P' | 'N' | 'B' | 'R' | 'Q' | 'K'
  | 'p' | 'n' | 'b' | 'r' | 'q' | 'k';

export type DifficultyLevel = 'beginner' | 'easy' | 'medium' | 'hard' | 'expert';

export type TimeControl = 'bullet' | 'blitz' | 'rapid' | 'classic' | 'casual';

export type GameMode = 'player_vs_ai' | 'pass_and_play';

export type PlayerColor = 'white' | 'black';

export interface GameState {
  session_id: string;
  fen: string;
  turn: Color;
  fullmove_number: number;
  halfmove_clock: number;
  is_check: boolean;
  is_terminal: boolean;
  status: GameStatus;
  result: GameResult;
  san_history: string[];
  uci_history: string[];
  fen_history: string[];
  legal_moves_uci: string[];
  legal_moves_san: string[];
  can_undo: boolean;
  difficulty: DifficultyLevel;
  can_claim_draw?: boolean;
  claimable_draw?: 'fifty_moves' | 'threefold_repetition' | null;
  time_control?: TimeControl;
  is_timed?: boolean;
  white_time_remaining?: number | null;
  black_time_remaining?: number | null;
  clock_started?: boolean;
  active_clock?: Color | null;
}

export interface NewGameRequest {
  initial_fen?: string;
  difficulty?: DifficultyLevel;
  time_control?: TimeControl;
}

export interface DifficultyUpdateRequest {
  session_id: string;
  difficulty: DifficultyLevel;
}

export interface AIMoveRequest {
  session_id: string;
}

export interface MakeMoveRequest {
  session_id: string;
  move: string;
}

export interface UndoMoveRequest {
  session_id: string;
  plies?: number;
}

export interface RestartGameRequest {
  session_id: string;
}

export interface ApiError {
  error?: string;
  detail: string;
  session_id?: string;
}

export interface AnalyzePositionRequest {
  session_id?: string;
  fen?: string;
  depth?: number;
  time_limit_ms?: number;
}

export interface AnalysisResponse {
  score_cp: number;
  is_mate: boolean;
  mate_in_plies: number | null;
  is_terminal?: boolean;
  claimable_draw?: string | null;
  depth: number;
  nodes_searched: number;
  quiescence_nodes: number;
  elapsed_ms: number;
  nodes_per_second: number;
  best_move_uci: string | null;
  best_move_san: string | null;
  pv_uci: string[];
  pv_san: string[];
  tt_hits: number;
  tt_probes: number;
  tt_cutoffs: number;
  tt_stores: number;
}

export interface ClaimDrawRequest {
  session_id: string;
}

export interface PGNResponse {
  session_id: string;
  pgn: string;
}
