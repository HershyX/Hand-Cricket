export default function CricketBall({ size = 32, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <circle cx="32" cy="32" r="30" fill="#dc2626" />
      <circle cx="32" cy="32" r="30" fill="url(#ballShine)" />
      <ellipse cx="32" cy="32" rx="30" ry="10" fill="none" stroke="#7f1d1d" strokeWidth="2" />
      <ellipse cx="32" cy="32" rx="30" ry="10" fill="none" stroke="#7f1d1d" strokeWidth="2" transform="rotate(60 32 32)" />
      <ellipse cx="32" cy="32" rx="30" ry="10" fill="none" stroke="#7f1d1d" strokeWidth="2" transform="rotate(120 32 32)" />
      <defs>
        <radialGradient id="ballShine" cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="rgba(255,255,255,0.55)" />
          <stop offset="45%" stopColor="rgba(255,255,255,0.12)" />
          <stop offset="100%" stopColor="rgba(0,0,0,0.25)" />
        </radialGradient>
      </defs>
    </svg>
  )
}
