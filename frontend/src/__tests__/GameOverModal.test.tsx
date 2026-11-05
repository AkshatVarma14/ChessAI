import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GameOverModal } from '../components/GameOverModal';

describe('GameOverModal Component', () => {
  it('does not render when isOpen is false', () => {
    const { container } = render(
      <GameOverModal
        isOpen={false}
        status="checkmate"
        result="1-0"
        turn="black"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.queryByTestId('game-over-modal')).not.toBeInTheDocument();
    expect(container.firstChild).toBeNull();
  });

  it('renders checkmate when White wins (1-0)', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="checkmate"
        result="1-0"
        turn="black"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-modal')).toBeInTheDocument();
    expect(screen.getByTestId('game-over-title')).toHaveTextContent('Checkmate');
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent('White wins by checkmate!');
    expect(screen.getByTestId('game-over-score')).toHaveTextContent('1-0');
  });

  it('renders checkmate when Black wins (0-1)', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="checkmate"
        result="0-1"
        turn="white"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent('Checkmate');
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent('Black wins by checkmate!');
    expect(screen.getByTestId('game-over-score')).toHaveTextContent('0-1');
  });

  it('renders stalemate with 1/2-1/2 score', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="stalemate"
        result="1/2-1/2"
        turn="black"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent('Stalemate');
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent('The game is a draw by stalemate.');
    expect(screen.getByTestId('game-over-score')).toHaveTextContent('½–½');
  });

  it('renders timeout win for White (1-0)', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="timeout"
        result="1-0"
        turn="black"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent("Time's Up");
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent('White wins on time!');
    expect(screen.getByTestId('game-over-score')).toHaveTextContent('1-0');
  });

  it('renders timeout win for Black (0-1)', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="timeout"
        result="0-1"
        turn="white"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent("Time's Up");
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent('Black wins on time!');
    expect(screen.getByTestId('game-over-score')).toHaveTextContent('0-1');
  });

  it('renders timeout draw under FIDE 6.9 when opponent has insufficient material', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="timeout"
        result="1/2-1/2"
        turn="white"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent("Time's Up");
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent(
      'Draw on time — opponent has insufficient material to checkmate'
    );
    expect(screen.getByTestId('game-over-score')).toHaveTextContent('½–½');
  });

  it('renders draw by insufficient material', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="draw_insufficient_material"
        result="1/2-1/2"
        turn="white"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent('Draw');
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent(
      'Draw by insufficient mating material.'
    );
    expect(screen.getByTestId('game-over-score')).toHaveTextContent('½–½');
  });

  it('renders draw by automatic 75-move rule', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="draw_75_moves"
        result="1/2-1/2"
        turn="black"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent('Draw');
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent(
      'Draw by 75-move rule (automatic).'
    );
  });

  it('renders draw by automatic fivefold repetition', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="draw_fivefold_repetition"
        result="1/2-1/2"
        turn="white"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent('Draw');
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent(
      'Draw by fivefold repetition (automatic).'
    );
  });

  it('renders claimed 50-move draw', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="draw_50_moves"
        result="1/2-1/2"
        turn="white"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent('Draw');
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent(
      'Draw by 50-move rule (claimed).'
    );
  });

  it('renders claimed threefold repetition draw', () => {
    render(
      <GameOverModal
        isOpen={true}
        status="draw_claimed"
        result="1/2-1/2"
        turn="white"
        onAnalyze={vi.fn()}
        onNewGame={vi.fn()}
      />
    );

    expect(screen.getByTestId('game-over-title')).toHaveTextContent('Draw');
    expect(screen.getByTestId('game-over-explanation')).toHaveTextContent(
      'Draw by threefold repetition (claimed).'
    );
  });

  it('triggers onAnalyze callback when Analyze Game button is clicked', () => {
    const handleAnalyze = vi.fn();
    const handleNewGame = vi.fn();

    render(
      <GameOverModal
        isOpen={true}
        status="checkmate"
        result="1-0"
        turn="black"
        onAnalyze={handleAnalyze}
        onNewGame={handleNewGame}
      />
    );

    const analyzeBtn = screen.getByTestId('modal-analyze-game');
    fireEvent.click(analyzeBtn);

    expect(handleAnalyze).toHaveBeenCalledTimes(1);
    expect(handleNewGame).not.toHaveBeenCalled();
  });

  it('triggers onNewGame callback when New Game button is clicked', () => {
    const handleAnalyze = vi.fn();
    const handleNewGame = vi.fn();

    render(
      <GameOverModal
        isOpen={true}
        status="checkmate"
        result="1-0"
        turn="black"
        onAnalyze={handleAnalyze}
        onNewGame={handleNewGame}
      />
    );

    const newGameBtn = screen.getByTestId('modal-new-game');
    fireEvent.click(newGameBtn);

    expect(handleNewGame).toHaveBeenCalledTimes(1);
    expect(handleAnalyze).not.toHaveBeenCalled();
  });

  it('triggers onAnalyze callback when Escape key is pressed', () => {
    const handleAnalyze = vi.fn();
    const handleNewGame = vi.fn();

    render(
      <GameOverModal
        isOpen={true}
        status="checkmate"
        result="1-0"
        turn="black"
        onAnalyze={handleAnalyze}
        onNewGame={handleNewGame}
      />
    );

    fireEvent.keyDown(window, { key: 'Escape' });

    expect(handleAnalyze).toHaveBeenCalledTimes(1);
    expect(handleNewGame).not.toHaveBeenCalled();
  });
});
