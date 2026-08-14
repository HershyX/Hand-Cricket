import CricketBall from './CricketBall'

export default function Logo({ size = 40, withText = true, className = '' }) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <CricketBall size={size} />
      {withText && (
        <div className="leading-tight">
          <p className="text-lg font-black tracking-tight text-slate-50">
            Hand Cricket
          </p>
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-emerald-400">
            Online
          </p>
        </div>
      )}
    </div>
  )
}
