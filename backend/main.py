"""Hand Cricket Online backend.

HTTP + WebSocket API on top of the framework-independent game engine and room
system. Run locally with:

    uvicorn main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from config import MAX_TEAM_SIZE
from game.models import ConnectionStatus
from rooms.errors import RoomError
from rooms.manager import DEFAULT_MAX_PLAYERS, RoomManager
from ws.connections import ConnectionManager
from ws.handler import handle_client_message
from ws.messages import (
    game_state_message,
    room_state_message,
    send_ws,
)

SERVICE_NAME = "hand-cricket-backend"
logger = logging.getLogger("handcricket")


class CreateRoomRequest(BaseModel):
    host_name: str
    max_players: int = Field(default=DEFAULT_MAX_PLAYERS, ge=2, le=2 * MAX_TEAM_SIZE)


class JoinRoomRequest(BaseModel):
    player_name: str


def create_app(
    room_manager: RoomManager | None = None,
    connections: ConnectionManager | None = None,
) -> FastAPI:
    manager = room_manager or RoomManager()
    conn = connections or ConnectionManager()

    app = FastAPI(
        title="Hand Cricket Online",
        description="Private-room multiplayer hand cricket backend.",
        version="0.1.0",
    )

    def _room_error(exc: RoomError) -> HTTPException:
        return HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message": exc.message},
        )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": SERVICE_NAME}

    @app.post("/rooms")
    async def create_room(payload: CreateRoomRequest) -> dict:
        try:
            room, player = await manager.create_room(payload.host_name, payload.max_players)
        except RoomError as exc:
            raise _room_error(exc)
        return {
            "room_code": room.room_code,
            "player_id": player.id,
            "room": room_state_message(room)["room"],
        }

    @app.post("/rooms/{room_code}/join")
    async def join_room(room_code: str, payload: JoinRoomRequest) -> dict:
        try:
            room, player = await manager.join_room(room_code, payload.player_name)
        except RoomError as exc:
            raise _room_error(exc)
        await conn.broadcast_room(room.room_code, {"type": "player_joined", "player_id": player.id})
        await conn.broadcast_room(room.room_code, room_state_message(room))
        return {
            "room_code": room.room_code,
            "player_id": player.id,
            "room": room_state_message(room)["room"],
        }

    @app.get("/rooms/{room_code}")
    async def get_room(room_code: str) -> dict:
        room = manager.get_room(room_code)
        if room is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "ROOM_NOT_FOUND", "message": "Room not found"},
            )
        return {"room_code": room.room_code, "room": room_state_message(room)["room"]}

    @app.websocket("/ws/{room_code}/{player_id}")
    async def websocket_endpoint(websocket: WebSocket, room_code: str, player_id: str) -> None:
        room = manager.get_room(room_code)
        if room is None:
            await websocket.close(code=4404, reason="room_not_found")
            return
        player = room.get_player(player_id)
        if player is None:
            await websocket.close(code=4404, reason="player_not_found")
            return

        await websocket.accept()
        kind = conn.connect(room.room_code, player_id, websocket)
        player.connection_status = ConnectionStatus.CONNECTED
        manager.touch(room)

        await send_ws(websocket, room_state_message(room))
        await send_ws(websocket, game_state_message(room))

        event = "player_reconnected" if kind == "reconnect" else "player_connected"
        await conn.broadcast_room(room.room_code, {"type": event, "player_id": player_id})
        await conn.broadcast_room(room.room_code, room_state_message(room))

        try:
            while True:
                raw = await websocket.receive_text()
                await handle_client_message(websocket, room, player, raw, conn, manager)
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            conn.disconnect(room.room_code, player_id, websocket)
            if not conn.is_player_connected(room.room_code, player_id):
                player.connection_status = ConnectionStatus.DISCONNECTED
                if manager.get_room(room.room_code) is not None:
                    manager.touch(room)
                    await conn.broadcast_room(
                        room.room_code, {"type": "player_disconnected", "player_id": player_id}
                    )
                    await conn.broadcast_room(room.room_code, room_state_message(room))

    return app


app = create_app()
