import { MODELS, TOKEN_ESTIMATES, ratesForPrompt, turnInputCost } from '../../utils/pricing'
import type { CalculatorInputs } from '../../utils/calculator'

export interface TurnLayer {
  /** The whole previous request (prefix plus earlier turns), read back from the prompt cache. */
  cacheRead: number
  /** The new part of this turn's prompt, written to the 5-minute cache at 1.25x input. */
  cacheWrite: number
  output: number
  promptTokens: number
}

function promptBase(inputs: CalculatorInputs): { stable: number; files: number } {
  const t = TOKEN_ESTIMATES
  return {
    stable:
      inputs.claudeMdLines * t.tokensPerClaudeMdLine +
      t.systemPromptTokens +
      inputs.mcpServers * t.tokensPerMcpServer,
    files: inputs.fileReadsPerTurn * t.tokensPerFileRead,
  }
}

/**
 * Splits each turn's cost from calculate().perTurnCurrent into what it paid for, using the same
 * per-turn billing as calculator.ts (turnInputCost). Each turn is scaled so its parts add up to the
 * calculator's own total -- Fast Mode included.
 */
export function splitTurns(inputs: CalculatorInputs, perTurn: readonly number[]): TurnLayer[] {
  const model = MODELS[inputs.model]
  const t = TOKEN_ESTIMATES
  const { stable, files } = promptBase(inputs)
  let previousPrompt = 0
  return perTurn.map((total, turn) => {
    const promptTokens = stable + files + turn * t.historyGrowthPerTurn
    const { readDollars, writeDollars } = turnInputCost(model, promptTokens, previousPrompt)
    previousPrompt = promptTokens
    const output = (t.outputTokensPerTurn / 1_000_000) * ratesForPrompt(model, promptTokens).outputPer1M
    const sum = readDollars + writeDollars + output
    const scale = sum > 0 ? total / sum : 0
    return { cacheRead: readDollars * scale, cacheWrite: writeDollars * scale, output: output * scale, promptTokens }
  })
}

/**
 * 0-based index of the first turn whose prompt is over the model's long-prompt line (Haiku 5.5:
 * MODELS['haiku-5-5'].longPrompt), or null for a one-rate model. It can lie past the session's last turn.
 */
export function tierCrossTurn(inputs: CalculatorInputs): number | null {
  const tier = MODELS[inputs.model].longPrompt
  if (!tier) return null
  const { stable, files } = promptBase(inputs)
  const headroom = tier.threshold - stable - files
  if (headroom < 0) return 0
  return Math.floor(headroom / TOKEN_ESTIMATES.historyGrowthPerTurn) + 1
}
