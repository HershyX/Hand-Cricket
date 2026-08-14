import PlayerList from './PlayerList'

export default function TeamPanel({ team, teamKey, myTeamKey, myId, hostId, onJoinTeam, onLeaveTeam }) {
  const isMeHere = myTeamKey === teamKey
  const full = team.player_count >= team.capacity

  return (
    <div className="rounded-2xl bg-white/5 p-4 ring-1 ring-white/10">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-black text-slate-50">{team.name}</h3>
          <p className="text-xs text-slate-400">
            {team.player_count}/{team.capacity} players
          </p>
        </div>
        {!isMeHere && (
          <button
            type="button"
            onClick={() => onJoinTeam(teamKey)}
            disabled={full}
            className="rounded-xl bg-emerald-500/15 px-3 py-2 text-xs font-black uppercase tracking-wide text-emerald-300 transition hover:bg-emerald-500/25 active:scale-95 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {full ? 'Full' : 'Join team'}
          </button>
        )}
        {isMeHere && (
          <button
            type="button"
            onClick={onLeaveTeam}
            className="rounded-xl bg-white/10 px-3 py-2 text-xs font-black uppercase tracking-wide text-slate-300 transition hover:bg-rose-500/20 hover:text-rose-300 active:scale-95"
          >
            Leave team
          </button>
        )}
      </div>

      <PlayerList players={team.players} myId={myId} hostId={hostId} />

      {!team.players.length && (
        <p className="mt-2 text-center text-xs font-semibold text-slate-500">No players yet</p>
      )}
    </div>
  )
}
