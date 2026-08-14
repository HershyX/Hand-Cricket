export default function Button({
  variant = 'primary',
  size = 'md',
  full = false,
  className = '',
  disabled = false,
  children,
  ...rest
}) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-2xl font-bold transition-all duration-150 ' +
    'focus:outline-none focus-visible:ring-4 focus-visible:ring-emerald-400/40 active:scale-[0.98] ' +
    'disabled:cursor-not-allowed disabled:opacity-40 disabled:active:scale-100'

  const variants = {
    primary:
      'bg-emerald-500 text-emerald-950 shadow-lg shadow-emerald-500/25 hover:bg-emerald-400',
    lime: 'bg-lime-400 text-lime-950 shadow-lg shadow-lime-400/25 hover:bg-lime-300',
    secondary:
      'bg-white/5 text-slate-100 ring-1 ring-white/15 hover:bg-white/10',
    ghost: 'bg-transparent text-slate-300 hover:bg-white/5 hover:text-slate-100',
    danger: 'bg-rose-500/90 text-white shadow-lg shadow-rose-500/25 hover:bg-rose-500',
  }

  const sizes = {
    sm: 'px-4 py-2 text-sm',
    md: 'px-5 py-3 text-base',
    lg: 'px-7 py-4 text-lg',
  }

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${full ? 'w-full' : ''} ${className}`}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  )
}
