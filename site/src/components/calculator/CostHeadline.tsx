import type { CalculatorResult } from '../../utils/calculator'
import { useTween } from './hooks'
import { usd } from './format'
import { BLUE_400, SAVINGS } from './palette'
import styles from './CostHeadline.module.css'

function Figure({
  label,
  value,
  perSession,
  optimized = false,
}: Readonly<{ label: string; value: number; perSession: number; optimized?: boolean }>) {
  return (
    <div className={optimized ? `${styles.figure} ${styles.figureOptimized}` : styles.figure}>
      <span className={styles.figureLabel}>{label}</span>
      <span className={styles.figureValue}>
        {usd(value)}
        <span className={styles.unit}>/mo</span>
      </span>
      <span className={styles.figureSub}>{usd(perSession)} per session</span>
    </div>
  )
}

/** One bar the length of the current bill: what you would still pay, then what the optimized setup saves. */
function SavingsMeter({ share }: Readonly<{ share: number }>) {
  const kept = Math.min(Math.max(1 - share, 0), 1) * 100
  return (
    <svg
      className={styles.meter}
      viewBox="0 0 100 14"
      preserveAspectRatio="none"
      role="img"
      aria-label={`Optimized cost is ${Math.round(share * 100)}% below current`}
    >
      <rect x={0} y={0} width={kept} height={14} fill={BLUE_400} />
      <rect x={kept} y={0} width={100 - kept} height={14} fill={SAVINGS} />
    </svg>
  )
}

/** Headline of the report: current vs optimized monthly cost, counting up to each new value. */
export function CostHeadline({
  result,
  sessionsPerMonth,
}: Readonly<{ result: CalculatorResult; sessionsPerMonth: number }>) {
  const [current, optimized] = useTween([result.monthlyCost, result.optimizedCost])
  const saved = current - optimized
  const share = current > 0 ? saved / current : 0
  const perSession = (monthly: number) => (sessionsPerMonth > 0 ? monthly / sessionsPerMonth : 0)

  return (
    <section className={styles.headline} aria-label="Monthly cost summary">
      <h2 className={styles.title}>Monthly Estimate</h2>
      <div className={styles.figures}>
        <Figure label="Current" value={current} perSession={perSession(current)} />
        <Figure label="Optimized" value={optimized} perSession={perSession(optimized)} optimized />
      </div>
      <SavingsMeter share={share} />
      <div className={styles.meterKey}>
        <span className={styles.keyItem}>
          <span className={styles.keySwatch} style={{ background: BLUE_400 }} />
          Still paying
        </span>
        <span className={styles.keyItem}>
          <span className={styles.keySwatch} style={{ background: SAVINGS }} />
          Saved
        </span>
      </div>
      <div className={styles.savingsRow}>
        <span className={styles.savingsAmount}>Save {usd(saved)}/mo</span>
        <span className={styles.savingsPercent}>{Math.round(share * 100)}% reduction</span>
        <span className={styles.savingsYear}>{usd(saved * 12)} per year</span>
      </div>
    </section>
  )
}
