import { useCallback, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { type ModelId, MODELS } from '../utils/pricing'
import { type CalculatorInputs, type CostBreakdown, sessionCostForModel } from '../utils/calculator'
import styles from './charts.module.css'

// Palette validated with the dataviz six-checks validator against the site
// surface #161b22 (lightness band, chroma floor, CVD separation, contrast).
const COLOR_CURRENT = '#4493e6'
const COLOR_OPTIMIZED = '#2ea043'
const COLOR_DEEMPHASIS = '#6e7681'
const GRID = '#21262d'
const SURFACE = '#161b22'

function useContainerWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      setWidth(entries[0].contentRect.width)
    })
    ro.observe(el)
    setWidth(el.clientWidth)
    return () => ro.disconnect()
  }, [])
  return [ref, width]
}

function niceTicks(max: number, count = 4): number[] {
  if (max <= 0) return [0]
  const rough = max / count
  const pow = 10 ** Math.floor(Math.log10(rough))
  const step = [1, 2, 5, 10].map((m) => m * pow).find((s) => max / s <= count) ?? 10 * pow
  // Top tick must clear the data max so the line never exits the plot area.
  const top = Math.ceil(max / step - 0.001) * step
  const ticks: number[] = []
  for (let v = 0; v <= top + step * 0.001; v += step) ticks.push(v)
  return ticks
}

function money(v: number, decimals = 2): string {
  return `$${v.toFixed(decimals)}`
}

interface TooltipState {
  x: number
  y: number
  lines: string[]
}

function Tooltip({ tip }: { tip: TooltipState | null }) {
  if (!tip) return null
  return (
    <div className={styles.tooltip} style={{ left: tip.x, top: tip.y }}>
      {tip.lines.map((l, i) => (
        <div key={i} className={i === 0 ? styles.tooltipTitle : styles.tooltipValue}>
          {l}
        </div>
      ))}
    </div>
  )
}

/**
 * Cost per turn across one session -- the "why sessions get expensive" curve.
 * Single series: no legend needed; the title names it.
 */
export function CostPerTurnChart({ perTurn }: { perTurn: number[] }) {
  const [ref, width] = useContainerWidth<HTMLDivElement>()
  const [tip, setTip] = useState<TooltipState | null>(null)
  const [hoverTurn, setHoverTurn] = useState<number | null>(null)

  const height = 200
  const m = { top: 10, right: 46, bottom: 26, left: 46 }
  const iw = Math.max(width - m.left - m.right, 0)
  const ih = height - m.top - m.bottom

  const n = perTurn.length
  const maxY = Math.max(...perTurn, 0.0001)
  const ticks = useMemo(() => niceTicks(maxY), [maxY])
  const topY = ticks[ticks.length - 1] || maxY

  const xFor = useCallback(
    (i: number) => m.left + (n <= 1 ? iw / 2 : (i / (n - 1)) * iw),
    [iw, m.left, n],
  )
  const yFor = useCallback(
    (v: number) => m.top + ih - (v / topY) * ih,
    [ih, m.top, topY],
  )

  const linePath = useMemo(
    () => perTurn.map((v, i) => `${i === 0 ? 'M' : 'L'}${xFor(i).toFixed(1)},${yFor(v).toFixed(1)}`).join(''),
    [perTurn, xFor, yFor],
  )
  const areaPath = useMemo(() => {
    if (n === 0) return ''
    return `${linePath}L${xFor(n - 1).toFixed(1)},${yFor(0).toFixed(1)}L${xFor(0).toFixed(1)},${yFor(0).toFixed(1)}Z`
  }, [linePath, n, xFor, yFor])

  const xTickEvery = Math.max(1, Math.ceil(n / 6))

  const handleMove = useCallback(
    (e: React.PointerEvent<SVGRectElement>) => {
      const rect = e.currentTarget.getBoundingClientRect()
      const px = e.clientX - rect.left
      const i = Math.min(n - 1, Math.max(0, Math.round(((px) / Math.max(rect.width, 1)) * (n - 1))))
      setHoverTurn(i)
      setTip({
        x: xFor(i),
        y: yFor(perTurn[i]) - 12,
        lines: [`Turn ${i + 1}`, `${money(perTurn[i], 3)} this turn`],
      })
    },
    [n, perTurn, xFor, yFor],
  )
  const handleLeave = useCallback(() => {
    setHoverTurn(null)
    setTip(null)
  }, [])

  if (n === 0) return null

  return (
    <div className={styles.chartBlock}>
      <div className={styles.chartTitle}>Cost per turn across one session</div>
      <div className={styles.chartCanvas} ref={ref}>
        {width > 0 && (
          <svg width={width} height={height} role="img" aria-label="Line chart of per-turn cost growing across the session">
            {ticks.map((t) => (
              <g key={t}>
                <line x1={m.left} x2={width - m.right} y1={yFor(t)} y2={yFor(t)} stroke={GRID} strokeWidth={1} />
                <text x={m.left - 8} y={yFor(t) + 4} textAnchor="end" className={styles.axisText}>
                  {money(t, t < 0.1 ? 2 : 2)}
                </text>
              </g>
            ))}
            {perTurn.map((_, i) =>
              i % xTickEvery === 0 || i === n - 1 ? (
                <text key={i} x={xFor(i)} y={height - 8} textAnchor="middle" className={styles.axisText}>
                  {i + 1}
                </text>
              ) : null,
            )}
            <path d={areaPath} fill={COLOR_CURRENT} opacity={0.1} />
            <path d={linePath} fill="none" stroke={COLOR_CURRENT} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            {/* end marker with surface ring + direct label */}
            <circle cx={xFor(n - 1)} cy={yFor(perTurn[n - 1])} r={4.5} fill={COLOR_CURRENT} stroke={SURFACE} strokeWidth={2} />
            <text x={xFor(n - 1) + 8} y={yFor(perTurn[n - 1]) + 4} className={styles.endLabel}>
              {money(perTurn[n - 1], 3)}
            </text>
            {hoverTurn !== null && (
              <g>
                <line x1={xFor(hoverTurn)} x2={xFor(hoverTurn)} y1={m.top} y2={m.top + ih} stroke={COLOR_DEEMPHASIS} strokeWidth={1} />
                <circle cx={xFor(hoverTurn)} cy={yFor(perTurn[hoverTurn])} r={4.5} fill={COLOR_CURRENT} stroke={SURFACE} strokeWidth={2} />
              </g>
            )}
            <rect
              x={m.left}
              y={m.top}
              width={iw}
              height={ih}
              fill="transparent"
              onPointerMove={handleMove}
              onPointerLeave={handleLeave}
            />
          </svg>
        )}
        <Tooltip tip={tip} />
      </div>
      <div className={styles.chartCaption}>
        Later turns resend the whole history, so per-turn cost climbs. Turn {n} costs{' '}
        {perTurn[0] > 0 ? `${(perTurn[n - 1] / perTurn[0]).toFixed(1)}x` : 'more than'} turn 1.
      </div>
    </div>
  )
}

const BREAKDOWN_LABELS: { key: keyof CostBreakdown; label: string }[] = [
  { key: 'claudeMd', label: 'CLAUDE.md' },
  { key: 'mcp', label: 'MCP servers' },
  { key: 'fileReads', label: 'File reads' },
  { key: 'history', label: 'History' },
  { key: 'output', label: 'Output' },
]

/** Current vs optimized monthly cost, paired horizontal bars per category. */
export function BeforeAfterChart({
  breakdown,
  optimizedBreakdown,
}: {
  breakdown: CostBreakdown
  optimizedBreakdown: CostBreakdown
}) {
  const [ref, width] = useContainerWidth<HTMLDivElement>()
  const [tip, setTip] = useState<TooltipState | null>(null)

  const labelW = 96
  const valueW = 62
  const barH = 12
  const pairGap = 2
  const rowH = 44
  const m = { top: 4, left: labelW, right: valueW }
  const iw = Math.max(width - m.left - m.right, 0)
  const height = m.top + BREAKDOWN_LABELS.length * rowH

  const maxV = Math.max(
    ...BREAKDOWN_LABELS.map(({ key }) => Math.max(breakdown[key], optimizedBreakdown[key])),
    0.0001,
  )
  const wFor = (v: number) => (v / maxV) * iw

  const hover = (label: string, cur: number, opt: number, y: number) => {
    const saved = cur - opt
    setTip({
      x: m.left + Math.min(wFor(cur), iw * 0.6),
      y,
      lines: [label, `Current ${money(cur)} / Optimized ${money(opt)}`, `Saves ${money(Math.max(saved, 0))}/mo`],
    })
  }

  return (
    <div className={styles.chartBlock}>
      <div className={styles.chartTitle}>Where the savings come from (monthly)</div>
      <div className={styles.legendRow}>
        <span className={styles.legendItem}>
          <span className={styles.swatch} style={{ background: COLOR_CURRENT }} />
          Current
        </span>
        <span className={styles.legendItem}>
          <span className={styles.swatch} style={{ background: COLOR_OPTIMIZED }} />
          Optimized
        </span>
      </div>
      <div className={styles.chartCanvas} ref={ref}>
        {width > 0 && (
          <svg width={width} height={height} role="img" aria-label="Paired bar chart comparing current and optimized monthly cost per category">
            {BREAKDOWN_LABELS.map(({ key, label }, row) => {
              const cur = breakdown[key]
              const opt = optimizedBreakdown[key]
              const y = m.top + row * rowH
              return (
                <g
                  key={key}
                  onPointerEnter={() => hover(label, cur, opt, y + barH)}
                  onPointerLeave={() => setTip(null)}
                >
                  <text x={0} y={y + barH + 4} className={styles.rowLabel}>
                    {label}
                  </text>
                  <rect
                    className={styles.bar}
                    x={m.left}
                    y={y}
                    width={Math.max(wFor(cur), 1)}
                    height={barH}
                    rx={4}
                    fill={COLOR_CURRENT}
                  />
                  <rect
                    className={styles.bar}
                    x={m.left}
                    y={y + barH + pairGap}
                    width={Math.max(wFor(opt), 1)}
                    height={barH}
                    rx={4}
                    fill={COLOR_OPTIMIZED}
                  />
                  <text x={m.left + wFor(cur) + 6} y={y + barH - 2} className={styles.valueLabel}>
                    {money(cur)}
                  </text>
                  <text x={m.left + wFor(opt) + 6} y={y + barH * 2 + pairGap - 2} className={styles.valueLabel}>
                    {money(opt)}
                  </text>
                </g>
              )
            })}
          </svg>
        )}
        <Tooltip tip={tip} />
      </div>
    </div>
  )
}

/** Same settings costed on each active model; the selected one is emphasized. */
export function ModelComparisonChart({ inputs }: { inputs: CalculatorInputs }) {
  const [ref, width] = useContainerWidth<HTMLDivElement>()
  const [tip, setTip] = useState<TooltipState | null>(null)

  const modelIds = useMemo(() => {
    const active = (Object.keys(MODELS) as ModelId[]).filter(
      (id) => MODELS[id].lifecycle === 'active' && !MODELS[id].inviteOnly,
    )
    if (!active.includes(inputs.model)) active.push(inputs.model)
    return active
  }, [inputs.model])

  const rows = useMemo(
    () =>
      modelIds
        .map((id) => ({ id, name: MODELS[id].name, cost: sessionCostForModel(inputs, id) }))
        .sort((a, b) => b.cost - a.cost),
    [inputs, modelIds],
  )

  const labelW = 96
  const valueW = 62
  const barH = 16
  const rowH = 30
  const m = { top: 4, left: labelW, right: valueW }
  const iw = Math.max(width - m.left - m.right, 0)
  const height = m.top + rows.length * rowH
  const maxV = Math.max(...rows.map((r) => r.cost), 0.0001)
  const sessionsPerMonth = inputs.sessionsPerDay * inputs.workingDaysPerMonth

  return (
    <div className={styles.chartBlock}>
      <div className={styles.chartTitle}>Same settings on other models (per session)</div>
      <div className={styles.chartCanvas} ref={ref}>
        {width > 0 && (
          <svg width={width} height={height} role="img" aria-label="Bar chart of session cost per model with the selected model highlighted">
            {rows.map((r, row) => {
              const y = m.top + row * rowH
              const selected = r.id === inputs.model
              const w = Math.max((r.cost / maxV) * iw, 1)
              return (
                <g
                  key={r.id}
                  onPointerEnter={() =>
                    setTip({
                      x: m.left + Math.min(w, iw * 0.6),
                      y: y + barH / 2,
                      lines: [r.name, `${money(r.cost)} per session`, `${money(r.cost * sessionsPerMonth)} per month`],
                    })
                  }
                  onPointerLeave={() => setTip(null)}
                >
                  <text x={0} y={y + barH - 3} className={selected ? styles.rowLabelStrong : styles.rowLabel}>
                    {r.name}
                  </text>
                  <rect
                    className={styles.bar}
                    x={m.left}
                    y={y}
                    width={w}
                    height={barH}
                    rx={4}
                    fill={selected ? COLOR_CURRENT : COLOR_DEEMPHASIS}
                  />
                  <text x={m.left + w + 6} y={y + barH - 3} className={styles.valueLabel}>
                    {money(r.cost)}
                  </text>
                </g>
              )
            })}
          </svg>
        )}
        <Tooltip tip={tip} />
      </div>
      <div className={styles.chartCaption}>
        Selected model highlighted. Legacy models appear only when selected.
      </div>
    </div>
  )
}
