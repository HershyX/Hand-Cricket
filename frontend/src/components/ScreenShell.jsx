import Logo from './Logo'

export default function ScreenShell({ title, subtitle, children, actions, className = '' }) {
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col px-5 pb-10 pt-8 sm:max-w-lg">
      <header className="mb-7 flex items-center justify-between gap-3">
        <Logo size={32} />
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </header>

      {(title || subtitle) && (
        <div className="mb-6 animate-rise">
          {title && (
            <h1 className="text-2xl font-black tracking-tight text-slate-50">{title}</h1>
          )}
          {subtitle && <p className="mt-1.5 text-sm text-slate-400">{subtitle}</p>}
        </div>
      )}

      <div className={`flex flex-1 flex-col ${className}`}>{children}</div>
    </div>
  )
}
