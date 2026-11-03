import {
  type CacheTtl,
  type ModelId,
  type ModelPricing,
  CACHE_TTL_MINUTES,
  MODELS,
  FAST_MODE_MULTIPLIER,
  TOKEN_ESTIMATES,
  ratesForPrompt,
  turnInputCost,
  formatRate,
} from './pricing'

/** Fast Mode premium for a model -- per-model rate, falling back to the global default. */
function fastModeMultiplier(model: ModelPricing): number {
  return model.fastModeMultiplier ?? FAST_MODE_MULTIPLIER
}

export interface CalculatorInputs {
  model: ModelId
  turnsPerSession: number
  claudeMdLines: number
  sessionsPerDay: number
  workingDaysPerMonth: number
  mcpServers: number
  fileReadsPerTurn: number
  fastMode: boolean
  /** Everything in the prompt except CLAUDE.md lines and MCP servers: built-in prompt, tools, harness. */
  basePromptTokens: number
  /** Idle breaks per session, spread evenly over the gaps between turns. */
  breaksPerSession: number
  /** Length of each break. Only a break longer than the cache TTL re-writes the prompt. */
  breakMinutes: number
  cacheTtl: CacheTtl
  /** /compact runs after this 1-based turn; 0, or a turn at or past the last, means never. */
  compactAtTurn: number
  /** History kept after /compact: the summary, written as output and cached by the next turn. */
  postCompactTokens: number
  /** What-if only: percent cut on file-read and tool-result tokens. */
  toolOutputCutPercent: number
  /** What-if only: brevity rule tokens loaded into the cached prefix. */
  ruleTokens: number
  /** What-if only: percent cut the rules make on prose output. */
  outputCutPercent: number
  /** What-if only: percent of output that is prose the rules can shorten. */
  proseSharePercent: number
}

/**
 * The calculator's starting point. The session events and what-ifs start neutral (no breaks, the
 * 5-minute TTL, no compaction, the 3,500-token base prompt), so the bill is the one the calculator
 * printed before they existed.
 */
export const DEFAULT_INPUTS: CalculatorInputs = {
  model: 'opus-5-5',
  turnsPerSession: 30,
  claudeMdLines: 100,
  sessionsPerDay: 3,
  workingDaysPerMonth: 22,
  mcpServers: 2,
  fileReadsPerTurn: 1,
  fastMode: false,
  basePromptTokens: TOKEN_ESTIMATES.systemPromptTokens,
  breaksPerSession: 0,
  breakMinutes: 15,
  cacheTtl: '5m',
  compactAtTurn: 0,
  postCompactTokens: 5000,
  toolOutputCutPercent: 0,
  ruleTokens: TOKEN_ESTIMATES.costModeRuleTokens,
  outputCutPercent: 0,
  proseSharePercent: 100,
}

export interface CostBreakdown {
  basePrompt: number
  claudeMd: number
  mcp: number
  fileReads: number
  history: number
  output: number
}

/** One turn of a session, split into what it paid for. */
export interface TurnLayer {
  /** Prompt read back from the cache: the previous request, or only the stable prefix after /compact. */
  cacheRead: number
  /** Prompt written to the cache at the TTL's write rate (full input under the model's cache floor). */
  cacheWrite: number
  output: number
  promptTokens: number
  /** A break past the TTL came before this turn, so its prompt (or the /compact request) was re-written whole. */
  cold: boolean
  /** /compact ran before this turn; its summary request is billed here. */
  compacted: boolean
}

/** One break past the TTL: the prompt it re-wrote, what that write cost and what reading it warm would have. */
export interface Rewrite {
  turn: number
  tokens: number
  writeDollars: number
  readDollars: number
}

/** The /compact summarization request, billed on the turn after it. */
export interface CompactionSummary {
  /** 0-based turn it is billed on (the first turn after /compact). */
  turn: number
  /** The prompt it reads: from cache, or re-written when a break past the TTL came first. */
  readTokens: number
  cold: boolean
  inputDollars: number
  outputDollars: number
}

/** Session events and what-ifs, computed from the inputs. Monthly figures use the same session count. */
export interface SessionEvents {
  /** Breaks the session has, at most one per gap between turns. */
  breaks: number
  ttlMinutes: number
  /** The same sessions on the other TTL (5-minute and 1-hour swapped), per month. */
  otherTtlMonthly: number
  /** What the breaks add per month against the same sessions with none (0 when none outlasts the TTL). */
  breakCostMonthly: number
  rewrites: Rewrite[]
  /** A 1-hour-TTL break longer than 60 minutes at 200K+ tokens, which idle compaction would compact first. */
  idleCompactionApplies: boolean
  compaction: (CompactionSummary & { savingPerSession: number; paybackTurn: number | null }) | null
  toolOutputSavingMonthly: number
  brevity: { loadMonthly: number; breakEvenCutPercent: number | null; netSavingMonthly: number }
}

export interface CalculatorResult {
  monthlyCost: number
  optimizedCost: number
  savings: number
  savingsPercent: number
  breakdown: CostBreakdown
  optimizedBreakdown: CostBreakdown
  recommendations: string[]
  /** Per-turn cost of one session at the current settings (session-level, not monthly). */
  perTurnCurrent: number[]
  /** The same turns split into cache read, cache write and output, as billed. */
  perTurnLayers: TurnLayer[]
  /** 0-based turns that follow a break past the TTL (their prompt, or the /compact request, re-written whole). */
  coldTurns: number[]
  sessionEvents: SessionEvents
}

/** The inputs one session's bill depends on; the model and the monthly counts are passed separately. */
type SessionInputs = Omit<CalculatorInputs, 'model' | 'sessionsPerDay' | 'workingDaysPerMonth'>

/** What-if knobs applied on top of the inputs. NO_WHAT_IF leaves the bill unchanged. */
interface WhatIf {
  extraPrefixTokens: number
  fileTokenScale: number
  outputScale: number
}

const NO_WHAT_IF: WhatIf = { extraPrefixTokens: 0, fileTokenScale: 1, outputScale: 1 }

interface SessionCost {
  total: number
  breakdown: CostBreakdown
  layers: TurnLayer[]
  perTurn: number[]
  /** Output of the turns themselves, without the /compact summary: the part a brevity cut shrinks. */
  turnOutput: number
  rewrites: Rewrite[]
  summary: CompactionSummary | null
}

type PromptPart = Exclude<keyof CostBreakdown, 'output'>

const HAIKUS: ReadonlySet<ModelId> = new Set<ModelId>(['haiku-5-5', 'haiku'])

/**
 * Idle compaction compacts a 200K+ token conversation before its one-hour cache expires
 * (guides/08-prompt-caching.md, "Idle Compaction", read 2026-11-01).
 */
const IDLE_COMPACT_MIN_TOKENS = 200_000

const TTL_NAMES: Record<CacheTtl, string> = { '5m': '5-minute', '1h': '1-hour' }

const emptyBreakdown = (): CostBreakdown => ({ basePrompt: 0, claudeMd: 0, mcp: 0, fileReads: 0, history: 0, output: 0 })

/** A percent input as a share, clamped to 0-100%. */
const shareOf = (percent: number) => Math.min(Math.max(percent, 0), 100) / 100

/** Tokens every request carries before file reads and history: base prompt, CLAUDE.md lines, MCP servers. */
export function stablePromptTokens(inputs: Pick<CalculatorInputs, 'basePromptTokens' | 'claudeMdLines' | 'mcpServers'>): number {
  const t = TOKEN_ESTIMATES
  return inputs.basePromptTokens + inputs.claudeMdLines * t.tokensPerClaudeMdLine + inputs.mcpServers * t.tokensPerMcpServer
}

/** File-read tokens each turn carries. */
export function fileReadTokens(inputs: Pick<CalculatorInputs, 'fileReadsPerTurn'>): number {
  return inputs.fileReadsPerTurn * TOKEN_ESTIMATES.tokensPerFileRead
}

/** 0-based turns that follow a break: the breaks spread evenly over the gaps between turns. */
function breakTurns(turns: number, breaks: number): Set<number> {
  const count = Math.min(Math.max(Math.floor(breaks), 0), Math.max(turns - 1, 0))
  return new Set(Array.from({ length: count }, (_, k) => Math.round(((k + 1) * turns) / (count + 1))))
}

/** 0-based turn that /compact runs before, or null when it never runs. */
export function compactionTurn(inputs: Pick<CalculatorInputs, 'compactAtTurn' | 'turnsPerSession'>): number | null {
  const after = Math.floor(inputs.compactAtTurn)
  return after >= 1 && after < inputs.turnsPerSession ? after : null
}

/** One request's input: a cache read and a cache write at the TTL's rates, times the Fast Mode multiplier. */
function request(pricing: ModelPricing, prompt: number, previousPrompt: number, ttl: CacheTtl, multiplier: number) {
  const { readDollars, writeDollars } = turnInputCost(pricing, prompt, previousPrompt, ttl)
  return { read: readDollars * multiplier, write: writeDollars * multiplier }
}

/** What a break past the TTL cost one request: the prompt it re-wrote, against reading it warm. */
function rewriteOf(
  pricing: ModelPricing,
  turn: number,
  prompt: number,
  previousPrompt: number,
  ttl: CacheTtl,
  multiplier: number,
  paidWrite: number,
): Rewrite {
  const warm = request(pricing, prompt, previousPrompt, ttl, multiplier)
  return { turn, tokens: Math.min(previousPrompt, prompt), writeDollars: paidWrite - warm.write, readDollars: warm.read }
}

/**
 * The /compact summarization request: it reads the last request from cache and writes the kept
 * history as output. Compaction requests use the 5-minute TTL (guides/08-prompt-caching.md, "How
 * Claude Code Picks the Cache TTL"), so after a break past the TTL it re-writes that prompt at the
 * 5-minute rate.
 */
function summaryRequest(pricing: ModelPricing, prompt: number, cold: boolean, keptTokens: number, multiplier: number) {
  const input = request(pricing, prompt, cold ? 0 : prompt, '5m', multiplier)
  const output = (keptTokens / 1_000_000) * ratesForPrompt(pricing, prompt).outputPer1M * multiplier
  return { ...input, output }
}

/** Shares one request's input cost over the prompt categories by their token share of the prompt. */
function addInputShares(breakdown: CostBreakdown, input: number, parts: Record<PromptPart, number>, prompt: number) {
  if (prompt <= 0) return
  for (const key of Object.keys(parts) as PromptPart[]) breakdown[key] += (input * parts[key]) / prompt
}

function computeSessionCost(inputs: SessionInputs, model: ModelId, whatIf: WhatIf = NO_WHAT_IF): SessionCost {
  const pricing = MODELS[model]
  const t = TOKEN_ESTIMATES
  const base = inputs.basePromptTokens + whatIf.extraPrefixTokens
  const claudeMd = inputs.claudeMdLines * t.tokensPerClaudeMdLine
  const mcp = inputs.mcpServers * t.tokensPerMcpServer
  const fileReads = fileReadTokens(inputs) * whatIf.fileTokenScale
  const stable = base + claudeMd + mcp

  // Each turn is billed the way Claude Code caches a conversation (turnInputCost): the previous
  // request is a cache read and only the new exchange is written. Costs accumulate per turn
  // because a tiered model (Haiku 5.5) also prices each request by its own prompt length.
  const multiplier = inputs.fastMode && pricing.fastModeCapable ? fastModeMultiplier(pricing) : 1
  const breaks = breakTurns(inputs.turnsPerSession, inputs.breaksPerSession)
  const breaksExpire = inputs.breakMinutes > CACHE_TTL_MINUTES[inputs.cacheTtl]
  const compactAt = compactionTurn(inputs)
  const cost: SessionCost = {
    total: 0,
    breakdown: emptyBreakdown(),
    layers: [],
    perTurn: [],
    turnOutput: 0,
    rewrites: [],
    summary: null,
  }
  let previousPrompt = 0
  let history = 0

  for (let turn = 0; turn < inputs.turnsPerSession; turn++) {
    const cold = breaksExpire && breaks.has(turn)
    const layer: TurnLayer = { cacheRead: 0, cacheWrite: 0, output: 0, promptTokens: 0, cold, compacted: turn === compactAt }

    if (layer.compacted) {
      const s = summaryRequest(pricing, previousPrompt, cold, inputs.postCompactTokens, multiplier)
      if (cold) cost.rewrites.push(rewriteOf(pricing, turn, previousPrompt, previousPrompt, '5m', multiplier, s.write))
      cost.summary = { turn, readTokens: previousPrompt, cold, inputDollars: s.read + s.write, outputDollars: s.output }
      layer.cacheRead += s.read
      layer.cacheWrite += s.write
      layer.output += s.output
      // The summary request manages history, so its input is counted as History.
      cost.breakdown.history += s.read + s.write
      cost.breakdown.output += s.output
      // The summary replaces the history; only the stable prefix is still cached for this turn.
      history = inputs.postCompactTokens
      previousPrompt = stable
    }

    const prompt = stable + fileReads + history
    const expired = cold && !layer.compacted
    const own = request(pricing, prompt, expired ? 0 : previousPrompt, inputs.cacheTtl, multiplier)
    if (expired) cost.rewrites.push(rewriteOf(pricing, turn, prompt, previousPrompt, inputs.cacheTtl, multiplier, own.write))
    const output = (t.outputTokensPerTurn * whatIf.outputScale / 1_000_000) * ratesForPrompt(pricing, prompt).outputPer1M * multiplier
    addInputShares(cost.breakdown, own.read + own.write, { basePrompt: base, claudeMd, mcp, fileReads, history }, prompt)
    cost.breakdown.output += output
    cost.turnOutput += output

    layer.cacheRead += own.read
    layer.cacheWrite += own.write
    layer.output += output
    layer.promptTokens = prompt
    cost.layers.push(layer)
    cost.perTurn.push(layer.cacheRead + layer.cacheWrite + layer.output)
    previousPrompt = prompt
    history += t.historyGrowthPerTurn
  }

  cost.total = cost.perTurn.reduce((sum, c) => sum + c, 0)
  return cost
}

/** Session cost at the current settings if run on `model` (Fast Mode only applies when the model supports it). */
export function sessionCostForModel(inputs: CalculatorInputs, model: ModelId): number {
  return computeSessionCost(inputs, model).total
}

function sumBreakdowns(parts: readonly CostBreakdown[], by: number): CostBreakdown {
  const out = emptyBreakdown()
  for (const part of parts) {
    for (const key of Object.keys(out) as (keyof CostBreakdown)[]) out[key] += part[key] * by
  }
  return out
}

export function calculate(inputs: CalculatorInputs): CalculatorResult {
  const sessionsPerMonth = inputs.sessionsPerDay * inputs.workingDaysPerMonth
  const current = computeSessionCost(inputs, inputs.model)

  // If Opus or Sonnet, 30% of work delegated to Haiku 5.5
  const haikuFraction = HAIKUS.has(inputs.model) ? 0 : 0.3
  const primaryFraction = 1 - haikuFraction
  const optimizedBase: CalculatorInputs = {
    ...inputs,
    claudeMdLines: Math.min(inputs.claudeMdLines, 80),
    fileReadsPerTurn: Math.round(inputs.fileReadsPerTurn * 0.7),
    fastMode: false,
  }

  // The primary run keeps the session's breaks and compaction, scaled to its share of the turns.
  const optimizedPrimary = computeSessionCost(
    {
      ...optimizedBase,
      turnsPerSession: Math.round(inputs.turnsPerSession * primaryFraction),
      breaksPerSession: Math.round(inputs.breaksPerSession * primaryFraction),
      compactAtTurn: Math.round(inputs.compactAtTurn * primaryFraction),
    },
    inputs.model,
  )

  // The Haiku share runs as subagents: the 5-minute TTL (unless subagentPromptCacheTtl is set),
  // no idle breaks of their own and no compaction.
  const optimizedRuns = [optimizedPrimary]
  if (haikuFraction > 0) {
    optimizedRuns.push(
      computeSessionCost(
        {
          ...optimizedBase,
          turnsPerSession: Math.round(inputs.turnsPerSession * haikuFraction),
          breaksPerSession: 0,
          cacheTtl: '5m',
          compactAtTurn: 0,
        },
        'haiku-5-5',
      ),
    )
  }

  const monthlyCost = current.total * sessionsPerMonth
  const optimizedCost = optimizedRuns.reduce((sum, run) => sum + run.total, 0) * sessionsPerMonth
  const savings = monthlyCost - optimizedCost
  const savingsPercent = monthlyCost > 0 ? (savings / monthlyCost) * 100 : 0

  const monthlyBreakdown = sumBreakdowns([current.breakdown], sessionsPerMonth)
  const events = sessionEvents(inputs, current, sessionsPerMonth)
  const recommendations = generateRecommendations(inputs, monthlyBreakdown, monthlyCost, events, current.layers)

  return {
    monthlyCost,
    optimizedCost,
    savings,
    savingsPercent,
    breakdown: monthlyBreakdown,
    optimizedBreakdown: sumBreakdowns(
      optimizedRuns.map((run) => run.breakdown),
      sessionsPerMonth,
    ),
    recommendations,
    perTurnCurrent: current.perTurn,
    perTurnLayers: current.layers,
    coldTurns: current.layers.flatMap((layer, turn) => (layer.cold ? [turn] : [])),
    sessionEvents: events,
  }
}

/** Compaction against the same session never compacted, and the turn by which it has paid for itself. */
function compactionEvent(inputs: CalculatorInputs, current: SessionCost): SessionEvents['compaction'] {
  if (!current.summary) return null
  const never = computeSessionCost({ ...inputs, compactAtTurn: 0 }, inputs.model)
  let compacted = 0
  let uncompacted = 0
  let paybackTurn: number | null = null
  for (let turn = 0; turn < current.perTurn.length && paybackTurn === null; turn++) {
    compacted += current.perTurn[turn]
    uncompacted += never.perTurn[turn]
    if (turn >= current.summary.turn && compacted <= uncompacted) paybackTurn = turn
  }
  return { ...current.summary, savingPerSession: never.total - current.total, paybackTurn }
}

/** Re-runs the session with one change at a time: the other TTL, no breaks, and each what-if lever. */
function sessionEvents(inputs: CalculatorInputs, current: SessionCost, sessionsPerMonth: number): SessionEvents {
  const run = (changes: Partial<SessionInputs>, whatIf: WhatIf = NO_WHAT_IF) =>
    computeSessionCost({ ...inputs, ...changes }, inputs.model, whatIf).total
  const monthly = (session: number) => session * sessionsPerMonth

  const prose = shareOf(inputs.proseSharePercent)
  const rules: WhatIf = { ...NO_WHAT_IF, extraPrefixTokens: inputs.ruleTokens }
  const withRules = computeSessionCost(inputs, inputs.model, rules)
  const load = withRules.total - current.total
  const shrinkable = withRules.turnOutput * prose
  const withRulesAndCut = run({}, { ...rules, outputScale: 1 - shareOf(inputs.outputCutPercent) * prose })

  return {
    breaks: breakTurns(inputs.turnsPerSession, inputs.breaksPerSession).size,
    ttlMinutes: CACHE_TTL_MINUTES[inputs.cacheTtl],
    otherTtlMonthly: monthly(run({ cacheTtl: inputs.cacheTtl === '5m' ? '1h' : '5m' })),
    breakCostMonthly: monthly(current.total - run({ breaksPerSession: 0 })),
    rewrites: current.rewrites,
    idleCompactionApplies:
      inputs.cacheTtl === '1h' &&
      inputs.breakMinutes > CACHE_TTL_MINUTES['1h'] &&
      current.rewrites.some((r) => r.tokens >= IDLE_COMPACT_MIN_TOKENS),
    compaction: compactionEvent(inputs, current),
    toolOutputSavingMonthly: monthly(
      current.total - run({}, { ...NO_WHAT_IF, fileTokenScale: 1 - shareOf(inputs.toolOutputCutPercent) }),
    ),
    brevity: {
      loadMonthly: monthly(load),
      // The cut c that pays for the rules: c x prose x output = load.
      breakEvenCutPercent: shrinkable > 0 ? (load / shrinkable) * 100 : null,
      netSavingMonthly: monthly(current.total - withRulesAndCut),
    },
  }
}

interface Rec {
  text: string
  impact: number
}

function generateRecommendations(
  inputs: CalculatorInputs,
  breakdown: CostBreakdown,
  monthlyCost: number,
  events: SessionEvents,
  layers: readonly TurnLayer[],
): string[] {
  const recs: Rec[] = []

  if (inputs.claudeMdLines > 80) {
    const savingsPct = ((inputs.claudeMdLines - 80) / inputs.claudeMdLines) * (breakdown.claudeMd / Object.values(breakdown).reduce((a, b) => a + b, 0)) * 100
    recs.push({
      text: `Trim CLAUDE.md from ${inputs.claudeMdLines} to 80 lines -- saves ~${savingsPct < 1 ? savingsPct.toFixed(1) : Math.round(savingsPct)}% of session cost (it is a cache read on every turn after the first)`,
      impact: savingsPct,
    })
  }

  if (inputs.fastMode) {
    const model = MODELS[inputs.model]
    const mult = model.fastModeMultiplier ?? FAST_MODE_MULTIPLIER
    const savePct = Math.round(((mult - 1) / mult) * 100)
    const status = model.fastModeStatus ? ' (' + model.name + ' Fast Mode: ' + model.fastModeStatus + ')' : ''
    recs.push({
      text: `Disable Fast Mode -- saves ${savePct}% by removing the ${mult}x multiplier${status}`,
      impact: savePct,
    })
  }

  if (!HAIKUS.has(inputs.model)) {
    recs.push({
      text: `Delegate simple tasks (tests, docs, formatting) to Haiku 5.5 subagents -- $0.10/$0.50 per 1M while each prompt stays under 100K tokens, 20x below Sonnet 5.5`,
      impact: 30,
    })
  }

  if (inputs.fileReadsPerTurn > 1) {
    recs.push({
      text: `Add permissions.deny Read(...) rules for build output, lock files and vendored code so Claude's file tools skip them (${inputs.fileReadsPerTurn} reads per turn now). Note: Claude Code does not read a .claudeignore file`,
      impact: 10,
    })
  }

  if (inputs.turnsPerSession > 20) {
    recs.push({
      text: `Use Plan Mode to reduce back-and-forth -- ${inputs.turnsPerSession} turns/session causes high history costs`,
      impact: 20,
    })
  }

  if (inputs.mcpServers > 3) {
    recs.push({
      text: `Disable unused MCP servers with /mcp (${inputs.mcpServers} configured). With tool search on, the default, each adds its tool names and instructions; full schemas load only when tool search is off. CLI tools like gh add nothing`,
      impact: 8,
    })
  }

  recs.push(...sessionEventRecommendations(inputs, monthlyCost, events))
  recs.push(...modelRecommendations(inputs))
  const tierWarning = promptTierRecommendation(inputs, layers)
  if (tierWarning) recs.push(tierWarning)

  recs.sort((a, b) => b.impact - a.impact)
  return recs.slice(0, 3).map((r) => r.text)
}

const COMPUTED = 'Computed from your inputs, not a measurement'

/** "12" or "0.4": a share of the estimate, with a decimal only below 1%. */
const percentText = (value: number) => (value < 1 ? value.toFixed(1) : String(Math.round(value)))

/** Cache TTL and idle-break advice, each ranked by the saving computed for these inputs. */
function sessionEventRecommendations(inputs: CalculatorInputs, monthlyCost: number, events: SessionEvents): Rec[] {
  const recs: Rec[] = []
  const shareOfBill = (dollars: number) => (monthlyCost > 0 ? (dollars / monthlyCost) * 100 : 0)
  const ttlSaving = monthlyCost - events.otherTtlMonthly
  const ttlPct = shareOfBill(ttlSaving)

  if (ttlSaving > 0 && inputs.cacheTtl === '5m') {
    recs.push({
      text: `Set promptCacheTtl to 1h -- at ${events.breaks} breaks of ${inputs.breakMinutes} minutes a session it saves $${ttlSaving.toFixed(2)}/month (${percentText(ttlPct)}% of this estimate), even at the 2x write. ${COMPUTED}`,
      impact: ttlPct,
    })
  } else if (ttlSaving > 0) {
    recs.push({
      text: `Use the 5-minute cache TTL (promptCacheTtl 5m) -- saves $${ttlSaving.toFixed(2)}/month (${percentText(ttlPct)}% of this estimate): at these breaks the 2x 1-hour write costs more than the re-writes it avoids. ${COMPUTED}`,
      impact: ttlPct,
    })
  }

  // When the 1-hour TTL already removes the re-writes, that is the advice; otherwise compact first.
  if (events.breakCostMonthly > 0 && !(inputs.cacheTtl === '5m' && ttlSaving > 0)) {
    const tokens = events.rewrites.reduce((sum, r) => sum + r.tokens, 0) / Math.max(events.rewrites.length, 1)
    const pct = shareOfBill(events.breakCostMonthly)
    recs.push({
      text: `Run /compact before a break longer than the ${TTL_NAMES[inputs.cacheTtl]} TTL -- each of your ${events.rewrites.length} breaks re-writes about ${Math.round(tokens).toLocaleString('en-US')} tokens, $${events.breakCostMonthly.toFixed(2)}/month in all (${percentText(pct)}% of this estimate). ${COMPUTED}`,
      impact: pct,
    })
  }
  return recs
}

const pctBelow = (cheaper: number, dearer: number) => Math.round((1 - cheaper / dearer) * 100)

/** Recommendations that depend on which model is selected. */
function modelRecommendations(inputs: CalculatorInputs): { text: string; impact: number }[] {
  const recs: { text: string; impact: number }[] = []

  // Ratios are computed from MODELS, never hardcoded: the Opus flagship price
  // moved on 2026-09-22, and every literal "60%" in this file went stale with it.
  const model = MODELS[inputs.model]
  const opusFlagship = MODELS['opus-5-5']
  const sonnetFlagship = MODELS['sonnet-5-5']

  const isFableTier =
    inputs.model === 'fable-5-1' ||
    inputs.model === 'fable-5' ||
    inputs.model === 'mythos-5-1' ||
    inputs.model === 'mythos-5'
  if (isFableTier) {
    const ratio = (model.inputPer1M / opusFlagship.inputPer1M).toFixed(1).replace(/\.0$/, '')
    recs.push({
      text: `Fable-tier costs ${ratio}x Opus 5.5 ($${model.inputPer1M}/$${model.outputPer1M} vs $${opusFlagship.inputPer1M}/$${opusFlagship.outputPer1M}). Reserve it for the hardest reasoning and route routine work to Opus 5.5 or Sonnet 5.5 -- saves ${pctBelow(opusFlagship.inputPer1M, model.inputPer1M)}%+ on those turns`,
      impact: 50,
    })
  }

  // Fable 5 -> 5.1 is the same posted price with a 4x cheaper cache read, so on
  // any cached workload it is a strict win with no quality tradeoff.
  if (inputs.model === 'fable-5' || inputs.model === 'mythos-5') {
    recs.push({
      text: 'Migrate to Fable 5.1 -- same $10/$50, but cache reads drop from $1.00 to $0.25 per 1M (0.025x vs 0.1x). Free savings on every cached turn',
      impact: 45,
    })
  }

  const isOpusTier =
    inputs.model === 'opus-5-5' ||
    inputs.model === 'opus-5' ||
    inputs.model === 'opus-4-8' ||
    inputs.model === 'opus-4-7' ||
    inputs.model === 'opus-4-6'
  if (isOpusTier && !inputs.fastMode) {
    recs.push({
      text: `Consider Sonnet 5.5 for routine development -- ${pctBelow(sonnetFlagship.inputPer1M, model.inputPer1M)}% cheaper ($${sonnetFlagship.inputPer1M}/$${sonnetFlagship.outputPer1M} vs $${model.inputPer1M}/$${model.outputPer1M}) with similar quality for most tasks`,
      impact: pctBelow(sonnetFlagship.inputPer1M, model.inputPer1M),
    })
  }

  // Every legacy Opus snapshot is on $5/$25; Opus 5.5 is $4/$20 with a 0.05x cache
  // read, so upgrading is a price cut on both input and every cached turn.
  const legacyOpus =
    inputs.model === 'opus-5' ||
    inputs.model === 'opus-4-8' ||
    inputs.model === 'opus-4-7' ||
    inputs.model === 'opus-4-6'
  if (legacyOpus) {
    const cacheFloorNote =
      model.minCacheTokens > opusFlagship.minCacheTokens
        ? `, and its minimum cacheable prompt is ${opusFlagship.minCacheTokens} tokens instead of ${model.minCacheTokens.toLocaleString()}`
        : ''
    recs.push({
      text: `Migrate to Opus 5.5 -- ${pctBelow(opusFlagship.inputPer1M, model.inputPer1M)}% cheaper ($${opusFlagship.inputPer1M}/$${opusFlagship.outputPer1M} vs $${model.inputPer1M}/$${model.outputPer1M}), cache reads drop from $${model.cacheHitPer1M.toFixed(2)} to $${opusFlagship.cacheHitPer1M.toFixed(2)} per 1M${cacheFloorNote}. Check first: thinking cannot be disabled and forced tool_choice returns 400`,
      impact: 30,
    })
  }

  if (inputs.model === 'opus-5') {
    recs.push({
      text: 'On Opus 5 thinking is ON by default. If a task does not need it, send thinking {type:"disabled"} at effort high or below -- reasoning tokens bill as output at $25/1M',
      impact: 15,
    })
  }

  if (inputs.model === 'opus-5-5') {
    recs.push({
      text: `On Opus 5.5 thinking cannot be turned off -- effort is the only dial. It defaults to medium; set effort low for routine turns, since reasoning tokens bill as output at $${model.outputPer1M}/1M`,
      impact: 15,
    })
  }

  if (model.minCacheTokens >= 4096) {
    recs.push({
      text: `${model.name} needs ${model.minCacheTokens.toLocaleString()}+ tokens before a prompt caches at all. Below that you pay full input price every turn -- Opus 5.5, Sonnet 5.5, Haiku 5.5 and Fable 5.1 cache from 512 tokens`,
      impact: 12,
    })
  }

  const sonnetMigration = legacySonnetRecommendation(inputs.model)
  if (sonnetMigration) recs.push(sonnetMigration)
  if (inputs.model === 'haiku') recs.push(haikuMigrationRecommendation())

  return recs
}

function haikuMigrationRecommendation(): { text: string; impact: number } {
  const legacy = MODELS.haiku
  const target = MODELS['haiku-5-5']
  return {
    text: `Migrate to Haiku 5.5 -- ${formatRate(target.inputPer1M)}/${formatRate(target.outputPer1M)} per 1M vs ${formatRate(legacy.inputPer1M)}/${formatRate(legacy.outputPer1M)} while each prompt stays under 100K tokens (10x per token; it counts ~30% more tokens for the same text), with a 1M window and prompts caching from ${target.minCacheTokens} tokens instead of ${legacy.minCacheTokens.toLocaleString()}. Check first: budget_tokens, sampling params and prefill return 400`,
    impact: 40,
  }
}

/**
 * Warn when a turn crosses a tiered model's prompt-length line (Haiku 5.5: 100K), read from the
 * billed per-turn prompts so a base-prompt edit or /compact moves it.
 */
function promptTierRecommendation(inputs: CalculatorInputs, layers: readonly TurnLayer[]): Rec | null {
  const tier = MODELS[inputs.model].longPrompt
  if (!tier) return null
  const firstTurnOver = layers.findIndex((layer) => layer.promptTokens > tier.threshold)
  if (firstTurnOver < 0) return null
  return {
    text: `From turn ${firstTurnOver + 1} the prompt passes ${tier.threshold.toLocaleString()} tokens, so each request over that line pays ${formatRate(tier.inputPer1M)}/${formatRate(tier.outputPer1M)} instead of ${formatRate(MODELS[inputs.model].inputPer1M)}/${formatRate(MODELS[inputs.model].outputPer1M)} (5x). Run /compact or /clear before then`,
    impact: 35,
  }
}

// Sonnet 5.5 is the same $2/$10 as Sonnet 5 (with half its cache-read price) and a
// third below Sonnet 4.6 / 4.5's $3/$15, with a 512-token cache floor, so moving up
// is always a price cut.
const LEGACY_SONNETS: ReadonlySet<ModelId> = new Set<ModelId>(['sonnet-5', 'sonnet', 'sonnet-4-5'])

function legacySonnetRecommendation(id: ModelId): { text: string; impact: number } | null {
  if (!LEGACY_SONNETS.has(id)) return null
  const model = MODELS[id]
  const target = MODELS['sonnet-5-5']
  const saving = pctBelow(target.inputPer1M, model.inputPer1M)
  const cacheNote =
    target.cacheHitPer1M < model.cacheHitPer1M
      ? ` with cache reads at $${target.cacheHitPer1M.toFixed(2)} vs $${model.cacheHitPer1M.toFixed(2)}`
      : ''
  const price =
    saving > 0
      ? `${saving}% cheaper ($${target.inputPer1M}/$${target.outputPer1M} vs $${model.inputPer1M}/$${model.outputPer1M})${cacheNote}`
      : `the same $${target.inputPer1M}/$${target.outputPer1M}${cacheNote}`
  return {
    text: `Migrate to Sonnet 5.5 -- ${price}, and prompts cache from ${target.minCacheTokens} tokens instead of ${model.minCacheTokens.toLocaleString()}. Check first: thinking {type:"disabled"} returns 400 (send between_tools) and forced tool_choice returns 400`,
    impact: saving > 0 ? 30 : 10,
  }
}

/* ------------------------------------------------------------------ */
/* Session events and what-ifs as text, for the report and Markdown    */
/* ------------------------------------------------------------------ */

export const COMPUTED_LABEL = `${COMPUTED}.`

export const DIVERGENCE_NOTE =
  'claude-rate and the MCP cost server do not model breaks, the TTL or compaction, so their estimates differ when these are set.'

export interface EventLine {
  key: 'ttl' | 'breaks' | 'compaction' | 'toolOutput' | 'brevity'
  label: string
  text: string
  /** False while the input is at its neutral default and the line only says how to use it. */
  active: boolean
}

const dollars = (value: number) => `$${value.toFixed(2)}`
const signedDollars = (value: number) => `${value < 0 ? '-' : '+'}$${Math.abs(value).toFixed(2)}`
const tokensText = (tokens: number) => Math.round(tokens).toLocaleString('en-US')
const clampPercent = (value: number) => Math.min(Math.max(value, 0), 100)

/** Per-request amounts are often under a cent, so keep enough decimals to tell them apart. */
function fine(value: number): string {
  const size = Math.abs(value)
  if (size >= 1) return `$${value.toFixed(2)}`
  if (size >= 0.01) return `$${value.toFixed(3)}`
  return `$${value.toFixed(4)}`
}

function ttlLine(inputs: CalculatorInputs, result: CalculatorResult): string {
  const model = MODELS[inputs.model]
  const write = inputs.cacheTtl === '1h' ? model.cacheWrite1hPer1M : model.cacheWrite5mPer1M
  const other: CacheTtl = inputs.cacheTtl === '5m' ? '1h' : '5m'
  const otherMonthly = result.sessionEvents.otherTtlMonthly
  const ratio = Number((write / model.inputPer1M).toFixed(2))
  return `${TTL_NAMES[inputs.cacheTtl]}: ${model.name} writes the cache at ${formatRate(write)} per 1M (${ratio}x input). The same sessions on the ${TTL_NAMES[other]} TTL: ${dollars(otherMonthly)}/month (${signedDollars(otherMonthly - result.monthlyCost)}).`
}

function breakLine(inputs: CalculatorInputs, result: CalculatorResult): string {
  const events = result.sessionEvents
  const ttl = `${TTL_NAMES[inputs.cacheTtl]} TTL`
  if (events.breaks === 0) return 'None. Add breaks under Session events to price idle gaps.'
  const gaps = `${events.breaks} ${events.breaks === 1 ? 'break' : 'breaks'} a session of ${inputs.breakMinutes} minutes`
  const count = events.rewrites.length
  if (count === 0) return `${gaps}, inside the ${ttl}: the cache is still warm, so nothing is re-written.`
  const mean = (pick: (r: Rewrite) => number) => events.rewrites.reduce((sum, r) => sum + pick(r), 0) / count
  const pct = result.monthlyCost > 0 ? (events.breakCostMonthly / result.monthlyCost) * 100 : 0
  const idle = events.idleCompactionApplies
    ? ' Idle compaction (v2.1.299+, 1-hour TTL, 200K+ tokens) would compact the largest of these first, so this is an upper bound.'
    : ''
  return `${gaps}, each longer than the ${ttl}. Each re-writes about ${tokensText(mean((r) => r.tokens))} tokens: ${fine(mean((r) => r.writeDollars))} to write vs ${fine(mean((r) => r.readDollars))} to read warm. Together ${dollars(events.breakCostMonthly)}/month (${percentText(pct)}% of this estimate).${idle}`
}

function compactionLine(inputs: CalculatorInputs, result: CalculatorResult): string {
  const c = result.sessionEvents.compaction
  if (inputs.compactAtTurn <= 0) return 'Never. Set a turn under Session events to compare with never compacting.'
  if (!c) return `After turn ${inputs.compactAtTurn} never runs: the session has ${inputs.turnsPerSession} turns.`
  const read = c.cold
    ? `re-writes ${tokensText(c.readTokens)} tokens uncached (a break past the TTL came first)`
    : `reads ${tokensText(c.readTokens)} tokens from cache`
  const payback = c.paybackTurn === null ? '' : `, paid back by turn ${c.paybackTurn + 1}`
  const verdict = c.savingPerSession > 0 ? `saves ${fine(c.savingPerSession)} a session${payback}` : `costs ${fine(-c.savingPerSession)} more a session`
  return `After turn ${inputs.compactAtTurn}, the summary request ${read} and writes ${tokensText(inputs.postCompactTokens)} tokens of kept history as output: ${fine(c.inputDollars + c.outputDollars)}. Against never compacting it ${verdict}.`
}

function toolOutputLine(inputs: CalculatorInputs, result: CalculatorResult): string {
  const cut = clampPercent(inputs.toolOutputCutPercent)
  if (cut === 0) return 'Enter a cut on file-read and tool-result tokens under What-if levers to price it.'
  const saving = result.sessionEvents.toolOutputSavingMonthly
  const pct = result.monthlyCost > 0 ? (saving / result.monthlyCost) * 100 : 0
  return `A ${cut}% cut on file-read and tool-result tokens saves ${dollars(saving)}/month (${percentText(pct)}% of this estimate).`
}

function brevityLine(inputs: CalculatorInputs, result: CalculatorResult): string {
  if (inputs.ruleTokens <= 0) return 'Enter rule tokens under What-if levers to price a brevity rule set.'
  const b = result.sessionEvents.brevity
  const prose = clampPercent(inputs.proseSharePercent)
  const head = `Loading ${tokensText(inputs.ruleTokens)} tokens of rules into the cached prefix adds ${dollars(b.loadMonthly)}/month.`
  let even: string
  if (b.breakEvenCutPercent === null) even = ' No output is prose, so they cannot break even.'
  else if (b.breakEvenCutPercent > 100) even = ' Even a 100% cut on prose output saves less than they cost.'
  else {
    const bound = prose === 100 ? ', so this is a lower bound' : ''
    even = ` They break even only if prose output drops at least ${b.breakEvenCutPercent.toFixed(1)}% (prose share ${prose}%${bound}).`
  }
  const cut = clampPercent(inputs.outputCutPercent)
  const net = b.netSavingMonthly
  const atCut = cut > 0 ? ` At a ${cut}% cut they ${net >= 0 ? 'save' : 'cost'} ${dollars(Math.abs(net))}/month net.` : ''
  return `${head}${even}${atCut} Counts the output saved, not the shorter history it leaves.`
}

/** One line per session event and what-if, the same text in the report card and the Markdown copy. */
export function sessionEventLines(inputs: CalculatorInputs, result: CalculatorResult): EventLine[] {
  return [
    { key: 'ttl', label: 'Cache TTL', text: ttlLine(inputs, result), active: true },
    { key: 'breaks', label: 'Breaks', text: breakLine(inputs, result), active: result.sessionEvents.breaks > 0 },
    {
      key: 'compaction',
      label: 'Compaction',
      text: compactionLine(inputs, result),
      active: result.sessionEvents.compaction !== null,
    },
    {
      key: 'toolOutput',
      label: 'Tool-output cut',
      text: toolOutputLine(inputs, result),
      active: clampPercent(inputs.toolOutputCutPercent) > 0,
    },
    { key: 'brevity', label: 'Brevity rules', text: brevityLine(inputs, result), active: inputs.ruleTokens > 0 },
  ]
}

const BREAKDOWN_ROWS: readonly [string, keyof CostBreakdown][] = [
  ['Base prompt', 'basePrompt'],
  ['CLAUDE.md', 'claudeMd'],
  ['MCP servers', 'mcp'],
  ['File reads', 'fileReads'],
  ['History', 'history'],
  ['Output', 'output'],
]

export function resultToMarkdown(inputs: CalculatorInputs, result: CalculatorResult): string {
  const model = MODELS[inputs.model]
  const assumption = inputs.basePromptTokens === TOKEN_ESTIMATES.systemPromptTokens ? ' (modelling assumption)' : ''
  const lines = [
    `## Claude Cost Estimate`,
    ``,
    `**Model:** ${model.name}${inputs.fastMode ? ' (Fast Mode)' : ''}`,
    `**Sessions:** ${inputs.sessionsPerDay}/day x ${inputs.workingDaysPerMonth} days = ${inputs.sessionsPerDay * inputs.workingDaysPerMonth}/month`,
    `**Turns/session:** ${inputs.turnsPerSession}`,
    `**Base prompt:** ${tokensText(inputs.basePromptTokens)} tokens${assumption}`,
    `**Cache TTL:** ${TTL_NAMES[inputs.cacheTtl]}`,
    ``,
    `| Category | Current | Optimized |`,
    `|----------|--------:|----------:|`,
    ...BREAKDOWN_ROWS.map(
      ([label, key]) => `| ${label} | $${result.breakdown[key].toFixed(2)} | $${result.optimizedBreakdown[key].toFixed(2)} |`,
    ),
    `| **Total** | **$${result.monthlyCost.toFixed(2)}** | **$${result.optimizedCost.toFixed(2)}** |`,
    ``,
    `**Savings: $${result.savings.toFixed(2)}/month (${Math.round(result.savingsPercent)}%)**`,
    ``,
    `### Session events and what-ifs`,
    ``,
    `*${COMPUTED_LABEL} ${DIVERGENCE_NOTE}*`,
    ``,
    ...sessionEventLines(inputs, result).map((line) => `- **${line.label}:** ${line.text}`),
    ``,
    `### Recommendations`,
    ...result.recommendations.map((r) => `- ${r}`),
    ``,
    `---`,
    `*Generated by [Claude Cost Optimizer](https://sagargupta.online/claude-cost-optimizer/calculator)*`,
  ]
  return lines.join('\n')
}
