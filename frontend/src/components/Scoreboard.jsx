export default function Scoreboard({ game, room }) {
  const totalBalls = room ? room.overs * room.ballsPerOver : 0
  const ballNo = Math.min(game.ballIndex, totalBalls)
  const over = Math.floor(ballNo / room.ballsPerOver) + 1
  const ballInOver = (ballNo % room.ballsPerOver) + 1
  const ballsLeft = totalBalls - ballNo
  const chasing = game.target != null
  const runsNeeded = chasing ? game.target - game.score : 0

  return (
    <div className="rounded-2xl bg-gradient-to-br from-emerald-500/15 via-white/5 to-transparent p-4 ring-1 ring-white/10">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-emerald-500/20 px-2.5 py-1 text-[11px] font-black uppercase tracking-wide text-emerald-300">
            {game.innings === 1 ? 'Innings 1' : 'Innings 2'}
          </span>
          {chasing && (
            <span className="rounded-full bg-amber-400/15 px-2.5 py-1 text-[11px] font-black uppercase tracking-wide text-amber-300">
              Chase
            </span>
          )}
        </div>
        <p className="text-xs font-bold text-slate-400">
          {game.battingTeamId ? room.teams[game.battingTeamId].name : ''} batting
        </p>
      </div>

      <div className="mt-3 flex items-end justify-between gap-4">
        <div>
          <p className="font-mono text-5xl font-black tracking-tight text-slate-50">
            {game.score}
            <span className="text-2xl text-slate-400">/{game.wickets}</span>
          </p>
          <p className="mt-1 text-xs font-bold uppercase tracking-wide text-slate-400">
            Overs {over}.{ballInOver}
          </p>
        </div>

        <div className="text-right">
          {chasing ? (
            <>
              <p className="text-sm font-bold text-slate-300">
                Target <span className="font-mono text-lg font-black text-amber-300">{game.target}</span>
              </p>
              <p className="mt-0.5 text-xs font-bold text-slate-400">
                {runsNeeded} run{runsNeeded === 1 ? '' : 's'} needed
              </p>
              <p className="text-xs font-bold text-slate-500">
                {ballsLeft} ball{ballsLeft === 1 ? '' : 's'} left
              </p>
            </>
          ) : (
            <>
              <p className="text-sm font-bold text-slate-300">
                Overs <span className="font-mono text-lg font-black text-emerald-300">{room.overs}</span>
              </p>
              <p className="mt-0.5 text-xs font-bold text-slate-400">per side</p>
              <p className="text-xs font-bold text-slate-500">
                {room.ballsPerOver} balls / over
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
