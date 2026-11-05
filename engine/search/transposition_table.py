"""Bounded Transposition Table with Zobrist hashing, bound types, and replacement policy."""

from dataclasses import dataclass
import enum
import math
from typing import List, Optional, Tuple
import chess

from engine.constants import MATE_SCORE


class Bound(enum.IntEnum):
    """Transposition table entry bound type."""

    EXACT = 1  # True minimax score (alpha < score < beta)
    LOWER = 2  # Lower bound score (score >= beta, cutoff occurred)
    UPPER = 3  # Upper bound score (score <= alpha, all moves failed low)


@dataclass(slots=True)
class TTEntry:
    """A single record stored in the Transposition Table."""

    key: int
    depth: int
    score: int  # Root-independent normalized score
    bound: Bound
    best_move: Optional[chess.Move] = None
    age: int = 0
    halfmove_clock: int = 0


class TranspositionTable:
    """
    Fixed-size in-memory transposition table indexed by Zobrist hash keys.
    
    Guarantees:
    - Bounded memory footprint with O(1) direct-mapped indexing.
    - Full 64-bit key verification to detect and prevent collision pollution.
    - Mate-score normalization across variable search plies.
    - Multi-criteria replacement policy prioritizing deeper entries and newer generations.
    - Fifty-move rule context awareness to prevent unsafe score reuse.
    - Comprehensive telemetry (probes, hits, cutoffs, stores, replacements, occupancy).
    """

    def __init__(self, size_mb: int = 16) -> None:
        """
        Initializes a transposition table with power-of-two capacity fitting within size_mb.
        
        Args:
            size_mb: Memory budget in megabytes (minimum 1 MB).
        """
        if size_mb < 1:
            size_mb = 1

        # Estimate entry size in Python (~128 bytes per slot including list pointer)
        target_entries = (size_mb * 1024 * 1024) // 128
        power = max(10, int(math.log2(target_entries)))
        self.capacity: int = 1 << power
        self.mask: int = self.capacity - 1
        self.size_mb: int = size_mb

        self.table: List[Optional[TTEntry]] = [None] * self.capacity

        # Statistics & telemetry
        self.probes: int = 0
        self.hits: int = 0
        self.cutoffs: int = 0
        self.stores: int = 0
        self.replacements: int = 0
        self.occupancy: int = 0
        self.generation: int = 0

    def clear(self) -> None:
        """Resets all entries and clears search telemetry."""
        self.table = [None] * self.capacity
        self.probes = 0
        self.hits = 0
        self.cutoffs = 0
        self.stores = 0
        self.replacements = 0
        self.occupancy = 0
        self.generation = 0

    def new_search(self) -> None:
        """Advances the table generation counter for aging entries across iterations/games."""
        self.generation += 1

    @staticmethod
    def normalize_score(score: int, ply: int) -> int:
        """
        Converts a search ply-dependent mate score to a root-independent score for storage.
        
        Args:
            score: Raw centipawn score from search.
            ply: Current search ply distance from root.
            
        Returns:
            Normalized root-independent integer score.
        """
        if score >= MATE_SCORE - 1000:
            return score + ply
        elif score <= -MATE_SCORE + 1000:
            return score - ply
        return score

    @staticmethod
    def denormalize_score(score: int, ply: int) -> int:
        """
        Converts a stored root-independent mate score back to the current search ply.
        
        Args:
            score: Stored root-independent integer score.
            ply: Current search ply distance from root.
            
        Returns:
            Ply-adjusted centipawn score.
        """
        if score >= MATE_SCORE - 1000:
            return score - ply
        elif score <= -MATE_SCORE + 1000:
            return score + ply
        return score

    def probe(
        self,
        key: int,
        depth: int,
        alpha: int,
        beta: int,
        ply: int,
        halfmove_clock: int = 0,
        max_extension: int = 10,
    ) -> Tuple[Optional[int], Optional[chess.Move], bool]:
        """
        Probes the transposition table for an existing entry matching the position key.
        
        Args:
            key: 64-bit Zobrist key of the current position.
            depth: Required nominal search depth.
            alpha: Current search alpha bound.
            beta: Current search beta bound.
            ply: Current search ply distance from root.
            halfmove_clock: Current board halfmove clock.
            max_extension: Maximum potential extension depth beyond nominal search (e.g. quiescence check evasions).
            
        Returns:
            Tuple of (score, best_move, is_cutoff):
            - score: Denormalized score if hit, else None.
            - best_move: Suggested move for ordering if available, else None.
            - is_cutoff: True if score satisfies alpha-beta cutoff criteria.
        """
        self.probes += 1
        idx = key & self.mask
        entry = self.table[idx]

        if entry is None or entry.key != key:
            return None, None, False

        self.hits += 1
        score = self.denormalize_score(entry.score, ply)
        best_move = entry.best_move

        # Fifty-move safety: never reuse a score for cutoff if clocks diverge and either search
        # could encounter or be influenced by the 50-move (100 halfmove) draw threshold,
        # accounting for both nominal search depth and potential quiescence check-evasion extensions.
        if entry.halfmove_clock != halfmove_clock:
            if (
                halfmove_clock >= 90
                or entry.halfmove_clock >= 90
                or (halfmove_clock + depth + max_extension >= 100)
                or (entry.halfmove_clock + entry.depth + max_extension >= 100)
            ):
                return score, best_move, False

        # Depth check: entry must have searched at least as deep as requested
        if entry.depth < depth:
            return score, best_move, False

        # Bound checks against current alpha/beta window
        if entry.bound == Bound.EXACT:
            self.cutoffs += 1
            return score, best_move, True
        elif entry.bound == Bound.LOWER and score >= beta:
            self.cutoffs += 1
            return score, best_move, True
        elif entry.bound == Bound.UPPER and score <= alpha:
            self.cutoffs += 1
            return score, best_move, True

        return score, best_move, False

    def get_entry(self, key: int) -> Optional[TTEntry]:
        """
        Directly looks up and returns the stored TTEntry for a given 64-bit Zobrist key.
        Does not increment probe or hit statistics.
        """
        idx = key & self.mask
        entry = self.table[idx]
        if entry is not None and entry.key == key:
            return entry
        return None

    def extract_pv(
        self,
        root_board: chess.Board,
        max_length: int = 10,
        first_move: Optional[chess.Move] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        Extracts the Principal Variation sequence from the Transposition Table.

        Follows best moves from the root position across consecutive search horizons,
        verifying legality and preventing cycles. If first_move is provided, it is
        guaranteed to be the root move of the PV.

        Args:
            root_board: The root chess.Board to start extraction from.
            max_length: Maximum plies of PV to extract.
            first_move: Optional authoritative best move for the root position.

        Returns:
            Tuple of (pv_uci_list, pv_san_list).
        """
        from engine.search.zobrist import compute_zobrist_hash

        if max_length <= 0:
            return [], []

        pv_uci: List[str] = []
        pv_san: List[str] = []
        curr_board = root_board.copy()
        seen_keys = set()

        # If explicit first move provided and legal, use it as step 0
        if first_move is not None:
            if not curr_board.is_legal(first_move):
                return [], []
            try:
                san = curr_board.san(first_move)
                pv_uci.append(first_move.uci())
                pv_san.append(san)
                seen_keys.add(compute_zobrist_hash(curr_board))
                curr_board.push(first_move)
            except Exception:
                return [], []

        while len(pv_uci) < max_length:
            key = compute_zobrist_hash(curr_board)
            if key in seen_keys:
                break
            seen_keys.add(key)

            entry = self.get_entry(key)
            if (
                entry is None
                or entry.best_move is None
                or not curr_board.is_legal(entry.best_move)
            ):
                break

            move = entry.best_move
            try:
                san = curr_board.san(move)
            except Exception:
                break

            pv_uci.append(move.uci())
            pv_san.append(san)
            curr_board.push(move)

        return pv_uci, pv_san

    def store(
        self,
        key: int,
        depth: int,
        score: int,
        bound: Bound,
        best_move: Optional[chess.Move] = None,
        ply: int = 0,
        halfmove_clock: int = 0,
    ) -> None:
        """
        Stores or updates an entry in the transposition table using replacement heuristics.
        
        Args:
            key: 64-bit Zobrist key.
            depth: Completed search depth.
            score: Centipawn score at root ply.
            bound: Bound type (EXACT, LOWER, UPPER).
            best_move: Best legal move found.
            ply: Current search ply.
            halfmove_clock: Halfmove clock at the stored node.
        """
        self.stores += 1
        norm_score = self.normalize_score(score, ply)
        idx = key & self.mask
        existing = self.table[idx]

        new_entry = TTEntry(
            key=key,
            depth=depth,
            score=norm_score,
            bound=bound,
            best_move=best_move,
            age=self.generation,
            halfmove_clock=halfmove_clock,
        )

        if existing is None:
            self.table[idx] = new_entry
            self.occupancy += 1
            return

        if existing.key == key:
            # Same position: update if deeper, or if equal depth and new entry is EXACT
            if depth >= existing.depth or (depth == existing.depth and bound == Bound.EXACT and existing.bound != Bound.EXACT):
                # If new entry has no best_move, preserve existing best_move
                if best_move is None and existing.best_move is not None:
                    new_entry.best_move = existing.best_move
                self.table[idx] = new_entry
            elif best_move is not None and existing.best_move is None:
                existing.best_move = best_move
            return

        # Collision with a different position: apply replacement policy
        self.replacements += 1
        # Replace if existing entry is from an older search generation, or if new entry is deeper
        if existing.age < self.generation or depth >= existing.depth:
            self.table[idx] = new_entry

    def store_move_only(self, key: int, best_move: chess.Move) -> None:
        """
        Stores or updates best_move for move ordering without storing a reusable score bound.

        Used for path-dependent nodes (e.g. repetition or fifty-move contexts) to guarantee
        that path-dependent scores never contaminate the transposition table, while
        preserving heuristic move ordering for future visits.

        Args:
            key: 64-bit Zobrist key.
            best_move: Suggested best legal move found.
        """
        idx = key & self.mask
        existing = self.table[idx]

        if existing is not None and existing.key == key:
            # Preserve existing entry's score/bound/depth if any, update best_move
            existing.best_move = best_move
        elif existing is None:
            # New slot: depth=-1 ensures probe will NEVER cutoff (depth < requested_depth >= 1)
            self.table[idx] = TTEntry(
                key=key,
                depth=-1,
                score=0,
                bound=Bound.UPPER,
                best_move=best_move,
                age=self.generation,
                halfmove_clock=0,
            )
            self.occupancy += 1

    @property
    def hit_rate(self) -> float:
        """Percentage of probes resulting in table hits."""
        return (self.hits / self.probes * 100.0) if self.probes > 0 else 0.0

    @property
    def cutoff_rate(self) -> float:
        """Percentage of probes resulting in search cutoffs."""
        return (self.cutoffs / self.probes * 100.0) if self.probes > 0 else 0.0

    @property
    def occupancy_rate(self) -> float:
        """Percentage of slots currently occupied."""
        return (self.occupancy / self.capacity * 100.0) if self.capacity > 0 else 0.0
