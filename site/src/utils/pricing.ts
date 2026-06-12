// Pricing data verified against Anthropic docs on 2026-06-12:
//   - https://platform.claude.com/docs/en/about-claude/pricing
//   - https://platform.claude.com/docs/en/about-claude/models/overview
//   - https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5
//   - https://platform.claude.com/docs/en/build-with-claude/fast-mode
//   - https://platform.claude.com/docs/en/about-claude/model-deprecations
//   - https://claude.com/pricing

export type ModelId =
  | 'fable-5'
  | 'opus'
  | 'opus-4-7'
  | 'opus-4-6'
  | 'opus-4-5'
  | 'sonnet'
  | 'sonnet-4-5'
  | 'haiku'
  | 'mythos-5'
  | 'mythos'

export interface ModelPricing {
  id: ModelId
  name: string
  inputPer1M: number
  outputPer1M: number
  cacheHitPer1M: number
  cacheWrite5mPer1M: number
  cacheWrite1hPer1M: number
  contextWindow: string
  maxOutput: string
  fastModeCapable: boolean
  // Fast Mode premium relative to standard rates. Opus 4.8 is 2x ($10/$50);
  // Opus 4.7 / 4.6 are 6x ($30/$150). Undefined when fastModeCapable is false.
  fastModeMultiplier?: number
  tokenizerOverhead?: number
  notes?: string
  inviteOnly?: boolean
  lifecycle?: 'active' | 'legacy'
}

export const MODELS: Record<ModelId, ModelPricing> = {
  'fable-5': {
    id: 'fable-5',
    name: 'Fable 5',
    inputPer1M: 10,
    outputPer1M: 50,
    cacheHitPer1M: 1,
    cacheWrite5mPer1M: 12.5,
    cacheWrite1hPer1M: 20,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: false,
    // Docs: same tokenizer as Opus 4.7, "roughly 30% more tokens" vs pre-4.7 models.
    tokenizerOverhead: 1.3,
    lifecycle: 'active',
    notes:
      "Anthropic's most capable widely released model (Mythos-class tier, GA 2026-06-09). " +
      '2x Opus 4.8 pricing. Adaptive thinking always on; control depth with effort. ' +
      'Safety classifiers can refuse requests (stop_reason "refusal"; pre-output refusals are free, ' +
      'beta fallbacks param + fallback credit cover retries). No Fast Mode; Batch supported ($5/$25). ' +
      'Requires 30-day data retention. 1M context at standard rates. ' +
      'GA on Claude API, Claude Platform on AWS, Bedrock, Vertex AI, and Microsoft Foundry.',
  },
  opus: {
    id: 'opus',
    name: 'Opus 4.8',
    inputPer1M: 5,
    outputPer1M: 25,
    cacheHitPer1M: 0.5,
    cacheWrite5mPer1M: 6.25,
    cacheWrite1hPer1M: 10,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: true,
    fastModeMultiplier: 2,
    tokenizerOverhead: 1.35,
    lifecycle: 'active',
    notes:
      'Opus-tier flagship (Fable 5 sits above it at 2x). New tokenizer (up to 35% more tokens for the same text). ' +
      'Adaptive thinking only; effort defaults to high on all surfaces. ' +
      'Fast Mode supported at 2x ($10/$50). 1M context at standard rates. ' +
      'Knowledge cutoff Jan 2026. Earliest retirement: 2027-05-28. ' +
      'GA on Anthropic API, Claude Platform on AWS, Bedrock, and Vertex AI (200K context on Microsoft Foundry).',
  },
  'opus-4-7': {
    id: 'opus-4-7',
    name: 'Opus 4.7',
    inputPer1M: 5,
    outputPer1M: 25,
    cacheHitPer1M: 0.5,
    cacheWrite5mPer1M: 6.25,
    cacheWrite1hPer1M: 10,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: true,
    fastModeMultiplier: 6,
    tokenizerOverhead: 1.35,
    lifecycle: 'legacy',
    notes:
      'Previous-generation flagship. New tokenizer (up to 35% more tokens for the same text). ' +
      'Adaptive thinking only with xhigh effort level. Fast Mode supported (6x = $30/$150). ' +
      'Earliest retirement: 2027-04-16. Migrate to Opus 4.8 for the same price.',
  },
  'opus-4-6': {
    id: 'opus-4-6',
    name: 'Opus 4.6',
    inputPer1M: 5,
    outputPer1M: 25,
    cacheHitPer1M: 0.5,
    cacheWrite5mPer1M: 6.25,
    cacheWrite1hPer1M: 10,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: true,
    fastModeMultiplier: 6,
    lifecycle: 'legacy',
    notes:
      'Legacy. Extended + adaptive thinking. Fast Mode (6x) deprecated as of the Opus 4.8 ' +
      'launch and removed ~30 days later (then falls back to standard speed). ' +
      'Earliest retirement: 2027-02-05. Migrate to Opus 4.8.',
  },
  'opus-4-5': {
    id: 'opus-4-5',
    name: 'Opus 4.5',
    inputPer1M: 5,
    outputPer1M: 25,
    cacheHitPer1M: 0.5,
    cacheWrite5mPer1M: 6.25,
    cacheWrite1hPer1M: 10,
    contextWindow: '200K',
    maxOutput: '64K',
    fastModeCapable: false,
    lifecycle: 'legacy',
    notes:
      'Legacy. Extended thinking. No Fast Mode. 200K context (not 1M). ' +
      'Earliest retirement: 2026-11-24. Migrate to Opus 4.8 unless you have a workload pinned to this snapshot.',
  },
  sonnet: {
    id: 'sonnet',
    name: 'Sonnet 4.6',
    inputPer1M: 3,
    outputPer1M: 15,
    cacheHitPer1M: 0.3,
    cacheWrite5mPer1M: 3.75,
    cacheWrite1hPer1M: 6,
    contextWindow: '1M',
    maxOutput: '64K',
    fastModeCapable: false,
    lifecycle: 'active',
    notes:
      'Extended + adaptive thinking. Best general-purpose default for production workloads. ' +
      'Earliest retirement: 2027-02-17.',
  },
  'sonnet-4-5': {
    id: 'sonnet-4-5',
    name: 'Sonnet 4.5',
    inputPer1M: 3,
    outputPer1M: 15,
    cacheHitPer1M: 0.3,
    cacheWrite5mPer1M: 3.75,
    cacheWrite1hPer1M: 6,
    contextWindow: '200K',
    maxOutput: '64K',
    fastModeCapable: false,
    lifecycle: 'legacy',
    notes:
      'Legacy. Extended thinking. 200K context. Earliest retirement: 2026-09-29. ' +
      'Migrate to Sonnet 4.6 for the 1M-context window unless your workload is pinned.',
  },
  haiku: {
    id: 'haiku',
    name: 'Haiku 4.5',
    inputPer1M: 1,
    outputPer1M: 5,
    cacheHitPer1M: 0.1,
    cacheWrite5mPer1M: 1.25,
    cacheWrite1hPer1M: 2,
    contextWindow: '200K',
    maxOutput: '64K',
    fastModeCapable: false,
    lifecycle: 'active',
    notes:
      'Extended thinking. No adaptive thinking. Fastest latency. ' +
      'Earliest retirement: 2026-10-15.',
  },
  'mythos-5': {
    id: 'mythos-5',
    name: 'Mythos 5',
    inputPer1M: 10,
    outputPer1M: 50,
    cacheHitPer1M: 1,
    cacheWrite5mPer1M: 12.5,
    cacheWrite1hPer1M: 20,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: false,
    tokenizerOverhead: 1.3,
    inviteOnly: true,
    lifecycle: 'active',
    notes:
      "Fable 5's capabilities without the safety classifiers. Same specs and pricing. " +
      'Limited availability to approved Project Glasswing customers only. ' +
      'Successor to Mythos Preview.',
  },
  mythos: {
    id: 'mythos',
    name: 'Mythos Preview',
    inputPer1M: 25,
    outputPer1M: 125,
    cacheHitPer1M: 2.5,
    cacheWrite5mPer1M: 31.25,
    cacheWrite1hPer1M: 50,
    contextWindow: '1M',
    maxOutput: 'n/a',
    fastModeCapable: false,
    inviteOnly: true,
    lifecycle: 'legacy',
    notes:
      'Superseded by Mythos 5 -- retires 2026-06-30. Was the invitation-only ' +
      'defensive-cybersecurity research preview under Project Glasswing.',
  },
}

// Default Fast Mode premium for models without an explicit fastModeMultiplier.
// Prefer ModelPricing.fastModeMultiplier: Opus 4.8 is 2x ($10/$50), while
// Opus 4.7 / 4.6 are 6x ($30/$150).
export const FAST_MODE_MULTIPLIER = 6
export const FAST_MODE_OTPS_GAIN = 2.5 // up to 2.5x output tokens per second
export const BATCH_DISCOUNT = 0.5
export const REGIONAL_ENDPOINT_PREMIUM = 1.1
export const DATA_RESIDENCY_PREMIUM = 1.1

// Subscription pricing — monthly vs annual.
// Pro annual = $200 up front, billed yearly (effective ~$16.67/mo, ~17% off).
export const SUBSCRIPTION_PRICING = {
  proMonthly: 20,
  proAnnualUpfront: 200,
  proAnnualEffectiveMonthly: 200 / 12,
  max5x: 100,
  max20x: 200,
}

export const TOKEN_ESTIMATES = {
  tokensPerClaudeMdLine: 7,
  systemPromptTokens: 3500,
  tokensPerMcpServer: 1500,
  tokensPerFileRead: 2000,
  outputTokensPerTurn: 500,
  historyGrowthPerTurn: 1500,
  cacheHitRate: 0.7,
}

export function formatDollars(amount: number): string {
  return `$${amount.toFixed(2)}`
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`
}

export function effectiveInputCost(model: ModelPricing): number {
  return model.inputPer1M * (model.tokenizerOverhead ?? 1)
}

export function effectiveOutputCost(model: ModelPricing): number {
  return model.outputPer1M * (model.tokenizerOverhead ?? 1)
}
