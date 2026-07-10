import { useState, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  parseRepoUrl,
  analyzeRepo,
  type AnalysisResult,
} from '../utils/repoAnalyzer'
import { MODELS, type ModelId } from '../utils/pricing'
import styles from './RepoAnalyzer.module.css'

type Status = 'idle' | 'loading' | 'done' | 'error'

const DEMO_REPO = 'Sagargupta16/claude-cost-optimizer'

const LOCAL_CMD =
  'curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- .'

function charBarColor(charCount: number, overLimit: boolean): string {
  if (overLimit) return 'var(--error-red)'
  if (charCount > 3000) return 'var(--warning-yellow)'
  return 'var(--accent-green)'
}

function categoryColor(score: number, maxScore: number): string {
  const pct = maxScore > 0 ? score / maxScore : 0
  if (pct >= 0.8) return 'var(--accent-green)'
  if (pct >= 0.5) return 'var(--warning-yellow)'
  return 'var(--error-red)'
}

function RepoAnalyzer() {
  const [searchParams] = useSearchParams()
  const [url, setUrl] = useState('')
  const [branch, setBranch] = useState('')
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [copied, setCopied] = useState(false)
  const [cmdCopied, setCmdCopied] = useState(false)

  // Auto-fill from ?repo= query param
  useEffect(() => {
    const repoParam = searchParams.get('repo')
    if (repoParam) {
      setUrl(repoParam)
    }
  }, [searchParams])

  const handleAnalyze = useCallback(async () => {
    const parsed = parseRepoUrl(url)
    if (!parsed) {
      setError('Invalid repo URL. Use https://github.com/owner/repo or owner/repo')
      setStatus('error')
      return
    }
    if (branch) parsed.branch = branch

    setStatus('loading')
    setError('')
    setResult(null)

    try {
      const analysis = await analyzeRepo(parsed)

      if (!analysis.repoExists) {
        setError(
          'Repository not found. Make sure the repo is public and the URL is correct.',
        )
        setStatus('error')
        return
      }

      setResult(analysis)
      setStatus('done')
    } catch {
      setError('Failed to analyze repo. Check your network connection and try again.')
      setStatus('error')
    }
  }, [url, branch])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') handleAnalyze()
    },
    [handleAnalyze],
  )

  const handleCopyBadge = useCallback(() => {
    if (!result) return
    const encodedGrade = encodeURIComponent(result.grade.letter)
    const encodedColor = result.grade.color.replace('#', '')
    const md = `[![Claude Cost Optimizer Grade](https://img.shields.io/badge/claude_cost_optimizer-${encodedGrade}-${encodedColor}?style=for-the-badge)](https://sagargupta16.github.io/claude-cost-optimizer/analyzer)`
    navigator.clipboard.writeText(md).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }, [result])

  const handleCopyCmd = useCallback(() => {
    navigator.clipboard.writeText(LOCAL_CMD).then(() => {
      setCmdCopied(true)
      setTimeout(() => setCmdCopied(false), 2000)
    })
  }, [])

  return (
    <div className={styles.analyzer}>
      <h1 className={styles.title}>Repo Analyzer</h1>
      <p className={styles.subtitle}>
        Paste a GitHub repo URL to analyze its Claude Code configuration and get
        cost optimization recommendations. Checks CLAUDE.md, .claudeignore,
        settings, MCP servers, hooks, skills, agents, commands, and secrets.
      </p>

      <div className={styles.inputSection}>
        <div className={styles.inputRow}>
          <input
            type="text"
            placeholder="https://github.com/owner/repo or owner/repo"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={handleKeyDown}
            className={styles.urlInput}
          />
          <input
            type="text"
            placeholder="Branch (optional)"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
            onKeyDown={handleKeyDown}
            className={styles.branchInput}
          />
          <button
            onClick={handleAnalyze}
            disabled={status === 'loading' || !url.trim()}
            className={styles.analyzeButton}
          >
            {status === 'loading' ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>
        {status === 'error' && <p className={styles.error}>{error}</p>}
        <div className={styles.hintRow}>
          <p className={styles.hint}>
            Uses GitHub's public API (no auth needed for public repos). Rate limit: 60 requests/hour.
          </p>
          {!result && (
            <button
              className={styles.tryDemo}
              onClick={() => {
                setUrl(DEMO_REPO)
              }}
            >
              Try it on our repo
            </button>
          )}
        </div>
      </div>

      {/* Local / private repos: the CLI covers what the web analyzer can't see */}
      <div className={styles.localCallout}>
        <div className={styles.localText}>
          <strong>Private or local repo?</strong> Run <code>claude-rate</code> in
          any project directory -- same rubric, plus local-only checks
          (.claudeignore coverage vs files on disk, settings.local.json, leaked
          secrets):
        </div>
        <div className={styles.localCmdRow}>
          <code className={styles.localCmd}>{LOCAL_CMD}</code>
          <button onClick={handleCopyCmd} className={styles.localCopyBtn}>
            {cmdCopied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      {status === 'loading' && (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <span>Fetching repo tree and files from GitHub...</span>
        </div>
      )}

      {result && (
        <div className={styles.results}>
          {/* Grade header */}
          <div className={styles.gradeSection}>
            <div className={styles.gradeCard}>
              <span
                className={styles.gradeLetter}
                style={{ color: result.grade.color }}
              >
                {result.grade.letter}
              </span>
              <span className={styles.gradeScore}>
                {result.grade.score} / 100
              </span>
              <span className={styles.repoName}>{result.repo}</span>
              <span className={styles.branchName}>{result.branch}</span>
            </div>
          </div>

          {/* Score breakdown */}
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>Score Breakdown</h2>
            <div className={styles.categoryList}>
              {result.categories.map((c) => (
                <div key={c.name} className={styles.categoryRow}>
                  <span className={styles.categoryName}>{c.name}</span>
                  <div className={styles.categoryBar}>
                    <div
                      className={styles.categoryFill}
                      style={{
                        width: `${c.maxScore > 0 ? (c.score / c.maxScore) * 100 : 0}%`,
                        backgroundColor: categoryColor(c.score, c.maxScore),
                      }}
                    />
                  </div>
                  <span className={styles.categoryScore}>
                    {c.score}/{c.maxScore}
                  </span>
                  <span className={styles.categoryDetail}>{c.detail}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Files found */}
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>Files Detected</h2>
            <div className={styles.fileList}>
              {result.files.map((f) => (
                <div
                  key={f.path}
                  className={`${styles.fileItem} ${f.found ? styles.fileFound : styles.fileMissing}`}
                >
                  <span className={styles.fileIcon}>
                    {f.found ? '+' : '-'}
                  </span>
                  <span className={styles.filePath}>{f.path}</span>
                  {f.found && (
                    <span className={styles.fileSize}>
                      {f.size.toLocaleString()} bytes
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Analysis details grid */}
          <div className={styles.detailsGrid}>
            {/* CLAUDE.md */}
            <div className={styles.panel}>
              <h2 className={styles.panelTitle}>CLAUDE.md</h2>
              {result.claudeMd.found ? (
                <div className={styles.statList}>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Characters</span>
                    <span
                      className={`${styles.statValue} ${result.claudeMd.overLimit ? styles.statDanger : ''}`}
                    >
                      {result.claudeMd.charCount.toLocaleString()} / 4,000
                    </span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Lines</span>
                    <span className={styles.statValue}>
                      {result.claudeMd.lineCount}
                    </span>
                  </div>
                  {result.claudeMdAll.fileCount > 1 && (
                    <div className={styles.stat}>
                      <span className={styles.statLabel}>Total across files</span>
                      <span
                        className={`${styles.statValue} ${result.claudeMdAll.overLimit ? styles.statDanger : ''}`}
                      >
                        {result.claudeMdAll.totalChars.toLocaleString()} / 12,000
                      </span>
                    </div>
                  )}
                  <div className={styles.charBar}>
                    <div
                      className={styles.charFill}
                      style={{
                        width: `${Math.min((result.claudeMd.charCount / 4000) * 100, 100)}%`,
                        backgroundColor: charBarColor(
                          result.claudeMd.charCount,
                          result.claudeMd.overLimit,
                        ),
                      }}
                    />
                  </div>
                </div>
              ) : (
                <p className={styles.notFound}>Not found</p>
              )}
            </div>

            {/* .claudeignore */}
            <div className={styles.panel}>
              <h2 className={styles.panelTitle}>.claudeignore</h2>
              {result.claudeIgnore.found ? (
                <div className={styles.statList}>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Patterns</span>
                    <span className={styles.statValue}>
                      {result.claudeIgnore.entryCount}
                    </span>
                  </div>
                  {result.claudeIgnore.entries.length > 0 && (
                    <div className={styles.entryList}>
                      {result.claudeIgnore.entries.slice(0, 10).map((e) => (
                        <code key={e} className={styles.entry}>
                          {e}
                        </code>
                      ))}
                      {result.claudeIgnore.entries.length > 10 && (
                        <span className={styles.moreEntries}>
                          +{result.claudeIgnore.entries.length - 10} more
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <p className={styles.notFound}>Not found</p>
              )}
            </div>

            {/* Settings */}
            <div className={styles.panel}>
              <h2 className={styles.panelTitle}>Settings</h2>
              {result.settings.found ? (
                <div className={styles.statList}>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Default model</span>
                    <span
                      className={`${styles.statValue} ${result.settings.hasModel ? styles.statGood : styles.statWarn}`}
                    >
                      {result.settings.hasModel ? 'Configured' : 'Not set'}
                    </span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Budget cap</span>
                    <span
                      className={`${styles.statValue} ${result.settings.hasBudget ? styles.statGood : styles.statWarn}`}
                    >
                      {result.settings.hasBudget ? 'Set' : 'Not set'}
                    </span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>MCP servers</span>
                    <span className={styles.statValue}>
                      {result.settings.mcpServerCount}
                    </span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Hooks</span>
                    <span className={styles.statValue}>
                      {result.settings.hasHooks
                        ? `${result.settings.hookCount} entries, ${result.tooling.hookScripts} scripts`
                        : 'None'}
                    </span>
                  </div>
                </div>
              ) : (
                <p className={styles.notFound}>Not found</p>
              )}
            </div>

            {/* Skills, agents, commands */}
            <div className={styles.panel}>
              <h2 className={styles.panelTitle}>Skills, Agents, Commands</h2>
              <div className={styles.statList}>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>cost-mode skill</span>
                  <span
                    className={`${styles.statValue} ${result.tooling.costModeInstalled ? styles.statGood : styles.statWarn}`}
                  >
                    {result.tooling.costModeInstalled ? 'Installed' : 'Not installed'}
                  </span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Skills</span>
                  <span className={styles.statValue}>
                    {result.tooling.skills.length}
                  </span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Subagents</span>
                  <span className={styles.statValue}>
                    {result.tooling.agentCount}
                  </span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Slash commands</span>
                  <span className={styles.statValue}>
                    {result.tooling.commandCount}
                  </span>
                </div>
                {result.tooling.skills.length > 0 && (
                  <div className={styles.entryList}>
                    {result.tooling.skills.slice(0, 8).map((s) => (
                      <code key={s} className={styles.entry}>
                        {s}
                      </code>
                    ))}
                    {result.tooling.skills.length > 8 && (
                      <span className={styles.moreEntries}>
                        +{result.tooling.skills.length - 8} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Security */}
            <div className={styles.panel}>
              <h2 className={styles.panelTitle}>Security</h2>
              <div className={styles.statList}>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>.env committed</span>
                  <span
                    className={`${styles.statValue} ${result.security.envTracked ? styles.statDanger : styles.statGood}`}
                  >
                    {result.security.envTracked ? 'Yes -- rotate secrets' : 'No'}
                  </span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>API keys in config</span>
                  <span
                    className={`${styles.statValue} ${result.security.keyLeakFiles.length > 0 ? styles.statDanger : styles.statGood}`}
                  >
                    {result.security.keyLeakFiles.length > 0
                      ? result.security.keyLeakFiles.join(', ')
                      : 'None detected'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Token & Cost estimates */}
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>
              Cost Estimate (30-turn session, 3 sessions/day, 22 days/month)
            </h2>
            <div className={styles.tokenSummary}>
              <div className={styles.tokenStat}>
                <span className={styles.tokenLabel}>System prompt</span>
                <span className={styles.tokenValue}>
                  ~{result.tokenEstimate.systemPromptTokens.toLocaleString()} tokens
                </span>
              </div>
              <div className={styles.tokenStat}>
                <span className={styles.tokenLabel}>Per turn (avg)</span>
                <span className={styles.tokenValue}>
                  ~{result.tokenEstimate.perTurnTokens.toLocaleString()} tokens
                </span>
              </div>
            </div>

            <table className={styles.costTable}>
              <thead>
                <tr>
                  <th>Model</th>
                  <th>Per Session</th>
                  <th>Per Month</th>
                </tr>
              </thead>
              <tbody>
                {(Object.keys(MODELS) as ModelId[])
                  .filter((id) => !MODELS[id].inviteOnly)
                  .map((id) => (
                  <tr key={id}>
                    <td>{MODELS[id].name}</td>
                    <td className={styles.mono}>
                      ${result.costEstimate[id].perSession.toFixed(2)}
                    </td>
                    <td className={styles.mono}>
                      ${result.costEstimate[id].perMonth.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Recommendations */}
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>Recommendations</h2>
            <ul className={styles.recommendations}>
              {result.recommendations.map((rec) => (
                <li key={rec} className={styles.recommendation}>
                  {rec}
                </li>
              ))}
            </ul>
          </div>

          {/* Badge */}
          <div className={styles.panel}>
            <h2 className={styles.panelTitle}>Your Badge</h2>
            <div className={styles.badgePreview}>
              <img
                src={`https://img.shields.io/badge/claude_cost_optimizer-${encodeURIComponent(result.grade.letter)}-${result.grade.color.replace('#', '')}?style=for-the-badge`}
                alt={`Grade: ${result.grade.letter}`}
              />
            </div>
            <button onClick={handleCopyBadge} className={styles.copyButton}>
              {copied ? 'Copied!' : 'Copy Badge Markdown'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default RepoAnalyzer
