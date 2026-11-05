import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { TimeControlSelector } from '../components/TimeControlSelector';
import { TimeControl } from '../types/chess';

describe('TimeControlSelector Component', () => {
  it('renders all 5 time control modes with correct labels', () => {
    const onSelect = vi.fn();
    render(
      <TimeControlSelector
        currentTimeControl="rapid"
        onSelectTimeControl={onSelect}
      />
    );

    expect(screen.getByTestId('time-control-bullet')).toBeInTheDocument();
    expect(screen.getByTestId('time-control-blitz')).toBeInTheDocument();
    expect(screen.getByTestId('time-control-rapid')).toBeInTheDocument();
    expect(screen.getByTestId('time-control-classic')).toBeInTheDocument();
    expect(screen.getByTestId('time-control-casual')).toBeInTheDocument();

    expect(screen.getByText('Bullet')).toBeInTheDocument();
    expect(screen.getByText('Blitz')).toBeInTheDocument();
    expect(screen.getByText('Rapid')).toBeInTheDocument();
    expect(screen.getByText('Classic')).toBeInTheDocument();
    expect(screen.getByText('Casual')).toBeInTheDocument();
  });

  it('highlights the selected time control', () => {
    const onSelect = vi.fn();
    const { rerender } = render(
      <TimeControlSelector
        currentTimeControl="rapid"
        onSelectTimeControl={onSelect}
      />
    );

    const rapidBtn = screen.getByTestId('time-control-rapid');
    expect(rapidBtn.className).toContain('bg-emerald-700');

    const blitzBtn = screen.getByTestId('time-control-blitz');
    expect(blitzBtn.className).not.toContain('bg-emerald-700');

    rerender(
      <TimeControlSelector
        currentTimeControl="blitz"
        onSelectTimeControl={onSelect}
      />
    );

    expect(screen.getByTestId('time-control-blitz').className).toContain('bg-emerald-700');
  });

  it('calls onSelectTimeControl callback with correct mode on click', () => {
    const onSelect = vi.fn();
    render(
      <TimeControlSelector
        currentTimeControl="rapid"
        onSelectTimeControl={onSelect}
      />
    );

    fireEvent.click(screen.getByTestId('time-control-bullet'));
    expect(onSelect).toHaveBeenCalledWith('bullet');

    fireEvent.click(screen.getByTestId('time-control-casual'));
    expect(onSelect).toHaveBeenCalledWith('casual');

    fireEvent.click(screen.getByTestId('time-control-classic'));
    expect(onSelect).toHaveBeenCalledWith('classic');
  });

  it('disables all buttons when disabled prop is true', () => {
    const onSelect = vi.fn();
    render(
      <TimeControlSelector
        currentTimeControl="rapid"
        onSelectTimeControl={onSelect}
        disabled={true}
      />
    );

    const modes: TimeControl[] = ['bullet', 'blitz', 'rapid', 'classic', 'casual'];
    modes.forEach((mode) => {
      const btn = screen.getByTestId(`time-control-${mode}`);
      expect(btn).toBeDisabled();
    });
  });
});
