import { useState, useMemo, useCallback, useId, type ReactNode } from 'react'
import { type CacheTtl, type ModelId, MODELS, FAST_MODE_MULTIPLIER, TOKEN_ESTIMATES, formatRate } from '../utils/pricing'
import { DEFAULT_INPUTS, calculate, resultToMarkdown, type CalculatorInputs } from '../utils/calculator'
import { CostPerTurnChart, ModelComparisonChart, SpendBreakdownChart } from '../components/charts'
import { CostHeadline } from '../components/calculator/CostHeadline'
import { LeverChart } from '../components/calculator/LeverChart'
import { RecommendationCards } from '../components/calculator/RecommendationCards'
import { SessionEventsCard } from '../components/calculator/SessionEvents'
import { PICKABLE_MODELS } from '../components/calculator/models'
import { copyWithFeedback } from '../utils/clipboard'
import styles from './Calculator.module.css'

type NumericField = Exclude<keyof CalculatorInputs, 'model' | 'fastMode' | 'cacheTtl'>

interface NumberFieldDef {
  field: NumericField
  label: string
  min: number
  max: number
  hint?: string
  /** Spans both grid columns, for a long label or hint. */
  wide?: boolean
}

const tokens = (n: number) => n.toLocaleString('en-US')

const NUMBER_FIELDS: readonly NumberFieldDef[] = [
  { field: 'turnsPerSession', label: 'Turns per session', min: 1, max: 200 },
  { field: 'claudeMdLines', label: 'CLAUDE.md lines', min: 0, max: 1000 },
  { field: 'sessionsPerDay', label: 'Sessions per day', min: 1, max: 50 },
  { field: 'workingDaysPerMonth', label: 'Working days / month', min: 1, max: 31 },
  {
    field: 'mcpServers',
    label: 'MCP servers',
    min: 0,
    max: 20,
    hint: `estimate: ${tokens(TOKEN_ESTIMATES.tokensPerMcpServer)} per server, tool search off worst case`,
  },
  { field: 'fileReadsPerTurn', label: 'File reads per turn', min: 0, max: 20 },
]

const EVENT_FIELDS: readonly NumberFieldDef[] = [
  { field: 'breaksPerSession', label: 'Breaks per session', min: 0, max: 50, hint: 'Spread evenly between turns' },
  { field: 'breakMinutes', label: 'Break length (minutes)', min: 0, max: 600, hint: 'Re-writes only past the TTL' },
  { field: 'compactAtTurn', label: 'Compact after turn', min: 0, max: 199, hint: '0 = never' },
  {
    field: 'postCompactTokens',
    label: 'History kept (tokens)',
    min: 0,
    max: 1_000_000,
    hint: 'The summary /compact writes as output',
  },
]

const PROMPT_FIELDS: readonly NumberFieldDef[] = [
  {
    field: 'basePromptTokens',
    label: 'Base prompt tokens (everything except CLAUDE.md lines and MCP servers)',
    min: 0,
    max: 1_000_000,
    wide: true,
    hint: `Modelling assumption: ${tokens(TOKEN_ESTIMATES.systemPromptTokens)}. For your own figure, run claude-rate --usage (0.4.0 or later) and enter its startup-floor residual, not the raw floor, so CLAUDE.md and MCP are not counted twice.`,
  },
]

const LEVER_FIELDS: readonly NumberFieldDef[] = [
  {
    field: 'toolOutputCutPercent',
    label: 'Cut on file-read and tool-result tokens (%)',
    min: 0,
    max: 100,
    wide: true,
    hint: 'No preset: enter a cut you measured on your own sessions',
  },
  {
    field: 'ruleTokens',
    label: 'Brevity rule tokens',
    min: 0,
    max: 100_000,
    wide: true,
    hint: `Default: the cost-mode SKILL.md, ${tokens(TOKEN_ESTIMATES.costModeRuleTokens)} tokens on the 4.7+ tokenizer (measured 2026-11-03)`,
  },
  { field: 'outputCutPercent', label: 'Prose output cut (%)', min: 0, max: 100, hint: 'No preset: no benchmark yet' },
  { field: 'proseSharePercent', label: 'Prose share of output (%)', min: 0, max: 100, hint: 'At 100% the break-even is a lower bound' },
]

const TTL_OPTIONS: readonly { ttl: CacheTtl; label: string; meta: string }[] = [
  { ttl: '5m', label: '5 minutes', meta: 'writes 1.25x input' },
  { ttl: '1h', label: '1 hour', meta: 'writes 2x input' },
]

/** Wide enough for the config rail beside the report (see .grid in Calculator.module.css). */
const WIDE_SCREEN = '(min-width: 960px)'

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
        {MODELS[model].fastModeStatus ? ` -- ${MODELS[model].name} ${MODELS[model].fastModeStatus}` : ''})
      </span>
    </label>
  )
}

function NumberInput({
  def,
  value,
  onNumber,
}: Readonly<{ def: NumberFieldDef; value: number; onNumber: (field: NumericField, raw: string) => void }>) {
  const id = useId()
  const hintId = `${id}-hint`
  return (
    <div className={def.wide ? `${styles.inputLabel} ${styles.inputWide}` : styles.inputLabel}>
      <label htmlFor={id}>{def.label}</label>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        min={def.min}
        max={def.max}
        value={value}
        aria-describedby={def.hint ? hintId : undefined}
        onChange={(e) => onNumber(def.field, e.target.value)}
        className={styles.numberInput}
      />
      {def.hint && (
        <span id={hintId} className={styles.hint}>
          {def.hint}
        </span>
      )}
    </div>
  )
}

function NumberGrid({
  fields,
  inputs,
  onNumber,
}: Readonly<{
  fields: readonly NumberFieldDef[]
  inputs: CalculatorInputs
  onNumber: (field: NumericField, raw: string) => void
}>) {
  return (
    <div className={styles.inputGrid}>
      {fields.map((def) => (
        <NumberInput key={def.field} def={def} value={inputs[def.field]} onNumber={onNumber} />
      ))}
    </div>
  )
}

/** Open beside the report on a wide screen; folded on a phone so the estimate stays close to the top. */
function Disclosure({ title, state, children }: Readonly<{ title: string; state: string; children: ReactNode }>) {
  const [open, setOpen] = useState(() => globalThis.matchMedia?.(WIDE_SCREEN).matches ?? false)
  return (
    <details className={styles.disclosure} open={open} onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary className={styles.disclosureSummary}>
        <span className={styles.disclosureTitle}>{title}</span>
        <span className={styles.disclosureState}>{state}</span>
      </summary>
      <div className={styles.disclosureBody}>{children}</div>
    </details>
  )
}

function TtlPicker({ value, onPick }: Readonly<{ value: CacheTtl; onPick: (ttl: CacheTtl) => void }>) {
  return (
    <fieldset className={styles.ttlGroup}>
      <legend className={styles.ttlLegend}>Cache TTL</legend>
      <div className={styles.segmented}>
        {TTL_OPTIONS.map(({ ttl, label, meta }) => (
          <label key={ttl} className={styles.segment}>
            <input
              type="radio"
              name="cacheTtl"
              value={ttl}
              checked={value === ttl}
              onChange={() => onPick(ttl)}
              className={styles.radio}
            />
            <span className={styles.radioText}>
              {label}
              <span className={styles.radioMeta}>{meta}</span>
            </span>
          </label>
        ))}
      </div>
      <span className={styles.hint}>
        Claude Code uses 1 hour for a subscription's main conversation and 5 minutes on an API key or cloud provider;
        promptCacheTtl overrides it.
      </span>
    </fieldset>
  )
}

function eventsState(inputs: CalculatorInputs): string {
  const ttl = inputs.cacheTtl === '1h' ? '1h TTL' : '5m TTL'
  const breaks = inputs.breaksPerSession > 0 ? `${inputs.breaksPerSession} x ${inputs.breakMinutes} min breaks` : 'no breaks'
  const compact = inputs.compactAtTurn > 0 ? `compact after ${inputs.compactAtTurn}` : 'no compaction'
  return [ttl, breaks, compact].join(', ')
}

function ConfigPanel({
  inputs,
  onPick,
  onNumber,
  onFastMode,
  onTtl,
}: Readonly<{
  inputs: CalculatorInputs
  onPick: (id: ModelId) => void
  onNumber: (field: NumericField, raw: string) => void
  onFastMode: (on: boolean) => void
  onTtl: (ttl: CacheTtl) => void
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

      <NumberGrid fields={NUMBER_FIELDS} inputs={inputs} onNumber={onNumber} />

      <FastModeToggle model={inputs.model} checked={inputs.fastMode} onToggle={onFastMode} />

      <Disclosure title="Session events" state={eventsState(inputs)}>
        <TtlPicker value={inputs.cacheTtl} onPick={onTtl} />
        <NumberGrid fields={EVENT_FIELDS} inputs={inputs} onNumber={onNumber} />
      </Disclosure>

      <Disclosure title="Prompt size" state={`${tokens(inputs.basePromptTokens)} base tokens`}>
        <NumberGrid fields={PROMPT_FIELDS} inputs={inputs} onNumber={onNumber} />
      </Disclosure>

      <Disclosure title="What-if levers" state="not in the estimate">
        <NumberGrid fields={LEVER_FIELDS} inputs={inputs} onNumber={onNumber} />
      </Disclosure>
    </div>
  )
}

function Calculator() {
  const [inputs, setInputs] = useState<CalculatorInputs>(DEFAULT_INPUTS)
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

  const setTtl = useCallback((ttl: CacheTtl) => {
    setInputs((prev) => ({ ...prev, cacheTtl: ttl }))
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
        <ConfigPanel
          inputs={inputs}
          onPick={pickModel}
          onNumber={setNumber}
          onFastMode={setFastMode}
          onTtl={setTtl}
        />

        <div className={styles.report}>
          <CostHeadline result={result} sessionsPerMonth={sessionsPerMonth} />
          <SpendBreakdownChart breakdown={result.breakdown} optimizedBreakdown={result.optimizedBreakdown} />
          <CostPerTurnChart inputs={inputs} layers={result.perTurnLayers} />
          <SessionEventsCard inputs={inputs} result={result} />
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
