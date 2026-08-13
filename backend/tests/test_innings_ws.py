"""WebSocket integration tests for the toss + innings lifecycle (Prompt 5).

Covers server-side toss broadcasts, toss decision validation over the wire,
innings 1 completion into the break, second innings start, bowler switching
and both game-over paths (target reached / all out).
"""

import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def create_room(client, host_name="Alice"):
    resp = client.post("/rooms", json={"host_name": host_name})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["room_code"], data["player_id"]


def join_room(client, room_code, name):
    resp = client.post(f"/rooms/{room_code}/join", json={"player_name": name})
    assert resp.status_code == 200, resp.text
    return resp.json()["player_id"]


def drain(ws, count):
    return [ws.receive_json() for _ in range(count)]


def open_ws(client, code, player_id):
    ws = client.websocket_connect(f"/ws/{code}/{player_id}")
    ws.__enter__()
    return ws


def close_ws(*sockets):
    for ws in sockets:
        if ws is not None:
            try:
                ws.__exit__(None, None, None)
            except Exception:
                pass


def start_game(client, code, host_id, guest_id):
    """Start the game via the host and return (winner_team_id, host_ws, guest_ws)."""
    host_ws = open_ws(client, code, host_id)
    drain(host_ws, 4)
    guest_ws = open_ws(client, code, guest_id)
    drain(host_ws, 2)
    drain(guest_ws, 4)
    guest_ws.send_json({"type": "join_team", "team": "B"})
    for ws in (host_ws, guest_ws):
        drain(ws, 2)
    host_ws.send_json({"type": "set_ready", "ready": True})
    guest_ws.send_json({"type": "set_ready", "ready": True})
    for ws in (host_ws, guest_ws):
        drain(ws, 4)
    host_ws.send_json({"type": "start_game"})
    host_msgs = drain(host_ws, 4)
    guest_msgs = drain(guest_ws, 4)
    for msgs in (host_msgs, guest_msgs):
        assert [m["type"] for m in msgs] == [
            "game_started",
            "room_state",
            "toss_result",
            "game_state",
        ]
        assert msgs[2]["winner_team_id"] in ("team-1", "team-2")
        assert msgs[3]["game"]["phase"] == "TOSS_DECISION"
    winner = host_msgs[2]["winner_team_id"]
    return winner, host_ws, guest_ws


def choose_batting(host_ws, guest_ws, winner):
    """Winner chooses to bat; returns the game_state from the host's stream."""
    winner_ws = host_ws if winner == "team-1" else guest_ws
    winner_ws.send_json({"type": "toss_decision", "decision": "BATTING"})
    host_msgs = drain(host_ws, 3)
    guest_msgs = drain(guest_ws, 3)
    for msgs in (host_msgs, guest_msgs):
        assert [m["type"] for m in msgs] == [
            "toss_decision",
            "innings_started",
            "game_state",
        ]
        assert msgs[0]["batting_team_id"] == winner
        assert msgs[1]["innings_number"] == 1
        assert msgs[2]["game"]["phase"] == "INNINGS_1"
    return host_msgs[2]


def get_roles(client, code, host_id, guest_id):
    """Return (winner, host_ws, guest_ws) with the winner batting in innings 1."""
    winner, host_ws, guest_ws = start_game(client, code, host_id, guest_id)
    state = choose_batting(host_ws, guest_ws, winner)
    batter_id = state["game"]["current_batter_id"]
    bowler_id = state["game"]["current_bowler_id"]
    batter_ws = host_ws if batter_id == host_id else guest_ws
    bowler_ws = guest_ws if bowler_id == guest_id else host_ws
    return winner, host_ws, guest_ws, batter_ws, bowler_ws


def finish_innings_one(host_ws, guest_ws, batter_ws, bowler_ws, runs=4, out_move=4):
    """Play innings 1 to completion (runs ball then out). Returns the target."""
    batter_ws.send_json({"type": "submit_batting_move", "move": runs})
    for ws in (batter_ws, bowler_ws):
        msgs = drain(ws, 2)
        assert msgs[0]["type"] == "move_submitted"
        assert msgs[0]["role"] == "batter"
        assert msgs[1]["type"] == "game_state"
    bowler_ws.send_json({"type": "submit_bowling_move", "move": max(runs - 1, 0)})
    for ws in (batter_ws, bowler_ws):
        msgs = drain(ws, 5)
        assert [m["type"] for m in msgs] == [
            "move_submitted",
            "move_result",
            "score_updated",
            "next_turn",
            "game_state",
        ]
        assert msgs[1]["ball"]["runs"] == runs
        assert msgs[2]["score"] == runs
    batter_ws.send_json({"type": "submit_batting_move", "move": out_move})
    for ws in (batter_ws, bowler_ws):
        msgs = drain(ws, 2)
        assert msgs[0]["type"] == "move_submitted"
        assert msgs[1]["type"] == "game_state"
    bowler_ws.send_json({"type": "submit_bowling_move", "move": out_move})
    for ws in (host_ws, guest_ws):
        msgs = drain(ws, 6)
        assert [m["type"] for m in msgs] == [
            "move_submitted",
            "move_result",
            "player_out",
            "innings_complete",
            "innings_break",
            "game_state",
        ]
        assert msgs[2]["wickets"] == 1
        assert msgs[4]["target"] == runs + 1
    return runs + 1


def begin_second_innings(host_ws, guest_ws, target):
    """Host starts innings 2; returns the game_state from the host's stream."""
    host_ws.send_json({"type": "begin_second_innings"})
    host_msgs = drain(host_ws, 2)
    guest_msgs = drain(guest_ws, 2)
    for msgs in (host_msgs, guest_msgs):
        assert [m["type"] for m in msgs] == [
            "second_innings_started",
            "game_state",
        ]
        assert msgs[0]["innings_number"] == 2
        assert msgs[0]["target"] == target
        assert msgs[1]["game"]["phase"] == "INNINGS_2"
    return host_msgs[1]


class TestTossEvents:
    def test_start_game_broadcasts_toss_result(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws = start_game(client, code, host_id, guest_id)
        assert winner in ("team-1", "team-2")
        close_ws(host_ws, guest_ws)

    def test_toss_decision_broadcasts_events(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws = start_game(client, code, host_id, guest_id)
        state = choose_batting(host_ws, guest_ws, winner)
        assert state["game"]["current_innings"]["score"] == 0
        assert state["game"]["current_innings"]["target"] is None
        close_ws(host_ws, guest_ws)

    def test_losing_team_cannot_choose(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws = start_game(client, code, host_id, guest_id)
        loser_ws = guest_ws if winner == "team-1" else host_ws
        loser_ws.send_json({"type": "toss_decision", "decision": "BATTING"})
        msg = loser_ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "illegal_action"
        close_ws(host_ws, guest_ws)

    def test_invalid_decision_rejected(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws = start_game(client, code, host_id, guest_id)
        winner_ws = host_ws if winner == "team-1" else guest_ws
        winner_ws.send_json({"type": "toss_decision", "decision": "SWIM"})
        msg = winner_ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "invalid_move"
        close_ws(host_ws, guest_ws)

    def test_duplicate_decision_rejected(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws = start_game(client, code, host_id, guest_id)
        winner_ws = host_ws if winner == "team-1" else guest_ws
        winner_ws.send_json({"type": "toss_decision", "decision": "BATTING"})
        drain(host_ws, 3)
        drain(guest_ws, 3)
        winner_ws.send_json({"type": "toss_decision", "decision": "BOWLING"})
        msg = winner_ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "illegal_action"
        close_ws(host_ws, guest_ws)

    def test_unauthorized_player_cannot_choose(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws = start_game(client, code, host_id, guest_id)
        winner_ws = host_ws if winner == "team-1" else guest_ws
        loser_ws = guest_ws if winner == "team-1" else host_ws
        winner_ws.send_json({"type": "toss_decision", "decision": "BATTING"})
        drain(host_ws, 3)
        drain(guest_ws, 3)
        loser_ws.send_json({"type": "toss_decision", "decision": "BOWLING"})
        msg = loser_ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "illegal_action"
        close_ws(host_ws, guest_ws)


class TestInningsEvents:
    def test_innings_one_out_broadcasts_complete_and_break(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws, batter_ws, bowler_ws = get_roles(
            client, code, host_id, guest_id
        )
        batter_ws.send_json({"type": "submit_move", "move": 4})
        for ws in (batter_ws, bowler_ws):
            drain(ws, 1)
        bowler_ws.send_json({"type": "submit_move", "move": 4})
        for ws in (host_ws, guest_ws):
            msgs = drain(ws, 4)
            assert [m["type"] for m in msgs] == [
                "move_result",
                "innings_complete",
                "innings_break",
                "game_state",
            ]
            assert msgs[2]["target"] == 1
            assert msgs[3]["game"]["phase"] == "INNINGS_BREAK"
        close_ws(host_ws, guest_ws)


class TestSecondInnings:
    def test_host_begins_second_innings(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws, batter_ws, bowler_ws = get_roles(
            client, code, host_id, guest_id
        )
        target = finish_innings_one(host_ws, guest_ws, batter_ws, bowler_ws, runs=4)
        state = begin_second_innings(host_ws, guest_ws, target)
        assert state["game"]["current_innings"]["target"] == target
        assert state["game"]["current_innings"]["score"] == 0
        assert state["game"]["current_innings"]["wickets"] == 0
        close_ws(host_ws, guest_ws)

    def test_non_host_cannot_begin_second_innings(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws, batter_ws, bowler_ws = get_roles(
            client, code, host_id, guest_id
        )
        finish_innings_one(host_ws, guest_ws, batter_ws, bowler_ws, runs=4)
        guest_ws.send_json({"type": "begin_second_innings"})
        msg = guest_ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "NOT_HOST"
        close_ws(host_ws, guest_ws)


class TestBowlerSwitch:
    def test_switch_bowler_broadcasts(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws = start_game(client, code, host_id, guest_id)
        state = choose_batting(host_ws, guest_ws, winner)
        bowler_id = state["game"]["current_bowler_id"]
        bowler_ws = guest_ws if bowler_id == guest_id else host_ws
        bowler_ws.send_json({"type": "switch_bowler"})
        for ws in (host_ws, guest_ws):
            msgs = drain(ws, 2)
            assert msgs[0]["type"] == "bowler_switch"
            assert msgs[0]["new_bowler_id"]
            assert msgs[1]["type"] == "game_state"
        close_ws(host_ws, guest_ws)

    def test_batting_player_cannot_switch(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws, batter_ws, bowler_ws = get_roles(
            client, code, host_id, guest_id
        )
        batter_ws.send_json({"type": "switch_bowler"})
        msg = batter_ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "illegal_action"
        close_ws(host_ws, guest_ws)

    def test_switch_after_move_submitted_rejected(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws, batter_ws, bowler_ws = get_roles(
            client, code, host_id, guest_id
        )
        batter_ws.send_json({"type": "submit_move", "move": 4})
        for ws in (batter_ws, bowler_ws):
            drain(ws, 1)
        bowler_ws.send_json({"type": "switch_bowler"})
        msg = bowler_ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "illegal_action"
        close_ws(host_ws, guest_ws)


class TestGameOver:
    def test_target_reached_wins_chase(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws, batter_ws, bowler_ws = get_roles(
            client, code, host_id, guest_id
        )
        target = finish_innings_one(host_ws, guest_ws, batter_ws, bowler_ws, runs=4)
        begin_second_innings(host_ws, guest_ws, target)

        chaser_id = guest_id if winner == "team-1" else host_id
        chaser_ws = guest_ws if chaser_id == guest_id else host_ws
        bowler2_id = host_id if winner == "team-1" else guest_id
        bowler2_ws = host_ws if bowler2_id == host_id else guest_ws

        chaser_ws.send_json({"type": "submit_move", "move": target})
        for ws in (chaser_ws, bowler2_ws):
            drain(ws, 1)
        bowler2_ws.send_json({"type": "submit_move", "move": 0})
        for ws in (host_ws, guest_ws):
            msgs = drain(ws, 3)
            assert [m["type"] for m in msgs] == [
                "move_result",
                "game_over",
                "game_state",
            ]
            assert msgs[1]["reason"] == "TARGET_REACHED"
            assert msgs[1]["winner_team_id"] == (
                "team-2" if winner == "team-1" else "team-1"
            )
            assert msgs[1]["target"] == target
            assert msgs[2]["game"]["phase"] == "GAME_OVER"
        close_ws(host_ws, guest_ws)

    def test_all_out_gives_first_innings_team_the_win(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws, batter_ws, bowler_ws = get_roles(
            client, code, host_id, guest_id
        )
        target = finish_innings_one(host_ws, guest_ws, batter_ws, bowler_ws, runs=4)
        begin_second_innings(host_ws, guest_ws, target)

        chaser_id = guest_id if winner == "team-1" else host_id
        chaser_ws = guest_ws if chaser_id == guest_id else host_ws
        bowler2_id = host_id if winner == "team-1" else guest_id
        bowler2_ws = host_ws if bowler2_id == host_id else guest_ws

        chaser_ws.send_json({"type": "submit_move", "move": 6})
        for ws in (chaser_ws, bowler2_ws):
            drain(ws, 1)
        bowler2_ws.send_json({"type": "submit_move", "move": 6})
        for ws in (host_ws, guest_ws):
            msgs = drain(ws, 3)
            assert [m["type"] for m in msgs] == [
                "move_result",
                "game_over",
                "game_state",
            ]
            assert msgs[1]["reason"] == "ALL_OUT"
            assert msgs[1]["winner_team_id"] == winner
            assert msgs[2]["game"]["phase"] == "GAME_OVER"
        close_ws(host_ws, guest_ws)

    def test_game_over_blocks_further_moves(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        winner, host_ws, guest_ws, batter_ws, bowler_ws = get_roles(
            client, code, host_id, guest_id
        )
        target = finish_innings_one(host_ws, guest_ws, batter_ws, bowler_ws, runs=4)
        begin_second_innings(host_ws, guest_ws, target)

        chaser_id = guest_id if winner == "team-1" else host_id
        chaser_ws = guest_ws if chaser_id == guest_id else host_ws
        bowler2_id = host_id if winner == "team-1" else guest_id
        bowler2_ws = host_ws if bowler2_id == host_id else guest_ws

        chaser_ws.send_json({"type": "submit_move", "move": 6})
        for ws in (chaser_ws, bowler2_ws):
            drain(ws, 1)
        bowler2_ws.send_json({"type": "submit_move", "move": 6})
        for ws in (host_ws, guest_ws):
            drain(ws, 3)
        chaser_ws.send_json({"type": "submit_move", "move": 1})
        msg = chaser_ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "illegal_action"
        close_ws(host_ws, guest_ws)
