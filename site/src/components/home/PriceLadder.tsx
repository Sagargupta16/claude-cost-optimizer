import { formatRate } from '../../utils/pricing'
import { useChartFrame } from './hooks'
import { ladderSummary, type LadderRow } from './modelData'
import RideBar from './RideBar'
import styles from './homeCharts.module.css'

const COLOR_INPUT = '#9ecbff'
const COLOR_OUTPUT = '#4493e6'
const LABEL_W = 112
const VALUE_W = 48
const BAR_H = 10
const PAIR_GAP = 3
const ROW_H = 40
const TOP = 2

function LadderBars({
  row,
  index,
  barW,
  shown,
}: Readonly<{ row: LadderRow; index: number; barW: (v: number) => number; shown: boolean }>) {
  const top = TOP + index * ROW_H
  const delay = 120 + index * 110
  return (
    <g>
      <text x={0} y={top + 9} className={styles.name}>
        {row.name}
      </text>
      {row.note && (
        <text x={0} y={top + 22} className={styles.note}>
          {row.note}
        </text>
      )}
      <RideBar
        x={LABEL_W}
        y={top}
        width={barW(row.input)}
        height={BAR_H}
        color={COLOR_INPUT}
        label={formatRate(row.input)}
        shown={shown}
        delay={delay}
      />
      <RideBar
        x={LABEL_W}
        y={top + BAR_H + PAIR_GAP}
        width={barW(row.output)}
        height={BAR_H}
        color={COLOR_OUTPUT}
        label={formatRate(row.output)}
        labelClass={styles.valueStrong}
        shown={shown}
        delay={delay + 60}
      />
    </g>
  )
}

/** Per-1M input and output price of the current lineup, straight from MODELS. */
export function PriceLadder({ rows }: Readonly<{ rows: LadderRow[] }>) {
  const { ref, width, shown } = useChartFrame()
  const height = TOP + (rows.length - 1) * ROW_H + BAR_H * 2 + PAIR_GAP + 2
  const plotW = Math.max(width - LABEL_W - VALUE_W, 0)
  const max = Math.max(...rows.map((r) => r.output), 0.0001)
  const barW = (v: number) => (v / max) * plotW

  return (
    <div>
      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={styles.swatch} style={{ background: COLOR_INPUT }} />
          Input
        </span>
        <span className={styles.legendItem}>
          <span className={styles.swatch} style={{ background: COLOR_OUTPUT }} />
          Output
        </span>
      </div>
      <div className={styles.frame} ref={ref} style={{ height }}>
        {width > 0 && (
          <svg
            width={width}
            height={height}
            role="img"
            aria-label={`Price per million tokens on a linear scale: ${ladderSummary(rows)}.`}
          >
            {rows.map((row, i) => (
              <LadderBars key={row.key} row={row} index={i} barW={barW} shown={shown} />
            ))}
          </svg>
        )}
      </div>
    </div>
  )
}
