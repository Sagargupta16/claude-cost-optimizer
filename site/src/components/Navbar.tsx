import { Link } from 'react-router-dom'
import styles from './Navbar.module.css'

function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.inner}>
        <Link to="/" className={styles.logo}>
          Claude Cost Optimizer
        </Link>
        <div className={styles.links}>
          <Link to="/calculator" className={styles.link}>
            Calculator
          </Link>
          <Link to="/badge" className={styles.link}>
            Badge
          </Link>
          <Link to="/analyzer" className={styles.link}>
            Analyzer
          </Link>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.link}
          >
            GitHub
          </a>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer/discussions"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.link}
          >
            Discussions
          </a>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
