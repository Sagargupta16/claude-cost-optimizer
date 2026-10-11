import type { CategoryScore } from '../../utils/repoAnalyzer'
import { Panel } from './primitives'
import { ratioHealth } from './status'
import styles from './analyzer.module.css'

type Priority = 'high' | 'medium' | 'low' | 'done'

interface RecItem {
  text: string
  priority: Priority
  category?: CategoryScore
}

// Ties each recommendation repoAnalyzer.ts emits to the rubric category it improves,
// matched on its wording. First match wins, so the order matters: the Read deny
// rule text mentions settings.json, and the cost-controls text mentions a hook.
// Anything unmatched still renders, as medium priority with no category tag.
const TOPICS: { pattern: RegExp; category: string }[] = [
  { pattern: /\.env file is committed|API-key-shaped/, category: 'Security' },
  { pattern: /claudeignore|Read\(|Read deny rule/, category: 'File-read exclusions' },
  { pattern: /settings\.json to pin|default model|cost controls/i, category: 'Settings' },
  { pattern: /MCP servers configured/, category: 'MCP servers' },
  { pattern: /hooks for budget/, category: 'Hooks' },
  { pattern: /cost-mode skill|slash commands|subagents/, category: 'Optimizer tooling' },
  { pattern: /CLAUDE\.md/, category: 'CLAUDE.md' },
]
const ALL_GOOD = /looks well-optimized/

const PRIORITY_ORDER: Priority[] = ['high', 'medium', 'low', 'done']

const PRIORITY_LABEL: Record<Priority, string> = {
  high: 'High priority',
  medium: 'Medium priority',
  low: 'Low priority',
  done: 'All good',
}

const PRIORITY_CLASS: Record<Priority, string> = {
  high: styles.recHigh,
  medium: styles.recMedium,
  low: styles.recLow,
  done: styles.recDone,
}

/** Security is always high; otherwise the share of points the category already earns decides. */
function priorityFor(category: CategoryScore): Priority {
  if (category.name === 'Security') return 'high'
  const health = ratioHealth(category.score, category.maxScore)
  if (health === 'bad') return 'high'
  if (health === 'warn') return 'medium'
  return 'low'
}

function classify(text: string, categories: CategoryScore[]): RecItem {
  if (ALL_GOOD.test(text)) return { text, priority: 'done' }
  const topic = TOPICS.find((t) => t.pattern.test(text))
  const category = categories.find((c) => c.name === topic?.category)
  if (!category) return { text, priority: 'medium' }
  return { text, category, priority: priorityFor(category) }
}

function PriorityCounts({ items }: Readonly<{ items: RecItem[] }>) {
  const counts = PRIORITY_ORDER.filter((p) => p !== 'done')
    .map((priority) => ({ priority, count: items.filter((i) => i.priority === priority).length }))
    .filter((c) => c.count > 0)
  return (
    <div className={styles.countChips}>
      {counts.map(({ priority, count }) => (
        <span key={priority} className={`${styles.countChip} ${PRIORITY_CLASS[priority]}`}>
          {count} {priority}
        </span>
      ))}
    </div>
  )
}

function RecCard({ item, index }: Readonly<{ item: RecItem; index: number }>) {
  return (
    <li
      className={`${styles.recCard} ${PRIORITY_CLASS[item.priority]}`}
      style={{ animationDelay: `${index * 70}ms` }}
    >
      <div className={styles.recHead}>
        <span className={styles.recPriority}>{PRIORITY_LABEL[item.priority]}</span>
        {item.category && (
          <span className={styles.recTopic}>
            {item.category.name} {item.category.score}/{item.category.maxScore}
          </span>
        )}
      </div>
      <p className={styles.recText}>{item.text}</p>
    </li>
  )
}

export function RecommendationsPanel({
  recommendations,
  categories,
}: Readonly<{ recommendations: string[]; categories: CategoryScore[] }>) {
  const items = recommendations
    .map((text) => classify(text, categories))
    .sort((a, b) => PRIORITY_ORDER.indexOf(a.priority) - PRIORITY_ORDER.indexOf(b.priority))
  return (
    <Panel title="Recommendations" aside={<PriorityCounts items={items} />}>
      <ul className={styles.recList}>
        {items.map((item, i) => (
          <RecCard key={item.text} item={item} index={i} />
        ))}
      </ul>
    </Panel>
  )
}
