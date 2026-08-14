const tones = {
  green: 'bg-emerald-500/15 text-emerald-300',
  amber: 'bg-amber-400/15 text-amber-300',
  sky: 'bg-sky-500/15 text-sky-300',
  rose: 'bg-rose-500/15 text-rose-300',
  slate: 'bg-white/10 text-slate-300',
}

export default function GameStatus({ items = [] }) {
  if (!items.length) return null
  return (
    <div className="flex flex-wrap items-center gap-2">
      {items.map((item, i) => (
        <span
          key={i}
          className={`rounded-full px-3 py-1 text-xs font-black uppercase tracking-wide ${
            tones[item.tone] || tones.slate
          }`}
        >
          {item.label}
        </span>
      ))}
    </div>
  )
}
