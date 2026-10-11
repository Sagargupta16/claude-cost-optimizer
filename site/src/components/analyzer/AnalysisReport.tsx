import type { AnalysisResult } from '../../utils/repoAnalyzer'
import { BadgePanel } from './BadgePanel'
import { CategoryBreakdown } from './CategoryBreakdown'
import { ClaudeMdPanel } from './ClaudeMdPanel'
import { CostPanel } from './CostPanel'
import { FilesPanel, FileReadPanel, SecurityPanel, SettingsPanel, ToolingPanel } from './DetailPanels'
import { GradeHero } from './GradeHero'
import { RecommendationsPanel } from './RecommendationsPanel'
import styles from './analyzer.module.css'

/** The whole results report: grade, breakdown, fixes, cost, per-area detail, badge. */
export function AnalysisReport({ result }: Readonly<{ result: AnalysisResult }>) {
  return (
    <div className={styles.results}>
      <GradeHero result={result} />
      <CategoryBreakdown categories={result.categories} />
      <RecommendationsPanel recommendations={result.recommendations} categories={result.categories} />
      <CostPanel result={result} />
      <div className={styles.detailsGrid}>
        <ClaudeMdPanel claudeMd={result.claudeMd} claudeMdAll={result.claudeMdAll} />
        <FileReadPanel exclusions={result.fileReadExclusions} />
        <SettingsPanel settings={result.settings} hookScripts={result.tooling.hookScripts} />
        <ToolingPanel tooling={result.tooling} />
        <SecurityPanel security={result.security} />
        <FilesPanel files={result.files} />
      </div>
      <BadgePanel grade={result.grade} />
    </div>
  )
}
