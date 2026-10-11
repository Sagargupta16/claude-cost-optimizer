import type { AnalysisResult } from '../../utils/repoAnalyzer'
import { useCountUp } from './hooks'
import { Panel, StatRow } from './primitives'
import { HEALTH_COLOR, type Health } from './status'
import styles from './analyzer.module.css'

// Anthropic's guidance: "target under 200 lines per CLAUDE.md file".
const CLAUDE_MD_LINE_GUIDANCE = 200

type ClaudeMd = AnalysisResult['claudeMd']
type ClaudeMdAll = AnalysisResult['claudeMdAll']

function lineHealth(lineCount: number): Health {
  if (lineCount > CLAUDE_MD_LINE_GUIDANCE) return 'bad'
  if (lineCount > 100) return 'warn'
  return 'good'
}

/** Fill to the line count on a scale that always leaves room past the 200-line mark. */
function LineMeter({ lineCount }: Readonly<{ lineCount: number }>) {
  const scaleMax = Math.max(lineCount, CLAUDE_MD_LINE_GUIDANCE) * 1.2
  const fillPct = (lineCount / scaleMax) * 100
  const markPct = (CLAUDE_MD_LINE_GUIDANCE / scaleMax) * 100
  const labelClass = markPct > 50 ? `${styles.meterLabel} ${styles.meterLabelEnd}` : styles.meterLabel
  return (
    <div className={styles.meter}>
      <svg
        className={styles.meterSvg}
        viewBox="0 0 100 14"
        preserveAspectRatio="none"
        role="img"
        aria-label={`${lineCount} lines against the ${CLAUDE_MD_LINE_GUIDANCE}-line guidance`}
      >
        <rect x={0} y={3} width={100} height={8} className={styles.meterTrack} />
        <rect
          x={0}
          y={3}
          width={fillPct}
          height={8}
          className={styles.meterFill}
          style={{ fill: HEALTH_COLOR[lineHealth(lineCount)] }}
        />
        <line x1={markPct} x2={markPct} y1={0} y2={14} className={styles.meterMark} />
      </svg>
      <span className={labelClass} style={{ left: `${markPct}%` }}>
        {CLAUDE_MD_LINE_GUIDANCE}-line guidance
      </span>
    </div>
  )
}

function ClaudeMdFound({ claudeMd, claudeMdAll }: Readonly<{ claudeMd: ClaudeMd; claudeMdAll: ClaudeMdAll }>) {
  const lines = useCountUp(claudeMd.lineCount, 1100)
  const plural = claudeMdAll.fileCount === 1 ? '' : 's'
  return (
    <div className={styles.statList}>
      <div className={styles.bigFigure}>
        <span className={`${styles.bigValue} ${styles[lineHealth(claudeMd.lineCount)]}`}>
          {Math.round(lines).toLocaleString()}
        </span>
        <span className={styles.bigUnit}>lines in the primary file</span>
      </div>
      <LineMeter lineCount={claudeMd.lineCount} />
      <StatRow
        label="Lines (guidance: under 200)"
        value={`${claudeMd.lineCount} / ${CLAUDE_MD_LINE_GUIDANCE}`}
        health={claudeMd.overGuidance ? 'bad' : undefined}
      />
      <StatRow label="Characters" value={claudeMd.charCount.toLocaleString()} />
      <StatRow
        label={`Est. tokens (${claudeMdAll.fileCount} file${plural})`}
        value={`~${claudeMdAll.totalTokens.toLocaleString()}`}
      />
      {claudeMdAll.files.length > 1 && (
        <ul className={styles.subList}>
          {claudeMdAll.files.map((f) => (
            <li key={f.path} className={styles.subItem}>
              <code>{f.path}</code>
              <span>{f.chars.toLocaleString()} chars</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function ClaudeMdPanel({ claudeMd, claudeMdAll }: Readonly<{ claudeMd: ClaudeMd; claudeMdAll: ClaudeMdAll }>) {
  return (
    <Panel title="CLAUDE.md">
      {claudeMd.found ? (
        <ClaudeMdFound claudeMd={claudeMd} claudeMdAll={claudeMdAll} />
      ) : (
        <p className={styles.notFound}>Not found</p>
      )}
    </Panel>
  )
}
