import type { AnalysisResult } from '../../utils/repoAnalyzer'
import { useCountUp } from './hooks'
import { StatTile } from './primitives'
import styles from './analyzer.module.css'

type Grade = AnalysisResult['grade']

const SIZE = 200
const CENTER = SIZE / 2
const RING_R = 78
const CIRCUMFERENCE = 2 * Math.PI * RING_R
const TICK_INNER = 90
const TICK_OUTER = 97
// One tick per 5 points; each lights up as the count-up passes it.
const TICK_VALUES = Array.from({ length: 20 }, (_, i) => (i + 1) * 5)
const UNLIT = '#30363d'

function tickLine(value: number) {
  const angle = (value / 100) * 2 * Math.PI - Math.PI / 2
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  return {
    x1: CENTER + TICK_INNER * cos,
    y1: CENTER + TICK_INNER * sin,
    x2: CENTER + TICK_OUTER * cos,
    y2: CENTER + TICK_OUTER * sin,
  }
}

/** Radial ring that sweeps to the score, the letter in the middle, the score counting up. */
function GradeGauge({ grade }: Readonly<{ grade: Grade }>) {
  const shown = useCountUp(grade.score, 1400)
  const offset = CIRCUMFERENCE * (1 - shown / 100)
  return (
    <svg
      className={styles.gauge}
      viewBox={`0 0 ${SIZE} ${SIZE}`}
      role="img"
      aria-label={`Grade ${grade.letter}: ${grade.score} out of 100 points`}
    >
      {TICK_VALUES.map((v) => (
        <line
          key={v}
          {...tickLine(v)}
          className={styles.gaugeTick}
          style={{ stroke: v <= shown ? grade.color : UNLIT }}
        />
      ))}
      <circle cx={CENTER} cy={CENTER} r={RING_R} className={styles.gaugeTrack} />
      <circle
        cx={CENTER}
        cy={CENTER}
        r={RING_R}
        className={styles.gaugeArc}
        style={{ stroke: grade.color }}
        strokeDasharray={CIRCUMFERENCE}
        strokeDashoffset={offset}
        strokeLinecap={shown > 0.5 ? 'round' : 'butt'}
        transform={`rotate(-90 ${CENTER} ${CENTER})`}
      />
      <text x={CENTER} y={110} className={styles.gaugeLetter} style={{ fill: grade.color }}>
        {grade.letter}
      </text>
      <text x={CENTER} y={137} className={styles.gaugeScore}>
        {Math.round(shown)} / 100
      </text>
    </svg>
  )
}

export function GradeHero({ result }: Readonly<{ result: AnalysisResult }>) {
  const { categories, files } = result
  const fullMarks = categories.filter((c) => c.score >= c.maxScore).length
  const pointsLeft = categories.reduce((sum, c) => sum + Math.max(c.maxScore - c.score, 0), 0)
  const filesFound = files.filter((f) => f.found).length

  return (
    <section className={styles.hero} aria-label="Grade">
      <GradeGauge grade={result.grade} />
      <div className={styles.heroBody}>
        <span className={styles.heroKicker}>Claude Code cost report</span>
        <h2 className={styles.heroRepo}>{result.repo}</h2>
        <span className={styles.branchChip}>{result.branch}</span>
        <div className={styles.tiles}>
          <StatTile
            label="Categories at full marks"
            value={fullMarks}
            suffix={` / ${categories.length}`}
          />
          <StatTile label="Points left to earn" value={pointsLeft} />
          <StatTile label="Recommendations" value={result.recommendations.length} />
          <StatTile label="Files detected" value={filesFound} suffix={` / ${files.length}`} />
        </div>
      </div>
    </section>
  )
}
