"""Tests for the game engine: flow, innings, targets and winners."""

import pytest

from game.engine import EngineError, GameEngine
from game.models import GamePhase, GameResult, ReadyStatus, TossDecision, TurnState
from game.rules import IllegalMoveError

from helpers import build_engine, play_ball, start_game


class TestEngineMoveValidation:
    @pytest.mark.parametrize("move", [-1, 11, 100, -5])
    def test_rejects_out_of_range(self, engine, move):
        with pytest.raises(IllegalMoveError):
            engine.submit_move(engine.state.current_batter_id, move)
        assert engine.state.batter_submitted is False

    @pytest.mark.parametrize("move", [3.5, "5", None, True])
    def test_rejects_non_integer(self, engine, move):
        with pytest.raises(IllegalMoveError):
            engine.submit_move(engine.state.current_bowler_id, move)
        assert engine.state.bowler_submitted is False

    def test_only_current_batter_or_bowler_can_submit(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        inactive = engine.state.teams["team-1"].players[1]
        with pytest.raises(EngineError):
            engine.submit_move(inactive.id, 4)
        assert engine.state.batter_submitted is False
        assert engine.state.bowler_submitted is False

    def test_cannot_submit_twice(self, engine):
        engine.submit_move(engine.state.current_batter_id, 3)
        with pytest.raises(EngineError):
            engine.submit_move(engine.state.current_batter_id, 4)


class TestZeroRuleInEngine:
    def test_zero_batter_scores_bowlers_number(self, engine):
        play_ball(engine, 0, 5)
        assert engine.state.current_innings.score == 5

        play_ball(engine, 0, 10)
        assert engine.state.current_innings.score == 15

    def test_zero_vs_zero_is_out(self, engine):
        play_ball(engine, 0, 0)
        assert engine.state.current_innings.wickets == 1
        assert engine.state.phase == GamePhase.INNINGS_BREAK


class TestBowlerSwitching:
    def test_bowler_switches_after_dismissal(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        first_bowler = engine.state.current_bowler_id

        play_ball(engine, 5, 5)  # out
        assert engine.state.current_bowler_id != first_bowler
        assert engine.state.bowler_switch_pending is False

    def test_single_bowler_keeps_bowling(self, engine):
        bowler = engine.state.current_bowler_id
        play_ball(engine, 4, 3)  # runs, no switch
        assert engine.state.current_bowler_id == bowler
        assert engine.state.current_batter_id is not None


class TestToss:
    def test_toss_tie_requires_retoss(self):
        engine = build_engine(players_per_team=1)
        for player in engine.all_players():
            engine.set_ready(player.id)
        engine.start_toss()
        team_1 = engine.state.teams["team-1"].players[0]
        team_2 = engine.state.teams["team-2"].players[0]
        engine.submit_toss(team_1.id, 5)
        engine.submit_toss(team_2.id, 5)
        assert engine.resolve_toss() is None
        assert engine.state.phase == GamePhase.TOSS
        assert engine.state.toss_numbers == {}

    def test_start_toss_requires_ready_players(self):
        engine = build_engine(players_per_team=1)
        for player in engine.all_players():
            engine.set_ready(player.id)
        engine.state.players[next(iter(engine.state.players))].ready_status = (
            ReadyStatus.NOT_READY
        )
        with pytest.raises(EngineError):
            engine.start_toss()

    def test_teams_must_have_players(self):
        engine = GameEngine.create(room_id="room-1")
        with pytest.raises(EngineError):
            engine.start_toss()


class TestInningsCompletion:
    def test_innings_ends_when_all_batters_out(self):
        engine = build_engine(players_per_team=2)
        start_game(engine)
        team_1 = engine.state.teams["team-1"]
        team_2 = engine.state.teams["team-2"]
        assert engine.state.current_batter_id == team_1.players[0].id

        play_ball(engine, 5, 5)  # first batter out
        assert engine.state.current_innings.wickets == 1
        assert engine.state.phase == GamePhase.INNINGS_1
        assert engine.state.current_batter_id == team_1.players[1].id
        assert engine.state.current_bowler_id == team_2.players[1].id
        assert len(engine.state.ball_log) == 1

        play_ball(engine, 3, 3)  # second batter out -> innings complete
        assert engine.state.current_innings.wickets == 2
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.turn_state is None

    def test_max_wickets_cap_ends_innings(self):
        engine = build_engine(players_per_team=1)
        start_game(engine)
        engine.state.max_wickets = 1
        play_ball(engine, 4, 3)  # runs
        assert engine.state.phase == GamePhase.INNINGS_1
        play_ball(engine, 5, 5)  # out -> reaches max_wickets
        assert engine.state.phase == GamePhase.INNINGS_BREAK


class TestTargetCalculation:
    def test_target_is_first_innings_score_plus_one(self):
        engine = build_engine(players_per_team=1)
        start_game(engine)

        play_ball(engine, 4, 3)  # 4 runs
        play_ball(engine, 2, 1)  # 2 runs
        assert engine.state.current_innings.score == 6

        play_ball(engine, 7, 7)  # out -> innings 1 ends
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.target_score == 7
        assert engine.state.innings_number == 1


class TestWinnerCalculation:
    def test_chasing_team_wins_on_reaching_target(self):
        engine = build_engine(players_per_team=1)
        start_game(engine)

        play_ball(engine, 4, 3)  # 4
        play_ball(engine, 2, 1)  # 2 -> 6
        play_ball(engine, 5, 5)  # out, innings 1 ends, target 7
        assert engine.state.target_score == 7

        engine.begin_second_innings()
        assert engine.state.phase == GamePhase.INNINGS_2
        assert engine.state.batting_team_id == "team-2"

        play_ball(engine, 4, 2)  # 4 -> total 4
        assert engine.state.phase == GamePhase.INNINGS_2
        play_ball(engine, 3, 1)  # 3 -> total 7, reaches target
        assert engine.state.phase == GamePhase.GAME_OVER
        assert engine.state.result == GameResult.TEAM_2_WIN
        assert engine.state.winner_team_id == "team-2"

    def test_first_batting_team_wins_when_chase_all_out_below_target(self):
        engine = build_engine(players_per_team=1)
        start_game(engine)

        play_ball(engine, 4, 3)
        play_ball(engine, 2, 1)
        play_ball(engine, 5, 5)  # innings 1 ends, target 7

        engine.begin_second_innings()
        play_ball(engine, 5, 2)  # 5 runs
        assert engine.state.phase == GamePhase.INNINGS_2

        play_ball(engine, 3, 3)  # out -> all out with 5 < 7
        assert engine.state.phase == GamePhase.GAME_OVER
        assert engine.state.result == GameResult.TEAM_1_WIN
        assert engine.state.winner_team_id == "team-1"

    def test_chasing_team_uses_first_batting_decision(self):
        # toss winner chooses to BOWL, so they field first and chase second
        engine = build_engine(players_per_team=1)
        start_game(engine, toss_winner="team-1", decision=TossDecision.BOWLING)
        assert engine.state.batting_team_id == "team-2"
        assert engine.state.bowling_team_id == "team-1"


class TestFlowGuards:
    def test_advance_batter_requires_player_out(self, engine):
        with pytest.raises(EngineError):
            engine.advance_batter()

    def test_begin_second_innings_requires_break(self, engine):
        with pytest.raises(EngineError):
            engine.begin_second_innings()

    def test_full_ball_log_is_recorded(self, engine):
        play_ball(engine, 6, 1)
        last = engine.state.last_ball
        assert last is not None
        assert last.batter_move == 6
        assert last.bowler_move == 1
        assert last.runs == 6
