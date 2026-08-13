"""Data models and enums for Hand Cricket Online.

This module only defines types. It contains no game logic.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class GamePhase(str, Enum):
    """High-level lifecycle phase of a game."""

    LOBBY = "LOBBY"
    TOSS = "TOSS"
    TOSS_DECISION = "TOSS_DECISION"
    INNINGS_1 = "INNINGS_1"
    INNINGS_BREAK = "INNINGS_BREAK"
    INNINGS_2 = "INNINGS_2"
    GAME_OVER = "GAME_OVER"


class TurnState(str, Enum):
    """Fine-grained state within a gameplay innings."""

    WAITING_FOR_MOVES = "WAITING_FOR_MOVES"
    RESOLVING_MOVE = "RESOLVING_MOVE"
    PLAYER_OUT = "PLAYER_OUT"
    NEXT_BATTER = "NEXT_BATTER"
    BOWLER_SWITCH_PENDING = "BOWLER_SWITCH_PENDING"


class ConnectionStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"


class ReadyStatus(str, Enum):
    NOT_READY = "NOT_READY"
    READY = "READY"


class TeamRole(str, Enum):
    BATTING = "BATTING"
    BOWLING = "BOWLING"


class TossDecision(str, Enum):
    BATTING = "BATTING"
    BOWLING = "BOWLING"


class BallOutcome(str, Enum):
    RUNS = "RUNS"
    OUT = "OUT"


class GameResult(str, Enum):
    PENDING = "PENDING"
    TEAM_1_WIN = "TEAM_1_WIN"
    TEAM_2_WIN = "TEAM_2_WIN"
    TIE = "TIE"


class Player(BaseModel):
    """A player in a game. A player is always a member of exactly one team
    once assigned, and belongs to a batting order."""

    id: str
    name: str
    team_id: str | None = None
    connection_status: ConnectionStatus = ConnectionStatus.CONNECTED
    ready_status: ReadyStatus = ReadyStatus.NOT_READY
    batting_position: int | None = None


class Team(BaseModel):
    """A team of one or more players."""

    id: str
    name: str
    players: list[Player] = Field(default_factory=list)
    score: int = 0
    wickets: int = 0


class BallRecord(BaseModel):
    """A single completed ball of an innings."""

    innings: int
    ball_number: int
    batter_id: str
    bowler_id: str
    batter_move: int
    bowler_move: int
    runs: int
    outcome: BallOutcome


class Innings(BaseModel):
    """Scoring container for one innings."""

    number: int
    batting_team_id: str
    bowling_team_id: str
    score: int = 0
    wickets: int = 0
    ball_count: int = 0
    target: int | None = None


class GameState(BaseModel):
    """The complete, authoritative state of one game."""

    game_id: str
    room_id: str

    phase: GamePhase = GamePhase.LOBBY
    turn_state: TurnState | None = None

    teams: dict[str, Team] = Field(default_factory=dict)
    team_order: list[str] = Field(default_factory=list)
    players: dict[str, Player] = Field(default_factory=dict)

    batting_team_id: str | None = None
    bowling_team_id: str | None = None
    current_batter_id: str | None = None
    current_bowler_id: str | None = None

    current_innings: Innings | None = None
    innings_number: int = 0
    target_score: int | None = None

    toss_winner_id: str | None = None
    toss_decision: TossDecision | None = None
    toss_numbers: dict[str, int] = Field(default_factory=dict)

    batter_submitted: bool = False
    bowler_submitted: bool = False
    batter_move: int | None = None
    bowler_move: int | None = None

    bowler_switch_pending: bool = False

    ball_count: int = 0
    ball_log: list[BallRecord] = Field(default_factory=list)
    last_ball: BallRecord | None = None
    last_outcome: BallOutcome | None = None

    result: GameResult = GameResult.PENDING
    winner_team_id: str | None = None
    game_over_reason: str | None = None

    max_wickets: int = 10
