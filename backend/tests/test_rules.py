"""Tests for the pure hand cricket rules."""

import pytest

from game.models import BallOutcome
from game.rules import IllegalMoveError, calculate_runs, calculate_target, validate_move


class TestScoring:
    def test_5_vs_3_scores_5(self):
        runs, outcome = calculate_runs(5, 3)
        assert runs == 5
        assert outcome == BallOutcome.RUNS

    def test_10_vs_2_scores_10(self):
        runs, outcome = calculate_runs(10, 2)
        assert runs == 10
        assert outcome == BallOutcome.RUNS

    def test_0_vs_5_scores_5(self):
        runs, outcome = calculate_runs(0, 5)
        assert runs == 5
        assert outcome == BallOutcome.RUNS

    def test_0_vs_10_scores_10(self):
        runs, outcome = calculate_runs(0, 10)
        assert runs == 10
        assert outcome == BallOutcome.RUNS

    def test_5_vs_5_is_out(self):
        runs, outcome = calculate_runs(5, 5)
        assert runs == 0
        assert outcome == BallOutcome.OUT

    def test_0_vs_0_is_out(self):
        runs, outcome = calculate_runs(0, 0)
        assert runs == 0
        assert outcome == BallOutcome.OUT


class TestMoveValidation:
    @pytest.mark.parametrize("move", [-1, 11, -10, 100])
    def test_rejects_out_of_range(self, move):
        with pytest.raises(IllegalMoveError):
            validate_move(move)
        with pytest.raises(IllegalMoveError):
            calculate_runs(move, 3)

    @pytest.mark.parametrize("move", [3.14, "5", None, True, [3], {"n": 3}])
    def test_rejects_non_integer(self, move):
        with pytest.raises(IllegalMoveError):
            validate_move(move)
        with pytest.raises(IllegalMoveError):
            calculate_runs(move, 3)

    def test_accepts_boundaries(self):
        assert validate_move(0) == 0
        assert validate_move(10) == 10


class TestTarget:
    def test_target_is_first_innings_plus_one(self):
        assert calculate_target(0) == 1
        assert calculate_target(12) == 13
        assert calculate_target(100) == 101
