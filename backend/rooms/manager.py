"""Private room management for Hand Cricket Online.

Rooms are stored in memory. Each room wraps exactly one GameEngine, which is
the authoritative source of truth for players, teams and game state. The room
system adds the lobby concepts the engine intentionally does not own: a room
code, a host, membership limits, configurable team sizes and join validation.

Team sizes are fully dynamic and independent: Team A and Team B may have
different numbers of players. The host configures ``team_a_size`` and
``team_b_size``; players then choose which team to join (or remain
UNASSIGNED). The game can start only when both teams hold exactly their
configured number of players and every player is ready.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from config import MAX_TEAM_SIZE, MIN_TEAM_SIZE
from game.engine import GameEngine
from game.models import ConnectionStatus, GamePhase, Player, ReadyStatus
from game.state import TEAM_1_ID, TEAM_2_ID

from .errors import RoomError

ROOM_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
ROOM_CODE_LENGTH = 6
MAX_NAME_LENGTH = 20

# Default total room capacity: enough for the largest valid team configuration
# (MAX_TEAM_SIZE vs MAX_TEAM_SIZE).
DEFAULT_MAX_PLAYERS = 2 * MAX_TEAM_SIZE

TEAM_A_KEY = "A"
TEAM_B_KEY = "B"


class RoomStatus(str, Enum):
    WAITING = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"


@dataclass
class Room:
    room_code: str
    host_player_id: str
    engine: GameEngine
    status: RoomStatus = RoomStatus.WAITING
    max_players: int = DEFAULT_MAX_PLAYERS
    team_a_size: int = MIN_TEAM_SIZE
    team_b_size: int = MIN_TEAM_SIZE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def players(self) -> dict[str, Player]:
        return self.engine.state.players

    def get_player(self, player_id: str) -> Player | None:
        return self.engine.state.players.get(player_id)

    @property
    def team_a_count(self) -> int:
        return len(self.engine.state.teams[TEAM_1_ID].players)

    @property
    def team_b_count(self) -> int:
        return len(self.engine.state.teams[TEAM_2_ID].players)

    def validate_start(self) -> list[str]:
        """Return the lobby problems that prevent the game from starting.

        The game may start only when the room is still in the lobby, Team A and
        Team B each hold exactly their configured number of players, and every
        player is assigned to a team and ready.
        """
        problems: list[str] = []
        if self.status != RoomStatus.WAITING or self.engine.state.phase != GamePhase.LOBBY:
            problems.append("The game is not in the lobby")
            return problems
        if self.team_a_count != self.team_a_size:
            problems.append(
                f"Team A needs exactly {self.team_a_size} player(s), has {self.team_a_count}"
            )
        if self.team_b_count != self.team_b_size:
            problems.append(
                f"Team B needs exactly {self.team_b_size} player(s), has {self.team_b_count}"
            )
        for player in self.engine.state.players.values():
            if not player.team_id:
                problems.append(f"{player.name} is not assigned to a team")
            elif player.ready_status != ReadyStatus.READY:
                problems.append(f"{player.name} is not ready")
        return problems

    @property
    def can_start(self) -> bool:
        return not self.validate_start()


def validate_player_name(name: object) -> str:
    """Validate and normalize a display name. Raises RoomError when invalid."""
    if not isinstance(name, str):
        raise RoomError("INVALID_NAME", "Player name must be a string", 400)
    cleaned = name.strip()
    if not cleaned:
        raise RoomError("INVALID_NAME", "Player name cannot be empty", 400)
    if len(cleaned) > MAX_NAME_LENGTH:
        raise RoomError(
            "INVALID_NAME",
            f"Player name must be {MAX_NAME_LENGTH} characters or fewer",
            400,
        )
    if any(ord(ch) < 32 for ch in cleaned):
        raise RoomError("INVALID_NAME", "Player name contains invalid characters", 400)
    return cleaned


class RoomManager:
    """In-memory registry of private rooms with code generation and joins."""

    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    def _generate_code(self) -> str:
        while True:
            code = "".join(
                secrets.choice(ROOM_CODE_ALPHABET) for _ in range(ROOM_CODE_LENGTH)
            )
            if code not in self._rooms:
                return code

    async def create_room(self, host_name: str, max_players: int = DEFAULT_MAX_PLAYERS) -> tuple[Room, Player]:
        """Create a private room. The host becomes the first player on Team A."""
        async with self._lock:
            name = validate_player_name(host_name)
            code = self._generate_code()
            engine = GameEngine.create(room_id=code)
            room = Room(
                room_code=code,
                host_player_id="",
                engine=engine,
                max_players=max_players,
            )
            host = engine.add_player(name=name)
            engine.assign_player_to_team(host.id, TEAM_1_ID)
            host.connection_status = ConnectionStatus.DISCONNECTED
            room.host_player_id = host.id
            self._rooms[code] = room
            return room, host

    async def join_room(self, room_code: str, player_name: str) -> tuple[Room, Player]:
        """Join a room by code. New players join UNASSIGNED and pick a team."""
        async with self._lock:
            room = self._rooms.get(room_code.strip().upper())
            if room is None:
                raise RoomError("ROOM_NOT_FOUND", "Room not found", 404)
            if room.status != RoomStatus.WAITING:
                raise RoomError("ROOM_STARTED", "This room has already started", 409)
            if len(room.engine.state.players) >= room.max_players:
                raise RoomError("ROOM_FULL", "This room is full", 409)
            name = validate_player_name(player_name)
            for existing in room.engine.state.players.values():
                if existing.name.lower() == name.lower():
                    raise RoomError(
                        "DUPLICATE_PLAYER",
                        "A player with this name is already in the room",
                        409,
                    )
            player = room.engine.add_player(name=name)
            player.connection_status = ConnectionStatus.DISCONNECTED
            self.touch(room)
            return room, player

    # ------------------------------------------------------------------
    # Team configuration and membership
    # ------------------------------------------------------------------

    @staticmethod
    def team_key_to_id(team_key: object) -> str:
        """Map a client team key ("A"/"B") onto the engine team id."""
        if isinstance(team_key, str):
            key = team_key.strip().upper()
            if key == TEAM_A_KEY:
                return TEAM_1_ID
            if key == TEAM_B_KEY:
                return TEAM_2_ID
        raise RoomError("INVALID_TEAM", "Team must be 'A' or 'B'", 400)

    @staticmethod
    def team_id_to_key(team_id: str) -> str:
        if team_id == TEAM_1_ID:
            return TEAM_A_KEY
        if team_id == TEAM_2_ID:
            return TEAM_B_KEY
        raise RoomError("INVALID_TEAM", f"Unknown team id {team_id!r}", 400)

    @staticmethod
    def _team_label(team_id: str) -> str:
        return "Team A" if team_id == TEAM_1_ID else "Team B"

    @staticmethod
    def _validate_size_value(value: object, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise RoomError(
                "INVALID_TEAM_SIZE",
                f"{label} size must be an integer, got {value!r}",
                400,
            )
        if value < MIN_TEAM_SIZE or value > MAX_TEAM_SIZE:
            raise RoomError(
                "INVALID_TEAM_SIZE",
                f"{label} size must be between {MIN_TEAM_SIZE} and {MAX_TEAM_SIZE}",
                400,
            )
        return value

    def _validate_size(self, room: Room, label: str, team_id: str, value: object) -> int:
        size = self._validate_size_value(value, label)
        current = len(room.engine.state.teams[team_id].players)
        if size < current:
            raise RoomError(
                "TEAM_SIZE_TOO_SMALL",
                f"{label} already has {current} player(s); "
                f"capacity cannot be reduced below that",
                409,
            )
        return size

    def set_team_sizes(self, room: Room, team_a_size: object, team_b_size: object) -> None:
        """Configure the lobby's Team A and Team B sizes (host only)."""
        if room.status != RoomStatus.WAITING:
            raise RoomError("ROOM_STARTED", "Team sizes can only be set in the lobby", 409)
        size_a = self._validate_size(room, "Team A", TEAM_1_ID, team_a_size)
        size_b = self._validate_size(room, "Team B", TEAM_2_ID, team_b_size)
        if size_a + size_b > room.max_players:
            raise RoomError(
                "INVALID_TEAM_SIZE",
                f"Combined team sizes {size_a} + {size_b} exceed the room "
                f"capacity of {room.max_players} players",
                400,
            )
        room.team_a_size = size_a
        room.team_b_size = size_b
        self.touch(room)

    def join_team(self, room: Room, player_id: str, team_key: object) -> Player:
        """Assign a player to a team, validating capacity and membership."""
        team_id = self.team_key_to_id(team_key)
        if room.status != RoomStatus.WAITING:
            raise RoomError("ROOM_STARTED", "Teams can only be changed in the lobby", 409)
        player = self._get_player(room, player_id)
        if player.team_id == team_id:
            return player
        team = room.engine.state.teams[team_id]
        capacity = room.team_a_size if team_id == TEAM_1_ID else room.team_b_size
        if len(team.players) >= capacity:
            raise RoomError(
                "TEAM_FULL",
                f"{self._team_label(team_id)} is full ({capacity}/{capacity})",
                409,
            )
        room.engine.assign_player_to_team(player.id, team_id)
        player.ready_status = ReadyStatus.NOT_READY
        self.touch(room)
        return player

    def leave_team(self, room: Room, player_id: str) -> None:
        """Remove a player from their team, leaving them UNASSIGNED."""
        if room.status != RoomStatus.WAITING:
            raise RoomError("ROOM_STARTED", "Teams can only be changed in the lobby", 409)
        player = self._get_player(room, player_id)
        if player.team_id is None:
            return
        room.engine.unassign_player(player.id)
        player.ready_status = ReadyStatus.NOT_READY
        self.touch(room)

    def _get_player(self, room: Room, player_id: str) -> Player:
        player = room.get_player(player_id)
        if player is None:
            raise RoomError("PLAYER_NOT_FOUND", "Player is not in this room", 404)
        return player

    def reset_lobby(self, room: Room) -> None:
        """Reset an in-progress (or waiting) room back to a clean lobby.

        All players keep their identities and connection status but are
        returned to UNASSIGNED and NOT_READY. Host-only.
        """
        snapshot = [
            (player.id, player.name, player.connection_status)
            for player in room.engine.all_players()
        ]
        room.engine = GameEngine.create(room_id=room.room_code)
        for player_id, name, connection_status in snapshot:
            player = room.engine.add_player(name=name, player_id=player_id)
            player.connection_status = connection_status
        room.status = RoomStatus.WAITING
        self.touch(room)

    def get_room(self, room_code: str) -> Room | None:
        if not room_code:
            return None
        return self._rooms.get(room_code.strip().upper())

    def remove_room(self, room_code: str) -> None:
        self._rooms.pop(room_code.strip().upper(), None)

    def touch(self, room: Room) -> None:
        room.last_activity = datetime.now(timezone.utc)
