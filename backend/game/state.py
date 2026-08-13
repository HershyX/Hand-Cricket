"""Game state factories and identity helpers.

State creation is kept separate from the engine so that callers can build a
GameState (e.g. for tests or persisted snapshots) without going through the
engine's lifecycle methods.
"""

from __future__ import annotations

import uuid

from .models import GamePhase, GameState, Team

TEAM_1_ID = "team-1"
TEAM_2_ID = "team-2"


def new_game_id() -> str:
    return uuid.uuid4().hex


def new_room_id() -> str:
    return uuid.uuid4().hex


def new_player_id() -> str:
    return uuid.uuid4().hex


def create_game_state(game_id: str | None = None, room_id: str | None = None) -> GameState:
    """Create a fresh game state with the two standard teams registered.

    Teams start empty; players are added and assigned in the LOBBY phase.
    """
    team_1 = Team(id=TEAM_1_ID, name="Team 1")
    team_2 = Team(id=TEAM_2_ID, name="Team 2")

    return GameState(
        game_id=game_id or new_game_id(),
        room_id=room_id or new_room_id(),
        teams={TEAM_1_ID: team_1, TEAM_2_ID: team_2},
        team_order=[TEAM_1_ID, TEAM_2_ID],
        players={},
        phase=GamePhase.LOBBY,
    )
