import { useCallback, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { copyWithFeedback } from '../utils/clipboard'
import { BenchmarkChart, type Benchmark } from '../components/home/BenchmarkChart'
import { CacheReadChart } from '../components/home/CacheReadChart'
import { PriceLadder } from '../components/home/PriceLadder'
import RevealSection from '../components/home/RevealSection'
import { staggerStyle, useCountUp, useInView } from '../components/home/hooks'
import {
  DEFAULT_CACHE_MULTIPLIER,
  cacheRows,
  cacheTierSummary,
  ladderRows,
  ladderSummary,
  tieredModel,
} from '../components/home/modelData'
import styles from './Home.module.css'

const INSTALL_CMD = 'npx skills add Sagargupta16/claude-cost-optimizer'
const COST_GUIDE = 'https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence'
const ANIM_BASE = `${import.meta.env.BASE_URL}anim/`

// Computed once from utils/pricing.ts; nothing on this page retypes a price.
const LADDER = ladderRows()
const CACHE = cacheRows()
const TIERED = tieredModel()

const features = [
  {
    title: 'Strips Filler',
    description: 'Drops pleasantries, hedging, restating your question, trailing summaries.',
    savings: 'not measured',
    tag: 'output',
  },
  {
    title: 'Model Routing',
    description: 'Suggests Haiku for simple tasks, Sonnet for standard work. Only Opus when justified.',
    savings: '1/40 per token',
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
    savings: '/clear is free',
    tag: 'input',
  },
  {
    title: 'Minimal Code Gen',
    description: 'Diffs over rewrites. No obvious comments. No speculative error handling.',
    savings: 'not measured',
    tag: 'output',
  },
  {
    title: 'Smart Deactivation',
    description: 'Full clarity for security warnings, destructive ops, and when you are confused.',
    savings: 'safety',
    tag: 'safe',
  },
]

const tagStyles: Record<string, string> = {
  output: styles.tagOutput,
  input: styles.tagInput,
  skip: styles.tagSkip,
  safe: styles.tagSafe,
}

const levels = [
  {
    name: '/cost-mode lite',
    savings: 'not measured',
    description: 'Professional brevity. Full sentences, no filler. Good for team-visible work.',
  },
  {
    name: '/cost-mode standard',
    savings: 'not measured',
    description: 'Default. Concise fragments OK. Skip articles where clear. Best daily driver.',
  },
  {
    name: '/cost-mode strict',
    savings: 'not measured',
    description: 'Telegraphic. Abbreviations, arrows for causality. Maximum brevity.',
  },
]
const DEFAULT_LEVEL = '/cost-mode standard'

const levers = [
  {
    title: 'Prompt caching',
    savings: '95% off',
    description: 'Cache hits bill at 0.05x input on Opus 5.5 and Sonnet 5.5 (0.1x on most other models). Automatic in Claude Code -- keep the prefix stable; a subscription main conversation keeps a 1-hour cache, an API key 5 minutes.',
    source: 'Anthropic',
    link: 'https://platform.claude.com/docs/en/build-with-claude/prompt-caching',
  },
  {
    title: 'Batch API',
    savings: 'flat 50%',
    description: 'Half price on input AND output for async work. Stacks with caching.',
    source: 'Anthropic',
    link: 'https://platform.claude.com/docs/en/build-with-claude/batch-processing',
  },
  {
    title: 'Model routing',
    savings: '40x',
    description: 'Haiku 5.5 costs 1/40 of Opus 5.5 per token while the prompt stays under 100K tokens. Anthropic measured it at 1/20 of Opus 5.5 per GPQA question (85% vs 91% accuracy).',
    source: 'Anthropic',
    link: COST_GUIDE,
  },
  {
    title: 'Context management',
    savings: '84%',
    description: "Context editing with the memory tool cut token use 84% in Anthropic's 100-turn agentic search eval. In Claude Code the levers are /compact, /clear and fresh sessions.",
    source: 'Anthropic',
    link: 'https://claude.com/blog/context-management',
  },
]

// Anthropic's published before/after runs, in dollars. Sources are linked under the chart.
const benchmarks: Benchmark[] = [
  { task: 'Cookbook agent, per task', before: 0.2906, after: 0.0223 },
  { task: 'Cache-busting prefix removed, per run', before: 4.24, after: 0.59 },
  { task: 'Memo -> one-line answers, per run', before: 1.4, after: 0.49 },
  { task: 'Low effort + retry at high, per task', before: 0.29, after: 0.17 },
]
const dollars = (v: number) => `$${v.toFixed(v < 0.1 ? 4 : 2)}`

const resources = [
  {
    title: '12 Optimization Guides',
    desc: 'From getting started to task routing, prompt caching, and speed-vs-cost deep dives.',
    link: 'https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/guides',
  },
  {
    title: '14 CLAUDE.md Templates',
    desc: 'Cost-optimized templates for React, Next.js, FastAPI, Go, Rust, Django, Rails, and more.',
    link: 'https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/templates/CLAUDE.md',
  },
  {
    title: '8 CLI Tools',
    desc: 'claude-rate setup grader, token estimator, usage analyzer, MCP cost server, VS Code extension, GitHub Action, and more.',
    link: 'https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/tools',
  },
]

const stats = [
  { num: 12, label: 'guides' },
  { num: 8, label: 'CLI tools' },
  { num: 14, label: 'templates' },
  { num: 4, label: 'skills planned' },
]

const toolLinks = [
  { to: '/calculator', title: 'Cost Calculator', desc: 'Estimate monthly spend and see where tokens go' },
  { to: '/badge', title: 'Badge Checker', desc: 'Score your setup and earn a grade badge' },
  { to: '/analyzer', title: 'Repo Analyzer', desc: 'Check a GitHub repo for cost leaks' },
]

const ctaLinks = [
  { label: 'GitHub', href: 'https://github.com/Sagargupta16/claude-cost-optimizer' },
  { label: 'Discussions', href: 'https://github.com/Sagargupta16/claude-cost-optimizer/discussions' },
  { label: 'Guides', href: 'https://github.com/Sagargupta16/claude-cost-optimizer/tree/main/guides' },
]

// cl100k_base counts of the two answers below (tiktoken); Claude 4.7+ tokenizers count about 30% more for both.
const VERBOSE_TOKENS = 72
const CONCISE_TOKENS = 13
const SAVED_PCT = Math.round((1 - CONCISE_TOKENS / VERBOSE_TOKENS) * 100)

function InstallBox() {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(() => {
    copyWithFeedback(INSTALL_CMD, setCopied)
  }, [])

  return (
    <div className={styles.installBox}>
      <span className={styles.prompt} aria-hidden="true">
        $
      </span>
      <code className={styles.installCmd}>{INSTALL_CMD}</code>
      <button type="button" onClick={handleCopy} className={styles.copyBtn} data-copied={copied}>
        {copied ? 'Copied' : 'Copy'}
      </button>
    </div>
  )
}

function SectionHead({ eyebrow, title, children }: Readonly<{ eyebrow: string; title: string; children?: ReactNode }>) {
  return (
    <header className={styles.sectionHead} data-stagger>
      <p className={styles.eyebrow}>{eyebrow}</p>
      <h2 className={styles.sectionTitle}>{title}</h2>
      {children}
    </header>
  )
}

function AnimFigure({
  file,
  alt,
  caption,
  index,
  wide = false,
}: Readonly<{ file: string; alt: string; caption: ReactNode; index: number; wide?: boolean }>) {
  return (
    <figure className={wide ? `${styles.figure} ${styles.figureWide}` : styles.figure} data-stagger style={staggerStyle(index)}>
      <div className={styles.figureMedia}>
        <img src={`${ANIM_BASE}${file}`} alt={alt} loading="lazy" decoding="async" className={styles.figureImg} />
      </div>
      <figcaption className={styles.figureCaption}>{caption}</figcaption>
    </figure>
  )
}

function Hero() {
  return (
    <section className={styles.hero}>
      <div className={styles.heroCopy}>
        <p className={styles.tagline}>Claude Code Skill</p>
        <h1 className={styles.title}>
          Cache reads at <span className={styles.accent}>5%</span> of input
        </h1>
        <p className={styles.subtitle}>
          An installable skill plus 12 guides, 14 templates, and 8 CLI tools
          that cut Claude Code costs through concise responses, model routing,
          prompt caching, and efficient workflow patterns.
        </p>
        <p className={styles.subtitleFine}>
          Every number here is sourced: cache reads at 5% of input on Opus 5.5
          and Sonnet 5.5, Haiku 5.5 at 1/40 of Opus 5.5 per token, Batch at 50% off.
        </p>

        <InstallBox />

        <p className={styles.installHint}>
          Then type <code>/cost-mode</code> in any session. Or in Claude Code: <code>/plugin marketplace add Sagargupta16/claude-cost-optimizer</code>
        </p>

        <nav className={styles.heroTools} aria-label="Site tools">
          {toolLinks.map((t) => (
            <Link key={t.to} to={t.to} className={styles.heroTool}>
              <span className={styles.heroToolTitle}>{t.title}</span>
              <span className={styles.heroToolDesc}>{t.desc}</span>
            </Link>
          ))}
        </nav>
      </div>

      <aside className={styles.heroCard} aria-labelledby="hero-ladder-title">
        <div className={styles.heroCardHead}>
          <span className={styles.liveDot} aria-hidden="true" />
          <span className={styles.heroCardKicker}>From the site's pricing table</span>
        </div>
        <h2 id="hero-ladder-title" className={styles.heroCardTitle}>
          Price per 1M tokens, current models
        </h2>
        <PriceLadder rows={LADDER} />
        <p className={styles.heroCardNote}>
          {TIERED && `${TIERED.name} is priced by prompt length, so it gets a row per tier. `}
          <Link to="/calculator">Price a full session in the calculator</Link>
        </p>
      </aside>
    </section>
  )
}

function TurnSection() {
  return (
    <RevealSection className={styles.section}>
      <SectionHead eyebrow="How billing works" title="What one turn actually bills">
        <p className={styles.sectionSub}>
          Every turn resends the conversation. What it costs depends on how much
          of that prompt is read from cache and how much is new.
        </p>
      </SectionHead>
      <AnimFigure
        file="token-flow.svg"
        index={1}
        wide
        alt="Animated diagram of how one Claude Code turn is billed: the stable prefix (system prompt, CLAUDE.md, tool names) and earlier history are read from the prompt cache, the fresh input is new, and output bills at 5x base input."
        caption="Everything the previous turn sent, history included, is read back from the cache. Only the fresh input is new (Claude Code writes it to the cache at 1.25x input), and output bills at the output rate."
      />
    </RevealSection>
  )
}

function TokenMeter({ tokens, tone, shown }: Readonly<{ tokens: number; tone: 'before' | 'after'; shown: boolean }>) {
  const fillClass = tone === 'after' ? styles.meterAfter : styles.meterBefore
  return (
    <svg className={styles.meter} viewBox="0 0 100 6" preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <rect width="100" height="6" className={styles.meterTrack} />
      <rect
        width={(tokens / VERBOSE_TOKENS) * 100}
        height="6"
        className={`${styles.meterFill} ${fillClass}`}
        style={{ transform: `scaleX(${shown ? 1 : 0})` }}
      />
    </svg>
  )
}

function DiffSection() {
  const ref = useRef<HTMLDivElement>(null)
  const shown = useInView(ref)
  return (
    <RevealSection className={styles.section}>
      <SectionHead eyebrow="Same answer, fewer tokens" title="Before vs After" />
      <div className={styles.diffGrid} ref={ref}>
        <div className={styles.diffCard} data-stagger style={staggerStyle(1)}>
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
            <div className={styles.diffFoot}>
              <TokenMeter tokens={VERBOSE_TOKENS} tone="before" shown={shown} />
              <p className={styles.diffMeta}>{VERBOSE_TOKENS} tokens</p>
            </div>
          </div>
        </div>
        <div className={styles.diffCard} data-stagger style={staggerStyle(2)}>
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
            <div className={styles.diffFoot}>
              <TokenMeter tokens={CONCISE_TOKENS} tone="after" shown={shown} />
              <p className={styles.diffMeta}>{CONCISE_TOKENS} tokens ({SAVED_PCT}% less)</p>
            </div>
          </div>
        </div>
      </div>
    </RevealSection>
  )
}

function FeaturesSection() {
  return (
    <RevealSection className={styles.section}>
      <SectionHead eyebrow="Inside the skill" title="What cost-mode Does" />
      <div className={styles.featuresGrid}>
        {features.map((f, i) => (
          <div key={f.title} className={styles.featureCard} data-tag={f.tag} data-stagger style={staggerStyle(i + 1)}>
            <div className={styles.featureHeader}>
              <h3 className={styles.featureTitle}>{f.title}</h3>
              <span className={`${styles.featureTag} ${tagStyles[f.tag] ?? ''}`}>
                {f.savings}
              </span>
            </div>
            <p className={styles.featureDesc}>{f.description}</p>
          </div>
        ))}
      </div>
    </RevealSection>
  )
}

function LevelMeter({ level, shown }: Readonly<{ level: number; shown: boolean }>) {
  return (
    <svg className={styles.levelMeter} viewBox="0 0 54 16" aria-hidden="true" focusable="false">
      {levels.map((l, i) => (
        <rect
          key={l.name}
          x={i * 19}
          y={10 - i * 5}
          width="14"
          height={6 + i * 5}
          rx="2"
          className={i <= level ? styles.levelSegOn : styles.levelSegOff}
          style={{ transform: `scaleY(${shown ? 1 : 0})`, transitionDelay: `${300 + i * 120}ms` }}
        />
      ))}
    </svg>
  )
}

function LevelsSection() {
  const ref = useRef<HTMLDivElement>(null)
  const shown = useInView(ref)
  return (
    <RevealSection className={styles.section}>
      <SectionHead eyebrow="Pick your intensity" title="Three Intensity Levels">
        <p className={styles.sectionSub}>
          None of the three is benchmarked. Closest measurement: Anthropic cut output
          tokens 39% and cost per run 14% by asking for shorter answers (
          <a href={COST_GUIDE} target="_blank" rel="noopener noreferrer">
            cost guide
          </a>
          ).
        </p>
      </SectionHead>
      <div className={styles.levelsGrid} ref={ref}>
        {levels.map((l, i) => (
          <div
            key={l.name}
            className={l.name === DEFAULT_LEVEL ? `${styles.levelCard} ${styles.levelActive}` : styles.levelCard}
            data-stagger
            style={staggerStyle(i + 1)}
          >
            <LevelMeter level={i} shown={shown} />
            <div className={styles.levelName}>{l.name}</div>
            <div className={styles.levelSavings}>{l.savings}</div>
            <p className={styles.levelDesc}>{l.description}</p>
          </div>
        ))}
      </div>
    </RevealSection>
  )
}

function PricingSection() {
  return (
    <RevealSection className={styles.section}>
      <SectionHead eyebrow="Pricing, visualized" title="Where the money goes">
        <p className={styles.sectionSub}>
          Two things set the bill before any optimization: which model answers,
          and how much of each prompt is read from cache.
        </p>
      </SectionHead>
      <div className={styles.figureGrid}>
        <AnimFigure
          file="cache-multipliers.svg"
          index={1}
          alt={`Animated chart of cache-read price as a share of fresh input: ${cacheTierSummary()}, and ${DEFAULT_CACHE_MULTIPLIER} on most older models.`}
          caption="A cache hit bills at a fraction of the fresh input price, and the fraction depends on the model."
        />
        <AnimFigure
          file="model-ladder.svg"
          index={2}
          alt={`Animated price ladder per million tokens: ${ladderSummary(LADDER)}.`}
          caption={
            TIERED
              ? `Each step up the ladder multiplies the per-token price. ${TIERED.name} changes rate once a prompt passes ${TIERED.line} tokens.`
              : 'Each step up the ladder multiplies the per-token price.'
          }
        />
      </div>
      <div className={styles.chartCard} data-stagger style={staggerStyle(3)}>
        <div className={styles.chartCardHead}>
          <h3 className={styles.chartCardTitle}>Cache-read price as a multiple of fresh input</h3>
          <p className={styles.chartCardSub}>Current models. Shorter is cheaper.</p>
        </div>
        <CacheReadChart rows={CACHE} />
        <p className={styles.chartCardNote}>
          Computed from the site's pricing table. Bars are scaled to the highest
          multiple shown; the track is that highest multiple.
        </p>
      </div>
    </RevealSection>
  )
}

function LeversSection() {
  return (
    <RevealSection className={styles.section}>
      <SectionHead eyebrow="Stack the levers" title="Measured levers">
        <p className={styles.sectionSub}>
          The skill trims visible output and suggests cheaper models; it has not
          been benchmarked. Each lever below is published by Anthropic and
          applies to its own slice of spend.
        </p>
      </SectionHead>
      <div className={styles.leversGrid}>
        {levers.map((l, i) => (
          <a
            key={l.title}
            href={l.link}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.leverCard}
            data-stagger
            style={staggerStyle(i + 1)}
          >
            <div className={styles.leverSavings}>{l.savings}</div>
            <h3 className={styles.leverTitle}>{l.title}</h3>
            <p className={styles.leverDesc}>{l.description}</p>
            <span className={styles.leverSource}>{l.source}</span>
          </a>
        ))}
      </div>
      <p className={styles.leversFine} data-stagger style={staggerStyle(5)}>
        No typical whole-workload figure has been published. Anthropic's one
        stacked measurement, its cookbook agent, cut cost per task 13x at the
        same pass rate.{' '}
        <a
          href="https://github.com/Sagargupta16/claude-cost-optimizer#how-far-can-you-actually-go"
          target="_blank"
          rel="noopener noreferrer"
        >
          Full evidence table
        </a>
      </p>
    </RevealSection>
  )
}

function BenchmarksSection() {
  return (
    <RevealSection className={styles.section}>
      <SectionHead eyebrow="Published runs" title="Before and After, in Dollars" />
      <div className={styles.chartCard} data-stagger style={staggerStyle(1)}>
        <BenchmarkChart rows={benchmarks} unit="USD per task or run" format={dollars} />
        <p className={styles.chartCardNote}>
          Each row is scaled to its own before. Row 1: Opus 5 at high effort, uncached, against
          Sonnet 5 at medium with cache breakpoints, 10/10 pass rate at both ends (Anthropic's{' '}
          <a href="https://platform.claude.com/cookbook/cost-optimization-cost-optimization" target="_blank" rel="noopener noreferrer">
            cost-optimization cookbook
          </a>
          ). Rows 2 to 4 are from Anthropic's{' '}
          <a href={COST_GUIDE} target="_blank" rel="noopener noreferrer">
            cost and intelligence guide
          </a>
          : a 25-token status line at the front of a triage agent's system prompt, a memo answer
          against a one-line one, and Opus 5.5 run all at high (95.3% pass) against low with
          failures re-run at high (about 97%).
        </p>
      </div>
    </RevealSection>
  )
}

function ResourcesSection() {
  return (
    <RevealSection className={styles.section}>
      <SectionHead eyebrow="Open source" title="What's in the Repo" />
      <div className={styles.toolsGrid}>
        {resources.map((r, i) => (
          <a
            key={r.title}
            href={r.link}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.toolCard}
            data-stagger
            style={staggerStyle(i + 1)}
          >
            <h3 className={styles.toolTitle}>{r.title}</h3>
            <p className={styles.toolDesc}>{r.desc}</p>
            <span className={styles.toolArrow}>View on GitHub</span>
          </a>
        ))}
      </div>
    </RevealSection>
  )
}

function StatItem({ num, label, index, shown }: Readonly<{ num: number; label: string; index: number; shown: boolean }>) {
  const value = useCountUp(num, shown, 900 + index * 150)
  return (
    <div className={styles.stat} data-stagger style={staggerStyle(index)}>
      <span className={styles.statNum}>{Math.round(value)}</span>
      <span className={styles.statLbl}>{label}</span>
    </div>
  )
}

function StatsBar() {
  const ref = useRef<HTMLDivElement>(null)
  const shown = useInView(ref)
  return (
    <RevealSection className={styles.statsSection} label="Repo at a glance">
      <div className={styles.statsBar} ref={ref}>
        {stats.map((s, i) => (
          <StatItem key={s.label} num={s.num} label={s.label} index={i} shown={shown} />
        ))}
      </div>
    </RevealSection>
  )
}

function Cta() {
  return (
    <RevealSection className={styles.cta}>
      <h2 className={styles.ctaTitle} data-stagger>
        Start saving tokens now
      </h2>
      <div className={styles.ctaInstall} data-stagger style={staggerStyle(1)}>
        <InstallBox />
      </div>
      <div className={styles.ctaLinks} data-stagger style={staggerStyle(2)}>
        {ctaLinks.map((l) => (
          <a key={l.label} href={l.href} target="_blank" rel="noopener noreferrer" className={styles.ctaLink}>
            {l.label}
          </a>
        ))}
      </div>
    </RevealSection>
  )
}

function Home() {
  return (
    <div className={styles.home}>
      <Hero />
      <TurnSection />
      <DiffSection />
      <FeaturesSection />
      <LevelsSection />
      <PricingSection />
      <LeversSection />
      <BenchmarksSection />
      <ResourcesSection />
      <StatsBar />
      <Cta />
    </div>
  )
}

export default Home
