import { useState } from 'react'
import Button from '../components/Button'
import ScreenShell from '../components/ScreenShell'
import { useGame, SCREENS } from '../state/GameContext'

export default function CreateRoom() {
  const { navigate, createRoom } = useGame()
  const [name, setName] = useState('')
  const [overs, setOvers] = useState(2)

  return (
    <ScreenShell
      title="Create a room"
      subtitle="Set up your match and invite a friend."
      actions={
        <Button size="sm" variant="ghost" onClick={() => navigate(SCREENS.landing)}>
          Back
        </Button>
      }
    >
      <form
        className="flex flex-1 flex-col gap-6"
        onSubmit={(e) => {
          e.preventDefault()
          createRoom({ name, overs })
        }}
      >
        <label className="block">
          <span className="mb-1.5 block text-xs font-black uppercase tracking-wide text-slate-400">
            Your name
          </span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Aarav"
            maxLength={20}
            className="w-full rounded-2xl bg-white/5 px-4 py-3.5 text-base font-bold text-slate-50 placeholder:text-slate-500 ring-1 ring-white/10 outline-none transition focus:ring-2 focus:ring-emerald-400"
          />
        </label>

        <div>
          <span className="mb-2 block text-xs font-black uppercase tracking-wide text-slate-400">
            Overs per side
          </span>
          <div className="grid grid-cols-5 gap-2.5">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setOvers(n)}
                className={`rounded-2xl py-3.5 text-lg font-black transition active:scale-95 ${
                  overs === n
                    ? 'bg-emerald-500 text-emerald-950 shadow-lg shadow-emerald-500/25'
                    : 'bg-white/5 text-slate-300 ring-1 ring-white/10 hover:bg-white/10'
                }`}
              >
                {n}
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs font-semibold text-slate-500">
            {overs} over{overs > 1 ? 's' : ''} of 6 balls each per team.
          </p>
        </div>

        <div className="mt-auto pt-2">
          <Button size="lg" full type="submit">
            Create room
          </Button>
        </div>
      </form>
    </ScreenShell>
  )
}
