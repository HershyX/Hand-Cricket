import BowlerSelector from '../components/BowlerSelector'
import GameStatus from '../components/GameStatus'
import MoveButtons from '../components/MoveButtons'
import MoveReveal from '../components/MoveReveal'
import PlayerStatus from '../components/PlayerStatus'
import Scoreboard from '../components/Scoreboard'
import { useGame } from '../state/GameContext'
import {
  canSubmitMove,
  canSwitchBowler,
  iHaveSubmitted,
  myRole,
  opponentSubmitted,
  outcomeLabel,
  playerById,
  teamLabel,
} from '../lib/gameView'

export default function Gameplay() {
  const { game, room, me, ball, submitMove, switchBowler, connection } = useGame()

  const role = myRole(game, me)
  const batter = playerById(game, room, game?.current_batter_id)
  const bowler = playerById(game, room, game?.current_bowler_id)
  const canSubmit = canSubmitMove(game, me)
  const submitted = iHaveSubmitted(game, role)
  const oppPlayed = opponentSubmitted(game, role)
  const canSwitch = canSwitchBowler(game, me)
  const lastLabel = outcomeLabel(game?.last_ball)

  if (!game || !room || !me) return null

  const hint =
    role === 'batter'
      ? 'Pick your move — match the bowler and you\'re OUT!'
      : role === 'bowler'
        ? 'Pick your move — match the batter to bowl them OUT!'
        : 'Waiting for the game to continue…'

  const status =
    connection !== 'connected'
      ? 'Reconnecting…'
      : submitted
        ? oppPlayed
          ? 'Ball resolved — get ready for the next one'
          : 'You picked — waiting for your opponent to play…'
        : canSubmit
          ? 'Your turn'
          : 'Waiting for the other player…'

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-5 pb-8 pt-6 sm:max-w-lg">
      <Scoreboard game={game} />

      <div className="mt-4">
        <GameStatus
          items={[
            { label: `${game.batting_team_id ? teamLabel(game.batting_team_id) : ''} batting`, tone: 'green' },
            { label: `${game.bowling_team_id ? teamLabel(game.bowling_team_id) : ''} bowling`, tone: 'sky' },
            { label: status, tone: canSubmit ? 'amber' : 'slate' },
          ]}
        />
      </div>

      <div className="mt-4 space-y-3">
        <PlayerStatus
          label="Batter"
          player={batter}
          teamName={game.batting_team_id ? teamLabel(game.batting_team_id) : undefined}
          accent="emerald"
          isMe={me?.id === batter?.id}
          right={
            lastLabel ? (
              <span
                className={`animate-score-pop rounded-xl px-3 py-1.5 text-sm font-black ${
                  lastLabel.tone === 'rose'
                    ? 'bg-rose-500/20 text-rose-300'
                    : lastLabel.tone === 'amber'
                      ? 'bg-amber-500/15 text-amber-300'
                      : 'bg-emerald-500/15 text-emerald-300'
                }`}
              >
                {lastLabel.text}
              </span>
            ) : null
          }
        />
        <PlayerStatus
          label="Bowler"
          player={bowler}
          teamName={game.bowling_team_id ? teamLabel(game.bowling_team_id) : undefined}
          accent="sky"
          isMe={me?.id === bowler?.id}
        />
      </div>

      <div className="mt-3">
        <BowlerSelector
          bowler={bowler}
          teamName={game.bowling_team_id ? teamLabel(game.bowling_team_id) : undefined}
          onSwitch={switchBowler}
          disabled={!canSwitch}
          disabledReason={
            canSubmit || submitted || oppPlayed
              ? 'Bowler can only change between balls'
              : undefined
          }
        />
      </div>

      <div className="mt-auto pt-8">
        <MoveButtons
          onMove={submitMove}
          disabled={!canSubmit}
          busy={submitted}
          hint={hint}
        />
      </div>

      <MoveReveal ball={ball} />
    </div>
  )
}
