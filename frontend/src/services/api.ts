import {
  GameState,
  NewGameRequest,
  MakeMoveRequest,
  UndoMoveRequest,
  RestartGameRequest,
  DifficultyLevel,
  DifficultyUpdateRequest,
  AIMoveRequest,
  AnalysisResponse,
  AnalyzePositionRequest,
  PGNResponse,
  TimeControl,
} from '../types/chess';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

class ChessApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      const response = await fetch(url, { ...options, headers });
      if (!response.ok) {
        let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage = errorData.detail;
          } else if (errorData.error) {
            errorMessage = errorData.error;
          }
        } catch {
          // Response was not JSON
        }
        throw new Error(errorMessage);
      }
      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof Error) {
        throw err;
      }
      throw new Error('An unknown network error occurred.');
    }
  }

  async createNewGame(
    initial_fen?: string,
    difficulty?: DifficultyLevel,
    time_control?: TimeControl
  ): Promise<GameState> {
    const payload: NewGameRequest = {
      ...(initial_fen ? { initial_fen } : {}),
      ...(difficulty ? { difficulty } : {}),
      ...(time_control ? { time_control } : {}),
    };
    return this.request<GameState>('/api/game/new', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async setDifficulty(session_id: string, difficulty: DifficultyLevel): Promise<GameState> {
    const payload: DifficultyUpdateRequest = { session_id, difficulty };
    return this.request<GameState>('/api/game/difficulty', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async makeAIMove(session_id: string): Promise<GameState> {
    const payload: AIMoveRequest = { session_id };
    return this.request<GameState>('/api/game/ai-move', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async makeMove(session_id: string, move: string): Promise<GameState> {
    const payload: MakeMoveRequest = { session_id, move };
    return this.request<GameState>('/api/game/move', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async undoMove(session_id: string, plies: number = 1): Promise<GameState> {
    const payload: UndoMoveRequest = { session_id, plies };
    return this.request<GameState>('/api/game/undo', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async restartGame(session_id: string): Promise<GameState> {
    const payload: RestartGameRequest = { session_id };
    return this.request<GameState>('/api/game/restart', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getGameState(session_id: string): Promise<GameState> {
    return this.request<GameState>(`/api/game/state?session_id=${encodeURIComponent(session_id)}`, {
      method: 'GET',
    });
  }

  async analyzePosition(
    payload: AnalyzePositionRequest,
    signal?: AbortSignal
  ): Promise<AnalysisResponse> {
    return this.request<AnalysisResponse>('/api/game/analyze', {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    });
  }

  async getPGN(session_id: string): Promise<PGNResponse> {
    return this.request<PGNResponse>(`/api/game/pgn?session_id=${encodeURIComponent(session_id)}`, {
      method: 'GET',
    });
  }

  async claimDraw(session_id: string): Promise<GameState> {
    return this.request<GameState>('/api/game/claim-draw', {
      method: 'POST',
      body: JSON.stringify({ session_id }),
    });
  }
}

export const chessApi = new ChessApiClient();
