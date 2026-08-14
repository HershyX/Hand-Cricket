import { useCopy } from '../hooks/useCopy'

export default function RoomCode({ code, label = 'Room code' }) {
  const [copied, copy] = useCopy()

  return (
    <div className="rounded-2xl bg-white/5 p-4 ring-1 ring-white/10">
      <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-400">{label}</p>
      <div className="mt-2 flex items-center gap-3">
        <p className="font-mono text-3xl font-black tracking-[0.25em] text-slate-50">{code}</p>
        <button
          type="button"
          onClick={() => copy(code)}
          className="rounded-xl bg-emerald-500/15 px-3 py-1.5 text-sm font-bold text-emerald-300 transition hover:bg-emerald-500/25 active:scale-95"
          aria-label="Copy room code"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
    </div>
  )
}
