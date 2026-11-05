"""Curated training and validation datasets for evaluation weight tuning.

Maintains strict separation between the training suite (used to compute fitness during
GA optimization) and the held-out validation suite (used exclusively for post-tuning
verification and baseline comparison).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class TuningPosition:
    """
    Specification of a curated test position with objective strategic/tactical criteria.

    Attributes:
        id: Unique identifier string.
        fen: Authoritative FEN representation.
        category: Strategic domain (material, pawn_structure, king_safety, center_control, tactical, endgame).
        description: Explanation of the position's objective characteristics.
        expected_eval_sign: Expected sign of evaluation from White's perspective (+1, -1, or 0).
        min_expected_margin_cp: Minimum expected centipawn margin (e.g. +80 cp for up a pawn).
        expected_best_move_uci: Optional tactical move expected from search.
        avoid_move_uci: Optional tactical blunder move that must be avoided.
        weight: Importance weighting of this position in aggregate fitness scoring.
    """

    id: str
    fen: str
    category: str
    description: str
    expected_eval_sign: Optional[int] = None
    min_expected_margin_cp: Optional[int] = None
    expected_best_move_uci: Optional[str] = None
    avoid_move_uci: Optional[str] = None
    weight: float = 1.0


# Authoritative Training Suite (24 curated positions)
TRAINING_SUITE: Tuple[TuningPosition, ...] = (
    # 1. Material Imbalances
    TuningPosition(
        id="TR_MAT_01",
        fen="r1bqkb1r/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        category="material",
        description="White up a knight (Black missing knight on g8)",
        expected_eval_sign=1,
        min_expected_margin_cp=200,
        weight=1.5,
    ),
    TuningPosition(
        id="TR_MAT_02",
        fen="rnbqkbnr/pppp1ppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        category="material",
        description="White up a pawn (Black missing pawn on e7)",
        expected_eval_sign=1,
        min_expected_margin_cp=70,
        weight=1.0,
    ),
    TuningPosition(
        id="TR_MAT_03",
        fen="rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        category="material",
        description="White up a queen (Black missing queen on d8)",
        expected_eval_sign=1,
        min_expected_margin_cp=750,
        weight=1.5,
    ),
    TuningPosition(
        id="TR_MAT_04",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR b KQkq - 0 1",
        category="material",
        description="Black up a queen (White missing queen on d1)",
        expected_eval_sign=-1,
        min_expected_margin_cp=-750,
        weight=1.5,
    ),
    TuningPosition(
        id="TR_MAT_05",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQK1NR b KQkq - 0 1",
        category="material",
        description="Black up a bishop (White missing bishop on f1)",
        expected_eval_sign=-1,
        min_expected_margin_cp=-220,
        weight=1.2,
    ),
    TuningPosition(
        id="TR_MAT_06",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBN1 b Qkq - 0 1",
        category="material",
        description="Black up a rook (White missing rook on h1)",
        expected_eval_sign=-1,
        min_expected_margin_cp=-380,
        weight=1.2,
    ),
    # 2. Passed Pawns & Pawn Structure
    TuningPosition(
        id="TR_PWN_01",
        fen="8/4P3/8/4k3/8/8/8/4K3 w - - 0 1",
        category="pawn_structure",
        description="White advanced passed pawn on e7",
        expected_eval_sign=1,
        min_expected_margin_cp=80,
        weight=1.2,
    ),
    TuningPosition(
        id="TR_PWN_02",
        fen="8/8/8/4K3/8/8/4p3/7k w - - 0 1",
        category="pawn_structure",
        description="Black advanced passed pawn on e2",
        expected_eval_sign=-1,
        min_expected_margin_cp=-80,
        weight=1.2,
    ),
    TuningPosition(
        id="TR_PWN_03",
        fen="8/p4p2/5k2/8/8/2PP4/8/4K3 w - - 0 1",
        category="pawn_structure",
        description="White connected pawns c3+d3 vs Black isolated a7+f7",
        expected_eval_sign=1,
        min_expected_margin_cp=20,
        weight=1.0,
    ),
    TuningPosition(
        id="TR_PWN_04",
        fen="8/6pp/5k2/8/8/2P5/2P5/4K3 w - - 0 1",
        category="pawn_structure",
        description="White doubled isolated pawns on c2+c3 vs Black connected g7+h7",
        expected_eval_sign=-1,
        min_expected_margin_cp=-20,
        weight=1.0,
    ),
    # 3. King Safety & Pawn Shields
    TuningPosition(
        id="TR_KNG_01",
        fen="r2q1rk1/ppp2ppp/2n5/8/8/2N5/PPP2PPP/R2QK2R w KQ - 0 1",
        category="king_safety",
        description="White uncastled king exposed on open e-file against castled Black",
        expected_eval_sign=-1,
        min_expected_margin_cp=-25,
        weight=1.0,
    ),
    TuningPosition(
        id="TR_KNG_02",
        fen="r2qk2r/ppp2ppp/2n5/8/8/2N5/PPP2PPP/R2Q1RK1 b kq - 0 1",
        category="king_safety",
        description="Black uncastled king exposed on open e-file against castled White",
        expected_eval_sign=1,
        min_expected_margin_cp=25,
        weight=1.0,
    ),
    TuningPosition(
        id="TR_KNG_03",
        fen="r1bq1rk1/ppp2ppp/2n5/3np3/8/2NP1N2/PPP1BPPP/R2Q1RK1 w - - 0 9",
        category="king_safety",
        description="Both kings castled safe; balanced middlegame",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    TuningPosition(
        id="TR_KNG_04",
        fen="r1bq1rk1/ppp2ppp/2n2n2/3pp3/3PP3/2N2N2/PPP2PPP/R1BQ1RK1 w - - 0 8",
        category="king_safety",
        description="Calm symmetrical positions with both kings safely castled",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    # 4. Center Control & Mobility
    TuningPosition(
        id="TR_CTR_01",
        fen="rnbqkbnr/pppppppp/8/8/3PP3/8/PPP2PPP/RNBQKBNR b KQkq - 0 1",
        category="center_control",
        description="White dual pawn center (d4+e4) control",
        expected_eval_sign=1,
        min_expected_margin_cp=25,
        weight=1.0,
    ),
    TuningPosition(
        id="TR_CTR_02",
        fen="rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        category="center_control",
        description="Central tension (Scandinavian e4 vs d5)",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=0.8,
    ),
    TuningPosition(
        id="TR_CTR_03",
        fen="r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        category="center_control",
        description="Italian Game central piece development",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    TuningPosition(
        id="TR_CTR_04",
        fen="1rbqkb1r/pppn1ppp/3p1n2/4p3/8/2N2NP1/PPPPPPBP/R1BQK2R w KQk - 2 6",
        category="center_control",
        description="Solid balanced fianchetto opening structure",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    # 5. Tactical Moves & Blunder Avoidance
    TuningPosition(
        id="TR_TAC_01",
        fen="r1bqk2r/pppp1ppp/2n5/4P3/1bB1n3/2N2N2/PPPP1PPP/R1BQK2R b KQkq - 2 6",
        category="tactical",
        description="Tactical resolution: Black captures knight b4c3",
        expected_eval_sign=None,
        min_expected_margin_cp=None,
        expected_best_move_uci="b4c3",
        weight=1.5,
    ),
    TuningPosition(
        id="TR_TAC_02",
        fen="rnb1kbnr/pppp1ppp/8/4q3/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 1",
        category="tactical",
        description="Hanging Black queen on e5: White plays d4e5",
        expected_eval_sign=1,
        min_expected_margin_cp=500,
        expected_best_move_uci="d4e5",
        weight=1.5,
    ),
    TuningPosition(
        id="TR_TAC_03",
        fen="r1bqkb1r/pppp1ppp/2n5/4p3/2B1n3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 0 1",
        category="tactical",
        description="Scholar's mate: White plays Qxf7#",
        expected_eval_sign=None,
        min_expected_margin_cp=None,
        expected_best_move_uci="f3f7",
        weight=1.5,
    ),
    TuningPosition(
        id="TR_TAC_04",
        fen="6k1/5ppp/8/8/8/8/5PPP/4R1K1 w - - 0 1",
        category="tactical",
        description="Back-rank mate in 1: White plays Re8#",
        expected_eval_sign=1,
        min_expected_margin_cp=500,
        expected_best_move_uci="e1e8",
        weight=2.0,
    ),
    # 6. Endgame Principles
    TuningPosition(
        id="TR_END_01",
        fen="8/5pk1/7p/8/4R3/7P/5PK1/4r3 w - - 0 1",
        category="endgame",
        description="Balanced rook endgame",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    TuningPosition(
        id="TR_END_02",
        fen="8/1R6/8/4k3/8/8/4K3/8 w - - 0 1",
        category="endgame",
        description="White rook active on 7th rank vs black king",
        expected_eval_sign=1,
        min_expected_margin_cp=40,
        weight=1.0,
    ),
)


# Authoritative Held-out Validation Suite (16 curated positions, NEVER seen during training)
VALIDATION_SUITE: Tuple[TuningPosition, ...] = (
    # 1. Material Imbalances
    TuningPosition(
        id="VAL_MAT_01",
        fen="r1bqkbnr/pppp1ppp/2n5/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 1 2",
        category="material",
        description="Equal material opening development",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    TuningPosition(
        id="VAL_MAT_02",
        fen="r1bqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        category="material",
        description="White up a knight (Black missing knight on b8)",
        expected_eval_sign=1,
        min_expected_margin_cp=250,
        weight=1.5,
    ),
    TuningPosition(
        id="VAL_MAT_03",
        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/R1BQKBNR b KQkq - 0 1",
        category="material",
        description="Black up a knight (White missing knight on b1)",
        expected_eval_sign=-1,
        min_expected_margin_cp=-250,
        weight=1.5,
    ),
    TuningPosition(
        id="VAL_MAT_04",
        fen="r4rk1/ppp2ppp/8/8/8/8/PPP2PPP/R2Q1RK1 w - - 0 1",
        category="material",
        description="White up a queen in endgame/middlegame (Q+R vs R)",
        expected_eval_sign=1,
        min_expected_margin_cp=750,
        weight=1.5,
    ),
    # 2. Passed Pawns & Pawn Structure
    TuningPosition(
        id="VAL_PWN_01",
        fen="8/1P6/8/8/8/5k2/8/4K3 w - - 0 1",
        category="pawn_structure",
        description="White b7 passed pawn near promotion",
        expected_eval_sign=1,
        min_expected_margin_cp=90,
        weight=1.2,
    ),
    TuningPosition(
        id="VAL_PWN_02",
        fen="8/8/5k2/8/8/8/1p6/4K3 b - - 0 1",
        category="pawn_structure",
        description="Black b2 passed pawn near promotion",
        expected_eval_sign=-1,
        min_expected_margin_cp=-90,
        weight=1.2,
    ),
    TuningPosition(
        id="VAL_PWN_03",
        fen="8/3pp3/5k2/8/8/3P1P2/8/4K3 w - - 0 1",
        category="pawn_structure",
        description="White isolated d3+f3 pawns vs Black connected d7+e7 pawns",
        expected_eval_sign=-1,
        min_expected_margin_cp=-5,
        weight=1.0,
    ),
    TuningPosition(
        id="VAL_PWN_04",
        fen="8/p4p2/4k3/8/4K3/8/2P1P3/8 w - - 0 1",
        category="pawn_structure",
        description="White connected pawns c2+e2 vs Black isolated a7+f7 with equal kings",
        expected_eval_sign=1,
        min_expected_margin_cp=1,
        weight=1.0,
    ),
    # 3. King Safety
    TuningPosition(
        id="VAL_KNG_01",
        fen="r4rk1/ppp2ppp/2n5/8/8/2N5/PPP1KPPP/R6R w - - 0 1",
        category="king_safety",
        description="White uncastled king exposed on e2 against safely castled Black king",
        expected_eval_sign=-1,
        min_expected_margin_cp=-5,
        weight=1.0,
    ),
    TuningPosition(
        id="VAL_KNG_02",
        fen="rnbqk1nr/ppp1bppp/8/3pp3/4P3/3P1N2/PPP2PPP/RNBQKB1R w KQkq - 0 4",
        category="king_safety",
        description="Symmetrical calm opening structure",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    # 4. Center Control
    TuningPosition(
        id="VAL_CTR_01",
        fen="rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq - 0 3",
        category="center_control",
        description="French Defense central space advantage",
        expected_eval_sign=1,
        min_expected_margin_cp=5,
        weight=1.0,
    ),
    TuningPosition(
        id="VAL_CTR_02",
        fen="r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 3 3",
        category="center_control",
        description="Ruy Lopez Spanish opening central tension",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    # 5. Tactical Test Cases
    TuningPosition(
        id="VAL_TAC_01",
        fen="6k1/5ppp/5B2/8/8/7Q/5PPP/6K1 w - - 0 1",
        category="tactical",
        description="White delivers checkmate in 1 with Qc8#",
        expected_eval_sign=1,
        min_expected_margin_cp=500,
        expected_best_move_uci="h3c8",
        weight=1.5,
    ),
    TuningPosition(
        id="VAL_TAC_02",
        fen="r2q1rk1/1b2bppp/p1n1pn2/1pp5/3PP3/2NB1N2/PP3PPP/R1BQR1K1 w - - 0 12",
        category="tactical",
        description="Closed middlegame pawn break",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    TuningPosition(
        id="VAL_TAC_03",
        fen="6k1/5ppp/8/8/8/8/5PPP/4q1RK w - - 0 1",
        category="tactical",
        description="Forced check evasion: White rook must capture checking queen with g1e1",
        expected_eval_sign=None,
        min_expected_margin_cp=None,
        expected_best_move_uci="g1e1",
        weight=2.0,
    ),
    TuningPosition(
        id="VAL_TAC_04",
        fen="8/8/4k3/8/8/8/1R6/4K3 w - - 0 1",
        category="endgame",
        description="White rook endgame advantage against bare king",
        expected_eval_sign=1,
        min_expected_margin_cp=350,
        weight=1.5,
    ),
)


# Authoritative Independent Benchmark Suite (Strictly separate from Train & Validation)
INDEPENDENT_SUITE: Tuple[TuningPosition, ...] = (
    TuningPosition(
        id="IND_END_01",
        fen="1K1k4/1P6/8/8/8/8/r7/2R5 w - - 0 1",
        category="endgame",
        description="Lucena position: White winning rook endgame",
        expected_eval_sign=1,
        min_expected_margin_cp=200,
        weight=1.5,
    ),
    TuningPosition(
        id="IND_END_02",
        fen="8/8/8/4k3/4r3/8/4KR2/8 w - - 0 1",
        category="endgame",
        description="Philidor drawing defense in rook endgame",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
    TuningPosition(
        id="IND_TAC_01",
        fen="6rk/6pp/7N/8/8/8/8/4K2Q w - - 0 1",
        category="tactical",
        description="Smothered checkmate in 1 with Nf7#",
        expected_eval_sign=1,
        min_expected_margin_cp=500,
        expected_best_move_uci="h6f7",
        weight=2.0,
    ),
    TuningPosition(
        id="IND_TAC_02",
        fen="r3kbnr/ppp1pppp/8/3N4/8/8/PPPP1PPP/R1BQK1NR w KQkq - 0 1",
        category="tactical",
        description="Royal knight fork: White plays Nc7+ winning rook",
        expected_eval_sign=1,
        min_expected_margin_cp=200,
        expected_best_move_uci="d5c7",
        weight=2.0,
    ),
    TuningPosition(
        id="IND_MAT_01",
        fen="2r2rk1/ppp2ppp/8/8/8/8/PPP2PPP/3Q2K1 w - - 0 1",
        category="material",
        description="Queen vs two rooks material imbalance",
        expected_eval_sign=-1,
        min_expected_margin_cp=-50,
        weight=1.2,
    ),
    TuningPosition(
        id="IND_CTR_01",
        fen="r1bqkbnr/pp1ppppp/2n5/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
        category="center_control",
        description="Sicilian Defense dynamic central tension",
        expected_eval_sign=0,
        min_expected_margin_cp=0,
        weight=1.0,
    ),
)


def get_training_suite() -> List[TuningPosition]:
    """Returns a fresh list of all training positions."""
    return list(TRAINING_SUITE)


def get_validation_suite() -> List[TuningPosition]:
    """Returns a fresh list of all held-out validation positions."""
    return list(VALIDATION_SUITE)


def get_independent_suite() -> List[TuningPosition]:
    """Returns a fresh list of independent benchmark positions."""
    return list(INDEPENDENT_SUITE)
