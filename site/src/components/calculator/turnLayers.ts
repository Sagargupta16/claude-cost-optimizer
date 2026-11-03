import { MODELS, TOKEN_ESTIMATES } from '../../utils/pricing'
import {
  type CalculatorInputs,
  type TurnLayer,
  compactionTurn,
  fileReadTokens,
  stablePromptTokens,
} from '../../utils/calculator'

/** A run of consecutive 0-based turns, both ends included. */
export interface TurnRun {
  start: number
  end: number
}

/**
 * Runs of turns whose prompt is over the model's long-prompt line (Haiku 5.5:
 * MODELS['haiku-5-5'].longPrompt), read from calculate()'s own per-turn layers, so /compact or a
 * base-prompt edit moves them. Empty for a one-rate model.
 */
export function tierRuns(inputs: CalculatorInputs, layers: readonly TurnLayer[]): TurnRun[] {
  const tier = MODELS[inputs.model].longPrompt
  if (!tier) return []
  const runs: TurnRun[] = []
  layers.forEach((layer, turn) => {
    if (layer.promptTokens <= tier.threshold) return
    const last = runs[runs.length - 1]
    if (last && last.end === turn - 1) last.end = turn
    else runs.push({ start: turn, end: turn })
  })
  return runs
}

/**
 * For a session that stays under the long-prompt line: the 0-based turn where it would cross with
 * no compaction, which lies past the last turn. Null for a one-rate model or when /compact runs.
 */
export function projectedTierCross(inputs: CalculatorInputs): number | null {
  const tier = MODELS[inputs.model].longPrompt
  if (!tier || compactionTurn(inputs) !== null) return null
  const headroom = tier.threshold - stablePromptTokens(inputs) - fileReadTokens(inputs)
  if (headroom < 0) return 0
  return Math.floor(headroom / TOKEN_ESTIMATES.historyGrowthPerTurn) + 1
}
