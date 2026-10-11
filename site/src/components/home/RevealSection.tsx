import { useRef, type ReactNode } from 'react'
import { useInView } from './hooks'
import styles from './RevealSection.module.css'

/**
 * A page section whose `data-stagger` children fade up in sequence once it
 * scrolls into view (stagger order comes from staggerStyle(i)).
 */
function RevealSection({
  className,
  children,
  id,
  label,
}: Readonly<{ className?: string; children: ReactNode; id?: string; label?: string }>) {
  const ref = useRef<HTMLElement>(null)
  const inView = useInView(ref)
  const classes = [styles.reveal, inView ? styles.in : '', className ?? ''].filter(Boolean).join(' ')
  return (
    <section ref={ref} id={id} aria-label={label} className={classes}>
      {children}
    </section>
  )
}

export default RevealSection
