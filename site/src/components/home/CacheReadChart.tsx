import { formatRate } from '../../utils/pricing'
import { useChartFrame } from './hooks'
import { formatMultiplier, type CacheRow } from './modelData'
import RideBar from './RideBar'
import styles from './homeCharts.module.css'

const COLOR_BAR = '#4493e6'
const LABEL_W = 96
const VALUE_W = 52
const BAR_H = 14
const ROW_H = 46
const TOP = 2

function CacheBar({
  row,
  index,
  plotW,
  max,
  shown,
}: Readonly<{ row: CacheRow; index: number; plotW: number; max: number; shown: boolean }>) {
  const top = TOP + index * ROW_H
  return (
    <g>
      <text x={0} y={top + 11} className={styles.name}>
        {row.name}
      </text>
      <rect x={LABEL_W} y={top} width={plotW} height={BAR_H} rx={2} className={styles.track} />
      <RideBar
        x={LABEL_W}
        y={top}
        width={(row.multiplier / max) * plotW}
        height={BAR_H}
        color={COLOR_BAR}
        label={formatMultiplier(row.multiplier)}
        labelClass={styles.valueStrong}
        shown={shown}
        delay={150 + index * 120}
      />
      <text x={LABEL_W} y={top + BAR_H + 14} className={styles.note}>
        {formatRate(row.cacheRead)} cached vs {formatRate(row.input)} fresh, per 1M
      </text>
    </g>
  )
}

/** Cache-read price as a multiple of fresh input on each current model. Shorter is cheaper. */
export function CacheReadChart({ rows }: Readonly<{ rows: CacheRow[] }>) {
  const { ref, width, shown } = useChartFrame()
  const height = TOP + rows.length * ROW_H
  const plotW = Math.max(width - LABEL_W - VALUE_W, 0)
  const max = Math.max(...rows.map((r) => r.multiplier), 0.0001)
  const summary = rows.map((r) => `${r.name} ${formatMultiplier(r.multiplier)}`).join(', ')

  return (
    <div className={styles.frame} ref={ref} style={{ height }}>
      {width > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={`Cache-read price as a multiple of fresh input price: ${summary}.`}
        >
          {rows.map((row, i) => (
            <CacheBar key={row.key} row={row} index={i} plotW={plotW} max={max} shown={shown} />
          ))}
        </svg>
      )}
    </div>
  )
}
