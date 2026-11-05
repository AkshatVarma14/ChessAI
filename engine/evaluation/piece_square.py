"""Piece-Square Table (PST) evaluation for positional square bonuses."""

from typing import Optional
import chess

from engine.config import EvaluationConfig

# 64-element square tables indexed 0..63 where square = rank * 8 + file.
# Rank 1 (indices 0..7), Rank 2 (indices 8..15) ... Rank 8 (indices 56..63).
# Table layouts below are written from Rank 8 (top) down to Rank 1 (bottom) for readability,
# and flipped so index 0 = a1.

def _flip_table(table_8x8: list[list[int]]) -> tuple[int, ...]:
    """Flattens a visual 8x8 table (Rank 8 at top, Rank 1 at bottom) to 0..63 square indices."""
    flat = []
    # Rank 1 is row index 7, Rank 8 is row index 0
    for rank in range(8):
        row = table_8x8[7 - rank]
        flat.extend(row)
    return tuple(flat)

# 1. Pawn table: Encourages central advancement, passing, penalizes premature flank pushes
PAWN_TABLE = _flip_table([
    [  0,   0,   0,   0,   0,   0,   0,   0],  # Rank 8 (Promoted)
    [ 35,  40,  45,  50,  50,  45,  40,  35],  # Rank 7
    [ 15,  20,  25,  30,  30,  25,  20,  15],  # Rank 6
    [  5,  10,  20,  25,  25,  20,  10,   5],  # Rank 5
    [  0,   5,  15,  20,  20,  15,   5,   0],  # Rank 4
    [  0,   0,   5,  10,  10,   5,   0,   0],  # Rank 3
    [  0,   0,   0, -10, -10,   0,   0,   0],  # Rank 2 (Initial)
    [  0,   0,   0,   0,   0,   0,   0,   0],  # Rank 1
])

# 2. Knight table: Encourages centralization and outposts, penalizes the rim
KNIGHT_TABLE = _flip_table([
    [-25, -15, -10, -10, -10, -10, -15, -25],  # Rank 8
    [-15,   0,   5,   5,   5,   5,   0, -15],  # Rank 7
    [-10,   5,  15,  20,  20,  15,   5, -10],  # Rank 6
    [-10,   5,  20,  25,  25,  20,   5, -10],  # Rank 5
    [-10,   5,  20,  25,  25,  20,   5, -10],  # Rank 4
    [-10,   5,  15,  20,  20,  15,   5, -10],  # Rank 3
    [-15,   0,   5,   5,   5,   5,   0, -15],  # Rank 2
    [-25, -15, -10, -10, -10, -10, -15, -25],  # Rank 1
])

# 3. Bishop table: Encourages central diagonal control, penalizes corners
BISHOP_TABLE = _flip_table([
    [-15, -10, -10, -10, -10, -10, -10, -15],
    [-10,   5,   5,   5,   5,   5,   5, -10],
    [-10,   5,  15,  15,  15,  15,   5, -10],
    [-10,  10,  15,  20,  20,  15,  10, -10],
    [-10,  10,  15,  20,  20,  15,  10, -10],
    [-10,   5,  15,  15,  15,  15,   5, -10],
    [-10,   5,   5,   5,   5,   5,   5, -10],
    [-15, -10, -10, -10, -10, -10, -10, -15],
])

# 4. Rook table: Encourages central and open files, 7th rank infiltration
ROOK_TABLE = _flip_table([
    [  0,   0,   5,  10,  10,   5,   0,   0],
    [ 15,  20,  20,  25,  25,  20,  20,  15],  # Rank 7
    [ -5,   0,   0,   5,   5,   0,   0,  -5],
    [ -5,   0,   0,   5,   5,   0,   0,  -5],
    [ -5,   0,   0,   5,   5,   0,   0,  -5],
    [ -5,   0,   0,   5,   5,   0,   0,  -5],
    [  0,   0,   5,  10,  10,   5,   0,   0],
    [  0,   0,   5,  10,  10,   5,   0,   0],
])

# 5. Queen table: Central positioning without overcommitting early
QUEEN_TABLE = _flip_table([
    [-15, -10,  -5,   0,   0,  -5, -10, -15],
    [-10,   0,   5,   5,   5,   5,   0, -10],
    [ -5,   5,  10,  15,  15,  10,   5,  -5],
    [  0,   5,  15,  20,  20,  15,   5,   0],
    [  0,   5,  15,  20,  20,  15,   5,   0],
    [ -5,   5,  10,  15,  15,  10,   5,  -5],
    [-10,   0,   5,   5,   5,   5,   0, -10],
    [-15, -10,  -5,   0,   0,  -5, -10, -15],
])

# 6. King Middlegame: Heavy preference for castled corner shelter (g1/c1)
KING_TABLE_MG = _flip_table([
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-25, -35, -35, -45, -45, -35, -35, -25],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -25, -25, -20, -20, -10],
    [ 15,  15,   0,   0,   0,   0,  15,  15],  # Castled pawn shield
    [ 20,  25,  10,   0,   0,  10,  25,  20],  # g1/c1 preferred
])

# 7. King Endgame: Preference for active central king
KING_TABLE_EG = _flip_table([
    [-25, -15, -10, -10, -10, -10, -15, -25],
    [-15,   0,   5,  10,  10,   5,   0, -15],
    [-10,   5,  15,  20,  20,  15,   5, -10],
    [-10,  10,  20,  30,  30,  20,  10, -10],  # Active central king
    [-10,  10,  20,  30,  30,  20,  10, -10],
    [-10,   5,  15,  20,  20,  15,   5, -10],
    [-15,   0,   5,  10,  10,   5,   0, -15],
    [-25, -15, -10, -10, -10, -10, -15, -25],
])


def get_piece_square_score(
    piece_type: chess.PieceType, square: chess.Square, phase: float = 1.0
) -> int:
    """Returns the static positional score for a White piece on square."""
    match piece_type:
        case chess.PAWN:
            return PAWN_TABLE[square]
        case chess.KNIGHT:
            return KNIGHT_TABLE[square]
        case chess.BISHOP:
            return BISHOP_TABLE[square]
        case chess.ROOK:
            return ROOK_TABLE[square]
        case chess.QUEEN:
            return QUEEN_TABLE[square]
        case chess.KING:
            mg_val = KING_TABLE_MG[square]
            eg_val = KING_TABLE_EG[square]
            return round(phase * mg_val + (1.0 - phase) * eg_val)
        case _:
            return 0


PST_TABLES = (
    (chess.PAWN, PAWN_TABLE),
    (chess.KNIGHT, KNIGHT_TABLE),
    (chess.BISHOP, BISHOP_TABLE),
    (chess.ROOK, ROOK_TABLE),
    (chess.QUEEN, QUEEN_TABLE),
)


def evaluate_piece_square(
    board: chess.Board,
    phase: float = 1.0,
    config: Optional[EvaluationConfig] = None,
) -> int:
    """
    Evaluates piece-square table bonuses in centipawns from White's perspective.
    
    Guarantees:
    - Black squares are vertically mirrored via chess.square_mirror(sq).
    - Perfect symmetry under board inversion: E(mirrored) == -E(pos).
    - Zero allocations via direct bitboard piece scanning.
    
    Args:
        board: Board position to evaluate.
        phase: Game phase in [0.0, 1.0] (1.0 = middlegame, 0.0 = endgame).
        config: Evaluation configuration.
        
    Returns:
        Integer centipawns (White PST minus Black PST).
    """
    white_pst = 0
    black_pst = 0

    for piece_type, table in PST_TABLES:
        w_mask = board.pieces_mask(piece_type, chess.WHITE)
        for sq in chess.scan_forward(w_mask):
            white_pst += table[sq]

        b_mask = board.pieces_mask(piece_type, chess.BLACK)
        for sq in chess.scan_forward(b_mask):
            black_pst += table[chess.square_mirror(sq)]

    w_king = board.king(chess.WHITE)
    if w_king is not None:
        white_pst += round(phase * KING_TABLE_MG[w_king] + (1.0 - phase) * KING_TABLE_EG[w_king])

    b_king = board.king(chess.BLACK)
    if b_king is not None:
        b_mirr = chess.square_mirror(b_king)
        black_pst += round(phase * KING_TABLE_MG[b_mirr] + (1.0 - phase) * KING_TABLE_EG[b_mirr])

    return white_pst - black_pst
