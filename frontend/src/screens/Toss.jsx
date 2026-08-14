import { useEffect, useRef } from 'react'
import Button from '../components/Button'
import ScreenShell from '../components/ScreenShell'
import TossAnimation from '../components/TossAnimation'
import { useGame, SCREENS } from '../state/GameContext'

export default function Toss() {
  const { room, toss, chooseTossCall, flipCoin, makeDecision, navigate } = useGame()
  const botDecidedRef = useRef(false)

  useEffect(() => {
    if (toss.winnerId === 'opp' && !botDecidedRef.current) {
      botDecidedRef.current = true
      const t = window.setTimeout(() => {
        makeDecision(Math.random() < 0.5 ? 'bat' : 'bowl')
      }, 1600)
      return () => window.clearTimeout(t)
    }
    if (toss.winnerId !== 'opp') botDecidedRef.current = false
    return undefined
  }, [toss.winnerId, makeDecision])

  const oppCaptain = room?.teams.B.players.find((p) => p.id === 'opp-captain')

  return (
    <ScreenShell
      title="Coin toss"
      subtitle="Whoever wins decides who bats first."
      actions={
        <Button size="sm" variant="ghost" onClick={() => navigate(SCREENS.lobby)}>
          Back
        </Button>
      }
    >
      <div className="flex flex-1 flex-col items-center justify-center gap-8">
        <TossAnimation outcome={toss.outcome} call={toss.call} />

        {!toss.call && (
          <div className="w-full">
            <p className="mb-3 text-center text-sm font-bold text-slate-300">
              {oppCaptain ? `${oppCaptain.name} flips the coin.` : 'Call the coin:'}
            </p>
            <div className="grid grid-cols-2 gap-3">
              <Button
                size="lg"
                variant="secondary"
                onClick={() => chooseTossCall('heads')}
                disabled={!!toss.outcome}
              >
                Heads
              </Button>
              <Button
                size="lg"
                variant="secondary"
                onClick={() => chooseTossCall('tails')}
                disabled={!!toss.outcome}
              >
                Tails
              </Button>
            </div>
          </div>
        )}

        {toss.call && !toss.outcome && (
          <Button size="lg" full variant="primary" onClick={flipCoin}>
            Flip the coin
          </Button>
        )}

        {toss.outcome && toss.winnerId === 'me' && (
          <Button
            size="lg"
            full
            variant="primary"
            onClick={() => navigate(SCREENS.tossDecision)}
          >
            Choose bat or bowl →
          </Button>
        )}

        {toss.outcome && toss.winnerId === 'opp' && (
          <p className="animate-rise text-center text-sm font-bold text-slate-400">
            {oppCaptain?.name} is deciding…
          </p>
        )}
      </div>
    </ScreenShell>
  )
}
