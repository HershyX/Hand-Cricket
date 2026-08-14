export function playerById(game, room, id) {
  if (!id) return null
  if (game?.players && game.players[id]) return game.players[id]
  if (room?.players) return room.players.find((p) => p.id === id) || null
  return null
}

export function teamLabel(teamId) {
  if (teamId === 'team-1') return 'Team A'
  if (teamId === 'team-2') return 'Team B'
  return teamId
}

export function currentInnings(game) {
  return game?.current_innings ?? null
}

export function scoreLine(game) {
  const innings = currentInnings(game)
  return {
    score: innings?.score ?? 0,
    wickets: innings?.wickets ?? 0,
  }
}

export function targetOf(game) {
  return game?.target_score ?? null
}

export function runsNeeded(game) {
  const target = targetOf(game)
  if (target == null) return null
  return Math.max(0, target - scoreLine(game).score)
}

export function isChasing(game) {
  return game?.innings_number === 2
}

export function myRole(game, me) {
  if (!game || !me) return null
  if (game.batting_team_id == null || game.bowling_team_id == null) return null
  if (me.team_id === game.batting_team_id) return 'batter'
  if (me.team_id === game.bowling_team_id) return 'bowler'
  return null
}

export function canSubmitMove(game, me) {
  const role = myRole(game, me)
  if (!role) return false
  if (game.phase !== 'INNINGS_1' && game.phase !== 'INNINGS_2') return false
  if (game.turn_state !== 'WAITING_FOR_MOVES') return false
  if (role === 'batter') return !game.batter_submitted
  return !game.bowler_submitted
}

export function iHaveSubmitted(game, role) {
  if (role === 'batter') return game?.batter_submitted === true
  if (role === 'bowler') return game?.bowler_submitted === true
  return false
}

export function opponentSubmitted(game, role) {
  if (role === 'batter') return game?.bowler_submitted === true
  if (role === 'bowler') return game?.batter_submitted === true
  return false
}

export function canSwitchBowler(game, me) {
  if (!game || !me) return false
  if (game.phase !== 'INNINGS_1' && game.phase !== 'INNINGS_2') return false
  if (game.turn_state !== 'WAITING_FOR_MOVES') return false
  if (me.team_id !== game.bowling_team_id) return false
  return !game.batter_submitted && !game.bowler_submitted
}

export function outcomeLabel(ball) {
  if (!ball) return null
  if (ball.outcome === 'OUT') return { text: 'WICKET!', tone: 'rose' }
  if (ball.runs === 0) return { text: 'Dot ball', tone: 'slate' }
  if (ball.runs === 6) return { text: 'SIX!', tone: 'amber' }
  if (ball.runs === 4) return { text: 'FOUR!', tone: 'amber' }
  return { text: `${ball.runs} run${ball.runs > 1 ? 's' : ''}`, tone: 'green' }
}
