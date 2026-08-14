import { SCREENS } from '../lib/screens'

const PHASE_TO_SCREEN = {
  LOBBY: SCREENS.lobby,
  TOSS: SCREENS.toss,
  TOSS_DECISION: SCREENS.toss,
  INNINGS_1: SCREENS.gameplay,
  INNINGS_2: SCREENS.gameplay,
  INNINGS_BREAK: SCREENS.inningsBreak,
  GAME_OVER: SCREENS.result,
}

export function screenForPhase(phase, fallback = SCREENS.lobby) {
  return PHASE_TO_SCREEN[phase] ?? fallback
}

export const INITIAL_STATE = {
  screen: SCREENS.landing,
  room: null,
  game: null,
  tossWinnerId: null,
  ball: null,
  error: null,
  closed: false,
}

function applyGameState(state, game) {
  const screen = screenForPhase(game.phase, state.screen)
  if (game.phase === 'LOBBY') {
    return { ...state, game, screen, tossWinnerId: null, ball: null, error: null }
  }
  return { ...state, game, screen, error: null }
}

export function reduceServerMessage(state, message) {
  switch (message.type) {
    case 'room_state': {
      const room = message.room
      return {
        ...state,
        room,
        screen: room && room.phase === 'LOBBY' ? SCREENS.lobby : state.screen,
        error: null,
      }
    }
    case 'game_state':
      return applyGameState(state, message.game)
    case 'toss_result':
      return { ...state, tossWinnerId: message.winner_team_id ?? null }
    case 'move_result':
      return { ...state, ball: message.ball ?? null, error: null }
    case 'game_over':
      return { ...state, screen: SCREENS.result }
    case 'room_closed':
      return { ...state, closed: true, screen: SCREENS.landing }
    case 'error':
      return { ...state, error: { code: message.code, message: message.message } }
    case 'pong':
    case 'player_joined':
    case 'player_left':
    case 'player_connected':
    case 'player_reconnected':
    case 'player_disconnected':
    case 'player_ready':
    case 'player_team_changed':
    case 'team_sizes_updated':
    case 'game_started':
    case 'lobby_reset':
    case 'move_submitted':
    case 'score_updated':
    case 'player_out':
    case 'next_turn':
    case 'bowler_changed':
    case 'innings_complete':
    case 'innings_break':
    case 'innings_started':
    case 'second_innings_started':
    case 'toss_decision':
      return { ...state, error: null }
    default:
      return state
  }
}
