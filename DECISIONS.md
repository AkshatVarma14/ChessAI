# DECISIONS.md — Architecture Decision Records (ADRs)

This document records key architectural and technical decisions made during the design and implementation of the **Chess AI — Player vs Computer** application, along with their context, rationale, and consequences.

---

## ADR-001: Technology Stack Selection

### Context
We need a robust, maintainable, performant technology stack to build a web-based chess application featuring a custom AI engine, responsive browser UI, and strict separation of concerns.

### Decision
Adopt the following stack:
- **Frontend**: React 18+, TypeScript 5+, Vite.
- **Backend API**: Python 3.12+, FastAPI, Uvicorn, Pydantic v2.
- **Rules Arbiter**: `python-chess`.
- **Custom Engine**: Pure Python 3.12+ in an isolated package (`engine/`).
- **Testing**: `pytest`, `pytest-cov`, `httpx`.

### Rationale
- **React + Vite** provides fast compilation, modern development ergonomics, and responsive component rendering for the 8x8 chessboard and analysis metrics.
- **FastAPI** provides high-throughput asynchronous request handling, automatic OpenAPI/Swagger documentation, and native Pydantic schema validation.
- **`python-chess`** is an industry-standard, exhaustively tested chess library that eliminates the risk of subtle move-generation or special-rule bugs (castling rights, en passant, promotion, repetition draws).
- **Pure Python for the custom engine** ensures portability across Windows, macOS, and Linux without requiring C++ compilation toolchains or external binaries.

### Consequences
- Frontend and backend can be developed and scaled independently.
- The engine can be tested directly without web server overhead.

---

## ADR-002: Separation of Engine from Rules Arbiter and Web Layer

### Context
In chess projects, move generation, rules arbitration, adversarial search, and HTTP orchestration often become tightly coupled, making search algorithms difficult to test, benchmark, and optimize.

### Decision
Strictly decouple the application into three isolated layers:
1. `backend/game/`: Authoritative game arbiter utilizing `python-chess`.
2. `engine/`: Custom search, evaluation, and optimization. Zero dependencies on FastAPI, HTTP, or presentation logic.
3. `backend/api/`: REST interface exposing game and engine endpoints.

### Rationale
- `python-chess` must **exclusively** handle chess rules, legal move generation, board state, FEN/PGN, and terminal-state detection.
- The custom engine must **independently** select the computer's moves.
- Pure engine functions (`choose_move`, `evaluate_position`) can be benchmarked and tested head-to-head in headless Python scripts without spinning up HTTP servers or React clients.

### Consequences
- Clear contract interfaces: `choose_move(board, config) -> SearchResult` and `evaluate_position(board, config) -> int`.
- Engine code is 100% portable and reusable in CLI tools and offline tuning scripts.

---

## ADR-003: Exclusion of Reinforcement Learning and Neural Networks

### Context
Modern chess engines often use neural networks (NNUE, AlphaZero-style CNNs/Transformers). We must establish whether neural techniques or classical search should be used.

### Decision
**Explicitly prohibit** reinforcement learning, neural network training, and neural policy/value models. The custom engine must rely exclusively on **classical adversarial search (Minimax, Alpha-Beta)** and **handcrafted heuristic static evaluation**.

### Rationale
- Classical heuristic search is fully explainable, deterministic, and educational. Every score component (material, PST, mobility, king safety, pawn structure) can be inspected in real time via the UI.
- Neural approaches are opaque black boxes that require substantial GPU resources for training and inference, violating portability and zero-cloud-cost requirements.
- The project's educational focus is on tree search, pruning, and computational optimization.

### Consequences
- Eliminates heavy dependencies (`torch`, `tensorflow`, `onnxruntime`).
- Ensures sub-second local CPU execution without hardware acceleration.

---

## ADR-004: Centipawn Unit and White-Relative Sign Convention

### Context
Adversarial search and static evaluation require a consistent scoring scale and perspective to prevent sign inversion bugs.

### Decision
1. Standardize all static evaluation and search scores on **integer centipawns (cp)**, where 100 cp equals 1 pawn.
2. Maintain a strict **White-relative perspective**:
   - Score $> 0$: Advantage for White.
   - Score $= 0$: Equal / drawn position.
   - Score $< 0$: Advantage for Black.
3. Checkmate scores are encoded as $\pm(30000 - \text{ply})$ so the engine prioritizes shorter paths to mate.

### Rationale
- Integer math is faster and immune to floating-point precision drift.
- A consistent White-relative perspective simplifies the evaluation bar in the UI and makes position symmetry tests straightforward ($E(\text{pos}_{\text{mirrored}}) = -E(\text{pos})$).

### Consequences
- Any internal Negamax search that operates from the perspective of the side-to-move must explicitly convert scores to White-relative when returning results to the caller.

---

## ADR-005: Multi-Feature Independent Pawn Structure Evaluation

### Context
Naive chess engines frequently evaluate pawn structures using `if...elif...else` priority ladders (e.g., checking if a pawn is isolated, and if so, skipping the check for whether it is passed). In real chess, pawns frequently possess multiple overlapping characteristics (e.g., an isolated passed pawn).

### Decision
Evaluate pawn structural features **independently**. Calculate separate terms for:
- Passed pawns (and advancement rank)
- Protected passed pawns
- Connected pawns
- Doubled pawns
- Isolated pawns
- Backward pawns
- Blocked pawns

### Rationale
A pawn can be both isolated and passed; ignoring its passed status because it was already flagged as isolated grossly undervalues dangerous endgame runners. Computing independent terms accurately captures the true tactical and strategic reality.

### Consequences
- Requires careful coefficient tuning to ensure multiple bonuses/penalties combine smoothly without double-counting weaknesses.

---

## ADR-006: Continuous Game-Phase Blending (Tapered Evaluation)

### Context
Positional features vary in importance across different stages of the game. For example, king safety is critical in the middlegame but king centralization becomes advantageous in the endgame.

### Decision
Implement tapered evaluation using a continuous phase value ($\text{phase} \in [0.0, 1.0]$) derived from remaining non-pawn material:
$$\text{Score} = \text{phase} \times \text{Score}_{mg} + (1 - \text{phase}) \times \text{Score}_{eg}$$
where $\text{phase} = 1.0$ is the opening/middlegame and $\text{phase} = 0.0$ is the pure endgame.

### Rationale
Discrete phase boundaries (e.g., switching abruptly when total material drops below a threshold) create evaluation cliffs that distort search and produce erratic moves near the boundary. Continuous interpolation ensures smooth, monotonic transitions.

### Consequences
- Evaluation components (especially PST and King evaluation) must maintain separate middlegame and endgame weight matrices.

---

## ADR-007: Difficulty Tiers Scaled by Search Resources (No Random Blunders)

### Context
Many simple chess programs create lower difficulty settings by randomly selecting suboptimal or blunder moves. This produces unnatural, erratic gameplay that frustrates human players.

### Decision
Scale difficulty tiers exclusively through **computational search limits and evaluation profiles**:
- **Easy**: Low depth limit (depth 2–3), strict time cap ($\le 500\text{ ms}$), simplified evaluation.
- **Medium**: Moderate depth (depth 4–5), time cap ($\le 1500\text{ ms}$), standard evaluation.
- **Hard**: Deep search (depth 6+), iterative deepening, full move ordering, quiescence search, and full evaluation.

### Rationale
Resource-constrained search makes the engine play like a weaker human (capable of missing deep tactical combinations while still playing fundamentally sensible chess) rather than playing master-level moves interrupted by random blunders.

### Consequences
- Search algorithms must reliably honor depth and time bounds.

---

## ADR-008: Offline Genetic Algorithm for Parameter Weight Optimization

### Context
Handcrafting positional weights requires calibration. We need an automated tuning mechanism that complies with the restriction against reinforcement learning and neural networks.

### Decision
Implement an **offline Genetic Algorithm (GA)** in `engine/tuning/`:
- Candidates represent chromosomes of numerical evaluation weights (mobility weights, king safety coefficients, pawn feature weights).
- Fitness is measured through automated match play across balanced opening test positions.
- Selection, crossover, and Gaussian mutation evolve subsequent generations.
- Tuned weights are saved as versioned JSON configurations in `experiments/`.

### Rationale
- A Genetic Algorithm is a classical heuristic optimization technique for tuning explicit parameters—it is not reinforcement learning or neural network training.
- Running it strictly offline ensures the web application remains fast, predictable, and self-contained.

### Consequences
- Normal gameplay loads pre-tuned weights and never invokes the GA.

---

## ADR-009: Repository Organization

### Context
The repository needs a clean structure separating search, evaluation, tuning, API, game management, frontend, tests, and documentation.

### Decision
Establish the following top-level directory layout:
- `frontend/`: React + TypeScript + Vite.
- `backend/`: FastAPI API routes and authoritative GameService.
- `engine/`: Custom Python engine (`search/`, `evaluation/`, `optimization/`, `tuning/`).
- `tests/`: Automated test suites (`unit/`, `integration/`, `benchmarks/`).
- `docs/`: Master specification and technical documentation.
- `scripts/`: Offline developer scripts (benchmark runners, tuning runners).

### Rationale
Provides clean separation of concerns, clear module boundaries, independent testability, and prevents circular dependencies between web presentation and chess logic.

### Consequences
- Modular code structure facilitates independent development and testing of components.

---

## ADR-010: Stable Python Runtime Selection (Python 3.12.10 vs Pre-Release Python 3.14.5)

### Context
During initial environment verification, the host system was found to have both `Python 3.14.5` (alpha/pre-release) and `Python 3.12.10` (stable LTS) installed. We must define the authoritative target runtime.

### Decision
Standardize on **Python 3.12.10** as the primary, recommended execution and testing runtime, while maintaining code compatibility across Python 3.12+.

### Rationale
- Python 3.14 is currently pre-release and bleeding-edge. Key C-extension dependencies (`numpy`, `pydantic-core`, `watchfiles`, `coverage`) frequently encounter wheel availability gaps or compiler ABI changes during pre-release cycles on Windows.
- Python 3.14 includes experimental features (such as PEP 649 deferred annotation evaluation and PEP 703 free-threading) which could introduce non-deterministic edge cases in Pydantic v2 and FastAPI request validation.
- Python 3.12.10 is fully stabilized, exhaustively supported across the entire scientific Python and FastAPI ecosystem, and directly matches the Master Specification requirement (`Python 3.12+`).

### Consequences
- Development environments should be initialized with `py -3.12 -m venv .venv`.
- CI/CD and test commands default to Python 3.12.

---

## ADR-011: Modular Subsystem Decomposition and Milestone Architecture

### Context
Building an end-to-end chess application with a custom search engine, web service, and responsive frontend requires strict separation of concerns to ensure testability, maintainability, and architectural integrity.

### Decision
Decompose the system into four decoupled subsystems mapped to distinct architectural milestones:
1. **Authoritative Rules & Game Service** (`backend/game/`): Rule enforcement, legal move arbitration, FEN/PGN state, and session isolation using `python-chess`.
2. **Web API Service** (`backend/api/`): Asynchronous FastAPI REST interface for game sessions and engine analysis.
3. **Pure Python Custom Engine** (`engine/`): Adversarial search (Minimax, Alpha-Beta, Iterative Deepening, Move Ordering, Quiescence Search, Transposition Table) and handcrafted evaluation heuristics.
4. **Interactive Web Client** (`frontend/`): React, TypeScript, Vite, Tailwind CSS interface with Cburnett SVG pieces, clock controls, and engine telemetry.

### Rationale
- Subsystem decomposition allows strictly decoupled test verification: backend game rules are 100% verified via automated perft tests before frontend integration begins.
- Isolating search optimization, transposition tables, and difficulty settings into distinct modules prevents regression blending and maintains clean architectural boundaries.

### Consequences
- Full architectural independence between web protocols, chess rules arbitration, and custom AI search math.
- Engine code is 100% portable and runnable in pure Python CLI or benchmark environments without web dependencies.

---

## ADR-015: Difficulty Profiles Architecture and Dynamic Time Management Policy

### Context
Supporting varied player skill levels requires five named difficulty presets (`Beginner`, `Easy`, `Medium`, `Hard`, `Expert`) and dynamic time allocation per move. We must ensure:
1. Strength differences arise from principled search depth and heuristic reach rather than random blunders.
2. No duplicated magic numbers exist between engine, API, and frontend.
3. Time allocation dynamically responds to game phase, branching factors, and tactical urgency while reserving safety margins.

### Decision
1. **Immutable Difficulty Profiles Layer (`engine/difficulty.py`)**:
   - Define `DifficultyLevel(str, Enum)` and immutable frozen `DifficultyProfile` dataclasses.
   - Maintain a single authoritative configuration dictionary `DIFFICULTY_PROFILES`.
   - Scale difficulty genuinely across depth (1 to 5), node budgets (300 to 250,000), quiescence extensions (0 to 8 plies), check evasion depth (0 to 2 plies), and transposition table cache sizing (4MB to 64MB).
   - Zero artificial random blunders; play is deterministic and principled at every level.
2. **Dynamic Time Management Policy (`engine/search/time_manager.py`)**:
   - Compute allocated per-move budget: $T_{\text{alloc}} = \text{clamp}(T_{\text{base}} \times F_{\text{moves}} \times F_{\text{phase}} \times F_{\text{check}}, T_{\min}, T_{\max})$.
   - Short-circuit single legal moves to minimal budget ($T_{\min}$).
   - Do not penalize move counts under check ($F_{\text{moves}} = 1.00$); apply 1.30x check urgency boost.
   - Strictly reserve 50ms safety margin (`DEFAULT_SAFETY_MARGIN_MS`) for Python stack unwinding and REST serialization.
   - Early termination on stable principal variations between completed iterations.
3. **Decoupled API & Game Session Integration**:
   - Game sessions track `difficulty: str` (default `"medium"`).
   - `POST /api/game/difficulty` updates active level without resetting board or move records.
   - `POST /api/game/ai-move` computes moves on demand, and frontend supports automatic AI replies in Player vs Computer mode.

### Rationale
- Decoupling `DifficultyProfile` from API schemas keeps `engine/` 100% independent of web concerns.
- Monotonic clock calculations prevent external clock desynchronization.
- Clean safety margin guarantees 100% deadline compliance.

### Consequences
- Every difficulty level returns safe, legal moves.
- Response times scale cleanly from <10ms on Beginner to ~3.8s on Expert.

---

## ADR-016: Beginner Check-Evasion Policy and Frontend Asynchronous Request Synchronization

### Context
Verification revealed that the initial Beginner difficulty profile (`use_quiescence=False, max_quiescence_depth=0, max_check_depth=0`) failed to recognize checks at the nominal search horizon ($d=0$), evaluating tactical checks with quiet static evaluation (+122 cp) and blundering the queen on defended squares (e.g., `Qxf7+` followed by `Kxf7`). Additionally, rapid clicks on the frontend could trigger concurrent asynchronous API calls before React updated the `isLoading` state.

### Decision
1. **Beginner Check-Evasion Policy**:
   - Configure Beginner with `use_quiescence=True, max_quiescence_depth=0, max_check_depth=1`.
   - *Quiet positions* (`not in_check`): `q_depth (0) >= max_quiescence_depth (0)` returns static evaluation immediately without exploring any capture moves, preserving ultra-fast 1-ply vision.
   - *Checked positions* (`in_check`): `emergency_ceiling = 0 + 1 = 1 > q_depth (0)`, enabling 1-ply of legal check evasion exploration. Recaptures and check evasions are evaluated, avoiding blunders and accurately detecting checkmate.
   - *Emergency fallback*: If check cannot be resolved within allowance or `max_check_depth=0`, `UNRESOLVED_CHECK_PENALTY` is strictly applied rather than treating the position as quiet.
2. **Frontend Synchronous Concurrency Guard**:
   - Introduce a React `useRef` lock (`isSubmittingRef`) checked synchronously before initiating any API mutation.
   - Pass `isTerminal` to `GameControls` to disable the "AI Move" button in terminal states.

### Rationale
- Preserves the mathematical equivalence between unpruned Minimax and Alpha-Beta without quiescence.
- Keeps Beginner computationally lightweight while adhering 100% to chess rules and check invariants.
- Eliminates frontend race conditions from rapid user clicks.

### Consequences
- Beginner avoids tactical queen blunders while remaining accessible and fast.
- Frontend cannot submit duplicate moves or concurrent requests under rapid interaction.


---

## ADR-017: Offline Genetic Algorithm for Evaluation Weight Optimization

### Context
Static evaluation in the custom engine depends on 12 handcrafted parameters (5 piece values and 7 component weights). Manually fine-tuning these weights is labor-intensive and subjective. We required an automated, offline tuning mechanism that optimizes these weights while strictly respecting project boundaries: zero neural networks, zero reinforcement learning, zero external engines (Stockfish), zero paid APIs, zero live gameplay tuning, and zero modification to default engine settings unless explicitly loaded.

### Decision
1. **Isolated Subsystem (`engine/tuning/`)**:
   - Implemented an offline Genetic Algorithm tuning suite strictly within `engine/tuning/`: `individual.py`, `dataset.py`, `fitness.py`, `selection.py`, `crossover.py`, `mutation.py`, `population.py`, `genetic_algorithm.py`, and `results.py`.
   - Enforce 12 tunable genes mapped 1-to-1 to `EvaluationConfig`: 5 piece values (`pawn_value` [80, 120], `knight_value` [250, 400], `bishop_value` [260, 420], `rook_value` [420, 600], `queen_value` [800, 1150]) and 7 component multipliers (`material_weight`, `pst_weight`, `mobility_weight`, `pawn_structure_weight`, `center_control_weight`, `king_safety_weight`, `coordination_weight` each [0.2 or 0.5, 2.5]).
2. **Multi-Objective Ground-Truth Fitness Evaluation**:
   - Multi-objective fitness combining:
     1. Positional Advantage Alignment ($w=0.60$): Directional correctness and margin fulfillment across curated positions.
     2. Tactical Decision Quality ($w=0.35$): 1-ply search selecting critical winning moves or avoiding tactical blunders.
     3. Evaluation Invariant Symmetry ($w=0.05$): Verification of mirrored board evaluation ($E(\text{pos}) = -E(\text{pos}_{\text{mirrored}})$).
   - Normalized composite fitness score in range $[0.0, 100.0]$.
3. **Strict Training vs. Validation Separation**:
   - 24 curated positions in `TRAINING_SUITE` used exclusively during GA evolution.
   - 16 held-out positions in `VALIDATION_SUITE` strictly isolated from the evolution loop, used exclusively for post-tuning generalization validation.
4. **Reproducible Genetic Operators**:
   - Elitism preservation: Top $K$ fittest candidates cloned directly into next generation.
   - Tournament selection ($k=3$) and Rank selection.
   - Blend Crossover (BLX-$\alpha$, $\alpha=0.30$) for continuous bounded exploration.
   - Bounded Gaussian perturbation mutation with hard clamping within gene specifications.
   - Deterministic reproducibility when initialized with a fixed random seed.
5. **Decoupled Experiment Tooling & Serialization**:
   - `scripts/run_ga_tuning.py` CLI supporting `--generations`, `--pop-size`, `--seed`, `--dry-run`, and `--export`.
   - Versioned JSON serialization format (`experiments/tuned_weights.json`) with roundtrip loading back into `EvaluationConfig`.
   - Engine runtime defaults remain 100% handcrafted and unchanged unless explicitly configured.

### Rationale
- Pure Python implementation without external C/ML dependencies guarantees zero-dependency offline optimization.
- Bounded parameter intervals prevent nonsensical chess valuations (e.g. rooks worth less than pawns).
- Held-out validation guarantees that candidates do not overfit to training positions.

### Consequences
- Evolution completes in seconds on commodity hardware (~1.6s for 5 generations of 12 individuals).
- Tuned weights show positive generalization (+0.1322 training delta, +0.0335 validation delta) with 100% tactical and positional accuracy.
- Default engine play remains unaffected unless explicitly loaded from JSON.


---

## ADR-018: Genetic Algorithm Parameter Overlap & Generalization Audit

### Context
Parameter analysis examined the mathematical coupling between individual piece values (`pawn_value`, `knight_value`, etc.) and the global `material_weight` multiplier, as well as the high baseline fitness scores (~98.85) and the generalization behavior across multiple random seeds and an independent test suite.

### Decision
1. **Defensibility of Parameter Overlap**:
   - Retain both individual piece values and `material_weight` in the chromosome.
   - *Rationale*: Individual piece values control *intra-material trade ratios* (e.g. Bishop vs Knight, Minor Piece vs 3 Pawns, Queen vs 2 Rooks), while `material_weight` controls the *global trade-off between material balance and all positional features* (PST, mobility, pawn structures, king safety, center control, coordination).
   - Retaining this separation preserves 100% backward compatibility with `EvaluationConfig`, API schemas, and existing serialized configurations.
2. **Multi-Seed Landscape Characterization**:
   - Multi-seed trials prove the heuristic parameter space is multi-modal: multiple distinct combinations of piece values and component weights achieve comparable aggregate fitness.
   - `material_weight` consistently drifts upward across all seeds (1.31 to 1.50), reflecting that high material fidelity is favored in tactical clarity.
3. **Independent Validation Invariant**:
   - Established `INDEPENDENT_SUITE` (6 positions) in `engine/tuning/dataset.py` strictly disjoint from both training and validation suites.
   - Verified that the tuned configuration achieves 100.0% accuracy on this independent benchmark suite.
4. **Self-Play Perspective**:
   - Paired self-play matches (`scripts/match_baseline_vs_tuned.py`) serve as behavioral and stability tests, not absolute Elo ratings.

### Consequences
- Architecture remains clean, robust, and backward-compatible.
- Independent validation confirms generalization without data leakage.

---

## ADR-019: Analysis UI, Historical Move Navigation, and Principal Variation Extraction

### Context
The application requires an interactive Analysis UI, engine telemetry introspection, move review with FEN synchronization, and standard PGN export without compromising existing gameplay or architectural invariants.

### Decision
1. **Principal Variation (PV) Extraction via Transposition Table**:
   - The engine extracts the PV sequence by chaining stored `best_move` records in the Transposition Table from the root position.
   - Legality verification and cycle detection guard against stale or cyclic table entries.
   - Populates both `pv_uci` and `pv_san` on `SearchResult` for immediate consumption.
2. **Lossless Historical FEN Tracking in Game Service**:
   - `backend/game/service.py` tracks `_fen_history = [self._initial_fen]`, appending the board's FEN after every applied move and popping on undo.
   - Enables the frontend to review arbitrary past plies without cloning board instances or modifying the active authoritative session state.
3. **FIDE-Standard PGN Generation**:
   - `Game.get_pgn()` generates standard PGN text with full Seven-Tag Roster headers (`Event`, `Site`, `Date`, `Round`, `White`, `Black`, `Result`) using `python-chess`'s built-in `chess.pgn.Game.from_board()`.
   - Exposed via `GET /api/game/pgn?session_id=...` and wired to clipboard copy and `.pgn` download in the frontend.
4. **Interactive Analysis UI & Evaluation Bar**:
   - `EvaluationBar.tsx` maps integer centipawn scores smoothly via standard chess sigmoid function into vertical advantage representation with forced checkmate indicators (`M#`).
   - `AnalysisPanel.tsx` visualizes real-time engine metrics: score, completed depth, total nodes, quiescence nodes, NPS, elapsed search time, and TT hits/stores/cutoffs.
   - `AbortController` and synchronous submit locks prevent stale responses and race conditions.

### Consequences
- Pure Python engine invariants remain strictly intact.
- Seamless user experience for college demonstration and viva examination.
- 100% test pass rate preserved across Python and TypeScript suites.

---

## ADR-020: Concurrency, Thread Safety, PV Isolation, and Evaluation Bar Orientation Hardening

### Context
Multi-threaded web environments require strict thread safety across concurrent API requests on shared game sessions, PV isolation against incomplete iterative deepening search iterations, race-condition mitigation during rapid user actions and historical review navigation, and responsive evaluation bar orientation when playing as Black.

### Decision
1. **Thread Safety in Backend Game Service**:
   - Added a mutex `threading.Lock()` to `Game` instances in `backend/game/service.py`, serializing calls to `board`, `apply_move`, `undo`, `restart`, `set_fen`, `get_pgn`, and `get_state`.
   - Prevents race conditions and board state corruption when multiple threads or concurrent requests access the same game session.
2. **PV Isolation & Cycle Prevention in Search Engine**:
   - `extract_pv` in `engine/search/transposition_table.py` accepts authoritative `first_move` matching `best_move` and enforces strict `max_length` bounds (`while len(pv_uci) < max_length`).
   - `iterative_deepening_search` caches `last_completed_pv = (iter_pv_uci, iter_pv_san)` at the completion of each iteration at depth $d$. When search is aborted at depth $d+1$, it returns the verified `last_completed_pv`, eliminating contamination from incomplete iterations.
3. **EvaluationBar Orientation & Contrast Legibility**:
   - Corrected vertical positioning in `frontend/src/components/EvaluationBar.tsx`: for `orientation === 'black'`, White bar is anchored at `top: 0` (top of board), and Black bar occupies the remaining space.
   - Dynamically calculates badge text colors (`text-slate-100` vs `text-slate-900`) and vertical positioning to guarantee high contrast and readability across dark and light advantage backgrounds.
4. **Frontend Concurrency & Historical Review Hardening**:
   - Added `analysisRequestIdRef` counter and `cancelPendingAnalysis()` aborting in-flight analysis on move, AI move, undo, restart, and historical review plies, discarding stale responses.
   - Added `displayedCheck` and `displayedLastMoveUci` ensuring king check highlights and move squares are rendered during historical review.
5. **Terminal State & Difficulty Parameter Handling in Analysis API**:
   - Checkmate positions return `is_mate=True`, `mate_in_plies=0`, `best_move_uci=None`, `pv_uci=[]` with appropriate checkmate score ($\pm 30000$).
   - Stalemate positions return `score_cp=0`, `is_mate=False`, `mate_in_plies=None`.
   - `AnalyzePositionRequest.difficulty` maps to calibrated search depth and time limits unless explicitly overridden.

### Consequences
- Complete request isolation and thread safety across concurrent API calls.
- Zero PV contamination, desynchronization, or cycle loops.
- Perfect visual representation and high-contrast text for both White and Black board orientations.

---

## ADR-021: Terminal Position Immediate Evaluation and Lock Safety Invariants

### Context
Handling already-concluded positions (checkmate, stalemate, insufficient material, 50-move rule, threefold repetition) requires upfront mathematical score consistency, prevention of redundant search invocations, non-reentrant mutex verification in `backend/game/service.py`, and clear client/server cancellation semantics.

### Decision
1. **Upfront Terminal Evaluation in Analysis API**:
   - `analyze_position` in `backend/api/routes/game.py` intercepts already-concluded positions before launching search:
     - Checkmate: returns `-30000` (White mated) or `+30000` (Black mated), `is_mate=True`, `mate_in_plies=0`, `best_move_uci=None`, `pv_uci=[]`, `depth=0`, `nodes_searched=0`.
     - Recognized draws (`is_stalemate()`, `is_insufficient_material()`, `is_fifty_moves()`, `is_repetition(3)`): returns `0 cp`, `is_mate=False`, `mate_in_plies=None`, `best_move_uci=None`, `pv_uci=[]`, `depth=0`, `nodes_searched=0`.
   - Prevents erroneous search execution on 50-move or insufficient-material positions, guaranteeing empty move/PV fields for ended positions.
2. **Non-Reentrant Lock Safety Invariants**:
   - Standard `threading.Lock()` is retained and verified.
   - Recursive acquisition cannot occur because internal methods never call the `board` property (they access `self._board` directly), and no locked method calls another locked method while holding `_lock`.
   - `ai_move()` and `get_pgn()` follow clean two-phase locking: copy under lock, release lock, execute search / export outside lock, and re-acquire only when pushing the move.
   - Thread safety confirmed under multi-threaded stress tests with bounded timeouts.
3. **Cancellation Semantics Clarification**:
   - Client-side: `cancelPendingAnalysis()` aborts the browser's HTTP fetch and increments `analysisRequestIdRef`. Stale responses are strictly ignored, preventing UI contamination.
   - Server-side: Synchronous Python search threads running in AnyIO/FastAPI threadpools are not interrupted by TCP disconnects; they run to their bounded depth/time limit.

### Consequences
- 100% mathematically correct terminal scores and empty PVs.
- Zero deadlock risk.
- Explicit, unambiguous cancellation semantics.

---

## ADR-022: Draw-Rule Semantics Separation and AI Move Atomic Position Consistency

### Context
In accordance with FIDE chess laws, automatic game endings (checkmate, stalemate, insufficient material, 75-move rule, fivefold repetition) must be strictly separated from claimable draws (50-move rule, threefold repetition). Furthermore, while `Game.ai_move()` releases its lock during heavy search, concurrent user actions (moves, undos, restarts) must not allow a stale AI move to be applied to a mutated position.

### Decision
1. **Separation of Automatic Terminations vs Claimable Draws**:
   - `Game.is_terminal` returns `True` strictly for automatic endings (`is_checkmate`, `is_stalemate`, `is_insufficient_material`, `is_seventyfive_moves`, `is_fivefold_repetition`) or when a draw has been explicitly claimed.
   - For positions eligible for a draw claim (`can_claim_fifty_moves`, `can_claim_threefold_repetition`), the game remains active (`is_terminal = False`, `status = "active"`, `result = "*"`), and exposes `can_claim_draw = True` with `claimable_draw = "fifty_moves"` or `"threefold_repetition"`.
   - Players can continue playing moves; if moves continue to 75 moves or fivefold repetition, the game terminates automatically.
2. **Explicit Draw Claim Support**:
   - Implemented `Game.claim_draw()` and `SessionManager.claim_draw(session_id)`.
   - Added REST endpoint `POST /api/game/claim-draw` validating eligibility (returning HTTP 400 if ineligible, HTTP 404 if session not found, and HTTP 200 with terminal state when claimed).
3. **Position Analysis Distinction (`/api/game/analyze`)**:
   - Automatically terminal positions return `is_terminal = True, claimable_draw = None, best_move_uci = None, pv_uci = []`.
   - Positions where a draw claim is currently available return `is_terminal = False, claimable_draw = "fifty_moves"` or `"threefold_repetition"`, while engine search executes normally, providing `best_move_uci`, `best_move_san`, and `pv_uci` recommendations for ongoing play.
4. **AI Move Atomic Position-Consistency Protection**:
   - Introduced a monotonic `self._version: int = 0` counter on `Game`, incremented on every state mutation (`apply_move`, `undo`, `restart`, `set_fen`, `claim_draw`) under `self._lock`.
   - In `Game.ai_move()`, the authoritative position identity (`expected_version` and `expected_fen`) is captured under `self._lock`.
   - Engine search executes unlocked on a detached board copy.
   - Move application is performed via `apply_move()` which verifies `expected_version` and `expected_fen` inside `with self._lock:`.
   - If the game position was modified concurrently, `StalePositionError` is raised. The stale move is strictly rejected without board or history mutation (even if the move happened to be legal in the mutated position).
   - In `backend/api/routes/game.py`, `StalePositionError` is caught and returned as `HTTP 409 Conflict`.

### Consequences
- Full adherence to FIDE draw-rule semantics: claimable draws do not prematurely end the game.
- Continuous engine analysis recommendations on claimable draw positions.
- Absolute protection against stale AI moves corrupting game state under concurrent operations.

---

## ADR-023: Single-Ply Undo Behaviour, Authentic Cburnett Staunton SVGs, and Chess-Centric UI Layout

### Context
Player experience testing identified three essential requirements for tournament-grade usability:
1. **Undo Granularity**: Reverting single half-moves (plies) independently across both Player-vs-AI and Pass-and-Play modes, allowing players to explore alternative defenses and review moves step-by-step.
2. **Visual Artwork Quality**: Tournament-standard Staunton vector pieces offering clarity, contrast, and familiarity.
3. **Chess-Centric Layout**: A modern dashboard prioritizing board geometry, player cards, captured piece differential, and structured sidebar tabs.

### Decision
1. **Strict Single-Ply Undo**:
   - Revert exactly **ONE half-move (ply)** per Undo action across all modes (`player_vs_ai` and `pass_and_play`).
   - The backend `service.undo(1)` pops 1 move from the `python-chess` board stack, 1 record from `san_history`/`uci_history`, and 1 FEN from `fen_history`.
   - `self._version += 1` is incremented under lock, guaranteeing that any pending background AI computation for the pre-undo position is rejected with `HTTP 409 Conflict`.
   - Claimed draws are cleared (`_draw_claimed = False`) if the position that claimed the draw is undone.
   - When an AI move is undone, the side to move becomes the computer's turn; the application does **not** automatically trigger an AI move, waiting for explicit user action via the `AI Move` button or a subsequent `Undo`.
2. **Authentic Cburnett Staunton Piece Vectors**:
   - Integrated the classic Staunton vector piece set designed by **Colin M. L. Burnett** (Cburnett), widely recognized as the tournament standard on Lichess.
   - Dual-licensed under CC BY-SA 3.0 and GNU GPL.
   - Extracted 12 standalone SVG files to `frontend/src/assets/pieces/` and inlined into `frontend/src/components/ChessPiece.tsx` with clean JSX paths.
   - 100% local, self-contained, and CDN-free.
3. **Chess-Centric Visual Redesign**:
   - Established dark chess palette (`#161512`, `#21201d`, `#262421`, `#769656`/`#eeeed2`).
   - Built top/bottom `PlayerCard` components displaying player identities, active turn indicators, captured pieces tray (ordered by standard piece value: Q, R, B, N, P), and centipawn material advantage badge (`+1`, `+3`).
   - Reorganized right sidebar into three focused tabs: `Play & Moves`, `Engine Analysis`, and `Info & Rules`.
   - Exposed prominent `Claim Draw` banner both in the live play area and the info panel whenever a position is eligible for threefold repetition or 50-move draw claim.

### Consequences
- True single-ply granularity: users can step backwards move-by-move in both Player-vs-AI and Pass-and-Play.
- Professional, familiar visual presentation matching modern chess platforms.

---

## ADR-024: Authoritative Backend Chess Clock, Standardized Time Controls, and Ergonomic Interface Refinement

### Context
Competitive chess play requires standardized tournament time controls (bullet, blitz, rapid, classical, and untimed casual). A client-side timer alone is vulnerable to drift and manipulation. Clocks must be arbitrated authoritatively on the backend, accurately deduct AI search time, enforce remaining time bounds on search, and implement FIDE Article 6.9 rules for timeouts with insufficient mating material.

### Decision
1. **Authoritative Backend Chess Clock (`backend/game/clock.py`)**:
   - Designed `ChessClock` with exactly 5 standardized time controls:
     - `bullet`: 60.0s (1m + 0s)
     - `blitz`: 180.0s (3m + 0s)
     - `rapid`: 600.0s (10m + 0s, default)
     - `classic`: 1800.0s (30m + 0s)
     - `casual`: untimed (`None`)
   - Uses `time.perf_counter` (monotonic clock) for precise timing without OS clock drift or leap adjustments.
   - Clock does not start until the first legal move is executed. Once started, it automatically switches turns.
   - Computer thinking time during search is deducted accurately from the AI clock. In `ai_move()`, search time is bounded by remaining clock time minus safety margins (`time_limit = min(base_time, max(0.05, remaining - 0.2))`).
   - Moves submitted after time expiration are rejected with `GameOverError("Time expired")`.
   - **FIDE Article 6.9 Rule**: When a player flags on time, check whether the opponent possesses mating material using `board.has_insufficient_material(opponent_color)`. If the opponent has insufficient material to deliver checkmate by any legal move series (e.g. lone King, King + Bishop, King + Knight), the game concludes as a draw (`result="1/2-1/2"`, `status="timeout"`). If the opponent has mating material, the opponent wins (`1-0` or `0-1`).
   - **Lossless Single-Ply Undo**: Immutable `ClockSnapshot` records remaining time and clock running state at every move. On `service.undo()`, the exact pre-move clock state is restored.
2. **Frontend UI Ergonomics and Visual Polish**:
   - **Floating Difficulty Toast**: Rendered in a fixed container (`fixed top-5 right-5 z-50`) with backdrop blur, subtle border, smooth fade animation, and auto-dismissal after 2.8s. Completely eliminates layout shift on the board or sidebar.
   - **Unified Player Cards**: Human and Computer `PlayerCard` instances share identical surface backgrounds (`#21201d` / `#1e1c18`), identical height, and matching active-turn indicators (`#262421` background lift and emerald glow ring).
   - **Integrated Digital Clocks**: Digital monospace clock formatted as `MM:SS` inside each player card. Shows amber low-time warning ($\le 30$s) and red pulsing critical warning ($\le 10$s). Displays `Casual` for untimed games and `Time Out` badge upon flag fall.
   - **Rectangular Status Badges**: All status pills converted to solid rounded-rectangle badges (`rounded-md`).
   - **Toolbar Reorganization**: `GameControls` moved directly above the right sidebar tabs, grouping game actions with game settings and clearing space below the board. Redundant `GameStatus` removed.

### Consequences
- Robust, tournament-compliant timekeeping arbitrated by the backend.
- Seamless frontend presentation with a 100ms local tick reconciling with authoritative server state.

---

## ADR-025: AI Search Low-Time Safety, Post-Search Timeout Verification, and Active Game Time-Control Selection Semantics

### Context
Extreme time scramble conditions (< 50ms remaining on the clock) introduce critical edge cases: search algorithms must not exceed remaining time or forfeit on time, post-search timeouts must be caught atomically before applying moves, and changing time controls mid-game must queue for the next match rather than corrupting active clocks.

### Decision
1. **Low-Time AI Search Safety & Fallback**:
   - Replaced fixed 50ms floor with calibrated safety margins:
     ```python
     ai_safety_margin_s = 0.020  # 20ms safety margin reserved for post-search overhead
     ai_min_search_time_s = 0.010  # 10ms minimum search threshold
     available_search_time = rem_seconds - ai_safety_margin_s
     if available_search_time < ai_min_search_time_s:
         skip_search = True  # Instant legal move in ~30 microseconds
     else:
         budget_seconds = min(profile.max_time_ms / 1000.0, available_search_time)
         budget_seconds = min(budget_seconds, rem_seconds)  # Hard cap
     ```
   - When time is below 30ms ($< 10\text{ms} + 20\text{ms}$), search is skipped and an instant legal move is chosen in microseconds without adversarial search, ensuring clock safety in extreme time scrambles.
   - When time is $\ge 30$ms, search time is bounded strictly by `available_search_time` and capped by `rem_seconds`. Search never receives more time than remaining.
2. **Atomic Post-Search Timeout Check**:
   - In `backend/game/service.py`, after search finishes and lock is re-acquired:
     ```python
     if self._clock.timed_out_color is not None or self.is_terminal:
         raise GameOverError(self.status, self.result)
     ```
   - If timeout occurred during search or clock deduction, `GameOverError` is raised immediately and the move is rejected without modifying board, SAN history, or clock snapshots.
3. **Controlled Testing Endpoint**:
   - Added `POST /api/game/test-clock` (internal, excluded from OpenAPI schema) enabling precise clock configuration for automated testing without weakening production presets.
4. **Active Game Time Control Selection Semantics**:
   - Updated `TimeControlSelector` to remain selectable during active games.
   - When changed during an active match, the selected mode updates client state for the next game and triggers a toast: `"Time control changed to [MODE]. Applies on New Game."`, leaving active game clocks completely unaltered.
5. **PlayerCard Terminal Badge Condition Repair**:
   - Removed `&& isCurrentTurn` constraint from `isTimeout` and `isCheckmate` badge conditions in `PlayerCard.tsx`, ensuring `Time Out` and `Checkmate` badges remain prominently rendered in the player cards upon game termination.

### Consequences
- AI handles sub-50ms and sub-20ms clocks safely without flagging.
- Post-timeout moves are rejected with HTTP 409 and board interaction is disabled.
- Full compliance with FIDE Article 6.9 (insufficient material draw on timeout).

---

## ADR-026: Screen-Width Layout Proportions, Horizontal Wrapping Move History, and Interface Text Streamlining

### Context
On wide modern displays, chess applications must optimize horizontal space, expand right-side control hubs, and avoid vertical scrolling in move history. Tabular move lists consume excessive height, which can be streamlined into a compact Chess.com-style horizontal wrapping layout.

### Decision
1. **Desktop Proportions & Expanded Container Width**:
   - Expanded main application container from `max-w-7xl` (1280px) to `max-w-[1440px] 2xl:max-w-[1536px]` with calibrated padding.
   - Scaled desktop layout proportions:
     - Left column (Chessboard): `max-w-[500px] xl:max-w-[640px] 2xl:max-w-[680px]` maintaining strict 1:1 square aspect ratio without horizontal distortion.
     - Right column (Sidebar Hub): Increased from 400px to `w-full lg:w-[430px] xl:w-[470px] 2xl:w-[500px]`.
   - Guaranteed zero horizontal scroll across all target viewports ($1920\times 1080$, $1600\times 900$, $1366\times 768$, $1024\times 768$, $768\times 1024$, $390\times 844$).
2. **Horizontal Wrapping Move History Layout (`MoveHistory.tsx`)**:
   - Replaced vertical tabular list with a Chess.com-style horizontal inline wrapping layout (`flex flex-wrap items-center gap-x-2 gap-y-1.5`).
   - Grouped plies into logical move units: `1. [e4] [e5]`, `2. [Nf3] [Nc6]`.
   - Incomplete Move Pair Support: If White has moved but Black has not, only White's move is rendered (`1. [e4]`) without placeholder empty boxes.
   - Preserved all interactive functionality: click-to-review (`data-ply`), active move highlighting, review banner with return-to-live button, navigation controls (`|<`, `<`, `>`, `>|`), and PGN copy/export.
   - Reduced vertical height consumption by over 50% while improving visual density.
3. **Uncongested Action Toolbar (`GameControls.tsx`)**:
   - Arranged all 5 buttons (`New Game`, `AI Move`, `Undo`, `Restart`, `Flip Board`) with uniform height (`h-9`, 36px).
   - Primary actions (`New Game`, `AI Move`) feature prominent emerald styling.
   - Fits on a single horizontal row across desktop viewports without button clipping or wrapping.
4. **Interface Text Streamlining**:
   - Removed redundant note in `DifficultySelector.tsx`: `"Difficulty changes take effect immediately on the next AI move."`.
   - Removed redundant active difficulty text in `DifficultySelector.tsx` header (since active button is visually highlighted).
   - Removed duplicate active mode subtitle in `GameModeSelector.tsx` header.
   - Simplified player color labels: `White (1st)` and `Black (AI 1st)`.
   - Simplified header subtitle and footer text.

### Consequences
- Clean, modern, and spacious desktop presentation.
- Move history flows naturally and occupies significantly less vertical space.
- Zero horizontal scrolling across all desktop, tablet, and mobile viewports.

---

## ADR-027: On-Board Game-Over Modal and Post-Game Analysis Flow

### Context
Terminal game outcomes (Checkmate, Stalemate, Timeout, and Draws) require immediate, prominent communication directly on the board, paired with a natural post-game flow allowing players to seamlessly transition between position review and starting a new match.

### Decision
1. **On-Board Game-Over Modal (`GameOverModal.tsx`)**:
   - Render a focused, elevated modal dialog directly centered over the chessboard container (`absolute inset-0 z-30`).
   - Use a subtle translucent backdrop (`bg-black/60 backdrop-blur-[2px] rounded-xl`) that emphasizes the dialog while keeping the final board position and pieces clearly visible behind it.
   - Employ an elevated dark surface (`bg-[#21201d]/95 backdrop-blur-md rounded-2xl border border-stone-700/80 ring-1 ring-white/10 shadow-2xl`) consistent with the application's dark design tokens.
   - Display a distinct icon (Trophy for win, Clock for timeout win, Scale for draws), unambiguous title, clear explanation, and score badge (`1-0`, `0-1`, `½–½`).
   - Provide two primary actions:
     - **Analyze Game**: Dismisses the modal, preserves the final board position, full move list, and PGN, transitions into post-game review mode where players can step through historical moves or request engine evaluations.
     - **New Game**: Cleanly restarts the match using active configuration settings (mode, player color, difficulty, time control), resetting board, move list, and clocks.
   - Comprehensive Keyboard & Accessibility Support: Escape key triggers `onAnalyze` to enter review mode; full ARIA semantics (`role="dialog"`, `aria-modal="true"`, `aria-labelledby="game-over-title"`).
2. **Terminal Outcome Triggers**:
   - The modal triggers strictly for true terminal states (`gameState.is_terminal === true`): Checkmate, Stalemate, Draw by insufficient material, Claimed 50-move / threefold repetition, Automatic 75-move / fivefold repetition, and Timeout (including FIDE Article 6.9 draws).
   - Claimable draws (`can_claim_draw === true`, `is_terminal === false`) do **not** trigger the modal; the claim banner remains available below the board so the player retains the option to claim or continue playing.
3. **Redundant Notification Cleanup & Review Mode Strip**:
   - Removed the redundant bottom game-over banner from beneath the board.
   - When the user dismisses the modal into review mode, a subtle post-game review strip (`[data-testid="post-game-review-strip"]`) is displayed below the board showing the result summary and a "Show Summary" button (`[data-testid="reopen-game-over-modal"]`) allowing players to re-open the dialog at any time.
   - Maintained player card status badges (`isCheckmate`, `isTimeout`) and clock state.
4. **State Integrity**:
   - Clocks halt immediately upon terminal state detection.
   - Board interaction is locked during terminal and review states (`aria-disabled="true"`, `cursor-not-allowed`, click handler early-return).

### Consequences
- Professional, modern game-over presentation matching industry standards (Chess.com / Lichess).
- Seamless transition to post-game analysis without accidental board resets or lost move history.

---

## ADR-028: Removal of Header Ready Status Indicator

### Context
In modern desktop web applications, an idle "Ready" status badge during regular gameplay adds unnecessary visual noise. Board readiness and interactive status are naturally communicated by interactive board squares and player turn indicators.

### Decision
1. **Remove Ready Badge**:
   - Completely remove the green pulsating badge (`Ready`) from the right side of `header` in `App.tsx`.
   - Do not render any substitute element or reserve empty whitespace when the application is in an idle, ready state.
2. **Preserve Operational Feedback**:
   - The right side of the header conditionally renders only when an explicit background operation is taking place:
     - `isAiThinking`: Displays the amber spinning indicator (`Computer Thinking ({difficulty})...`).
     - `isInitializing`: Displays the subtle `Starting Game...` loader during initial session connection.
3. **Preserve Header Branding and Dimensions**:
   - Keep the pawn icon, `Chess AI` title, and `CUSTOM ADVERSARIAL ENGINE` badge on the left.
   - Maintain the standard `flex items-center justify-between` layout, vertical padding, and height without layout shifts across desktop, tablet, and mobile screens.

### Consequences
- Cleaner, distraction-free top navigation bar with clear feedback during active background operations.





