"""Lobby and team-system tests: dynamic team sizes, membership and readiness.

These tests exercise the room manager and engine directly (no WebSockets).
Host-only enforcement and the WebSocket event flow live in test_lobby_ws.py.
"""

import asyncio

import pytest

from game.engine import EngineError
from game.models import GamePhase, ReadyStatus, TossDecision
from rooms.errors import RoomError
from rooms.manager import RoomManager

from helpers import start_game


def run(coro):
    return asyncio.run(coro)


def make_room(manager, a_size, b_size, ready=True):
    """Create a room configured a_size vs b_size, fully filled.

    The host is the first player on Team A; the remaining players are joined
    into the two teams until the configured sizes are reached. When ``ready``
    is true every player is marked ready.
    """
    room, host = run(manager.create_room("Host"))
    manager.set_team_sizes(room, a_size, b_size)
    assigned_a = 1  # host
    assigned_b = 0
    idx = 0
    while assigned_a < a_size or assigned_b < b_size:
        _, player = run(manager.join_room(room.room_code, f"P{idx}"))
        if assigned_a < a_size:
            manager.join_team(room, player.id, "A")
            assigned_a += 1
        else:
            manager.join_team(room, player.id, "B")
            assigned_b += 1
        idx += 1
    if ready:
        for player in room.players.values():
            room.engine.set_ready(player.id)
    return room, host


VALID_CONFIGS = [
    (1, 1),
    (1, 2),
    (1, 5),
    (2, 1),
    (2, 3),
    (2, 5),
    (3, 7),
    (5, 2),
    (10, 1),
    (1, 10),
    (10, 10),
]

INVALID_CONFIGS = [
    (0, 1),
    (1, 0),
    (-1, 2),
    (2, -1),
    (11, 2),
    (2, 11),
]


class TestValidTeamSizes:
    @pytest.mark.parametrize("a_size,b_size", VALID_CONFIGS)
    def test_set_team_sizes_accepts_valid_configurations(self, a_size, b_size):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, a_size, b_size)
        assert room.team_a_size == a_size
        assert room.team_b_size == b_size
        assert room.team_a_size + room.team_b_size == a_size + b_size

    def test_combined_sizes_cannot_exceed_room_capacity(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host", max_players=4))
        with pytest.raises(RoomError) as exc:
            manager.set_team_sizes(room, 3, 2)
        assert exc.value.code == "INVALID_TEAM_SIZE"


class TestInvalidTeamSizes:
    @pytest.mark.parametrize("a_size,b_size", INVALID_CONFIGS)
    def test_rejects_out_of_range(self, a_size, b_size):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        with pytest.raises(RoomError) as exc:
            manager.set_team_sizes(room, a_size, b_size)
        assert exc.value.code == "INVALID_TEAM_SIZE"
        assert room.team_a_size == 1  # unchanged
        assert room.team_b_size == 1

    @pytest.mark.parametrize("value", ["2", 2.5, True, None, [], {}])
    def test_rejects_non_integer_values(self, value):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        with pytest.raises(RoomError) as exc:
            manager.set_team_sizes(room, value, 1)
        assert exc.value.code == "INVALID_TEAM_SIZE"


class TestTeamCapacity:
    def test_team_a_capacity_enforced(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 1, 2)
        _, player = run(manager.join_room(room.room_code, "P1"))
        with pytest.raises(RoomError) as exc:
            manager.join_team(room, player.id, "A")
        assert exc.value.code == "TEAM_FULL"
        manager.join_team(room, player.id, "B")
        assert player.team_id == "team-2"
        assert room.team_a_count == 1
        assert room.team_b_count == 1

    def test_team_b_capacity_enforced(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 2, 1)
        _, p1 = run(manager.join_room(room.room_code, "P1"))
        _, p2 = run(manager.join_room(room.room_code, "P2"))
        manager.join_team(room, p1.id, "B")
        with pytest.raises(RoomError) as exc:
            manager.join_team(room, p2.id, "B")
        assert exc.value.code == "TEAM_FULL"
        manager.join_team(room, p2.id, "A")
        assert room.team_a_count == 2  # host + p2
        assert room.team_b_count == 1


class TestTeamMembership:
    def test_player_joins_team_a(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 2, 2)
        _, player = run(manager.join_room(room.room_code, "P"))
        manager.join_team(room, player.id, "A")
        assert player.team_id == "team-1"
        assert player.id in {p.id for p in room.engine.state.teams["team-1"].players}

    def test_player_joins_team_b(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 2, 2)
        _, player = run(manager.join_room(room.room_code, "P"))
        manager.join_team(room, player.id, "B")
        assert player.team_id == "team-2"

    def test_player_leaves_a_team(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 2, 1)
        _, player = run(manager.join_room(room.room_code, "P"))
        manager.join_team(room, player.id, "A")
        assert player.team_id == "team-1"
        manager.leave_team(room, player.id)
        assert player.team_id is None
        assert player.batting_position is None
        assert player.id not in {p.id for p in room.engine.state.teams["team-1"].players}

    def test_player_cannot_belong_to_both_teams(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 2, 2)
        _, player = run(manager.join_room(room.room_code, "P"))
        manager.join_team(room, player.id, "A")
        manager.join_team(room, player.id, "B")
        assert player.team_id == "team-2"
        assert player.id not in {p.id for p in room.engine.state.teams["team-1"].players}
        assert player.id in {p.id for p in room.engine.state.teams["team-2"].players}

    def test_full_team_rejects_a_moving_player(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 1, 2)
        _, p1 = run(manager.join_room(room.room_code, "P1"))
        _, p2 = run(manager.join_room(room.room_code, "P2"))
        manager.join_team(room, p1.id, "B")
        manager.join_team(room, p2.id, "B")
        with pytest.raises(RoomError) as exc:
            manager.join_team(room, p2.id, "A")
        assert exc.value.code == "TEAM_FULL"
        assert p2.team_id == "team-2"  # membership unchanged

    def test_invalid_team_key_rejected(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        _, player = run(manager.join_room(room.room_code, "P"))
        with pytest.raises(RoomError) as exc:
            manager.join_team(room, player.id, "C")
        assert exc.value.code == "INVALID_TEAM"


class TestReadySystem:
    def test_everyone_ready_allows_start(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 5)
        assert room.validate_start() == []
        assert room.can_start is True

    def test_player_not_ready_blocks_start(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 2, ready=False)
        first = next(iter(room.players))
        room.engine.set_ready(first)
        assert room.can_start is False
        assert any("not ready" in problem for problem in room.validate_start())
        with pytest.raises(EngineError):
            room.engine.start_toss()

    def test_team_not_full_blocks_start(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 2, ready=False)
        b_player = room.engine.state.teams["team-2"].players[0]
        manager.leave_team(room, b_player.id)
        for player in room.players.values():
            room.engine.set_ready(player.id)
        assert room.can_start is False
        assert any("Team B" in problem and "exactly" in problem for problem in room.validate_start())

    def test_unassigned_player_blocks_start(self):
        manager = RoomManager()
        room, _ = make_room(manager, 1, 1, ready=False)
        _, stray = run(manager.join_room(room.room_code, "Stray"))
        room.engine.set_ready(stray.id)
        for player in room.players.values():
            room.engine.set_ready(player.id)
        assert room.can_start is False
        assert any("not assigned" in problem for problem in room.validate_start())


class TestHostTeamSizeChanges:
    def test_host_changes_team_sizes(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 2, 5)
        assert room.team_a_size == 2
        assert room.team_b_size == 5

    def test_increasing_capacity_is_allowed(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 2, 2)
        manager.set_team_sizes(room, 2, 5)
        assert room.team_a_size == 2
        assert room.team_b_size == 5

    def test_reject_capacity_reduction_below_current_player_count(self):
        manager = RoomManager()
        room, _ = run(manager.create_room("Host"))
        manager.set_team_sizes(room, 3, 3)
        _, p1 = run(manager.join_room(room.room_code, "P1"))
        _, p2 = run(manager.join_room(room.room_code, "P2"))
        manager.join_team(room, p1.id, "A")
        manager.join_team(room, p2.id, "A")
        # Team A now holds 3 (host + 2): capacity cannot drop below 3.
        with pytest.raises(RoomError) as exc:
            manager.set_team_sizes(room, 2, 3)
        assert exc.value.code == "TEAM_SIZE_TOO_SMALL"
        assert room.team_a_size == 3  # unchanged
        # Increasing capacity afterwards is still allowed.
        manager.set_team_sizes(room, 3, 5)
        assert room.team_a_size == 3
        assert room.team_b_size == 5


class TestStartGame:
    @pytest.mark.parametrize("a_size,b_size", [(1, 5), (2, 5), (5, 2)])
    def test_uneven_games_can_start(self, a_size, b_size):
        manager = RoomManager()
        room, _ = make_room(manager, a_size, b_size)
        assert room.can_start is True
        start_game(room.engine)
        assert room.engine.state.phase == GamePhase.INNINGS_1

    def test_start_requires_everyone_ready(self):
        manager = RoomManager()
        room, _ = make_room(manager, 1, 1, ready=False)
        with pytest.raises(EngineError):
            room.engine.start_toss()


class TestBattingAndBowlingOrders:
    def test_batting_order_uses_only_batting_team_players(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 5)
        start_game(room.engine)
        assert room.engine.state.batting_team_id == "team-1"
        batting = room.engine.batting_order()
        assert len(batting) == 2
        assert {p.id for p in batting} == {
            p.id for p in room.engine.state.teams["team-1"].players
        }

    def test_bowling_eligibility_uses_only_bowling_team_players(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 5)
        start_game(room.engine)
        assert room.engine.state.bowling_team_id == "team-2"
        bowling = room.engine.bowling_order()
        assert len(bowling) == 5
        assert {p.id for p in bowling} == {
            p.id for p in room.engine.state.teams["team-2"].players
        }

    def test_batting_order_uses_actual_team_size_when_team_b_bats(self):
        manager = RoomManager()
        room, _ = make_room(manager, 5, 2)
        start_game(room.engine, toss_winner="team-1", decision=TossDecision.BOWLING)
        assert room.engine.state.batting_team_id == "team-2"
        assert len(room.engine.batting_order()) == 2
        assert len(room.engine.bowling_order()) == 5

    def test_batting_positions_are_contiguous_per_team(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 5)
        for team_id in ("team-1", "team-2"):
            positions = sorted(
                p.batting_position for p in room.engine.state.teams[team_id].players
            )
            assert positions == list(range(1, len(positions) + 1))

    def test_no_artificial_players_are_created(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 5)
        before = len(room.engine.state.players)
        start_game(room.engine)
        assert len(room.engine.state.players) == before == 7
        assert len(room.engine.state.teams["team-1"].players) == 2
        assert len(room.engine.state.teams["team-2"].players) == 5

    def test_bowler_switching_stays_within_bowling_team(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 5)
        start_game(room.engine)
        team_2_ids = {p.id for p in room.engine.state.teams["team-2"].players}
        assert room.engine.state.current_bowler_id in team_2_ids


class TestLobbySnapshotHelpers:
    def test_room_reports_team_counts(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 5)
        assert room.team_a_count == 2
        assert room.team_b_count == 5

    def test_join_team_resets_that_players_ready_state(self):
        manager = RoomManager()
        room, _ = make_room(manager, 2, 2, ready=False)
        # free a slot on Team B so the moved player fits
        b_player = room.engine.state.teams["team-2"].players[0]
        manager.leave_team(room, b_player.id)
        player = room.engine.state.teams["team-1"].players[1]
        room.engine.set_ready(player.id)
        assert player.ready_status == ReadyStatus.READY
        manager.join_team(room, player.id, "B")
        assert player.ready_status == ReadyStatus.NOT_READY
        assert player.team_id == "team-2"
