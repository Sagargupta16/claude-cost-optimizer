const dollars = (decimals: number) =>
  new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })

const USD_2 = dollars(2)
const USD_3 = dollars(3)
const USD_4 = dollars(4)
const USD_SIGNED = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  signDisplay: 'exceptZero',
})

/** "$1,234.56" -- grouped dollars for report figures. */
export function usd(value: number): string {
  return USD_2.format(value)
}

/** "-$2.47" / "+$1.10" / "$0.00" for current-to-optimized changes. */
export function signedUsd(value: number): string {
  return USD_SIGNED.format(value)
}

/** Per-turn amounts are often under a cent, so keep enough decimals to tell turns apart. */
export function usdFine(value: number): string {
  const size = Math.abs(value)
  if (size >= 1) return USD_2.format(value)
  if (size >= 0.01) return USD_3.format(value)
  return USD_4.format(value)
}

export function tokenCount(tokens: number): string {
  return Math.round(tokens).toLocaleString('en-US')
}

const trimDecimal = (v: number) => v.toFixed(1).replace(/\.0$/, '')

/** 100000 -> "100K", 1500000 -> "1.5M". */
export function compactTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${trimDecimal(tokens / 1_000_000)}M`
  if (tokens >= 1000) return `${trimDecimal(tokens / 1000)}K`
  return String(tokens)
}

/**
 * Round axis ticks from 0 whose top tick clears `max`, so a line never exits the plot. Allows one
 * extra tick over `count` so the top stays close to the data (0.20 gets a 0.25 top, not 0.30).
 */
export function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0, 1]
  const rough = max / count
  const pow = 10 ** Math.floor(Math.log10(rough))
  const step = [1, 2, 5, 10].map((m) => m * pow).find((s) => max / s <= count + 1) ?? 10 * pow
  const steps = Math.ceil(max / step - 0.001)
  return Array.from({ length: steps + 1 }, (_, i) => i * step)
}

/** "$0.05" or "$0.005": enough decimals that neighbouring tick labels differ. */
export function tickLabel(value: number, ticks: readonly number[]): string {
  const step = ticks.length > 1 ? ticks[1] - ticks[0] : 1
  const decimals = Math.min(4, Math.max(2, Math.ceil(-Math.log10(step) - 1e-9)))
  return `$${value.toFixed(decimals)}`
}
