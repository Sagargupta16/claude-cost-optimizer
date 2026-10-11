import { CACHE_HIT_MULTIPLIER_DEFAULT, MODELS, formatRate, type ModelPricing } from '../../utils/pricing'

// Everything the home-page visuals show is derived here from MODELS, so a
// price change in utils/pricing.ts reaches the charts, captions and alt text
// without anyone retyping a number.

/** The current, generally available lineup: active and not invite-only. */
export function currentModels(): ModelPricing[] {
  return Object.values(MODELS).filter((m) => m.lifecycle === 'active' && !m.inviteOnly)
}

/** 100000 -> "100K". */
export function formatTokensShort(tokens: number): string {
  return tokens >= 1000 ? `${tokens / 1000}K` : `${tokens}`
}

/** 0.05 -> "0.05x"; float noise from the division is rounded away. */
export function formatMultiplier(multiplier: number): string {
  return `${Number(multiplier.toFixed(3))}x`
}

export interface LadderRow {
  key: string
  name: string
  note: string
  input: number
  output: number
}

/** Per-1M input/output rates, one row per model plus one per long-prompt tier. */
export function ladderRows(): LadderRow[] {
  return currentModels()
    .flatMap((m): LadderRow[] => {
      const base = { key: m.id, name: m.name, note: '', input: m.inputPer1M, output: m.outputPer1M }
      if (!m.longPrompt) return [base]
      const line = formatTokensShort(m.longPrompt.threshold)
      return [
        { ...base, note: `up to ${line} prompt` },
        {
          key: `${m.id}-long`,
          name: m.name,
          note: `over ${line} prompt`,
          input: m.longPrompt.inputPer1M,
          output: m.longPrompt.outputPer1M,
        },
      ]
    })
    .sort((a, b) => b.output - a.output)
}

/** The first current model priced by prompt length, with its line ("100K"). */
export function tieredModel(): { name: string; line: string } | undefined {
  const m = currentModels().find((model) => model.longPrompt)
  return m?.longPrompt ? { name: m.name, line: formatTokensShort(m.longPrompt.threshold) } : undefined
}

/** "Fable 5.1 $10 in / $50 out; ..." for alt text and screen readers. */
export function ladderSummary(rows: LadderRow[]): string {
  return rows
    .map((r) => {
      const label = r.note ? `${r.name} (${r.note})` : r.name
      return `${label} ${formatRate(r.input)} in / ${formatRate(r.output)} out`
    })
    .join('; ')
}

export interface CacheRow {
  key: string
  name: string
  multiplier: number
  cacheRead: number
  input: number
}

/** Cache-read price as a multiple of fresh input, highest multiple first. */
export function cacheRows(): CacheRow[] {
  return currentModels()
    .map((m) => ({
      key: m.id,
      name: m.name,
      multiplier: m.cacheHitPer1M / m.inputPer1M,
      cacheRead: m.cacheHitPer1M,
      input: m.inputPer1M,
    }))
    .sort((a, b) => b.multiplier - a.multiplier || a.name.localeCompare(b.name))
}

/**
 * Groups every active model (invite-only included) by cache-read multiple:
 * "0.025x on Fable 5.1 and Mythos 5.1, 0.05x on ...".
 */
export function cacheTierSummary(): string {
  const tiers = new Map<string, string[]>()
  const active = Object.values(MODELS)
    .filter((m) => m.lifecycle === 'active')
    .sort((a, b) => a.cacheHitPer1M / a.inputPer1M - b.cacheHitPer1M / b.inputPer1M)
  for (const m of active) {
    const key = formatMultiplier(m.cacheHitPer1M / m.inputPer1M)
    tiers.set(key, [...(tiers.get(key) ?? []), m.name])
  }
  return [...tiers].map(([mult, names]) => `${mult} on ${names.join(' and ')}`).join(', ')
}

/** The multiple most older models read cache at, from pricing.ts. */
export const DEFAULT_CACHE_MULTIPLIER = formatMultiplier(CACHE_HIT_MULTIPLIER_DEFAULT)
