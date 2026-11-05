import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { PromotionDialog } from '../components/PromotionDialog';

describe('PromotionDialog Component', () => {
  it('renders promotion choices when open', () => {
    render(
      <PromotionDialog
        isOpen={true}
        color="white"
        onSelect={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(screen.getByText('Pawn Promotion')).toBeInTheDocument();
    expect(screen.getByText('Queen')).toBeInTheDocument();
    expect(screen.getByText('Rook')).toBeInTheDocument();
    expect(screen.getByText('Bishop')).toBeInTheDocument();
    expect(screen.getByText('Knight')).toBeInTheDocument();
  });

  it('does not render when isOpen is false', () => {
    const { container } = render(
      <PromotionDialog
        isOpen={false}
        color="white"
        onSelect={vi.fn()}
        onCancel={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it('calls onSelect with piece symbol when piece is clicked', () => {
    const handleSelect = vi.fn();
    render(
      <PromotionDialog
        isOpen={true}
        color="white"
        onSelect={handleSelect}
        onCancel={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText('Queen'));
    expect(handleSelect).toHaveBeenCalledWith('q');
  });

  it('calls onCancel when cancel button is clicked', () => {
    const handleCancel = vi.fn();
    render(
      <PromotionDialog
        isOpen={true}
        color="white"
        onSelect={vi.fn()}
        onCancel={handleCancel}
      />
    );

    fireEvent.click(screen.getByText('Cancel move'));
    expect(handleCancel).toHaveBeenCalledTimes(1);
  });
});
