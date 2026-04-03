import { MODELS, TOKEN_ESTIMATES, type ModelId } from './pricing'

export interface RepoInput {
  owner: string
  repo: string
  branch: string
}

export interface FetchedFile {
  path: string
  content: string
  size: number
  found: boolean
}

export interface AnalysisResult {
  repo: string
  branch: string
  files: FetchedFile[]
  claudeMd: {
    found: boolean
    charCount: number
    lineCount: number
    overLimit: boolean
  }
  claudeMdAll: {
    totalChars: number
    fileCount: number
    overLimit: boolean
    files: { path: string; chars: number }[]
  }
  claudeIgnore: {
    found: boolean
    entryCount: number
    entries: string[]
  }
  settings: {
    found: boolean
    hasModel: boolean
    hasBudget: boolean
    mcpServerCount: number
    hasHooks: boolean
    raw: Record<string, unknown> | null
  }
  grade: { letter: string; score: number; color: string }
  tokenEstimate: {
    systemPromptTokens: number
    perTurnTokens: number
    sessionTokens30Turns: number
  }
  repoExists: boolean
  costEstimate: Record<ModelId, { perSession: number; perMonth: number }>
  recommendations: string[]
}

const GITHUB_API = 'https://api.github.com'

const FILES_TO_FETCH = [
  'CLAUDE.md',
  '.claude/CLAUDE.md',
  '.claude/settings.json',
  '.claude/settings.local.json',
  '.claudeignore',
]

export function parseRepoUrl(input: string): RepoInput | null {
  const trimmed = input.trim().replace(/\/+$/, '')

  // https://github.com/owner/repo or github.com/owner/repo
  const urlMatch = trimmed.match(
    /(?:https?:\/\/)?github\.com\/([^/\s]+)\/([^/\s#?]+)/,
  )
  if (urlMatch) {
    return {
      owner: urlMatch[1],
      repo: urlMatch[2].replace(/\.git$/, ''),
      branch: '',
    }
  }

  // owner/repo shorthand
  const shortMatch = trimmed.match(/^([^/\s]+)\/([^/\s]+)$/)
  if (shortMatch) {
    return {
      owner: shortMatch[1],
      repo: shortMatch[2],
      branch: '',
    }
  }

  return null
}

async function fetchFile(
  owner: string,
  repo: string,
  path: string,
  branch: string,
): Promise<FetchedFile> {
  const ref = branch ? `?ref=${encodeURIComponent(branch)}` : ''
  const url = `${GITHUB_API}/repos/${owner}/${repo}/contents/${path}${ref}`

  try {
    const res = await fetch(url)
    if (!res.ok) {
      return { path, content: '', size: 0, found: false }
    }
    const data = await res.json()
    if (data.encoding === 'base64' && data.content) {
      const content = atob(data.content.replace(/\n/g, ''))
      return { path, content, size: data.size, found: true }
    }
    return { path, content: '', size: 0, found: false }
  } catch {
    return { path, content: '', size: 0, found: false }
  }
}

async function fetchDefaultBranch(
  owner: string,
  repo: string,
): Promise<{ branch: string; exists: boolean }> {
  try {
    const res = await fetch(`${GITHUB_API}/repos/${owner}/${repo}`)
    if (!res.ok) return { branch: 'main', exists: false }
    const data = await res.json()
    return { branch: data.default_branch || 'main', exists: true }
  } catch {
    return { branch: 'main', exists: false }
  }
}

function countIgnoreEntries(content: string): string[] {
  return content
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#'))
}

function parseSettings(content: string): Record<string, unknown> | null {
  try {
    return JSON.parse(content)
  } catch {
    return null
  }
}

function getGrade(score: number): { letter: string; score: number; color: string } {
  if (score >= 95) return { letter: 'A+', score, color: '#3fb950' }
  if (score >= 85) return { letter: 'A', score, color: '#3fb950' }
  if (score >= 70) return { letter: 'B', score, color: '#d29922' }
  if (score >= 55) return { letter: 'C', score, color: '#d29922' }
  if (score >= 40) return { letter: 'D', score, color: '#f85149' }
  return { letter: 'F', score, color: '#f85149' }
}

function estimateTokens(chars: number): number {
  return Math.ceil(chars / 4)
}

export async function analyzeRepo(
  input: RepoInput,
): Promise<AnalysisResult> {
  const { owner, repo } = input
  const repoInfo = input.branch
    ? { branch: input.branch, exists: true }
    : await fetchDefaultBranch(owner, repo)
  const branch = repoInfo.branch

  const files = await Promise.all(
    FILES_TO_FETCH.map((path) => fetchFile(owner, repo, path, branch)),
  )

  const fileMap = new Map(files.map((f) => [f.path, f]))

  // CLAUDE.md analysis
  const rootClaudeMd = fileMap.get('CLAUDE.md')
  const nestedClaudeMd = fileMap.get('.claude/CLAUDE.md')

  const claudeMdFiles: { path: string; chars: number }[] = []
  if (rootClaudeMd?.found) {
    claudeMdFiles.push({ path: 'CLAUDE.md', chars: rootClaudeMd.content.length })
  }
  if (nestedClaudeMd?.found) {
    claudeMdFiles.push({ path: '.claude/CLAUDE.md', chars: nestedClaudeMd.content.length })
  }

  const primaryClaudeMd = rootClaudeMd?.found ? rootClaudeMd : nestedClaudeMd
  const totalInstructionChars = claudeMdFiles.reduce((sum, f) => sum + f.chars, 0)

  const claudeMd = {
    found: !!primaryClaudeMd?.found,
    charCount: primaryClaudeMd?.found ? primaryClaudeMd.content.length : 0,
    lineCount: primaryClaudeMd?.found
      ? primaryClaudeMd.content.split('\n').length
      : 0,
    overLimit: (primaryClaudeMd?.found ? primaryClaudeMd.content.length : 0) > 4000,
  }

  const claudeMdAll = {
    totalChars: totalInstructionChars,
    fileCount: claudeMdFiles.length,
    overLimit: totalInstructionChars > 12000,
    files: claudeMdFiles,
  }

  // .claudeignore
  const ignoreFile = fileMap.get('.claudeignore')
  const ignoreEntries = ignoreFile?.found
    ? countIgnoreEntries(ignoreFile.content)
    : []
  const claudeIgnore = {
    found: !!ignoreFile?.found,
    entryCount: ignoreEntries.length,
    entries: ignoreEntries,
  }

  // Settings
  const settingsFile = fileMap.get('.claude/settings.json')
  const localSettingsFile = fileMap.get('.claude/settings.local.json')
  const settingsRaw = settingsFile?.found
    ? parseSettings(settingsFile.content)
    : localSettingsFile?.found
      ? parseSettings(localSettingsFile.content)
      : null

  const hasModel = settingsRaw
    ? !!(
        (settingsRaw as Record<string, unknown>).model ||
        (settingsRaw as Record<string, unknown>).preferredModel
      )
    : false

  const hasBudget = settingsRaw
    ? !!(
        (settingsRaw as Record<string, unknown>).maxCost ||
        (settingsRaw as Record<string, unknown>).costLimit ||
        (settingsRaw as Record<string, unknown>).maxMonthlyCost
      )
    : false

  const mcpServersObj = settingsRaw
    ? ((settingsRaw as Record<string, unknown>).mcpServers as Record<string, unknown> | undefined)
    : undefined
  const mcpServerCount = mcpServersObj ? Object.keys(mcpServersObj).length : 0

  const hasHooks = settingsRaw
    ? !!(settingsRaw as Record<string, unknown>).hooks
    : false

  const settings = {
    found: !!settingsRaw,
    hasModel,
    hasBudget,
    mcpServerCount,
    hasHooks,
    raw: settingsRaw,
  }

  // Scoring (same logic as badge.ts)
  let claudeMdScore: number
  if (claudeMd.charCount <= 2000) claudeMdScore = 25
  else if (claudeMd.charCount <= 3000) claudeMdScore = 20
  else if (claudeMd.charCount <= 4000) claudeMdScore = 15
  else if (claudeMd.charCount <= 6000) claudeMdScore = 10
  else if (claudeMd.charCount <= 8000) claudeMdScore = 5
  else claudeMdScore = 0

  let ignoreScore: number
  if (claudeIgnore.entryCount >= 5) ignoreScore = 25
  else if (claudeIgnore.entryCount >= 1) ignoreScore = 15
  else ignoreScore = 0

  let settingsScore: number
  if (hasModel && hasBudget) settingsScore = 25
  else if (hasModel) settingsScore = 15
  else settingsScore = 0

  let mcpScore: number
  if (mcpServerCount <= 3) mcpScore = 25
  else if (mcpServerCount <= 5) mcpScore = 20
  else if (mcpServerCount <= 8) mcpScore = 15
  else if (mcpServerCount <= 12) mcpScore = 10
  else mcpScore = 0

  const totalScore = claudeMdScore + ignoreScore + settingsScore + mcpScore
  const grade = getGrade(totalScore)

  // Token estimation
  const claudeMdTokens = estimateTokens(totalInstructionChars)
  const mcpTokens = mcpServerCount * TOKEN_ESTIMATES.tokensPerMcpServer
  const systemPromptTokens =
    TOKEN_ESTIMATES.systemPromptTokens + claudeMdTokens + mcpTokens

  const perTurnTokens =
    TOKEN_ESTIMATES.tokensPerFileRead +
    TOKEN_ESTIMATES.outputTokensPerTurn +
    TOKEN_ESTIMATES.historyGrowthPerTurn

  const turns = 30
  const inputTokensSession =
    systemPromptTokens * turns +
    (turns * (turns - 1) * TOKEN_ESTIMATES.historyGrowthPerTurn) / 2 +
    TOKEN_ESTIMATES.tokensPerFileRead * turns
  const outputTokensSession = TOKEN_ESTIMATES.outputTokensPerTurn * turns

  const cacheHitRate = TOKEN_ESTIMATES.cacheHitRate
  const cachedInput = inputTokensSession * cacheHitRate
  const uncachedInput = inputTokensSession * (1 - cacheHitRate)

  const tokenEstimate = {
    systemPromptTokens,
    perTurnTokens,
    sessionTokens30Turns: inputTokensSession + outputTokensSession,
  }

  // Cost per model
  const sessionsPerDay = 3
  const workingDays = 22

  const costEstimate = {} as Record<ModelId, { perSession: number; perMonth: number }>
  for (const modelId of Object.keys(MODELS) as ModelId[]) {
    const model = MODELS[modelId]
    const inputCost = (uncachedInput / 1_000_000) * model.inputPer1M
    const cacheCost = (cachedInput / 1_000_000) * model.cacheHitPer1M
    const outputCost = (outputTokensSession / 1_000_000) * model.outputPer1M
    const perSession = inputCost + cacheCost + outputCost
    costEstimate[modelId] = {
      perSession: Math.round(perSession * 100) / 100,
      perMonth: Math.round(perSession * sessionsPerDay * workingDays * 100) / 100,
    }
  }

  // Recommendations
  const recommendations: string[] = []

  if (!claudeMd.found) {
    recommendations.push(
      'Create a CLAUDE.md file at your repo root. This gives Claude project context and reduces back-and-forth tokens.',
    )
  } else if (claudeMd.overLimit) {
    recommendations.push(
      `Your CLAUDE.md is ${claudeMd.charCount.toLocaleString()} characters -- over the 4,000 char hard limit. Content beyond 4K is silently truncated. Trim it down.`,
    )
  } else if (claudeMd.charCount > 3000) {
    recommendations.push(
      `CLAUDE.md is ${claudeMd.charCount.toLocaleString()} chars (limit: 4,000). Consider trimming to stay safely under the limit.`,
    )
  }

  if (claudeMdAll.overLimit) {
    recommendations.push(
      `Total instruction files are ${claudeMdAll.totalChars.toLocaleString()} chars -- over the 12,000 char total limit. Split into essentials only.`,
    )
  }

  if (!claudeIgnore.found) {
    recommendations.push(
      'Add a .claudeignore file. Exclude build outputs, node_modules, lock files, and generated code to reduce context loading.',
    )
  } else if (claudeIgnore.entryCount < 5) {
    recommendations.push(
      `Only ${claudeIgnore.entryCount} .claudeignore entries. Aim for 5+ patterns to exclude build artifacts, vendor dirs, and large generated files.`,
    )
  }

  if (!settings.found) {
    recommendations.push(
      'Create .claude/settings.json to configure default model and budget caps.',
    )
  } else {
    if (!hasModel) {
      recommendations.push(
        'Set a default model in settings to avoid accidentally using expensive models for simple tasks.',
      )
    }
    if (!hasBudget) {
      recommendations.push(
        'Set a budget cap (maxCost or maxMonthlyCost) in settings to prevent runaway costs.',
      )
    }
  }

  if (mcpServerCount > 3) {
    recommendations.push(
      `${mcpServerCount} MCP servers configured -- each adds ~1,500 tokens/turn to the system prompt. Disable servers you don't use every session.`,
    )
  }

  if (!hasHooks && settings.found) {
    recommendations.push(
      'Consider adding hooks for budget tracking. PreToolUse hooks can warn when costs are high.',
    )
  }

  if (recommendations.length === 0) {
    recommendations.push(
      'Your setup looks well-optimized. Keep CLAUDE.md concise and .claudeignore up to date as your project grows.',
    )
  }

  return {
    repo: `${owner}/${repo}`,
    branch,
    files,
    claudeMd,
    claudeMdAll,
    claudeIgnore,
    settings,
    repoExists: repoInfo.exists,
    grade,
    tokenEstimate,
    costEstimate,
    recommendations,
  }
}
