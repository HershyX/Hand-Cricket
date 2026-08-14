export default function TossAnimation({ outcome, call }) {
  const spinning = !outcome
  const win = outcome && call === outcome

  return (
    <div className="flex flex-col items-center">
      <div
        className={`flex h-32 w-32 items-center justify-center rounded-full text-4xl font-black shadow-xl ${
          spinning
            ? 'animate-toss-ball bg-gradient-to-br from-emerald-400 to-sky-500 text-white'
            : outcome === 'heads'
              ? 'animate-pop bg-amber-300 text-amber-950'
              : 'animate-pop bg-slate-200 text-slate-900'
        } ring-4 ring-white/20`}
        style={{ borderRadius: '50%' }}
      >
        {spinning ? '?' : outcome === 'heads' ? 'H' : 'T'}
      </div>

      {outcome && (
        <div className="mt-6 animate-rise text-center">
          <p className="text-2xl font-black tracking-tight text-slate-50">
            It&apos;s <span className="uppercase text-amber-300">{outcome}</span>!
          </p>
          <p className="mt-2 text-base font-bold text-slate-300">
            {win ? 'You win the toss!' : 'Opponent wins the toss.'}
          </p>
        </div>
      )}
    </div>
  )
}
