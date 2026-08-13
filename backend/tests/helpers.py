"""Shared helpers for game engine tests."""

from __future__ import annotations

from game.engine import GameEngine
from game.models import GamePhase, TossDecision, TurnState


def build_engine(players_per_team: int = 1) -> GameEngine:
    """Create an engine in LOBBY with players_per_team players on each team."""
    engine = GameEngine.create(room_id="room-1")
    for i in range(players_per_team):
        engine.add_player(name=f"T1-P{i + 1}", team_id="team-1")
        engine.add_player(name=f"T2-P{i + 1}", team_id="team-2")
    return engine


def build_engine_sizes(team_a_size: int, team_b_size: int) -> GameEngine:
    """Create an engine in LOBBY with the given team sizes."""
    engine = GameEngine.create(room_id="room-1")
    for i in range(team_a_size):
        engine.add_player(name=f"T1-P{i + 1}", team_id="team-1")
    for i in range(team_b_size):
        engine.add_player(name=f"T2-P{i + 1}", team_id="team-2")
    return engine


def start_game(
    engine: GameEngine,
    toss_winner: str = "team-1",
    decision: TossDecision = TossDecision.BATTING,
) -> GameEngine:
    """Drive an engine from LOBBY through the toss into INNINGS_1."""
    for player in engine.all_players():
        engine.set_ready(player.id)
    engine.start_toss()

    high_team, low_team = (
        ("team-1", "team-2") if toss_winner == "team-1" else ("team-2", "team-1")
    )
    engine.submit_toss(engine.state.teams[high_team].players[0].id, 6)
    engine.submit_toss(engine.state.teams[low_team].players[0].id, 4)
    winner = engine.resolve_toss()
    assert winner == toss_winner, "toss did not produce the expected winner"

    engine.set_toss_decision(decision)
    assert engine.state.phase == GamePhase.INNINGS_1
    return engine


def play_ball(engine: GameEngine, batter_move: int, bowler_move: int) -> None:
    """Submit both moves for the current batter/bowler and advance past outs."""
    engine.submit_move(engine.state.current_batter_id, batter_move)
    engine.submit_move(engine.state.current_bowler_id, bowler_move)
    if engine.state.turn_state == TurnState.PLAYER_OUT:
        engine.advance_batter()
