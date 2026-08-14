import { describe, expect, it } from 'vitest'
import { SCREENS } from '../lib/screens'
import { INITIAL_STATE, reduceServerMessage, screenForPhase } from './serverReducer'

function msg(partial) {
  return { ...partial }
}

const HOST = 'host-1'
const GUEST = 'guest-2'

function roomState(overrides = {}) {
  return msg({
    type: 'room_state',
    room: {
      room_code: 'ABC123',
      host_player_id: HOST,
      status: 'WAITING',
      max_players: 20,
      phase: 'LOBBY',
      team_a_size: 1,
      team_b_size: 1,
      max_team_size: 10,
      team_a: { team_id: 'team-1', name: 'Team A', capacity: 1, player_count: 1, players: [] },
      team_b: { team_id: 'team-2', name: 'Team B', capacity: 1, player_count: 0, players: [] },
      players: [
        { id: HOST, name: 'Alice', team_id: 'team-1', connection_status: 'CONNECTED', ready_status: 'NOT_READY', batting_position: 1 },
        { id: GUEST, name: 'Bob', team_id: null, connection_status: 'CONNECTED', ready_status: 'NOT_READY', batting_position: null },
      ],
      can_start: false,
      ...overrides,
    },
  })
}

function gameState(overrides = {}) {
  return msg({
    type: 'game_state',
    game: {
      game_id: 'g',
      room_id: 'ABC123',
      phase: 'LOBBY',
      turn_state: null,
      teams: {},
      team_order: ['team-1', 'team-2'],
      players: {},
      batting_team_id: null,
      bowling_team_id: null,
      current_batter_id: null,
      current_bowler_id: null,
      current_innings: null,
      innings_number: 0,
      target_score: null,
      toss_winner_id: null,
      toss_decision: null,
      toss_numbers: {},
      batter_submitted: false,
      bowler_submitted: false,
      batter_move: null,
      bowler_move: null,
      bowler_switch_pending: false,
      turn_number: 0,
      ball_count: 0,
      ball_log: [],
      last_ball: null,
      last_outcome: null,
      result: 'PENDING',
      winner_team_id: null,
      game_over_reason: null,
      max_wickets: 2,
      ...overrides,
    },
  })
}

describe('screenForPhase', () => {
  it('maps every backend phase onto a screen', () => {
    expect(screenForPhase('LOBBY')).toBe(SCREENS.lobby)
    expect(screenForPhase('TOSS_DECISION')).toBe(SCREENS.toss)
    expect(screenForPhase('INNINGS_1')).toBe(SCREENS.gameplay)
    expect(screenForPhase('INNINGS_2')).toBe(SCREENS.gameplay)
    expect(screenForPhase('INNINGS_BREAK')).toBe(SCREENS.inningsBreak)
    expect(screenForPhase('GAME_OVER')).toBe(SCREENS.result)
    expect(screenForPhase('UNKNOWN')).toBe(SCREENS.lobby)
  })
})

describe('reduceServerMessage', () => {
  it('stores room state and stays on the lobby', () => {
    const next = reduceServerMessage(INITIAL_STATE, roomState())
    expect(next.room.room_code).toBe('ABC123')
    expect(next.screen).toBe(SCREENS.lobby)
  })

  it('records the toss winner without leaving the toss screen', () => {
    const state = reduceServerMessage(
      reduceServerMessage(INITIAL_STATE, roomState({ phase: 'TOSS_DECISION' })),
      gameState({ phase: 'TOSS_DECISION' }),
    )
    const next = reduceServerMessage(state, msg({ type: 'toss_result', winner_team_id: 'team-1' }))
    expect(next.tossWinnerId).toBe('team-1')
    expect(next.screen).toBe(SCREENS.toss)
  })

  it('moves to gameplay on innings 1', () => {
    const next = reduceServerMessage(
      INITIAL_STATE,
      gameState({ phase: 'INNINGS_1', innings_number: 1 }),
    )
    expect(next.screen).toBe(SCREENS.gameplay)
  })

  it('stores the resolved ball from move_result', () => {
    const ball = {
      innings: 1,
      ball_number: 1,
      batter_id: HOST,
      bowler_id: GUEST,
      batter_move: 4,
      bowler_move: 3,
      runs: 4,
      outcome: 'RUNS',
    }
    const next = reduceServerMessage(INITIAL_STATE, msg({ type: 'move_result', ball }))
    expect(next.ball).toEqual(ball)
  })

  it('surfaces backend errors', () => {
    const next = reduceServerMessage(
      INITIAL_STATE,
      msg({ type: 'error', code: 'TEAM_FULL', message: 'Team A is full' }),
    )
    expect(next.error.code).toBe('TEAM_FULL')
  })

  it('enters the innings break screen', () => {
    const next = reduceServerMessage(
      INITIAL_STATE,
      gameState({ phase: 'INNINGS_BREAK', innings_number: 1, target_score: 5 }),
    )
    expect(next.screen).toBe(SCREENS.inningsBreak)
    expect(next.game.target_score).toBe(5)
  })

  it('moves to gameplay for innings 2', () => {
    const next = reduceServerMessage(
      INITIAL_STATE,
      gameState({ phase: 'INNINGS_2', innings_number: 2 }),
    )
    expect(next.screen).toBe(SCREENS.gameplay)
  })

  it('shows the result screen on game_over and keeps game state', () => {
    let state = reduceServerMessage(INITIAL_STATE, gameState({ phase: 'INNINGS_2' }))
    state = reduceServerMessage(
      state,
      msg({ type: 'game_over', result: 'TEAM_1_WIN', winner_team_id: 'team-1' }),
    )
    expect(state.screen).toBe(SCREENS.result)
  })

  it('clears transient toss/ball state when a fresh lobby arrives', () => {
    let state = reduceServerMessage(
      INITIAL_STATE,
      gameState({ phase: 'INNINGS_2', toss_winner_id: 'team-1' }),
    )
    state = reduceServerMessage(state, msg({ type: 'move_result', ball: { runs: 4 } }))
    state = reduceServerMessage(state, gameState({ phase: 'LOBBY' }))
    expect(state.game.phase).toBe('LOBBY')
    expect(state.tossWinnerId).toBeNull()
    expect(state.ball).toBeNull()
  })

  it('returns to the landing screen when the room is closed', () => {
    const next = reduceServerMessage(INITIAL_STATE, msg({ type: 'room_closed' }))
    expect(next.screen).toBe(SCREENS.landing)
    expect(next.closed).toBe(true)
  })

  it('ignores unknown messages without crashing', () => {
    expect(reduceServerMessage(INITIAL_STATE, msg({ type: 'wat' }))).toEqual(INITIAL_STATE)
  })
})

describe('full flow simulation', () => {
  it('drives lobby -> toss -> decision -> innings 1 -> balls -> break -> innings 2 -> game over', () => {
    let state = reduceServerMessage(INITIAL_STATE, roomState())
    expect(state.screen).toBe(SCREENS.lobby)

    state = reduceServerMessage(state, msg({ type: 'player_joined', player_id: GUEST }))
    state = reduceServerMessage(state, roomState({ can_start: true }))

    state = reduceServerMessage(state, msg({ type: 'game_started' }))
    state = reduceServerMessage(state, roomState({ phase: 'TOSS_DECISION' }))
    state = reduceServerMessage(state, msg({ type: 'toss_result', winner_team_id: 'team-1' }))
    state = reduceServerMessage(state, gameState({ phase: 'TOSS_DECISION', toss_winner_id: 'team-1' }))
    expect(state.screen).toBe(SCREENS.toss)
    expect(state.tossWinnerId).toBe('team-1')

    state = reduceServerMessage(state, msg({ type: 'toss_decision', decision: 'BATTING' }))
    state = reduceServerMessage(state, gameState({ phase: 'INNINGS_1', innings_number: 1 }))
    expect(state.screen).toBe(SCREENS.gameplay)

    state = reduceServerMessage(state, msg({ type: 'move_submitted', player_id: HOST, role: 'batter' }))
    state = reduceServerMessage(
      state,
      gameState({ phase: 'INNINGS_1', innings_number: 1, batter_submitted: true, turn_state: 'WAITING_FOR_MOVES' }),
    )
    state = reduceServerMessage(state, msg({ type: 'move_submitted', player_id: GUEST, role: 'bowler' }))
    state = reduceServerMessage(
      state,
      msg({
        type: 'move_result',
        ball: { innings: 1, ball_number: 1, batter_id: HOST, bowler_id: GUEST, batter_move: 4, bowler_move: 3, runs: 4, outcome: 'RUNS' },
      }),
    )
    state = reduceServerMessage(state, msg({ type: 'score_updated', score: 4, wickets: 0 }))
    state = reduceServerMessage(
      state,
      gameState({ phase: 'INNINGS_1', innings_number: 1, current_innings: { score: 4, wickets: 0, ball_count: 1 }, turn_number: 2 }),
    )
    expect(state.game.current_innings.score).toBe(4)

    state = reduceServerMessage(
      state,
      msg({ type: 'move_result', ball: { innings: 1, batter_id: HOST, bowler_id: GUEST, batter_move: 3, bowler_move: 3, runs: 0, outcome: 'OUT' } }),
    )
    state = reduceServerMessage(state, msg({ type: 'player_out', player_id: HOST, wickets: 1 }))
    state = reduceServerMessage(state, msg({ type: 'innings_complete', innings_number: 1, score: 4, wickets: 1, target: 5 }))
    state = reduceServerMessage(state, msg({ type: 'innings_break', target: 5 }))
    state = reduceServerMessage(state, gameState({ phase: 'INNINGS_BREAK', innings_number: 1, target_score: 5 }))
    expect(state.screen).toBe(SCREENS.inningsBreak)
    expect(state.game.target_score).toBe(5)

    state = reduceServerMessage(state, msg({ type: 'second_innings_started', innings_number: 2, target: 5 }))
    state = reduceServerMessage(state, gameState({ phase: 'INNINGS_2', innings_number: 2, target_score: 5 }))
    expect(state.screen).toBe(SCREENS.gameplay)

    state = reduceServerMessage(
      state,
      msg({ type: 'move_result', ball: { innings: 2, batter_id: GUEST, bowler_id: HOST, batter_move: 5, bowler_move: 0, runs: 5, outcome: 'RUNS' } }),
    )
    state = reduceServerMessage(state, msg({ type: 'score_updated', score: 5, wickets: 0 }))
    state = reduceServerMessage(state, msg({ type: 'game_over', result: 'TEAM_2_WIN', winner_team_id: 'team-2', reason: 'TARGET_REACHED' }))
    state = reduceServerMessage(state, gameState({ phase: 'GAME_OVER', result: 'TEAM_2_WIN' }))
    expect(state.screen).toBe(SCREENS.result)
    expect(state.game.phase).toBe('GAME_OVER')
  })
})
