import { describe, expect, it } from 'vitest'
import {
  canSubmitMove,
  canSwitchBowler,
  iHaveSubmitted,
  myRole,
  opponentSubmitted,
  outcomeLabel,
  playerById,
  runsNeeded,
  scoreLine,
  teamLabel,
} from './gameView'

const ME = { id: 'host-1', name: 'Alice', team_id: 'team-1' }
const OPP = { id: 'guest-2', name: 'Bob', team_id: 'team-2' }

function game(overrides = {}) {
  return {
    phase: 'INNINGS_1',
    innings_number: 1,
    turn_state: 'WAITING_FOR_MOVES',
    batting_team_id: 'team-1',
    bowling_team_id: 'team-2',
    current_batter_id: ME.id,
    current_bowler_id: OPP.id,
    batter_submitted: false,
    bowler_submitted: false,
    target_score: null,
    current_innings: { number: 1, batting_team_id: 'team-1', bowling_team_id: 'team-2', score: 12, wickets: 2, ball_count: 7, target: null },
    players: { [ME.id]: ME, [OPP.id]: OPP },
    ...overrides,
  }
}

describe('teamLabel', () => {
  it('maps internal team ids onto lobby labels', () => {
    expect(teamLabel('team-1')).toBe('Team A')
    expect(teamLabel('team-2')).toBe('Team B')
    expect(teamLabel('team-9')).toBe('team-9')
  })
})

describe('myRole', () => {
  it('returns batter for the batting team', () => {
    expect(myRole(game(), ME)).toBe('batter')
  })
  it('returns bowler for the bowling team', () => {
    expect(myRole(game(), OPP)).toBe('bowler')
  })
  it('returns null before roles are set', () => {
    expect(myRole(game({ batting_team_id: null, bowling_team_id: null }), ME)).toBeNull()
  })
})

describe('canSubmitMove', () => {
  it('allows the active batter before submission', () => {
    expect(canSubmitMove(game(), ME)).toBe(true)
  })
  it('blocks when the player already submitted', () => {
    expect(canSubmitMove(game({ batter_submitted: true }), ME)).toBe(false)
  })
  it('blocks outside the waiting-for-moves turn state', () => {
    expect(canSubmitMove(game({ turn_state: 'PLAYER_OUT' }), ME)).toBe(false)
  })
  it('blocks outside innings phases', () => {
    expect(canSubmitMove(game({ phase: 'INNINGS_BREAK' }), ME)).toBe(false)
  })
  it('allows the active bowler before submission', () => {
    expect(canSubmitMove(game(), OPP)).toBe(true)
    expect(canSubmitMove(game({ bowler_submitted: true }), OPP)).toBe(false)
  })
})

describe('submission flags', () => {
  it('tracks own and opponent submission by role', () => {
    expect(iHaveSubmitted(game({ batter_submitted: true }), 'batter')).toBe(true)
    expect(iHaveSubmitted(game({ batter_submitted: true }), 'bowler')).toBe(false)
    expect(opponentSubmitted(game({ bowler_submitted: true }), 'batter')).toBe(true)
    expect(opponentSubmitted(game({ bowler_submitted: true }), 'batter')).toBe(true)
    expect(opponentSubmitted(game({ bowler_submitted: false }), 'batter')).toBe(false)
    expect(opponentSubmitted(game({ batter_submitted: true }), 'bowler')).toBe(true)
  })
})

describe('canSwitchBowler', () => {
  it('allows only a bowling-team member before any submission', () => {
    expect(canSwitchBowler(game(), OPP)).toBe(true)
    expect(canSwitchBowler(game(), ME)).toBe(false)
    expect(canSwitchBowler(game({ batter_submitted: true }), OPP)).toBe(false)
    expect(canSwitchBowler(game({ turn_state: 'PLAYER_OUT' }), OPP)).toBe(false)
  })
})

describe('scoring helpers', () => {
  it('reads score and wickets from the server innings', () => {
    expect(scoreLine(game())).toEqual({ score: 12, wickets: 2 })
  })
  it('computes runs needed only in a chase', () => {
    expect(runsNeeded(game({ target_score: 15 }))).toBe(3)
    expect(runsNeeded(game({ target_score: null }))).toBeNull()
  })
  it('never reports negative runs needed', () => {
    expect(runsNeeded(game({ target_score: 10 }))).toBe(0)
  })
})

describe('outcomeLabel', () => {
  it('labels balls from the server record', () => {
    expect(outcomeLabel({ outcome: 'OUT' }).text).toBe('WICKET!')
    expect(outcomeLabel({ outcome: 'RUNS', runs: 0 }).text).toBe('Dot ball')
    expect(outcomeLabel({ outcome: 'RUNS', runs: 6 }).text).toBe('SIX!')
    expect(outcomeLabel({ outcome: 'RUNS', runs: 4 }).text).toBe('FOUR!')
    expect(outcomeLabel({ outcome: 'RUNS', runs: 2 }).text).toBe('2 runs')
    expect(outcomeLabel(null)).toBeNull()
  })
})

describe('playerById', () => {
  it('resolves players from the game players map first, then room players', () => {
    expect(playerById(game(), null, ME.id).name).toBe('Alice')
    expect(
      playerById(null, { players: [{ id: 'x', name: 'Carol' }] }, 'x').name,
    ).toBe('Carol')
    expect(playerById(game(), null, 'missing')).toBeNull()
  })
})
