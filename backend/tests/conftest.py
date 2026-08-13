"""Pytest fixtures for game engine tests."""

import pytest

from helpers import build_engine, start_game


@pytest.fixture
def engine():
    """An engine already in INNINGS_1 with one player per team."""
    return start_game(build_engine(players_per_team=1))
