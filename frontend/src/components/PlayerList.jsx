export default function PlayerList({ players, myId, hostId }) {
  return (
    <ul className="flex flex-col gap-2">
      {players.map((player) => {
        const isMe = player.id === myId
        const isHost = player.id === hostId
        const ready = player.ready_status === 'READY'
        const connected = player.connection_status === 'CONNECTED'
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
                {isHost && (
                  <span className="rounded bg-amber-400/15 px-1.5 py-0.5 text-[10px] font-black uppercase tracking-wide text-amber-300">
                    Host
                  </span>
                )}
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${connected ? 'bg-emerald-400' : 'bg-rose-400'}`}
                />
                <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
                <span
                  className={`rounded px-1.5 py-0.5 text-[10px] font-black uppercase tracking-wide ${
                    ready
                      ? 'bg-emerald-500/15 text-emerald-300'
                      : 'bg-white/10 text-slate-400'
                  }`}
                >
                  {ready ? 'Ready' : 'Not ready'}
                </span>
              </div>
            </div>
          </li>
        )
      })}
    </ul>
  )
}
