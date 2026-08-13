"""Server-to-client message builders and broadcast helpers."""

from __future__ import annotations

import json

from config import MAX_TEAM_SIZE
from game.state import TEAM_1_ID, TEAM_2_ID


def player_dict(player) -> dict:
    return {
        "id": player.id,
        "name": player.name,
        "team_id": player.team_id,
        "connection_status": player.connection_status.value,
        "ready_status": player.ready_status.value,
        "batting_position": player.batting_position,
    }


def team_section(room, team_id: str, label: str, capacity: int) -> dict:
    team = room.engine.state.teams[team_id]
    return {
        "team_id": team_id,
        "name": label,
        "capacity": capacity,
        "player_count": len(team.players),
        "players": [player_dict(p) for p in team.players],
    }


def room_snapshot(room) -> dict:
    return {
        "room_code": room.room_code,
        "host_player_id": room.host_player_id,
        "status": room.status.value,
        "max_players": room.max_players,
        "phase": room.engine.state.phase.value,
        "team_a_size": room.team_a_size,
        "team_b_size": room.team_b_size,
        "max_team_size": MAX_TEAM_SIZE,
        "team_a": team_section(room, TEAM_1_ID, "Team A", room.team_a_size),
        "team_b": team_section(room, TEAM_2_ID, "Team B", room.team_b_size),
        "players": [player_dict(p) for p in room.engine.state.players.values()],
        "can_start": room.can_start,
        "created_at": room.created_at.isoformat(),
        "last_activity": room.last_activity.isoformat(),
    }


def room_state_message(room) -> dict:
    return {"type": "room_state", "room": room_snapshot(room)}


def game_state_message(room) -> dict:
    game = room.engine.state.model_dump(mode="json")
    # Anti-cheat: never expose either player's submitted move before the ball
    # is resolved. Moves are revealed only via move_result after both submit.
    game["batter_move"] = None
    game["bowler_move"] = None
    return {"type": "game_state", "game": game}


def move_submitted_message(player_id: str, role: str) -> dict:
    """A batter/bowler move was stored. Never carries the move value."""
    return {"type": "move_submitted", "player_id": player_id, "role": role}


def player_out_message(room) -> dict:
    state = room.engine.state
    innings = state.current_innings
    return {
        "type": "player_out",
        "player_id": state.last_ball.batter_id if state.last_ball else None,
        "team_id": state.batting_team_id,
        "innings_number": innings.number if innings else None,
        "wickets": innings.wickets if innings else None,
    }


def score_updated_message(room) -> dict:
    state = room.engine.state
    innings = state.current_innings
    return {
        "type": "score_updated",
        "score": innings.score if innings else None,
        "wickets": innings.wickets if innings else None,
        "innings_number": innings.number if innings else None,
        "batting_team_id": state.batting_team_id,
        "target": state.target_score,
    }


def next_turn_message(room) -> dict:
    state = room.engine.state
    return {
        "type": "next_turn",
        "innings_number": state.innings_number,
        "current_batter_id": state.current_batter_id,
        "current_bowler_id": state.current_bowler_id,
        "turn_state": state.turn_state.value if state.turn_state else None,
    }


def toss_decision_message(room) -> dict:
    state = room.engine.state
    return {
        "type": "toss_decision",
        "decision": state.toss_decision.value if state.toss_decision else None,
        "batting_team_id": state.batting_team_id,
        "bowling_team_id": state.bowling_team_id,
    }


def innings_started_message(room) -> dict:
    state = room.engine.state
    return {
        "type": "innings_started",
        "innings_number": state.innings_number,
        "batting_team_id": state.batting_team_id,
        "bowling_team_id": state.bowling_team_id,
        "current_batter_id": state.current_batter_id,
        "current_bowler_id": state.current_bowler_id,
    }


def innings_complete_message(room) -> dict:
    state = room.engine.state
    innings = state.current_innings
    return {
        "type": "innings_complete",
        "innings_number": state.innings_number,
        "score": innings.score if innings else None,
        "wickets": innings.wickets if innings else None,
        "batting_team_id": state.batting_team_id,
        "bowling_team_id": state.bowling_team_id,
        "target": state.target_score,
    }


def innings_break_message(room) -> dict:
    state = room.engine.state
    return {
        "type": "innings_break",
        "target": state.target_score,
        "batting_team_id": state.batting_team_id,
        "bowling_team_id": state.bowling_team_id,
    }


def second_innings_started_message(room) -> dict:
    state = room.engine.state
    return {
        "type": "second_innings_started",
        "innings_number": 2,
        "batting_team_id": state.batting_team_id,
        "bowling_team_id": state.bowling_team_id,
        "current_batter_id": state.current_batter_id,
        "current_bowler_id": state.current_bowler_id,
        "target": state.target_score,
    }


def bowler_changed_message(room) -> dict:
    state = room.engine.state
    return {
        "type": "bowler_changed",
        "new_bowler_id": state.current_bowler_id,
        "bowler_team_id": state.bowling_team_id,
    }


def game_over_message(room) -> dict:
    state = room.engine.state
    return {
        "type": "game_over",
        "result": state.result.value,
        "winner_team_id": state.winner_team_id,
        "reason": state.game_over_reason,
        "target": state.target_score,
        "team_a_score": state.teams[TEAM_1_ID].score,
        "team_b_score": state.teams[TEAM_2_ID].score,
    }


def error_message(code: str, message: str) -> dict:
    return {"type": "error", "code": code, "message": message}


async def send_ws(websocket, payload: dict) -> None:
    await websocket.send_text(json.dumps(payload))


async def broadcast_room_state(connections, room) -> None:
    await connections.broadcast_room(room.room_code, room_state_message(room))


async def broadcast_game_state(connections, room) -> None:
    await connections.broadcast_room(room.room_code, game_state_message(room))
