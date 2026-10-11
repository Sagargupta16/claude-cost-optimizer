export type Health = 'good' | 'warn' | 'bad'

/** 80% of the points or more is good, under 50% is bad: the page's original bar thresholds. */
export function ratioHealth(score: number, maxScore: number): Health {
  const ratio = maxScore > 0 ? score / maxScore : 0
  if (ratio >= 0.8) return 'good'
  if (ratio >= 0.5) return 'warn'
  return 'bad'
}

// Same values as --accent-green, --warning-yellow and --error-red in index.css.
// Hex rather than var() because SVG presentation attributes do not resolve var().
export const HEALTH_COLOR: Record<Health, string> = {
  good: '#3fb950',
  warn: '#d29922',
  bad: '#f85149',
}

export function money(value: number): string {
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
