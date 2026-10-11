import { useEffect, useState } from 'react'
import styles from './analyzer.module.css'

// The order analyzeRepo() works in. It reports no progress, so the sequence
// advances on a timer and holds on the last step until the result arrives.
const STEPS = [
  'Looking up the repo and its default branch',
  'Fetching the repo tree',
  'Reading CLAUDE.md, settings and MCP config',
  'Scoring the rubric and estimating cost',
]
const STEP_MS = 850

type StepState = 'done' | 'active' | 'pending'

function stepState(index: number, active: number): StepState {
  if (index < active) return 'done'
  if (index === active) return 'active'
  return 'pending'
}

const STEP_CLASS: Record<StepState, string> = {
  done: styles.stepDone,
  active: styles.stepActive,
  pending: styles.stepPending,
}

function StepIcon({ state }: Readonly<{ state: StepState }>) {
  return (
    <svg className={styles.stepIcon} viewBox="0 0 18 18" aria-hidden="true">
      <circle cx={9} cy={9} r={7} className={styles.stepRing} />
      {state === 'active' && (
        <circle cx={9} cy={9} r={7} className={styles.stepSpin} style={{ transformOrigin: '9px 9px' }} />
      )}
      {state === 'done' && <path d="M5.5 9.3l2.3 2.3 4.7-4.9" pathLength={1} className={styles.stepCheck} />}
    </svg>
  )
}

function Skeleton() {
  return (
    <div className={styles.skeleton} aria-hidden="true">
      <div className={styles.skelCircle} />
      <div className={styles.skelLines}>
        <div className={styles.skelLine} />
        <div className={styles.skelLine} />
        <div className={styles.skelLine} />
        <div className={styles.skelLine} />
      </div>
    </div>
  )
}

export function AnalyzerLoading() {
  const [active, setActive] = useState(0)

  useEffect(() => {
    const id = setInterval(() => {
      setActive((s) => Math.min(s + 1, STEPS.length - 1))
    }, STEP_MS)
    return () => clearInterval(id)
  }, [])

  return (
    <div className={styles.loadingCard} role="status" aria-live="polite">
      <div className={styles.progress}>
        <div className={styles.progressBar} />
      </div>
      <ol className={styles.steps}>
        {STEPS.map((label, i) => {
          const state = stepState(i, active)
          return (
            <li key={label} className={`${styles.step} ${STEP_CLASS[state]}`}>
              <StepIcon state={state} />
              <span>{label}</span>
            </li>
          )
        })}
      </ol>
      <Skeleton />
    </div>
  )
}
