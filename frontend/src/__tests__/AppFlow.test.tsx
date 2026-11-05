import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from '../App';
import { chessApi } from '../services/api';
import { GameState } from '../types/chess';

vi.mock('../services/api', () => ({
  chessApi: {
    createNewGame: vi.fn(),
    makeMove: vi.fn(),
    makeAIMove: vi.fn(),
    setDifficulty: vi.fn(),
    undoMove: vi.fn(),
    restartGame: vi.fn(),
    getGameState: vi.fn(),
    analyzePosition: vi.fn(),
    getPGN: vi.fn(),
    claimDraw: vi.fn(),
  },
}));

const mockInitialGameState: GameState = {
  session_id: 'test-session-1234',
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  turn: 'white',
  fullmove_number: 1,
  halfmove_clock: 0,
  is_check: false,
  is_terminal: false,
  status: 'active',
  result: '*',
  san_history: [],
  uci_history: [],
  fen_history: ['rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'],
  legal_moves_uci: ['e2e4', 'd2d4', 'g1f3'],
  legal_moves_san: ['e4', 'd4', 'Nf3'],
  can_undo: false,
  difficulty: 'medium',
  can_claim_draw: false,
  claimable_draw: null,
};

const mockAfterMoveState: GameState = {
  ...mockInitialGameState,
  fen: 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1',
  turn: 'black',
  halfmove_clock: 0,
  san_history: ['e4'],
  uci_history: ['e2e4'],
  legal_moves_uci: ['e7e5', 'c7c5', 'g8f6'],
  legal_moves_san: ['e5', 'c5', 'Nf6'],
  can_undo: true,
};

const mockAfterAiState: GameState = {
  ...mockInitialGameState,
  fen: 'rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
  turn: 'white',
  fullmove_number: 2,
  san_history: ['e4', 'd5'],
  uci_history: ['e2e4', 'd7d5'],
  legal_moves_uci: ['e4d5', 'g1f3'],
  legal_moves_san: ['exd5', 'Nf3'],
  can_undo: true,
};

describe('App Gameplay Flow & Usability Verification', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (chessApi.createNewGame as any).mockResolvedValue(mockInitialGameState);
    (chessApi.makeMove as any).mockResolvedValue(mockAfterMoveState);
    (chessApi.makeAIMove as any).mockResolvedValue(mockAfterAiState);
    (chessApi.setDifficulty as any).mockImplementation((_sid: string, diff: string) =>
      Promise.resolve({ ...mockInitialGameState, difficulty: diff })
    );
    (chessApi.restartGame as any).mockResolvedValue(mockInitialGameState);
    (chessApi.undoMove as any).mockResolvedValue(mockInitialGameState);
    (chessApi.getGameState as any).mockResolvedValue(mockInitialGameState);
  });

  it('initializes game exactly once on mount without infinite request loops', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    // Exactly one call to createNewGame on initial mount!
    expect(chessApi.createNewGame).toHaveBeenCalledTimes(1);

    // Initial state does not start in thinking
    expect(screen.queryByTestId('ai-thinking-indicator')).not.toBeInTheDocument();

    // Ready badge is removed from header (Stage 10.7)
    expect(screen.queryByText('Ready')).not.toBeInTheDocument();

    // Mode is Player vs Computer and Player is White (moves first)
    expect(screen.getByTestId('status-your-turn')).toBeInTheDocument();
    expect(screen.getByTestId('player-card-white')).toHaveTextContent('To move');
  });

  it('does not trigger automatic AI move before the human makes their first move as White', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    // AI move should not be invoked on mount when human plays White
    expect(chessApi.makeAIMove).not.toHaveBeenCalled();
    expect(screen.getByTestId('status-your-turn')).toBeInTheDocument();
  });

  it('triggers AI move automatically after human move in Player vs Computer mode', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    // Human makes move by clicking e2 then e4
    const e2 = screen.getByTestId('square-e2');
    fireEvent.click(e2);
    const e4 = screen.getByTestId('square-e4');
    fireEvent.click(e4);

    await waitFor(() => {
      expect(chessApi.makeMove).toHaveBeenCalledWith('test-session-1234', 'e2e4');
      expect(chessApi.makeAIMove).toHaveBeenCalledWith('test-session-1234');
    });

    // Board returns to interactive state
    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
      expect(screen.getByTestId('status-your-turn')).toBeInTheDocument();
    });
  });

  it('does not trigger automatic AI reply when in Pass & Play mode', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    // Switch to Pass & Play
    const passPlayBtn = screen.getByTestId('mode-pass-and-play');
    fireEvent.click(passPlayBtn);

    // Human makes move
    const e2 = screen.getByTestId('square-e2');
    fireEvent.click(e2);
    const e4 = screen.getByTestId('square-e4');
    fireEvent.click(e4);

    await waitFor(() => {
      expect(chessApi.makeMove).toHaveBeenCalledWith('test-session-1234', 'e2e4');
    });

    // Make AIMove should NOT be called in Pass & Play!
    expect(chessApi.makeAIMove).not.toHaveBeenCalled();
  });

  it('clears loading state and displays error banner when API call fails', async () => {
    (chessApi.makeMove as any).mockRejectedValueOnce(new Error('Network timeout during move execution'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    const e2 = screen.getByTestId('square-e2');
    fireEvent.click(e2);
    const e4 = screen.getByTestId('square-e4');
    fireEvent.click(e4);

    await waitFor(() => {
      expect(screen.getByText('Network timeout during move execution')).toBeInTheDocument();
    });

    // Crucially: UI does NOT stay stuck; returns to interactive
    expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    expect(screen.queryByTestId('ai-thinking-indicator')).not.toBeInTheDocument();
  });

  it('gracefully handles HTTP 409 StalePositionError by resynchronizing game state', async () => {
    (chessApi.makeAIMove as any).mockRejectedValueOnce(
      new Error('AI move rejected: position changed during search. (409 Conflict)')
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    const e2 = screen.getByTestId('square-e2');
    fireEvent.click(e2);
    const e4 = screen.getByTestId('square-e4');
    fireEvent.click(e4);

    await waitFor(() => {
      // Re-synchronization was called
      expect(chessApi.getGameState).toHaveBeenCalledWith('test-session-1234');
    });

    // UI is not stuck
    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
      expect(screen.queryByTestId('ai-thinking-indicator')).not.toBeInTheDocument();
    });
  });

  it('allows manual AI move triggering in any mode via AI Move button', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    const aiBtn = screen.getByText('AI Move');
    fireEvent.click(aiBtn);

    await waitFor(() => {
      expect(chessApi.makeAIMove).toHaveBeenCalledWith('test-session-1234');
    });
  });

  it('updates difficulty and notifies backend without resetting board', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    const expertBtn = screen.getByTestId('difficulty-option-expert');
    fireEvent.click(expertBtn);

    await waitFor(() => {
      expect(chessApi.setDifficulty).toHaveBeenCalledWith('test-session-1234', 'expert');
    });
  });

  it('reverts exactly 1 ply in Player vs AI mode when undo is clicked', async () => {
    // Start with game after human move (can_undo = true)
    (chessApi.createNewGame as any).mockResolvedValueOnce({
      ...mockAfterMoveState,
      can_undo: true,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    const undoBtn = screen.getByTestId('control-undo');
    expect(undoBtn).not.toBeDisabled();
    fireEvent.click(undoBtn);

    await waitFor(() => {
      // Must call undoMove with EXACTLY 1 ply, NEVER 2 plies
      expect(chessApi.undoMove).toHaveBeenCalledWith('test-session-1234', 1);
    });

    // Crucially: Undo must NOT auto-trigger an AI move!
    expect(chessApi.makeAIMove).not.toHaveBeenCalled();
  });

  it('reverts exactly 1 ply in Pass & Play mode when undo is clicked', async () => {
    (chessApi.createNewGame as any).mockResolvedValueOnce({
      ...mockAfterMoveState,
      can_undo: true,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    // Switch to Pass & Play
    const passPlayBtn = screen.getByTestId('mode-pass-and-play');
    fireEvent.click(passPlayBtn);

    const undoBtn = screen.getByTestId('control-undo');
    fireEvent.click(undoBtn);

    await waitFor(() => {
      expect(chessApi.undoMove).toHaveBeenCalledWith('test-session-1234', 1);
    });
    expect(chessApi.makeAIMove).not.toHaveBeenCalled();
  });

  it('allows consecutive undos each removing 1 ply at a time', async () => {
    (chessApi.createNewGame as any).mockResolvedValueOnce({
      ...mockAfterAiState,
      can_undo: true,
    });
    (chessApi.undoMove as any)
      .mockResolvedValueOnce({
        ...mockAfterMoveState,
        can_undo: true,
      })
      .mockResolvedValueOnce({
        ...mockInitialGameState,
        can_undo: false,
      });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    const undoBtn = screen.getByTestId('control-undo');
    // First undo (takes back AI's move)
    fireEvent.click(undoBtn);

    await waitFor(() => {
      expect(chessApi.undoMove).toHaveBeenNthCalledWith(1, 'test-session-1234', 1);
    });

    // AI move should not be auto-triggered
    expect(chessApi.makeAIMove).not.toHaveBeenCalled();

    // Second undo (takes back Human's move)
    fireEvent.click(undoBtn);

    await waitFor(() => {
      expect(chessApi.undoMove).toHaveBeenNthCalledWith(2, 'test-session-1234', 1);
    });
    expect(chessApi.makeAIMove).not.toHaveBeenCalled();
  });

  it('calls claimDraw when Claim Draw button is clicked', async () => {
    (chessApi.createNewGame as any).mockResolvedValueOnce({
      ...mockInitialGameState,
      can_claim_draw: true,
      claimable_draw: 'threefold_repetition',
    });
    (chessApi.claimDraw as any).mockResolvedValueOnce({
      ...mockInitialGameState,
      is_terminal: true,
      status: 'draw',
      result: '1/2-1/2',
      can_claim_draw: false,
      claimable_draw: null,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Claim Draw')).toBeInTheDocument();
    });

    const claimBtn = screen.getByText('Claim Draw');
    fireEvent.click(claimBtn);

    await waitFor(() => {
      expect(chessApi.claimDraw).toHaveBeenCalledWith('test-session-1234');
    });
  });

  it('displays GameOverModal when game reaches checkmate, and allows post-game analysis and reopening summary', async () => {
    (chessApi.createNewGame as any).mockResolvedValueOnce({
      ...mockInitialGameState,
      is_terminal: true,
      status: 'checkmate',
      result: '1-0',
      turn: 'black',
      san_history: ['e4', 'e5', 'Qh5', 'Nc6', 'Bc4', 'Nf6', 'Qxf7#'],
      uci_history: ['e2e4', 'e7e5', 'd1h5', 'b8c6', 'f1c4', 'g8f6', 'h5f7'],
    });

    render(<App />);

    // Game over modal is displayed centered on board
    await waitFor(() => {
      expect(screen.getByTestId('game-over-modal')).toBeInTheDocument();
      expect(screen.getByTestId('game-over-title')).toHaveTextContent('Checkmate');
      expect(screen.getByTestId('game-over-explanation')).toHaveTextContent('White wins by checkmate!');
      expect(screen.getByTestId('game-over-score')).toHaveTextContent('1-0');
    });

    // Clicking Analyze Game dismisses modal and enters review mode
    const analyzeBtn = screen.getByTestId('modal-analyze-game');
    fireEvent.click(analyzeBtn);

    await waitFor(() => {
      expect(screen.queryByTestId('game-over-modal')).not.toBeInTheDocument();
      expect(screen.getByTestId('post-game-review-strip')).toBeInTheDocument();
    });

    // Move history and final position are intact
    expect(screen.getByText('Qxf7#')).toBeInTheDocument();

    // Clicking "Show Summary" re-opens the game over modal
    const showSummaryBtn = screen.getByTestId('reopen-game-over-modal');
    fireEvent.click(showSummaryBtn);

    await waitFor(() => {
      expect(screen.getByTestId('game-over-modal')).toBeInTheDocument();
    });
  });

  it('resets game when New Game button is clicked in GameOverModal', async () => {
    (chessApi.createNewGame as any).mockResolvedValueOnce({
      ...mockInitialGameState,
      is_terminal: true,
      status: 'stalemate',
      result: '1/2-1/2',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('game-over-modal')).toBeInTheDocument();
    });

    const newGameBtn = screen.getByTestId('modal-new-game');
    fireEvent.click(newGameBtn);

    await waitFor(() => {
      // restartGame should be called to restart the match cleanly
      expect(chessApi.restartGame).toHaveBeenCalledWith('test-session-1234');
    });
  });

  it('does not display the Ready badge in the top navigation bar', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId('chess-board')).toBeInTheDocument();
    });

    // Logo, title and label are rendered
    expect(screen.getByText('Chess AI')).toBeInTheDocument();
    expect(screen.getByText('Custom Adversarial Engine')).toBeInTheDocument();

    // Ready badge is completely removed
    expect(screen.queryByText('Ready')).not.toBeInTheDocument();
  });
});
