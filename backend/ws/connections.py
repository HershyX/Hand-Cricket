"""Registry of active WebSocket connections.

Connections are keyed by (room_code, player_id) and every broadcast is
scoped to a single room code. This is the enforcement point for room
isolation: messages sent to room ABC123 can never reach sockets registered
under room XYZ789.
"""

from __future__ import annotations

import json


class ConnectionManager:
    """Tracks per-room/per-player WebSocket connections."""

    def __init__(self) -> None:
        self._sockets: dict[tuple[str, str], set] = {}
        self._ever_connected: set[tuple[str, str]] = set()

    def _key(self, room_code: str, player_id: str) -> tuple[str, str]:
        return (room_code.upper(), player_id)

    def is_player_connected(self, room_code: str, player_id: str) -> bool:
        return bool(self._sockets.get(self._key(room_code, player_id)))

    def connect(self, room_code: str, player_id: str, websocket) -> str:
        """Register a socket for a player.

        Returns ``"first"`` the first time the player connects, or
        ``"reconnect"`` when the player has connected to this room before.
        """
        key = self._key(room_code, player_id)
        sockets = self._sockets.setdefault(key, set())
        sockets.add(websocket)
        if key in self._ever_connected:
            return "reconnect"
        self._ever_connected.add(key)
        return "first"

    def disconnect(self, room_code: str, player_id: str, websocket) -> None:
        """Unregister a single socket. Idempotent."""
        key = self._key(room_code, player_id)
        sockets = self._sockets.get(key)
        if sockets is None:
            return
        sockets.discard(websocket)
        if not sockets:
            self._sockets.pop(key, None)

    async def drop_player_sockets(self, room_code: str, player_id: str) -> None:
        """Close and forget every socket for a player."""
        key = self._key(room_code, player_id)
        sockets = self._sockets.pop(key, set())
        for websocket in sockets:
            try:
                await websocket.close()
            except Exception:
                pass
        self._ever_connected.discard(key)

    async def close_all(self, room_code: str) -> None:
        """Close every socket in a room."""
        room_code = room_code.upper()
        for (code, _player_id), sockets in list(self._sockets.items()):
            if code != room_code:
                continue
            for websocket in list(sockets):
                try:
                    await websocket.close()
                except Exception:
                    pass

    def remove_room(self, room_code: str) -> None:
        """Forget all connection state for a room."""
        room_code = room_code.upper()
        for key in list(self._sockets):
            if key[0] == room_code:
                self._sockets.pop(key, None)
        for key in list(self._ever_connected):
            if key[0] == room_code:
                self._ever_connected.discard(key)

    async def send_to_player(self, room_code: str, player_id: str, payload: dict) -> None:
        text = json.dumps(payload)
        for websocket in self._sockets.get(self._key(room_code, player_id), set()):
            try:
                await websocket.send_text(text)
            except Exception:
                pass

    async def broadcast_room(self, room_code: str, payload: dict) -> None:
        """Send a message to every socket in one room, and only that room."""
        room_code = room_code.upper()
        text = json.dumps(payload)
        for (code, _player_id), sockets in self._sockets.items():
            if code != room_code:
                continue
            for websocket in list(sockets):
                try:
                    await websocket.send_text(text)
                except Exception:
                    pass
