import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GameControls } from '../components/GameControls';
import { MoveHistory } from '../components/MoveHistory';
import { GameStatus } from '../components/GameStatus';

describe('GameControls Component', () => {
  it('renders all control buttons and responds to clicks', () => {
    const onNewGame = vi.fn();
    const onRestart = vi.fn();
    const onUndo = vi.fn();
    const onFlipBoard = vi.fn();

    render(
      <GameControls
        onNewGame={onNewGame}
        onRestart={onRestart}
        onUndo={onUndo}
        onFlipBoard={onFlipBoard}
        canUndo={true}
        isLoading={false}
      />
    );

    fireEvent.click(screen.getByText('New Game'));
    expect(onNewGame).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Undo'));
    expect(onUndo).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Restart'));
    expect(onRestart).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText('Flip Board'));
    expect(onFlipBoard).toHaveBeenCalledTimes(1);
  });

  it('disables undo button when canUndo is false', () => {
    render(
      <GameControls
        onNewGame={vi.fn()}
        onRestart={vi.fn()}
        onUndo={vi.fn()}
        onFlipBoard={vi.fn()}
        canUndo={false}
        isLoading={false}
      />
    );

    const undoBtn = screen.getByText('Undo').closest('button');
    expect(undoBtn).toBeDisabled();
  });

  it('disables AI Move button when isTerminal is true', () => {
    const onAIMove = vi.fn();
    render(
      <GameControls
        onNewGame={vi.fn()}
        onRestart={vi.fn()}
        onUndo={vi.fn()}
        onFlipBoard={vi.fn()}
        onAIMove={onAIMove}
        canUndo={true}
        isLoading={false}
        isTerminal={true}
      />
    );

    const aiBtn = screen.getByText('AI Move').closest('button');
    expect(aiBtn).toBeDisabled();
    if (aiBtn) fireEvent.click(aiBtn);
    expect(onAIMove).not.toHaveBeenCalled();
  });

  it('disables AI Move button when isLoading is true', () => {
    const onAIMove = vi.fn();
    render(
      <GameControls
        onNewGame={vi.fn()}
        onRestart={vi.fn()}
        onUndo={vi.fn()}
        onFlipBoard={vi.fn()}
        onAIMove={onAIMove}
        canUndo={true}
        isLoading={true}
        isTerminal={false}
      />
    );

    const aiBtn = screen.getByText('AI Move').closest('button');
    expect(aiBtn).toBeDisabled();
  });
});

describe('MoveHistory Component', () => {
  it('displays moves in grouped fullmove notation', () => {
    render(<MoveHistory sanHistory={['e4', 'e5', 'Nf3', 'Nc6', 'Bc4']} />);

    expect(screen.getByText('1.')).toBeInTheDocument();
    expect(screen.getByText('e4')).toBeInTheDocument();
    expect(screen.getByText('e5')).toBeInTheDocument();
    expect(screen.getByText('2.')).toBeInTheDocument();
    expect(screen.getByText('Nf3')).toBeInTheDocument();
    expect(screen.getByText('Nc6')).toBeInTheDocument();
    expect(screen.getByText('3.')).toBeInTheDocument();
    expect(screen.getByText('Bc4')).toBeInTheDocument();
  });

  it('shows empty placeholder when no moves have been played', () => {
    render(<MoveHistory sanHistory={[]} />);
    expect(screen.getByText('No moves played yet.')).toBeInTheDocument();
  });
});

describe('GameStatus Component', () => {
  it('displays turn indicator for active game', () => {
    render(
      <GameStatus
        turn="white"
        isCheck={false}
        isTerminal={false}
        status="active"
        result="*"
      />
    );

    expect(screen.getByText('White to move')).toBeInTheDocument();
    expect(screen.getByText('Game in progress')).toBeInTheDocument();
  });

  it('displays check badge when king is in check', () => {
    render(
      <GameStatus
        turn="black"
        isCheck={true}
        isTerminal={false}
        status="active"
        result="*"
      />
    );

    expect(screen.getByText('Black to move')).toBeInTheDocument();
    expect(screen.getByText('King is in check!')).toBeInTheDocument();
    expect(screen.getByText('Check')).toBeInTheDocument();
  });

  it('displays checkmate terminal status and winner', () => {
    render(
      <GameStatus
        turn="black"
        isCheck={true}
        isTerminal={true}
        status="checkmate"
        result="1-0"
      />
    );

    expect(screen.getByText('Checkmate!')).toBeInTheDocument();
    expect(screen.getByText('White wins the game (1-0)')).toBeInTheDocument();
    expect(screen.getByText('Concluded')).toBeInTheDocument();
  });

  it('displays stalemate terminal status', () => {
    render(
      <GameStatus
        turn="black"
        isCheck={false}
        isTerminal={true}
        status="stalemate"
        result="1/2-1/2"
      />
    );

    expect(screen.getByText('Draw — Stalemate')).toBeInTheDocument();
  });
});
