import { useState, useMemo, useCallback } from 'react'
import { type ModelId, MODELS, FAST_MODE_MULTIPLIER, formatRate } from '../utils/pricing'
import { calculate, resultToMarkdown, type CalculatorInputs } from '../utils/calculator'
import { CostPerTurnChart, ModelComparisonChart, SpendBreakdownChart } from '../components/charts'
import { CostHeadline } from '../components/calculator/CostHeadline'
import { LeverChart } from '../components/calculator/LeverChart'
import { RecommendationCards } from '../components/calculator/RecommendationCards'
import { PICKABLE_MODELS } from '../components/calculator/models'
import { copyWithFeedback } from '../utils/clipboard'
import styles from './Calculator.module.css'

type NumericField = Exclude<keyof CalculatorInputs, 'model' | 'fastMode'>

const defaultInputs: CalculatorInputs = {
  model: 'opus-5-5',
  turnsPerSession: 30,
  claudeMdLines: 100,
  sessionsPerDay: 3,
  workingDaysPerMonth: 22,
  mcpServers: 2,
  fileReadsPerTurn: 1,
  fastMode: false,
}

const NUMBER_FIELDS: readonly { field: NumericField; label: string; min: number; max: number }[] = [
  { field: 'turnsPerSession', label: 'Turns per session', min: 1, max: 200 },
  { field: 'claudeMdLines', label: 'CLAUDE.md lines', min: 0, max: 1000 },
  { field: 'sessionsPerDay', label: 'Sessions per day', min: 1, max: 50 },
  { field: 'workingDaysPerMonth', label: 'Working days / month', min: 1, max: 31 },
  { field: 'mcpServers', label: 'MCP servers', min: 0, max: 20 },
  { field: 'fileReadsPerTurn', label: 'File reads per turn', min: 0, max: 20 },
]

function ModelOption({
  id,
  checked,
  onPick,
}: Readonly<{ id: ModelId; checked: boolean; onPick: (id: ModelId) => void }>) {
  const model = MODELS[id]
  return (
    <label className={styles.radioLabel}>
      <input
        type="radio"
        name="model"
        value={id}
        checked={checked}
        onChange={() => onPick(id)}
        className={styles.radio}
      />
      <span className={styles.radioText}>
        {model.name}
        <span className={styles.radioMeta}>
          {formatRate(model.inputPer1M)}/{formatRate(model.outputPer1M)} per 1M
          {model.longPrompt ? ` up to ${(model.longPrompt.threshold / 1000).toLocaleString()}K prompt tokens` : ''}
        </span>
      </span>
    </label>
  )
}

function FastModeToggle({
  model,
  checked,
  onToggle,
}: Readonly<{ model: ModelId; checked: boolean; onToggle: (on: boolean) => void }>) {
  if (!MODELS[model].fastModeCapable) return null
  return (
    <label className={styles.checkboxLabel}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onToggle(e.target.checked)}
        className={styles.checkbox}
      />
      <span>
        Fast Mode ({MODELS[model].fastModeMultiplier ?? FAST_MODE_MULTIPLIER}x cost
        --{' '}
        {MODELS[model].name} research preview)
      </span>
    </label>
  )
}

function ConfigPanel({
  inputs,
  onPick,
  onNumber,
  onFastMode,
}: Readonly<{
  inputs: CalculatorInputs
  onPick: (id: ModelId) => void
  onNumber: (field: NumericField, raw: string) => void
  onFastMode: (on: boolean) => void
}>) {
  return (
    <div className={styles.inputPanel}>
      <h2 className={styles.panelTitle}>Configuration</h2>

      <fieldset className={styles.fieldset}>
        <legend className={styles.legend}>Model</legend>
        <div className={styles.radioGroup}>
          {PICKABLE_MODELS.map((id) => (
            <ModelOption key={id} id={id} checked={inputs.model === id} onPick={onPick} />
          ))}
        </div>
      </fieldset>

      <div className={styles.inputGrid}>
        {NUMBER_FIELDS.map(({ field, label, min, max }) => (
          <label key={field} className={styles.inputLabel}>
            <span>{label}</span>
            <input
              type="number"
              min={min}
              max={max}
              value={inputs[field]}
              onChange={(e) => onNumber(field, e.target.value)}
              className={styles.numberInput}
            />
          </label>
        ))}
      </div>

      <FastModeToggle model={inputs.model} checked={inputs.fastMode} onToggle={onFastMode} />
    </div>
  )
}

function Calculator() {
  const [inputs, setInputs] = useState<CalculatorInputs>(defaultInputs)
  const [copied, setCopied] = useState(false)

  const result = useMemo(() => calculate(inputs), [inputs])
  const sessionsPerMonth = inputs.sessionsPerDay * inputs.workingDaysPerMonth

  const pickModel = useCallback((id: ModelId) => {
    setInputs((prev) => ({ ...prev, model: id, fastMode: MODELS[id].fastModeCapable && prev.fastMode }))
  }, [])

  const setNumber = useCallback((field: NumericField, raw: string) => {
    const val = Number.parseInt(raw, 10)
    if (!Number.isNaN(val) && val >= 0) {
      setInputs((prev) => ({ ...prev, [field]: val }))
    }
  }, [])

  const setFastMode = useCallback((on: boolean) => {
    setInputs((prev) => ({ ...prev, fastMode: on }))
  }, [])

  const handleCopy = useCallback(() => {
    copyWithFeedback(resultToMarkdown(inputs, result), setCopied)
  }, [inputs, result])

  return (
    <div className={styles.calculator}>
      <h1 className={styles.title}>Cost Calculator</h1>
      <p className={styles.subtitle}>
        Estimate your monthly Claude Code costs and see where tokens go.
      </p>

      <div className={styles.grid}>
        <ConfigPanel inputs={inputs} onPick={pickModel} onNumber={setNumber} onFastMode={setFastMode} />

        <div className={styles.report}>
          <CostHeadline result={result} sessionsPerMonth={sessionsPerMonth} />
          <SpendBreakdownChart breakdown={result.breakdown} optimizedBreakdown={result.optimizedBreakdown} />
          <CostPerTurnChart inputs={inputs} perTurn={result.perTurnCurrent} />
          <ModelComparisonChart inputs={inputs} />
          <LeverChart inputs={inputs} monthlyCost={result.monthlyCost} />
          <RecommendationCards recommendations={result.recommendations} />
          <button type="button" onClick={handleCopy} className={styles.copyButton}>
            {copied ? 'Copied!' : 'Copy as Markdown'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default Calculator
