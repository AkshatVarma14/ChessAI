import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PlayerCard } from '../components/PlayerCard';

describe('PlayerCard Component', () => {
  it('renders player info, active turn highlight, and clock formatted as MM:SS', () => {
    render(
      <PlayerCard
        name="You"
        color="white"
        isAi={false}
        isCurrentTurn={true}
        capturedPieces={['p', 'p', 'n']}
        materialAdvantage={3}
        timeRemaining={582} // 09:42
        isTimed={true}
        isClockActive={true}
      />
    );

    expect(screen.getByText('You')).toBeInTheDocument();
    expect(screen.getByTestId('status-your-turn')).toHaveTextContent('To move');
    expect(screen.getByTestId('player-clock-white')).toHaveTextContent('09:42');
    expect(screen.getByText('+3')).toBeInTheDocument();
  });

  it('renders Casual label when match is untimed', () => {
    render(
      <PlayerCard
        name="Computer"
        color="black"
        isAi={true}
        difficultyName="medium"
        isCurrentTurn={false}
        capturedPieces={[]}
        timeRemaining={null}
        isTimed={false}
      />
    );

    expect(screen.getByText('Computer')).toBeInTheDocument();
    expect(screen.getByText('medium')).toBeInTheDocument();
    expect(screen.getByTestId('player-clock-black')).toHaveTextContent('Casual');
  });

  it('applies low time warning styling when time is <= 30 seconds', () => {
    render(
      <PlayerCard
        name="You"
        color="white"
        isAi={false}
        isCurrentTurn={true}
        capturedPieces={[]}
        timeRemaining={25}
        isTimed={true}
        isClockActive={true}
      />
    );

    const clock = screen.getByTestId('player-clock-white');
    expect(clock).toHaveTextContent('00:25');
    expect(clock.className).toContain('text-amber-200');
  });

  it('applies critical time styling when time is <= 10 seconds', () => {
    render(
      <PlayerCard
        name="You"
        color="white"
        isAi={false}
        isCurrentTurn={true}
        capturedPieces={[]}
        timeRemaining={7}
        isTimed={true}
        isClockActive={true}
      />
    );

    const clock = screen.getByTestId('player-clock-white');
    expect(clock).toHaveTextContent('00:07');
    expect(clock.className).toContain('text-red-200');
  });

  it('renders Timeout status badge when player times out', () => {
    render(
      <PlayerCard
        name="Computer"
        color="black"
        isAi={true}
        isCurrentTurn={true}
        capturedPieces={[]}
        timeRemaining={0}
        isTimed={true}
        isTimeout={true}
      />
    );

    expect(screen.getByTestId('status-timeout')).toHaveTextContent('Time Out');
    expect(screen.getByTestId('player-clock-black')).toHaveTextContent('00:00');
  });

  it('renders Check and Checkmate badges', () => {
    const { rerender } = render(
      <PlayerCard
        name="You"
        color="white"
        isAi={false}
        isCurrentTurn={true}
        capturedPieces={[]}
        isCheck={true}
        isTimed={false}
      />
    );

    expect(screen.getByTestId('status-check')).toHaveTextContent('Check');

    rerender(
      <PlayerCard
        name="You"
        color="white"
        isAi={false}
        isCurrentTurn={true}
        capturedPieces={[]}
        isCheckmate={true}
        isTimed={false}
      />
    );

    expect(screen.getByTestId('status-checkmate')).toHaveTextContent('Checkmate');
  });
});
