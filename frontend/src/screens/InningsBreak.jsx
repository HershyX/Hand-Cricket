import Button from '../components/Button'
import GameStatus from '../components/GameStatus'
import ScreenShell from '../components/ScreenShell'
import { useGame } from '../state/GameContext'

export default function InningsBreak() {
  const { game, room, continueToSecondInnings, backToLobby } = useGame()

  if (!game || !room) return null

  const target = game.score + 1
  const battingTeam = room.teams[game.battingTeamId]
  const bowlingTeam = room.teams[game.bowlingTeamId]

  return (
    <ScreenShell
      title="Innings break"
      subtitle={`${battingTeam.name} have finished batting.`}
      actions={
        <Button size="sm" variant="ghost" onClick={backToLobby}>
          Leave
        </Button>
      }
    >
      <div className="flex flex-1 flex-col justify-center gap-6">
        <div className="animate-pop rounded-3xl bg-gradient-to-br from-emerald-500/15 to-transparent p-8 text-center ring-1 ring-white/15">
          <p className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
            End of innings
          </p>
          <p className="mt-3 font-mono text-6xl font-black tracking-tight text-slate-50">
            {game.score}
            <span className="text-2xl text-slate-400">/{game.wickets}</span>
          </p>
          <p className="mt-2 text-sm font-bold text-slate-300">{battingTeam.name}</p>
        </div>

        <div className="animate-rise rounded-2xl bg-amber-400/10 p-5 text-center ring-1 ring-amber-400/25 [animation-delay:0.15s]">
          <p className="text-[11px] font-black uppercase tracking-[0.3em] text-amber-300">
            Target for {bowlingTeam.name}
          </p>
          <p className="mt-1 font-mono text-4xl font-black tracking-tight text-amber-200">
            {target}
          </p>
          <p className="mt-1 text-xs font-bold text-amber-300/80">
            Run{target === 1 ? '' : 's'} to win
          </p>
        </div>

        <div className="animate-rise space-y-3 pt-2 [animation-delay:0.3s]">
          <GameStatus
            items={[
              { label: `1st innings complete`, tone: 'slate' },
              { label: `${bowlingTeam.name} to bat`, tone: 'amber' },
            ]}
          />
          <Button size="lg" full variant="primary" onClick={continueToSecondInnings}>
            Start 2nd innings
          </Button>
        </div>
      </div>
    </ScreenShell>
  )
}
