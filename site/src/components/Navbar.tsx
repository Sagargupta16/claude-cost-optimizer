import styles from './Navbar.module.css'

function Navbar() {
  return (
    <nav className={styles.navbar}>
      <div className={styles.inner}>
        <a href="/" className={styles.logo}>
          Claude Cost Optimizer
        </a>
        <div className={styles.links}>
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
