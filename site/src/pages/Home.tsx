import { Link } from 'react-router-dom'
import styles from './Home.module.css'

const quickWins = [
  {
    title: 'Keep CLAUDE.md under 4,000 characters',
    savings: '10-20%',
    description:
      'Content beyond 4,000 characters per file is silently truncated. Total budget across all instruction files: 12,000 characters.',
  },
  {
    title: 'Use Haiku for simple tasks',
    savings: '20-40%',
    description:
      'Tests, docs, formatting, and boilerplate do not need Opus. Delegate to Haiku 4.5 at $1/$5 per 1M tokens.',
  },
  {
    title: 'Use Plan Mode before coding',
    savings: '15-25%',
    description:
      'Planning upfront reduces back-and-forth turns. Fewer turns means less cumulative history cost.',
  },
  {
    title: 'Add .claudeignore',
    savings: '5-15%',
    description:
      'Exclude build outputs, node_modules, lock files, and generated code from context to reduce file read tokens.',
  },
  {
    title: 'Delegate to subagents',
    savings: '20-40%',
    description:
      'Subagents get fresh context windows. They avoid the ballooning history cost of long main sessions.',
  },
]

const tools = [
  {
    title: 'Repo Analyzer',
    description: 'Paste a GitHub repo URL to get a full cost audit, grade, and recommendations.',
    link: '/analyzer',
    internal: true,
  },
  {
    title: 'Cost Calculator',
    description: 'Estimate your monthly Claude costs and see exactly where tokens go.',
    link: '/calculator',
    internal: true,
  },
  {
    title: 'Badge Checker',
    description: 'Score your setup, get a grade, and earn a shields.io badge for your repo.',
    link: '/badge',
    internal: true,
  },
  {
    title: 'GitHub Repository',
    description: '9 guides, CLI tools, templates, benchmarks, and community contributions.',
    link: 'https://github.com/Sagargupta16/claude-cost-optimizer',
    internal: false,
  },
]

const whatsInside = [
  { count: 10, label: 'optimization guides' },
  { count: 7, label: 'CLI tools and scripts' },
  { count: 10, label: 'ready-to-use templates' },
  { count: 3, label: 'real-world benchmarks' },
]

function Home() {
  return (
    <div className={styles.home}>
      <section className={styles.hero}>
        <h1 className={styles.title}>Claude Cost Optimizer</h1>
        <p className={styles.subtitle}>
          Save 30-60% on Claude Code costs with proven strategies, real
          benchmarks, and ready-to-use tools.
        </p>
        <div className={styles.heroCtas}>
          <Link to="/calculator" className={styles.primaryCta}>
            Open Calculator
          </Link>
          <Link to="/analyzer" className={styles.secondaryCta}>
            Analyze Your Repo
          </Link>
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Quick Wins</h2>
        <div className={styles.quickWinsGrid}>
          {quickWins.map((win) => (
            <div key={win.title} className={styles.quickWinCard}>
              <div className={styles.quickWinHeader}>
                <h3 className={styles.quickWinTitle}>{win.title}</h3>
                <span className={styles.savingsBadge}>{win.savings}</span>
              </div>
              <p className={styles.quickWinDesc}>{win.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Tools</h2>
        <div className={styles.toolsGrid}>
          {tools.map((tool) => (
            <div key={tool.title} className={styles.toolCard}>
              <h3 className={styles.toolTitle}>{tool.title}</h3>
              <p className={styles.toolDesc}>{tool.description}</p>
              {tool.internal ? (
                <Link to={tool.link} className={styles.toolLink}>
                  Open tool
                </Link>
              ) : (
                <a
                  href={tool.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={styles.toolLink}
                >
                  View on GitHub
                </a>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What's Inside</h2>
        <div className={styles.statsGrid}>
          {whatsInside.map((item) => (
            <div key={item.label} className={styles.statCard}>
              <span className={styles.statNumber}>{item.count}</span>
              <span className={styles.statLabel}>{item.label}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

export default Home
