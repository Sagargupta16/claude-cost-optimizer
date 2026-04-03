import { type ModelId, MODELS, FAST_MODE_MULTIPLIER, TOKEN_ESTIMATES } from './pricing'

export interface CalculatorInputs {
  model: ModelId
  turnsPerSession: number
  claudeMdLines: number
  sessionsPerDay: number
  workingDaysPerMonth: number
  mcpServers: number
  fileReadsPerTurn: number
  fastMode: boolean
}

export interface CostBreakdown {
  claudeMd: number
  mcp: number
  fileReads: number
  history: number
  output: number
}

export interface CalculatorResult {
  monthlyCost: number
  optimizedCost: number
  savings: number
  savingsPercent: number
  breakdown: CostBreakdown
  optimizedBreakdown: CostBreakdown
  recommendations: string[]
}

function computeSessionCost(
  inputs: {
    claudeMdLines: number
    mcpServers: number
    fileReadsPerTurn: number
    turnsPerSession: number
    fastMode: boolean
  },
  model: ModelId,
): { total: number; breakdown: CostBreakdown } {
  const pricing = MODELS[model]
  const t = TOKEN_ESTIMATES

  const claudeMdTokens = inputs.claudeMdLines * t.tokensPerClaudeMdLine
  const systemTokens = t.systemPromptTokens
  const mcpTokens = inputs.mcpServers * t.tokensPerMcpServer
  const fileTokensPerTurn = inputs.fileReadsPerTurn * t.tokensPerFileRead

  const stableInputPerTurn = claudeMdTokens + systemTokens + mcpTokens
  const cacheRate = t.cacheHitRate

  let totalInputTokens = 0
  let totalCachedTokens = 0
  let totalOutputTokens = 0

  let claudeMdInput = 0
  let mcpInput = 0
  let fileReadsInput = 0
  let historyInput = 0
  let outputTotal = 0

  for (let turn = 0; turn < inputs.turnsPerSession; turn++) {
    const historyTokens = turn * t.historyGrowthPerTurn

    const stableCached = stableInputPerTurn * cacheRate
    const stableUncached = stableInputPerTurn * (1 - cacheRate)

    const turnFileTokens = fileTokensPerTurn
    const turnOutput = t.outputTokensPerTurn

    totalCachedTokens += stableCached
    totalInputTokens += stableUncached + turnFileTokens + historyTokens
    totalOutputTokens += turnOutput

    const claudeMdFraction = claudeMdTokens / stableInputPerTurn
    const mcpFraction = mcpTokens / stableInputPerTurn

    claudeMdInput += claudeMdTokens * (1 - cacheRate) + claudeMdTokens * cacheRate
    mcpInput += mcpTokens * (1 - cacheRate) + mcpTokens * cacheRate
    fileReadsInput += turnFileTokens
    historyInput += historyTokens
    outputTotal += turnOutput

    // Adjust for cache pricing proportionally
    void claudeMdFraction
    void mcpFraction
  }

  const inputCost = (totalInputTokens / 1_000_000) * pricing.inputPer1M
  const cacheCost = (totalCachedTokens / 1_000_000) * pricing.cacheHitPer1M
  const outputCost = (totalOutputTokens / 1_000_000) * pricing.outputPer1M

  let sessionTotal = inputCost + cacheCost + outputCost

  if (inputs.fastMode && model === 'opus') {
    sessionTotal *= FAST_MODE_MULTIPLIER
  }

  // Compute breakdown costs proportionally
  const totalAllInput = claudeMdInput + mcpInput + fileReadsInput + historyInput
  const inputPlusCacheCost = inputCost + cacheCost
  const breakdownMultiplier = inputs.fastMode && model === 'opus' ? FAST_MODE_MULTIPLIER : 1
  const outputCostFinal = outputCost * breakdownMultiplier

  const breakdown: CostBreakdown = {
    claudeMd: totalAllInput > 0
      ? (claudeMdInput / totalAllInput) * inputPlusCacheCost * breakdownMultiplier
      : 0,
    mcp: totalAllInput > 0
      ? (mcpInput / totalAllInput) * inputPlusCacheCost * breakdownMultiplier
      : 0,
    fileReads: totalAllInput > 0
      ? (fileReadsInput / totalAllInput) * inputPlusCacheCost * breakdownMultiplier
      : 0,
    history: totalAllInput > 0
      ? (historyInput / totalAllInput) * inputPlusCacheCost * breakdownMultiplier
      : 0,
    output: outputCostFinal,
  }

  return { total: sessionTotal, breakdown }
}

export function calculate(inputs: CalculatorInputs): CalculatorResult {
  const sessionsPerMonth = inputs.sessionsPerDay * inputs.workingDaysPerMonth

  const current = computeSessionCost(
    {
      claudeMdLines: inputs.claudeMdLines,
      mcpServers: inputs.mcpServers,
      fileReadsPerTurn: inputs.fileReadsPerTurn,
      turnsPerSession: inputs.turnsPerSession,
      fastMode: inputs.fastMode,
    },
    inputs.model,
  )

  const optimizedClaudeMdLines = Math.min(inputs.claudeMdLines, 80)
  const optimizedFileReads = Math.round(inputs.fileReadsPerTurn * 0.7)

  // If Opus or Sonnet, 30% of work delegated to Haiku
  const isHaiku = inputs.model === 'haiku'
  const haikuFraction = isHaiku ? 0 : 0.3
  const primaryFraction = 1 - haikuFraction

  const optimizedPrimary = computeSessionCost(
    {
      claudeMdLines: optimizedClaudeMdLines,
      mcpServers: inputs.mcpServers,
      fileReadsPerTurn: optimizedFileReads,
      turnsPerSession: Math.round(inputs.turnsPerSession * primaryFraction),
      fastMode: false,
    },
    inputs.model,
  )

  let optimizedHaiku = { total: 0, breakdown: { claudeMd: 0, mcp: 0, fileReads: 0, history: 0, output: 0 } }
  if (haikuFraction > 0) {
    optimizedHaiku = computeSessionCost(
      {
        claudeMdLines: optimizedClaudeMdLines,
        mcpServers: inputs.mcpServers,
        fileReadsPerTurn: optimizedFileReads,
        turnsPerSession: Math.round(inputs.turnsPerSession * haikuFraction),
        fastMode: false,
      },
      'haiku',
    )
  }

  const monthlyCost = current.total * sessionsPerMonth
  const optimizedSessionCost = optimizedPrimary.total + optimizedHaiku.total
  const optimizedCost = optimizedSessionCost * sessionsPerMonth
  const savings = monthlyCost - optimizedCost
  const savingsPercent = monthlyCost > 0 ? (savings / monthlyCost) * 100 : 0

  const optimizedBreakdown: CostBreakdown = {
    claudeMd: (optimizedPrimary.breakdown.claudeMd + optimizedHaiku.breakdown.claudeMd) * sessionsPerMonth,
    mcp: (optimizedPrimary.breakdown.mcp + optimizedHaiku.breakdown.mcp) * sessionsPerMonth,
    fileReads: (optimizedPrimary.breakdown.fileReads + optimizedHaiku.breakdown.fileReads) * sessionsPerMonth,
    history: (optimizedPrimary.breakdown.history + optimizedHaiku.breakdown.history) * sessionsPerMonth,
    output: (optimizedPrimary.breakdown.output + optimizedHaiku.breakdown.output) * sessionsPerMonth,
  }

  const monthlyBreakdown: CostBreakdown = {
    claudeMd: current.breakdown.claudeMd * sessionsPerMonth,
    mcp: current.breakdown.mcp * sessionsPerMonth,
    fileReads: current.breakdown.fileReads * sessionsPerMonth,
    history: current.breakdown.history * sessionsPerMonth,
    output: current.breakdown.output * sessionsPerMonth,
  }

  const recommendations = generateRecommendations(inputs, monthlyBreakdown, monthlyCost)

  return {
    monthlyCost,
    optimizedCost,
    savings,
    savingsPercent,
    breakdown: monthlyBreakdown,
    optimizedBreakdown,
    recommendations,
  }
}

function generateRecommendations(
  inputs: CalculatorInputs,
  breakdown: CostBreakdown,
  _totalCost: number,
): string[] {
  const recs: { text: string; impact: number }[] = []

  if (inputs.claudeMdLines > 80) {
    const savingsPct = ((inputs.claudeMdLines - 80) / inputs.claudeMdLines) * (breakdown.claudeMd / Object.values(breakdown).reduce((a, b) => a + b, 0)) * 100
    recs.push({
      text: `Trim CLAUDE.md from ${inputs.claudeMdLines} to 80 lines -- saves ~${Math.round(savingsPct)}% of input costs`,
      impact: savingsPct,
    })
  }

  if (inputs.fastMode) {
    recs.push({
      text: 'Disable Fast Mode -- saves 83% by removing the 6x multiplier',
      impact: 83,
    })
  }

  if (inputs.model !== 'haiku') {
    recs.push({
      text: `Delegate simple tasks (tests, docs, formatting) to Haiku 4.5 -- saves 20-40% on delegated work`,
      impact: 30,
    })
  }

  if (inputs.fileReadsPerTurn > 1) {
    recs.push({
      text: `Add .claudeignore to reduce file reads from ${inputs.fileReadsPerTurn} per turn -- saves 5-15%`,
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
      text: `Reduce MCP servers from ${inputs.mcpServers} to 3 or fewer -- each adds ${TOKEN_ESTIMATES.tokensPerMcpServer} tokens/turn`,
      impact: 8,
    })
  }

  if (inputs.model === 'opus' && !inputs.fastMode) {
    recs.push({
      text: 'Consider Sonnet 4.6 for routine development -- 40% cheaper with similar quality for most tasks',
      impact: 40,
    })
  }

  recs.sort((a, b) => b.impact - a.impact)
  return recs.slice(0, 3).map((r) => r.text)
}

export function resultToMarkdown(inputs: CalculatorInputs, result: CalculatorResult): string {
  const model = MODELS[inputs.model]
  const lines = [
    `## Claude Cost Estimate`,
    ``,
    `**Model:** ${model.name}${inputs.fastMode ? ' (Fast Mode)' : ''}`,
    `**Sessions:** ${inputs.sessionsPerDay}/day x ${inputs.workingDaysPerMonth} days = ${inputs.sessionsPerDay * inputs.workingDaysPerMonth}/month`,
    `**Turns/session:** ${inputs.turnsPerSession}`,
    ``,
    `| Category | Current | Optimized |`,
    `|----------|--------:|----------:|`,
    `| CLAUDE.md | $${result.breakdown.claudeMd.toFixed(2)} | $${result.optimizedBreakdown.claudeMd.toFixed(2)} |`,
    `| MCP servers | $${result.breakdown.mcp.toFixed(2)} | $${result.optimizedBreakdown.mcp.toFixed(2)} |`,
    `| File reads | $${result.breakdown.fileReads.toFixed(2)} | $${result.optimizedBreakdown.fileReads.toFixed(2)} |`,
    `| History | $${result.breakdown.history.toFixed(2)} | $${result.optimizedBreakdown.history.toFixed(2)} |`,
    `| Output | $${result.breakdown.output.toFixed(2)} | $${result.optimizedBreakdown.output.toFixed(2)} |`,
    `| **Total** | **$${result.monthlyCost.toFixed(2)}** | **$${result.optimizedCost.toFixed(2)}** |`,
    ``,
    `**Savings: $${result.savings.toFixed(2)}/month (${Math.round(result.savingsPercent)}%)**`,
    ``,
    `### Recommendations`,
    ...result.recommendations.map((r) => `- ${r}`),
    ``,
    `---`,
    `*Generated by [Claude Cost Optimizer](https://sagargupta16.github.io/claude-cost-optimizer/calculator)*`,
  ]
  return lines.join('\n')
}
