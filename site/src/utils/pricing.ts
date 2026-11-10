// Pricing data verified against Anthropic docs on 2026-11-10 (Fable 5.2 and Mythos 5.2 added
// 2026-11-09; Haiku 3.5 dropped from the pricing page):
//   - https://platform.claude.com/docs/en/about-claude/pricing
//   - https://platform.claude.com/docs/en/models/overview
//   - https://platform.claude.com/docs/en/models/haiku-5-5/overview
//   - https://platform.claude.com/docs/en/models/haiku-5-5/whats-new-haiku-5-5
//   - https://platform.claude.com/docs/en/models/sonnet-5-5/overview
//   - https://platform.claude.com/docs/en/models/sonnet-5-5/whats-new-sonnet-5-5
//   - https://platform.claude.com/docs/en/models/opus-5-5/overview
//   - https://platform.claude.com/docs/en/models/opus-5-5/migration-guide
//   - https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2
//   - https://platform.claude.com/docs/en/models/fable-5-1/overview
//   - https://platform.claude.com/docs/en/build-with-claude/fast-mode
//   - https://platform.claude.com/docs/en/build-with-claude/prompt-caching
//   - https://platform.claude.com/docs/en/about-claude/model-deprecations
//   - https://claude.com/pricing

export type ModelId =
  | 'fable-5-2'
  | 'fable-5-1'
  | 'fable-5'
  | 'opus-5-5'
  | 'opus-5'
  | 'opus-4-8'
  | 'opus-4-7'
  | 'opus-4-6'
  | 'opus-4-5'
  | 'sonnet-5-5'
  | 'sonnet-5'
  | 'sonnet'
  | 'sonnet-4-5'
  | 'haiku-5-5'
  | 'haiku'
  | 'mythos-5-2'
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
  // Fast Mode premium relative to standard rates. Fable 5.2, Mythos 5.2, Opus 5.5, Opus 5
  // and Opus 4.8 are the supported models, all at 2x of their own base rate: $16/$80 on
  // Fable 5.2 and Mythos 5.2, $8/$40 on Opus 5.5, $10/$50 on the other two.
  // Undefined when fastModeCapable is false.
  fastModeMultiplier?: number
  // Fast Mode availability caveat shown in the calculator; unset when Fast Mode is
  // generally available (Opus 5.5 since 2026-10-15).
  fastModeStatus?: string
  tokenizerOverhead?: number
  // Minimum prompt length (tokens) before a cache_control block does anything.
  // Shorter prefixes are silently not cached, so cache savings are 0 below this.
  minCacheTokens: number
  notes?: string
  inviteOnly?: boolean
  // 'deprecated' mirrors the state Anthropic's deprecations page publishes:
  // still served, no longer recommended, replacement named. It is distinct from
  // 'legacy', which only means superseded. Chart selection filters on
  // 'active', so a deprecated model is excluded the same way a legacy one is.
  lifecycle?: 'active' | 'legacy' | 'deprecated'
  // Prompt-length pricing. A request whose prompt -- all of its input tokens,
  // cache reads and writes included -- is over `threshold` pays these rates for
  // the whole request, output included. Only Haiku 5.5 has one (100,000 tokens);
  // every other model bills its full context window at one rate.
  longPrompt?: {
    threshold: number
    inputPer1M: number
    outputPer1M: number
    cacheHitPer1M: number
    cacheWrite5mPer1M: number
    cacheWrite1hPer1M: number
  }
}

/** Prompt-cache lifetime: '5m' writes at 1.25x input, '1h' at 2x. */
export type CacheTtl = '5m' | '1h'

/** How long each TTL keeps an unread prefix alive. A gap longer than this re-writes the prompt. */
export const CACHE_TTL_MINUTES: Record<CacheTtl, number> = { '5m': 5, '1h': 60 }

/**
 * The input, output, cache-read and cache-write rates a request of `promptTokens` pays. Writes
 * use the `ttl` cache: the 5-minute rate by default, the 1-hour rate for '1h' (Haiku 5.5 over its
 * 100K line uses the long-prompt tier's own 1-hour rate).
 */
export function ratesForPrompt(
  model: ModelPricing,
  promptTokens: number,
  ttl: CacheTtl = '5m',
): { inputPer1M: number; outputPer1M: number; cacheHitPer1M: number; cacheWritePer1M: number } {
  const tier = model.longPrompt && promptTokens > model.longPrompt.threshold ? model.longPrompt : model
  return {
    inputPer1M: tier.inputPer1M,
    outputPer1M: tier.outputPer1M,
    cacheHitPer1M: tier.cacheHitPer1M,
    cacheWritePer1M: ttl === '1h' ? tier.cacheWrite1hPer1M : tier.cacheWrite5mPer1M,
  }
}

/**
 * Input cost of one Claude Code turn, billed the way Claude Code caches a conversation: "the
 * prefix is the entire previous request and only the latest exchange is new"
 * (code.claude.com/docs/en/prompt-caching). The previous request is a cache read; the new part is
 * a cache write on the `ttl` cache (5-minute: 1.25x input, the default; 1-hour: 2x). The first
 * turn (previousPrompt 0) writes everything, and so does a turn after a gap longer than the TTL.
 * A prompt under the model's minimum cacheable length is not cached at all and pays full input,
 * reported as writeDollars (the new-input share).
 */
export function turnInputCost(
  model: ModelPricing,
  promptTokens: number,
  previousPrompt: number,
  ttl: CacheTtl = '5m',
): { readDollars: number; writeDollars: number } {
  const rates = ratesForPrompt(model, promptTokens, ttl)
  if (promptTokens < model.minCacheTokens) {
    return { readDollars: 0, writeDollars: (promptTokens / 1_000_000) * rates.inputPer1M }
  }
  const cacheRead = previousPrompt >= model.minCacheTokens ? Math.min(previousPrompt, promptTokens) : 0
  return {
    readDollars: (cacheRead / 1_000_000) * rates.cacheHitPer1M,
    writeDollars: ((promptTokens - cacheRead) / 1_000_000) * rates.cacheWritePer1M,
  }
}

// Cache hits are 0.1x base input on every model EXCEPT six: Fable 5.2, Mythos 5.2,
// Fable 5.1 and Mythos 5.1 read at 0.025x ($0.20/MTok on the 5.2 pair, $0.25 on the 5.1
// pair), and Opus 5.5 ($0.20/MTok) and Sonnet 5.5 ($0.10/MTok, cut from $0.20 on
// 2026-10-07) read at 0.05x. Derive displays from cacheHitPer1M rather than
// multiplying input by 0.1 -- that shortcut is now wrong on six models.
export const CACHE_HIT_MULTIPLIER_DEFAULT = 0.1
export const CACHE_HIT_MULTIPLIER_FABLE_5_1 = 0.025
export const CACHE_HIT_MULTIPLIER_FABLE_5_2 = 0.025
export const CACHE_HIT_MULTIPLIER_OPUS_5_5 = 0.05
export const CACHE_HIT_MULTIPLIER_SONNET_5_5 = 0.05

/** Cache-read discount off base input, as a share (0.9 = 90% off). */
export function cacheDiscountShare(model: ModelPricing): number {
  return 1 - model.cacheHitPer1M / model.inputPer1M
}

export const MODELS: Record<ModelId, ModelPricing> = {
  'fable-5-2': {
    id: 'fable-5-2',
    name: 'Fable 5.2',
    // $8/$40 -- 20% below Fable 5.1's $10/$50 on every rate; exactly 2x Opus 5.5 ($4/$20).
    inputPer1M: 8,
    outputPer1M: 40,
    // 0.025x base input (8 * 0.025 = 0.20) -- the same $0.20 as Opus 5.5's 0.05x of $4.
    cacheHitPer1M: 0.2,
    // 5m write 1.25x (8 * 1.25 = 10), 1h write 2x (8 * 2 = 16).
    cacheWrite5mPer1M: 10,
    cacheWrite1hPer1M: 16,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: true,
    // 2x of its own base: $16/$80 (8 * 2, 40 * 2).
    fastModeMultiplier: 2,
    // Same tokenizer as Opus 4.7+: ~30% more tokens vs pre-4.7 models.
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    lifecycle: 'active',
    notes:
      "Anthropic's most capable widely released model (released 2026-11-09), for demanding reasoning and " +
      'long-horizon agentic work. $8/$40 -- 20% below Fable 5.1 on every rate and exactly 2x Opus 5.5 ' +
      '(Fable 5.1 was 2.5x); cache reads are $0.20/MTok (0.025x), the same as Opus 5.5. Anthropic still says ' +
      'start with Opus 5.5 and move up when evals at higher effort fall short. Fast Mode 2x ($16/$80, ' +
      'no beta header). Adaptive thinking always on (disabled/budget_tokens return 400); effort default is ' +
      'high on the API and medium in Claude Code. Forced tool_choice (any/tool) returns 400. Breaking changes ' +
      'vs Fable 5.1: the edited-history prefix check applies on every account, only Fable 5.2 and Mythos 5.2 ' +
      'read its thinking blocks, computer_20251124 returns 400 except on Bedrock, and an advisor tool needs a ' +
      'Fable 5.2 or Mythos 5.2 advisor. Batch $4/$20. Requires 30-day retention. 1M context at standard rates; ' +
      '128K max output. Min cacheable prompt 512 tokens. Earliest retirement: 2027-11-09.',
  },
  'fable-5-1': {
    id: 'fable-5-1',
    name: 'Fable 5.1',
    inputPer1M: 10,
    outputPer1M: 50,
    // 0.025x base input, same multiplier as Fable 5.2 (Opus 5.5 is 0.05x).
    cacheHitPer1M: 0.25,
    cacheWrite5mPer1M: 12.5,
    cacheWrite1hPer1M: 20,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: false,
    // Same tokenizer as Fable 5 / Opus 4.7+: ~30% more tokens vs pre-4.7 models.
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    lifecycle: 'legacy',
    notes:
      'Legacy Fable release (2026-09-01), superseded by Fable 5.2, which is 20% cheaper. Still served ' +
      '(not deprecated, earliest retirement 2027-09-01). Same $10/$50 as Fable 5, ' +
      'but cache reads are $0.25/MTok -- 0.025x base input, a quarter of Fable 5 ' +
      '(Fable 5.2 reads at $0.20). That makes a cache miss expensive relative to a hit, ' +
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
  'opus-5-5': {
    id: 'opus-5-5',
    name: 'Opus 5.5',
    // $4/$20 -- 20% below Opus 5's $5/$25 (Opus 4.5 made the earlier cut, $15/$75 to $5/$25).
    inputPer1M: 4,
    outputPer1M: 20,
    // 0.05x base input -- the second model family to break the 0.1x cache rule.
    cacheHitPer1M: 0.2,
    cacheWrite5mPer1M: 5,
    cacheWrite1hPer1M: 8,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: true,
    // 2x of its own base: $8/$40, which undercuts the $10/$50 Fast rate of Opus 5 and 4.8.
    fastModeMultiplier: 2,
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    lifecycle: 'active',
    notes:
      "Anthropic's recommended starting model for most workloads (released 2026-09-22). $4/$20 -- 20% " +
      'below Opus 5 -- with cache reads at $0.20/MTok, 0.05x base input (95% off, versus 90% on Opus 5). ' +
      'Adaptive thinking is ALWAYS ON: thinking {type:"disabled"} and budget_tokens both return 400, so ' +
      'code that disabled thinking on Opus 5 now pays for thinking tokens it did not before. ' +
      'Default effort drops to medium (Opus 5 defaulted to high), so a request that omits effort thinks ' +
      'less than it did. Forced tool_choice (any/tool) returns 400; sampling params and prefill 400; ' +
      'the computer_20251124 tool is rejected on the Claude API and Google Cloud (use ' +
      'computer_toolset_20260801). No Priority Tier. Fast Mode 2x ($8/$40), generally available since ' +
      '2026-10-15 (no beta header), also on Google Cloud (Anthropic managed) and Foundry on Azure. Batch $2/$10. ' +
      '1M context at standard rates; 128K max output (300K on Batch via beta). Min cacheable prompt 512. ' +
      'Refusal classifiers cover bio and reasoning_extraction as well as cyber. Knowledge cutoff Jun 2026. ' +
      'Earliest retirement: 2027-09-22. On the Claude API, Bedrock (anthropic.claude-opus-5-5), Google ' +
      'Cloud, Microsoft Foundry, and Claude Platform on AWS.',
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
    fastModeStatus: 'research preview',
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    lifecycle: 'legacy',
    notes:
      'Previous Opus-tier flagship (GA 2026-07-24), moved to legacy by the Opus 5.5 launch. ' +
      'Opus 5.5 costs 20% less ($4/$20) and reads cache at half the rate, so there is no cost reason ' +
      'to stay unless you need thinking disabled or forced tool_choice, both of which Opus 5.5 rejects. ' +
      'Same $5/$25 as Opus 4.8. ' +
      'Adaptive thinking is ON by default when you omit the thinking param -- max_tokens is a hard cap ' +
      'on thinking plus text, so budget it (64K+ if you run xhigh/max effort). ' +
      'thinking {type:"disabled"} is only legal at effort high or below; pairing it with xhigh/max returns a 400. ' +
      'Min cacheable prompt 512 tokens (half of Opus 4.8), so short system prompts now cache. ' +
      'Fast Mode in research preview at 2x ($10/$50). Batch $2.50/$12.50. 1M context at standard rates; ' +
      '128K max output (300K on Batch via the output-300k-2026-03-24 beta). ' +
      'Ships cybersecurity safety classifiers -- a cyber refusal can auto-fall-back to Opus 4.8 via the ' +
      'server-side fallbacks param. Knowledge cutoff May 2026. Earliest retirement: 2027-07-24. ' +
      'GA on Claude API, Claude Platform on AWS, Bedrock (anthropic.claude-opus-5), and Google Cloud.',
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
    fastModeStatus: 'research preview, removed 2026-11-30',
    tokenizerOverhead: 1.3,
    minCacheTokens: 1024,
    lifecycle: 'legacy',
    notes:
      'Legacy Opus-tier release (superseded by Opus 5, then Opus 5.5). Opus 5.5 costs 20% less ($4/$20), ' +
      'so there is no cost reason to stay -- migrate unless your prompts are tuned to this snapshot, ' +
      'or you need thinking fully off or forced tool_choice, both of which Opus 5.5 rejects. ' +
      'Keeps Priority Tier, which Opus 5.5 does not offer. ' +
      'Adaptive thinking, off by default; effort defaults to high. Fast Mode at 2x ($10/$50) is deprecated: ' +
      'removed 2026-11-30, after which speed "fast" returns an error. ' +
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
    tokenizerOverhead: 1.3,
    minCacheTokens: 2048,
    lifecycle: 'legacy',
    notes:
      'Legacy. New tokenizer (approximately 30% more tokens for the same text, per the Anthropic pricing page). ' +
      'Adaptive thinking only with xhigh effort level. ' +
      'Fast Mode has been removed: speed "fast" now returns an error here, with no fallback to standard. ' +
      'Min cacheable prompt 2,048 tokens. Earliest retirement: 2027-04-16. ' +
      'Migrate to Opus 5.5, which costs 20% less ($4/$20).',
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
      'Min cacheable prompt 4,096 tokens. Earliest retirement: 2027-02-05. Migrate to Opus 5.5.',
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
      'Earliest retirement: 2026-11-24. Migrate to Opus 5.5 unless you have a workload pinned to this snapshot.',
  },
  'sonnet-5-5': {
    id: 'sonnet-5-5',
    name: 'Sonnet 5.5',
    // Same $2/$10, cache writes and batch rates as Sonnet 5. The cache read was
    // cut to $0.10 (0.05x base input) on 2026-10-07, half Sonnet 5's $0.20.
    inputPer1M: 2,
    outputPer1M: 10,
    cacheHitPer1M: 0.1,
    cacheWrite5mPer1M: 2.5,
    cacheWrite1hPer1M: 4,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: false,
    // Same tokenizer as Sonnet 5, so the same text gives the same token count.
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    lifecycle: 'active',
    notes:
      'Current Sonnet-tier flagship (released 2026-09-28): best combination of speed and intelligence. ' +
      'Same $2/$10 and tokenizer as Sonnet 5, and cache reads cost half as much ($0.10, 0.05x, since ' +
      '2026-10-07), so migrating is a saving on any cached workload. Half the price of ' +
      'Opus 5.5 ($4/$20). Min cacheable prompt drops to 512 tokens (Sonnet 5: 1,024) and the tool-use system ' +
      'prompt to 286 tokens (Sonnet 5: 354). Adaptive thinking on by default, effort defaults to high and ' +
      'is recalibrated -- re-run your effort sweep. thinking {type:"disabled"} returns 400: the lowest ' +
      'setting is between_tools (no up-front thinking), at high effort or below. Forced tool_choice ' +
      '(any/tool), sampling params and computer_20251124 (Claude API, Google Cloud) return 400. ' +
      'Mid-conversation tool changes supported. No Fast Mode. Batch $1/$5. 1M context; 128K output. ' +
      'Earliest retirement: 2027-09-28.',
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
    lifecycle: 'legacy',
    notes:
      'Previous Sonnet-tier flagship (GA 2026-06-30), moved to legacy by the Sonnet 5.5 launch. ' +
      '$2/$10 per MTok is the permanent standard price -- Anthropic cancelled the increase to ' +
      '$3/$15 that was scheduled for 2026-09-01. Sonnet 5.5 costs the same and caches from 512 tokens. ' +
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
      'Min cacheable prompt 1,024 tokens. Earliest retirement: 2027-02-17. Migrate to Sonnet 5.5.',
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
    lifecycle: 'deprecated',
    notes:
      'Deprecated on 2026-09-30; retirement scheduled for 2026-11-30 on the Claude API. ' +
      'Extended thinking. 200K context. Min cacheable prompt 1,024 tokens. ' +
      "Anthropic's recommended replacement is Sonnet 5.5: a third cheaper ($2/$10) with a 1M window.",
  },
  'haiku-5-5': {
    id: 'haiku-5-5',
    name: 'Haiku 5.5',
    // The first tiered model: $0.10/$0.50 for prompts up to 100,000 tokens.
    inputPer1M: 0.1,
    outputPer1M: 0.5,
    cacheHitPer1M: 0.01,
    cacheWrite5mPer1M: 0.125,
    cacheWrite1hPer1M: 0.2,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: false,
    // Claude 4.7+ tokenizer: ~30% more tokens than Haiku 4.5 for the same text.
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    lifecycle: 'active',
    longPrompt: {
      threshold: 100_000,
      inputPer1M: 0.5,
      outputPer1M: 2.5,
      cacheHitPer1M: 0.05,
      cacheWrite5mPer1M: 0.625,
      cacheWrite1hPer1M: 1,
    },
    notes:
      'Current Haiku (released 2026-10-07), for high-volume, latency-sensitive work: classification, ' +
      'extraction, routing, subagents. Priced by prompt length: $0.10/$0.50 up to 100,000 prompt tokens, ' +
      '$0.50/$2.50 above -- the prompt counts cache reads and writes, and a request over the line pays the ' +
      'higher rate on all of it. 40x below Opus 5.5 and 20x below Sonnet 5.5 per token in the low tier. ' +
      '1M context, 128K output, min cacheable prompt 512 (Haiku 4.5: 4,096). Adaptive thinking on by ' +
      'default, effort defaults to medium. budget_tokens, sampling params, prefill and computer_20250124 ' +
      '(Claude API, Google Cloud) return 400. No Fast Mode. Earliest retirement: 2027-10-07.',
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
    lifecycle: 'legacy',
    notes:
      'Legacy since the Haiku 5.5 launch (not deprecated). Extended thinking. 200K context. ' +
      'Min cacheable prompt 4,096 tokens, so short system prompts get no cache discount here. ' +
      'Haiku 5.5 is 10x cheaper per token up to 100K prompt tokens. Active; no retirement announced ' +
      '(its earliest date, 2026-10-15, has passed).',
  },
  'mythos-5-2': {
    id: 'mythos-5-2',
    name: 'Mythos 5.2',
    // Price alias of Fable 5.2: same rates, including the 0.025x cache read (8 * 0.025 = 0.20).
    inputPer1M: 8,
    outputPer1M: 40,
    cacheHitPer1M: 0.2,
    cacheWrite5mPer1M: 10,
    cacheWrite1hPer1M: 16,
    contextWindow: '1M',
    maxOutput: '128K',
    fastModeCapable: true,
    fastModeMultiplier: 2,
    tokenizerOverhead: 1.3,
    minCacheTokens: 512,
    inviteOnly: true,
    lifecycle: 'active',
    notes:
      'Fable 5.2 for verified organizations: same capabilities and prices, including Fast Mode ' +
      '($16/$80) and the $0.20/MTok (0.025x) cache-read rate. Available only through ' +
      "Anthropic's verification programs (e.g. the Cyber Verification Program); on the Claude API, " +
      'Bedrock (anthropic.claude-mythos-5-2), Google Cloud and Foundry, not Claude Platform on AWS. ' +
      'Min cacheable prompt 512 tokens. Successor to Mythos 5.1.',
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
    lifecycle: 'legacy',
    notes:
      'Superseded by Mythos 5.2 ($8/$40). ' +
      'Fable 5.1 for verified organizations: same capabilities, limits, and pricing, ' +
      'including the $0.25/MTok (0.025x) cache-read rate. Unlike Mythos 5 it runs safeguards ' +
      'that depend on the access program, so stop_reason "refusal" can occur. ' +
      "Available only through Anthropic's verification programs (e.g. the Cyber Verification " +
      'Program); not offered on Claude Platform on AWS. ' +
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
      "Available only through Anthropic's verification programs, such as the Cyber Verification Program. " +
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
    lifecycle: 'deprecated',
    notes:
      'Superseded by Mythos 5 and deprecated: still functional, no retirement ' +
      'date published. The invitation-only ' +
      'defensive-cybersecurity research preview under Project Glasswing.',
  },
}

// Default Fast Mode premium for models without an explicit fastModeMultiplier.
// Prefer ModelPricing.fastModeMultiplier. Only Fable 5.2, Mythos 5.2, Opus 5.5, Opus 5 and
// Opus 4.8 support Fast Mode, and all are 2x of their own base rate ($16/$80 on the 5.2 pair,
// $8/$40 on Opus 5.5, $10/$50 on the other two), so 2 is the only sensible default.
export const FAST_MODE_MULTIPLIER = 2
export const FAST_MODE_OTPS_GAIN = 2.5 // up to 2.5x output tokens per second
export const BATCH_DISCOUNT = 0.5
export const REGIONAL_ENDPOINT_PREMIUM = 1.1
export const DATA_RESIDENCY_PREMIUM = 1.1

// Subscription pricing -- monthly vs annual (https://claude.com/pricing, read 2026-11-01).
// Pro annual = $200 up front, billed yearly (effective ~$16.67/mo, ~17% off).
// Max ($100, 5x Pro) and Ultra ($200, formerly Max 20x) are monthly only.
export const SUBSCRIPTION_PRICING = {
  proMonthly: 20,
  proAnnualUpfront: 200,
  proAnnualEffectiveMonthly: 200 / 12,
  max: 100,
  ultra: 200,
}

export const TOKEN_ESTIMATES = {
  // Measured on this repo's 15 CLAUDE.md files (the templates plus the root file): 20,161 cl100k
  // tokens over 2,048 lines, 9.8 per line counting blank lines. The 4.7+ tokenizer makes about 30% more.
  tokensPerClaudeMdLine: 10,
  // Modelling assumption for the built-in prompt and tools (everything except CLAUDE.md lines and
  // MCP servers). The calculator's "Base prompt tokens" field starts here and takes your own figure.
  systemPromptTokens: 3500,
  // Worst case: full tool schemas loaded up front, which only happens when MCP tool search is
  // off: ENABLE_TOOL_SEARCH=false, CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1, a HIPAA configuration,
  // a gateway that rejects it, or a platform that does (older models on Google Cloud, Microsoft
  // Foundry on Azure). Behind a custom ANTHROPIC_BASE_URL it is on by default since v2.1.304
  // (guides/07-mcp-agent-costs.md). With tool search on -- the default -- a server adds only its
  // tool names and instructions, and Anthropic publishes no per-server figure for that case.
  tokensPerMcpServer: 1500,
  tokensPerFileRead: 2000,
  outputTokensPerTurn: 500,
  historyGrowthPerTurn: 1500,
  // The calculator's brevity what-if loads skills/cost-mode/SKILL.md (and its identical copy in
  // plugins/cost-mode/skills/cost-mode/, both 11,406 bytes). Measured 2026-11-03 with
  // tools/token-estimator: 2,901 cl100k tokens, x1.3 for the 4.7+ tokenizer = 3,771.
  // Re-measure after editing SKILL.md.
  costModeRuleTokens: 3771,
}

/** A per-1M rate for display: "$2" when whole, "$0.10" otherwise. */
export function formatRate(rate: number): string {
  return Number.isInteger(rate) ? `$${rate}` : `$${rate.toFixed(2)}`
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
