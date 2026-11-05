# TESTING.md — Verification, Testing & Benchmarking Strategy

This document outlines the testing strategy, correctness criteria, automated test suites, and benchmarking methodology for the **Chess AI — Player vs Computer** application.

---

## 1. Test Architecture & Directory Organization

Automated tests are housed under `tests/` and executed using `pytest`:

```
tests/
├── unit/                         # Fast, deterministic tests (< 5s)
│   ├── test_rules_integration.py # python-chess integration, perft, legal move checks
│   ├── test_game_service.py      # Session lifecycle, undo (2-ply), restart, draws
│   ├── test_session_manager.py   # Multi-session isolation and lifecycle
│   ├── test_material_eval.py     # Material point counting & sign convention
│   ├── test_minimax.py           # Minimax algorithm & hand-crafted trees
│   ├── test_alpha_beta.py        # Alpha-Beta pruning & cutoff correctness
│   ├── test_move_ordering.py     # Move prioritization, MVV-LVA, killers, history
│   ├── test_iterative_deepening.py # Progressive depth search & interruption
│   ├── test_search_limits.py     # Node/time limits, interruption unwinding
│   ├── test_engine_integration.py# Engine integration with GameService
│   ├── test_piece_square.py      # PST orientation, centralization, King MG/EG switching
│   ├── test_mobility.py          # Piece mobility counting, pin restrictions, and pawn attack avoidance
│   ├── test_pawn_structure.py    # Non-exclusive passed, isolated, doubled, connected pawns
│   ├── test_center_control.py    # Central square occupation and piece pressure
│   ├── test_king_safety.py       # Pawn shield, open files, king zone attacks, phase tapering
│   ├── test_coordination.py      # Bishop pair, rooks on open files/7th rank, defended pieces
│   ├── test_game_phase.py        # Non-pawn material phase calculation and monotonicity
│   ├── test_evaluator_integration.py # Breakdown summation, symmetry, search equivalence
│   ├── test_quiescence.py        # Quiescence search, check evasions, and tactical horizon stability
│   ├── test_transposition_table.py# TT bounds, replacement policy, and mate distance normalization
│   ├── test_zobrist.py           # 64-bit deterministic keys, make/unmake, castling, and en passant
│   ├── test_difficulty.py        # Five difficulty profiles, scaling, and resource limits
│   ├── test_time_manager.py      # Dynamic per-move time allocation and safety margins
│   └── test_tuning.py            # Genetic algorithm, bounded genes, fitness, selection, crossover, and mutation
├── integration/                  # API and GameService tests (< 15s)
│   ├── test_game_flow.py         # End-to-end multi-turn scenarios
│   └── test_api_endpoints.py     # FastAPI endpoints (/api/game/*, /api/engine/*)
└── benchmarks/                   # Performance and node-count benchmark suites
    ├── test_search_benchmarks.py # Node counts, NPS, speedup comparisons
    └── test_tactical_positions.py# WAC (Win At Chess) tactical test suite
```

---

## 2. Correctness & Acceptance Criteria

### 2.1 Rules Correctness (`test_rules_integration.py`)
- **Move Legality**: Moves generated match `python-chess.Board.legal_moves`.
- **Special Moves**: En passant, castling (kingside/queenside), and pawn promotions to all piece types ($Q, R, B, N$) execute properly.
- **Perft Validation**: Perft counts match standard reference values:
  - Initial Position: Depth 1 = 20, Depth 2 = 400, Depth 3 = 8,902, Depth 4 = 197,281.
  - Kiwipete (`r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -`): Depth 1 = 48, Depth 2 = 2,039, Depth 3 = 97,862.
- **Undo / Restart Integrity**: Undoing moves restores castling rights, en passant targets, halfmove clock, and full move history without state corruption.
- **Terminal States**: Correct detection and classification of checkmate, stalemate, insufficient material, threefold repetition, and fifty-move rule.

### 2.2 Search Correctness (`test_search.py`, `test_search_equivalence.py`)
- **Minimax Tree Tests**: Returns exact analytical values on known hand-crafted game trees.
- **Minimax == Alpha-Beta Equivalence**: At identical search depths and evaluation functions, Alpha-Beta pruning MUST return the exact same score and move as unpruned Minimax:
  $$\text{Score}(\text{Alpha-Beta}) \equiv \text{Score}(\text{Minimax})$$
  while searching strictly fewer nodes.
- **Perspective Correctness**: White maximizes the score ($+\infty$); Black minimizes the score ($-\infty$).
- **Board Preservation Invariant**: `board.push(move)` and `board.pop()` within `try...finally` must leave the root board completely unchanged after search execution, even if interrupted by exceptions.
- **Iterative Deepening**: Never returns an incomplete search iteration. If interrupted by a time limit, returns the move from the deepest *fully completed* iteration.
- **Quiescence Search**: Correctly continues capture and promotion lines; searches all legal check evasions when the king is in check; obeys maximum quiescence depth.
- **Transposition Table Bounds**: Stores and retrieves `EXACT`, `LOWERBOUND`, and `UPPERBOUND` values according to Alpha-Beta cutoff conditions without hash pollution.

### 2.3 Evaluation Correctness (`test_positional_eval.py`, `test_pawn_structure.py`)
- **Centipawn Scale & Sign**: Integer scores from White's perspective:
  - White advantage: $> 0$
  - Equal position: $0$
  - Black advantage: $< 0$
- **Color Symmetry**: For any mirrored board position (board inverted with colors swapped), the evaluation score must equal the negative of the original score:
  $$E(\text{pos}_{\text{mirrored}}) = -E(\text{pos})$$
- **Pawn Structure Feature Independence**: A pawn with multiple attributes (e.g., isolated and passed) receives both evaluations; structural detection does NOT short-circuit or discard valid attributes.
- **Terminal Overrides**: Terminal positions (checkmate, stalemate) bypass static heuristics and return exact terminal/ply scores.
- **Component Breakdown Summation**: Individual component scores (material, PST, mobility, king safety, pawns, center, coordination) sum to the reported total score.

### 2.4 API & Integration Acceptance (`test_api_endpoints.py`)
- Client can create a session (`POST /api/game/new`), play moves (`POST /api/game/move`), undo (`POST /api/game/undo`), and reset (`POST /api/game/restart`).
- Submitting an illegal move returns `400 Bad Request` with an explanatory error payload.
- Game over conditions are reported accurately in `GameStateResponse`.

### 2.5 Transposition Table & Zobrist Hashing Acceptance (`test_zobrist.py`, `test_transposition_table.py`)
- **Deterministic 64-bit Zobrist Hashing**: Seed `0x20261031_57A6E7` ensures deterministic cross-platform hash values; side to move, castling rights, and legal en passant files are differentiated; incremental update matches full bitboard recomputation on all move types.
- **Bound & Depth Verification**: Exact, Lower, and Upper bounds enforce mathematical alpha-beta cutoff rules; insufficient depth entries are rejected for cutoffs but preserved for move ordering.
- **Mate-Score Normalization**: Ply-dependent mate scores are converted to root-independent representations on store and denormalized accurately on probe across variable plies.
- **Asymmetric Fifty-Move Horizon Safety**: When halfmove clocks diverge, cutoff reuse is rejected if either stored or current search horizons could reach the 100-halfmove draw threshold (`entry.halfmove_clock != halfmove_clock` and `(halfmove_clock >= 90 or entry.halfmove_clock >= 90 or halfmove_clock + depth >= 100 or entry.halfmove_clock + entry.depth >= 100)`). Safe `best_move` ordering is preserved.
- **Path-Dependence & Repetition Safety**: Repetition-derived draw scores propagate path-dependence up the search tree; affected ancestors have score bounds suppressed from TT storage via `store_move_only`, ensuring clean cross-branch isolation while preserving move ordering.
- **Telemetry Semantics**: Verified identity: `nodes_searched == normal_nodes + quiescence_nodes`.
- **Subtree Reduction**: Repeated searches or higher-depth searches with populated TT achieve significant node reductions (up to 28% at depth 4, >99% on identical root depth replays).

### 2.6 Difficulty Levels & Time Management Acceptance (`test_difficulty.py`, `test_time_manager.py`)
- **Five Named Presets**: Verified existence and configuration of `Beginner`, `Easy`, `Medium`, `Hard`, and `Expert`.
- **Search Budget Monotonicity**: Search depth, node limits, base times, and max times scale monotonically from Beginner to Expert.
- **Dynamic Time Allocations**: Move time allocations strictly respect profile bounds `[min_time_ms, max_time_ms]` across all positions.
- **Single Legal Move Acceleration**: When exactly 1 legal move exists, search allocates minimal time (`min_time_ms`).
- **Tactical Check Urgency Boost**: Positions under active check receive a 1.30x time boost unsuppressed by branching penalties.
- **Phase & Branching Factors**: Peak middlegame allocations receive higher time budgets than simplified endgames; move counts scale appropriately.
- **Overhead Safety Margin**: Effective search limits deduct 50ms safety margin for Python and API serialization overhead.
- **Interruption Guarantees**: Interrupted searches always restore board state (100% pop restoration) and return safe legal moves from the deepest completed iteration.
- **API Difficulty Integration**: `POST /api/game/new`, `POST /api/game/difficulty`, and `POST /api/game/ai-move` operate with full schema validation and error reporting.

### 2.7 Offline Genetic Algorithm Acceptance (`test_tuning.py`)
- **12 Bounded Evaluation Genes**: Exactly 12 genes mapped 1-to-1 to `EvaluationConfig` parameters (5 piece values, 7 component multipliers) with hard mathematical clamping within authorized physical spans.
- **Multi-Objective Ground-Truth Fitness**: Composite scoring across positional alignment (60%), tactical move quality (35%), and mirrored board symmetry (5%) returning normalized scores in $[0.0, 100.0]$.
- **Strict Generalization Hold-out**: Training suite (24 positions) and validation suite (16 positions) strictly disjoint with zero shared FENs; validation suite is never accessed during evolution.
- **Deterministic Reproducibility**: Fixed random seeds produce byte-for-byte identical generations, gene values, and fitness telemetry.
- **Elitism Preservation**: Top-$K$ fittest candidates cloned directly into subsequent generations without mutation or score regression.
- **Genetic Operators**: Tournament ($k=3$) and rank selection, BLX-$\alpha$ continuous crossover ($\alpha=0.30$), and Gaussian perturbation mutation enforcing boundary invariants.
- **JSON Serialization & Roundtrip**: Versioned export/import (`export_tuned_config`, `load_tuned_config`) directly reconstructs valid `EvaluationConfig` instances usable by search and evaluation.
- **Zero Runtime Interference**: Default engine settings remain 100% handcrafted; tuning executes purely offline via `scripts/run_ga_tuning.py`.

---

## 3. Standard Benchmarking Plan (B1 to B9)

The project defines 9 repeatable benchmarks to measure search efficiency, evaluation quality, and algorithmic improvements:

| ID | Benchmark Name | Comparison | Target Metric |
| :--- | :--- | :--- | :--- |
| **B1** | Alpha-Beta Pruning Efficiency | Minimax vs Alpha-Beta | Score equivalence; node count reduction ($>70\%$ at depth 4). |
| **B2** | Search Depth Scaling | Depth 1 through 6 | Nodes searched, search time (ms), branching factor. |
| **B3** | Move Ordering Impact | With vs without move ordering | Node reduction with MVV-LVA and killer moves ($>40\%$). |
| **B4** | Quiescence Search Verification | With vs without quiescence | Tactical position accuracy; horizon effect mitigation. |
| **B5** | Transposition Table Impact | With vs without TT | TT hit rate ($>20\%$); repeated position node reduction. |
| **B6** | Material vs Positional Evaluation | Pure material vs full heuristic | Match win-rate over 50 games. |
| **B7** | Pawn Structure Refinement | Naive pawns vs contextual pawns | Strategic test positions; endgame match win-rate. |
| **B8** | Sacrifice Compensation | Base search vs compensation-aware | Accurate evaluation of sound piece sacrifices. |
| **B9** | Tuned vs Default Weights | Default weights vs GA-tuned weights | Win-rate over 100 validation games with swapped colors. |

---

## 4. Test Execution Instructions

### Run Fast Unit Tests:
```powershell
pytest tests/unit/ -v
```

### Run Integration Tests:
```powershell
pytest tests/integration/ -v
```

### Run Full Test Suite with Coverage:
```powershell
pytest --cov=engine --cov=backend tests/
```

### Run Search Benchmarks:
```powershell
pytest tests/benchmarks/ -v -s
```
