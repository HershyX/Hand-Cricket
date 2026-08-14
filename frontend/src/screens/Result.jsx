import Button from '../components/Button'
import GameStatus from '../components/GameStatus'
import ResultCard from '../components/ResultCard'
import ScreenShell from '../components/ScreenShell'
import { useGame } from '../state/GameContext'
import { teamLabel } from '../lib/gameView'

export default function Result() {
  const { game, me, isHost, resetLobby, backToHome } = useGame()

  if (!game) return null

  const winnerTeamId = game.winner_team_id
  const reason = game.game_over_reason
  const iWon = me?.team_id != null && winnerTeamId === me.team_id
  const teamAScore = game.teams?.['team-1']?.score ?? 0
  const teamBScore = game.teams?.['team-2']?.score ?? 0

  return (
    <ScreenShell>
      <div className="flex flex-1 flex-col justify-center gap-6">
        <ResultCard
          winnerTeamName={winnerTeamId ? teamLabel(winnerTeamId) : null}
          iWon={iWon}
          reason={reason}
        />

        <div className="animate-rise space-y-2 [animation-delay:0.2s]">
          <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3 ring-1 ring-white/10">
            <span className="text-sm font-bold text-slate-400">Team A</span>
            <span className="font-mono text-lg font-black text-slate-100">{teamAScore}</span>
          </div>
          <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3 ring-1 ring-white/10">
            <span className="text-sm font-bold text-slate-400">Team B</span>
            <span className="font-mono text-lg font-black text-slate-100">{teamBScore}</span>
          </div>
        </div>

        <div className="animate-rise space-y-3 pt-2 [animation-delay:0.35s]">
          <GameStatus
            items={[
              { label: 'Match complete', tone: 'slate' },
              { label: `Target ${game.target_score ?? '-'}`, tone: 'amber' },
            ]}
          />
          {isHost ? (
            <Button size="lg" full variant="primary" onClick={resetLobby}>
              Play again
            </Button>
          ) : (
            <Button size="lg" full variant="secondary" disabled>
              Waiting for host to restart…
            </Button>
          )}
          <Button size="lg" full variant="ghost" onClick={backToHome}>
            Back to home
          </Button>
        </div>
      </div>
    </ScreenShell>
  )
}
