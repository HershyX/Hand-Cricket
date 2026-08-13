"""Client-to-server WebSocket message routing and handlers.

Every inbound message is dispatched by ``type``. Handlers mutate game state
only through the GameEngine and the room manager, which validate phase,
player identity, role, team capacity, readiness and move legality. Broadcasts
always carry the resulting authoritative state, and the room snapshot reports
the canonical lobby info (team sizes, membership, readiness, can_start) for
the frontend to render.
"""

from __future__ import annotations

import json
import logging

from game.engine import EngineError
from game.models import BallOutcome, GamePhase, TossDecision, TurnState
from game.rules import IllegalMoveError
from rooms.errors import RoomError
from rooms.manager import RoomStatus
from ws.messages import (
    bowler_changed_message,
    broadcast_room_state,
    error_message,
    game_over_message,
    game_state_message,
    innings_break_message,
    innings_complete_message,
    innings_started_message,
    move_submitted_message,
    next_turn_message,
    player_out_message,
    score_updated_message,
    second_innings_started_message,
    send_ws,
    toss_decision_message,
)

logger = logging.getLogger("handcricket.ws")


def _require_host(room, player) -> None:
    if player.id != room.host_player_id:
        raise RoomError("NOT_HOST", "Only the host can perform this action", 403)


async def handle_client_message(websocket, room, player, raw: str, connections, manager) -> None:
    """Parse one raw message and route it, or reply with a structured error."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        await send_ws(websocket, error_message("invalid_json", "Malformed JSON message"))
        return

    if not isinstance(data, dict):
        await send_ws(websocket, error_message("invalid_message", "Message must be a JSON object"))
        return

    handler = MESSAGE_HANDLERS.get(data.get("type"))
    if handler is None:
        await send_ws(
            websocket,
            error_message("unknown_type", f"Unknown message type: {data.get('type')!r}"),
        )
        return

    try:
        await handler(websocket, room, player, data, connections, manager)
    except IllegalMoveError as exc:
        await send_ws(websocket, error_message("invalid_move", str(exc)))
    except EngineError as exc:
        await send_ws(websocket, error_message("illegal_action", str(exc)))
    except RoomError as exc:
        await send_ws(websocket, error_message(exc.code, str(exc)))
    except Exception:
        logger.exception("Unhandled error while processing %s", data.get("type"))
        await send_ws(websocket, error_message("internal_error", "Internal server error"))


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------


async def _set_ready(websocket, room, player, data, connections, manager) -> None:
    if room.engine.state.phase != GamePhase.LOBBY:
        raise EngineError("Cannot change ready status after the game has started")
    if "ready" in data and not isinstance(data["ready"], bool):
        raise RoomError("INVALID_READY", "ready must be a boolean", 400)
    ready = data.get("ready", True)
    if ready:
        room.engine.set_ready(player.id)
    else:
        room.engine.unset_ready(player.id)
    manager.touch(room)
    await connections.broadcast_room(
        room.room_code, {"type": "player_ready", "player_id": player.id, "ready": ready}
    )
    await broadcast_room_state(connections, room)


async def _set_team_sizes(websocket, room, player, data, connections, manager) -> None:
    _require_host(room, player)
    manager.set_team_sizes(room, data.get("team_a_size"), data.get("team_b_size"))
    await connections.broadcast_room(
        room.room_code,
        {
            "type": "team_sizes_updated",
            "team_a_size": room.team_a_size,
            "team_b_size": room.team_b_size,
        },
    )
    await broadcast_room_state(connections, room)


async def _join_team(websocket, room, player, data, connections, manager) -> None:
    manager.join_team(room, player.id, data.get("team"))
    await connections.broadcast_room(
        room.room_code,
        {
            "type": "player_team_changed",
            "player_id": player.id,
            "team_id": player.team_id,
            "team": manager.team_id_to_key(player.team_id) if player.team_id else None,
        },
    )
    await broadcast_room_state(connections, room)


async def _leave_team(websocket, room, player, data, connections, manager) -> None:
    manager.leave_team(room, player.id)
    await connections.broadcast_room(
        room.room_code,
        {"type": "player_team_changed", "player_id": player.id, "team_id": None, "team": None},
    )
    await broadcast_room_state(connections, room)


async def _start_game(websocket, room, player, data, connections, manager) -> None:
    _require_host(room, player)
    if room.status != RoomStatus.WAITING:
        raise EngineError("The game has already started")
    problems = room.validate_start()
    if problems:
        raise RoomError("LOBBY_NOT_READY", " ".join(problems), 409)
    room.engine.start_toss()
    winner = room.engine.perform_toss()
    room.status = RoomStatus.IN_PROGRESS
    manager.touch(room)
    await connections.broadcast_room(room.room_code, {"type": "game_started"})
    await broadcast_room_state(connections, room)
    await connections.broadcast_room(
        room.room_code, {"type": "toss_result", "winner_team_id": winner}
    )
    await connections.broadcast_room(room.room_code, game_state_message(room))


async def _reset_lobby(websocket, room, player, data, connections, manager) -> None:
    _require_host(room, player)
    manager.reset_lobby(room)
    await connections.broadcast_room(room.room_code, {"type": "lobby_reset"})
    await broadcast_room_state(connections, room)
    await connections.broadcast_room(room.room_code, game_state_message(room))


async def _submit_toss(websocket, room, player, data, connections, manager) -> None:
    room.engine.submit_toss(player.id, data.get("move"))
    manager.touch(room)
    if set(room.engine.state.toss_numbers) == set(room.engine.state.team_order):
        winner = room.engine.resolve_toss()
        await connections.broadcast_room(
            room.room_code, {"type": "toss_result", "winner_team_id": winner}
        )
    await connections.broadcast_room(room.room_code, game_state_message(room))


async def _toss_decision(websocket, room, player, data, connections, manager) -> None:
    if room.engine.state.phase != GamePhase.TOSS_DECISION:
        raise EngineError("No toss decision is pending")
    if player.team_id != room.engine.state.toss_winner_id:
        raise EngineError("Only the toss-winning team can choose")
    raw = data.get("decision")
    try:
        decision = TossDecision(raw)
    except ValueError:
        raise IllegalMoveError(f"Invalid toss decision: {raw!r}")
    room.engine.set_toss_decision(decision)
    manager.touch(room)
    await connections.broadcast_room(room.room_code, toss_decision_message(room))
    await connections.broadcast_room(room.room_code, innings_started_message(room))
    await connections.broadcast_room(room.room_code, game_state_message(room))


async def _submit_move(websocket, room, player, data, connections, manager) -> None:
    state = room.engine.state
    if player.id not in (state.current_batter_id, state.current_bowler_id):
        raise EngineError("Player is neither the current batter nor bowler")
    role = "batter" if player.id == state.current_batter_id else "bowler"
    await _apply_submit_and_broadcast(
        room, player, role, data.get("move"), connections, manager
    )


async def _submit_batting_move(websocket, room, player, data, connections, manager) -> None:
    if player.id != room.engine.state.current_batter_id:
        raise EngineError("Only the current batter may submit a batting move")
    await _apply_submit_and_broadcast(
        room, player, "batter", data.get("move"), connections, manager
    )


async def _submit_bowling_move(websocket, room, player, data, connections, manager) -> None:
    if player.id != room.engine.state.current_bowler_id:
        raise EngineError("Only the current bowler may submit a bowling move")
    await _apply_submit_and_broadcast(
        room, player, "bowler", data.get("move"), connections, manager
    )


async def _apply_submit_and_broadcast(room, player, role, move, connections, manager) -> None:
    state = room.engine.state
    bowler_before = state.current_bowler_id
    room.engine.submit_move(player.id, move)
    if state.turn_state == TurnState.PLAYER_OUT:
        room.engine.advance_batter()
    manager.touch(room)
    resolved = not (state.batter_submitted or state.bowler_submitted)

    await connections.broadcast_room(
        room.room_code, move_submitted_message(player.id, role)
    )
    if resolved:
        ball = state.last_ball
        await connections.broadcast_room(
            room.room_code,
            {"type": "move_result", "ball": ball.model_dump(mode="json") if ball else None},
        )
        if ball is not None and ball.outcome == BallOutcome.OUT:
            await connections.broadcast_room(room.room_code, player_out_message(room))
        elif ball is not None and ball.runs > 0:
            await connections.broadcast_room(room.room_code, score_updated_message(room))

        if state.phase == GamePhase.INNINGS_BREAK:
            await connections.broadcast_room(room.room_code, innings_complete_message(room))
            await connections.broadcast_room(room.room_code, innings_break_message(room))
        elif state.phase == GamePhase.GAME_OVER:
            await connections.broadcast_room(room.room_code, game_over_message(room))
        else:
            if state.current_bowler_id != bowler_before:
                await connections.broadcast_room(room.room_code, bowler_changed_message(room))
            await connections.broadcast_room(room.room_code, next_turn_message(room))
    await connections.broadcast_room(room.room_code, game_state_message(room))


async def _switch_bowler(websocket, room, player, data, connections, manager) -> None:
    room.engine.switch_bowler(player.id)
    manager.touch(room)
    await connections.broadcast_room(room.room_code, bowler_changed_message(room))
    await connections.broadcast_room(room.room_code, game_state_message(room))


async def _begin_second_innings(websocket, room, player, data, connections, manager) -> None:
    _require_host(room, player)
    room.engine.begin_second_innings()
    manager.touch(room)
    await connections.broadcast_room(room.room_code, second_innings_started_message(room))
    await connections.broadcast_room(room.room_code, game_state_message(room))


async def _leave_room(websocket, room, player, data, connections, manager) -> None:
    if player.id == room.host_player_id:
        await connections.broadcast_room(room.room_code, {"type": "room_closed"})
        await connections.close_all(room.room_code)
        connections.remove_room(room.room_code)
        manager.remove_room(room.room_code)
        return
    room.engine.remove_player(player.id)
    await connections.drop_player_sockets(room.room_code, player.id)
    manager.touch(room)
    await connections.broadcast_room(room.room_code, {"type": "player_left", "player_id": player.id})
    await broadcast_room_state(connections, room)


async def _ping(websocket, room, player, data, connections, manager) -> None:
    await send_ws(websocket, {"type": "pong"})


MESSAGE_HANDLERS = {
    "set_team_sizes": _set_team_sizes,
    "join_team": _join_team,
    "leave_team": _leave_team,
    "set_ready": _set_ready,
    "player_ready": _set_ready,
    "start_game": _start_game,
    "reset_lobby": _reset_lobby,
    "submit_toss": _submit_toss,
    "toss_decision": _toss_decision,
    "submit_move": _submit_move,
    "submit_batting_move": _submit_batting_move,
    "submit_bowling_move": _submit_bowling_move,
    "switch_bowler": _switch_bowler,
    "request_bowler_switch": _switch_bowler,
    "begin_second_innings": _begin_second_innings,
    "leave_room": _leave_room,
    "ping": _ping,
}
