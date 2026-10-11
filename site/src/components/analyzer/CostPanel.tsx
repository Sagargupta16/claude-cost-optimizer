import { useMemo, useState } from 'react'
import type { AnalysisResult } from '../../utils/repoAnalyzer'
import { MODELS, TOKEN_ESTIMATES, type ModelId } from '../../utils/pricing'
import { useContainerWidth, useCountUp } from './hooks'
import { Panel } from './primitives'
import { money } from './status'
import styles from './analyzer.module.css'

interface CostRow {
  id: ModelId
  name: string
  perSession: number
  perMonth: number
  current: boolean
  lifecycle: string
}

const LABEL_W = 84
const VALUE_W = 78
const BAR_H = 18
const ROW_H = 30

const COLOR_BASE = '#6e7681'
const COLOR_CLAUDE_MD = '#58a6ff'
const COLOR_MCP = '#1f6feb'

/** Every publicly available model, most expensive first. */
function buildRows(costEstimate: AnalysisResult['costEstimate']): CostRow[] {
  return (Object.keys(MODELS) as ModelId[])
    .filter((id) => !MODELS[id].inviteOnly)
    .map((id) => ({
      id,
      name: MODELS[id].name,
      perSession: costEstimate[id].perSession,
      perMonth: costEstimate[id].perMonth,
      current: MODELS[id].lifecycle === 'active',
      lifecycle: MODELS[id].lifecycle ?? 'active',
    }))
    .sort((a, b) => b.perMonth - a.perMonth)
}

function TokenStat({ label, tokens }: Readonly<{ label: string; tokens: number }>) {
  const shown = useCountUp(tokens, 1000)
  return (
    <div className={styles.tokenStat}>
      <span className={styles.tokenLabel}>{label}</span>
      <span className={styles.tokenValue}>~{Math.round(shown).toLocaleString()} tokens</span>
    </div>
  )
}

/** The system-prompt estimate split into its three inputs, as one stacked bar. */
function ContextStack({ result }: Readonly<{ result: AnalysisResult }>) {
  const mcpServers = result.settings.mcpServerCount
  const parts = [
    { key: 'base', label: 'Claude Code system prompt', tokens: TOKEN_ESTIMATES.systemPromptTokens, color: COLOR_BASE },
    { key: 'claudeMd', label: 'CLAUDE.md files', tokens: result.claudeMdAll.totalTokens, color: COLOR_CLAUDE_MD },
    { key: 'mcp', label: 'MCP servers', tokens: mcpServers * TOKEN_ESTIMATES.tokensPerMcpServer, color: COLOR_MCP },
  ]
  const total = Math.max(parts.reduce((sum, p) => sum + p.tokens, 0), 1)
  const segments = parts.map((p, i) => ({
    ...p,
    x: (parts.slice(0, i).reduce((sum, q) => sum + q.tokens, 0) / total) * 100,
    w: (p.tokens / total) * 100,
  }))
  const summary = parts.map((p) => `${p.label} ${p.tokens.toLocaleString()} tokens`).join(', ')

  return (
    <div className={styles.stackBlock}>
      <span className={styles.subTitle}>Fixed context on every request</span>
      <svg
        className={styles.stack}
        viewBox="0 0 100 10"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Fixed context per request: ${summary}`}
      >
        <rect x={0} y={0} width={100} height={10} className={styles.meterTrack} />
        {segments
          .filter((s) => s.tokens > 0)
          .map((s, i) => (
            <rect
              key={s.key}
              x={s.x}
              y={0}
              width={s.w}
              height={10}
              className={styles.stackSeg}
              style={{ fill: s.color, animationDelay: `${i * 260}ms` }}
            />
          ))}
      </svg>
      <ul className={styles.stackLegend}>
        {parts.map((p) => (
          <li key={p.key} className={styles.stackLegendItem}>
            <span className={styles.swatch} style={{ backgroundColor: p.color }} />
            <span>{p.label}</span>
            <span className={styles.stackLegendValue}>
              {p.tokens.toLocaleString()} ({Math.round((p.tokens / total) * 100)}%)
            </span>
          </li>
        ))}
      </ul>
      {mcpServers > 0 && (
        <p className={styles.caption}>
          The MCP figure is the worst case: full tool schemas, which load up front only when tool
          search is off.
        </p>
      )}
    </div>
  )
}

function CostBar({
  row,
  index,
  plotW,
  scale,
}: Readonly<{ row: CostRow; index: number; plotW: number; scale: number }>) {
  const barW = Math.max(plotW * scale, 2)
  const delay = index * 70
  return (
    <g className={styles.costRow} style={{ transform: `translateY(${index * ROW_H}px)` }}>
      <title>{`${row.name}: ${money(row.perSession)} per session, ${money(row.perMonth)} per month`}</title>
      <text x={0} y={BAR_H - 5} className={row.current ? styles.barLabelStrong : styles.barLabel}>
        {row.name}
      </text>
      <rect
        x={LABEL_W}
        y={0}
        width={plotW}
        height={BAR_H}
        className={`${styles.costBar} ${row.current ? styles.barCurrent : styles.barLegacy}`}
        style={{ transform: `scaleX(${barW / plotW})`, animationDelay: `${delay}ms` }}
      />
      <text
        y={BAR_H - 5}
        className={styles.barValue}
        style={{ transform: `translateX(${LABEL_W + barW + 6}px)`, animationDelay: `${delay + 500}ms` }}
      >
        {money(row.perMonth)}
      </text>
    </g>
  )
}

function CostBars({ rows }: Readonly<{ rows: CostRow[] }>) {
  const [ref, width] = useContainerWidth<HTMLDivElement>()
  const plotW = Math.max(width - LABEL_W - VALUE_W, 1)
  const maxMonth = Math.max(...rows.map((r) => r.perMonth), 0.0001)
  const summary = rows.map((r) => `${r.name} ${money(r.perMonth)}`).join(', ')
  return (
    <div ref={ref} className={styles.chartCanvas}>
      {width > 0 && (
        <svg
          width={width}
          height={rows.length * ROW_H}
          className={styles.chartSvg}
          role="img"
          aria-label={`Estimated monthly cost per model, highest first: ${summary}`}
        >
          {rows.map((row, i) => (
            <CostBar key={row.id} row={row} index={i} plotW={plotW} scale={row.perMonth / maxMonth} />
          ))}
        </svg>
      )}
    </div>
  )
}

function LineupToggle({ showAll, onChange }: Readonly<{ showAll: boolean; onChange: (all: boolean) => void }>) {
  return (
    <div className={styles.segmented} role="group" aria-label="Models shown">
      <button type="button" aria-pressed={!showAll} onClick={() => onChange(false)}>
        Current lineup
      </button>
      <button type="button" aria-pressed={showAll} onClick={() => onChange(true)}>
        All models
      </button>
    </div>
  )
}

function ChartLegend() {
  return (
    <div className={styles.legend}>
      <span className={styles.legendItem}>
        <span className={`${styles.swatch} ${styles.swatchCurrent}`} />
        Current lineup
      </span>
      <span className={styles.legendItem}>
        <span className={`${styles.swatch} ${styles.swatchLegacy}`} />
        Legacy or deprecated
      </span>
    </div>
  )
}

/** Most and least expensive of the charted models, from this repo's own estimate. */
function SpreadCaption({ rows }: Readonly<{ rows: CostRow[] }>) {
  if (rows.length < 2) return null
  const priciest = rows[0]
  const cheapest = rows.reduce((min, r) => (r.perMonth < min.perMonth ? r : min), priciest)
  if (cheapest.perMonth <= 0) return null
  return (
    <p className={styles.caption}>
      On this repo, {priciest.name} comes to {money(priciest.perMonth)} a month and {cheapest.name}{' '}
      to {money(cheapest.perMonth)}: a {(priciest.perMonth / cheapest.perMonth).toFixed(1)}x spread.
    </p>
  )
}

function CostTable({ rows }: Readonly<{ rows: CostRow[] }>) {
  return (
    <div className={styles.tableScroll}>
      <table className={styles.costTable}>
        <thead>
          <tr>
            <th>Model</th>
            <th>Per Session</th>
            <th>Per Month</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className={r.current ? undefined : styles.rowLegacy}>
              <td>
                {r.name}
                {!r.current && <span className={styles.lifecycleTag}>{r.lifecycle}</span>}
              </td>
              <td className={styles.mono}>{money(r.perSession)}</td>
              <td className={styles.mono}>{money(r.perMonth)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function CostPanel({ result }: Readonly<{ result: AnalysisResult }>) {
  const [showAll, setShowAll] = useState(false)
  const allRows = useMemo(() => buildRows(result.costEstimate), [result.costEstimate])
  const chartRows = showAll ? allRows : allRows.filter((r) => r.current)

  return (
    <Panel title="Cost Estimate (30-turn session, 3 sessions/day, 22 days/month)">
      <div className={styles.tokenSummary}>
        <TokenStat label="System prompt" tokens={result.tokenEstimate.systemPromptTokens} />
        <TokenStat label="Per turn (avg)" tokens={result.tokenEstimate.perTurnTokens} />
      </div>
      <ContextStack result={result} />
      <div className={styles.chartHead}>
        <span className={styles.subTitle}>Monthly cost by model</span>
        <LineupToggle showAll={showAll} onChange={setShowAll} />
      </div>
      {showAll && <ChartLegend />}
      <CostBars rows={chartRows} />
      <SpreadCaption rows={chartRows} />
      <CostTable rows={allRows} />
    </Panel>
  )
}
