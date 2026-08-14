import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import { createRoom as apiCreateRoom, joinRoom as apiJoinRoom } from '../lib/api'
import { wsBaseUrl } from '../config'
import { myRole } from '../lib/gameView'
import { SCREENS } from '../lib/screens'
import { createSocket } from '../lib/ws'
import { INITIAL_STATE, reduceServerMessage } from './serverReducer'

export { SCREENS }

const GameContext = createContext(null)

export function GameProvider({ children }) {
  const [state, setState] = useState(INITIAL_STATE)
  const [session, setSession] = useState(null)
  const [connection, setConnection] = useState('idle')
  const [busy, setBusy] = useState(false)
  const socketRef = useRef(null)

  useEffect(
    () => () => {
      if (socketRef.current) socketRef.current.close()
    },
    [],
  )

  useEffect(() => {
    if (!state.ball) return undefined
    const current = state.ball
    const timer = window.setTimeout(() => {
      setState((prev) => (prev.ball === current ? { ...prev, ball: null } : prev))
    }, 1800)
    return () => window.clearTimeout(timer)
  }, [state.ball])

  useEffect(() => {
    if (!state.error) return undefined
    const timer = window.setTimeout(() => {
      setState((prev) => (prev.error ? { ...prev, error: null } : prev))
    }, 6000)
    return () => window.clearTimeout(timer)
  }, [state.error])

  const openSocket = useCallback((sess) => {
    if (socketRef.current) socketRef.current.close()
    const url = `${wsBaseUrl()}/${sess.roomCode}/${sess.playerId}`
    const socket = createSocket(url)
    socketRef.current = socket
    setConnection('connecting')

    socket.on((event, payload) => {
      if (event === 'open') {
        setConnection('connected')
      } else if (event === 'close') {
        setConnection(socket.isClosedByClient ? 'idle' : 'disconnected')
      } else if (event === 'message') {
        const message = payload
        if (message.type === 'room_closed') {
          socket.close()
          setSession(null)
          setConnection('idle')
          setState((prev) => reduceServerMessage({ ...prev }, message))
          return
        }
        setState((prev) => reduceServerMessage(prev, message))
      }
    })
  }, [])

  const send = useCallback((type, payload = {}) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) return false
    return socket.send(type, payload)
  }, [])

  const resetToLanding = useCallback(() => {
    if (socketRef.current) socketRef.current.close()
    setSession(null)
    setConnection('idle')
    setState(INITIAL_STATE)
  }, [])

  const createRoom = useCallback(
    async ({ name }) => {
      setBusy(true)
      try {
        const data = await apiCreateRoom(name)
        const sess = {
          roomCode: data.room_code,
          playerId: data.player_id,
          playerName: (name || '').trim() || data.room.players[0]?.name || 'Host',
          isHost: true,
        }
        setSession(sess)
        setState((prev) => ({
          ...prev,
          room: data.room,
          game: null,
          screen: SCREENS.lobby,
          error: null,
          closed: false,
        }))
        openSocket(sess)
        return { ok: true }
      } catch (err) {
        return { ok: false, error: err.message }
      } finally {
        setBusy(false)
      }
    },
    [openSocket],
  )

  const joinRoom = useCallback(
    async ({ code, name }) => {
      setBusy(true)
      try {
        const data = await apiJoinRoom(code, name)
        const sess = {
          roomCode: data.room_code,
          playerId: data.player_id,
          playerName: (name || '').trim() || 'Player',
          isHost: false,
        }
        setSession(sess)
        setState((prev) => ({
          ...prev,
          room: data.room,
          game: null,
          screen: SCREENS.lobby,
          error: null,
          closed: false,
        }))
        openSocket(sess)
        return { ok: true }
      } catch (err) {
        return { ok: false, error: err.message }
      } finally {
        setBusy(false)
      }
    },
    [openSocket],
  )

  const me = useMemo(() => {
    if (!session) return null
    if (state.game?.players && state.game.players[session.playerId]) {
      return state.game.players[session.playerId]
    }
    if (state.room) {
      return state.room.players.find((p) => p.id === session.playerId) || null
    }
    return null
  }, [session, state.game, state.room])

  const isHost = useMemo(() => {
    if (state.room) return state.room.host_player_id === session?.playerId
    return session?.isHost ?? false
  }, [state.room, session])

  const actions = useMemo(
    () => ({
      setTeamSizes: (teamA, teamB) => send('set_team_sizes', { team_a_size: teamA, team_b_size: teamB }),
      joinTeam: (team) => send('join_team', { team }),
      leaveTeam: () => send('leave_team'),
      setReady: (ready) => send('set_ready', { ready }),
      startGame: () => send('start_game'),
      resetLobby: () => send('reset_lobby'),
      tossDecision: (decision) => send('toss_decision', { decision }),
      submitMove: (value) => {
        const role = myRole(state.game, me)
        if (!role) return false
        return send(role === 'batter' ? 'submit_batting_move' : 'submit_bowling_move', { move: value })
      },
      switchBowler: () => send('switch_bowler'),
      beginSecondInnings: () => send('begin_second_innings'),
      leaveRoom: () => {
        if (socketRef.current) {
          if (socketRef.current.readyState === WebSocket.OPEN) {
            socketRef.current.send('leave_room')
          }
          socketRef.current.close()
        }
        setSession(null)
        setConnection('idle')
        setState(INITIAL_STATE)
      },
      backToHome: resetToLanding,
    }),
    [send, state.game, me, resetToLanding],
  )

  const value = useMemo(
    () => ({
      screen: state.screen,
      room: state.room,
      game: state.game,
      session,
      me,
      isHost,
      busy,
      connection,
      error: state.error,
      ball: state.ball,
      tossWinnerId: state.tossWinnerId,
      closed: state.closed,
      navigate: (next) => setState((prev) => ({ ...prev, screen: next })),
      createRoom,
      joinRoom,
      ...actions,
    }),
    [state, session, me, isHost, busy, connection, createRoom, joinRoom, actions],
  )

  return <GameContext.Provider value={value}>{children}</GameContext.Provider>
}

export function useGame() {
  return useContext(GameContext)
}
