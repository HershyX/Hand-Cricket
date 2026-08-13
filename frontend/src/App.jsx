function App() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6 text-center">
      <div className="w-full max-w-md">
        <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
          Hand Cricket Online
        </h1>
        <p className="mt-4 text-lg text-slate-400">
          Multiplayer hand cricket with friends.
        </p>

        <div className="mt-10 flex flex-col gap-4">
          <button
            type="button"
            className="rounded-lg bg-emerald-500 px-6 py-3 text-lg font-semibold text-white transition hover:bg-emerald-400"
          >
            Create Room
          </button>
          <button
            type="button"
            className="rounded-lg border border-slate-600 px-6 py-3 text-lg font-semibold text-slate-200 transition hover:border-slate-400 hover:text-white"
          >
            Join Room
          </button>
        </div>

        <p className="mt-8 text-sm text-slate-500">
          Private rooms with friends. Coming soon.
        </p>
      </div>
    </div>
  )
}

export default App
