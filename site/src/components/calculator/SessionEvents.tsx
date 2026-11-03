import { useId } from 'react'
import {
  type CalculatorInputs,
  type CalculatorResult,
  type EventLine,
  COMPUTED_LABEL,
  DIVERGENCE_NOTE,
  sessionEventLines,
} from '../../utils/calculator'
import chartStyles from '../charts.module.css'
import styles from './SessionEvents.module.css'

const GUIDE_08 = 'https://github.com/Sagargupta16/claude-cost-optimizer/blob/main/guides/08-prompt-caching.md'

/** Where the guide explains each event; the card computes, the guide gives the reasons. */
const GUIDE_LINKS: Partial<Record<EventLine['key'], { href: string; label: string }>> = {
  ttl: { href: `${GUIDE_08}#how-claude-code-picks-the-cache-ttl`, label: 'Which TTL Claude Code uses' },
  breaks: { href: `${GUIDE_08}#3-work-in-focused-sessions`, label: 'Why long gaps cost' },
  compaction: { href: `${GUIDE_08}#4-use-compact-strategically`, label: 'When /compact helps' },
}

function EventRow({ line }: Readonly<{ line: EventLine }>) {
  const link = GUIDE_LINKS[line.key]
  return (
    <div className={line.active ? `${styles.row} ${styles.rowActive}` : styles.row}>
      <dt className={styles.term}>{line.label}</dt>
      <dd className={styles.text}>
        {line.text}
        {link && (
          <>
            {' '}
            <a className={styles.link} href={link.href} target="_blank" rel="noreferrer">
              {link.label}
            </a>
          </>
        )}
      </dd>
    </div>
  )
}

/** Idle breaks, the cache TTL, compaction and the what-if levers, priced from the inputs. */
export function SessionEventsCard({ inputs, result }: Readonly<{ inputs: CalculatorInputs; result: CalculatorResult }>) {
  const titleId = useId()
  return (
    <section className={chartStyles.chartBlock} aria-labelledby={titleId}>
      <div className={styles.head}>
        <h3 id={titleId} className={chartStyles.chartTitle}>
          Session events and what-ifs
        </h3>
        <span className={styles.note}>{COMPUTED_LABEL}</span>
      </div>
      <dl className={styles.list}>
        {sessionEventLines(inputs, result).map((line) => (
          <EventRow key={line.key} line={line} />
        ))}
      </dl>
      <p className={chartStyles.chartCaption}>
        Breaks, the TTL and compaction change the estimate above; the tool-output and brevity levers do not. They are
        what-ifs against it. {DIVERGENCE_NOTE}
      </p>
    </section>
  )
}
