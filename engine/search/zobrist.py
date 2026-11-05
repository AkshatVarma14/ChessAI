"""Deterministic Zobrist hashing for chess board positions."""

import random
from typing import List
import chess

# Fixed deterministic PRNG seed to guarantee 100% reproducible keys across environments
ZOBRIST_SEED: int = 0x20261031_57A6E7

_prng = random.Random(ZOBRIST_SEED)

# 1. Piece square keys: [color 0..1][piece_type 1..6][square 0..63]
# Using 7 piece types (0 unused, 1=Pawn, 2=Knight, 3=Bishop, 4=Rook, 5=Queen, 6=King)
ZOBRIST_PIECES: List[List[List[int]]] = [
    [
        [_prng.getrandbits(64) for _ in range(64)]
        for _ in range(7)
    ]
    for _ in range(2)
]

# 2. Side to move key: XORed when Black is to move (White is baseline 0)
ZOBRIST_BLACK_TO_MOVE: int = _prng.getrandbits(64)

# 3. Castling rights keys: 16 possible states (4 bits: W-k, W-q, B-k, B-q)
ZOBRIST_CASTLING: List[int] = [_prng.getrandbits(64) for _ in range(16)]

# 4. En passant file keys: 8 files (0..7 for files a..h)
# Only XORed when an en passant capture is legally available
ZOBRIST_EP_FILE: List[int] = [_prng.getrandbits(64) for _ in range(8)]


def compute_castling_index(board: chess.Board) -> int:
    """Computes a 4-bit integer (0..15) representing active castling rights."""
    mask = 0
    if board.has_kingside_castling_rights(chess.WHITE):
        mask |= 1
    if board.has_queenside_castling_rights(chess.WHITE):
        mask |= 2
    if board.has_kingside_castling_rights(chess.BLACK):
        mask |= 4
    if board.has_queenside_castling_rights(chess.BLACK):
        mask |= 8
    return mask


def compute_zobrist_hash(board: chess.Board) -> int:
    """
    Computes a 64-bit deterministic Zobrist hash for a chess board from scratch.
    
    Includes:
    - Piece placement (type, color, square) via fast 64-bit bitboard scans.
    - Side to move (XORed with ZOBRIST_BLACK_TO_MOVE if Black's turn).
    - Castling rights (4-bit mask for White/Black kingside/queenside).
    - En passant file (only when an en passant capture is legally possible).
    
    Args:
        board: Authoritative python-chess Board.
        
    Returns:
        64-bit unsigned integer hash.
    """
    h = 0

    # 1. Piece positions via bitboard piece masks
    for color in (chess.WHITE, chess.BLACK):
        for piece_type in range(1, 7):
            mask = board.pieces_mask(piece_type, color)
            for square in chess.scan_forward(mask):
                h ^= ZOBRIST_PIECES[color][piece_type][square]

    # 2. Side to move
    if board.turn == chess.BLACK:
        h ^= ZOBRIST_BLACK_TO_MOVE

    # 3. Castling availability
    c_idx = compute_castling_index(board)
    h ^= ZOBRIST_CASTLING[c_idx]

    # 4. En passant square (only relevant if an en passant capture is legally possible)
    if board.ep_square is not None and board.has_legal_en_passant():
        ep_file = chess.square_file(board.ep_square)
        h ^= ZOBRIST_EP_FILE[ep_file]

    return h


def update_zobrist_hash(
    current_hash: int,
    board_before: chess.Board,
    move: chess.Move,
    board_after: chess.Board,
) -> int:
    """
    Incrementally updates a 64-bit Zobrist hash after a move is made.
    
    Demonstrates incremental XOR updating and can be used for fast make-move tracking.
    
    Args:
        current_hash: 64-bit Zobrist hash before the move.
        board_before: Board state before the move was pushed.
        move: Move being applied.
        board_after: Board state after move was pushed.
        
    Returns:
        Updated 64-bit Zobrist hash matching compute_zobrist_hash(board_after).
    """
    h = current_hash
    from_sq = move.from_square
    to_sq = move.to_square
    moving_color = board_before.turn
    piece_type = board_before.piece_type_at(from_sq)

    if piece_type is None:
        # Fallback if board states are inconsistent
        return compute_zobrist_hash(board_after)

    # 1. Remove moving piece from from_sq
    h ^= ZOBRIST_PIECES[moving_color][piece_type][from_sq]

    # 2. Handle captures
    if board_before.is_en_passant(move):
        # En passant capture: captured pawn is on the same file as to_sq, rank of from_sq
        cap_sq = chess.square(chess.square_file(to_sq), chess.square_rank(from_sq))
        opponent_color = not moving_color
        h ^= ZOBRIST_PIECES[opponent_color][chess.PAWN][cap_sq]
    elif board_before.is_capture(move):
        # Ordinary capture: captured piece is on to_sq
        captured_type = board_before.piece_type_at(to_sq)
        if captured_type is not None:
            opponent_color = not moving_color
            h ^= ZOBRIST_PIECES[opponent_color][captured_type][to_sq]

    # 3. Place piece on to_sq (handling promotions)
    if move.promotion is not None:
        h ^= ZOBRIST_PIECES[moving_color][move.promotion][to_sq]
    else:
        h ^= ZOBRIST_PIECES[moving_color][piece_type][to_sq]

    # 4. Handle castling rook movement
    if board_before.is_castling(move):
        if to_sq == chess.G1:  # White O-O
            h ^= ZOBRIST_PIECES[chess.WHITE][chess.ROOK][chess.H1]
            h ^= ZOBRIST_PIECES[chess.WHITE][chess.ROOK][chess.F1]
        elif to_sq == chess.C1:  # White O-O-O
            h ^= ZOBRIST_PIECES[chess.WHITE][chess.ROOK][chess.A1]
            h ^= ZOBRIST_PIECES[chess.WHITE][chess.ROOK][chess.D1]
        elif to_sq == chess.G8:  # Black O-O
            h ^= ZOBRIST_PIECES[chess.BLACK][chess.ROOK][chess.H8]
            h ^= ZOBRIST_PIECES[chess.BLACK][chess.ROOK][chess.F8]
        elif to_sq == chess.C8:  # Black O-O-O
            h ^= ZOBRIST_PIECES[chess.BLACK][chess.ROOK][chess.A8]
            h ^= ZOBRIST_PIECES[chess.BLACK][chess.ROOK][chess.D8]

    # 5. Side to move flip
    h ^= ZOBRIST_BLACK_TO_MOVE

    # 6. Castling rights update
    old_c = compute_castling_index(board_before)
    new_c = compute_castling_index(board_after)
    if old_c != new_c:
        h ^= ZOBRIST_CASTLING[old_c]
        h ^= ZOBRIST_CASTLING[new_c]

    # 7. En passant update
    if board_before.ep_square is not None and board_before.has_legal_en_passant():
        h ^= ZOBRIST_EP_FILE[chess.square_file(board_before.ep_square)]
    if board_after.ep_square is not None and board_after.has_legal_en_passant():
        h ^= ZOBRIST_EP_FILE[chess.square_file(board_after.ep_square)]

    return h


def verify_zobrist_hash(board: chess.Board, expected_hash: int) -> bool:
    """Verifies that a given hash strictly matches the freshly computed position hash."""
    return compute_zobrist_hash(board) == expected_hash
