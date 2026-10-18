import { describe, expect, it } from 'vitest'
import { calculate, sessionCostForModel, type CalculatorInputs } from './calculator'
import { MODELS, turnInputCost } from './pricing'

const perM = (tokens: number, rate: number) => (tokens / 1_000_000) * rate

/**
 * A 30-turn session billed the way the README's "Before vs After" describes it: turn 1 writes
 * the whole prompt, every later turn reads the previous request and writes the new 1,500
 * tokens, each turn carries one 2,000-token file read and 500 output tokens.
 */
function readmeSession(prefix: number, cached: boolean): number {
  const opus = MODELS['opus-5-5']
  let total = 0
  let previous = 0
  for (let turn = 0; turn < 30; turn++) {
    const prompt = prefix + 2_000 + turn * 1_500
    if (cached) {
      const { readDollars, writeDollars } = turnInputCost(opus, prompt, previous)
      total += readDollars + writeDollars
    } else {
      total += perM(prompt, opus.inputPer1M)
    }
    total += perM(500, opus.outputPer1M)
    previous = prompt
  }
  return total
}

describe('README worked example (Opus 5.5, 30 turns)', () => {
  // Closed form for the cached session with prefix P, so the expected value does not come from
  // the loop above: turn 1 writes P + 2,000 at $5; turns 2-30 read the previous prompt at $0.20
  // and write 1,500 at $5; 30 x 500 output tokens at $20.
  const closedForm = (prefix: number) => {
    const first = prefix + 2_000
    let reads = 0
    for (let t = 0; t < 29; t++) reads += first + t * 1_500
    return perM(first, 5) + perM(reads, 0.2) + perM(29 * 1_500, 5) + perM(30 * 500, 20)
  }

  it('costs $0.82 a session before the cleanup (15,000-token prefix)', () => {
    expect(readmeSession(15_000, true)).toBeCloseTo(0.8229, 4)
    expect(readmeSession(15_000, true)).toBeCloseTo(closedForm(15_000), 10)
  })

  it('costs $0.72 a session after the cleanup (5,500-token prefix), a 12% saving', () => {
    const before = readmeSession(15_000, true)
    const after = readmeSession(5_500, true)
    expect(after).toBeCloseTo(0.7203, 4)
    expect(Math.round((1 - after / before) * 100)).toBe(12)
  })

  it('matches the monthly figures at 3 sessions a day for 22 days', () => {
    expect(readmeSession(15_000, true) * 66).toBeCloseTo(54.31, 2)
    expect(readmeSession(5_500, true) * 66).toBeCloseTo(47.54, 2)
  })

  it('costs $4.95 uncached, where the same cleanup saves 23%', () => {
    const before = readmeSession(15_000, false)
    expect(before).toBeCloseTo(4.95, 10)
    expect(Math.round((1 - readmeSession(5_500, false) / before) * 100)).toBe(23)
  })

  it('puts output at 36% of the cached session ($0.30 of $0.8229)', () => {
    const output = perM(30 * 500, 20)
    expect(output).toBeCloseTo(0.3, 10)
    expect(Math.round((output / readmeSession(15_000, true)) * 100)).toBe(36)
  })
})

const defaults: CalculatorInputs = {
  model: 'opus-5-5',
  turnsPerSession: 30,
  claudeMdLines: 100,
  sessionsPerDay: 3,
  workingDaysPerMonth: 22,
  mcpServers: 2,
  fileReadsPerTurn: 1,
  fastMode: false,
}

describe('calculate', () => {
  it('prices the calculator default session at $0.7419 (CHANGELOG 1.16.0)', () => {
    // 100 lines x 10 + 3,500 system + 2 x 1,500 MCP + 2,000 file read = 9,500 tokens on turn 1.
    expect(sessionCostForModel(defaults, 'opus-5-5')).toBeCloseTo(0.7419, 4)
    expect(calculate(defaults).monthlyCost).toBeCloseTo(0.7419 * 66, 2)
  })

  it('splits the monthly cost into categories that add back to the total', () => {
    const result = calculate(defaults)
    const sum = Object.values(result.breakdown).reduce((a, b) => a + b, 0)
    expect(sum).toBeCloseTo(result.monthlyCost, 8)
    expect(result.perTurnCurrent).toHaveLength(30)
  })

  it('doubles every turn under Fast Mode on Opus 5.5 ($8/$40)', () => {
    const fast = sessionCostForModel({ ...defaults, fastMode: true }, 'opus-5-5')
    expect(fast).toBeCloseTo(2 * sessionCostForModel(defaults, 'opus-5-5'), 10)
  })

  it('ignores Fast Mode on a model that does not support it', () => {
    expect(sessionCostForModel({ ...defaults, fastMode: true }, 'sonnet-5-5')).toBeCloseTo(
      sessionCostForModel(defaults, 'sonnet-5-5'),
      10,
    )
  })

  it('never reports an optimized cost above the current one', () => {
    for (const id of Object.keys(MODELS) as (keyof typeof MODELS)[]) {
      const result = calculate({ ...defaults, model: id, claudeMdLines: 400, fileReadsPerTurn: 4 })
      expect(result.optimizedCost, id).toBeLessThanOrEqual(result.monthlyCost)
    }
  })
})

describe('Haiku 5.5 prompt-length tier', () => {
  const haiku: CalculatorInputs = { ...defaults, model: 'haiku-5-5', turnsPerSession: 100 }

  it('warns on the first turn whose prompt passes 100,000 tokens', () => {
    // Turn n (0-based) carries 9,500 + 1,500n tokens: n = 60 is 99,500, n = 61 is 101,000.
    // The threshold is printed with toLocaleString(), so match only the locale-free part.
    const recs = calculate(haiku).recommendations
    expect(recs.some((r) => r.startsWith('From turn 62 the prompt passes '))).toBe(true)
  })

  it('bills that turn at the high tier and the one before it at the low tier', () => {
    const perTurn = calculate(haiku).perTurnCurrent
    const low = perM(99_500 - 1_500, 0.01) + perM(1_500, 0.125) + perM(500, 0.5)
    const high = perM(99_500, 0.05) + perM(1_500, 0.625) + perM(500, 2.5)
    expect(perTurn[60]).toBeCloseTo(low, 10)
    expect(perTurn[61]).toBeCloseTo(high, 10)
  })

  it('stays silent when the session never reaches the line', () => {
    const recs = calculate({ ...haiku, turnsPerSession: 30 }).recommendations
    expect(recs.some((r) => r.startsWith('From turn'))).toBe(false)
  })
})
