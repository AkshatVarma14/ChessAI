import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GameModeSelector } from '../components/GameModeSelector';

describe('GameModeSelector Component', () => {
  it('renders both game mode options and highlights the active mode', () => {
    const onSelectMode = vi.fn();
    const onSelectPlayerColor = vi.fn();

    render(
      <GameModeSelector
        gameMode="player_vs_ai"
        playerColor="white"
        onSelectMode={onSelectMode}
        onSelectPlayerColor={onSelectPlayerColor}
      />
    );

    const vsAiBtn = screen.getByTestId('mode-player-vs-ai');
    const passPlayBtn = screen.getByTestId('mode-pass-and-play');

    expect(vsAiBtn).toBeInTheDocument();
    expect(passPlayBtn).toBeInTheDocument();
    expect(vsAiBtn).toHaveAttribute('aria-checked', 'true');
    expect(passPlayBtn).toHaveAttribute('aria-checked', 'false');

    // Click Pass & Play
    fireEvent.click(passPlayBtn);
    expect(onSelectMode).toHaveBeenCalledWith('pass_and_play');
  });

  it('displays side selection (White/Black) when in player_vs_ai mode', () => {
    const onSelectMode = vi.fn();
    const onSelectPlayerColor = vi.fn();

    render(
      <GameModeSelector
        gameMode="player_vs_ai"
        playerColor="white"
        onSelectMode={onSelectMode}
        onSelectPlayerColor={onSelectPlayerColor}
      />
    );

    const whiteBtn = screen.getByTestId('color-select-white');
    const blackBtn = screen.getByTestId('color-select-black');

    expect(whiteBtn).toBeInTheDocument();
    expect(blackBtn).toBeInTheDocument();
    expect(whiteBtn).toHaveAttribute('aria-checked', 'true');
    expect(blackBtn).toHaveAttribute('aria-checked', 'false');

    fireEvent.click(blackBtn);
    expect(onSelectPlayerColor).toHaveBeenCalledWith('black');
  });

  it('hides player color selection when in pass_and_play mode', () => {
    render(
      <GameModeSelector
        gameMode="pass_and_play"
        playerColor="white"
        onSelectMode={vi.fn()}
        onSelectPlayerColor={vi.fn()}
      />
    );

    expect(screen.queryByTestId('color-select-white')).not.toBeInTheDocument();
    expect(screen.queryByTestId('color-select-black')).not.toBeInTheDocument();
  });

  it('disables controls when disabled prop is true', () => {
    render(
      <GameModeSelector
        gameMode="player_vs_ai"
        playerColor="white"
        onSelectMode={vi.fn()}
        onSelectPlayerColor={vi.fn()}
        disabled={true}
      />
    );

    expect(screen.getByTestId('mode-player-vs-ai')).toBeDisabled();
    expect(screen.getByTestId('mode-pass-and-play')).toBeDisabled();
    expect(screen.getByTestId('color-select-white')).toBeDisabled();
    expect(screen.getByTestId('color-select-black')).toBeDisabled();
  });
});
