import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DifficultySelector } from '../components/DifficultySelector';
import { DifficultyLevel } from '../types/chess';

describe('DifficultySelector Component', () => {
  const levels: DifficultyLevel[] = ['beginner', 'easy', 'medium', 'hard', 'expert'];

  it('renders all five difficulty options with badges', () => {
    const onSelect = vi.fn();
    render(<DifficultySelector currentDifficulty="medium" onSelectDifficulty={onSelect} />);

    expect(screen.getByText('AI Difficulty Level')).toBeInTheDocument();
    expect(screen.getByText('Beginner')).toBeInTheDocument();
    expect(screen.getByText('Easy')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('Hard')).toBeInTheDocument();
    expect(screen.getByText('Expert')).toBeInTheDocument();

    expect(screen.getByText('Depth 1')).toBeInTheDocument();
    expect(screen.getByText('Depth 2')).toBeInTheDocument();
    expect(screen.getByText('Depth 3')).toBeInTheDocument();
    expect(screen.getByText('Depth 4')).toBeInTheDocument();
    expect(screen.getByText('Depth 5')).toBeInTheDocument();
  });

  it('indicates the active difficulty and triggers callback on change', () => {
    const onSelect = vi.fn();
    render(<DifficultySelector currentDifficulty="medium" onSelectDifficulty={onSelect} />);

    const beginnerBtn = screen.getByTestId('difficulty-option-beginner');
    expect(beginnerBtn).toBeInTheDocument();
    expect(beginnerBtn).toHaveAttribute('aria-checked', 'false');

    const mediumBtn = screen.getByTestId('difficulty-option-medium');
    expect(mediumBtn).toHaveAttribute('aria-checked', 'true');

    fireEvent.click(beginnerBtn);
    expect(onSelect).toHaveBeenCalledWith('beginner');

    const expertBtn = screen.getByTestId('difficulty-option-expert');
    fireEvent.click(expertBtn);
    expect(onSelect).toHaveBeenCalledWith('expert');
  });

  it('disables all options when disabled prop is true', () => {
    const onSelect = vi.fn();
    render(<DifficultySelector currentDifficulty="easy" onSelectDifficulty={onSelect} disabled={true} />);

    levels.forEach((lvl) => {
      const btn = screen.getByTestId(`difficulty-option-${lvl}`);
      expect(btn).toBeDisabled();
    });
  });

  it('omits redundant explanatory notice to keep interface clean', () => {
    render(<DifficultySelector currentDifficulty="hard" onSelectDifficulty={vi.fn()} />);
    expect(
      screen.queryByText('Difficulty changes take effect immediately on the next AI move.')
    ).not.toBeInTheDocument();
  });
});
