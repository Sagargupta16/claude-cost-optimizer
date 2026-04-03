import styles from './Footer.module.css'

function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.inner}>
        <div className={styles.links}>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/guides"
            target="_blank"
            rel="noopener noreferrer"
          >
            Guides
          </a>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer/blob/main/CONTRIBUTING.md"
            target="_blank"
            rel="noopener noreferrer"
          >
            Contributing
          </a>
        </div>
        <p className={styles.license}>
          MIT License. Built for the Claude Code community.
        </p>
      </div>
    </footer>
  )
}

export default Footer
