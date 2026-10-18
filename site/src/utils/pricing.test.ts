import { describe, expect, it } from 'vitest'
import { MODELS, cacheDiscountShare, ratesForPrompt, turnInputCost } from './pricing'

// Golden values for the billing primitives every estimator on the site is built on.
// Expected numbers are written out as arithmetic from the posted per-1M rates so a
// reviewer can check them by hand; none of them is copied from the code under test.

const perM = (tokens: number, rate: number) => (tokens / 1_000_000) * rate

describe('ratesForPrompt', () => {
  it('bills Haiku 5.5 at the low tier up to and including 100,000 prompt tokens', () => {
    const rates = ratesForPrompt(MODELS['haiku-5-5'], 100_000)
    expect(rates).toEqual({ inputPer1M: 0.1, outputPer1M: 0.5, cacheHitPer1M: 0.01, cacheWrite5mPer1M: 0.125 })
  })

  it('moves the whole Haiku 5.5 request to the high tier at 100,001 prompt tokens', () => {
    const rates = ratesForPrompt(MODELS['haiku-5-5'], 100_001)
    expect(rates).toEqual({ inputPer1M: 0.5, outputPer1M: 2.5, cacheHitPer1M: 0.05, cacheWrite5mPer1M: 0.625 })
  })

  it('keeps one rate across the full window on models without a prompt-length tier', () => {
    expect(ratesForPrompt(MODELS['opus-5-5'], 900_000).inputPer1M).toBe(4)
    expect(ratesForPrompt(MODELS['sonnet-5-5'], 900_000).cacheHitPer1M).toBe(0.1)
  })
})

describe('turnInputCost', () => {
  const opus = MODELS['opus-5-5']

  it('writes the whole prompt to the 5-minute cache on turn 1', () => {
    const { readDollars, writeDollars } = turnInputCost(opus, 20_000, 0)
    expect(readDollars).toBe(0)
    expect(writeDollars).toBeCloseTo(perM(20_000, 5), 10) // 1.25 x $4
  })

  it('reads the previous request from cache and writes only the new part', () => {
    const { readDollars, writeDollars } = turnInputCost(opus, 21_500, 20_000)
    expect(readDollars).toBeCloseTo(perM(20_000, 0.2), 10)
    expect(writeDollars).toBeCloseTo(perM(1_500, 5), 10)
  })

  it('pays full input when the prompt is under the minimum cacheable length', () => {
    const haiku45 = MODELS.haiku // Haiku 4.5: 4,096-token floor
    const { readDollars, writeDollars } = turnInputCost(haiku45, 4_000, 3_000)
    expect(readDollars).toBe(0)
    expect(writeDollars).toBeCloseTo(perM(4_000, 1), 10)
  })

  it('prices a Haiku 5.5 turn that crosses 100K at the high tier, cache read included', () => {
    const { readDollars, writeDollars } = turnInputCost(MODELS['haiku-5-5'], 101_000, 99_500)
    expect(readDollars).toBeCloseTo(perM(99_500, 0.05), 10)
    expect(writeDollars).toBeCloseTo(perM(1_500, 0.625), 10)
  })
})

describe('cache multipliers', () => {
  // The three multipliers the docs keep repeating: 0.1x by default, 0.05x on Opus 5.5
  // and Sonnet 5.5, 0.025x on Fable 5.1 and Mythos 5.1.
  it.each([
    ['opus-5', 0.9],
    ['haiku-5-5', 0.9],
    ['opus-5-5', 0.95],
    ['sonnet-5-5', 0.95],
    ['fable-5-1', 0.975],
    ['mythos-5-1', 0.975],
  ] as const)('%s reads cache at %s off base input', (id, share) => {
    expect(cacheDiscountShare(MODELS[id])).toBeCloseTo(share, 10)
  })

  it('prices every 5-minute write at 1.25x and every 1-hour write at 2x base input', () => {
    for (const model of Object.values(MODELS)) {
      expect(model.cacheWrite5mPer1M, model.name).toBeCloseTo(model.inputPer1M * 1.25, 10)
      expect(model.cacheWrite1hPer1M, model.name).toBeCloseTo(model.inputPer1M * 2, 10)
    }
  })
})
