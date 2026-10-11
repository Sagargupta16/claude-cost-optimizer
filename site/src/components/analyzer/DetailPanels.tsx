import type { AnalysisResult, FetchedFile } from '../../utils/repoAnalyzer'
import { CopyButton, EntryChips, Panel, StatRow, StatTile, StatusIcon } from './primitives'
import { type Health } from './status'
import styles from './analyzer.module.css'

type Exclusions = AnalysisResult['fileReadExclusions']
type Settings = AnalysisResult['settings']
type Tooling = AnalysisResult['tooling']
type Security = AnalysisResult['security']

function okOrWarn(ok: boolean): Health {
  return ok ? 'good' : 'warn'
}

function lockFilesLabel(present: string[], uncovered: string[]): string {
  if (present.length === 0) return 'None at root'
  if (uncovered.length > 0) return `Not covered: ${uncovered.join(', ')}`
  return 'Covered'
}

// -- Files detected -----------------------------------------------------------

function FileTile({ file, index }: Readonly<{ file: FetchedFile; index: number }>) {
  const stateClass = file.found ? styles.fileFound : styles.fileMissing
  return (
    <li className={`${styles.fileTile} ${stateClass}`} style={{ animationDelay: `${index * 60}ms` }}>
      <span className={styles.fileIcon}>{file.found ? '+' : '-'}</span>
      <span className={styles.filePath}>{file.path}</span>
      {file.found && <span className={styles.fileSize}>{file.size.toLocaleString()} bytes</span>}
    </li>
  )
}

export function FilesPanel({ files }: Readonly<{ files: FetchedFile[] }>) {
  const found = files.filter((f) => f.found).length
  return (
    <Panel
      title="Files Detected"
      aside={
        <span className={styles.panelMeta}>
          {found} of {files.length} found
        </span>
      }
    >
      <ul className={styles.fileGrid}>
        {files.map((f, i) => (
          <FileTile key={f.path} file={f} index={i} />
        ))}
      </ul>
    </Panel>
  )
}

// -- File-read exclusions -----------------------------------------------------

/** A committed .claudeignore: flag it and offer its patterns as Read deny rules. */
function IgnoreFileMigration({ rules }: Readonly<{ rules: string[] }>) {
  const snippet = JSON.stringify({ permissions: { deny: rules } }, null, 2)
  return (
    <>
      <StatRow label=".claudeignore" value="Not read by Claude Code" health="bad" />
      <p className={styles.notFound}>
        It appears nowhere in Claude Code's documentation and scores
        nothing. Its patterns as Read deny rules:
      </p>
      <EntryChips items={rules} limit={10} />
      {rules.length > 0 && (
        <CopyButton text={snippet} label="Copy as settings.json snippet" doneLabel="Copied" />
      )}
    </>
  )
}

export function FileReadPanel({ exclusions }: Readonly<{ exclusions: Exclusions }>) {
  const ruleCount = exclusions.readDenyRules.length
  return (
    <Panel title="File-read exclusions">
      <div className={styles.statList}>
        <StatRow label="Read deny rules" value={ruleCount} health={okOrWarn(ruleCount > 0)} />
        {ruleCount > 0 ? (
          <EntryChips items={exclusions.readDenyRules} limit={10} />
        ) : (
          <p className={styles.notFound}>No Read deny rules in permissions.deny</p>
        )}
        <StatRow
          label="Lock files"
          value={lockFilesLabel(exclusions.lockFilesPresent, exclusions.lockFilesUncovered)}
          health={okOrWarn(exclusions.lockFilesUncovered.length === 0)}
        />
        {exclusions.ignoreFileFound && <IgnoreFileMigration rules={exclusions.ignoreFileRules} />}
      </div>
    </Panel>
  )
}

// -- Settings -----------------------------------------------------------------

function SettingsStats({ settings, hookScripts }: Readonly<{ settings: Settings; hookScripts: number }>) {
  const hooks = settings.hasHooks ? `${settings.hookCount} entries, ${hookScripts} scripts` : 'None'
  return (
    <div className={styles.statList}>
      <StatRow
        label="Default model"
        value={settings.hasModel ? 'Configured' : 'Not set'}
        health={okOrWarn(settings.hasModel)}
      />
      <StatRow
        label="Cost controls"
        value={settings.hasCostControls ? 'Set' : 'Not set'}
        health={okOrWarn(settings.hasCostControls)}
      />
      <StatRow label="MCP servers" value={settings.mcpServerCount} />
      <StatRow label="Hooks" value={hooks} />
    </div>
  )
}

export function SettingsPanel({ settings, hookScripts }: Readonly<{ settings: Settings; hookScripts: number }>) {
  return (
    <Panel title="Settings">
      {settings.found ? (
        <SettingsStats settings={settings} hookScripts={hookScripts} />
      ) : (
        <p className={styles.notFound}>Not found</p>
      )}
    </Panel>
  )
}

// -- Skills, agents, commands -------------------------------------------------

export function ToolingPanel({ tooling }: Readonly<{ tooling: Tooling }>) {
  return (
    <Panel title="Skills, Agents, Commands">
      <div className={styles.miniTiles}>
        <StatTile label="Skills" value={tooling.skills.length} />
        <StatTile label="Subagents" value={tooling.agentCount} />
        <StatTile label="Slash commands" value={tooling.commandCount} />
      </div>
      <div className={styles.statList}>
        <StatRow
          label="cost-mode skill"
          value={tooling.costModeInstalled ? 'Installed' : 'Not installed'}
          health={okOrWarn(tooling.costModeInstalled)}
        />
        {tooling.skills.length > 0 && <EntryChips items={tooling.skills} limit={8} />}
      </div>
    </Panel>
  )
}

// -- Security -----------------------------------------------------------------

export function SecurityPanel({ security }: Readonly<{ security: Security }>) {
  const leaks = security.keyLeakFiles.length > 0
  const problems = Number(security.envTracked) + Number(leaks)
  const health: Health = problems > 0 ? 'bad' : 'good'
  const plural = problems === 1 ? '' : 's'
  const headline = problems > 0 ? `${problems} problem${plural} found` : 'No leaks detected'
  return (
    <Panel title="Security">
      <div className={`${styles.statusBanner} ${styles[health]}`}>
        <StatusIcon health={health} />
        <span>{headline}</span>
      </div>
      <div className={styles.statList}>
        <StatRow
          label=".env committed"
          value={security.envTracked ? 'Yes -- rotate secrets' : 'No'}
          health={security.envTracked ? 'bad' : 'good'}
        />
        <StatRow
          label="API keys in config"
          value={leaks ? security.keyLeakFiles.join(', ') : 'None detected'}
          health={leaks ? 'bad' : 'good'}
        />
      </div>
    </Panel>
  )
}
