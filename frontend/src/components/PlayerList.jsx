export default function PlayerList({ players, captainId, myId, onRemove }) {
  return (
    <ul className="flex flex-col gap-2">
      {players.map((player) => {
        const isCaptain = player.id === captainId
        const isMe = player.id === myId
        return (
          <li
            key={player.id}
            className="flex items-center gap-3 rounded-xl bg-white/5 px-3 py-2.5 ring-1 ring-white/10"
          >
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-black ${
                isMe ? 'bg-emerald-400 text-emerald-950' : 'bg-white/10 text-slate-200'
              }`}
            >
              {player.name.slice(0, 1)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-bold text-slate-100">
                {player.name}
                {isMe && <span className="ml-1.5 text-xs font-black text-emerald-300">(you)</span>}
              </p>
              <div className="flex items-center gap-1.5">
                {isCaptain && (
                  <span className="rounded bg-amber-400/15 px-1.5 py-0.5 text-[10px] font-black uppercase tracking-wide text-amber-300">
                    Captain
                  </span>
                )}
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
                  Ready
                </span>
              </div>
            </div>
            {onRemove && !isCaptain && (
              <button
                type="button"
                onClick={() => onRemove(player.id)}
                className="rounded-lg bg-white/5 px-2 py-1 text-xs font-bold text-slate-400 transition hover:bg-rose-500/20 hover:text-rose-300 active:scale-95"
              >
                Remove
              </button>
            )}
          </li>
        )
      })}
    </ul>
  )
}
