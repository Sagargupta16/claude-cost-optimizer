import type { CategoryScore } from '../../utils/repoAnalyzer'
import { Panel } from './primitives'
import { HEALTH_COLOR, ratioHealth, type Health } from './status'
import styles from './analyzer.module.css'

const VIEW_W = 360
const VIEW_H = 280
const CX = VIEW_W / 2
const CY = VIEW_H / 2
const RADIUS = 96
const LABEL_RADIUS = 116
const LINE_H = 14
const RINGS = [0.25, 0.5, 0.75, 1]

const LEGEND: { health: Health; label: string }[] = [
  { health: 'good', label: 'Strong' },
  { health: 'warn', label: 'Partial' },
  { health: 'bad', label: 'Weak' },
]

function share(c: CategoryScore): number {
  return c.maxScore > 0 ? c.score / c.maxScore : 0
}

/** Point on axis `index` of `count`, at `ratio` of the full radius. Axis 0 points up. */
function point(index: number, count: number, ratio: number) {
  const angle = (index / count) * 2 * Math.PI - Math.PI / 2
  return {
    x: CX + RADIUS * ratio * Math.cos(angle),
    y: CY + RADIUS * ratio * Math.sin(angle),
  }
}

function polygonPoints(count: number, ratioAt: (index: number) => number): string {
  return Array.from({ length: count }, (_, i) => {
    const p = point(i, count, ratioAt(i))
    return `${p.x.toFixed(1)},${p.y.toFixed(1)}`
  }).join(' ')
}

function anchorFor(x: number): 'start' | 'middle' | 'end' {
  if (x > CX + 8) return 'start'
  if (x < CX - 8) return 'end'
  return 'middle'
}

/** Long names ("File-read exclusions") wrap onto two lines at the first space. */
function labelLines(name: string): string[] {
  const space = name.indexOf(' ')
  if (name.length <= 10 || space < 0) return [name]
  return [name.slice(0, space), name.slice(space + 1)]
}

function RadarLabel({ name, index, count }: Readonly<{ name: string; index: number; count: number }>) {
  const p = point(index, count, LABEL_RADIUS / RADIUS)
  const lines = labelLines(name)
  const firstY = p.y + 4 - ((lines.length - 1) * LINE_H) / 2
  return (
    <text x={p.x} y={firstY} textAnchor={anchorFor(p.x)} className={styles.radarLabel}>
      {lines.map((line, i) => (
        <tspan key={line} x={p.x} dy={i === 0 ? 0 : LINE_H}>
          {line}
        </tspan>
      ))}
    </text>
  )
}

function RadarDot({ category, index, count }: Readonly<{ category: CategoryScore; index: number; count: number }>) {
  const p = point(index, count, share(category))
  const color = HEALTH_COLOR[ratioHealth(category.score, category.maxScore)]
  return (
    <circle
      cx={p.x}
      cy={p.y}
      r={5}
      className={styles.radarDot}
      style={{ fill: color, animationDelay: `${600 + index * 70}ms` }}
    />
  )
}

function Radar({ categories }: Readonly<{ categories: CategoryScore[] }>) {
  const count = categories.length
  const summary = categories.map((c) => `${c.name} ${c.score} of ${c.maxScore}`).join(', ')
  return (
    <svg
      className={styles.radar}
      viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
      role="img"
      aria-label={`Radar chart of category scores: ${summary}`}
    >
      {RINGS.map((ring) => (
        <polygon key={ring} points={polygonPoints(count, () => ring)} className={styles.radarGrid} />
      ))}
      {categories.map((c, i) => {
        const end = point(i, count, 1)
        return <line key={c.name} x1={CX} y1={CY} x2={end.x} y2={end.y} className={styles.radarSpoke} />
      })}
      <g className={styles.radarShape} style={{ transformOrigin: `${CX}px ${CY}px` }}>
        <polygon points={polygonPoints(count, (i) => share(categories[i]))} className={styles.radarArea} />
        {categories.map((c, i) => (
          <RadarDot key={c.name} category={c} index={i} count={count} />
        ))}
      </g>
      {categories.map((c, i) => (
        <RadarLabel key={c.name} name={c.name} index={i} count={count} />
      ))}
    </svg>
  )
}

function CategoryRow({ category, index }: Readonly<{ category: CategoryScore; index: number }>) {
  const health = ratioHealth(category.score, category.maxScore)
  return (
    <li className={styles.categoryRow}>
      <div className={styles.categoryTop}>
        <span className={styles.categoryName}>{category.name}</span>
        <span className={`${styles.categoryScore} ${styles[health]}`}>
          {category.score}/{category.maxScore}
        </span>
      </div>
      <div className={styles.track}>
        <div
          className={styles.fill}
          style={{
            width: `${share(category) * 100}%`,
            backgroundColor: HEALTH_COLOR[health],
            animationDelay: `${index * 90}ms`,
          }}
        />
      </div>
      <span className={styles.categoryDetail}>{category.detail}</span>
    </li>
  )
}

function Legend() {
  return (
    <div className={styles.legend}>
      {LEGEND.map(({ health, label }) => (
        <span key={health} className={styles.legendItem}>
          <span className={styles.swatch} style={{ backgroundColor: HEALTH_COLOR[health] }} />
          {label}
        </span>
      ))}
    </div>
  )
}

export function CategoryBreakdown({ categories }: Readonly<{ categories: CategoryScore[] }>) {
  return (
    <Panel title="Score Breakdown" aside={<Legend />}>
      <div className={styles.breakdown}>
        <Radar categories={categories} />
        <ul className={styles.categoryList}>
          {categories.map((c, i) => (
            <CategoryRow key={c.name} category={c} index={i} />
          ))}
        </ul>
      </div>
    </Panel>
  )
}
