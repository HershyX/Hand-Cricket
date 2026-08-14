import { useState } from 'react'
import Button from '../components/Button'
import ScreenShell from '../components/ScreenShell'
import { useGame, SCREENS } from '../state/GameContext'

export default function CreateRoom() {
  const { navigate, createRoom, busy } = useGame()
  const [name, setName] = useState('')
  const [error, setError] = useState(null)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)
    const result = await createRoom({ name })
    if (!result.ok) setError(result.error)
  }

  return (
    <ScreenShell
      title="Create a room"
      subtitle="Set up your match and share the room code."
      actions={
        <Button size="sm" variant="ghost" onClick={() => navigate(SCREENS.landing)}>
          Back
        </Button>
      }
    >
      <form className="flex flex-1 flex-col gap-6" onSubmit={submit}>
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

        {error && (
          <p className="rounded-xl bg-rose-500/15 px-4 py-3 text-sm font-bold text-rose-300 ring-1 ring-rose-400/30">
            {error}
          </p>
        )}

        <div className="mt-auto pt-2">
          <Button size="lg" full type="submit" disabled={busy}>
            {busy ? 'Creating…' : 'Create room'}
          </Button>
        </div>
      </form>
    </ScreenShell>
  )
}
