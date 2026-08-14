import Button from '../components/Button'
import GameStatus from '../components/GameStatus'
import ResultCard from '../components/ResultCard'
import ScreenShell from '../components/ScreenShell'
import { useGame } from '../state/GameContext'

export default function Result() {
  const { game, room, me, backToLobby, navigate } = useGame()

  if (!game || !room) return null

  const winnerTeam = game.winnerTeamId ? room.teams[game.winnerTeamId] : null
  const battingTeam = room.teams[game.battingTeamId]
  const bowlingTeam = room.teams[game.bowlingTeamId]

  return (
    <ScreenShell>
      <div className="flex flex-1 flex-col justify-center gap-6">
        <ResultCard winner={winnerTeam} result={game} me={me} />

        <div className="animate-rise space-y-2 [animation-delay:0.2s]">
          <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3 ring-1 ring-white/10">
            <span className="text-sm font-bold text-slate-400">{battingTeam.name}</span>
            <span className="font-mono text-lg font-black text-slate-100">{game.score}/{game.wickets}</span>
          </div>
          <div className="flex items-center justify-between rounded-2xl bg-white/5 px-4 py-3 ring-1 ring-white/10">
            <span className="text-sm font-bold text-slate-400">{bowlingTeam.name}</span>
            <span className="font-mono text-lg font-black text-slate-100">
              {game.firstInningsScore}/{game.firstInningsWickets}
            </span>
          </div>
        </div>

        <div className="animate-rise space-y-3 pt-2 [animation-delay:0.35s]">
          <GameStatus
            items={[
              { label: 'Match complete', tone: 'slate' },
              { label: `Target ${game.target}`, tone: 'amber' },
            ]}
          />
          <Button size="lg" full variant="primary" onClick={backToLobby}>
            Play again
          </Button>
          <Button size="lg" full variant="ghost" onClick={() => navigate('landing')}>
            Back to home
          </Button>
        </div>
      </div>
    </ScreenShell>
  )
}
