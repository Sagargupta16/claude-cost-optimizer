import type { AnalysisResult } from '../../utils/repoAnalyzer'
import { CopyButton, Panel } from './primitives'
import styles from './analyzer.module.css'

export function BadgePanel({ grade }: Readonly<{ grade: AnalysisResult['grade'] }>) {
  const encodedGrade = encodeURIComponent(grade.letter)
  const encodedColor = grade.color.replace('#', '')
  const badgeUrl = `https://img.shields.io/badge/claude_cost_optimizer-${encodedGrade}-${encodedColor}?style=for-the-badge`
  const markdown = `[![Claude Cost Optimizer Grade](${badgeUrl})](https://sagargupta16.github.io/claude-cost-optimizer/analyzer)`
  return (
    <Panel title="Your Badge">
      <div className={styles.badgePreview}>
        <img src={badgeUrl} alt={`Grade: ${grade.letter}`} />
      </div>
      <code className={styles.badgeCode}>{markdown}</code>
      <CopyButton text={markdown} label="Copy Badge Markdown" doneLabel="Copied!" />
    </Panel>
  )
}
