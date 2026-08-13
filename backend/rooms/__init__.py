"""Room system: private rooms, hosts, players, teams and membership."""

from .errors import RoomError
from .manager import (
    DEFAULT_MAX_PLAYERS,
    MAX_NAME_LENGTH,
    ROOM_CODE_ALPHABET,
    ROOM_CODE_LENGTH,
    Room,
    RoomManager,
    RoomStatus,
    validate_player_name,
)

__all__ = [
    "DEFAULT_MAX_PLAYERS",
    "MAX_NAME_LENGTH",
    "ROOM_CODE_ALPHABET",
    "ROOM_CODE_LENGTH",
    "Room",
    "RoomError",
    "RoomManager",
    "RoomStatus",
    "validate_player_name",
]
