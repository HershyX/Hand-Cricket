export default function MoveReveal({ phase, batterMove, bowlerMove, result }) {
  if (phase !== 'reveal' && phase !== 'settle') return null

  const isOut = phase === 'settle' && result?.type === 'out'
  const runs = phase === 'settle' && result?.type === 'runs' ? result.runs : null

  return (
    <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-6 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-3xl bg-slate-900 p-8 text-center ring-1 ring-white/15 shadow-2xl">
        {phase === 'reveal' ? (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="animate-pop rounded-2xl bg-emerald-500/15 p-5 ring-1 ring-emerald-400/30">
                <p className="text-[11px] font-black uppercase tracking-[0.25em] text-emerald-300">
                  Batter
                </p>
                <p className="mt-1 font-mono text-5xl font-black text-emerald-300">{batterMove}</p>
              </div>
              <div className="animate-pop rounded-2xl bg-sky-500/15 p-5 ring-1 ring-sky-400/30 [animation-delay:0.3s]">
                <p className="text-[11px] font-black uppercase tracking-[0.25em] text-sky-300">
                  Bowler
                </p>
                <p className="mt-1 font-mono text-5xl font-black text-sky-300">{bowlerMove}</p>
              </div>
            </div>
            <p className="mt-6 animate-rise text-sm font-bold uppercase tracking-[0.2em] text-slate-400 [animation-delay:0.55s]">
              Resolving…
            </p>
          </>
        ) : isOut ? (
          <div className="animate-bounce-in">
            <p className="text-6xl font-black tracking-tight text-rose-400">OUT!</p>
            <p className="mt-3 text-sm font-bold uppercase tracking-[0.2em] text-slate-400">
              Same number — batter is gone
            </p>
          </div>
        ) : (
          <div className="animate-bounce-in">
            <p className="text-[11px] font-black uppercase tracking-[0.25em] text-emerald-300">
              Result
            </p>
            <p className="mt-1 font-mono text-6xl font-black tracking-tight text-slate-50">
              {runs} {runs === 1 ? 'RUN' : 'RUNS'}
            </p>
            {runs === 6 && (
              <p className="mt-3 text-xl font-black text-amber-300">SIX!</p>
            )}
            {runs === 4 && <p className="mt-3 text-xl font-black text-amber-300">FOUR!</p>}
          </div>
        )}
      </div>
    </div>
  )
}
