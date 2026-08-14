import { useMemo } from 'react'
import BowlerSelector from '../components/BowlerSelector'
import GameStatus from '../components/GameStatus'
import MoveButtons from '../components/MoveButtons'
import MoveReveal from '../components/MoveReveal'
import PlayerStatus from '../components/PlayerStatus'
import Scoreboard from '../components/Scoreboard'
import { useGame } from '../state/GameContext'

export default function Gameplay() {
  const {
    room,
    game,
    me,
    submitMove,
    switchBowler,
    getActingRole,
    getCurrentBatter,
    getCurrentBowler,
  } = useGame()

  const batter = getCurrentBatter()
  const bowler = getCurrentBowler()
  const role = getActingRole()
  const battingTeam = game ? room.teams[game.battingTeamId] : null
  const bowlingTeam = game ? room.teams[game.bowlingTeamId] : null

  const canSubmit = useMemo(() => game?.phase === 'pick' && !game.ballInProgress, [game])
  const canSwitch = useMemo(
    () => game?.phase === 'pick' && !game.ballInProgress && bowlingTeam?.players.length > 1,
    [game, bowlingTeam],
  )

  if (!game || !room) return null

  const hint =
    role === 'batter'
      ? 'Pick your move — match the bowler and you\'re OUT!'
      : 'Pick your move — match the batter to bowl them OUT!'

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-5 pb-8 pt-6 sm:max-w-lg">
      <Scoreboard game={game} room={room} />

      <div className="mt-4">
        <GameStatus
          items={[
            { label: `${battingTeam.name} batting`, tone: 'green' },
            { label: `${bowlingTeam.name} bowling`, tone: 'sky' },
            { label: me.teamId === game.battingTeamId ? 'Your turn to pick' : 'Opponent batting', tone: 'amber' },
          ]}
        />
      </div>

      <div className="mt-4 space-y-3">
        <PlayerStatus
          label="Batter"
          player={batter}
          teamName={battingTeam.name}
          accent="emerald"
          right={
            game.lastTag ? (
              <span
                className={`animate-score-pop rounded-xl px-3 py-1.5 text-sm font-black ${
                  game.lastTag === 'WICKET!' ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/15 text-emerald-300'
                }`}
              >
                {game.lastTag}
              </span>
            ) : null
          }
        />
        <PlayerStatus label="Bowler" player={bowler} teamName={bowlingTeam.name} accent="sky" />
      </div>

      <div className="mt-3">
        <BowlerSelector
          bowler={bowler}
          team={bowlingTeam}
          onSwitch={switchBowler}
          disabled={!canSwitch}
          disabledReason={canSubmit ? undefined : 'Bowler can only change between balls'}
        />
      </div>

      <div className="mt-auto pt-8">
        <MoveButtons onMove={submitMove} disabled={!canSubmit} busy={!canSubmit} hint={hint} />
      </div>

      <MoveReveal
        phase={game.phase}
        batterMove={game.batterMove}
        bowlerMove={game.bowlerMove}
        result={game.result}
      />
    </div>
  )
}
