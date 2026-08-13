"""Toss and innings lifecycle tests for the game engine (Prompt 5).

These tests drive the engine directly (no WebSockets): server-side toss,
toss decisions, innings setup with uneven team sizes, target chase, innings
completion, bowler switching and game-over rules.
"""

import pytest

from game.engine import EngineError, GameEngine
from game.models import GamePhase, GameResult, TossDecision, TurnState

from helpers import build_engine, build_engine_sizes, play_ball, start_game


def ready_and_toss(engine: GameEngine) -> str:
    for player in engine.all_players():
        engine.set_ready(player.id)
    engine.start_toss()
    return engine.perform_toss()


def play_outs(engine: GameEngine, count: int) -> None:
    for _ in range(count):
        play_ball(engine, 5, 5)


class TestServerSideToss:
    def test_perform_toss_returns_a_team(self):
        engine = build_engine(players_per_team=1)
        winner = ready_and_toss(engine)
        assert winner in engine.state.team_order
        assert engine.state.toss_winner_id == winner
        assert engine.state.phase == GamePhase.TOSS_DECISION

    def test_perform_toss_requires_toss_phase(self):
        engine = build_engine(players_per_team=1)
        with pytest.raises(EngineError):
            engine.perform_toss()

    def test_perform_toss_requires_teams(self):
        engine = GameEngine.create(room_id="room-1")
        for player in engine.all_players():
            engine.set_ready(player.id)
        with pytest.raises(EngineError):
            engine.start_toss()


class TestTossDecision:
    def test_winner_batting_decision(self):
        engine = build_engine(players_per_team=1)
        ready_and_toss(engine)
        engine.state.toss_winner_id = "team-1"
        engine.set_toss_decision(TossDecision.BATTING)
        assert engine.state.batting_team_id == "team-1"
        assert engine.state.bowling_team_id == "team-2"
        assert engine.state.phase == GamePhase.INNINGS_1

    def test_winner_bowling_decision(self):
        engine = build_engine(players_per_team=1)
        ready_and_toss(engine)
        engine.state.toss_winner_id = "team-1"
        engine.set_toss_decision(TossDecision.BOWLING)
        assert engine.state.batting_team_id == "team-2"
        assert engine.state.bowling_team_id == "team-1"

    def test_invalid_decision_rejected(self):
        engine = build_engine(players_per_team=1)
        ready_and_toss(engine)
        engine.state.toss_winner_id = "team-1"
        with pytest.raises(EngineError):
            engine.set_toss_decision("SWIM")  # type: ignore[arg-type]

    def test_decision_requires_toss_winner(self):
        engine = build_engine(players_per_team=1)
        ready_and_toss(engine)
        engine.state.toss_winner_id = None
        with pytest.raises(EngineError):
            engine.set_toss_decision(TossDecision.BATTING)


class TestInningsOneSetup:
    @pytest.mark.parametrize("a,b", [(1, 1), (1, 5), (2, 5), (5, 2), (3, 7), (10, 1)])
    def test_innings_one_initial_state(self, a, b):
        engine = build_engine_sizes(a, b)
        start_game(engine, toss_winner="team-1", decision=TossDecision.BATTING)
        state = engine.state
        assert state.innings_number == 1
        assert state.phase == GamePhase.INNINGS_1
        assert state.current_innings.score == 0
        assert state.current_innings.wickets == 0
        assert state.target_score is None
        assert state.max_wickets == a

    def test_first_batter_from_batting_order(self):
        engine = build_engine_sizes(2, 5)
        start_game(engine)
        batting = engine.batting_order()
        assert engine.state.current_batter_id == batting[0].id
        assert engine.state.current_batter_id in {
            p.id for p in engine.state.teams["team-1"].players
        }

    def test_first_bowler_from_bowling_order(self):
        engine = build_engine_sizes(2, 5)
        start_game(engine)
        bowling = engine.bowling_order()
        assert engine.state.current_bowler_id == bowling[0].id
        assert engine.state.current_bowler_id in {
            p.id for p in engine.state.teams["team-2"].players
        }

    def test_batting_order_uses_only_batting_team(self):
        engine = build_engine_sizes(1, 5)
        start_game(engine)
        assert [p.id for p in engine.batting_order()] == [
            p.id for p in engine.state.teams["team-1"].players
        ]

    def test_bowling_order_uses_only_bowling_team(self):
        engine = build_engine_sizes(1, 5)
        start_game(engine)
        assert [p.id for p in engine.bowling_order()] == [
            p.id for p in engine.state.teams["team-2"].players
        ]


class TestInningsOneCompletion:
    @pytest.mark.parametrize("a,b", [(1, 5), (2, 5), (5, 2), (3, 7), (10, 1)])
    def test_innings_one_ends_at_batting_team_size_wickets(self, a, b):
        engine = build_engine_sizes(a, b)
        start_game(engine)
        play_outs(engine, a)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.current_innings.wickets == a
        assert engine.state.target_score == engine.state.current_innings.score + 1

    def test_innings_one_does_not_use_fixed_wicket_cap(self):
        engine = build_engine_sizes(1, 5)
        start_game(engine)
        assert engine.state.max_wickets == 1
        play_outs(engine, 1)
        assert engine.state.phase == GamePhase.INNINGS_BREAK

    def test_bowling_team_size_does_not_limit_innings(self):
        engine = build_engine_sizes(5, 1)
        start_game(engine)
        assert engine.state.max_wickets == 5
        play_outs(engine, 5)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        assert engine.state.current_innings.wickets == 5


class TestSecondInnings:
    def test_roles_swap_and_state_resets(self):
        engine = build_engine_sizes(2, 5)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_outs(engine, 2)
        assert engine.state.phase == GamePhase.INNINGS_BREAK
        target = engine.state.target_score

        engine.begin_second_innings()
        state = engine.state
        assert state.phase == GamePhase.INNINGS_2
        assert state.innings_number == 2
        assert state.batting_team_id == "team-2"
        assert state.bowling_team_id == "team-1"
        assert state.current_innings.score == 0
        assert state.current_innings.wickets == 0
        assert state.target_score == target
        assert state.max_wickets == 5

    def test_second_innings_batting_order(self):
        engine = build_engine_sizes(5, 2)
        start_game(engine, toss_winner="team-1", decision=TossDecision.BOWLING)
        play_outs(engine, 2)
        engine.begin_second_innings()
        assert engine.state.batting_team_id == "team-1"
        assert len(engine.batting_order()) == 5
        assert engine.state.current_batter_id in {
            p.id for p in engine.state.teams["team-1"].players
        }

    def test_second_innings_requires_break(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        with pytest.raises(EngineError):
            engine.begin_second_innings()


class TestTargetChase:
    def test_chasing_team_wins_immediately_on_reaching_target(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)
        assert engine.state.target_score == 5

        engine.begin_second_innings()
        play_ball(engine, 3, 2)
        assert engine.state.phase == GamePhase.INNINGS_2
        play_ball(engine, 2, 1)  # reaches target -> game over immediately
        assert engine.state.phase == GamePhase.GAME_OVER
        assert engine.state.result == GameResult.TEAM_2_WIN
        assert engine.state.winner_team_id == "team-2"
        assert engine.state.game_over_reason == "TARGET_REACHED"

    def test_all_out_below_target_first_team_wins(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)

        engine.begin_second_innings()
        play_ball(engine, 3, 2)
        assert engine.state.phase == GamePhase.INNINGS_2
        play_ball(engine, 5, 5)  # out with score below target
        assert engine.state.phase == GamePhase.GAME_OVER
        assert engine.state.result == GameResult.TEAM_1_WIN
        assert engine.state.winner_team_id == "team-1"
        assert engine.state.game_over_reason == "ALL_OUT"

    def test_chase_continues_below_target(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)

        engine.begin_second_innings()
        play_ball(engine, 2, 1)
        assert engine.state.phase == GamePhase.INNINGS_2
        assert engine.state.result == GameResult.PENDING

    def test_uneven_chase_completes(self):
        engine = build_engine_sizes(1, 5)
        start_game(engine)
        play_outs(engine, 1)  # team-1 scores 0, target 1
        engine.begin_second_innings()
        play_ball(engine, 1, 2)  # reaches target 1
        assert engine.state.phase == GamePhase.GAME_OVER
        assert engine.state.result == GameResult.TEAM_2_WIN

    def test_game_over_blocks_further_turns(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)
        engine.begin_second_innings()
        play_ball(engine, 3, 2)
        play_ball(engine, 2, 1)
        assert engine.state.phase == GamePhase.GAME_OVER
        with pytest.raises(EngineError):
            engine.submit_move(engine.state.current_batter_id, 4)


class TestBowlerSwitching:
    def test_switch_rotates_bowler(self):
        engine = build_engine_sizes(1, 2)
        start_game(engine)
        first = engine.state.current_bowler_id
        new_bowler = engine.switch_bowler(engine.state.teams["team-2"].players[0].id)
        assert new_bowler != first
        assert engine.state.current_bowler_id == new_bowler

    def test_switch_rejects_batting_team_member(self):
        engine = build_engine_sizes(1, 2)
        start_game(engine)
        with pytest.raises(EngineError):
            engine.switch_bowler(engine.state.current_batter_id)

    def test_switch_rejects_after_batter_submits(self):
        engine = build_engine_sizes(1, 2)
        start_game(engine)
        engine.submit_move(engine.state.current_batter_id, 4)
        with pytest.raises(EngineError):
            engine.switch_bowler(engine.state.teams["team-2"].players[0].id)

    def test_switch_rejects_after_bowler_submits(self):
        engine = build_engine_sizes(1, 2)
        start_game(engine)
        engine.submit_move(engine.state.current_bowler_id, 4)
        with pytest.raises(EngineError):
            engine.switch_bowler(engine.state.teams["team-2"].players[0].id)

    def test_switch_rejects_in_wrong_phase(self):
        engine = build_engine_sizes(1, 1)
        with pytest.raises(EngineError):
            engine.switch_bowler(next(iter(engine.state.players.values())).id)

    def test_switch_rejects_after_game_over(self):
        engine = build_engine_sizes(1, 1)
        start_game(engine)
        play_ball(engine, 4, 3)
        play_ball(engine, 5, 5)
        engine.begin_second_innings()
        play_ball(engine, 3, 2)
        play_ball(engine, 2, 1)
        assert engine.state.phase == GamePhase.GAME_OVER
        with pytest.raises(EngineError):
            engine.switch_bowler(engine.state.teams["team-2"].players[0].id)


class TestRoleIsolation:
    def test_batting_player_cannot_bowl(self):
        engine = build_engine_sizes(2, 1)
        start_game(engine)
        inactive_batter = engine.state.teams["team-1"].players[1]
        with pytest.raises(EngineError):
            engine.submit_move(inactive_batter.id, 4)

    def test_bowling_player_cannot_bat(self):
        engine = build_engine_sizes(1, 2)
        start_game(engine)
        inactive_bowler = engine.state.teams["team-2"].players[1]
        with pytest.raises(EngineError):
            engine.submit_move(inactive_bowler.id, 4)
