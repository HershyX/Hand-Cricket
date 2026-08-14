import ScreenShell from '../components/ScreenShell'
import { useGame } from '../state/GameContext'
import { teamLabel } from '../lib/gameView'

function BatIcon({ className = '' }) {
  return (
    <svg width="72" height="72" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden="true">
      <rect x="8" y="10" width="10" height="30" rx="5" fill="#fbbf24" />
      <rect x="14" y="6" width="12" height="24" rx="6" fill="#f59e0b" />
      <rect x="22" y="4" width="34" height="9" rx="4.5" fill="#d97706" />
      <rect x="22" y="13" width="34" height="9" rx="4.5" fill="#b45309" opacity="0.8" />
      <path d="M6 46l52-8" stroke="#e2e8f0" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

function BallIcon({ className = '' }) {
  return (
    <svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden="true">
      <circle cx="32" cy="32" r="28" fill="#38bdf8" />
      <path d="M32 4a28 28 0 010 56" stroke="#0c4a6e" strokeWidth="2.5" fill="none" />
      <path d="M4 32h56" stroke="#0c4a6e" strokeWidth="2.5" />
      <path d="M14 14l36 36M50 14L14 50" stroke="#0c4a6e" strokeWidth="2.5" />
      <circle cx="22" cy="22" r="4" fill="#e0f2fe" opacity="0.6" />
    </svg>
  )
}

export default function TossDecision() {
  const { tossWinnerId, me, tossDecision } = useGame()
  const iWon = me && tossWinnerId === me.team_id

  if (!iWon) {
    return (
      <ScreenShell title="Your call" subtitle="Waiting for the toss winner…">
        <div className="flex flex-1 items-center justify-center">
          <p className="animate-rise text-center text-sm font-bold text-slate-400">
            Waiting for {tossWinnerId ? teamLabel(tossWinnerId) : 'the other team'} to choose bat or bowl.
          </p>
        </div>
      </ScreenShell>
    )
  }

  return (
    <ScreenShell
      title="Your call"
      subtitle="You won the toss — bat or bowl first?"
    >
      <div className="grid flex-1 grid-rows-2 gap-4">
        <button
          type="button"
          onClick={() => tossDecision('BATTING')}
          className="group flex flex-col items-center justify-center rounded-3xl bg-gradient-to-br from-emerald-500/20 to-transparent ring-1 ring-white/15 transition hover:ring-emerald-400/50 active:scale-[0.98]"
        >
          <BatIcon className="transition-transform group-hover:scale-110" />
          <span className="mt-3 text-2xl font-black tracking-tight text-slate-50">BAT</span>
          <span className="mt-1 text-sm font-bold text-slate-400">Chase a target first</span>
        </button>

        <button
          type="button"
          onClick={() => tossDecision('BOWLING')}
          className="group flex flex-col items-center justify-center rounded-3xl bg-gradient-to-br from-sky-500/20 to-transparent ring-1 ring-white/15 transition hover:ring-sky-400/50 active:scale-[0.98]"
        >
          <BallIcon className="transition-transform group-hover:scale-110" />
          <span className="mt-3 text-2xl font-black tracking-tight text-slate-50">BOWL</span>
          <span className="mt-1 text-sm font-bold text-slate-400">Set a target first</span>
        </button>
      </div>
    </ScreenShell>
  )
}
