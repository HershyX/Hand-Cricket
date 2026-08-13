"""WebSocket integration tests for the lobby and team system.

These cover host-only enforcement (team sizes, start, reset), team assignment
events, readiness and lobby validation over real (TestClient) sockets.
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


def connect_pair(client, code, host_id, guest_id):
    host_ws = client.websocket_connect(f"/ws/{code}/{host_id}")
    guest_ws = client.websocket_connect(f"/ws/{code}/{guest_id}")
    host_ws.__enter__()
    guest_ws.__enter__()
    drain(host_ws, 6)
    drain(guest_ws, 4)
    return host_ws, guest_ws


class TestSetTeamSizes:
    def test_host_sets_team_sizes(self, client):
        code, host_id = create_room(client)
        with client.websocket_connect(f"/ws/{code}/{host_id}") as ws:
            drain(ws, 4)
            ws.send_json({"type": "set_team_sizes", "team_a_size": 2, "team_b_size": 5})
            msgs = drain(ws, 2)
            assert msgs[0]["type"] == "team_sizes_updated"
            assert msgs[0]["team_a_size"] == 2
            assert msgs[0]["team_b_size"] == 5
            room = msgs[1]["room"]
            assert room["team_a_size"] == 2
            assert room["team_b_size"] == 5
            assert room["team_a"]["capacity"] == 2
            assert room["team_b"]["capacity"] == 5
            assert room["max_team_size"] == 10

    def test_non_host_cannot_set_team_sizes(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        host_ws, guest_ws = connect_pair(client, code, host_id, guest_id)
        try:
            guest_ws.send_json({"type": "set_team_sizes", "team_a_size": 3, "team_b_size": 3})
            msg = guest_ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "NOT_HOST"
        finally:
            host_ws.__exit__(None, None, None)
            guest_ws.__exit__(None, None, None)

    def test_invalid_team_size_reported(self, client):
        code, host_id = create_room(client)
        with client.websocket_connect(f"/ws/{code}/{host_id}") as ws:
            drain(ws, 4)
            ws.send_json({"type": "set_team_sizes", "team_a_size": 0, "team_b_size": 1})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "INVALID_TEAM_SIZE"


class TestTeamAssignment:
    def test_join_team_broadcasts(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        host_ws, guest_ws = connect_pair(client, code, host_id, guest_id)
        try:
            guest_ws.send_json({"type": "join_team", "team": "B"})
            for ws in (host_ws, guest_ws):
                msgs = drain(ws, 2)
                assert msgs[0]["type"] == "player_team_changed"
                assert msgs[0]["player_id"] == guest_id
                assert msgs[0]["team"] == "B"
                assert msgs[1]["type"] == "room_state"
                assert msgs[1]["room"]["team_b"]["player_count"] == 1
                assert msgs[1]["room"]["team_a"]["player_count"] == 1
        finally:
            host_ws.__exit__(None, None, None)
            guest_ws.__exit__(None, None, None)

    def test_join_full_team_rejected(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        host_ws, guest_ws = connect_pair(client, code, host_id, guest_id)
        try:
            # default sizes are 1 vs 1; the host already fills Team A
            guest_ws.send_json({"type": "join_team", "team": "A"})
            msg = guest_ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "TEAM_FULL"
        finally:
            host_ws.__exit__(None, None, None)
            guest_ws.__exit__(None, None, None)

    def test_leave_team_broadcasts(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        host_ws, guest_ws = connect_pair(client, code, host_id, guest_id)
        try:
            guest_ws.send_json({"type": "join_team", "team": "B"})
            drain(guest_ws, 2)
            drain(host_ws, 2)
            guest_ws.send_json({"type": "leave_team"})
            msgs = drain(guest_ws, 2)
            assert msgs[0]["type"] == "player_team_changed"
            assert msgs[0]["team"] is None
            assert msgs[1]["room"]["team_b"]["player_count"] == 0
        finally:
            host_ws.__exit__(None, None, None)
            guest_ws.__exit__(None, None, None)


class TestSetReady:
    def test_set_ready_toggles_and_broadcasts(self, client):
        code, host_id = create_room(client)
        with client.websocket_connect(f"/ws/{code}/{host_id}") as ws:
            drain(ws, 4)
            ws.send_json({"type": "set_ready", "ready": True})
            msgs = drain(ws, 2)
            assert msgs[0]["type"] == "player_ready"
            assert msgs[0]["ready"] is True
            assert msgs[1]["room"]["players"][0]["ready_status"] == "READY"

            ws.send_json({"type": "set_ready", "ready": False})
            msgs = drain(ws, 2)
            assert msgs[0]["type"] == "player_ready"
            assert msgs[0]["ready"] is False
            assert msgs[1]["room"]["players"][0]["ready_status"] == "NOT_READY"

    def test_invalid_ready_value_rejected(self, client):
        code, host_id = create_room(client)
        with client.websocket_connect(f"/ws/{code}/{host_id}") as ws:
            drain(ws, 4)
            ws.send_json({"type": "set_ready", "ready": "yes"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "INVALID_READY"


class TestStartGame:
    def test_host_cannot_start_incomplete_lobby(self, client):
        code, host_id = create_room(client)
        with client.websocket_connect(f"/ws/{code}/{host_id}") as ws:
            drain(ws, 4)
            ws.send_json({"type": "set_ready"})
            drain(ws, 2)
            ws.send_json({"type": "start_game"})
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "LOBBY_NOT_READY"
            assert "Team B" in msg["message"]

    def test_host_starts_a_valid_lobby(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        host_ws, guest_ws = connect_pair(client, code, host_id, guest_id)
        try:
            guest_ws.send_json({"type": "join_team", "team": "B"})
            drain(host_ws, 2)
            drain(guest_ws, 2)
            host_ws.send_json({"type": "set_ready"})
            guest_ws.send_json({"type": "set_ready"})
            drain(host_ws, 4)
            drain(guest_ws, 4)

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
        finally:
            host_ws.__exit__(None, None, None)
            guest_ws.__exit__(None, None, None)

    def test_non_host_cannot_start_game(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        host_ws, guest_ws = connect_pair(client, code, host_id, guest_id)
        try:
            guest_ws.send_json({"type": "start_game"})
            msg = guest_ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "NOT_HOST"
        finally:
            host_ws.__exit__(None, None, None)
            guest_ws.__exit__(None, None, None)


class TestResetLobby:
    def test_host_resets_a_started_lobby(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        host_ws, guest_ws = connect_pair(client, code, host_id, guest_id)
        try:
            guest_ws.send_json({"type": "join_team", "team": "B"})
            drain(host_ws, 2)
            drain(guest_ws, 2)
            host_ws.send_json({"type": "set_ready"})
            guest_ws.send_json({"type": "set_ready"})
            drain(host_ws, 4)
            drain(guest_ws, 4)
            host_ws.send_json({"type": "start_game"})
            for ws in (host_ws, guest_ws):
                drain(ws, 4)

            host_ws.send_json({"type": "reset_lobby"})
            for ws in (host_ws, guest_ws):
                msgs = drain(ws, 3)
                assert msgs[0]["type"] == "lobby_reset"
                assert msgs[1]["type"] == "room_state"
                assert msgs[1]["room"]["phase"] == "LOBBY"
                assert msgs[1]["room"]["can_start"] is False
                assert msgs[1]["room"]["team_a"]["player_count"] == 0
                assert msgs[1]["room"]["team_b"]["player_count"] == 0
                assert msgs[2]["type"] == "game_state"
                assert msgs[2]["game"]["phase"] == "LOBBY"
        finally:
            host_ws.__exit__(None, None, None)
            guest_ws.__exit__(None, None, None)

    def test_non_host_cannot_reset_lobby(self, client):
        code, host_id = create_room(client)
        guest_id = join_room(client, code, "Bob")
        host_ws, guest_ws = connect_pair(client, code, host_id, guest_id)
        try:
            guest_ws.send_json({"type": "reset_lobby"})
            msg = guest_ws.receive_json()
            assert msg["type"] == "error"
            assert msg["code"] == "NOT_HOST"
        finally:
            host_ws.__exit__(None, None, None)
            guest_ws.__exit__(None, None, None)
