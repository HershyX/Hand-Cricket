"""Prompt 6 gameplay tests: move resolution, simultaneous submission,
anti-cheat move secrecy, bowler eligibility, target chase and batting order.

These drive the engine directly (no WebSockets) so every combination and
state transition is covered deterministically.
"""

import pytest

from game.engine import EngineError
from game.models import (
    BallOutcome,
    ConnectionStatus,
    GamePhase,
    GameResult,
    TurnState,
)
from game.rules import IllegalMoveError, calculate_runs

from helpers import build_engine, build_engine_sizes, play_ball, start_game

# (batter_move, bowler_move, expected_runs, expected_outcome)
MOVE_CASES = [
    (0, 0, 0, BallOutcome.OUT),
    (0, 1, 1, BallOutcome.RUNS),
    (0, 5, 5, BallOutcome.RUNS),
    (0, 10, 10, BallOutcome.RUNS),
    (1, 1, 0, BallOutcome.OUT),
    (1, 2, 1, BallOutcome.RUNS),
    (5, 5, 0, BallOutcome.OUT),
    (5, 3, 5, BallOutcome.RUNS),
    (10, 10, 0, BallOutcome.OUT),
    (10, 1, 10, BallOutcome.RUNS),
]


class TestMoveResolutionRules:
    @pytest.mark.parametrize("batter,bowler,runs,outcome", MOVE_CASES)
    def test_calculate_runs(self, batter, bowler, runs, outcome):
        assert calculate_runs(batter, bowler) == (runs, outcome)


class TestMoveResolutionEngine:
    @pytest.mark.parametrize("batter,bowler,runs,outcome", MOVE_CASES)
    def test_engine_resolves_move(self, batter, bowler, runs, outcome):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        score_before = engine.state.current_innings.score
        wickets_before = engine.state.current_innings.wickets

        engine.submit_move(engine.state.current_batter_id, batter)
        engine.submit_move(engine.state.current_bowler_id, bowler)

        last = engine.state.last_ball
        assert last is not None
        assert last.batter_move == batter
        assert last.bowler_move == bowler
        assert last.runs == runs
        assert last.outcome == outcome

        if outcome == BallOutcome.OUT:
            assert engine.state.current_innings.score == score_before
            assert engine.state.current_innings.wickets == wickets_before + 1
            assert engine.state.turn_state == TurnState.PLAYER_OUT
        else:
            assert engine.state.current_innings.score == score_before + runs
            assert engine.state.current_innings.wickets == wickets_before
            assert engine.state.turn_state == TurnState.WAITING_FOR_MOVES


class TestSimultaneousSubmission:
    def test_no_resolution_until_both_submit(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        engine.submit_move(engine.state.current_batter_id, 4)
        assert engine.state.batter_submitted is True
        assert engine.state.bowler_submitted is False
        assert engine.state.last_ball is None
        assert engine.state.current_innings.score == 0

    def test_batter_submits_first_then_bowler(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        batter = engine.state.current_batter_id
        bowler = engine.state.current_bowler_id
        engine.submit_move(batter, 4)
        assert engine.state.batter_submitted is True
        assert engine.state.bowler_submitted is False
        engine.submit_move(bowler, 3)
        assert engine.state.batter_submitted is False
        assert engine.state.bowler_submitted is False
        assert engine.state.current_innings.score == 4

    def test_bowler_submits_first_then_batter(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        batter = engine.state.current_batter_id
        bowler = engine.state.current_bowler_id
        engine.submit_move(bowler, 3)
        assert engine.state.bowler_submitted is True
        assert engine.state.batter_submitted is False
        engine.submit_move(batter, 4)
        assert engine.state.batter_submitted is False
        assert engine.state.bowler_submitted is False
        assert engine.state.current_innings.score == 4

    def test_submission_order_does_not_affect_result(self):
        engines = []
        for order in ("batter_first", "bowler_first"):
            engine = build_engine(players_per_team=2)
            start_game(engine)
            batter = engine.state.current_batter_id
            bowler = engine.state.current_bowler_id
            if order == "batter_first":
                engine.submit_move(batter, 4)
                engine.submit_move(bowler, 3)
            else:
                engine.submit_move(bowler, 3)
                engine.submit_move(batter, 4)
            engines.append(engine)
        assert engines[0].state.current_innings.score == 4
        assert engines[0].state.current_innings.score == engines[1].state.current_innings.score
        for key in ("batter_move", "bowler_move", "runs", "outcome"):
            assert getattr(engines[0].state.last_ball, key) == getattr(
                engines[1].state.last_ball, key
            )


class TestSubmissionValidation:
    def test_duplicate_submission_rejected(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        batter = engine.state.current_batter_id
        engine.submit_move(batter, 4)
        with pytest.raises(EngineError):
            engine.submit_move(batter, 5)
        assert engine.state.batter_move == 4

    def test_invalid_submission_rejected(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        batter = engine.state.current_batter_id
        for move in (-1, 11, "4", None, True):
            with pytest.raises(IllegalMoveError):
                engine.submit_move(batter, move)
        assert engine.state.batter_submitted is False

    def test_wrong_player_submission_rejected(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        team = engine.state.teams["team-1"]
        inactive = next(
            p for p in team.players if p.id != engine.state.current_batter_id
        )
        with pytest.raises(EngineError):
            engine.submit_move(inactive.id, 4)

    def test_batting_and_bowling_roles_enforced(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        batter = engine.state.current_batter_id
        bowler = engine.state.current_bowler_id
        with pytest.raises(EngineError):
            engine.submit_batting_move(bowler, 4)
        with pytest.raises(EngineError):
            engine.submit_bowling_move(batter, 4)


class TestBowlerSwitchEligibility:
    def test_switch_rotates_to_next_connected_bowler(self):
        engine = build_engine_sizes(2, 2)
        start_game(engine)
        current = engine.state.current_bowler_id
        new_bowler = engine.switch_bowler(current)
        assert new_bowler != current
        assert new_bowler in {p.id for p in engine.state.teams["team-2"].players}

    def test_switch_skips_disconnected_bowler(self):
        engine = build_engine_sizes(2, 2)
        start_game(engine)
        current = engine.state.current_bowler_id
        bowling = engine.state.teams["team-2"]
        next_bowler = next(p for p in bowling.players if p.id != current)
        next_bowler.connection_status = ConnectionStatus.DISCONNECTED
        new_bowler = engine.switch_bowler(current)
        assert new_bowler == current

    def test_switch_keeps_bowler_when_all_others_disconnected(self):
        engine = build_engine_sizes(2, 3)
        start_game(engine)
        current = engine.state.current_bowler_id
        bowling = engine.state.teams["team-2"]
        for player in bowling.players:
            if player.id != current:
                player.connection_status = ConnectionStatus.DISCONNECTED
        assert engine.switch_bowler(current) == current

    def test_switch_rejected_after_batter_submits(self):
        engine = build_engine_sizes(2, 2)
        start_game(engine)
        engine.submit_move(engine.state.current_batter_id, 4)
        with pytest.raises(EngineError):
            engine.switch_bowler(engine.state.current_bowler_id)

    def test_switch_rejected_for_batting_team_member(self):
        engine = build_engine_sizes(2, 2)
        start_game(engine)
        with pytest.raises(EngineError):
            engine.switch_bowler(engine.state.current_batter_id)


class TestNextBatter:
    def test_batter_continues_after_runs(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        first = engine.state.current_batter_id
        play_ball(engine, 4, 3)
        assert engine.state.current_batter_id == first
        assert engine.state.turn_state == TurnState.WAITING_FOR_MOVES

    def test_next_batter_after_out(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        first = engine.state.current_batter_id
        play_ball(engine, 4, 4)
        assert engine.state.current_batter_id != first
        assert engine.state.turn_state == TurnState.WAITING_FOR_MOVES

    def test_last_batter_out_ends_innings(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        play_ball(engine, 4, 4)
        play_ball(engine, 5, 5)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.current_innings.wickets == 2


class TestTargetChase:
    def test_target_reached_ends_game_immediately(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)
        assert engine.state.target_score == 5

        engine.begin_second_innings()
        assert engine.state.phase == GamePhase.INNINGS_2
        play_ball(engine, 5, 0)
        assert engine.state.phase == GamePhase.GAME_OVER
        assert engine.state.game_over_reason == "TARGET_REACHED"

    def test_score_below_target_keeps_game_going(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)
        engine.begin_second_innings()
        play_ball(engine, 3, 2)
        assert engine.state.phase == GamePhase.INNINGS_2
        assert engine.state.result == GameResult.PENDING
