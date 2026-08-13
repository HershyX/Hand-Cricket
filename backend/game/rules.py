"""Pure hand cricket rules.

This module contains no game state and no side effects. Every function is a
pure calculation over move values, which keeps the rules trivially testable.
"""

from __future__ import annotations

from .models import BallOutcome

MIN_MOVE = 0
MAX_MOVE = 10


class IllegalMoveError(ValueError):
    """Raised when a move is not a legal integer in the range 0..10."""


def validate_move(value: object) -> int:
    """Validate a move value.

    Legal moves are integers in the inclusive range MIN_MOVE..MAX_MOVE.
    Booleans are rejected (they subclass int). Decimals, strings, null and
    other malformed values are rejected.

    Returns the validated integer.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise IllegalMoveError(
            f"Move must be an integer between {MIN_MOVE} and {MAX_MOVE}, got {value!r}"
        )
    if value < MIN_MOVE or value > MAX_MOVE:
        raise IllegalMoveError(
            f"Move must be between {MIN_MOVE} and {MAX_MOVE}, got {value}"
        )
    return value


def is_out(batter_move: object, bowler_move: object) -> bool:
    """A batter is out when both players choose the same number."""
    batter = validate_move(batter_move)
    bowler = validate_move(bowler_move)
    return batter == bowler


def calculate_runs(batter_move: object, bowler_move: object) -> tuple[int, BallOutcome]:
    """Resolve a completed ball into (runs, outcome).

    Rules:
      * batter == bowler        -> OUT (including 0 == 0)
      * batter == 0, bowler > 0 -> runs = bowler's number
      * otherwise               -> runs = batter's number
    """
    batter = validate_move(batter_move)
    bowler = validate_move(bowler_move)

    if batter == bowler:
        return 0, BallOutcome.OUT

    if batter == 0:
        return bowler, BallOutcome.RUNS

    return batter, BallOutcome.RUNS


def calculate_target(first_innings_score: int) -> int:
    """A chasing team needs one more run than the first innings total."""
    return first_innings_score + 1
