import { useState } from 'react'
import Button from '../components/Button'
import ScreenShell from '../components/ScreenShell'
import { useGame, SCREENS } from '../state/GameContext'

export default function JoinRoom() {
  const { navigate, joinRoom } = useGame()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')

  const cleanCode = (value) => value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6)

  return (
    <ScreenShell
      title="Join a room"
      subtitle="Enter the code shared by your friend."
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
          if (cleanCode(code).length < 4) return
          joinRoom({ code, name })
        }}
      >
        <label className="block">
          <span className="mb-1.5 block text-xs font-black uppercase tracking-wide text-slate-400">
            Room code
          </span>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(cleanCode(e.target.value))}
            placeholder="7K3M9Q"
            maxLength={6}
            inputMode="text"
            autoCapitalize="characters"
            className="w-full rounded-2xl bg-white/5 px-4 py-3.5 text-center font-mono text-2xl font-black tracking-[0.4em] text-slate-50 placeholder:text-slate-600 ring-1 ring-white/10 outline-none transition focus:ring-2 focus:ring-emerald-400"
          />
        </label>

        <label className="block">
          <span className="mb-1.5 block text-xs font-black uppercase tracking-wide text-slate-400">
            Your name
          </span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Rohan"
            maxLength={20}
            className="w-full rounded-2xl bg-white/5 px-4 py-3.5 text-base font-bold text-slate-50 placeholder:text-slate-500 ring-1 ring-white/10 outline-none transition focus:ring-2 focus:ring-emerald-400"
          />
        </label>

        <div className="mt-auto pt-2">
          <Button
            size="lg"
            full
            type="submit"
            disabled={cleanCode(code).length < 4}
          >
            Join room
          </Button>
        </div>
      </form>
    </ScreenShell>
  )
}
