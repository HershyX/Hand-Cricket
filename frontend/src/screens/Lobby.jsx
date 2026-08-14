import Button from '../components/Button'
import RoomCode from '../components/RoomCode'
import ScreenShell from '../components/ScreenShell'
import TeamPanel from '../components/TeamPanel'
import { useGame } from '../state/GameContext'

const TEAM_KEY = { 'team-1': 'A', 'team-2': 'B' }

export default function Lobby() {
  const {
    room,
    me,
    isHost,
    connection,
    setTeamSizes,
    joinTeam,
    leaveTeam,
    setReady,
    startGame,
    leaveRoom,
  } = useGame()

  if (!room || !me) return null

  const myReady = me.ready_status === 'READY'
  const myTeamKey = me.team_id ? TEAM_KEY[me.team_id] : null
  const sizeOptions = Array.from({ length: room.max_team_size }, (_, i) => i + 1)

  const teamA = room.team_a
  const teamB = room.team_b

  return (
    <ScreenShell
      title="Lobby"
      subtitle={room.status === 'IN_PROGRESS' ? 'Match room' : 'Set up your teams, then start when everyone is ready.'}
      actions={
        <Button size="sm" variant="ghost" onClick={leaveRoom}>
          Leave
        </Button>
      }
    >
      <div className="space-y-4">
        <RoomCode code={room.room_code} />

        {isHost && (
          <div className="rounded-2xl bg-white/5 p-4 ring-1 ring-white/10">
            <span className="mb-2 block text-xs font-black uppercase tracking-wide text-slate-400">
              Team sizes (host)
            </span>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="mb-1.5 block text-xs font-bold text-slate-400">Team A size</span>
                <select
                  value={room.team_a_size}
                  onChange={(e) => setTeamSizes(Number(e.target.value), room.team_b_size)}
                  className="w-full rounded-xl bg-white/5 px-3 py-2.5 text-sm font-black text-slate-100 ring-1 ring-white/10 outline-none transition focus:ring-2 focus:ring-emerald-400"
                >
                  {sizeOptions.map((n) => (
                    <option key={n} value={n} className="bg-slate-900">
                      {n} player{n > 1 ? 's' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <span className="mb-1.5 block text-xs font-bold text-slate-400">Team B size</span>
                <select
                  value={room.team_b_size}
                  onChange={(e) => setTeamSizes(room.team_a_size, Number(e.target.value))}
                  className="w-full rounded-xl bg-white/5 px-3 py-2.5 text-sm font-black text-slate-100 ring-1 ring-white/10 outline-none transition focus:ring-2 focus:ring-emerald-400"
                >
                  {sizeOptions.map((n) => (
                    <option key={n} value={n} className="bg-slate-900">
                      {n} player{n > 1 ? 's' : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <p className="mt-2 text-[11px] font-semibold text-slate-500">
              Each player must join a team; the game starts when both teams are full and ready.
            </p>
          </div>
        )}

        <TeamPanel
          team={teamA}
          teamKey="A"
          myTeamKey={myTeamKey}
          myId={me.id}
          hostId={room.host_player_id}
          onJoinTeam={joinTeam}
          onLeaveTeam={leaveTeam}
        />

        <TeamPanel
          team={teamB}
          teamKey="B"
          myTeamKey={myTeamKey}
          myId={me.id}
          hostId={room.host_player_id}
          onJoinTeam={joinTeam}
          onLeaveTeam={leaveTeam}
        />
      </div>

      <div className="mt-auto space-y-3 pt-6">
        <button
          type="button"
          onClick={() => setReady(!myReady)}
          disabled={connection !== 'connected' || !myTeamKey}
          className={`w-full rounded-2xl py-3.5 text-base font-black transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-40 ${
            myReady
              ? 'bg-emerald-500 text-emerald-950 shadow-lg shadow-emerald-500/25'
              : 'bg-white/5 text-slate-200 ring-1 ring-white/15 hover:bg-white/10'
          }`}
        >
          {myReady ? "✓ You're ready" : 'Tap when ready'}
        </button>

        {isHost ? (
          <Button size="lg" full disabled={!room.can_start} onClick={startGame}>
            Start game
          </Button>
        ) : (
          <Button size="lg" full variant="secondary" disabled>
            Waiting for host to start…
          </Button>
        )}

        <p className="text-center text-xs font-semibold text-slate-500">
          {connection !== 'connected'
            ? 'Connecting to the room…'
            : !myTeamKey
              ? 'Join a team to get ready.'
              : room.can_start
                ? 'All players ready — the host can start.'
                : 'Waiting for all players to join a team and mark ready.'}
        </p>
      </div>
    </ScreenShell>
  )
}
