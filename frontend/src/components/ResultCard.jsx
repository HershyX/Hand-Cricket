export default function ResultCard({ winner, result, me }) {
  if (!result) return null

  const winnerTeam = result.winnerTeamId ? winner : null
  const iWon = result.winnerTeamId === me.teamId

  return (
    <div className="animate-bounce-in rounded-3xl bg-gradient-to-br from-emerald-500/20 via-white/5 to-transparent p-8 text-center ring-1 ring-white/15">
      <p className="text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
        {iWon ? 'Victory' : 'Defeat'}
      </p>
      <h2 className="mt-3 text-4xl font-black tracking-tight text-slate-50">
        {winnerTeam ? winnerTeam.name : 'Draw'}
      </h2>
      <p className="mt-2 text-lg font-bold text-slate-300">wins the match</p>

      <div className="mx-auto mt-5 w-fit rounded-2xl bg-white/5 px-5 py-3 ring-1 ring-white/10">
        <p className="text-sm font-black text-slate-100">
          {result.byWickets != null
            ? `Won by ${result.byWickets} wicket${result.byWickets === 1 ? '' : 's'}`
            : result.byRuns != null
              ? `Won by ${result.byRuns} run${result.byRuns === 1 ? '' : 's'}`
              : 'Match tied'}
        </p>
      </div>
    </div>
  )
}
