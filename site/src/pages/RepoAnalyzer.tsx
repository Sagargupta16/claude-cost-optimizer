import { useState, useCallback, useEffect, type KeyboardEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  parseRepoUrl,
  analyzeRepo,
  type AnalysisResult,
} from '../utils/repoAnalyzer'
import { copyWithFeedback } from '../utils/clipboard'
import { AnalysisReport } from '../components/analyzer/AnalysisReport'
import { AnalyzerLoading } from '../components/analyzer/AnalyzerLoading'
import styles from './RepoAnalyzer.module.css'

type Status = 'idle' | 'loading' | 'done' | 'error'

const DEMO_REPO = 'Sagargupta16/claude-cost-optimizer'

const LOCAL_CMD =
  'curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- .'

const INVALID_URL_ERROR = 'Invalid repo URL. Use https://github.com/owner/repo or owner/repo'
const NOT_FOUND_ERROR =
  'Repository not found. Make sure the repo is public and the URL is correct.'
const NETWORK_ERROR = 'Failed to analyze repo. Check your network connection and try again.'

/** Analysis state plus the action that runs one. Never leaves a promise unhandled. */
function useRepoAnalysis() {
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState('')
  const [result, setResult] = useState<AnalysisResult | null>(null)

  const fail = useCallback((message: string) => {
    setError(message)
    setStatus('error')
  }, [])

  const succeed = useCallback(
    (analysis: AnalysisResult) => {
      if (!analysis.repoExists) {
        fail(NOT_FOUND_ERROR)
        return
      }
      setResult(analysis)
      setStatus('done')
    },
    [fail],
  )

  const analyze = useCallback(
    (url: string, branch: string) => {
      const parsed = parseRepoUrl(url)
      if (!parsed) {
        fail(INVALID_URL_ERROR)
        return
      }
      setStatus('loading')
      setError('')
      setResult(null)
      analyzeRepo({ ...parsed, branch: branch || parsed.branch }).then(succeed, () =>
        fail(NETWORK_ERROR),
      )
    },
    [fail, succeed],
  )

  return { status, error, result, analyze }
}

interface AnalyzerInputProps {
  url: string
  branch: string
  loading: boolean
  error: string
  showDemo: boolean
  onUrlChange: (url: string) => void
  onBranchChange: (branch: string) => void
  onAnalyze: () => void
  onDemo: () => void
}

function AnalyzerInput(props: Readonly<AnalyzerInputProps>) {
  const { url, branch, loading, error, showDemo, onUrlChange, onBranchChange, onAnalyze, onDemo } = props

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !loading) onAnalyze()
  }

  return (
    <div className={styles.inputSection}>
      <div className={styles.inputRow}>
        <input
          type="text"
          aria-label="GitHub repo URL"
          placeholder="https://github.com/owner/repo or owner/repo"
          value={url}
          onChange={(e) => onUrlChange(e.target.value)}
          onKeyDown={handleKeyDown}
          className={styles.urlInput}
        />
        <input
          type="text"
          aria-label="Branch"
          placeholder="Branch (optional)"
          value={branch}
          onChange={(e) => onBranchChange(e.target.value)}
          onKeyDown={handleKeyDown}
          className={styles.branchInput}
        />
        <button
          type="button"
          onClick={onAnalyze}
          disabled={loading || !url.trim()}
          className={styles.analyzeButton}
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
      {error && <p className={styles.error}>{error}</p>}
      <div className={styles.hintRow}>
        <p className={styles.hint}>
          Uses GitHub's public API (no auth needed for public repos). Rate limit: 60 requests/hour.
        </p>
        {showDemo && (
          <button type="button" className={styles.tryDemo} onClick={onDemo}>
            Try it on our repo
          </button>
        )}
      </div>
    </div>
  )
}

/** Local / private repos: the CLI covers what the web analyzer can't see. */
function LocalCliCallout() {
  const [copied, setCopied] = useState(false)
  const handleCopy = useCallback(() => copyWithFeedback(LOCAL_CMD, setCopied), [])
  return (
    <div className={styles.localCallout}>
      <div className={styles.localText}>
        <strong>Private or local repo?</strong> Run <code>claude-rate</code> in
        any project directory -- same rubric, plus local-only checks
        (gitignored settings.local.json, leaked secrets, files you have not
        pushed):
      </div>
      <div className={styles.localCmdRow}>
        <code className={styles.localCmd}>{LOCAL_CMD}</code>
        <button type="button" onClick={handleCopy} className={styles.localCopyBtn}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  )
}

function RepoAnalyzer() {
  const [searchParams] = useSearchParams()
  const [url, setUrl] = useState('')
  const [branch, setBranch] = useState('')
  const { status, error, result, analyze } = useRepoAnalysis()

  // Auto-fill from ?repo= query param
  useEffect(() => {
    const repoParam = searchParams.get('repo')
    if (repoParam) {
      setUrl(repoParam)
    }
  }, [searchParams])

  const handleAnalyze = useCallback(() => analyze(url, branch), [analyze, url, branch])
  const handleDemo = useCallback(() => setUrl(DEMO_REPO), [])

  return (
    <div className={styles.analyzer}>
      <h1 className={styles.title}>Repo Analyzer</h1>
      <p className={styles.subtitle}>
        Paste a GitHub repo URL to analyze its Claude Code configuration and get
        cost optimization recommendations. Checks CLAUDE.md, file-read
        exclusions (Read rules in permissions.deny), settings, MCP servers,
        hooks, skills, agents, commands, and secrets.
      </p>

      <AnalyzerInput
        url={url}
        branch={branch}
        loading={status === 'loading'}
        error={status === 'error' ? error : ''}
        showDemo={!result}
        onUrlChange={setUrl}
        onBranchChange={setBranch}
        onAnalyze={handleAnalyze}
        onDemo={handleDemo}
      />

      <LocalCliCallout />

      {status === 'loading' && <AnalyzerLoading />}
      {result && <AnalysisReport result={result} />}
    </div>
  )
}

export default RepoAnalyzer
