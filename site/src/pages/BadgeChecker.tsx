import { useState, useMemo, useCallback, useId, useRef } from 'react'
import { scoreBadge, type BadgeInputs, type BadgeResult, type CategoryScore } from '../utils/badge'
import { copyWithFeedback } from '../utils/clipboard'
import { useCountUp, useInView } from '../components/home/hooks'
import styles from './BadgeChecker.module.css'

type NumberKey = 'claudeMdLines' | 'claudeMdTokens' | 'readDenyRules' | 'mcpServers'
type FlagKey = 'lockFilesCovered' | 'hasIgnoreFile' | 'hasModelConfigured' | 'hasCostControls'

const defaultInputs: BadgeInputs = {
  claudeMdLines: 100,
  claudeMdTokens: 1000,
  readDenyRules: 0,
  lockFilesCovered: false,
  hasIgnoreFile: false,
  hasModelConfigured: false,
  hasCostControls: false,
  mcpServers: 2,
}

interface NumberFieldSpec {
  key: NumberKey
  label: string
  max: number
  /** Step for the - / + buttons; typing any value still works. */
  step: number
}

const NUMBER_FIELDS: NumberFieldSpec[] = [
  { key: 'claudeMdLines', label: 'CLAUDE.md line count (0 = none)', max: 1000, step: 10 },
  { key: 'claudeMdTokens', label: 'CLAUDE.md tokens, root + .claude/ (about chars / 4)', max: 100000, step: 250 },
  { key: 'readDenyRules', label: 'File-read exclusions: Read(...) rules in permissions.deny', max: 100, step: 1 },
  { key: 'mcpServers', label: 'MCP servers', max: 20, step: 1 },
]

interface FlagFieldSpec {
  key: FlagKey
  label: string
  /** Extra text shown only while the box is ticked. */
  whenChecked?: string
}

const FLAG_FIELDS: FlagFieldSpec[] = [
  { key: 'lockFilesCovered', label: 'Every lock file at the repo root has a Read deny rule (or there are none)' },
  {
    key: 'hasIgnoreFile',
    label: 'Project has a .claudeignore',
    whenChecked: ' -- not read by Claude Code, scores nothing. Move its patterns into permissions.deny as Read(...) rules.',
  },
  { key: 'hasModelConfigured', label: 'Default model configured' },
  {
    key: 'hasCostControls',
    label: 'Cost controls set (effortLevel, fastMode: false, autoCompactEnabled, or enforceAvailableModels)',
  },
]

/** Full marks green, 60% or more yellow, below that red. */
function progressColor(score: number, maxScore: number): string {
  if (score === maxScore) return 'var(--accent-green)'
  if (score >= maxScore * 0.6) return 'var(--warning-yellow)'
  return 'var(--error-red)'
}

function StepIcon({ plus }: Readonly<{ plus: boolean }>) {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true" focusable="false">
      <path d="M3 8h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      {plus && <path d="M8 3v10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />}
    </svg>
  )
}

function NumberField({
  spec,
  value,
  onValue,
}: Readonly<{ spec: NumberFieldSpec; value: number; onValue: (key: NumberKey, value: number) => void }>) {
  const id = useId()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number.parseInt(e.target.value, 10)
    if (!Number.isNaN(val) && val >= 0) {
      onValue(spec.key, val)
    }
  }

  const nudge = (direction: number) => {
    onValue(spec.key, Math.min(spec.max, Math.max(0, value + direction * spec.step)))
  }

  return (
    <div className={styles.inputLabel}>
      <label htmlFor={id}>{spec.label}</label>
      <div className={styles.numberRow}>
        <button
          type="button"
          className={styles.stepBtn}
          onClick={() => nudge(-1)}
          disabled={value <= 0}
          aria-label={`Decrease: ${spec.label}`}
        >
          <StepIcon plus={false} />
        </button>
        <input
          id={id}
          type="number"
          inputMode="numeric"
          min={0}
          max={spec.max}
          value={value}
          onChange={handleChange}
          className={styles.numberInput}
        />
        <button
          type="button"
          className={styles.stepBtn}
          onClick={() => nudge(1)}
          disabled={value >= spec.max}
          aria-label={`Increase: ${spec.label}`}
        >
          <StepIcon plus />
        </button>
      </div>
    </div>
  )
}

function FlagField({
  spec,
  checked,
  onFlag,
}: Readonly<{ spec: FlagFieldSpec; checked: boolean; onFlag: (key: FlagKey, value: boolean) => void }>) {
  return (
    <label className={styles.checkboxLabel}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onFlag(spec.key, e.target.checked)}
        className={styles.checkbox}
      />
      <span>
        {spec.label}
        {checked && spec.whenChecked}
      </span>
    </label>
  )
}

function InputPanel({
  inputs,
  onNumber,
  onFlag,
}: Readonly<{
  inputs: BadgeInputs
  onNumber: (key: NumberKey, value: number) => void
  onFlag: (key: FlagKey, value: boolean) => void
}>) {
  return (
    <div className={styles.inputPanel}>
      <h2 className={styles.panelTitle}>Your Setup</h2>
      {NUMBER_FIELDS.map((spec) => (
        <NumberField key={spec.key} spec={spec} value={inputs[spec.key]} onValue={onNumber} />
      ))}
      <div className={styles.checkboxGroup}>
        {FLAG_FIELDS.map((spec) => (
          <FlagField key={spec.key} spec={spec} checked={inputs[spec.key]} onFlag={onFlag} />
        ))}
      </div>
    </div>
  )
}

// Ring geometry: one quarter of the circle per category, clockwise from the top.
const RING_R = 56
const RING_C = 2 * Math.PI * RING_R
const SEGMENT_GAP_DEG = 5

function RingSegment({
  cat,
  index,
  count,
  shown,
}: Readonly<{ cat: CategoryScore; index: number; count: number; shown: boolean }>) {
  const spanDeg = 360 / count
  const segLen = (RING_C * (spanDeg - SEGMENT_GAP_DEG)) / 360
  const share = shown ? cat.score / cat.maxScore : 0
  const rotate = `rotate(${-90 + index * spanDeg + SEGMENT_GAP_DEG / 2} 70 70)`
  return (
    <>
      <circle
        cx="70"
        cy="70"
        r={RING_R}
        className={styles.ringTrack}
        transform={rotate}
        style={{ strokeDasharray: `${segLen} ${RING_C}` }}
      />
      <circle
        cx="70"
        cy="70"
        r={RING_R}
        className={styles.ringFill}
        transform={rotate}
        style={{
          stroke: progressColor(cat.score, cat.maxScore),
          strokeDasharray: `${segLen} ${RING_C}`,
          strokeDashoffset: segLen * (1 - share),
          transitionDelay: `${index * 140}ms`,
        }}
      />
    </>
  )
}

function GradeRing({ result, shown }: Readonly<{ result: BadgeResult; shown: boolean }>) {
  const score = Math.round(useCountUp(result.totalScore, shown, 900))
  const summary = result.categories.map((c) => `${c.name} ${c.score} of ${c.maxScore}`).join(', ')
  return (
    <svg
      viewBox="0 0 140 140"
      className={styles.ring}
      role="img"
      aria-label={`Grade ${result.grade}, ${result.totalScore} out of 100. ${summary}.`}
    >
      {result.categories.map((cat, i) => (
        <RingSegment key={cat.name} cat={cat} index={i} count={result.categories.length} shown={shown} />
      ))}
      <text key={result.grade} x="70" y="74" textAnchor="middle" className={styles.ringGrade} style={{ fill: result.gradeColor }}>
        {result.grade}
      </text>
      <text x="70" y="96" textAnchor="middle" className={styles.ringScore}>
        {score} / 100
      </text>
    </svg>
  )
}

function CategoryRow({ cat, index, shown }: Readonly<{ cat: CategoryScore; index: number; shown: boolean }>) {
  const missing = cat.maxScore - cat.score
  const color = progressColor(cat.score, cat.maxScore)
  return (
    <li className={styles.category}>
      <div className={styles.categoryHeader}>
        <span className={styles.categoryName}>
          <span className={styles.categoryDot} style={{ backgroundColor: color }} aria-hidden="true" />
          {cat.name}
        </span>
        <span className={styles.categoryScore}>
          {cat.score} / {cat.maxScore}
        </span>
      </div>
      <div className={styles.progressBar} aria-hidden="true">
        <div
          className={styles.progressFill}
          style={{
            transform: `scaleX(${shown ? cat.score / cat.maxScore : 0})`,
            backgroundColor: color,
            transitionDelay: `${index * 90}ms`,
          }}
        />
      </div>
      {missing > 0 && <span className={styles.categoryGap}>+{missing} points available</span>}
    </li>
  )
}

function ScoreSummary({ result, shown }: Readonly<{ result: BadgeResult; shown: boolean }>) {
  return (
    <div className={styles.summary}>
      <div className={styles.ringWrap}>
        <GradeRing result={result} shown={shown} />
        <p className={styles.ringCaption}>One quarter per category, clockwise from the top.</p>
      </div>
      <div className={styles.breakdown}>
        <h3 className={styles.subTitle}>Score Breakdown</h3>
        <ul className={styles.categories}>
          {result.categories.map((cat, i) => (
            <CategoryRow key={cat.name} cat={cat} index={i} shown={shown} />
          ))}
        </ul>
      </div>
    </div>
  )
}

function BadgePreview({
  result,
  copied,
  onCopy,
}: Readonly<{ result: BadgeResult; copied: boolean; onCopy: () => void }>) {
  return (
    <div className={styles.badgeBlock}>
      <h3 className={styles.subTitle}>Badge Preview</h3>
      <div className={styles.badgePreview}>
        <img key={result.badgeUrl} src={result.badgeUrl} alt={`Grade: ${result.grade}`} className={styles.badgeImg} />
      </div>
      <pre className={styles.markdown}>
        <code>{result.badgeMarkdown}</code>
      </pre>
      <button type="button" onClick={onCopy} className={styles.copyButton} data-copied={copied}>
        {copied ? 'Copied!' : 'Copy Badge Markdown'}
      </button>
    </div>
  )
}

function Recommendations({ categories }: Readonly<{ categories: CategoryScore[] }>) {
  const active = categories.filter((c) => c.recommendation)
  if (active.length === 0) {
    return <p className={styles.allClear}>No recommendations: every category is at full marks.</p>
  }
  return (
    <div>
      <h3 className={styles.subTitle}>Recommendations</h3>
      <ul className={styles.recommendations}>
        {active.map((cat, i) => (
          <li key={cat.name} className={styles.recommendation} style={{ animationDelay: `${i * 70}ms` }}>
            <strong>{cat.name}:</strong> {cat.recommendation}
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Phone-only floating score, so the grade stays visible while editing inputs. */
function MobileScore({ result, hidden }: Readonly<{ result: BadgeResult; hidden: boolean }>) {
  return (
    <a
      href="#badge-result"
      className={styles.mobileScore}
      data-hidden={hidden}
      aria-hidden={hidden}
      tabIndex={hidden ? -1 : 0}
    >
      <span key={result.grade} className={styles.mobileGrade} style={{ color: result.gradeColor }}>
        {result.grade}
      </span>
      <span className={styles.mobileTotal}>{result.totalScore} / 100</span>
      <span className={styles.mobileJump}>See breakdown</span>
    </a>
  )
}

function BadgeChecker() {
  const [inputs, setInputs] = useState<BadgeInputs>(defaultInputs)
  const [copied, setCopied] = useState(false)
  const resultRef = useRef<HTMLDivElement>(null)
  const shown = useInView(resultRef)
  const resultVisible = useInView(resultRef, { rootMargin: '0px', threshold: 0, once: false })

  const result = useMemo(() => scoreBadge(inputs), [inputs])

  const setNumber = useCallback((key: NumberKey, value: number) => {
    setInputs((prev) => ({ ...prev, [key]: value }))
  }, [])

  const setFlag = useCallback((key: FlagKey, value: boolean) => {
    setInputs((prev) => ({ ...prev, [key]: value }))
  }, [])

  const handleCopy = useCallback(() => {
    copyWithFeedback(result.badgeMarkdown, setCopied)
  }, [result.badgeMarkdown])

  return (
    <div className={styles.checker}>
      <header className={styles.head}>
        <p className={styles.eyebrow}>Setup grade</p>
        <h1 className={styles.title}>Badge Checker</h1>
        <p className={styles.subtitle}>
          Score your Claude Code setup and earn a grade badge for your repo.
        </p>
      </header>

      <div className={styles.grid}>
        <InputPanel inputs={inputs} onNumber={setNumber} onFlag={setFlag} />

        <div id="badge-result" ref={resultRef} className={styles.outputPanel}>
          <ScoreSummary result={result} shown={shown} />
          <BadgePreview result={result} copied={copied} onCopy={handleCopy} />
          <Recommendations categories={result.categories} />
        </div>
      </div>

      <MobileScore result={result} hidden={resultVisible} />
    </div>
  )
}

export default BadgeChecker
