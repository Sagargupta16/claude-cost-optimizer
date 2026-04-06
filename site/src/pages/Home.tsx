import { useState, useCallback } from 'react'
import styles from './Home.module.css'

const INSTALL_CMD = 'npx skills add Sagargupta16/claude-cost-optimizer'

const features = [
  {
    title: 'Strips Filler',
    description: 'Drops pleasantries, hedging, restating your question, trailing summaries.',
    savings: '40-60%',
    tag: 'output',
  },
  {
    title: 'Model Routing',
    description: 'Suggests Haiku for simple tasks, Sonnet for standard work. Only Opus when justified.',
    savings: '20-40%',
    tag: 'input',
  },
  {
    title: 'CLI Over LLM',
    description: 'Points to prettier, eslint --fix, git instead of burning tokens on deterministic tasks.',
    savings: '100%',
    tag: 'skip',
  },
  {
    title: 'Session Aware',
    description: 'Reminds to /compact after 20+ turns. Suggests fresh sessions for new tasks.',
    savings: '10-20%',
    tag: 'input',
  },
  {
    title: 'Minimal Code Gen',
    description: 'Diffs over rewrites. No obvious comments. No speculative error handling.',
    savings: '15-30%',
    tag: 'output',
  },
  {
    title: 'Smart Deactivation',
    description: 'Full clarity for security warnings, destructive ops, and when you are confused.',
    savings: 'safety',
    tag: 'safe',
  },
]

const benchmarks = [
  { task: 'React re-render bug', before: 1180, after: 350 },
  { task: 'Auth middleware fix', before: 704, after: 210 },
  { task: 'PostgreSQL setup', before: 2347, after: 700 },
  { task: 'Docker multi-stage', before: 1042, after: 310 },
  { task: 'Error boundary', before: 3454, after: 1040 },
]

const resources = [
  {
    title: '10 Optimization Guides',
    desc: 'From getting started to three-tier task routing and prompt caching deep dives.',
    link: 'https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/guides',
  },
  {
    title: '10 CLAUDE.md Templates',
    desc: 'Cost-optimized templates for React, Next.js, FastAPI, Go, Rust, Django, Rails, and more.',
    link: 'https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/templates/CLAUDE.md',
  },
  {
    title: '7 CLI Tools',
    desc: 'Token estimator, usage analyzer, badge generator, MCP server, budget hooks, and more.',
    link: 'https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/tools',
  },
]

function Home() {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(INSTALL_CMD).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [])

  const maxTokens = Math.max(...benchmarks.map((b) => b.before))

  return (
    <div className={styles.home}>
      {/* Hero */}
      <section className={styles.hero}>
        <p className={styles.tagline}>Claude Code Skill</p>
        <h1 className={styles.title}>
          Save <span className={styles.accent}>30-60%</span> on costs
        </h1>
        <p className={styles.subtitle}>
          An installable skill that cuts Claude Code costs through concise
          responses, model routing, and efficient workflow patterns.
          10 guides, templates, and CLI tools included.
        </p>

        <div className={styles.installBox}>
          <code className={styles.installCmd}>{INSTALL_CMD}</code>
          <button onClick={handleCopy} className={styles.copyBtn}>
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>

        <p className={styles.installHint}>
          Then type <code>/cost-mode</code> in any session. Or in Claude Code: <code>/plugin marketplace add Sagargupta16/claude-cost-optimizer</code>
        </p>
      </section>

      {/* Before / After */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Before vs After</h2>
        <div className={styles.diffGrid}>
          <div className={styles.diffCard}>
            <div className={styles.diffLabel}>Without cost-mode</div>
            <div className={styles.diffContent}>
              <p className={styles.diffLine}>
                <span className={styles.diffDel}>
                  Sure! I'd be happy to help with that. The reason your
                  component is re-rendering is because you're creating a new
                  object reference on each render. When you pass an inline
                  object as a prop, React sees it as a new value every time and
                  triggers a re-render. I'd recommend wrapping it in useMemo to
                  maintain referential equality between renders.
                </span>
              </p>
              <p className={styles.diffMeta}>69 tokens</p>
            </div>
          </div>
          <div className={styles.diffCard}>
            <div className={`${styles.diffLabel} ${styles.diffLabelGreen}`}>
              With cost-mode
            </div>
            <div className={styles.diffContent}>
              <p className={styles.diffLine}>
                <span className={styles.diffAdd}>
                  Inline object prop = new ref each render. Wrap in{' '}
                  <code>useMemo</code>.
                </span>
              </p>
              <p className={styles.diffMeta}>14 tokens (80% less)</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What cost-mode Does</h2>
        <div className={styles.featuresGrid}>
          {features.map((f) => {
            const tagStyles: Record<string, string> = {
              output: styles.tagOutput,
              input: styles.tagInput,
              skip: styles.tagSkip,
              safe: styles.tagSafe,
            }
            return (
              <div key={f.title} className={styles.featureCard}>
                <div className={styles.featureHeader}>
                  <h3 className={styles.featureTitle}>{f.title}</h3>
                  <span className={`${styles.featureTag} ${tagStyles[f.tag] ?? ''}`}>
                    {f.savings}
                  </span>
                </div>
                <p className={styles.featureDesc}>{f.description}</p>
              </div>
            )
          })}
        </div>
      </section>

      {/* Intensity Levels */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Three Intensity Levels (Output Token Reduction)</h2>
        <div className={styles.levelsGrid}>
          <div className={styles.levelCard}>
            <div className={styles.levelName}>/cost-mode lite</div>
            <div className={styles.levelSavings}>20-40%</div>
            <p className={styles.levelDesc}>
              Professional brevity. Full sentences, no filler. Good for
              team-visible work.
            </p>
          </div>
          <div className={`${styles.levelCard} ${styles.levelActive}`}>
            <div className={styles.levelName}>/cost-mode standard</div>
            <div className={styles.levelSavings}>40-60%</div>
            <p className={styles.levelDesc}>
              Default. Concise fragments OK. Skip articles where clear. Best
              daily driver.
            </p>
          </div>
          <div className={styles.levelCard}>
            <div className={styles.levelName}>/cost-mode strict</div>
            <div className={styles.levelSavings}>60-70%</div>
            <p className={styles.levelDesc}>
              Telegraphic. Abbreviations, arrows for causality. Maximum
              savings.
            </p>
          </div>
        </div>
      </section>

      {/* Benchmarks */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Token Reduction by Task</h2>
        <div className={styles.benchmarks}>
          {benchmarks.map((b) => {
            const reduction = Math.round(
              ((b.before - b.after) / b.before) * 100,
            )
            return (
              <div key={b.task} className={styles.benchRow}>
                <span className={styles.benchTask}>{b.task}</span>
                <div className={styles.benchBars}>
                  <div
                    className={styles.benchBarBefore}
                    style={{ width: `${(b.before / maxTokens) * 100}%` }}
                  >
                    <span className={styles.benchVal}>{b.before}</span>
                  </div>
                  <div
                    className={styles.benchBarAfter}
                    style={{ width: `${(b.after / maxTokens) * 100}%` }}
                  >
                    <span className={styles.benchVal}>{b.after}</span>
                  </div>
                </div>
                <span className={styles.benchPct}>-{reduction}%</span>
              </div>
            )
          })}
          <div className={styles.benchLegend}>
            <span className={styles.legendBefore}>Before</span>
            <span className={styles.legendAfter}>After</span>
            <span className={styles.legendUnit}>output tokens</span>
          </div>
        </div>
      </section>

      {/* Resources */}
      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>What's in the Repo</h2>
        <div className={styles.toolsGrid}>
          {resources.map((r) => (
            <a
              key={r.title}
              href={r.link}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.toolCard}
            >
              <h3 className={styles.toolTitle}>{r.title}</h3>
              <p className={styles.toolDesc}>{r.desc}</p>
              <span className={styles.toolArrow}>View on GitHub</span>
            </a>
          ))}
        </div>
      </section>

      {/* Stats */}
      <section className={styles.statsBar}>
        <div className={styles.stat}>
          <span className={styles.statNum}>10</span>
          <span className={styles.statLbl}>guides</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statNum}>7</span>
          <span className={styles.statLbl}>CLI tools</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statNum}>10</span>
          <span className={styles.statLbl}>templates</span>
        </div>
        <div className={styles.stat}>
          <span className={styles.statNum}>5</span>
          <span className={styles.statLbl}>skills planned</span>
        </div>
      </section>

      {/* CTA */}
      <section className={styles.cta}>
        <h2 className={styles.ctaTitle}>Start saving tokens now</h2>
        <div className={styles.installBox}>
          <code className={styles.installCmd}>{INSTALL_CMD}</code>
          <button onClick={handleCopy} className={styles.copyBtn}>
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
        <div className={styles.ctaLinks}>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.ctaLink}
          >
            GitHub
          </a>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer/discussions"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.ctaLink}
          >
            Discussions
          </a>
          <a
            href="https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/guides"
            target="_blank"
            rel="noopener noreferrer"
            className={styles.ctaLink}
          >
            Guides
          </a>
        </div>
      </section>
    </div>
  )
}

export default Home
