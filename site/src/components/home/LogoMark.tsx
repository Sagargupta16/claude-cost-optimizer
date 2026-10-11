/** Site mark: three falling bars, a cost curve going down. Decorative only. */
function LogoMark({ className }: Readonly<{ className?: string }>) {
  return (
    <svg className={className} viewBox="0 0 32 32" width="22" height="22" aria-hidden="true" focusable="false">
      <rect x="1" y="1" width="30" height="30" rx="7" fill="#161b22" stroke="#30363d" strokeWidth="1.5" />
      <rect x="8" y="8" width="4" height="16" rx="1" fill="#58a6ff" />
      <rect x="14" y="13" width="4" height="11" rx="1" fill="#58a6ff" opacity="0.8" />
      <rect x="20" y="18" width="4" height="6" rx="1" fill="#58a6ff" opacity="0.6" />
    </svg>
  )
}

export default LogoMark
