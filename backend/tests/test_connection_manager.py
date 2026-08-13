"""Unit tests for the WebSocket connection manager, including isolation."""

import asyncio

from ws.connections import ConnectionManager


def run(coro):
    return asyncio.run(coro)


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def send_text(self, text):
        self.sent.append(text)

    async def close(self):
        self.closed = True


class TestConnectionManager:
    def test_broadcast_is_room_isolated(self):
        conn = ConnectionManager()
        a1 = FakeWebSocket()
        a2 = FakeWebSocket()
        b1 = FakeWebSocket()
        conn.connect("ABC123", "p1", a1)
        conn.connect("ABC123", "p2", a2)
        conn.connect("XYZ789", "p3", b1)

        run(conn.broadcast_room("ABC123", {"type": "room_state"}))
        run(conn.broadcast_room("XYZ789", {"type": "secret"}))

        assert len(a1.sent) == 1
        assert len(a2.sent) == 1
        assert len(b1.sent) == 1
        assert '"secret"' in b1.sent[0]
        assert '"secret"' not in a1.sent[0]

    def test_rooms_with_similar_names_are_isolated(self):
        conn = ConnectionManager()
        ws_a = FakeWebSocket()
        ws_b = FakeWebSocket()
        conn.connect("ABC", "p1", ws_a)
        conn.connect("ABCDE", "p1", ws_b)

        run(conn.broadcast_room("ABC", {"type": "x"}))
        assert len(ws_a.sent) == 1
        assert len(ws_b.sent) == 0

    def test_connect_and_disconnect_lifecycle(self):
        conn = ConnectionManager()
        ws = FakeWebSocket()
        assert conn.connect("ABC", "p1", ws) == "first"
        assert conn.is_player_connected("ABC", "p1")
        conn.disconnect("ABC", "p1", ws)
        assert not conn.is_player_connected("ABC", "p1")
        conn.disconnect("ABC", "p1", ws)  # idempotent
        assert not conn.is_player_connected("ABC", "p1")

    def test_reconnect_detection(self):
        conn = ConnectionManager()
        ws1 = FakeWebSocket()
        assert conn.connect("ABC", "p1", ws1) == "first"
        conn.disconnect("ABC", "p1", ws1)
        ws2 = FakeWebSocket()
        assert conn.connect("ABC", "p1", ws2) == "reconnect"
        assert conn.is_player_connected("ABC", "p1")

    def test_multiple_sockets_per_player(self):
        conn = ConnectionManager()
        ws1 = FakeWebSocket()
        ws2 = FakeWebSocket()
        conn.connect("ABC", "p1", ws1)
        conn.connect("ABC", "p1", ws2)
        assert conn.is_player_connected("ABC", "p1")
        conn.disconnect("ABC", "p1", ws1)
        assert conn.is_player_connected("ABC", "p1")
        conn.disconnect("ABC", "p1", ws2)
        assert not conn.is_player_connected("ABC", "p1")

    def test_send_to_player_only_reaches_that_player(self):
        conn = ConnectionManager()
        target = FakeWebSocket()
        other = FakeWebSocket()
        conn.connect("ABC", "p1", target)
        conn.connect("ABC", "p2", other)
        run(conn.send_to_player("ABC", "p1", {"type": "ping"}))
        assert len(target.sent) == 1
        assert len(other.sent) == 0

    def test_drop_player_sockets_closes_and_forgets(self):
        conn = ConnectionManager()
        ws = FakeWebSocket()
        conn.connect("ABC", "p1", ws)
        run(conn.drop_player_sockets("ABC", "p1"))
        assert ws.closed
        assert not conn.is_player_connected("ABC", "p1")

    def test_remove_room_forgets_all_sockets(self):
        conn = ConnectionManager()
        ws = FakeWebSocket()
        conn.connect("ABC", "p1", ws)
        conn.remove_room("ABC")
        assert not conn.is_player_connected("ABC", "p1")
        run(conn.broadcast_room("ABC", {"type": "x"}))
        assert len(ws.sent) == 0
