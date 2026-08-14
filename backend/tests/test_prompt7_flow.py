"""Prompt 7 regression tests: the complete ball-by-ball game loop.

Verifies that a normal completed ball never ends the game, score accumulates,
turn numbers increment, batters rotate only after OUT, innings end only on a
real all-out / target condition, and that connection status never influences
innings-ending conditions.

Two layers are covered:
  * engine-level tests (deterministic, no WebSockets)
  * WS-level tests that play consecutive balls through the handler and check
    the broadcast loop (move_submitted -> move_result -> score_updated ->
    next_turn -> game_state, with turn numbers exposed).
"""

import pytest

from game.engine import EngineError
from game.models import (
    ConnectionStatus,
    GamePhase,
    GameResult,
    TurnState,
)
from game.rules import calculate_runs

from helpers import build_engine, build_engine_sizes, play_ball, start_game

RULES = {
    (0, 5): (5, "RUNS"),
    (5, 0): (5, "RUNS"),
    (5, 5): (0, "OUT"),
    (0, 0): (0, "OUT"),
}

RULE_CASES = [
    (batter, bowler, runs, outcome)
    for (batter, bowler), (runs, outcome) in RULES.items()
]


class TestNormalBallDoesNotEndGame:
    def test_01_normal_scoring_ball_does_not_end_game(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        play_ball(engine, 4, 3)
        assert engine.state.phase in (GamePhase.INNINGS_1, GamePhase.INNINGS_2)

    def test_02_score_persists_after_a_ball(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        play_ball(engine, 4, 3)
        assert engine.state.current_innings.score == 4

    def test_03_score_accumulates_across_multiple_balls(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 6, 2)
        play_ball(engine, 3, 1)
        assert engine.state.current_innings.score == 13

    def test_04_same_batter_remains_after_scoring(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        first = engine.state.current_batter_id
        play_ball(engine, 4, 3)
        play_ball(engine, 6, 2)
        assert engine.state.current_batter_id == first

    def test_05_new_turn_created_after_normal_ball(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        play_ball(engine, 4, 3)
        assert engine.state.turn_state == TurnState.WAITING_FOR_MOVES

    def test_06_previous_moves_are_cleared(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        play_ball(engine, 4, 3)
        assert engine.state.batter_move is None
        assert engine.state.bowler_move is None
        assert engine.state.batter_submitted is False
        assert engine.state.bowler_submitted is False

    def test_07_turn_number_increments(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        assert engine.state.turn_number == 1
        play_ball(engine, 4, 3)
        assert engine.state.turn_number == 2
        play_ball(engine, 6, 2)
        assert engine.state.turn_number == 3

    def test_08_batter_can_submit_again_next_turn(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        batter = engine.state.current_batter_id
        play_ball(engine, 4, 3)
        engine.submit_move(batter, 5)
        assert engine.state.batter_submitted is True

    def test_09_bowler_can_submit_again_next_turn(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        bowler = engine.state.current_bowler_id
        play_ball(engine, 4, 3)
        engine.submit_move(bowler, 5)
        assert engine.state.bowler_submitted is True

    def test_10_batter_changes_only_after_out(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        first = engine.state.current_batter_id
        play_ball(engine, 4, 3)
        assert engine.state.current_batter_id == first
        play_ball(engine, 5, 5)
        assert engine.state.current_batter_id != first
        assert engine.state.turn_state == TurnState.WAITING_FOR_MOVES


class TestAllOutRules:
    def test_11_one_player_team_ends_after_out(self):
        engine = build_engine(players_per_team=1)
        start_game(engine)
        play_ball(engine, 4, 4)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.current_innings.wickets == 1

    def test_12_two_player_team_continues_after_first_out(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        first = engine.state.current_batter_id
        play_ball(engine, 4, 4)
        assert engine.state.phase == GamePhase.INNINGS_1
        assert engine.state.current_batter_id != first
        assert engine.state.turn_state == TurnState.WAITING_FOR_MOVES

    def test_13_five_player_team_rotates_through_all_batters(self):
        engine = build_engine(players_per_team=5)
        start_game(engine)
        seen = [engine.state.current_batter_id]
        for move in (1, 2, 3, 4):
            play_ball(engine, move, move)
            seen.append(engine.state.current_batter_id)
        assert len(set(seen)) == 5
        assert engine.state.phase == GamePhase.INNINGS_1
        # the fifth (final) dismissal ends the innings
        play_ball(engine, 5, 5)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.current_innings.wickets == 5

    def test_14_opposing_team_size_does_not_affect_all_out(self):
        engine = build_engine_sizes(2, 5)
        start_game(engine)
        play_ball(engine, 1, 1)
        assert engine.state.phase == GamePhase.INNINGS_1
        assert engine.state.current_innings.wickets == 1
        play_ball(engine, 2, 2)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.current_innings.wickets == 2


class TestMoveRules:
    @pytest.mark.parametrize(
        "batter,bowler,expected_runs,expected_outcome", RULE_CASES
    )
    def test_rule_combinations(self, batter, bowler, expected_runs, expected_outcome):
        runs, outcome = calculate_runs(batter, bowler)
        assert runs == expected_runs
        assert outcome.value == expected_outcome


class TestSecondInningsLoop:
    def _innings_one_done(self, engine):
        play_ball(engine, 4, 3)  # 4 runs
        play_ball(engine, 1, 1)  # out -> A2 in
        play_ball(engine, 2, 2)  # out -> innings 1 ends (2-player team)
        assert engine.state.phase == GamePhase.INNINGS_BREAK

    def test_19_second_innings_continues_after_normal_scoring(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        self._innings_one_done(engine)
        engine.begin_second_innings()
        assert engine.state.phase == GamePhase.INNINGS_2
        assert engine.state.current_innings.score == 0
        play_ball(engine, 3, 2)
        assert engine.state.phase == GamePhase.INNINGS_2
        assert engine.state.current_innings.score == 3
        assert engine.state.turn_number == 2

    def test_20_target_checked_after_every_scoring_ball(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)
        assert engine.state.target_score == 5
        engine.begin_second_innings()
        play_ball(engine, 3, 2)  # below target -> keep going
        assert engine.state.phase == GamePhase.INNINGS_2
        play_ball(engine, 2, 1)  # reaches target -> end immediately
        assert engine.state.phase == GamePhase.GAME_OVER

    def test_21_target_reached_ends_game_immediately(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)
        engine.begin_second_innings()
        play_ball(engine, 5, 0)
        assert engine.state.phase == GamePhase.GAME_OVER
        assert engine.state.game_over_reason == "TARGET_REACHED"

    def test_22_all_out_before_target_gives_first_team_win(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        self._innings_one_done(engine)  # team-1 scores 4, target 5
        assert engine.state.target_score == 5
        engine.begin_second_innings()
        play_ball(engine, 5, 5)  # out -> 1 wicket, still batting (2 players)
        assert engine.state.phase == GamePhase.INNINGS_2
        play_ball(engine, 6, 6)  # out -> all out before target
        assert engine.state.phase == GamePhase.GAME_OVER
        assert engine.state.winner_team_id == "team-1"
        assert engine.state.game_over_reason == "ALL_OUT"

    def test_23_no_extra_turn_after_game_over(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)
        engine.begin_second_innings()
        play_ball(engine, 5, 0)
        assert engine.state.phase == GamePhase.GAME_OVER
        turn_number = engine.state.turn_number
        with pytest.raises(EngineError):
            engine.submit_move(engine.state.current_batter_id, 3)
        assert engine.state.turn_number == turn_number


class TestBatterAndBowlerRotation:
    def test_24_dismissed_batter_cannot_submit_again(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        first = engine.state.current_batter_id
        play_ball(engine, 1, 1)
        assert engine.state.current_batter_id != first
        with pytest.raises(EngineError):
            engine.submit_move(first, 3)

    def test_25_bowler_remains_valid_for_next_ball(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        bowler = engine.state.current_bowler_id
        play_ball(engine, 4, 3)
        assert engine.state.current_bowler_id == bowler
        engine.submit_move(bowler, 2)
        assert engine.state.bowler_submitted is True

    def test_26_bowler_switching_before_next_move_works(self):
        engine = build_engine_sizes(2, 2)
        start_game(engine)
        bowler = engine.state.current_bowler_id
        play_ball(engine, 4, 3)
        new_bowler = engine.switch_bowler(engine.state.current_bowler_id)
        assert new_bowler != bowler
        assert engine.state.turn_state == TurnState.WAITING_FOR_MOVES

    def test_27_bowler_cannot_switch_after_batter_submits(self):
        engine = build_engine_sizes(2, 2)
        start_game(engine)
        engine.submit_move(engine.state.current_batter_id, 4)
        with pytest.raises(EngineError):
            engine.switch_bowler(engine.state.current_bowler_id)

    def test_28_multiple_consecutive_balls_do_not_reset_innings(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        for batter, bowler in ((4, 3), (6, 2), (3, 1), (8, 4)):
            play_ball(engine, batter, bowler)
        assert engine.state.current_innings.score == 21
        assert engine.state.phase == GamePhase.INNINGS_1
        assert engine.state.ball_count == 4
        assert engine.state.current_innings.ball_count == 4
        assert engine.state.turn_number == 5


class TestConnectionIndependence:
    def test_disconnected_bowler_team_does_not_end_game(self):
        engine = build_engine_sizes(2, 2)
        start_game(engine)
        for player in engine.state.teams["team-2"].players:
            player.connection_status = ConnectionStatus.DISCONNECTED
        play_ball(engine, 4, 3)
        play_ball(engine, 6, 2)
        assert engine.state.phase == GamePhase.INNINGS_1
        assert engine.state.current_innings.score == 10

    def test_all_out_counts_batting_team_players_not_connections(self):
        engine = build_engine_sizes(2, 5)
        start_game(engine)
        for player in engine.state.teams["team-1"].players:
            player.connection_status = ConnectionStatus.DISCONNECTED
        play_ball(engine, 1, 1)
        play_ball(engine, 2, 2)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.current_innings.wickets == 2

    def test_disconnected_current_batter_still_advances_innings(self):
        engine = build_engine_sizes(3, 3)
        start_game(engine)
        first = engine.state.current_batter_id
        engine.state.players[first].connection_status = ConnectionStatus.DISCONNECTED
        play_ball(engine, 1, 1)
        assert engine.state.phase == GamePhase.INNINGS_1
        assert engine.state.current_batter_id != first
        play_ball(engine, 2, 2)
        assert engine.state.phase == GamePhase.INNINGS_1
        play_ball(engine, 3, 3)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.current_innings.wickets == 3


# ----------------------------------------------------------------------
# WS-level loop verification
# ----------------------------------------------------------------------

from fastapi.testclient import TestClient  # noqa: E402

from main import create_app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


def _create_room(client, host_name="Alice"):
    data = client.post("/rooms", json={"host_name": host_name}).json()
    return data["room_code"], data["player_id"]


def _join(client, code, name):
    return client.post(f"/rooms/{code}/join", json={"player_name": name}).json()[
        "player_id"
    ]


def _open_ws(client, code, player_id):
    ws = client.websocket_connect(f"/ws/{code}/{player_id}")
    ws.__enter__()
    return ws


def _drain(ws, count):
    return [ws.receive_json() for _ in range(count)]


def _close(*sockets):
    for ws in sockets:
        if ws is not None:
            try:
                ws.__exit__(None, None, None)
            except Exception:
                pass


def _start_roles(client):
    """Drive a room to INNINGS_1 and return (host_ws, guest_ws, winner)."""
    code, host_id = _create_room(client)
    guest_id = _join(client, code, "Bob")
    host_ws = _open_ws(client, code, host_id)
    _drain(host_ws, 4)
    guest_ws = _open_ws(client, code, guest_id)
    _drain(host_ws, 2)
    _drain(guest_ws, 4)
    guest_ws.send_json({"type": "join_team", "team": "B"})
    for ws in (host_ws, guest_ws):
        _drain(ws, 2)
    host_ws.send_json({"type": "set_ready", "ready": True})
    guest_ws.send_json({"type": "set_ready", "ready": True})
    for ws in (host_ws, guest_ws):
        _drain(ws, 4)
    host_ws.send_json({"type": "start_game"})
    host_msgs = _drain(host_ws, 4)
    _drain(guest_ws, 4)
    winner = host_msgs[2]["winner_team_id"]
    winner_ws = host_ws if winner == "team-1" else guest_ws
    winner_ws.send_json({"type": "toss_decision", "decision": "BATTING"})
    for ws in (host_ws, guest_ws):
        msgs = _drain(ws, 3)
        assert msgs[2]["game"]["phase"] == "INNINGS_1"
    return host_ws, guest_ws, winner


class TestWsBallLoop:
    def test_three_consecutive_balls_continue_the_game(self, client):
        host_ws, guest_ws, winner = _start_roles(client)

        batter_ws = host_ws if winner == "team-1" else guest_ws
        bowler_ws = guest_ws if winner == "team-1" else host_ws

        # Ball 1: 4 vs 3 -> 4 runs
        batter_ws.send_json({"type": "submit_move", "move": 4})
        for ws in (batter_ws, bowler_ws):
            msgs = _drain(ws, 2)
            assert msgs[0]["type"] == "move_submitted"
            assert msgs[1]["type"] == "game_state"
        bowler_ws.send_json({"type": "submit_move", "move": 3})
        for ws in (host_ws, guest_ws):
            msgs = _drain(ws, 5)
            assert [m["type"] for m in msgs] == [
                "move_submitted",
                "move_result",
                "score_updated",
                "next_turn",
                "game_state",
            ]
            assert msgs[1]["ball"]["runs"] == 4
            assert msgs[2]["score"] == 4
            assert msgs[3]["turn_number"] == 2
            assert msgs[4]["game"]["turn_number"] == 2
            assert msgs[4]["game"]["phase"] == "INNINGS_1"
            assert msgs[4]["game"]["current_innings"]["score"] == 4

        # Ball 2: 6 vs 2 -> 6 runs (score 10), loop continues
        batter_ws.send_json({"type": "submit_move", "move": 6})
        for ws in (batter_ws, bowler_ws):
            _drain(ws, 2)
        bowler_ws.send_json({"type": "submit_move", "move": 2})
        for ws in (host_ws, guest_ws):
            msgs = _drain(ws, 5)
            assert msgs[2]["score"] == 10
            assert msgs[3]["turn_number"] == 3
            assert msgs[4]["game"]["phase"] == "INNINGS_1"

        # Ball 3: 3 vs 1 -> 3 runs (score 13), loop continues
        batter_ws.send_json({"type": "submit_move", "move": 3})
        for ws in (batter_ws, bowler_ws):
            _drain(ws, 2)
        bowler_ws.send_json({"type": "submit_move", "move": 1})
        for ws in (host_ws, guest_ws):
            msgs = _drain(ws, 5)
            assert msgs[2]["score"] == 13
            assert msgs[3]["turn_number"] == 4
            assert msgs[4]["game"]["phase"] == "INNINGS_1"
            assert msgs[4]["game"]["current_innings"]["score"] == 13

        _close(host_ws, guest_ws)
