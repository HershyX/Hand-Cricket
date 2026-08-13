"""WebSocket layer: connection registry, message builders and handlers."""

from .connections import ConnectionManager
from .handler import handle_client_message
from .messages import (
    error_message,
    game_state_message,
    room_state_message,
    send_ws,
)

__all__ = [
    "ConnectionManager",
    "error_message",
    "game_state_message",
    "handle_client_message",
    "room_state_message",
    "send_ws",
]
