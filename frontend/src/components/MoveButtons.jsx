export default function MoveButtons({ onMove, disabled, busy, hint }) {
  const values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  const defaultHint = busy
    ? 'Ball in progress…'
    : 'Pick a number — same number means OUT!'

  return (
    <div>
      <div className="grid grid-cols-5 gap-2.5 sm:grid-cols-6">
        {values.map((value) => (
          <button
            key={value}
            type="button"
            disabled={disabled}
            onClick={() => onMove(value)}
            className={
              'rounded-2xl bg-white/5 py-4 text-2xl font-black text-slate-100 ring-1 ring-white/10 ' +
              'transition hover:bg-emerald-500 hover:text-emerald-950 hover:ring-emerald-400 ' +
              'hover:shadow-lg hover:shadow-emerald-500/25 active:scale-90 disabled:cursor-not-allowed disabled:opacity-40 ' +
              (value === 6
                ? 'bg-amber-500/15 text-amber-300 ring-amber-400/30 hover:bg-amber-400 hover:text-amber-950'
                : '')
            }
          >
            {value}
          </button>
        ))}
      </div>
      <p className="mt-3 text-center text-xs font-semibold text-slate-500">
        {hint || defaultHint}
      </p>
    </div>
  )
}
