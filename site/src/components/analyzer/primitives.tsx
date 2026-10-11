import { type ReactNode, useCallback, useState } from 'react'
import { copyWithFeedback } from '../../utils/clipboard'
import { useCountUp } from './hooks'
import { type Health } from './status'
import styles from './analyzer.module.css'

export function Panel({
  title,
  aside,
  children,
}: Readonly<{ title: string; aside?: ReactNode; children: ReactNode }>) {
  return (
    <section className={styles.panel}>
      <header className={styles.panelHead}>
        <h2 className={styles.panelTitle}>{title}</h2>
        {aside}
      </header>
      {children}
    </section>
  )
}

export function StatRow({
  label,
  value,
  health,
}: Readonly<{ label: ReactNode; value: ReactNode; health?: Health }>) {
  const valueClass = health ? `${styles.statValue} ${styles[health]}` : styles.statValue
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <span className={valueClass}>
        {health && <span className={styles.dot} aria-hidden="true" />}
        {value}
      </span>
    </div>
  )
}

/** Up to `limit` entries as chips, then a "+N more" count. */
export function EntryChips({ items, limit }: Readonly<{ items: string[]; limit: number }>) {
  const unique = [...new Set(items)]
  const hidden = unique.length - limit
  return (
    <div className={styles.entryList}>
      {unique.slice(0, limit).map((item, i) => (
        <code key={item} className={styles.entry} style={{ animationDelay: `${i * 40}ms` }}>
          {item}
        </code>
      ))}
      {hidden > 0 && <span className={styles.moreEntries}>+{hidden} more</span>}
    </div>
  )
}

/** A number that counts up from zero, with a label under it. */
export function StatTile({
  label,
  value,
  suffix,
}: Readonly<{ label: string; value: number; suffix?: string }>) {
  const shown = useCountUp(value, 1000)
  return (
    <div className={styles.tile}>
      <span className={styles.tileValue}>
        {Math.round(shown).toLocaleString()}
        {suffix && <span className={styles.tileSuffix}>{suffix}</span>}
      </span>
      <span className={styles.tileLabel}>{label}</span>
    </div>
  )
}

/** Circle with a check (good) or an exclamation mark, stroke drawn in on mount. */
export function StatusIcon({ health }: Readonly<{ health: Health }>) {
  const mark = health === 'good' ? 'M7 12.5l3.2 3.2L17 9' : 'M12 7v6.5M12 16.8v.2'
  return (
    <svg className={`${styles.statusIcon} ${styles[health]}`} viewBox="0 0 24 24" aria-hidden="true">
      <circle cx={12} cy={12} r={10} />
      <path d={mark} pathLength={1} className={styles.statusMark} />
    </svg>
  )
}

export function CopyButton({
  text,
  label,
  doneLabel,
}: Readonly<{ text: string; label: string; doneLabel: string }>) {
  const [copied, setCopied] = useState(false)
  const handleClick = useCallback(() => copyWithFeedback(text, setCopied), [text])
  return (
    <button
      type="button"
      onClick={handleClick}
      className={copied ? `${styles.button} ${styles.buttonDone}` : styles.button}
    >
      {copied ? doneLabel : label}
    </button>
  )
}
