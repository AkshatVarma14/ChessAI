# REQUIREMENTS.md — System Requirements Specification

This document formalizes the functional, non-functional, and operational requirements for the **Chess AI — Player vs Computer** application, derived from the authoritative Master Specification.

---

## 1. Functional Requirements (FR)

### 1.1 Chess Rules & Game State Arbitration
- **FR-1.1 (Authoritative Engine)**: All game rules, legal move generation, board transformations, and terminal status checks must be executed authoritatively on the backend using `python-chess`.
- **FR-1.2 (Special Rules)**: Full support for castling (kingside and queenside), en passant captures, pawn promotions (queen, rook, bishop, knight), and legal check evasions.
- **FR-1.3 (Terminal Conditions)**: Automatic detection of checkmate, stalemate, insufficient material, threefold repetition, and the fifty-move rule.
- **FR-1.4 (State Restoration)**: Complete state restoration for undo and restart operations, preserving full move history, castling rights, and en passant availability.
- **FR-1.5 (Standard Notations)**: Board state interchange must use FEN (Forsyth–Edwards Notation); engine move transactions must use UCI (Universal Chess Interface, e.g., `e2e4`); user move history must display SAN (Standard Algebraic Notation, e.g., `Nf3`, `O-O`).

### 1.2 Custom Search Engine (`engine/search/`)
- **FR-2.1 (Minimax Search)**: Implement depth-limited adversarial Minimax search where White maximizes and Black minimizes score.
- **FR-2.2 (Alpha-Beta Pruning)**: Implement Alpha-Beta pruning ($\alpha \ge \beta$). Alpha-Beta must yield the exact same minimax value as unpruned Minimax at identical depths and deterministic evaluations.
- **FR-2.3 (Iterative Deepening)**: Progressively search depth 1, 2, 3, ... up to a depth or time limit. Only return the best move from the deepest *fully completed* iteration.
- **FR-2.4 (Move Ordering)**: Optimize search tree pruning by ordering moves:
  1. Transposition table best move.
  2. Winning and equal captures (ordered by MVV-LVA: Most Valuable Victim - Least Valuable Attacker).
  3. Pawn promotions.
  4. Killer moves (quiet moves that caused beta cutoffs at the same ply).
  5. History heuristic moves.
  6. Remaining quiet moves.
- **FR-2.5 (Quiescence Search)**: At nominal depth 0, extend search on captures and pawn promotions to prevent horizon effects. If the side to move is in check, search all legal evasions. Include a bounded depth cutoff to guarantee termination.
- **FR-2.6 (Terminal State Scoring)**: Checkmate scores must be ply-adjusted:
  $$\text{Mate Score} = 30000 - \text{ply}$$
  Draws score strictly $0 \text{ cp}$.

### 1.3 Static Heuristic Position Evaluation (`engine/evaluation/`)
- **FR-3.1 (Score Convention)**: All evaluation terms must be integer centipawns (cp, where 100 cp = 1 pawn) from White's perspective ($>0$ favors White, $<0$ favors Black).
- **FR-3.2 (Material Balance)**: Base piece valuations: Pawn = 100, Knight = 320, Bishop = 330, Rook = 500, Queen = 900 cp.
- **FR-3.3 (Piece-Square Tables)**: Square-dependent positional bonuses interpolated between middlegame and endgame tables.
- **FR-3.4 (Mobility)**: Calculate safe legal moves and attack ray mobility for non-king pieces.
- **FR-3.5 (King Safety)**: Evaluate pawn shield completeness, open/semi-open files facing the king, and enemy attacking piece pressure in the king zone.
- **FR-3.6 (Pawn Structure Multi-Feature Independence)**: Evaluate passed, protected, connected, doubled, isolated, backward, and blocked pawns independently without mutual exclusion ladder bugs.
- **FR-3.7 (Center Control)**: Score occupation and pawn influence over central squares ($d4, e4, d5, e5$).
- **FR-3.8 (Piece Coordination)**: Score defended pieces, connected rooks, bishop pairs, and penalize undefended/hanging pieces.
- **FR-3.9 (Game-Phase Tapered Blending)**: Calculate continuous game-phase ($\text{phase} \in [0, 1]$) from non-pawn material:
  $$\text{Score} = \text{phase} \times \text{Score}_{mg} + (1 - \text{phase}) \times \text{Score}_{eg}$$
- **FR-3.10 (Sacrifice Recognition)**: Sacrifices are recognized primarily through search depth, move ordering, and quiescence lines; positional compensation terms must be bounded and evidence-based.

### 1.4 Search Optimizations (`engine/search/`)
- **FR-4.1 (Transposition Table)**: Hash table storing 64-bit Zobrist position hashes, searched depth, score, node bound flag (`EXACT`, `LOWER`, `UPPER`), and best move.
- **FR-4.2 (Zobrist Hashing)**: Full 64-bit keys incorporating piece positions, side to move, castling rights, and legal en passant target files.

### 1.5 Difficulty Profiles
- **FR-5.1 (Difficulty Tiers)**:
  - **Easy**: Search depth 2–3, small time budget ($\le 500\text{ ms}$), simplified evaluation.
  - **Medium**: Search depth 4–5, moderate time budget ($\le 1500\text{ ms}$), standard positional evaluation.
  - **Hard**: Search depth 6+ with iterative deepening, full move ordering, quiescence search, and full evaluation.
- **FR-5.2 (No Artificial Blunders)**: Weaker difficulty tiers must be achieved via search/evaluation resource limits, not by deliberately injecting random illegal moves or blunders.

### 1.6 Web Application & Presentation (`frontend/`)
- **FR-6.1 (Interactive Board)**: Responsive 8x8 chessboard supporting piece clicks / drag-and-drop, valid move indicators, check warning highlights, and last move indicator.
- **FR-6.2 (Promotion Dialog)**: Interactive choice modal when promoting a pawn (Queen, Rook, Bishop, Knight).
- **FR-6.3 (Game Controls)**: Controls to initiate New Game, Undo (2 plies), Restart, Select Side, and Select Difficulty.
- **FR-6.4 (Move History)**: Clean, scrollable list of played moves rendered in SAN.
- **FR-6.5 (Evaluation Bar)**: Dynamic vertical bar showing centipawn advantage for White or Black.
- **FR-6.6 (Analysis Panel)**: Real-time search telemetry: current depth, nodes searched, nodes per second, elapsed time, and component evaluation breakdown.

### 1.7 Offline Genetic Algorithm Tuning (`engine/tuning/`)
- **FR-7.1 (Offline Execution)**: Genetic Algorithm runs strictly offline via CLI scripts to optimize handcrafted evaluation weights.
- **FR-7.2 (Evolutionary Operators)**: Population initialization, fitness selection based on match outcomes, crossover, and Gaussian mutation.
- **FR-7.3 (Match Runner)**: Deterministic head-to-head match runner with color swapping across a balanced test suite of starting positions.
- **FR-7.4 (Validation Set)**: Tuned weights must be validated on an independent test suite not seen during tuning before being saved to versioned JSON.

---

## 2. Non-Functional Requirements (NFR)

- **NFR-1 (Responsiveness & Non-blocking Search)**: The web UI must remain completely responsive while the backend computes AI moves. The backend must complete move searches within configured time limits.
- **NFR-2 (Determinism & Reproducibility)**: At identical search depth, identical evaluation weights, and with disabled time limits, the engine must produce identical search scores and node counts.
- **NFR-3 (Independence & Portability)**: The `engine/` package must run independently of FastAPI and React. It must run on any standard OS (Windows, macOS, Linux) without binary compilation requirements.
- **NFR-4 (Zero External Cost)**: The application must operate 100% locally with zero external API calls or paid cloud dependencies.
- **NFR-5 (Code Quality & Type Safety)**: 100% type-annotated Python code (checked via MyPy or strict typing) and TypeScript strict mode enabled.
- **NFR-6 (Automated Test Coverage)**: Extensive unit, integration, and benchmark tests covering rules correctness, evaluation symmetry, search equivalence, and API endpoints.

---

## 3. Strict Exclusions & Non-Goals

1. **No Reinforcement Learning**: Prohibited from using policy/value gradients, actor-critic, or Q-learning.
2. **No Neural Networks**: Prohibited from using PyTorch, TensorFlow, CNNs, Transformers, or ONNX models.
3. **No Stockfish Move Selection**: Prohibited from using Stockfish or any external engine as the primary playing opponent.
4. **No python-chess Move Selection**: Prohibited from using `python-chess` for AI move choices.
5. **No Online Tuning**: Genetic Algorithm tuning must never execute during live user gameplay.
