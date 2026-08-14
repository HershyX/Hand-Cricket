const REASON_LABEL = {
  TARGET_REACHED: 'won by reaching the target',
  ALL_OUT: 'won by all out',
}

export default function ResultCard({ winnerTeamName, iWon, reason }) {
  return (
    <div className="animate-bounce-in rounded-3xl bg-gradient-to-br from-emerald-500/20 via-white/5 to-transparent p-8 text-center ring-1 ring-white/15">
      <p className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
        {iWon ? 'Victory' : 'Defeat'}
      </p>
      <h2 className="mt-3 text-4xl font-black tracking-tight text-slate-50">
        {winnerTeamName || 'Draw'}
      </h2>
      <p className="mt-2 text-lg font-bold text-slate-300">
        {REASON_LABEL[reason] ?? 'wins the match'}
      </p>
    </div>
  )
}
