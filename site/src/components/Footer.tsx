import { Link } from 'react-router-dom'
import LogoMark from './home/LogoMark'
import styles from './Footer.module.css'

const TOOLS = [
  { to: '/calculator', label: 'Cost Calculator' },
  { to: '/badge', label: 'Badge Checker' },
  { to: '/analyzer', label: 'Repo Analyzer' },
]

const PROJECT = [
  { href: 'https://github.com/Sagargupta16/claude-cost-optimizer', label: 'GitHub' },
  { href: 'https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/guides', label: 'Guides' },
  { href: 'https://github.com/Sagargupta16/claude-cost-optimizer/blob/main/CONTRIBUTING.md', label: 'Contributing' },
  { href: 'https://github.com/Sagargupta16/claude-cost-optimizer/discussions', label: 'Discussions' },
]

function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.brand}>
          <Link to="/" className={styles.brandLink}>
            <LogoMark />
            <span>Claude Cost Optimizer</span>
          </Link>
          <p className={styles.blurb}>
            An installable Claude Code skill plus guides, templates and tools for
            spending fewer tokens.
          </p>
        </div>

        <nav className={styles.cols} aria-label="Footer">
          <div className={styles.col}>
            <p className={styles.colTitle}>Tools</p>
            <ul className={styles.list}>
              {TOOLS.map((t) => (
                <li key={t.to}>
                  <Link to={t.to} className={styles.link}>
                    {t.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div className={styles.col}>
            <p className={styles.colTitle}>Project</p>
            <ul className={styles.list}>
              {PROJECT.map((p) => (
                <li key={p.href}>
                  <a href={p.href} target="_blank" rel="noopener noreferrer" className={styles.link}>
                    {p.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </nav>
      </div>

      <div className={styles.bottom}>
        <p className={styles.license}>
          MIT License. Built for the Claude Code community.
        </p>
      </div>
    </footer>
  )
}

export default Footer
