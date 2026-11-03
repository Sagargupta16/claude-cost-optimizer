import { describe, expect, it } from 'vitest'
import { DEFAULT_INPUTS, calculate, resultToMarkdown, sessionCostForModel, type CalculatorInputs } from './calculator'
import { MODELS, TOKEN_ESTIMATES, turnInputCost, type ModelId } from './pricing'

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

const defaults: CalculatorInputs = { ...DEFAULT_INPUTS }

describe('calculate', () => {
  it('keeps the pre-session-events defaults: no breaks, the 5-minute TTL, no compaction, a 3,500-token base', () => {
    expect(defaults).toMatchObject({
      model: 'opus-5-5',
      turnsPerSession: 30,
      claudeMdLines: 100,
      sessionsPerDay: 3,
      workingDaysPerMonth: 22,
      mcpServers: 2,
      fileReadsPerTurn: 1,
      fastMode: false,
      basePromptTokens: 3_500,
      breaksPerSession: 0,
      cacheTtl: '5m',
      compactAtTurn: 0,
      toolOutputCutPercent: 0,
      outputCutPercent: 0,
    })
  })

  it('prices the calculator default session at $0.7419 (CHANGELOG 1.16.0)', () => {
    // 100 lines x 10 + 3,500 system + 2 x 1,500 MCP + 2,000 file read = 9,500 tokens on turn 1.
    expect(sessionCostForModel(defaults, 'opus-5-5')).toBeCloseTo(0.7419, 4)
    expect(calculate(defaults).monthlyCost).toBeCloseTo(0.7419 * 66, 2)
    // The same session as the README loop with a 7,500-token prefix (9,500 minus the file read).
    expect(sessionCostForModel(defaults, 'opus-5-5')).toBeCloseTo(readmeSession(7_500, true), 12)
  })

  it('leaves the default optimized figures where they were before the session events', () => {
    // Values printed by calculate() at 8e337f0 (before this change) for the default inputs.
    expect(calculate(defaults).optimizedCost).toBeCloseTo(33.447249, 6)
    expect(calculate({ ...defaults, model: 'sonnet-5-5' }).monthlyCost).toBeCloseTo(24.4827, 6)
    expect(calculate({ ...defaults, model: 'sonnet-5-5' }).optimizedCost).toBeCloseTo(16.924149, 6)
  })

  it('keeps the what-if levers out of the estimate', () => {
    const levers = { ...defaults, toolOutputCutPercent: 50, ruleTokens: 20_000, outputCutPercent: 40, proseSharePercent: 50 }
    expect(calculate(levers).monthlyCost).toBeCloseTo(calculate(defaults).monthlyCost, 12)
    expect(calculate(levers).optimizedCost).toBeCloseTo(calculate(defaults).optimizedCost, 12)
  })

  it('splits the monthly cost into categories that add back to the total', () => {
    const result = calculate(defaults)
    const sum = Object.values(result.breakdown).reduce((a, b) => a + b, 0)
    expect(sum).toBeCloseTo(result.monthlyCost, 8)
    expect(result.perTurnCurrent).toHaveLength(30)
  })

  it('gives the base prompt its own row instead of spreading it over CLAUDE.md and MCP', () => {
    // One turn: the 9,500-token prompt is written at $5/1M, and each row takes its token share.
    const result = calculate({ ...defaults, turnsPerSession: 1, sessionsPerDay: 1, workingDaysPerMonth: 1 })
    const input = perM(9_500, 5)
    expect(result.breakdown.basePrompt).toBeCloseTo((input * 3_500) / 9_500, 12)
    expect(result.breakdown.claudeMd).toBeCloseTo((input * 1_000) / 9_500, 12)
    expect(result.breakdown.mcp).toBeCloseTo((input * 3_000) / 9_500, 12)
    expect(result.breakdown.fileReads).toBeCloseTo((input * 2_000) / 9_500, 12)
  })

  it('bills an edited base prompt on every turn', () => {
    // Turn 1 of a 52,000-token prompt (46,000 base + 1,000 CLAUDE.md + 3,000 MCP + 2,000 file read).
    const result = calculate({ ...defaults, basePromptTokens: 46_000 })
    expect(result.perTurnCurrent[0]).toBeCloseTo(perM(52_000, 5) + perM(500, 20), 12)
    expect(result.perTurnLayers[1].cacheRead).toBeCloseTo(perM(52_000, 0.2), 12)
  })

  it('returns per-turn layers that add up to each turn, as billed', () => {
    const result = calculate({ ...defaults, breaksPerSession: 2, breakMinutes: 20, compactAtTurn: 25 })
    result.perTurnLayers.forEach((layer, turn) => {
      expect(layer.cacheRead + layer.cacheWrite + layer.output).toBeCloseTo(result.perTurnCurrent[turn], 12)
    })
    // Turn 1 writes 9,500 tokens; turn 2 reads them and writes the 1,500 new ones.
    expect(result.perTurnLayers[0]).toMatchObject({ cacheRead: 0, promptTokens: 9_500 })
    expect(result.perTurnLayers[0].cacheWrite).toBeCloseTo(perM(9_500, 5), 12)
    expect(result.perTurnLayers[1].cacheRead).toBeCloseTo(perM(9_500, 0.2), 12)
    expect(result.perTurnLayers[1].cacheWrite).toBeCloseTo(perM(1_500, 5), 12)
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

  it('never reports an optimized cost above the current one with breaks, either TTL and compaction', () => {
    const events: Partial<CalculatorInputs>[] = [
      { breaksPerSession: 3, breakMinutes: 20 },
      { breaksPerSession: 5, breakMinutes: 90, compactAtTurn: 12 },
      { breaksPerSession: 29, breakMinutes: 90, turnsPerSession: 30 },
      { breaksPerSession: 2, breakMinutes: 20, compactAtTurn: 50, turnsPerSession: 100, postCompactTokens: 2_000 },
    ]
    for (const id of Object.keys(MODELS) as ModelId[]) {
      for (const cacheTtl of ['5m', '1h'] as const) {
        for (const event of events) {
          const result = calculate({ ...defaults, model: id, cacheTtl, ...event })
          expect(result.optimizedCost, `${id} ${cacheTtl} ${JSON.stringify(event)}`).toBeLessThanOrEqual(result.monthlyCost)
        }
      }
    }
  })

  it('passes every session event through to the model comparison, so it agrees with the headline', () => {
    const inputs: CalculatorInputs = {
      ...defaults,
      basePromptTokens: 20_000,
      breaksPerSession: 3,
      breakMinutes: 20,
      cacheTtl: '1h',
      compactAtTurn: 18,
      postCompactTokens: 4_000,
    }
    for (const id of ['opus-5-5', 'sonnet-5-5', 'haiku-5-5', 'fable-5-1'] as const) {
      const result = calculate({ ...inputs, model: id })
      expect(sessionCostForModel({ ...inputs, model: id }, id) * 66, id).toBeCloseTo(result.monthlyCost, 10)
      expect(sessionCostForModel(inputs, id), id).not.toBeCloseTo(sessionCostForModel(defaults, id), 4)
    }
  })
})

describe('idle breaks and the cache TTL', () => {
  const session = (changes: Partial<CalculatorInputs>) => sessionCostForModel({ ...defaults, ...changes }, 'opus-5-5')

  it('adds the computed re-write for one Opus 5.5 break past the 5-minute TTL', () => {
    // The break falls before turn 16 (0-based 15), whose prompt is 9,500 + 15 x 1,500 = 32,000.
    // Warm, it reads the previous 30,500 at $0.20 and writes 1,500 at $5; cold, it writes all
    // 32,000 at $5. The difference is 30,500 x ($5.00 - $0.20) / 1M = $0.1464.
    const changes = { breaksPerSession: 1, breakMinutes: 15 }
    expect(session(changes) - session({})).toBeCloseTo(perM(30_500, 5 - 0.2), 12)
    expect(session(changes) - session({})).toBeCloseTo(0.1464, 4)

    const result = calculate({ ...defaults, ...changes })
    expect(result.coldTurns).toEqual([15])
    expect(result.perTurnLayers[15].cacheRead).toBe(0)
    expect(result.perTurnLayers[15].cacheWrite).toBeCloseTo(perM(32_000, 5), 12)
    expect(result.sessionEvents.breakCostMonthly).toBeCloseTo(perM(30_500, 4.8) * 66, 10)
    expect(result.sessionEvents.rewrites).toHaveLength(1)
    expect(result.sessionEvents.rewrites[0]).toMatchObject({ turn: 15, tokens: 30_500 })
    expect(result.sessionEvents.rewrites[0].writeDollars).toBeCloseTo(perM(30_500, 5), 12)
    expect(result.sessionEvents.rewrites[0].readDollars).toBeCloseTo(perM(30_500, 0.2), 12)
  })

  it('costs nothing for a break shorter than the TTL', () => {
    expect(session({ breaksPerSession: 2, breakMinutes: 4 })).toBe(session({}))
    expect(session({ breaksPerSession: 2, breakMinutes: 45, cacheTtl: '1h' })).toBe(session({ cacheTtl: '1h' }))
    expect(calculate({ ...defaults, breaksPerSession: 2, breakMinutes: 4 }).sessionEvents.breakCostMonthly).toBe(0)
  })

  it('writes turn 1 at $8 per 1M on the 1-hour TTL (Opus 5.5, 2x input)', () => {
    const result = calculate({ ...defaults, cacheTtl: '1h' })
    expect(result.perTurnLayers[0].cacheWrite).toBeCloseTo(perM(9_500, 8), 12)
    // Input $0.6009 (turn 1 at $8, 29 reads at $0.20, 29 x 1,500 written at $8) plus $0.30 of output.
    expect(session({ cacheTtl: '1h' })).toBeCloseTo(0.9009, 4)
  })

  it('makes the 1-hour TTL win at 2 breaks of 20 minutes in 30 turns, and lose with none', () => {
    // guides/08-prompt-caching.md: the 5-minute default wins with no pauses, and the 1-hour cache
    // wins once enough turns follow a 5-to-60-minute pause. Breaks before turns 11 and 21.
    const fiveMinute = session({ breaksPerSession: 2, breakMinutes: 20 })
    const oneHour = session({ breaksPerSession: 2, breakMinutes: 20, cacheTtl: '1h' })
    expect(fiveMinute).toBeCloseTo(0.7419 + perM(23_000, 4.8) + perM(38_000, 4.8), 10)
    expect(fiveMinute).toBeCloseTo(1.0347, 4)
    expect(oneHour).toBeCloseTo(0.9009, 4)
    expect(oneHour).toBeLessThan(fiveMinute)
    expect(session({})).toBeLessThan(session({ cacheTtl: '1h' }))

    const events = calculate({ ...defaults, breaksPerSession: 2, breakMinutes: 20 }).sessionEvents
    expect(events.otherTtlMonthly).toBeCloseTo(oneHour * 66, 10)
  })

  it('still re-writes on the 1-hour TTL after a break longer than an hour, at the 1-hour rate', () => {
    const changes = { cacheTtl: '1h' as const, breaksPerSession: 1, breakMinutes: 90 }
    expect(session(changes) - session({ cacheTtl: '1h' })).toBeCloseTo(perM(30_500, 8 - 0.2), 12)
  })

  it("re-writes a Haiku 5.5 prompt over 100K at the long tier's own 1-hour rate", () => {
    // Breaks before turns 26, 51 and 76; turn 76's prompt is 9,500 + 75 x 1,500 = 122,000 tokens.
    const result = calculate({
      ...defaults,
      model: 'haiku-5-5',
      turnsPerSession: 100,
      cacheTtl: '1h',
      breaksPerSession: 3,
      breakMinutes: 90,
    })
    expect(result.coldTurns).toEqual([25, 50, 75])
    expect(result.perTurnLayers[75].cacheWrite).toBeCloseTo(perM(122_000, MODELS['haiku-5-5'].longPrompt!.cacheWrite1hPer1M), 12)
    expect(result.perTurnLayers[75].cacheWrite).toBeCloseTo(perM(122_000, 1), 12)
  })

  it('flags idle compaction only for a 1-hour break past 60 minutes at 200K+ tokens', () => {
    // At defaults the prompt passes 200,000 tokens after turn 128 (9,500 + 127 x 1,500 = 200,000).
    // Breaks before turns 51, 101 and 151 of 200; the last one re-writes 9,500 + 149 x 1,500 = 233,000.
    const long = { ...defaults, turnsPerSession: 200, cacheTtl: '1h' as const, breaksPerSession: 3 }
    expect(calculate({ ...long, breakMinutes: 90 }).sessionEvents.idleCompactionApplies).toBe(true)
    expect(calculate({ ...long, breakMinutes: 30 }).sessionEvents.idleCompactionApplies).toBe(false)
    expect(calculate({ ...long, breaksPerSession: 1, breakMinutes: 90 }).sessionEvents.idleCompactionApplies).toBe(false)
  })
})

describe('compaction', () => {
  it('never saves when it keeps the whole history', () => {
    for (const id of ['opus-5-5', 'sonnet-5-5', 'haiku-5-5', 'fable-5-1', 'haiku'] as const) {
      for (const after of [1, 5, 15, 29]) {
        // History at turn `after` (0-based) is after x 1,500 tokens; keeping all of it saves nothing.
        const kept = { ...defaults, model: id, compactAtTurn: after, postCompactTokens: after * 1_500 }
        expect(sessionCostForModel(kept, id), `${id} after ${after}`).toBeGreaterThan(sessionCostForModel(defaults, id))
        expect(calculate(kept).sessionEvents.compaction!.savingPerSession).toBeLessThan(0)
      }
    }
  })

  it('bills the summary request as a cache read of the prompt plus the kept history as output', () => {
    // After turn 20 the last prompt is 9,500 + 19 x 1,500 = 38,000 tokens, read at $0.20, and the
    // 5,000 kept tokens are output at $20. Turn 21 then reads the 7,500-token stable prefix and
    // writes the 2,000-token file read plus the 5,000-token summary at $5.
    const result = calculate({ ...defaults, compactAtTurn: 20, postCompactTokens: 5_000 })
    const turn = result.perTurnLayers[20]
    expect(turn).toMatchObject({ compacted: true, cold: false, promptTokens: 14_500 })
    expect(turn.cacheRead).toBeCloseTo(perM(38_000, 0.2) + perM(7_500, 0.2), 12)
    expect(turn.cacheWrite).toBeCloseTo(perM(7_000, 5), 12)
    expect(turn.output).toBeCloseTo(perM(5_000, 20) + perM(500, 20), 12)
    expect(result.perTurnLayers[21].promptTokens).toBe(16_000)

    // Never compacting, turns 21-30 read 447,500 tokens and write 15,000: $0.1645 of input.
    // Compacting, they cost $0.1076 (summary) + $0.0365 (turn 21) + $0.0369 + $0.0675 = $0.2485.
    const compaction = result.sessionEvents.compaction!
    expect(compaction).toMatchObject({ turn: 20, readTokens: 38_000, cold: false })
    expect(compaction.inputDollars).toBeCloseTo(perM(38_000, 0.2), 12)
    expect(compaction.outputDollars).toBeCloseTo(perM(5_000, 20), 12)
    expect(compaction.savingPerSession).toBeCloseTo(0.1645 - 0.2485, 10)
    expect(compaction.paybackTurn).toBeNull()
  })

  it('pays back within a long session that compacts to a short summary', () => {
    const result = calculate({ ...defaults, turnsPerSession: 100, compactAtTurn: 50, postCompactTokens: 5_000 })
    const compaction = result.sessionEvents.compaction!
    expect(compaction.savingPerSession).toBeGreaterThan(0)
    expect(compaction.paybackTurn).toBeGreaterThanOrEqual(50)
    expect(compaction.paybackTurn).toBeLessThan(100)
  })

  it('makes the summary request uncached when a break past the TTL lands on it', () => {
    // One break sits before turn 16 (0-based 15), the same gap /compact after turn 15 uses. The
    // summary request then re-writes the 9,500 + 14 x 1,500 = 30,500-token prompt on the
    // 5-minute TTL, which compaction requests use even when the conversation is on 1 hour.
    for (const cacheTtl of ['5m', '1h'] as const) {
      const result = calculate({ ...defaults, cacheTtl, breaksPerSession: 1, breakMinutes: 90, compactAtTurn: 15 })
      expect(result.perTurnLayers[15]).toMatchObject({ cold: true, compacted: true })
      expect(result.coldTurns).toEqual([15])
      const compaction = result.sessionEvents.compaction!
      expect(compaction.cold).toBe(true)
      expect(compaction.inputDollars).toBeCloseTo(perM(30_500, 5), 12)
      expect(result.sessionEvents.rewrites[0]).toMatchObject({ turn: 15, tokens: 30_500 })
    }
  })

  it('does not run at or past the last turn', () => {
    const result = calculate({ ...defaults, compactAtTurn: 30 })
    expect(result.sessionEvents.compaction).toBeNull()
    expect(result.monthlyCost).toBe(calculate(defaults).monthlyCost)
  })
})

describe('what-if levers', () => {
  it('prices a tool-output cut on the file-read tokens of every turn', () => {
    // A 50% cut takes 1,000 tokens out of every prompt: turn 1 writes them at $5 and the 29 later
    // turns read them at $0.20, so the session saves 1,000 x ($5 + 29 x $0.20) / 1M = $0.0108.
    const events = calculate({ ...defaults, toolOutputCutPercent: 50 }).sessionEvents
    expect(events.toolOutputSavingMonthly).toBeCloseTo(perM(1_000, 5 + 29 * 0.2) * 66, 10)
    expect(calculate(defaults).sessionEvents.toolOutputSavingMonthly).toBe(0)
  })

  it('computes the brevity break-even from the closed form', () => {
    // R rule tokens in the cached prefix: written once at $5, read 29 times at $0.20. Output is
    // 30 x 500 tokens at $20 = $0.30 a session, so the cut that pays for them is
    // R x ($5 + 29 x $0.20) / 1M / ($0.30 x prose share).
    const rules = TOKEN_ESTIMATES.costModeRuleTokens
    const load = perM(rules, 5 + 29 * 0.2)
    const events = calculate(defaults).sessionEvents
    expect(events.brevity.loadMonthly).toBeCloseTo(load * 66, 10)
    expect(events.brevity.breakEvenCutPercent).toBeCloseTo((load / 0.3) * 100, 8)
    expect(calculate({ ...defaults, proseSharePercent: 50 }).sessionEvents.brevity.breakEvenCutPercent).toBeCloseTo(
      (load / 0.15) * 100,
      8,
    )

    const atBreakEven = calculate({ ...defaults, outputCutPercent: events.brevity.breakEvenCutPercent! }).sessionEvents
    expect(atBreakEven.brevity.netSavingMonthly).toBeCloseTo(0, 10)
    expect(calculate({ ...defaults, outputCutPercent: 50 }).sessionEvents.brevity.netSavingMonthly).toBeGreaterThan(0)
  })

  it('stores the measured cost-mode SKILL.md size as the default rule tokens', () => {
    // 2,901 cl100k tokens x 1.3 for the 4.7+ tokenizer, measured 2026-11-03 with tools/token-estimator.
    expect(TOKEN_ESTIMATES.costModeRuleTokens).toBe(Math.round(2_901 * 1.3))
    expect(defaults.ruleTokens).toBe(TOKEN_ESTIMATES.costModeRuleTokens)
  })
})

describe('recommendations from session events', () => {
  // Haiku 5.5 with 80 CLAUDE.md lines, 20 turns and 1 file read leaves no other recommendation.
  const quiet: CalculatorInputs = { ...defaults, model: 'haiku-5-5', claudeMdLines: 80, turnsPerSession: 20 }

  it('suggests the 1-hour TTL with its computed saving when the breaks fit inside an hour', () => {
    const inputs = { ...quiet, breaksPerSession: 10, breakMinutes: 30 }
    const result = calculate(inputs)
    const saving = result.monthlyCost - result.sessionEvents.otherTtlMonthly
    const share = (saving / result.monthlyCost) * 100
    expect(saving).toBeGreaterThan(0)
    expect(result.recommendations[0]).toBe(
      `Set promptCacheTtl to 1h -- at 10 breaks of 30 minutes a session it saves $${saving.toFixed(2)}/month (${share < 1 ? share.toFixed(1) : Math.round(share)}% of this estimate), even at the 2x write. Computed from your inputs, not a measurement`,
    )
  })

  it('suggests /compact before a break longer than an hour, ranked by the re-write cost', () => {
    const result = calculate({ ...quiet, breaksPerSession: 10, breakMinutes: 90 })
    const rec = result.recommendations.find((r) => r.startsWith('Run /compact before a break'))
    const share = (result.sessionEvents.breakCostMonthly / result.monthlyCost) * 100
    expect(rec).toContain(`$${result.sessionEvents.breakCostMonthly.toFixed(2)}/month in all (${Math.round(share)}% of this estimate)`)

    // On Opus 5.5 with a break in every gap the re-writes outrank every fixed-impact suggestion.
    const opus = calculate({ ...defaults, breaksPerSession: 29, breakMinutes: 90 })
    expect(opus.recommendations[0]).toMatch(/^Run \/compact before a break longer than the 5-minute TTL -- each of your 29 breaks/)
  })

  it('suggests the 5-minute TTL when the 1-hour write costs more than it saves', () => {
    const result = calculate({ ...quiet, cacheTtl: '1h' })
    expect(result.recommendations[0]).toMatch(/^Use the 5-minute cache TTL \(promptCacheTtl 5m\) -- saves \$/)
  })
})

describe('resultToMarkdown', () => {
  it('adds the base-prompt row and the session events, labelled as computed', () => {
    const inputs = { ...defaults, breaksPerSession: 2, breakMinutes: 20 }
    const text = resultToMarkdown(inputs, calculate(inputs))
    expect(text).toContain('**Base prompt:** 3,500 tokens (modelling assumption)')
    expect(text).toContain('**Cache TTL:** 5-minute')
    expect(text).toMatch(/\| Base prompt \| \$\d+\.\d\d \| \$\d+\.\d\d \|/)
    expect(text).toContain('### Session events and what-ifs')
    expect(text).toContain('*Computed from your inputs, not a measurement.')
    expect(text).toContain('- **Breaks:** 2 breaks a session of 20 minutes, each longer than the 5-minute TTL.')
    expect(text).toContain(`- **Brevity rules:** Loading ${TOKEN_ESTIMATES.costModeRuleTokens.toLocaleString('en-US')} tokens of rules`)
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
