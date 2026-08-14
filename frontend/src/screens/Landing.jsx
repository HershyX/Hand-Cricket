import Button from '../components/Button'
import CricketBall from '../components/CricketBall'
import Logo from '../components/Logo'
import { useGame, SCREENS } from '../state/GameContext'

export default function Landing() {
  const { navigate } = useGame()

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-6 py-10 sm:max-w-lg">
      <header className="animate-rise">
        <Logo size={44} />
      </header>

      <main className="flex flex-1 flex-col items-center justify-center py-12 text-center">
        <div className="animate-bounce-in">
          <CricketBall size={84} className="animate-toss-ball drop-shadow-[0_0_25px_rgba(220,38,38,0.35)]" />
        </div>

        <h1 className="mt-8 animate-rise text-4xl font-black leading-tight tracking-tight text-slate-50 sm:text-5xl">
          Play the game
          <br />
          <span className="bg-gradient-to-r from-emerald-400 to-lime-300 bg-clip-text text-transparent">
            you grew up with
          </span>
          <br />
          online.
        </h1>

        <p className="mt-4 max-w-sm animate-rise text-base text-slate-400 [animation-delay:0.15s]">
          Face off with a friend in instant hand cricket. Call the toss, pick your numbers,
          and outsmart the bowler one ball at a time.
        </p>

        <div className="mt-10 w-full max-w-xs animate-rise space-y-3 [animation-delay:0.25s]">
          <Button
            size="lg"
            full
            variant="primary"
            onClick={() => navigate(SCREENS.createRoom)}
          >
            Create a Room
          </Button>
          <Button
            size="lg"
            full
            variant="secondary"
            onClick={() => navigate(SCREENS.joinRoom)}
          >
            Join a Room
          </Button>
        </div>
      </main>

      <footer className="animate-fade-in text-center text-xs font-semibold text-slate-500 [animation-delay:0.4s]">
        Free • No sign-up • Real-time matches
      </footer>
    </div>
  )
}
