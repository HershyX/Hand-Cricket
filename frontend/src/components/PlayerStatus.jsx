export default function PlayerStatus({ label, player, teamName, accent = 'emerald', isMe = false, right }) {
  const accents = {
    emerald: 'from-emerald-400/20 text-emerald-300',
    sky: 'from-sky-400/20 text-sky-300',
    rose: 'from-rose-400/20 text-rose-300',
  }

  if (!player) return null

  return (
    <div className="flex items-center gap-3 rounded-2xl bg-gradient-to-r from-white/5 to-transparent p-3 ring-1 ring-white/10">
      <div
        className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-br text-base font-black ${
          accents[accent]
        } ring-1 ring-white/15`}
      >
        {player.name.slice(0, 1)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
            {label}
          </span>
        </div>
        <p className="truncate text-base font-black text-slate-50">
          {player.name}
          {isMe && <span className="ml-1.5 text-xs font-bold text-emerald-300">(you)</span>}
        </p>
        {teamName && <p className="text-xs font-semibold text-slate-400">{teamName}</p>}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  )
}
