import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { mockGame, pickName, teamColorPresets } from '../data/mock'

export const SCREENS = {
  landing: 'landing',
  createRoom: 'createRoom',
  joinRoom: 'joinRoom',
  lobby: 'lobby',
  toss: 'toss',
  tossDecision: 'tossDecision',
  gameplay: 'gameplay',
  inningsBreak: 'inningsBreak',
  result: 'result',
}

const BALLS_PER_OVER = 6

function buildOpponentTeam() {
  const used = ['Aarav']
  const captain = { id: 'opp-captain', name: pickName(used) }
  used.push(captain.name)
  const p2 = { id: 'opp-p2', name: pickName(used) }
  used.push(p2.name)
  const p3 = { id: 'opp-p3', name: pickName(used) }
  used.push(p3.name)
  return {
    id: 'B',
    name: 'Team Sky',
    color: teamColorPresets[1],
    captainId: captain.id,
    players: [
      { ...captain, role: 'captain' },
      { ...p2 },
      { ...p3 },
    ],
  }
}

function buildUserTeam(playerName) {
  return {
    id: 'A',
    name: 'Team Emerald',
    color: teamColorPresets[0],
    captainId: 'me',
    players: [{ id: 'me', name: playerName || 'Aarav', role: 'captain' }],
  }
}

function randomMove() {
  return Math.floor(Math.random() * 11)
}

function resolveBall(batterMove, bowlerMove) {
  if (batterMove === bowlerMove) return { type: 'out', runs: 0 }
  if (batterMove === 0) return { type: 'runs', runs: bowlerMove }
  return { type: 'runs', runs: batterMove }
}

function resultTag(runs) {
  if (runs === 6) return 'SIX!'
  if (runs === 4) return 'FOUR!'
  return null
}

function newInnings({ battingTeamId, bowlingTeamId, innings = 1 }) {
  return {
    innings,
    battingTeamId,
    bowlingTeamId,
    battingOrder: [],
    batterIndex: 0,
    bowlerIndex: 0,
    score: 0,
    wickets: 0,
    ballIndex: 0,
    target: null,
    isChasing: false,
    phase: 'pick',
    ballInProgress: false,
    lastTag: null,
    batterMove: null,
    bowlerMove: null,
    result: null,
    inningsOver: false,
    outcome: null,
    winnerTeamId: null,
    byRuns: null,
    byWickets: null,
    firstInningsScore: 0,
    firstInningsWickets: 0,
  }
}

const GameContext = createContext(null)

export function GameProvider({ children }) {
  const [screen, setScreen] = useState(SCREENS.landing)
  const [room, setRoom] = useState(null)
  const [me, setMe] = useState({ id: 'me', name: 'Aarav', teamId: 'A' })
  const [ready, setReady] = useState(false)
  const [playerName, setPlayerName] = useState('')

  const [toss, setToss] = useState({
    call: null,
    outcome: null,
    winnerId: null,
    chosen: null,
  })

  const [game, setGame] = useState(null)
  const timerRef = useRef(null)

  useEffect(() => {
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current)
    }
  }, [])

  useEffect(() => {
    if (game && game.inningsOver) {
      if (game.innings === 1) setScreen(SCREENS.inningsBreak)
      else setScreen(SCREENS.result)
    }
  }, [game])

  const navigate = useCallback((next) => setScreen(next), [])

  const resetGame = useCallback(() => {
    setToss({ call: null, outcome: null, winnerId: null, chosen: null })
    setGame(null)
    setReady(false)
  }, [])

  const createRoom = useCallback(
    ({ name, overs }) => {
      const userName = name.trim() || 'Aarav'
      const userTeam = buildUserTeam(userName)
      const oppTeam = buildOpponentTeam()
      const roomId = mockGame.roomId
      setPlayerName(userName)
      setMe({ id: 'me', name: userName, teamId: 'A' })
      setRoom({
        id: roomId,
        code: roomId,
        hostId: 'me',
        overs: Math.max(1, Math.min(5, Number(overs) || 2)),
        ballsPerOver: BALLS_PER_OVER,
        teams: { A: userTeam, B: oppTeam },
        joined: false,
      })
      resetGame()
      setScreen(SCREENS.lobby)
    },
    [resetGame],
  )

  const joinRoom = useCallback(
    ({ code, name }) => {
      const userName = name.trim() || 'Aarav'
      const userTeam = buildUserTeam(userName)
      const oppTeam = buildOpponentTeam()
      const roomId = (code || '').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6) || mockGame.roomId
      setPlayerName(userName)
      setMe({ id: 'me', name: userName, teamId: 'A' })
      setRoom({
        id: roomId,
        code: roomId,
        hostId: 'me',
        overs: 2,
        ballsPerOver: BALLS_PER_OVER,
        teams: { A: userTeam, B: oppTeam },
        joined: true,
      })
      resetGame()
      setScreen(SCREENS.lobby)
    },
    [resetGame],
  )

  const updateTeam = useCallback((teamId, updater) => {
    setRoom((prev) => {
      if (!prev) return prev
      const teams = { ...prev.teams }
      teams[teamId] = updater(teams[teamId])
      return { ...prev, teams }
    })
  }, [])

  const addTeammate = useCallback(
    (teamId) => {
      updateTeam(teamId, (team) => {
        if (team.players.length >= 6) return team
        const existing = new Set(team.players.map((p) => p.name))
        existing.add(me.name)
        const name = pickName([...existing])
        return {
          ...team,
          players: [...team.players, { id: `${teamId}-auto-${Date.now()}`, name }],
        }
      })
    },
    [me.name, updateTeam],
  )

  const removePlayer = useCallback(
    (teamId, playerId) => {
      updateTeam(teamId, (team) => {
        if (team.captainId === playerId) return team
        if (team.players.length <= 1) return team
        return { ...team, players: team.players.filter((p) => p.id !== playerId) }
      })
    },
    [updateTeam],
  )

  const setTeamColor = useCallback(
    (teamId, color) => {
      updateTeam(teamId, (team) => ({ ...team, color }))
    },
    [updateTeam],
  )

  const startGame = useCallback(() => {
    if (!room) return
    setScreen(SCREENS.toss)
  }, [room])

  const chooseTossCall = useCallback((call) => {
    setToss((prev) => ({ ...prev, call }))
  }, [])

  const makeDecision = useCallback(
    (choice) => {
      if (!room) return
      const myTeamId = 'A'
      const oppTeamId = 'B'
      const battingTeamId = choice === 'bat' ? myTeamId : oppTeamId
      const bowlingTeamId = battingTeamId === 'A' ? 'B' : 'A'
      setToss((prev) => ({ ...prev, chosen: choice }))
      setGame(
        newInnings({
          battingTeamId,
          bowlingTeamId,
          innings: 1,
          battingOrder: room.teams[battingTeamId].players.map((p) => p.id),
        }),
      )
      setScreen(SCREENS.gameplay)
    },
    [room],
  )

  const flipCoin = useCallback(() => {
    if (!toss.call) return
    const outcome = Math.random() < 0.5 ? 'heads' : 'tails'
    const meWon = toss.call === outcome
    setToss((prev) => ({ ...prev, outcome, winnerId: meWon ? 'me' : 'opp' }))
  }, [toss.call])

  const getActingRole = useCallback(() => {
    if (!game) return null
    return game.battingTeamId === me.teamId ? 'batter' : 'bowler'
  }, [game, me.teamId])

  const getCurrentBatter = useCallback(() => {
    if (!game || !room) return null
    const order = game.battingOrder
    if (!order.length) return null
    const idx = Math.min(game.batterIndex, order.length - 1)
    return room.teams[game.battingTeamId]?.players.find((p) => p.id === order[idx]) || null
  }, [game, room])

  const getCurrentBowler = useCallback(() => {
    if (!game || !room) return null
    const team = room.teams[game.bowlingTeamId]
    if (!team || !team.players.length) return null
    const idx = game.bowlerIndex % team.players.length
    return team.players[idx]
  }, [game, room])

  const switchBowler = useCallback(() => {
    if (!game || !room) return
    if (game.phase !== 'pick' || game.ballInProgress) return
    const team = room.teams[game.bowlingTeamId]
    if (!team || team.players.length < 2) return
    setGame((prev) => ({
      ...prev,
      bowlerIndex: (prev.bowlerIndex + 1) % team.players.length,
    }))
  }, [game, room])

  const totalBalls = useCallback(() => {
    if (!room) return 0
    return room.overs * room.ballsPerOver
  }, [room])

  const finishBall = useCallback((state) => {
    const order = state.battingOrder
    const allOut = state.wickets >= order.length
    const oversDone = state.isOver
    const chasing = state.target != null

    if (chasing && state.score >= state.target) {
      return {
        ...state,
        inningsOver: true,
        outcome: 'won',
        winnerTeamId: state.battingTeamId,
        byWickets: order.length - state.wickets,
      }
    }

    if (allOut || oversDone) {
      if (chasing) {
        return {
          ...state,
          inningsOver: true,
          outcome: 'lost',
          winnerTeamId: state.bowlingTeamId,
          byRuns: state.target - 1 - state.score,
        }
      }
      return { ...state, inningsOver: true, outcome: 'declared' }
    }

    return { ...state, inningsOver: false }
  }, [])

  const applyBallOutcome = useCallback(
    (result) => {
      const { type, runs } = result
      setGame((prev) => {
        if (!prev) return prev
        const total = totalBalls()
        const ballIndex = prev.ballIndex + 1
        const isOver = ballIndex >= total

        if (type === 'out') {
          return finishBall({
            ...prev,
            phase: 'pick',
            ballInProgress: false,
            lastTag: 'WICKET!',
            ballIndex,
            isOver,
            wickets: prev.wickets + 1,
            batterIndex: prev.batterIndex + 1,
          })
        }

        const score = prev.score + runs
        const lastTag = resultTag(runs) || (runs > 0 ? `${runs} run${runs > 1 ? 's' : ''}` : 'Dot ball')
        return finishBall({
          ...prev,
          phase: 'pick',
          ballInProgress: false,
          lastTag,
          ballIndex,
          isOver,
          score,
        })
      })
    },
    [totalBalls, finishBall],
  )

  const submitMove = useCallback(
    (value) => {
      if (!game) return
      if (game.phase !== 'pick' || game.ballInProgress) return
      if (!Number.isInteger(value) || value < 0 || value > 10) return

      const role = getActingRole()
      const batterMove = role === 'batter' ? value : randomMove()
      const bowlerMove = role === 'bowler' ? value : randomMove()
      const result = resolveBall(batterMove, bowlerMove)
      const outcome = { type: result.type, runs: result.runs }

      setGame((prev) => ({
        ...prev,
        phase: 'reveal',
        ballInProgress: true,
        batterMove,
        bowlerMove,
      }))

      if (timerRef.current) window.clearTimeout(timerRef.current)
      timerRef.current = window.setTimeout(() => {
        setGame((prev) => ({
          ...prev,
          phase: 'settle',
          result: outcome,
        }))
        timerRef.current = window.setTimeout(() => {
          setGame((prev) => ({ ...prev, result: null }))
          applyBallOutcome(outcome)
        }, 1400)
      }, 1200)
    },
    [game, getActingRole, applyBallOutcome],
  )

  const continueToSecondInnings = useCallback(() => {
    setGame((prev) => {
      if (!prev || !room) return prev
      const target = prev.score + 1
      const next = newInnings({
        battingTeamId: prev.bowlingTeamId,
        bowlingTeamId: prev.battingTeamId,
        battingOrder: room.teams[prev.bowlingTeamId].players.map((p) => p.id),
      })
      return {
        ...next,
        innings: 2,
        target,
        isChasing: true,
        firstInningsScore: prev.score,
        firstInningsWickets: prev.wickets,
      }
    })
    setScreen(SCREENS.gameplay)
  }, [room])

  const backToLobby = useCallback(() => {
    resetGame()
    setScreen(SCREENS.lobby)
  }, [resetGame])

  const value = useMemo(
    () => ({
      screen,
      room,
      me,
      playerName,
      ready,
      setReady,
      toss,
      game,
      navigate,
      createRoom,
      joinRoom,
      addTeammate,
      removePlayer,
      setTeamColor,
      startGame,
      chooseTossCall,
      flipCoin,
      makeDecision,
      submitMove,
      switchBowler,
      getActingRole,
      getCurrentBatter,
      getCurrentBowler,
      totalBalls,
      continueToSecondInnings,
      backToLobby,
    }),
    [
      screen,
      room,
      me,
      playerName,
      ready,
      toss,
      game,
      navigate,
      createRoom,
      joinRoom,
      addTeammate,
      removePlayer,
      setTeamColor,
      startGame,
      chooseTossCall,
      flipCoin,
      makeDecision,
      submitMove,
      switchBowler,
      getActingRole,
      getCurrentBatter,
      getCurrentBowler,
      totalBalls,
      continueToSecondInnings,
      backToLobby,
    ],
  )

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>
}

export function useGame() {
  return useContext(GameContext)
}
