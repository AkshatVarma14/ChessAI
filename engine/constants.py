"""Constants for chess evaluation and adversarial search."""

# Centipawn value for checkmate. Adjusted by ply to favor faster mates.
MATE_SCORE: int = 30000

# Practical infinity boundary for search window bounds
INFINITY: int = 100000

# Default provisional piece values in centipawns (Master Spec Section 8.3)
DEFAULT_PAWN_VALUE: int = 100
DEFAULT_KNIGHT_VALUE: int = 320
DEFAULT_BISHOP_VALUE: int = 330
DEFAULT_ROOK_VALUE: int = 500
DEFAULT_QUEEN_VALUE: int = 900
DEFAULT_KING_VALUE: int = 0  # King is not treated as capturable material

# Penalty in centipawns applied when an emergency check depth ceiling is reached under check
UNRESOLVED_CHECK_PENALTY: int = 300

