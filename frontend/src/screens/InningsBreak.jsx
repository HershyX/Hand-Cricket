import Button from '../components/Button'
import GameStatus from '../components/GameStatus'
import ScreenShell from '../components/ScreenShell'
import { useGame } from '../state/GameContext'
import { teamLabel } from '../lib/gameView'

export default function InningsBreak() {
  const { game, isHost, beginSecondInnings, leaveRoom } = useGame()

  if (!game) return null

  const completed = game.current_innings
  const score = completed?.score ?? 0
  const wickets = completed?.wickets ?? 0
  const target = game.target_score ?? 0
  const battedTeam = teamLabel(game.batting_team_id)
  const toBatTeam = teamLabel(game.bowling_team_id)

  return (
    <ScreenShell
      title="Innings break"
      subtitle={`${battedTeam} have finished batting.`}
      actions={
        <Button size="sm" variant="ghost" onClick={leaveRoom}>
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
            {score}
            <span className="text-2xl text-slate-400">/{wickets}</span>
          </p>
          <p className="mt-2 text-sm font-bold text-slate-300">{battedTeam}</p>
        </div>

        <div className="animate-rise rounded-2xl bg-amber-400/10 p-5 text-center ring-1 ring-amber-400/25 [animation-delay:0.15s]">
          <p className="text-[11px] font-black uppercase tracking-[0.3em] text-amber-300">
            Target for {toBatTeam}
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
              { label: '1st innings complete', tone: 'slate' },
              { label: `${toBatTeam} to bat`, tone: 'amber' },
            ]}
          />
          {isHost ? (
            <Button size="lg" full variant="primary" onClick={beginSecondInnings}>
              Start 2nd innings
            </Button>
          ) : (
            <Button size="lg" full variant="secondary" disabled>
              Waiting for host to start…
            </Button>
          )}
        </div>
      </div>
    </ScreenShell>
  )
}
