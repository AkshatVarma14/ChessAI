"""FastAPI router for chess game session management and moves."""

from typing import Optional
import chess
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.dependencies import get_session_manager
from backend.api.schemas import (
    AIMoveRequest,
    AnalysisResponse,
    AnalyzePositionRequest,
    ClaimDrawRequest,
    DifficultyUpdateRequest,
    ErrorResponse,
    GameState,
    MakeMoveRequest,
    NewGameRequest,
    PGNResponse,
    RestartGameRequest,
    UndoMoveRequest,
)
from backend.game.exceptions import (
    GameOverError,
    IllegalMoveError,
    InvalidFENError,
    SessionNotFoundError,
    StalePositionError,
    UndoError,
)
from backend.game.session import SessionManager
from engine import SearchConfig, choose_move, get_difficulty_profile, validate_difficulty

router = APIRouter(prefix="/api/game", tags=["Game"])


@router.post(
    "/new",
    response_model=GameState,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new game session",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid initial FEN or difficulty"},
    },
)
def create_game(
    payload: Optional[NewGameRequest] = None,
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Initializes a new chess game session with standard or custom starting position, difficulty, and time control."""
    initial_fen = payload.initial_fen if payload else None
    difficulty = payload.difficulty if (payload and payload.difficulty) else "medium"
    time_control = payload.time_control if (payload and payload.time_control) else "rapid"
    try:
        return session_manager.create_session(
            initial_fen=initial_fen,
            difficulty=difficulty,
            time_control=time_control,
        )
    except (InvalidFENError, ValueError) as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/move",
    response_model=GameState,
    status_code=status.HTTP_200_OK,
    summary="Execute a chess move",
    responses={
        400: {"model": ErrorResponse, "description": "Illegal move or invalid format"},
        404: {"model": ErrorResponse, "description": "Session not found"},
        409: {"model": ErrorResponse, "description": "Game is already over"},
    },
)
def make_move(
    payload: MakeMoveRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Applies a legal move in UCI or SAN notation to the specified game session."""
    try:
        return session_manager.make_move(payload.session_id, payload.move)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except IllegalMoveError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err
    except GameOverError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err


@router.post(
    "/undo",
    response_model=GameState,
    status_code=status.HTTP_200_OK,
    summary="Undo move(s)",
    responses={
        400: {"model": ErrorResponse, "description": "Cannot undo requested plies"},
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
def undo_move(
    payload: UndoMoveRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Reverts plies from the game history."""
    try:
        return session_manager.undo_move(payload.session_id, plies=payload.plies)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except UndoError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/restart",
    response_model=GameState,
    status_code=status.HTTP_200_OK,
    summary="Restart game to initial position",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
def restart_game(
    payload: RestartGameRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Resets the game session back to its starting state."""
    try:
        return session_manager.restart_session(payload.session_id)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.get(
    "/state",
    response_model=GameState,
    status_code=status.HTTP_200_OK,
    summary="Get current game state",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
def get_game_state(
    session_id: str = Query(..., description="Active session ID"),
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Retrieves authoritative current state of the game session."""
    try:
        return session_manager.get_state(session_id)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/difficulty",
    response_model=GameState,
    status_code=status.HTTP_200_OK,
    summary="Update engine difficulty preset for active session",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid difficulty preset"},
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
def update_difficulty(
    payload: DifficultyUpdateRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Updates the difficulty level for subsequent AI moves without resetting the board."""
    try:
        return session_manager.set_difficulty(payload.session_id, payload.difficulty)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/ai-move",
    response_model=GameState,
    status_code=status.HTTP_200_OK,
    summary="Trigger an AI move for the active session",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
        409: {"model": ErrorResponse, "description": "Game is already over or position changed during calculation"},
    },
)
def make_ai_move(
    payload: AIMoveRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Calculates and applies an AI move on behalf of the active player."""
    try:
        return session_manager.make_ai_move(payload.session_id)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except (GameOverError, StalePositionError) as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err


@router.post(
    "/claim-draw",
    response_model=GameState,
    status_code=status.HTTP_200_OK,
    summary="Claim a draw by threefold repetition or 50-move rule",
    responses={
        400: {"model": ErrorResponse, "description": "Draw cannot be claimed in current position"},
        404: {"model": ErrorResponse, "description": "Session not found"},
        409: {"model": ErrorResponse, "description": "Game is already over"},
    },
)
def claim_draw(
    payload: ClaimDrawRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Claims a draw for the active session if eligible by 50-move rule or threefold repetition."""
    try:
        return session_manager.claim_draw(payload.session_id)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
    except GameOverError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err
    except IllegalMoveError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze a board position with custom chess engine",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid FEN or parameters"},
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
def analyze_position(
    payload: AnalyzePositionRequest,
    session_manager: SessionManager = Depends(get_session_manager),
) -> AnalysisResponse:
    """
    Evaluates a position and produces score, principal variation (PV), and search telemetry.
    Can analyze either an arbitrary FEN string or the current board state of an active session.
    """
    game = None
    diff_label = None
    if payload.fen:
        try:
            board = chess.Board(payload.fen)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid FEN: {err}",
            ) from err
    elif payload.session_id:
        try:
            game = session_manager.get_game(payload.session_id)
            board = game.board
            diff_label = game.difficulty
        except SessionNotFoundError as err:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(err),
            ) from err
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'session_id' or 'fen' must be provided for analysis.",
        )

    # 1. Immediate evaluation for automatic terminal positions (checkmate, stalemate, and automatic rules draws)
    if board.is_checkmate():
        is_white_turn = board.turn == chess.WHITE
        return AnalysisResponse(
            score_cp=-30000 if is_white_turn else 30000,
            is_mate=True,
            mate_in_plies=0,
            is_terminal=True,
            claimable_draw=None,
            depth=0,
            nodes_searched=0,
            quiescence_nodes=0,
            elapsed_ms=0.0,
            nodes_per_second=0,
            best_move_uci=None,
            best_move_san=None,
            pv_uci=[],
            pv_san=[],
            tt_hits=0,
            tt_probes=0,
            tt_cutoffs=0,
            tt_stores=0,
        )

    if (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_seventyfive_moves()
        or board.is_fivefold_repetition()
        or (game is not None and game.is_terminal)
    ):
        return AnalysisResponse(
            score_cp=0,
            is_mate=False,
            mate_in_plies=None,
            is_terminal=True,
            claimable_draw=None,
            depth=0,
            nodes_searched=0,
            quiescence_nodes=0,
            elapsed_ms=0.0,
            nodes_per_second=0,
            best_move_uci=None,
            best_move_san=None,
            pv_uci=[],
            pv_san=[],
            tt_hits=0,
            tt_probes=0,
            tt_cutoffs=0,
            tt_stores=0,
        )

    # 2. Check for claimable (non-terminal) draw opportunities
    claimable_type: Optional[str] = None
    if board.can_claim_fifty_moves():
        claimable_type = "fifty_moves"
    elif board.can_claim_threefold_repetition():
        claimable_type = "threefold_repetition"

    if payload.difficulty:
        try:
            diff_label = validate_difficulty(payload.difficulty)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            ) from err

    if diff_label:
        profile = get_difficulty_profile(diff_label)
        base_cfg = profile.search_config
        search_cfg = SearchConfig(
            depth=payload.depth if payload.depth is not None else base_cfg.depth,
            algorithm=base_cfg.algorithm,
            use_iterative_deepening=base_cfg.use_iterative_deepening,
            use_move_ordering=base_cfg.use_move_ordering,
            use_quiescence=base_cfg.use_quiescence,
            max_quiescence_depth=base_cfg.max_quiescence_depth,
            max_check_depth=base_cfg.max_check_depth,
            use_transposition_table=base_cfg.use_transposition_table,
            transposition_table_size_mb=base_cfg.transposition_table_size_mb,
            time_limit_ms=payload.time_limit_ms if payload.time_limit_ms is not None else base_cfg.time_limit_ms,
        )
    else:
        depth = payload.depth if payload.depth is not None else 3
        time_limit_ms = payload.time_limit_ms if payload.time_limit_ms is not None else 1500.0
        search_cfg = SearchConfig(
            depth=depth,
            algorithm="iterative_deepening",
            use_iterative_deepening=True,
            use_move_ordering=True,
            use_quiescence=True,
            use_transposition_table=True,
            time_limit_ms=time_limit_ms,
        )

    res = choose_move(board, config=search_cfg, difficulty=diff_label)

    is_mate = abs(res.score_cp) >= 29000 or res.is_checkmate
    mate_in_plies = max(0, 30000 - abs(res.score_cp)) if is_mate else None
    score_cp = res.score_cp

    return AnalysisResponse(
        score_cp=score_cp,
        is_mate=is_mate,
        mate_in_plies=mate_in_plies,
        is_terminal=False,
        claimable_draw=claimable_type,
        depth=res.completed_depth or res.depth,
        nodes_searched=res.nodes_searched,
        quiescence_nodes=res.quiescence_nodes,
        elapsed_ms=res.elapsed_ms,
        nodes_per_second=res.nodes_per_second,
        best_move_uci=res.best_move_uci,
        best_move_san=res.best_move_san,
        pv_uci=res.pv_uci,
        pv_san=res.pv_san,
        tt_hits=res.tt_hits,
        tt_probes=res.tt_probes,
        tt_cutoffs=res.tt_cutoffs,
        tt_stores=res.tt_stores,
    )


@router.get(
    "/pgn",
    response_model=PGNResponse,
    status_code=status.HTTP_200_OK,
    summary="Export game in standard PGN format",
    responses={
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
def export_pgn(
    session_id: str = Query(..., description="Active session ID"),
    session_manager: SessionManager = Depends(get_session_manager),
) -> PGNResponse:
    """Exports the full game history of an active session in standard PGN format."""
    try:
        pgn_text = session_manager.get_pgn(session_id)
        return PGNResponse(session_id=session_id, pgn=pgn_text)
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post(
    "/test-clock",
    response_model=GameState,
    include_in_schema=False,
    summary="Controlled test configuration to set clock times without waiting",
)
def set_test_clock(
    session_id: str = Query(...),
    white_time: Optional[float] = Query(None),
    black_time: Optional[float] = Query(None),
    session_manager: SessionManager = Depends(get_session_manager),
) -> GameState:
    """Sets clock times for a session strictly for controlled browser edge-case testing."""
    try:
        game = session_manager.get_game(session_id)
        with game._lock:
            if white_time is not None:
                game.clock._white_time = white_time
                if white_time <= 0.0:
                    game.clock._timed_out_color = "white"
            if black_time is not None:
                game.clock._black_time = black_time
                if black_time <= 0.0:
                    game.clock._timed_out_color = "black"
        return game.get_state()
    except SessionNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
