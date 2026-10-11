import { useId } from 'react'
import styles from './RecommendationCards.module.css'

const PIPS = [1, 2, 3, 4, 5]

/**
 * calculate() returns recommendations already sorted by its impact estimate but exposes only
 * the text, so the meter shows that rank (more bars = higher in the list), not a magnitude.
 */
function ImpactMeter({ rank, total }: Readonly<{ rank: number; total: number }>) {
  const filled = total - rank + 1
  return (
    <div className={styles.meter}>
      <span className={styles.rank}>#{rank}</span>
      <span className={styles.pips} aria-hidden="true">
        {PIPS.slice(0, total).map((pip) => (
          <span key={pip} className={pip <= filled ? styles.pipOn : styles.pip} />
        ))}
      </span>
    </div>
  )
}

/** The text stays verbatim; the part before " -- " is set in bold as the card's lead. */
function RecommendationCard({ text, rank, total }: Readonly<{ text: string; rank: number; total: number }>) {
  const split = text.indexOf(' -- ')
  const lead = split > 0 ? text.slice(0, split) : text
  const rest = split > 0 ? text.slice(split) : ''
  return (
    <li
      className={rank === 1 ? `${styles.card} ${styles.cardTop}` : styles.card}
      style={{ animationDelay: `${rank * 90}ms` }}
    >
      <ImpactMeter rank={rank} total={total} />
      <p className={styles.text}>
        <strong className={styles.lead}>{lead}</strong>
        {rest}
      </p>
    </li>
  )
}

export function RecommendationCards({ recommendations }: Readonly<{ recommendations: string[] }>) {
  const titleId = useId()
  if (recommendations.length === 0) return null
  const total = recommendations.length
  return (
    <section className={styles.recs} aria-labelledby={titleId}>
      <div className={styles.head}>
        <h3 id={titleId} className={styles.title}>
          Top Recommendations
        </h3>
        <span className={styles.note}>Ranked by estimated impact</span>
      </div>
      <ol className={styles.list}>
        {recommendations.map((rec, index) => (
          <RecommendationCard key={rec} text={rec} rank={index + 1} total={total} />
        ))}
      </ol>
    </section>
  )
}
