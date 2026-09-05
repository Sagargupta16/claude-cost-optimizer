// Pricing data verified against Anthropic docs on 2026-09-05 (Fable 5.1 launch):
//   - https://platform.claude.com/docs/en/about-claude/pricing
//   - https://platform.claude.com/docs/en/about-claude/models/overview
//   - https://platform.claude.com/docs/en/about-claude/models/migrating-to-claude-opus-5
//   - https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5-and-claude-mythos-5
//   - https://platform.claude.com/docs/en/build-with-claude/fast-mode
//   - https://platform.claude.com/docs/en/build-with-claude/prompt-caching
//   - https://platform.claude.com/docs/en/about-claude/model-deprecations
//   - https://claude.com/pricing

export type ModelId =
  | 'fable-5-1'
  | 'fable-5'
  | 'opus-5'
  | 'opus-4-8'
  | 'opus-4-7'
  | 'opus-4-6'
  | 'opus-4-5'
  | 'sonnet-5'
  | 'sonnet'
  | 'sonnet-4-5'
  | 'haiku'
  | 'mythos-5-1'
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
  // Fast Mode premium relative to standard rates. Opus 5 and Opus 4.8 are the
  // only supported models, both at 2x ($10/$50). Undefined when
  // fastModeCapable is false.
  fastModeMultiplier?: number
  tokenizerOverhead?: number
  // Minimum prompt length (tokens) before a cache_control block does anything.
  // Shorter prefixes are silently not cached, so cache savings are 0 below this.
  minCacheTokens: number
  notes?: string
  inviteOnly?: boolean
  lifecycle?: 'active' | 'legacy'
}

// Cache hits are 0.1x base input on every model EXCEPT Fable 5.1 and Mythos 5.1,
// which read at 0.025x ($0.25/MTok). Derive displays from cacheHitPer1M rather
// than multiplying input by 0.1 -- that shortcut is now wrong on two models.
export const CACHE_HIT_MULTIPLIER_DEFAULT = 0.1
export const CACHE_HIT_MULTIPLIER_FABLE_5_1 = 0.025

/** Cache-read discount off base input, as a share (0.9 = 90% off). */
export function cacheDiscountShare(model: ModelPricing): number {
  return 1 - model.cacheHitPer1M / model.inputPer1M
}

export const MODELS: Record<ModelId, ModelPricing> = {
  'fable-5-1': {
    id: 'fable-5-1',
    name: 'Fable 5.1',
    inputPer1M: 10,
    outputPer1M: 50,
    // 0.025x base input -- the only tier that breaks the universal 0.1x cache rule.
    cacheHitPer1M: 0.25,
    cacheWrite5mPer1M: 12.5,
    cacheWrite1hPer1M: 20,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: false,
    // Same tokenizer as Fable 5 / Opus 4.7+: ~30% more tokens vs pre-4.7 models.
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    lifecycle: 'active',
    notes:
      "Anthropic's most capable widely released model (GA 2026-09-04). Same $10/$50 as Fable 5, " +
      'but cache reads are $0.25/MTok -- 0.025x base input, a quarter of Fable 5 and the only ' +
      'exception to the 0.1x cache-hit rule. That makes a cache miss expensive relative to a hit, ' +
      'so a max_tokens:0 keep-alive on the 5-minute TTL usually beats paying the 2x 1-hour write. ' +
      'Adaptive thinking always on (thinking disabled/budget_tokens both 400); control depth with effort. ' +
      'Three breaking changes vs Fable 5: forced tool_choice (any/tool) returns 400, thinking blocks ' +
      'are bound to the producing model, and editing earlier turns invalidates thinking blocks ' +
      '(preserved thinking -- accounts created on/after 2026-08-31 get a 400 on edited history). ' +
      'No Fast Mode, no Priority Tier. Batch $5/$25. Requires 30-day retention (ZDR returns 400). ' +
      '1M context at standard rates. Min cacheable prompt 512 tokens.',
  },
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
    minCacheTokens: 512,
    lifecycle: 'legacy',
    notes:
      'Previous Fable-tier release (GA 2026-06-09), superseded by Fable 5.1 at the same $10/$50. ' +
      'Still served and selectable by id. The one reason to prefer it: cache reads cost $1/MTok here ' +
      'versus $0.25 on Fable 5.1, so migrating is strictly cheaper on any cached workload. ' +
      'Adaptive thinking always on; control depth with effort. No Fast Mode; Batch $5/$25. ' +
      'Requires 30-day data retention. 1M context at standard rates. Min cacheable prompt 512 tokens.',
  },
  'opus-5': {
    id: 'opus-5',
    name: 'Opus 5',
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
    minCacheTokens: 512,
    lifecycle: 'active',
    notes:
      'Opus-tier flagship and the recommended default for complex agentic coding (GA 2026-07-24). ' +
      'Same $5/$25 as Opus 4.8, so the upgrade is free at the posted rate. ' +
      'Adaptive thinking is ON by default when you omit the thinking param -- max_tokens is a hard cap ' +
      'on thinking plus text, so budget it (64K+ if you run xhigh/max effort). ' +
      'thinking {type:"disabled"} is only legal at effort high or below; pairing it with xhigh/max returns a 400. ' +
      'Min cacheable prompt 512 tokens (half of Opus 4.8), so short system prompts now cache. ' +
      'Fast Mode supported at 2x ($10/$50). Batch $2.50/$12.50. 1M context at standard rates; ' +
      '128K max output (300K on Batch via the output-300k-2026-03-24 beta). ' +
      'Ships cybersecurity safety classifiers -- a cyber refusal can auto-fall-back to Opus 4.8 via the ' +
      'server-side fallbacks param. Knowledge cutoff May 2026. Earliest retirement: 2027-07-24. ' +
      'GA on Claude API, Claude Platform on AWS, Bedrock (anthropic.claude-opus-5), and Vertex AI.',
  },
  'opus-4-8': {
    id: 'opus-4-8',
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
    minCacheTokens: 1024,
    lifecycle: 'legacy',
    notes:
      'Previous Opus-tier flagship, moved to legacy by the Opus 5 launch. Same $5/$25 price as Opus 5, ' +
      'so there is no cost reason to stay -- migrate unless your prompts are tuned to this snapshot ' +
      '(or you need thinking off at xhigh/max, which Opus 5 rejects). ' +
      'Adaptive thinking, off by default; effort defaults to high. Fast Mode supported at 2x ($10/$50). ' +
      '1M context at standard rates. Min cacheable prompt 1,024 tokens. Knowledge cutoff Jan 2026. ' +
      'Still the server-side fallback target for Opus 5 cyber refusals. Earliest retirement: 2027-05-28.',
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
    fastModeCapable: false,
    tokenizerOverhead: 1.35,
    minCacheTokens: 2048,
    lifecycle: 'legacy',
    notes:
      'Legacy. New tokenizer (up to 35% more tokens for the same text). ' +
      'Adaptive thinking only with xhigh effort level. ' +
      'Fast Mode has been removed: speed "fast" now returns an error here, with no fallback to standard. ' +
      'Min cacheable prompt 2,048 tokens. Earliest retirement: 2027-04-16. ' +
      'Migrate to Opus 5 for the same price.',
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
    fastModeCapable: false,
    minCacheTokens: 4096,
    lifecycle: 'legacy',
    notes:
      'Legacy. Extended + adaptive thinking. Fast Mode has been removed: speed "fast" is accepted ' +
      'but silently runs at standard speed and standard rates (usage.speed comes back "standard"). ' +
      'Min cacheable prompt 4,096 tokens. Earliest retirement: 2027-02-05. Migrate to Opus 5.',
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
    minCacheTokens: 4096,
    lifecycle: 'legacy',
    notes:
      'Legacy. Extended thinking. No Fast Mode. 200K context (not 1M). Min cacheable prompt 4,096 tokens. ' +
      'Earliest retirement: 2026-11-24. Migrate to Opus 5 unless you have a workload pinned to this snapshot.',
  },
  'sonnet-5': {
    id: 'sonnet-5',
    name: 'Sonnet 5',
    // $2/$10 is now the STANDARD price. The launch "introductory" rate was made
    // permanent on 2026-09-01; the scheduled rise to $3/$15 was cancelled.
    inputPer1M: 2,
    outputPer1M: 10,
    cacheHitPer1M: 0.2,
    cacheWrite5mPer1M: 2.5,
    cacheWrite1hPer1M: 4,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: false,
    // New tokenizer shared with Opus 4.7+/Fable 5 -- ~30% more tokens for the same text.
    tokenizerOverhead: 1.3,
    minCacheTokens: 1024,
    lifecycle: 'active',
    notes:
      'Current Sonnet-tier flagship (GA 2026-06-30): best combination of speed and intelligence. ' +
      '$2/$10 per MTok is now the permanent standard price -- Anthropic cancelled the increase to ' +
      '$3/$15 that was scheduled for 2026-09-01, so this is 60% cheaper than Opus 5 rather than 40%. ' +
      'Adaptive thinking (effort defaults to high on the Claude API and Claude Code). No Fast Mode. ' +
      '1M context at standard rates; Batch $1/$5. Min cacheable prompt 1,024 tokens. ' +
      'Earliest retirement: 2027-06-30.',
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
    minCacheTokens: 1024,
    lifecycle: 'legacy',
    notes:
      'Legacy. Extended + adaptive thinking. Previous general-purpose default. ' +
      'Min cacheable prompt 1,024 tokens. Earliest retirement: 2027-02-17. Migrate to Sonnet 5.',
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
    minCacheTokens: 1024,
    lifecycle: 'legacy',
    notes:
      'Legacy. Extended thinking. 200K context. Min cacheable prompt 1,024 tokens. ' +
      'Earliest retirement: 2026-09-29. Migrate to Sonnet 5 for the 1M-context window ' +
      'unless your workload is pinned.',
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
    minCacheTokens: 4096,
    lifecycle: 'active',
    notes:
      'Extended thinking. No adaptive thinking. Fastest latency. ' +
      'Min cacheable prompt 4,096 tokens -- the highest of any current model, so short ' +
      'system prompts get no cache discount here. Earliest retirement: 2026-10-15.',
  },
  'mythos-5-1': {
    id: 'mythos-5-1',
    name: 'Mythos 5.1',
    inputPer1M: 10,
    outputPer1M: 50,
    // Confirmed on the pricing page: the 0.025x rate covers Mythos 5.1 too.
    cacheHitPer1M: 0.25,
    cacheWrite5mPer1M: 12.5,
    cacheWrite1hPer1M: 20,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: false,
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    inviteOnly: true,
    lifecycle: 'active',
    notes:
      'Fable 5.1 offered under Project Glasswing: same capabilities, limits, and pricing, ' +
      'including the $0.25/MTok (0.025x) cache-read rate. Unlike Mythos 5 it runs safeguards ' +
      'that depend on the access program, so stop_reason "refusal" can occur. ' +
      'Approved Glasswing customers only; not offered on Claude Platform on AWS. ' +
      'Min cacheable prompt 512 tokens. Successor to Mythos 5.',
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
    minCacheTokens: 512,
    inviteOnly: true,
    lifecycle: 'legacy',
    notes:
      "Fable 5's capabilities without the safety classifiers, so stop_reason \"refusal\" never " +
      'occurs. Same specs and pricing as Fable 5, including the $1/MTok cache read. ' +
      'Superseded by Mythos 5.1 (which reads at $0.25/MTok). ' +
      'Limited availability to approved Project Glasswing customers only. ' +
      'Min cacheable prompt 512 tokens. Successor to Mythos Preview.',
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
    minCacheTokens: 2048,
    inviteOnly: true,
    lifecycle: 'legacy',
    notes:
      'Superseded by Mythos 5 -- retired 2026-06-30. Was the invitation-only ' +
      'defensive-cybersecurity research preview under Project Glasswing.',
  },
}

// Default Fast Mode premium for models without an explicit fastModeMultiplier.
// Prefer ModelPricing.fastModeMultiplier. Only Opus 5 and Opus 4.8 support Fast
// Mode, and both are 2x ($10/$50), so 2 is the only sensible default.
export const FAST_MODE_MULTIPLIER = 2
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
