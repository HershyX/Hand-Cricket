import { useMemo, useState } from 'react'
import Button from '../components/Button'
import RoomCode from '../components/RoomCode'
import ScreenShell from '../components/ScreenShell'
import TeamPanel from '../components/TeamPanel'
import { useGame, SCREENS } from '../state/GameContext'
import { teamColorPresets } from '../data/mock'

export default function Lobby() {
  const {
    room,
    me,
    ready,
    setReady,
    addTeammate,
    removePlayer,
    setTeamColor,
    startGame,
    navigate,
  } = useGame()
  const [overs, setOvers] = useState(room?.overs || 2)

  const canStart = useMemo(
    () => room && room.teams.A.players.length > 0 && room.teams.B.players.length > 0,
    [room],
  )

  if (!room) return null

  return (
    <ScreenShell
      title="Lobby"
      subtitle={`Match room · ${room.overs} overs, 6 balls per over`}
      actions={
        <Button size="sm" variant="ghost" onClick={() => navigate(SCREENS.landing)}>
          Leave
        </Button>
      }
    >
      <div className="space-y-4">
        <RoomCode code={room.code} />

        <div>
          <span className="mb-2 block text-xs font-black uppercase tracking-wide text-slate-400">
            Overs per side
          </span>
          <div className="grid grid-cols-5 gap-2.5">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setOvers(n)}
                className={`rounded-2xl py-2.5 text-base font-black transition active:scale-95 ${
                  overs === n
                    ? 'bg-emerald-500 text-emerald-950'
                    : 'bg-white/5 text-slate-300 ring-1 ring-white/10 hover:bg-white/10'
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <TeamPanel
          team={room.teams.A}
          myId={me.id}
          subtitle="Your team"
          onAdd={() => addTeammate('A')}
          onRemove={(id) => removePlayer('A', id)}
          onColor={(c) => setTeamColor('A', c)}
          colors={teamColorPresets}
        />

        <TeamPanel
          team={room.teams.B}
          myId={me.id}
          subtitle="Opponent"
          onAdd={() => addTeammate('B')}
          onRemove={(id) => removePlayer('B', id)}
          onColor={(c) => setTeamColor('B', c)}
          colors={teamColorPresets}
        />
      </div>

      <div className="mt-auto space-y-3 pt-6">
        <button
          type="button"
          onClick={() => setReady((r) => !r)}
          className={`w-full rounded-2xl py-3.5 text-base font-black transition active:scale-[0.98] ${
            ready
              ? 'bg-emerald-500 text-emerald-950 shadow-lg shadow-emerald-500/25'
              : 'bg-white/5 text-slate-200 ring-1 ring-white/15 hover:bg-white/10'
          }`}
        >
          {ready ? "✓ You're ready" : 'Tap when ready'}
        </button>

        <Button size="lg" full disabled={!ready || !canStart} onClick={startGame}>
          Start game
        </Button>
        <p className="text-center text-xs font-semibold text-slate-500">
          {!ready
            ? 'Mark yourself ready to begin.'
            : !canStart
              ? 'Both teams need at least one player.'
              : 'The coin toss decides who bats first.'}
        </p>
      </div>
    </ScreenShell>
  )
}
