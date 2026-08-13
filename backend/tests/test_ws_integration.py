"""Integration tests for HTTP room endpoints and WebSocket synchronization."""

import pytest
from fastapi.testclient import TestClient

from main import create_app


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def create_room(client, host_name="Alice", max_players=None):
    payload = {"host_name": host_name}
    if max_players is not None:
        payload["max_players"] = max_players
    resp = client.post("/rooms", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    return data["room_code"], data["player_id"]


def join_room(client, room_code, name):
    resp = client.post(f"/rooms/{room_code}/join", json={"player_name": name})
    assert resp.status_code == 200, resp.text
    return resp.json()["player_id"]


def drain(ws, count):
    return [ws.receive_json() for _ in range(count)]


class TestHttpRoomEndpoints:
    def test_create_room(self, client):
        code, pid = create_room(client, "Alice")
        assert len(code) == 6
        assert code.isalnum() and code.isupper()
        assert pid
        room = client.get(f"/rooms/{code}").json()["room"]
        assert room["players"][0]["name"] == "Alice"

    def test_join_room(self, client):
        code, _ = create_room(client, "Alice")
        pid = join_room(client, code, "Bob")
        assert pid
        room = client.get(f"/rooms/{code}").json()["room"]
        assert len(room["players"]) == 2

    def test_multiple_players_join_same_room(self, client):
        code, _ = create_room(client, "Alice")
        for name in ("Bob", "Carol", "Dave"):
            join_room(client, code, name)
        room = client.get(f"/rooms/{code}").json()["room"]
        assert len(room["players"]) == 4

    def test_join_invalid_room_code(self, client):
        resp = client.post("/rooms/ZZZZZZ/join", json={"player_name": "Bob"})
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "ROOM_NOT_FOUND"

    def test_get_missing_room(self, client):
        assert client.get("/rooms/ZZZZZZ").status_code == 404

    def test_join_duplicate_name_rejected(self, client):
        code, _ = create_room(client, "Alice")
        resp = client.post(f"/rooms/{code}/join", json={"player_name": "ALICE"})
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "DUPLICATE_PLAYER"

    def test_join_full_room_rejected(self, client):
        code, _ = create_room(client, "Alice", max_players=2)
        join_room(client, code, "Bob")
        resp = client.post(f"/rooms/{code}/join", json={"player_name": "Carol"})
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "ROOM_FULL"

    def test_room_codes_are_not_predictable(self, client):
        codes = {create_room(client, f"Host{i}")[0] for i in range(10)}
        assert len(codes) == 10


class TestRoomIsolationOverHttp:
    def test_rooms_do_not_leak_players(self, client):
        code_a, _ = create_room(client, "Alice")
        code_b, _ = create_room(client, "Bob")
        join_room(client, code_a, "Carol")
        room_a = client.get(f"/rooms/{code_a}").json()["room"]
        room_b = client.get(f"/rooms/{code_b}").json()["room"]
        assert [p["name"] for p in room_a["players"]] == ["Alice", "Carol"]
        assert [p["name"] for p in room_b["players"]] == ["Bob"]


class TestWebSocket:
    def test_connect_sends_initial_state(self, client):
        code, pid = create_room(client, "Alice")
        with client.websocket_connect(f"/ws/{code}/{pid}") as ws:
            msgs = drain(ws, 4)
            assert msgs[0]["type"] == "room_state"
            assert msgs[0]["room"]["room_code"] == code
            assert msgs[1]["type"] == "game_state"
            assert msgs[2]["type"] == "player_connected"
            assert msgs[3]["type"] == "room_state"

    def test_connect_unknown_room_rejected(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/ZZZZZZ/nope") as ws:
                ws.receive_json()

    def test_connect_unknown_player_rejected(self, client):
        code, _ = create_room(client, "Alice")
        with pytest.raises(Exception):
            with client.websocket_connect(f"/ws/{code}/unknown") as ws:
                ws.receive_json()

    def test_disconnect_broadcasts_status(self, client):
        code, host_id = create_room(client, "Alice")
        guest_id = join_room(client, code, "Bob")

        with client.websocket_connect(f"/ws/{code}/{host_id}") as host_ws:
            drain(host_ws, 4)
            with client.websocket_connect(f"/ws/{code}/{guest_id}") as guest_ws:
                host_extra = drain(host_ws, 2)
                assert host_extra[0]["type"] == "player_connected"
                assert host_extra[0]["player_id"] == guest_id
                drain(guest_ws, 4)
            # guest socket closed -> host sees the disconnect
            msgs = drain(host_ws, 2)
            assert msgs[0]["type"] == "player_disconnected"
            assert msgs[0]["player_id"] == guest_id
            assert msgs[1]["type"] == "room_state"

    def test_reconnect_broadcasts_status(self, client):
        code, host_id = create_room(client, "Alice")
        guest_id = join_room(client, code, "Bob")

        with client.websocket_connect(f"/ws/{code}/{guest_id}") as guest_ws:
            drain(guest_ws, 4)
        # guest is now disconnected; host connects
        with client.websocket_connect(f"/ws/{code}/{host_id}") as host_ws:
            drain(host_ws, 4)
            # guest reconnects
            with client.websocket_connect(f"/ws/{code}/{guest_id}") as guest_ws2:
                msgs = drain(guest_ws2, 4)
                assert msgs[0]["type"] == "room_state"
                assert msgs[1]["type"] == "game_state"
                assert msgs[2]["type"] == "player_reconnected"
                assert msgs[2]["player_id"] == guest_id
                assert msgs[3]["type"] == "room_state"
                host_msgs = drain(host_ws, 2)
                assert host_msgs[0]["type"] == "player_reconnected"
                assert host_msgs[0]["player_id"] == guest_id

    def test_invalid_websocket_action(self, client):
        code, pid = create_room(client, "Alice")
        with client.websocket_connect(f"/ws/{code}/{pid}") as ws:
            drain(ws, 4)
            ws.send_json({"type": "no_such_event"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "unknown_type"

    def test_malformed_json(self, client):
        code, pid = create_room(client, "Alice")
        with client.websocket_connect(f"/ws/{code}/{pid}") as ws:
            drain(ws, 4)
            ws.send_text("{definitely not json")
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "invalid_json"

    def test_non_object_message(self, client):
        code, pid = create_room(client, "Alice")
        with client.websocket_connect(f"/ws/{code}/{pid}") as ws:
            drain(ws, 4)
            ws.send_json([1, 2, 3])
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "invalid_message"

    def test_unauthorized_action_non_host_start(self, client):
        code, host_id = create_room(client, "Alice")
        guest_id = join_room(client, code, "Bob")
        with client.websocket_connect(f"/ws/{code}/{host_id}") as host_ws:
            drain(host_ws, 4)
            with client.websocket_connect(f"/ws/{code}/{guest_id}") as guest_ws:
                host_extra = drain(host_ws, 2)
                assert host_extra[0]["type"] == "player_connected"
                drain(guest_ws, 4)
                guest_ws.send_json({"type": "start_game"})
                msg = guest_ws.receive_json()
                assert msg["type"] == "error"
                assert msg["code"] == "NOT_HOST"


class TestFullFlow:
    def test_full_game_flow_over_websocket(self, client):
        code, host_id = create_room(client, "Alice")
        guest_id = join_room(client, code, "Bob")

        with client.websocket_connect(f"/ws/{code}/{host_id}") as host_ws:
            with client.websocket_connect(f"/ws/{code}/{guest_id}") as guest_ws:
                drain(host_ws, 6)
                drain(guest_ws, 4)

                # guest joins Team B; the host is already on Team A
                guest_ws.send_json({"type": "join_team", "team": "B"})
                for ws in (host_ws, guest_ws):
                    msgs = drain(ws, 2)
                    assert msgs[0]["type"] == "player_team_changed"
                    assert msgs[0]["team"] == "B"
                    assert msgs[0]["player_id"] == guest_id
                    assert msgs[1]["type"] == "room_state"
                    assert msgs[1]["room"]["team_b"]["player_count"] == 1

                # both ready
                host_ws.send_json({"type": "set_ready", "ready": True})
                guest_ws.send_json({"type": "set_ready", "ready": True})
                for ws in (host_ws, guest_ws):
                    types = [m["type"] for m in drain(ws, 4)]
                    assert types == ["player_ready", "room_state", "player_ready", "room_state"]

                # host starts the game -> server performs the toss
                host_ws.send_json({"type": "start_game"})
                for ws in (host_ws, guest_ws):
                    msgs = drain(ws, 4)
                    assert [m["type"] for m in msgs] == [
                        "game_started",
                        "room_state",
                        "toss_result",
                        "game_state",
                    ]
                    assert msgs[2]["winner_team_id"] in ("team-1", "team-2")
                    assert msgs[3]["game"]["phase"] == "TOSS_DECISION"
                winner = msgs[2]["winner_team_id"]
                winner_ws = host_ws if winner == "team-1" else guest_ws

                # toss winner chooses to bat
                winner_ws.send_json({"type": "toss_decision", "decision": "BATTING"})
                for ws in (host_ws, guest_ws):
                    msgs = drain(ws, 3)
                    assert [m["type"] for m in msgs] == [
                        "toss_decision",
                        "innings_started",
                        "game_state",
                    ]
                    assert msgs[2]["game"]["phase"] == "INNINGS_1"
                batter_id = msgs[2]["game"]["current_batter_id"]
                bowler_id = msgs[2]["game"]["current_bowler_id"]
                batter_ws = host_ws if batter_id == host_id else guest_ws
                bowler_ws = guest_ws if batter_id == host_id else host_ws

                # invalid move value is rejected
                batter_ws.send_json({"type": "submit_batting_move", "move": 99})
                msg = batter_ws.receive_json()
                assert msg["type"] == "error"
                assert msg["code"] == "invalid_move"

                # batter submits; not yet resolved
                batter_ws.send_json({"type": "submit_batting_move", "move": 4})
                for ws in (batter_ws, bowler_ws):
                    msgs = drain(ws, 2)
                    assert msgs[0]["type"] == "move_submitted"
                    assert msgs[0]["player_id"] == batter_id
                    assert msgs[0]["role"] == "batter"
                    assert msgs[1]["type"] == "game_state"
                    assert msgs[1]["game"]["batter_submitted"] is True
                    # anti-cheat: the batter's move is never exposed in game_state
                    assert msgs[1]["game"]["batter_move"] is None

                # double submission by the batter is rejected
                batter_ws.send_json({"type": "submit_batting_move", "move": 5})
                msg = batter_ws.receive_json()
                assert msg["type"] == "error"
                assert msg["code"] == "illegal_action"

                # bowler submits -> resolved: 4 runs
                bowler_ws.send_json({"type": "submit_bowling_move", "move": 3})
                for ws in (batter_ws, bowler_ws):
                    msgs = drain(ws, 5)
                    assert msgs[0]["type"] == "move_submitted"
                    assert msgs[0]["role"] == "bowler"
                    assert msgs[1]["type"] == "move_result"
                    assert msgs[1]["ball"]["runs"] == 4
                    assert msgs[1]["ball"]["outcome"] == "RUNS"
                    assert msgs[1]["ball"]["batter_move"] == 4
                    assert msgs[1]["ball"]["bowler_move"] == 3
                    assert msgs[2]["type"] == "score_updated"
                    assert msgs[2]["score"] == 4
                    assert msgs[3]["type"] == "next_turn"
                    assert msgs[4]["type"] == "game_state"
                    assert msgs[4]["game"]["current_innings"]["score"] == 4


class TestLeaveRoom:
    def test_guest_can_leave_room(self, client):
        code, host_id = create_room(client, "Alice")
        guest_id = join_room(client, code, "Bob")
        with client.websocket_connect(f"/ws/{code}/{host_id}") as host_ws:
            drain(host_ws, 4)
            with client.websocket_connect(f"/ws/{code}/{guest_id}") as guest_ws:
                host_extra = drain(host_ws, 2)
                assert host_extra[0]["type"] == "player_connected"
                drain(guest_ws, 4)
                guest_ws.send_json({"type": "leave_room"})
                msgs = drain(host_ws, 2)
                assert msgs[0]["type"] == "player_left"
                assert msgs[0]["player_id"] == guest_id
                assert msgs[1]["type"] == "room_state"
                assert len(msgs[1]["room"]["players"]) == 1

    def test_host_leaving_closes_the_room(self, client):
        code, host_id = create_room(client, "Alice")
        guest_id = join_room(client, code, "Bob")
        with client.websocket_connect(f"/ws/{code}/{host_id}") as host_ws:
            drain(host_ws, 4)
            with client.websocket_connect(f"/ws/{code}/{guest_id}") as guest_ws:
                drain(host_ws, 2)
                drain(guest_ws, 4)
                host_ws.send_json({"type": "leave_room"})
                msg = guest_ws.receive_json()
                assert msg["type"] == "room_closed"
        assert client.get(f"/rooms/{code}").status_code == 404
