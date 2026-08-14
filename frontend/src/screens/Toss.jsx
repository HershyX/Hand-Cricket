import Button from '../components/Button'
import CricketBall from '../components/CricketBall'
import ScreenShell from '../components/ScreenShell'
import { useGame, SCREENS } from '../state/GameContext'
import { teamLabel } from '../lib/gameView'

export default function Toss() {
  const { tossWinnerId, me, navigate } = useGame()
  const iWon = me && tossWinnerId === me.team_id

  return (
    <ScreenShell
      title="Toss"
      subtitle="The server decides who bats first."
      actions={
        <Button size="sm" variant="ghost" onClick={() => navigate(SCREENS.lobby)}>
          Back
        </Button>
      }
    >
      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        <CricketBall size={84} className="animate-toss-ball drop-shadow-[0_0_25px_rgba(220,38,38,0.35)]" />

        <div className="animate-rise text-center">
          <p className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
            Toss result
          </p>
          <h2 className="mt-3 text-4xl font-black tracking-tight text-slate-50">
            {tossWinnerId ? teamLabel(tossWinnerId) : '…'}
          </h2>
          <p className="mt-2 text-base font-bold text-slate-300">
            {iWon ? 'You won the toss!' : 'won the toss.'}
          </p>
        </div>

        {iWon && (
          <Button size="lg" full variant="primary" onClick={() => navigate(SCREENS.tossDecision)}>
            Choose bat or bowl →
          </Button>
        )}

        {!iWon && tossWinnerId && (
          <p className="animate-rise text-center text-sm font-bold text-slate-400">
            Waiting for {teamLabel(tossWinnerId)} to decide…
          </p>
        )}
      </div>
    </ScreenShell>
  )
}
