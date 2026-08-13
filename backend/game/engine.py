"""Hand cricket game engine.

The engine is the authoritative source of truth for a game. It owns a
GameState and performs every state transition: player/team management, ready
status, toss, innings setup, move resolution, wickets, batter/bowler
advancement and game completion.

The engine is fully independent of FastAPI and WebSockets. It can be driven
from a test, a CLI, or an API layer without modification.
"""

from __future__ import annotations

import secrets

from .models import (
    BallOutcome,
    BallRecord,
    GamePhase,
    GameResult,
    GameState,
    Innings,
    Player,
    ReadyStatus,
    Team,
    TossDecision,
    TurnState,
)
from .rules import calculate_runs, calculate_target, validate_move
from .state import create_game_state, new_player_id


class EngineError(Exception):
    """Raised when an engine operation is illegal for the current state."""


class GameEngine:
    """Encapsulates all game rules and state transitions for one game."""

    def __init__(self, state: GameState | None = None) -> None:
        self.state = state if state is not None else create_game_state()

    @classmethod
    def create(cls, room_id: str, game_id: str | None = None) -> "GameEngine":
        """Create a fresh game for a room."""
        return cls(create_game_state(game_id=game_id, room_id=room_id))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _require_phase(self, *phases: GamePhase) -> None:
        if self.state.phase not in phases:
            expected = ", ".join(p.value for p in phases)
            raise EngineError(
                f"Operation not allowed in phase {self.state.phase.value!r} "
                f"(expected {expected})"
            )

    def _get_player(self, player_id: str) -> Player:
        player = self.state.players.get(player_id)
        if player is None:
            raise EngineError(f"Unknown player {player_id!r}")
        return player

    def _team(self, team_id: str) -> Team:
        team = self.state.teams.get(team_id)
        if team is None:
            raise EngineError(f"Unknown team {team_id!r}")
        return team

    def _other_team_id(self, team_id: str) -> str:
        for candidate in self.state.team_order:
            if candidate != team_id:
                return candidate
        raise EngineError(f"Team {team_id!r} has no opponent")

    def _winner_result(self, team_id: str) -> GameResult:
        if team_id == self.state.team_order[0]:
            return GameResult.TEAM_1_WIN
        return GameResult.TEAM_2_WIN

    def _team_sorted_players(self, team_id: str) -> list[Player]:
        return sorted(self._team(team_id).players, key=lambda p: p.batting_position)

    def _renumber_team(self, team: Team) -> None:
        """Rebuild a team's batting order as contiguous 1..N positions.

        The batting order is always based on the actual players on that team,
        so the number of batting positions matches the number of team members.
        """
        for index, player in enumerate(team.players, start=1):
            player.batting_position = index

    def _clear_moves(self) -> None:
        self.state.batter_move = None
        self.state.bowler_move = None
        self.state.batter_submitted = False
        self.state.bowler_submitted = False

    # ------------------------------------------------------------------
    # Players and teams (LOBBY phase)
    # ------------------------------------------------------------------

    def add_player(
        self, name: str, player_id: str | None = None, team_id: str | None = None
    ) -> Player:
        """Add a player to the game. Optionally assign them to a team."""
        self._require_phase(GamePhase.LOBBY)
        pid = player_id or new_player_id()
        if pid in self.state.players:
            raise EngineError(f"Player id {pid!r} already exists")
        player = Player(id=pid, name=name)
        self.state.players[pid] = player
        if team_id is not None:
            self.assign_player_to_team(pid, team_id)
        return player

    def assign_player_to_team(self, player_id: str, team_id: str) -> None:
        """Assign a player to a team (removing them from any previous team)."""
        self._require_phase(GamePhase.LOBBY)
        team = self._team(team_id)
        player = self._get_player(player_id)
        if player.team_id:
            previous = self._team(player.team_id)
            previous.players = [p for p in previous.players if p.id != player_id]
            self._renumber_team(previous)
        player.team_id = team_id
        player.batting_position = len(team.players) + 1
        team.players.append(player)
        self._renumber_team(team)

    def unassign_player(self, player_id: str) -> None:
        """Remove a player from their team, leaving them UNASSIGNED (LOBBY only)."""
        self._require_phase(GamePhase.LOBBY)
        player = self._get_player(player_id)
        if player.team_id is None:
            return
        team = self._team(player.team_id)
        team.players = [p for p in team.players if p.id != player_id]
        player.team_id = None
        player.batting_position = None
        self._renumber_team(team)

    def all_players(self) -> list[Player]:
        return list(self.state.players.values())

    def team_players(self, team_id: str) -> list[Player]:
        """The explicit batting order of a team, in batting order."""
        return self._team_sorted_players(team_id)

    def batting_order(self) -> list[Player]:
        """The batting team's explicit batting order."""
        if self.state.batting_team_id is None:
            return []
        return self._team_sorted_players(self.state.batting_team_id)

    def bowling_order(self) -> list[Player]:
        """The bowling team's list of eligible bowlers, in batting order."""
        if self.state.bowling_team_id is None:
            return []
        return self._team_sorted_players(self.state.bowling_team_id)

    def remove_player(self, player_id: str) -> None:
        """Permanently remove a player from the game (LOBBY only)."""
        self._require_phase(GamePhase.LOBBY)
        player = self._get_player(player_id)
        if player.team_id:
            team = self._team(player.team_id)
            team.players = [p for p in team.players if p.id != player_id]
            self._renumber_team(team)
        del self.state.players[player_id]

    def set_ready(self, player_id: str) -> None:
        self._get_player(player_id).ready_status = ReadyStatus.READY

    def unset_ready(self, player_id: str) -> None:
        self._get_player(player_id).ready_status = ReadyStatus.NOT_READY

    # ------------------------------------------------------------------
    # Toss
    # ------------------------------------------------------------------

    def start_toss(self) -> None:
        """Move from LOBBY to TOSS once every team is ready and populated."""
        self._require_phase(GamePhase.LOBBY, GamePhase.TOSS)
        for team_id in self.state.team_order:
            team = self._team(team_id)
            if not team.players:
                raise EngineError(f"Team {team.name!r} needs at least one player")
        for player in self.all_players():
            if not player.team_id:
                raise EngineError("All players must be assigned to a team before toss")
            if player.ready_status != ReadyStatus.READY:
                raise EngineError(f"Player {player.name!r} is not ready")
        self.state.phase = GamePhase.TOSS
        self.state.toss_winner_id = None
        self.state.toss_decision = None
        self.state.toss_numbers = {}
        self.state.turn_state = None

    def submit_toss(self, player_id: str, number: object) -> None:
        """Record a team's toss number. The first player to submit wins the slot."""
        self._require_phase(GamePhase.TOSS)
        value = validate_move(number)
        player = self._get_player(player_id)
        if not player.team_id:
            raise EngineError("Player is not assigned to a team")
        if player.team_id in self.state.toss_numbers:
            raise EngineError("This team has already submitted its toss number")
        self.state.toss_numbers[player.team_id] = value

    def resolve_toss(self) -> str | None:
        """Resolve the toss. Higher number wins; a tie returns None (retoss).

        Returns the winning team id, or None if the teams tied and must retoss.
        """
        self._require_phase(GamePhase.TOSS)
        if set(self.state.toss_numbers) != set(self.state.team_order):
            raise EngineError("Both teams must submit a toss number first")
        team_1, team_2 = self.state.team_order
        first, second = self.state.toss_numbers[team_1], self.state.toss_numbers[team_2]
        if first == second:
            self.state.toss_numbers = {}
            return None
        winner = team_1 if first > second else team_2
        self.state.toss_winner_id = winner
        self.state.phase = GamePhase.TOSS_DECISION
        return winner

    def perform_toss(self) -> str:
        """Perform the toss server-side, choosing a winner at random.

        The engine is authoritative: the winner is selected here, never by a
        client. Returns the winning team id.
        """
        self._require_phase(GamePhase.TOSS)
        if len(self.state.team_order) < 2:
            raise EngineError("Two teams are required for the toss")
        winner = secrets.choice(self.state.team_order)
        self.state.toss_winner_id = winner
        self.state.phase = GamePhase.TOSS_DECISION
        return winner

    def set_toss_decision(self, decision: TossDecision) -> None:
        """The toss winner chooses to bat or bowl, then innings 1 begins."""
        self._require_phase(GamePhase.TOSS_DECISION)
        if self.state.toss_winner_id is None:
            raise EngineError("No toss winner yet")
        if not isinstance(decision, TossDecision):
            raise EngineError(f"Invalid toss decision: {decision!r}")
        winner = self.state.toss_winner_id
        loser = self._other_team_id(winner)
        if decision == TossDecision.BATTING:
            batting, bowling = winner, loser
        else:
            batting, bowling = loser, winner
        self.state.toss_decision = decision
        self.state.batting_team_id = batting
        self.state.bowling_team_id = bowling
        self._setup_innings(1, batting, bowling)

    def _setup_innings(self, number: int, batting: str, bowling: str) -> None:
        batting_order = self._team_sorted_players(batting)
        bowling_order = self._team_sorted_players(bowling)
        self.state.innings_number = number
        self.state.current_innings = Innings(
            number=number,
            batting_team_id=batting,
            bowling_team_id=bowling,
            target=self.state.target_score if number == 2 else None,
        )
        self.state.batting_team_id = batting
        self.state.bowling_team_id = bowling
        self.state.phase = GamePhase.INNINGS_1 if number == 1 else GamePhase.INNINGS_2
        self.state.bowler_switch_pending = False
        self.state.max_wickets = len(batting_order)
        self._clear_moves()
        self.state.current_batter_id = batting_order[0].id
        self.state.current_bowler_id = bowling_order[0].id
        self.state.turn_state = TurnState.WAITING_FOR_MOVES

    # ------------------------------------------------------------------
    # Gameplay
    # ------------------------------------------------------------------

    def submit_move(self, player_id: str, number: object) -> None:
        """Submit a move for the current batter or bowler.

        When both have submitted, the ball is resolved automatically.
        """
        self._require_phase(GamePhase.INNINGS_1, GamePhase.INNINGS_2)
        if self.state.turn_state != TurnState.WAITING_FOR_MOVES:
            raise EngineError(
                f"Cannot submit a move while in turn state {self.state.turn_state.value}"
            )
        value = validate_move(number)
        player = self._get_player(player_id)

        if player.id == self.state.current_batter_id:
            if self.state.batter_submitted:
                raise EngineError("Batter has already submitted a move")
            self.state.batter_move = value
            self.state.batter_submitted = True
        elif player.id == self.state.current_bowler_id:
            if self.state.bowler_submitted:
                raise EngineError("Bowler has already submitted a move")
            self.state.bowler_move = value
            self.state.bowler_submitted = True
        else:
            raise EngineError("Player is neither the current batter nor bowler")

        if self.state.batter_submitted and self.state.bowler_submitted:
            self.resolve_move()

    def submit_batting_move(self, player_id: str, number: object) -> None:
        """Submit a move as the current batter (role-enforced)."""
        if player_id != self.state.current_batter_id:
            raise EngineError("Only the current batter may submit a batting move")
        self.submit_move(player_id, number)

    def submit_bowling_move(self, player_id: str, number: object) -> None:
        """Submit a move as the current bowler (role-enforced)."""
        if player_id != self.state.current_bowler_id:
            raise EngineError("Only the current bowler may submit a bowling move")
        self.submit_move(player_id, number)

    def resolve_move(self) -> BallOutcome:
        """Resolve the completed ball and update scores / wickets / state."""
        if not (self.state.batter_submitted and self.state.bowler_submitted):
            raise EngineError("Both batter and bowler must submit a move first")

        self.state.turn_state = TurnState.RESOLVING_MOVE
        runs, outcome = calculate_runs(self.state.batter_move, self.state.bowler_move)
        innings = self.state.current_innings

        innings.ball_count += 1
        ball = BallRecord(
            innings=innings.number,
            ball_number=innings.ball_count,
            batter_id=self.state.current_batter_id,
            bowler_id=self.state.current_bowler_id,
            batter_move=self.state.batter_move,
            bowler_move=self.state.bowler_move,
            runs=runs,
            outcome=outcome,
        )
        self.state.ball_log.append(ball)
        self.state.last_ball = ball
        self.state.last_outcome = outcome

        if outcome == BallOutcome.OUT:
            self.record_wicket()
            self.state.bowler_switch_pending = True
            self.state.turn_state = TurnState.PLAYER_OUT
            return outcome

        innings.score += runs
        self._team(innings.batting_team_id).score = innings.score
        self._clear_moves()

        if (
            innings.number == 2
            and self.state.target_score is not None
            and innings.score >= self.state.target_score
        ):
            self._finish_game(innings.batting_team_id, "TARGET_REACHED")
            return outcome

        self.state.turn_state = TurnState.WAITING_FOR_MOVES
        return outcome

    def record_wicket(self) -> None:
        """Record a wicket against the current batting team."""
        innings = self.state.current_innings
        innings.wickets += 1
        team = self._team(innings.batting_team_id)
        team.wickets = innings.wickets

    def advance_batter(self) -> str | None:
        """Advance past an out: move to the next batter, or end the innings.

        Returns the new batter id, or None if the innings ended.
        """
        if self.state.turn_state != TurnState.PLAYER_OUT:
            raise EngineError("advance_batter requires turn_state PLAYER_OUT")

        if self.check_innings_complete():
            self._handle_innings_end()
            return None

        innings = self.state.current_innings
        ordered = self._team_sorted_players(innings.batting_team_id)
        current_index = next(
            i for i, p in enumerate(ordered) if p.id == self.state.current_batter_id
        )
        self.state.current_batter_id = ordered[current_index + 1].id

        self.apply_bowler_switch()
        self._clear_moves()
        self.state.turn_state = TurnState.WAITING_FOR_MOVES
        return self.state.current_batter_id

    def apply_bowler_switch(self) -> str:
        """Rotate to the next bowler on the bowling team (round-robin)."""
        innings = self.state.current_innings
        ordered = self._team_sorted_players(innings.bowling_team_id)
        current_index = next(
            i for i, p in enumerate(ordered) if p.id == self.state.current_bowler_id
        )
        self.state.current_bowler_id = ordered[(current_index + 1) % len(ordered)].id
        self.state.bowler_switch_pending = False
        return self.state.current_bowler_id

    def switch_bowler(self, player_id: str) -> str:
        """Manually rotate to the next bowler.

        Only a member of the bowling team may switch, and only while the ball is
        waiting for moves (before the batter submits). After the batter has
        submitted the switch is rejected, so the batter's move is never exposed
        during a switch.
        """
        self._require_phase(GamePhase.INNINGS_1, GamePhase.INNINGS_2)
        if self.state.turn_state != TurnState.WAITING_FOR_MOVES:
            raise EngineError(
                f"Cannot switch the bowler while in turn state {self.state.turn_state.value}"
            )
        if self.state.batter_submitted or self.state.bowler_submitted:
            raise EngineError("Cannot switch the bowler after a move has been submitted")
        player = self._get_player(player_id)
        if player.team_id != self.state.bowling_team_id:
            raise EngineError("Only a member of the bowling team can switch the bowler")
        return self.apply_bowler_switch()

    def check_innings_complete(self) -> bool:
        """True when the current innings has no batters left to face up."""
        innings = self.state.current_innings
        if innings is None:
            return True
        if innings.wickets >= self.state.max_wickets:
            return True
        ordered = self._team_sorted_players(innings.batting_team_id)
        current_index = next(
            (
                i
                for i, p in enumerate(ordered)
                if p.id == self.state.current_batter_id
            ),
            None,
        )
        return current_index is None or current_index == len(ordered) - 1

    def _handle_innings_end(self) -> None:
        innings = self.state.current_innings
        self._clear_moves()
        if innings.number == 1:
            self.state.target_score = calculate_target(innings.score)
            self.state.phase = GamePhase.INNINGS_BREAK
            self.state.turn_state = None
        else:
            self.check_game_over()

    def begin_second_innings(self) -> None:
        """Swap roles and start innings 2 after the innings break."""
        self._require_phase(GamePhase.INNINGS_BREAK)
        if self.state.target_score is None:
            raise EngineError("Target has not been calculated yet")
        self._setup_innings(2, self.state.bowling_team_id, self.state.batting_team_id)

    def check_game_over(self) -> GameResult:
        """Determine the winner once the second innings has ended.

        The chasing team wins by reaching the target; otherwise the team that
        batted first wins. The reason is recorded on the state.
        """
        innings = self.state.current_innings
        if innings.number != 2:
            return GameResult.PENDING
        target = self.state.target_score
        if target is None:
            raise EngineError("Target has not been calculated yet")
        if innings.score >= target:
            self._finish_game(innings.batting_team_id, "TARGET_REACHED")
        else:
            self._finish_game(
                self._other_team_id(innings.batting_team_id), "ALL_OUT"
            )
        return self.state.result

    def _finish_game(self, winner_team_id: str, reason: str) -> None:
        self.state.winner_team_id = winner_team_id
        self.state.result = self._winner_result(winner_team_id)
        self.state.phase = GamePhase.GAME_OVER
        self.state.turn_state = None
        self.state.game_over_reason = reason
