"""Hand Cricket Online game engine.

Pure, framework-independent game logic. The engine owns the authoritative
game state and can be exercised without a browser or server.
"""

from .engine import EngineError, GameEngine
from .models import (
    BallOutcome,
    BallRecord,
    ConnectionStatus,
    GamePhase,
    GameResult,
    GameState,
    Innings,
    Player,
    ReadyStatus,
    Team,
    TeamRole,
    TossDecision,
    TurnState,
)
from .rules import (
    MAX_MOVE,
    MIN_MOVE,
    IllegalMoveError,
    calculate_runs,
    calculate_target,
    is_out,
    validate_move,
)
from .state import (
    TEAM_1_ID,
    TEAM_2_ID,
    create_game_state,
    new_game_id,
    new_player_id,
    new_room_id,
)

__all__ = [
    "BallOutcome",
    "BallRecord",
    "ConnectionStatus",
    "EngineError",
    "GameEngine",
    "GamePhase",
    "GameResult",
    "GameState",
    "IllegalMoveError",
    "Innings",
    "MAX_MOVE",
    "MIN_MOVE",
    "Player",
    "ReadyStatus",
    "TEAM_1_ID",
    "TEAM_2_ID",
    "Team",
    "TeamRole",
    "TossDecision",
    "TurnState",
    "calculate_runs",
    "calculate_target",
    "create_game_state",
    "is_out",
    "new_game_id",
    "new_player_id",
    "new_room_id",
    "validate_move",
]
