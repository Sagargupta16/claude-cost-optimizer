import { useChartFrame } from './hooks'
import RideBar from './RideBar'
import styles from './homeCharts.module.css'

export interface Benchmark {
  task: string
  before: number
  after: number
}

const COLOR_BEFORE = '#4493e6'
const COLOR_AFTER = '#2ea043'
const VALUE_W = 56
const PCT_W = 52
const LABEL_H = 18
const BAR_H = 11
const PAIR_GAP = 3
const ROW_H = 60

function reductionPct(b: Benchmark): number {
  return Math.round(((b.before - b.after) / b.before) * 100)
}

function BenchRow({
  row,
  index,
  plotW,
  pctX,
  shown,
  format,
}: Readonly<{ row: Benchmark; index: number; plotW: number; pctX: number; shown: boolean; format: (v: number) => string }>) {
  const top = index * ROW_H
  const barsTop = top + LABEL_H
  const delay = 100 + index * 120
  return (
    <g>
      <text x={0} y={top + 12} className={styles.name}>
        {row.task}
      </text>
      <RideBar
        x={0}
        y={barsTop}
        width={plotW}
        height={BAR_H}
        color={COLOR_BEFORE}
        label={format(row.before)}
        shown={shown}
        delay={delay}
      />
      <RideBar
        x={0}
        y={barsTop + BAR_H + PAIR_GAP}
        width={(row.after / row.before) * plotW}
        height={BAR_H}
        color={COLOR_AFTER}
        label={format(row.after)}
        labelClass={styles.valueStrong}
        shown={shown}
        delay={delay + 80}
      />
      <text
        x={pctX}
        y={barsTop + BAR_H + 6}
        textAnchor="end"
        className={styles.pct}
        style={{ opacity: shown ? 1 : 0 }}
      >
        -{reductionPct(row)}%
      </text>
    </g>
  )
}

/**
 * Before and after values per row. Each row is scaled to its own "before", so rows measured in
 * different units (or orders of magnitude) still compare by the size of the cut.
 */
export function BenchmarkChart({
  rows,
  unit,
  format,
}: Readonly<{ rows: Benchmark[]; unit: string; format: (v: number) => string }>) {
  const { ref, width, shown } = useChartFrame()
  const height = (rows.length - 1) * ROW_H + LABEL_H + BAR_H * 2 + PAIR_GAP + 2
  const plotW = Math.max(width - VALUE_W - PCT_W, 0)
  const summary = rows.map((r) => `${r.task} ${format(r.before)} to ${format(r.after)}`).join('; ')

  return (
    <div>
      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={styles.swatch} style={{ background: COLOR_BEFORE }} />
          Before
        </span>
        <span className={styles.legendItem}>
          <span className={styles.swatch} style={{ background: COLOR_AFTER }} />
          After
        </span>
        <span className={styles.legendItem}>{unit}</span>
      </div>
      <div className={styles.frame} ref={ref} style={{ height }}>
        {width > 0 && (
          <svg width={width} height={height} role="img" aria-label={`${unit}, before and after: ${summary}.`}>
            {rows.map((row, i) => (
              <BenchRow key={row.task} row={row} index={i} plotW={plotW} pctX={width} shown={shown} format={format} />
            ))}
          </svg>
        )}
      </div>
    </div>
  )
}
