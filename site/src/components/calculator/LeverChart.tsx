import { useMemo } from 'react'
import { calculate, type CalculatorInputs } from '../../utils/calculator'
import { type BarRow, RankedBars } from '../charts'
import { usd } from './format'
import { SAVINGS } from './palette'
import styles from '../charts.module.css'

type HalvableField = 'turnsPerSession' | 'claudeMdLines' | 'mcpServers' | 'fileReadsPerTurn'

const HALVABLE: readonly { field: HalvableField; label: string; floor: number }[] = [
  { field: 'turnsPerSession', label: 'Turns per session', floor: 1 },
  { field: 'claudeMdLines', label: 'CLAUDE.md lines', floor: 0 },
  { field: 'mcpServers', label: 'MCP servers', floor: 0 },
  { field: 'fileReadsPerTurn', label: 'File reads per turn', floor: 0 },
]

interface Lever {
  id: string
  label: string
  saving: number
}

/** Re-runs calculate() with one input halved (or Fast Mode off) and everything else unchanged. */
function levers(inputs: CalculatorInputs, monthlyCost: number): Lever[] {
  const found: Lever[] = HALVABLE.flatMap(({ field, label, floor }) => {
    const from = inputs[field]
    const to = Math.max(floor, Math.floor(from / 2))
    if (to === from) return []
    return [
      {
        id: field,
        label: `${label}: ${from} to ${to}`,
        saving: monthlyCost - calculate({ ...inputs, [field]: to }).monthlyCost,
      },
    ]
  })
  if (inputs.fastMode) {
    found.push({
      id: 'fastMode',
      label: 'Fast Mode: on to off',
      saving: monthlyCost - calculate({ ...inputs, fastMode: false }).monthlyCost,
    })
  }
  return found
}

/** Which single change moves this bill most, measured by the calculator itself. */
export function LeverChart({ inputs, monthlyCost }: Readonly<{ inputs: CalculatorInputs; monthlyCost: number }>) {
  const rows = useMemo<BarRow[]>(() => {
    const found = levers(inputs, monthlyCost)
    const best = Math.max(...found.map((l) => l.saving), 0)
    return found.map((l) => ({
      id: l.id,
      label: l.label,
      value: l.saving,
      color: SAVINGS,
      tone: l.saving === best ? 'strong' : 'normal',
    }))
  }, [inputs, monthlyCost])

  if (rows.length === 0) return null

  const format = (v: number) => {
    const share = monthlyCost > 0 ? Math.round((v / monthlyCost) * 100) : 0
    return `-${usd(v)} (${share}%)`
  }

  return (
    <section className={styles.chartBlock}>
      <h3 className={styles.chartTitle}>What-if: halve one input</h3>
      <RankedBars
        rows={rows}
        format={format}
        scaleMax={monthlyCost}
        ariaLabel={`Bar chart of monthly savings from halving one input at a time, largest first: ${[...rows]
          .sort((a, b) => b.value - a.value)
          .map((r) => `${r.label} saves ${usd(r.value)}`)
          .join('; ')}.`}
      />
      <p className={styles.chartCaption}>
        Each bar re-runs the calculator with one input halved and the rest unchanged. The full track is your
        current monthly bill.
      </p>
    </section>
  )
}
