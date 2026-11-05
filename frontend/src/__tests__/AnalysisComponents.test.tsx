import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { EvaluationBar } from '../components/EvaluationBar';
import { AnalysisPanel } from '../components/AnalysisPanel';
import { MoveHistory } from '../components/MoveHistory';
import { AnalysisResponse } from '../types/chess';

describe('EvaluationBar Component', () => {
  it('renders neutral evaluation when score is 0', () => {
    render(<EvaluationBar scoreCp={0} />);
    expect(screen.getByRole('meter')).toBeInTheDocument();
    // 0 cp renders as 0.0
    expect(screen.getAllByText('0.0').length).toBeGreaterThan(0);
  });

  it('renders positive score for White advantage', () => {
    render(<EvaluationBar scoreCp={175} />);
    expect(screen.getByText('+1.8')).toBeInTheDocument();
  });

  it('renders negative score for Black advantage', () => {
    render(<EvaluationBar scoreCp={-240} />);
    expect(screen.getByText('-2.4')).toBeInTheDocument();
  });

  it('renders checkmate score accurately for both sides', () => {
    const { rerender } = render(<EvaluationBar scoreCp={29998} isMate={true} mateInPlies={2} />);
    expect(screen.getByText('M1')).toBeInTheDocument();

    rerender(<EvaluationBar scoreCp={-29996} isMate={true} mateInPlies={4} />);
    expect(screen.getByText('-M2')).toBeInTheDocument();
  });

  it('renders correctly when board is flipped (black orientation)', () => {
    render(<EvaluationBar scoreCp={250} orientation="black" />);
    expect(screen.getByText('+2.5')).toBeInTheDocument();
  });

  it('renders neutral dash when score is null', () => {
    render(<EvaluationBar scoreCp={null} />);
    expect(screen.getByText('-')).toBeInTheDocument();
  });
});

describe('AnalysisPanel Component', () => {
  const mockAnalysis: AnalysisResponse = {
    score_cp: 145,
    is_mate: false,
    mate_in_plies: null,
    depth: 4,
    nodes_searched: 1250,
    quiescence_nodes: 340,
    elapsed_ms: 120.5,
    nodes_per_second: 10373,
    best_move_uci: 'e2e4',
    best_move_san: 'e4',
    pv_uci: ['e2e4', 'e7e5', 'g1f3'],
    pv_san: ['e4', 'e5', 'Nf3'],
    tt_hits: 45,
    tt_probes: 120,
    tt_cutoffs: 32,
    tt_stores: 88,
  };

  it('renders empty placeholder when analysis is null', () => {
    render(
      <AnalysisPanel
        analysis={null}
        isAnalyzing={false}
        onAnalyze={vi.fn()}
        autoAnalyze={false}
        onToggleAutoAnalyze={vi.fn()}
      />
    );
    expect(screen.getByText('No Analysis Available')).toBeInTheDocument();
  });

  it('renders analysis metrics and PV line when provided', () => {
    render(
      <AnalysisPanel
        analysis={mockAnalysis}
        isAnalyzing={false}
        onAnalyze={vi.fn()}
        autoAnalyze={false}
        onToggleAutoAnalyze={vi.fn()}
      />
    );

    // Score display
    expect(screen.getByText('+1.45 (+145 cp)')).toBeInTheDocument();
    // Best move and PV line
    expect(screen.getAllByText('e4').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('e5')).toBeInTheDocument();
    expect(screen.getByText('Nf3')).toBeInTheDocument();
    // Telemetry
    expect(screen.getAllByText('4 plies').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('1,250')).toBeInTheDocument();
  });

  it('renders checkmate score in AnalysisPanel for Black advantage', () => {
    const mateAnalysis: AnalysisResponse = {
      ...mockAnalysis,
      score_cp: -29998,
      is_mate: true,
      mate_in_plies: 2,
    };
    render(
      <AnalysisPanel
        analysis={mateAnalysis}
        isAnalyzing={false}
        onAnalyze={vi.fn()}
        autoAnalyze={false}
        onToggleAutoAnalyze={vi.fn()}
      />
    );
    expect(screen.getByText('#-M1')).toBeInTheDocument();
  });

  it('triggers onAnalyze callback on button click', () => {
    const onAnalyze = vi.fn();
    render(
      <AnalysisPanel
        analysis={null}
        isAnalyzing={false}
        onAnalyze={onAnalyze}
        autoAnalyze={false}
        onToggleAutoAnalyze={vi.fn()}
      />
    );

    const button = screen.getByRole('button', { name: /analyze/i });
    fireEvent.click(button);
    expect(onAnalyze).toHaveBeenCalledWith(3);
  });

  it('toggles auto-analyze correctly', () => {
    const onToggle = vi.fn();
    render(
      <AnalysisPanel
        analysis={null}
        isAnalyzing={false}
        onAnalyze={vi.fn()}
        autoAnalyze={false}
        onToggleAutoAnalyze={onToggle}
      />
    );

    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(onToggle).toHaveBeenCalledWith(true);
  });
});

describe('MoveHistory Component Navigation & PGN', () => {
  const sampleMoves = ['e4', 'e5', 'Nf3', 'Nc6'];

  it('renders navigation buttons and triggers onSelectPly', () => {
    const onSelectPly = vi.fn();
    render(
      <MoveHistory
        sanHistory={sampleMoves}
        selectedPly={4}
        onSelectPly={onSelectPly}
      />
    );

    // Test |< Start button
    const firstBtn = screen.getByLabelText('First move');
    fireEvent.click(firstBtn);
    expect(onSelectPly).toHaveBeenCalledWith(0);

    // Test < Prev button (4 - 1 = 3)
    const prevBtn = screen.getByLabelText('Previous move');
    fireEvent.click(prevBtn);
    expect(onSelectPly).toHaveBeenCalledWith(3);
  });

  it('triggers onCopyPGN and onDownloadPGN', async () => {
    const onCopy = vi.fn();
    const onDownload = vi.fn();
    render(
      <MoveHistory
        sanHistory={sampleMoves}
        onCopyPGN={onCopy}
        onDownloadPGN={onDownload}
      />
    );

    const copyBtn = screen.getByTitle('Copy PGN to clipboard');
    await act(async () => {
      fireEvent.click(copyBtn);
    });
    expect(onCopy).toHaveBeenCalledTimes(1);

    const exportBtn = screen.getByTitle('Download PGN file');
    fireEvent.click(exportBtn);
    expect(onDownload).toHaveBeenCalledTimes(1);
  });

  it('allows clicking individual moves in the history table', () => {
    const onSelectPly = vi.fn();
    render(
      <MoveHistory
        sanHistory={sampleMoves}
        onSelectPly={onSelectPly}
      />
    );

    // Click 'Nf3' which is White's 2nd move -> ply 3
    const nf3Btn = screen.getByRole('button', { name: 'Nf3' });
    fireEvent.click(nf3Btn);
    expect(onSelectPly).toHaveBeenCalledWith(3);
  });

  it('handles incomplete move pairs without rendering empty black buttons', () => {
    const onSelectPly = vi.fn();
    const { rerender } = render(
      <MoveHistory
        sanHistory={['e4']}
        selectedPly={1}
        onSelectPly={onSelectPly}
      />
    );

    // Only 1 ply button should exist in document
    const moveButtons = screen.getAllByRole('button').filter(b => b.hasAttribute('data-ply'));
    expect(moveButtons).toHaveLength(1);
    expect(moveButtons[0]).toHaveTextContent('e4');
    expect(screen.getByText('1.')).toBeInTheDocument();

    // Rerender with 3 plies (incomplete 2nd pair)
    rerender(
      <MoveHistory
        sanHistory={['e4', 'e5', 'd4']}
        selectedPly={3}
        onSelectPly={onSelectPly}
      />
    );

    const updatedMoveButtons = screen.getAllByRole('button').filter(b => b.hasAttribute('data-ply'));
    expect(updatedMoveButtons).toHaveLength(3);
    expect(screen.getByText('1.')).toBeInTheDocument();
    expect(screen.getByText('2.')).toBeInTheDocument();
    expect(screen.queryByText('3.')).not.toBeInTheDocument();
  });

  it('highlights the selected move ply with distinct active styling', () => {
    render(
      <MoveHistory
        sanHistory={['e4', 'e5', 'Nf3', 'Nc6']}
        selectedPly={2}
      />
    );

    const e5Button = screen.getByRole('button', { name: 'e5' });
    expect(e5Button).toHaveAttribute('data-ply', '2');
    expect(e5Button.className).toContain('text-emerald-300');
    expect(e5Button.className).toContain('border-emerald-600');

    const e4Button = screen.getByRole('button', { name: 'e4' });
    expect(e4Button.className).not.toContain('border-emerald-600');
  });
});
