"""Unit tests for the room manager (no WebSockets involved)."""

import asyncio

import pytest

from game.models import ReadyStatus
from rooms.errors import RoomError
from rooms.manager import RoomManager, RoomStatus, validate_player_name


def run(coro):
    return asyncio.run(coro)


class TestCreateRoom:
    def test_create_room_returns_code_and_host(self):
        manager = RoomManager()
        room, host = run(manager.create_room("Alice"))
        assert len(room.room_code) == 6
        assert room.room_code.isalnum()
        assert room.room_code.isupper()
        assert room.host_player_id == host.id
        assert len(room.players) == 1
        assert host.name == "Alice"
        assert host.team_id == "team-1"
        assert room.engine.state.room_id == room.room_code

    def test_created_codes_are_unique(self):
        manager = RoomManager()
        codes = {run(manager.create_room(f"Player{i}"))[0].room_code for i in range(50)}
        assert len(codes) == 50

    def test_create_room_rejects_invalid_names(self):
        manager = RoomManager()
        with pytest.raises(RoomError):
            run(manager.create_room("   "))
        with pytest.raises(RoomError):
            run(manager.create_room("x" * 21))
        with pytest.raises(RoomError):
            run(manager.create_room(""))


class TestJoinRoom:
    def test_join_room(self):
        manager = RoomManager()
        room, host = run(manager.create_room("Alice"))
        joined, guest = run(manager.join_room(room.room_code, "Bob"))
        assert joined is room
        assert len(room.players) == 2
        assert guest.name == "Bob"
        assert guest.team_id is None  # new players join UNASSIGNED

    def test_multiple_players_join_same_room(self):
        manager = RoomManager()
        room, host = run(manager.create_room("Alice"))
        for i in range(3):
            run(manager.join_room(room.room_code, f"Player{i}"))
        assert len(room.players) == 4
        assert host.team_id == "team-1"  # host founds Team A
        assert all(p.team_id is None for p in room.players.values() if p.id != host.id)

    def test_invalid_room_code(self):
        manager = RoomManager()
        with pytest.raises(RoomError) as exc:
            run(manager.join_room("XXXXXX", "Bob"))
        assert exc.value.code == "ROOM_NOT_FOUND"
        assert exc.value.http_status == 404

    def test_room_code_matching_is_case_insensitive(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Alice"))
        joined, guest = run(manager.join_room(room.room_code.lower(), "Bob"))
        assert joined is room

    def test_duplicate_player_rejected(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Alice"))
        with pytest.raises(RoomError) as exc:
            run(manager.join_room(room.room_code, "alice"))
        assert exc.value.code == "DUPLICATE_PLAYER"

    def test_room_full_rejected(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Alice", max_players=2))
        run(manager.join_room(room.room_code, "Bob"))
        with pytest.raises(RoomError) as exc:
            run(manager.join_room(room.room_code, "Carol"))
        assert exc.value.code == "ROOM_FULL"

    def test_join_after_game_started_rejected(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Alice"))
        room.status = RoomStatus.IN_PROGRESS
        with pytest.raises(RoomError) as exc:
            run(manager.join_room(room.room_code, "Bob"))
        assert exc.value.code == "ROOM_STARTED"


class TestRoomIsolation:
    def test_rooms_have_isolated_state_and_players(self):
        manager = RoomManager()
        room_a, _ = run(manager.create_room("A1"))
        room_b, _ = run(manager.create_room("B1"))
        run(manager.join_room(room_a.room_code, "A2"))
        run(manager.join_room(room_b.room_code, "B2"))

        assert room_a.room_code != room_b.room_code
        assert room_a.engine is not room_b.engine
        assert set(room_a.players) != set(room_b.players)
        assert room_a.players != room_b.players

        for player in room_a.players.values():
            room_a.engine.set_ready(player.id)
        assert all(
            p.ready_status == ReadyStatus.READY for p in room_a.players.values()
        )
        assert all(
            p.ready_status == ReadyStatus.NOT_READY for p in room_b.players.values()
        )

    def test_removing_a_room_does_not_affect_others(self):
        manager = RoomManager()
        room_a, _ = run(manager.create_room("A1"))
        room_b, _ = run(manager.create_room("B1"))
        manager.remove_room(room_a.room_code)
        assert manager.get_room(room_a.room_code) is None
        assert manager.get_room(room_b.room_code) is room_b


class TestNameValidation:
    @pytest.mark.parametrize("name", ["", "   ", "x" * 21, None, 42, "a\x00b"])
    def test_invalid(self, name):
        with pytest.raises(RoomError):
            validate_player_name(name)

    @pytest.mark.parametrize("name", ["Alice", "  Bob  ", "J", "x" * 20])
    def test_valid(self, name):
        cleaned = validate_player_name(name)
        assert cleaned == name.strip()
