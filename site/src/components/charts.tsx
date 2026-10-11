import { type PointerEvent as ReactPointerEvent, useMemo, useState } from 'react'
import { type ModelId, MODELS, formatRate } from '../utils/pricing'
import { type CalculatorInputs, type CostBreakdown, sessionCostForModel } from '../utils/calculator'
import { useContainerWidth, useTween, useTweenRecord, useTweenSeries } from './calculator/hooks'
import { compactTokens, niceTicks, signedUsd, tickLabel, tokenCount, usd, usdFine } from './calculator/format'
import { PICKABLE_MODELS } from './calculator/models'
import {
  BLUE_100,
  BLUE_200,
  BLUE_400,
  BLUE_600,
  GRID,
  INK_DARK,
  INK_LIGHT,
  NEUTRAL,
  NEUTRAL_DIM,
  SAVINGS,
  SURFACE,
  TEXT,
  WARN,
} from './calculator/palette'
import { splitTurns, tierCrossTurn, type TurnLayer } from './calculator/turnLayers'
import styles from './charts.module.css'

const sum = (values: readonly number[]) => values.reduce((a, b) => a + b, 0)

/** A mouse hover ends when the pointer leaves; a tap keeps its pick until the next tap. */
const isMouse = (e: ReactPointerEvent) => e.pointerType === 'mouse'

/* ------------------------------------------------------------------ */
/* Where the money goes: current vs optimized as two stacked bars      */
/* ------------------------------------------------------------------ */

type Category = keyof CostBreakdown

const CATEGORIES: readonly { key: Category; label: string; color: string; ink: string }[] = [
  { key: 'claudeMd', label: 'CLAUDE.md', color: BLUE_100, ink: INK_DARK },
  { key: 'mcp', label: 'MCP servers', color: BLUE_400, ink: INK_DARK },
  { key: 'fileReads', label: 'File reads', color: BLUE_200, ink: INK_DARK },
  { key: 'history', label: 'History', color: BLUE_600, ink: INK_LIGHT },
  { key: 'output', label: 'Output', color: NEUTRAL, ink: INK_DARK },
]

const STACK_BAR_H = 28
const STACK_CURRENT = { label: 14, bar: 22 }
const STACK_OPTIMIZED = { label: 76, bar: 84 }
const STACK_H = STACK_OPTIMIZED.bar + STACK_BAR_H + 2
const SEG_GAP = 2

interface Span {
  x: number
  w: number
  share: number
}

function spans(values: readonly number[], scale: number): Span[] {
  const total = sum(values)
  let acc = 0
  return values.map((v) => {
    const span = { x: acc * scale, w: v * scale, share: total > 0 ? v / total : 0 }
    acc += v
    return span
  })
}

function Segment({ span, y, color, ink }: Readonly<{ span: Span; y: number; color: string; ink: string }>) {
  const w = Math.max(span.w - SEG_GAP, 0)
  return (
    <>
      <rect x={span.x} y={y} width={w} height={STACK_BAR_H} rx={3} fill={color} />
      {w >= 38 && (
        <text x={span.x + w / 2} y={y + STACK_BAR_H / 2 + 4} textAnchor="middle" fill={ink} className={styles.segLabel}>
          {Math.round(span.share * 100)}%
        </text>
      )}
    </>
  )
}

function StackHeading({ y, label, total, width }: Readonly<{ y: number; label: string; total: number; width: number }>) {
  return (
    <>
      <text x={0} y={y} className={styles.rowLabelStrong}>
        {label}
      </text>
      <text x={width} y={y} textAnchor="end" className={styles.valueStrong}>
        {usd(total)}/mo
      </text>
    </>
  )
}

/** Dashed outline from the optimized total out to the current total: the spend that goes away. */
function SavedGhost({ from, to, saved }: Readonly<{ from: number; to: number; saved: number }>) {
  const w = to - from - SEG_GAP
  if (w < 4) return null
  const y = STACK_OPTIMIZED.bar
  return (
    <g>
      <rect
        className={styles.ghost}
        x={from + 1}
        y={y + 1}
        width={w}
        height={STACK_BAR_H - 2}
        rx={3}
        fill="none"
        stroke={SAVINGS}
        strokeWidth={1.5}
        strokeDasharray="5 4"
      />
      {w >= 96 && (
        <text x={from + 1 + w / 2} y={y + STACK_BAR_H / 2 + 4} textAnchor="middle" className={styles.ghostLabel}>
          saved {usd(saved)}
        </text>
      )}
    </g>
  )
}

function BreakdownTable({
  current,
  optimized,
  active,
}: Readonly<{ current: readonly number[]; optimized: readonly number[]; active: Category | null }>) {
  const curTotal = sum(current)
  const optTotal = sum(optimized)
  return (
    <table className={styles.legendTable}>
      <thead>
        <tr>
          <th scope="col">Category</th>
          <th scope="col">Current</th>
          <th scope="col">Optimized</th>
          <th scope="col" className={styles.changeCol}>
            Change
          </th>
        </tr>
      </thead>
      <tbody>
        {CATEGORIES.map((cat, i) => (
          <tr key={cat.key} className={active === cat.key ? styles.rowActive : undefined}>
            <th scope="row">
              <span className={styles.catCell}>
                <span className={styles.swatch} style={{ background: cat.color }} />
                {cat.label}
              </span>
            </th>
            <td>{usd(current[i])}</td>
            <td>{usd(optimized[i])}</td>
            <td className={`${styles.changeCol} ${styles.change}`}>{signedUsd(optimized[i] - current[i])}</td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <th scope="row">Total</th>
          <td>{usd(curTotal)}</td>
          <td>{usd(optTotal)}</td>
          <td className={`${styles.changeCol} ${styles.change}`}>{signedUsd(optTotal - curTotal)}</td>
        </tr>
      </tfoot>
    </table>
  )
}

/** Current vs optimized monthly cost as two stacked bars on one scale, plus the per-category table. */
export function SpendBreakdownChart({
  breakdown,
  optimizedBreakdown,
}: Readonly<{
  breakdown: CostBreakdown
  optimizedBreakdown: CostBreakdown
}>) {
  const [ref, width] = useContainerWidth<HTMLDivElement>()
  const [active, setActive] = useState<Category | null>(null)
  const target = useMemo(
    () => [CATEGORIES.map(({ key }) => breakdown[key]), CATEGORIES.map(({ key }) => optimizedBreakdown[key])],
    [breakdown, optimizedBreakdown],
  )
  const [cur, opt] = useTweenSeries(target)
  const curTotal = sum(cur)
  const optTotal = sum(opt)
  const scale = width / Math.max(curTotal, optTotal, 1e-9)
  const curSpans = spans(cur, scale)
  const optSpans = spans(opt, scale)
  const largest = CATEGORIES.reduce((a, b) => (breakdown[b.key] > breakdown[a.key] ? b : a))

  return (
    <section className={styles.chartBlock}>
      <h3 className={styles.chartTitle}>Where the money goes (monthly)</h3>
      <div className={styles.chartCanvas} ref={ref}>
        {width > 0 && (
          <svg
            viewBox={`0 0 ${width} ${STACK_H}`}
            width="100%"
            height={STACK_H}
            role="img"
            aria-label={`Stacked bars: current ${usd(sum(target[0]))} per month, optimized ${usd(sum(target[1]))} per month. Largest current category: ${largest.label}.`}
          >
            <StackHeading y={STACK_CURRENT.label} label="Current" total={curTotal} width={width} />
            <StackHeading y={STACK_OPTIMIZED.label} label="Optimized" total={optTotal} width={width} />
            <SavedGhost from={optTotal * scale} to={curTotal * scale} saved={curTotal - optTotal} />
            {CATEGORIES.map((cat, i) => (
              <g
                key={cat.key}
                className={styles.segment}
                opacity={active && active !== cat.key ? 0.28 : 1}
                onPointerEnter={() => setActive(cat.key)}
                onPointerDown={() => setActive(cat.key)}
                onPointerLeave={(e) => {
                  if (isMouse(e)) setActive(null)
                }}
              >
                <Segment span={curSpans[i]} y={STACK_CURRENT.bar} color={cat.color} ink={cat.ink} />
                <Segment span={optSpans[i]} y={STACK_OPTIMIZED.bar} color={cat.color} ink={cat.ink} />
              </g>
            ))}
          </svg>
        )}
      </div>
      <BreakdownTable current={cur} optimized={opt} active={active} />
      <p className={styles.chartCaption}>
        Hover or tap a segment to pick out one category. The dashed outline is the spend the optimized setup no
        longer pays for.
      </p>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Cost per turn: stacked layers across one session                    */
/* ------------------------------------------------------------------ */

type LayerKey = Exclude<keyof TurnLayer, 'promptTokens'>

/** Bottom of the stack first. Cache reads go on top: they grow with history, so the climbing edge is theirs. */
const TURN_LAYERS: readonly { key: LayerKey; label: string; color: string }[] = [
  { key: 'output', label: 'Output', color: NEUTRAL },
  { key: 'cacheWrite', label: 'New input (cache write)', color: BLUE_400 },
  { key: 'cacheRead', label: 'Earlier turns (cache read)', color: BLUE_600 },
]
const TOP_LAYER = TURN_LAYERS.length - 1
/** Top of the stack first, matching what the eye meets first on the chart. */
const READOUT_ORDER = [...TURN_LAYERS].reverse()

const TURN_H = 230
const TURN_M = { top: 26, right: 14, bottom: 24, left: 52 }

interface Plot {
  left: number
  right: number
  top: number
  bottom: number
  x: (i: number) => number
  y: (v: number) => number
}

function makePlot(width: number, maxValue: number, points: number): Plot {
  const left = TURN_M.left
  const right = Math.max(width - TURN_M.right, left + 1)
  const top = TURN_M.top
  const bottom = TURN_H - TURN_M.bottom
  const span = Math.max(points - 1, 1)
  const ceiling = Math.max(maxValue, 1e-9)
  return {
    left,
    right,
    top,
    bottom,
    x: (i) => left + (i / span) * (right - left),
    y: (v) => bottom - (v / ceiling) * (bottom - top),
  }
}

/** A one-turn session still draws as a flat band across the plot. */
const padSingle = (values: readonly number[]) => (values.length === 1 ? [values[0], values[0]] : [...values])

function stackSeries(series: readonly (readonly number[])[]): number[][] {
  let below: readonly number[] = []
  return series.map((s) => {
    const level = s.map((v, i) => v + (below[i] ?? 0))
    below = level
    return level
  })
}

const pointsOf = (values: readonly number[], plot: Plot) =>
  values.map((v, i) => `${plot.x(i).toFixed(1)},${plot.y(v).toFixed(1)}`)

const linePath = (values: readonly number[], plot: Plot) => `M${pointsOf(values, plot).join('L')}`

function bandPath(upper: readonly number[], lower: readonly number[], plot: Plot): string {
  const floor = lower.length > 0 ? lower : upper.map(() => 0)
  return `M${pointsOf(upper, plot).join('L')}L${pointsOf(floor, plot).reverse().join('L')}Z`
}

/** Turn numbers for the x axis: about six, always including the last, never crowding it. */
function xTickTurns(turns: number): number[] {
  const every = Math.max(1, Math.ceil(turns / 6))
  return Array.from({ length: turns }, (_, i) => i + 1).filter((turn) => {
    if (turn === turns) return true
    return (turn - 1) % every === 0 && turns - turn >= every / 2
  })
}

function TurnAxes({
  plot,
  ticks,
  top,
  turns,
}: Readonly<{ plot: Plot; ticks: readonly number[]; top: number; turns: number }>) {
  return (
    <g pointerEvents="none">
      {ticks
        .filter((t) => t <= top * 1.0001)
        .map((t) => (
          <g key={t}>
            <line x1={plot.left} x2={plot.right} y1={plot.y(t)} y2={plot.y(t)} stroke={GRID} strokeWidth={1} />
            <text x={plot.left - 8} y={plot.y(t) + 4} textAnchor="end" className={styles.axisText}>
              {tickLabel(t, ticks)}
            </text>
          </g>
        ))}
      {xTickTurns(turns).map((turn) => (
        <text key={turn} x={plot.x(turn - 1)} y={TURN_H - 6} textAnchor="middle" className={styles.axisText}>
          {turn}
        </text>
      ))}
    </g>
  )
}

function TurnBands({ stacks, plot }: Readonly<{ stacks: readonly number[][]; plot: Plot }>) {
  return (
    <g pointerEvents="none">
      {TURN_LAYERS.map((layer, k) => (
        <path
          key={layer.key}
          className={styles.band}
          d={bandPath(stacks[k], k > 0 ? stacks[k - 1] : [], plot)}
          fill={layer.color}
          stroke={SURFACE}
          strokeWidth={1}
          strokeLinejoin="round"
        />
      ))}
    </g>
  )
}

/** Session total per turn: draws in from the left on mount and whenever the model changes. */
function TotalLine({ values, plot }: Readonly<{ values: readonly number[]; plot: Plot }>) {
  const end = values.length - 1
  if (end < 0) return null
  const endX = plot.x(end)
  const endY = plot.y(values[end])
  return (
    <g pointerEvents="none">
      <path
        className={styles.drawLine}
        d={linePath(values, plot)}
        pathLength={1}
        fill="none"
        stroke={TEXT}
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle className={styles.pulse} cx={endX} cy={endY} r={4.5} fill="none" stroke={TEXT} strokeWidth={1.5} />
      <circle className={styles.endDot} cx={endX} cy={endY} r={4} fill={TEXT} stroke={SURFACE} strokeWidth={2} />
    </g>
  )
}

/** Where a tiered model's prompt passes its long-prompt line and every later request pays the higher rate. */
function TierMarker({ plot, at, threshold }: Readonly<{ plot: Plot; at: number; threshold: number }>) {
  const x = at === 0 ? plot.left : (plot.x(at - 1) + plot.x(at)) / 2
  const flip = x > (plot.left + plot.right) / 2
  return (
    <g pointerEvents="none" className={styles.tier}>
      <rect x={x} y={plot.top} width={Math.max(plot.right - x, 0)} height={plot.bottom - plot.top} fill={WARN} opacity={0.08} />
      <line x1={x} x2={x} y1={plot.top - 8} y2={plot.bottom} stroke={WARN} strokeWidth={1.5} strokeDasharray="4 3" />
      <text x={flip ? x - 6 : x + 6} y={plot.top - 12} textAnchor={flip ? 'end' : 'start'} className={styles.tierLabel}>
        {compactTokens(threshold)} prompt line, turn {at + 1}
      </text>
    </g>
  )
}

function HoverMarker({ plot, stacks, index }: Readonly<{ plot: Plot; stacks: readonly number[][]; index: number }>) {
  const x = plot.x(index)
  return (
    <g pointerEvents="none">
      <line x1={x} x2={x} y1={plot.top} y2={plot.bottom} stroke={NEUTRAL} strokeWidth={1} strokeDasharray="3 3" />
      {TURN_LAYERS.map((layer, k) => (
        <circle
          key={layer.key}
          cx={x}
          cy={plot.y(stacks[k][index] ?? 0)}
          r={3.5}
          fill={layer.color}
          stroke={SURFACE}
          strokeWidth={1.5}
        />
      ))}
    </g>
  )
}

/** The per-turn tooltip, docked above the chart so a finger never covers it. */
function TurnReadout({
  layer,
  total,
  turn,
  turns,
  tierThreshold,
}: Readonly<{ layer: TurnLayer; total: number; turn: number; turns: number; tierThreshold?: number }>) {
  const overTier = tierThreshold !== undefined && layer.promptTokens > tierThreshold
  return (
    <div className={styles.readout}>
      <div className={styles.readoutHead}>
        <span>
          Turn <strong className={styles.readoutTurn}>{turn + 1}</strong> of {turns}
        </span>
        <span className={styles.readoutTotal}>{usdFine(total)}</span>
      </div>
      <ul className={styles.readoutList}>
        {READOUT_ORDER.map((l) => (
          <li key={l.key} className={styles.readoutItem}>
            <span className={styles.swatch} style={{ background: l.color }} />
            <span>{l.label}</span>
            <span className={styles.readoutValue}>{usdFine(layer[l.key])}</span>
          </li>
        ))}
      </ul>
      <div className={overTier ? styles.readoutPromptWarn : styles.readoutPrompt}>
        Prompt {tokenCount(layer.promptTokens)} tokens
        {overTier ? `, over the ${compactTokens(tierThreshold)} prompt line` : ''}
      </div>
    </div>
  )
}

function tierSentence(inputs: CalculatorInputs, turns: number, cross: number | null): string {
  const model = MODELS[inputs.model]
  const tier = model.longPrompt
  if (!tier || cross === null) return ''
  const line = compactTokens(tier.threshold)
  if (cross < turns) {
    return ` From turn ${cross + 1} the prompt is over ${line} tokens, so ${model.name} bills the whole request at ${formatRate(tier.inputPer1M)}/${formatRate(tier.outputPer1M)} per 1M instead of ${formatRate(model.inputPer1M)}/${formatRate(model.outputPer1M)}.`
  }
  return ` ${model.name} stays under its ${line} prompt line for all ${turns} turns; at these settings it would cross at turn ${cross + 1}.`
}

function turnCaption(perTurn: readonly number[], inputs: CalculatorInputs, cross: number | null): string {
  const n = perTurn.length
  const first = `Turn 1 writes the whole prompt to the prompt cache at 1.25x input (${usdFine(perTurn[0])}).`
  if (n < 2) return `${first}${tierSentence(inputs, n, cross)}`
  return `${first} Every later turn reads the previous request back at the cache rate and writes only the new exchange, so turn 2 costs ${usdFine(perTurn[1])} and the growing history it re-reads lifts turn ${n} to ${usdFine(perTurn[n - 1])}.${tierSentence(inputs, n, cross)}`
}

/**
 * Cost per turn across one session, split into earlier turns read from the prompt cache, the
 * new exchange written to it, and output. Hover or drag to read any turn.
 */
export function CostPerTurnChart({ inputs, perTurn }: Readonly<{ inputs: CalculatorInputs; perTurn: number[] }>) {
  const [ref, width] = useContainerWidth<HTMLDivElement>()
  const [hover, setHover] = useState<number | null>(null)
  const layers = useMemo(() => splitTurns(inputs, perTurn), [inputs, perTurn])
  const series = useMemo(() => TURN_LAYERS.map(({ key }) => layers.map((l) => l[key])), [layers])
  const shown = useTweenSeries(series)
  const ticks = useMemo(() => niceTicks(Math.max(...perTurn, 0)), [perTurn])
  const [top] = useTween([Math.max(...ticks)], false)

  const n = perTurn.length
  if (n === 0) return null

  const stacks = stackSeries(shown.map(padSingle))
  const plot = makePlot(width, top, stacks[0].length)
  const turn = Math.min(hover ?? n - 1, n - 1)
  const cross = tierCrossTurn(inputs)
  const tier = MODELS[inputs.model].longPrompt

  const pick = (e: ReactPointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.getBoundingClientRect()
    const ratio = (e.clientX - box.left) / Math.max(box.width, 1)
    setHover(Math.min(n - 1, Math.max(0, Math.round(ratio * (n - 1)))))
  }

  return (
    <section className={styles.chartBlock}>
      <h3 className={styles.chartTitle}>Cost per turn across one session</h3>
      <TurnReadout layer={layers[turn]} total={perTurn[turn]} turn={turn} turns={n} tierThreshold={tier?.threshold} />
      <div className={`${styles.chartCanvas} ${styles.scrub}`} ref={ref}>
        {width > 0 && (
          <svg
            viewBox={`0 0 ${width} ${TURN_H}`}
            width="100%"
            height={TURN_H}
            role="img"
            aria-label={`Stacked area chart of cost per turn over ${n} turns: ${usdFine(perTurn[0])} at turn 1, ${usdFine(perTurn[n - 1])} at turn ${n}.`}
          >
            <TurnAxes plot={plot} ticks={ticks} top={top} turns={n} />
            <TurnBands stacks={stacks} plot={plot} />
            <TotalLine key={inputs.model} values={stacks[TOP_LAYER]} plot={plot} />
            {tier && cross !== null && cross < n && <TierMarker plot={plot} at={cross} threshold={tier.threshold} />}
            {hover !== null && <HoverMarker plot={plot} stacks={stacks} index={turn} />}
            <rect
              x={plot.left}
              y={plot.top}
              width={plot.right - plot.left}
              height={plot.bottom - plot.top}
              fill="transparent"
              onPointerMove={pick}
              onPointerDown={pick}
              onPointerLeave={(e) => {
                if (isMouse(e)) setHover(null)
              }}
            />
          </svg>
        )}
      </div>
      <p className={styles.chartCaption}>{turnCaption(perTurn, inputs, cross)}</p>
    </section>
  )
}

/* ------------------------------------------------------------------ */
/* Ranked bars: sorted rows that slide when the order changes          */
/* ------------------------------------------------------------------ */

export interface BarRow {
  id: string
  label: string
  note?: string
  value: number
  color: string
  tone: 'strong' | 'normal' | 'muted'
}

const BAR_ROW_H = 38

const LABEL_CLASS: Record<BarRow['tone'], string> = {
  strong: styles.rowLabelStrong,
  normal: styles.rowLabel,
  muted: styles.rowLabelMuted,
}

function rankOf(rows: readonly BarRow[]): Record<string, number> {
  const order = [...rows].sort((a, b) => b.value - a.value)
  return Object.fromEntries(order.map((r, i) => [r.id, i]))
}

function RankedBar({
  row,
  y,
  value,
  scale,
  width,
  format,
}: Readonly<{ row: BarRow; y: number; value: number; scale: number; width: number; format: (v: number) => string }>) {
  const w = value > 0 ? Math.max(value * scale, 2) : 0
  // Muted rows (legacy models) get a thinner bar, so they recede without dropping below 3:1 contrast.
  const barH = row.tone === 'muted' ? 6 : 10
  const barY = 25 - barH / 2
  return (
    <g transform={`translate(0 ${y.toFixed(2)})`}>
      <text x={0} y={13} className={LABEL_CLASS[row.tone]}>
        {row.label}
        {row.note && (
          <tspan dx={8} className={styles.rowNote}>
            {row.note}
          </tspan>
        )}
      </text>
      <text x={width} y={13} textAnchor="end" className={row.tone === 'strong' ? styles.valueStrong : styles.valueLabel}>
        {format(value)}
      </text>
      <rect x={0} y={barY} width={width} height={barH} rx={3} fill={GRID} />
      <rect x={0} y={barY} width={Math.min(w, width)} height={barH} rx={3} fill={row.color} />
    </g>
  )
}

/**
 * Horizontal bars sorted largest first. Values count up and rows slide to their new rank when
 * inputs change. Bars scale to the largest row, or to `scaleMax` when given (a share of a whole).
 */
export function RankedBars({
  rows,
  format,
  ariaLabel,
  scaleMax,
}: Readonly<{ rows: readonly BarRow[]; format: (v: number) => string; ariaLabel: string; scaleMax?: number }>) {
  const [ref, width] = useContainerWidth<HTMLDivElement>()
  const values = useMemo(() => Object.fromEntries(rows.map((r) => [r.id, r.value])), [rows])
  const ranks = useMemo(() => rankOf(rows), [rows])
  const shownValues = useTweenRecord(values)
  const shownRanks = useTweenRecord(ranks, false)
  const [max] = useTween([scaleMax ?? Math.max(...rows.map((r) => r.value), 0)], false)
  const scale = width / Math.max(max, 1e-9)
  const height = rows.length * BAR_ROW_H

  return (
    <div className={styles.chartCanvas} ref={ref}>
      {width > 0 && (
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} role="img" aria-label={ariaLabel}>
          {rows.map((row) => (
            <RankedBar
              key={row.id}
              row={row}
              y={(shownRanks[row.id] ?? ranks[row.id]) * BAR_ROW_H}
              value={shownValues[row.id] ?? 0}
              scale={scale}
              width={width}
              format={format}
            />
          ))}
        </svg>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Same settings on every model                                        */
/* ------------------------------------------------------------------ */

function ratioText(ratio: number): string {
  if (ratio < 1) return `${ratio.toFixed(2)}x`
  return `${ratio.toFixed(1)}x`
}

function modelNote(id: ModelId, inputs: CalculatorInputs, ratio: number): string {
  const { lifecycle, fastModeCapable } = MODELS[id]
  const tags = [id === inputs.model ? 'selected' : ratioText(ratio)]
  if (lifecycle && lifecycle !== 'active') tags.push(lifecycle)
  if (inputs.fastMode && fastModeCapable) tags.push('fast')
  return tags.join(' · ')
}

function modelColor(id: ModelId, selected: ModelId): string {
  if (id === selected) return BLUE_400
  return MODELS[id].lifecycle === 'active' ? NEUTRAL : NEUTRAL_DIM
}

function modelTone(id: ModelId, selected: ModelId): BarRow['tone'] {
  if (id === selected) return 'strong'
  return MODELS[id].lifecycle === 'active' ? 'normal' : 'muted'
}

function modelRows(inputs: CalculatorInputs, showLegacy: boolean): BarRow[] {
  const sessionsPerMonth = inputs.sessionsPerDay * inputs.workingDaysPerMonth
  const selectedCost = sessionCostForModel(inputs, inputs.model)
  return PICKABLE_MODELS.filter(
    (id) => showLegacy || id === inputs.model || MODELS[id].lifecycle === 'active',
  ).map((id) => {
    const session = sessionCostForModel(inputs, id)
    return {
      id,
      label: MODELS[id].name,
      note: modelNote(id, inputs, selectedCost > 0 ? session / selectedCost : 0),
      value: session * sessionsPerMonth,
      color: modelColor(id, inputs.model),
      tone: modelTone(id, inputs.model),
    }
  })
}

const perMonth = (v: number) => `${usd(v)}/mo`

/** Same settings costed on every selectable model; the selected one is highlighted, legacy ones dimmed. */
export function ModelComparisonChart({ inputs }: Readonly<{ inputs: CalculatorInputs }>) {
  const [showLegacy, setShowLegacy] = useState(true)
  const rows = useMemo(() => modelRows(inputs, showLegacy), [inputs, showLegacy])
  const cheapest = rows.reduce((a, b) => (b.value < a.value ? b : a))

  return (
    <section className={styles.chartBlock}>
      <div className={styles.chartHead}>
        <h3 className={styles.chartTitle}>Same settings on every model (per month)</h3>
        <button
          type="button"
          className={styles.chip}
          aria-pressed={showLegacy}
          onClick={() => setShowLegacy((v) => !v)}
        >
          <span className={styles.chipDot} aria-hidden="true" />
          Legacy models
        </button>
      </div>
      <RankedBars
        rows={rows}
        format={perMonth}
        ariaLabel={`Bar chart of monthly cost at your settings on ${rows.length} models. Cheapest: ${cheapest.label} at ${perMonth(cheapest.value)}.`}
      />
      <p className={styles.chartCaption}>
        Selected model in blue; legacy and deprecated models dimmed. The multiplier is each model's cost relative to{' '}
        {MODELS[inputs.model].name}.
      </p>
    </section>
  )
}
