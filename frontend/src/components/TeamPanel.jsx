import PlayerList from './PlayerList'

export default function TeamPanel({
  team,
  myId,
  onAdd,
  onRemove,
  onColor,
  colors,
  subtitle,
}) {
  return (
    <div className="rounded-2xl bg-white/5 p-4 ring-1 ring-white/10">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-black text-slate-50">{team.name}</h3>
          {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
        </div>
        <div className="flex items-center gap-1.5">
          {colors.map((c) => (
            <button
              key={c.name}
              type="button"
              onClick={() => onColor(c)}
              className="h-6 w-6 rounded-full ring-2 ring-white/10 transition hover:scale-110 active:scale-95"
              style={{ backgroundColor: c.fg }}
              aria-label={`Set ${team.name} color to ${c.name}`}
            />
          ))}
        </div>
      </div>

      <PlayerList players={team.players} captainId={team.captainId} myId={myId} onRemove={onRemove} />

      {onAdd && (
        <button
          type="button"
          onClick={onAdd}
          className="mt-3 w-full rounded-xl border-2 border-dashed border-white/15 py-2.5 text-sm font-bold text-slate-300 transition hover:border-emerald-400/50 hover:text-emerald-300 active:scale-[0.98]"
        >
          + Add teammate
        </button>
      )}
    </div>
  )
}
