import { useCallback, useEffect, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import LogoMark from './home/LogoMark'
import styles from './Navbar.module.css'

const ROUTES = [
  { to: '/calculator', label: 'Calculator' },
  { to: '/badge', label: 'Badge' },
  { to: '/analyzer', label: 'Analyzer' },
]

const EXTERNAL = [
  { href: 'https://github.com/Sagargupta16/claude-cost-optimizer', label: 'GitHub' },
  { href: 'https://github.com/Sagargupta16/claude-cost-optimizer/discussions', label: 'Discussions' },
]

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive ? `${styles.link} ${styles.active}` : styles.link
}

function Navbar() {
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  const toggle = useCallback(() => setOpen((o) => !o), [])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <nav className={styles.navbar} aria-label="Main">
      <div className={styles.inner}>
        <Link to="/" className={styles.logo} onClick={close}>
          <LogoMark className={styles.logoMark} />
          <span>Claude Cost Optimizer</span>
        </Link>

        <button
          type="button"
          className={styles.menuBtn}
          aria-expanded={open}
          aria-controls="site-nav-links"
          aria-label={open ? 'Close menu' : 'Open menu'}
          data-open={open}
          onClick={toggle}
        >
          <span className={styles.menuBar} />
          <span className={styles.menuBar} />
          <span className={styles.menuBar} />
        </button>

        <div id="site-nav-links" className={styles.links} data-open={open}>
          {ROUTES.map((r) => (
            <NavLink key={r.to} to={r.to} className={navClass} onClick={close}>
              {r.label}
            </NavLink>
          ))}
          <span className={styles.divider} aria-hidden="true" />
          {EXTERNAL.map((l) => (
            <a
              key={l.href}
              href={l.href}
              target="_blank"
              rel="noopener noreferrer"
              className={`${styles.link} ${styles.external}`}
              onClick={close}
            >
              {l.label}
            </a>
          ))}
        </div>
      </div>
    </nav>
  )
}

export default Navbar
