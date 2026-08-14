export default function BowlerSelector({ bowler, team, onSwitch, disabled, disabledReason }) {
  if (!bowler || !team) return null
  const canSwitch = team.players.length > 1

  return (
    <div className="flex items-center gap-3 rounded-2xl bg-white/5 p-3 ring-1 ring-white/10">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sky-500/15 text-sm font-black text-sky-300 ring-1 ring-white/15">
        {bowler.name.slice(0, 1)}
      </div>
      <div className="min-w-0 flex-1">
        <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
          Bowler
        </span>
        <p className="truncate text-sm font-black text-slate-50">{bowler.name}</p>
      </div>
      <button
        type="button"
        onClick={onSwitch}
        disabled={disabled || !canSwitch}
        title={disabledReason || (canSwitch ? 'Switch bowler' : 'Need more players to switch')}
        className="rounded-xl bg-sky-500/15 px-3 py-2 text-xs font-black uppercase tracking-wide text-sky-300 transition hover:bg-sky-500/25 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Switch bowler
      </button>
    </div>
  )
}
