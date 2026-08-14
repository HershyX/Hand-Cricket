import { runsNeeded, teamLabel } from '../lib/gameView'

export default function Scoreboard({ game }) {
  const innings = game?.current_innings ?? null
  const score = innings?.score ?? 0
  const wickets = innings?.wickets ?? 0
  const balls = innings?.ball_count ?? 0
  const target = game?.target_score ?? null
  const chasing = target != null
  const runsNeededCount = runsNeeded(game)

  return (
    <div className="rounded-2xl bg-gradient-to-br from-emerald-500/15 via-white/5 to-transparent p-4 ring-1 ring-white/10">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-emerald-500/20 px-2.5 py-1 text-[11px] font-black uppercase tracking-wide text-emerald-300">
            Innings {game?.innings_number ?? '-'}
          </span>
          {chasing && (
            <span className="rounded-full bg-amber-400/15 px-2.5 py-1 text-[11px] font-black uppercase tracking-wide text-amber-300">
              Chase
            </span>
          )}
        </div>
        <p className="text-xs font-bold text-slate-400">
          {game?.batting_team_id ? teamLabel(game.batting_team_id) : ''} batting
        </p>
      </div>

      <div className="mt-3 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-5xl font-black tracking-tight text-slate-50">
            {score}
            <span className="text-2xl text-slate-400">/{wickets}</span>
          </p>
          <p className="mt-1 text-xs font-bold uppercase tracking-wide text-slate-400">
            Ball {balls} · Turn {game?.turn_number ?? 0}
          </p>
        </div>

        <div className="text-right">
          {chasing ? (
            <>
              <p className="text-sm font-bold text-slate-300">
                Target <span className="font-mono text-lg font-black text-amber-300">{target}</span>
              </p>
              <p className="mt-0.5 text-xs font-bold text-slate-400">
                {runsNeededCount} run{runsNeededCount === 1 ? '' : 's'} needed
              </p>
              <p className="text-xs font-bold text-slate-500">
                Innings 2
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-bold text-slate-300">
                Batting <span className="font-mono text-lg font-black text-emerald-300">first</span>
              </p>
              <p className="mt-0.5 text-xs font-bold text-slate-400">
                No over limit
              </p>
              <p className="text-xs font-bold text-slate-500">
                Play until all out
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
