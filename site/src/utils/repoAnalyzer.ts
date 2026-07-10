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

export interface CategoryScore {
  name: string
  score: number
  maxScore: number
  detail: string
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
    hookCount: number
    raw: Record<string, unknown> | null
  }
  tooling: {
    costModeInstalled: boolean
    skills: string[]
    commandCount: number
    agentCount: number
    agents: string[]
    hasPluginMetadata: boolean
    hookScripts: number
  }
  security: {
    envTracked: boolean
    keyLeakFiles: string[]
  }
  categories: CategoryScore[]
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

// GitHub constraints: owner is alphanumeric/hyphen (max 39), repo is
// alphanumeric/hyphen/underscore/dot (max 100). Validating here keeps
// user input from reaching the request URL unchecked.
const OWNER_PATTERN = /^[a-zA-Z0-9-]{1,39}$/
const REPO_PATTERN = /^[a-zA-Z0-9._-]{1,100}$/
// Git ref names: path-like segments of word chars, dots, dashes.
const BRANCH_PATTERN = /^[a-zA-Z0-9._/-]{1,250}$/

/** Returns the branch if it looks like a valid git ref, else the safe default. */
export function sanitizeBranch(branch: string): string {
  const trimmed = branch.trim()
  if (!trimmed) return ''
  return BRANCH_PATTERN.test(trimmed) && !trimmed.includes('..') ? trimmed : ''
}

function validateRepoInput(owner: string, repo: string): RepoInput | null {
  const cleanRepo = repo.replace(/\.git$/, '')
  if (!OWNER_PATTERN.test(owner) || !REPO_PATTERN.test(cleanRepo)) {
    return null
  }
  return { owner, repo: cleanRepo, branch: '' }
}

export function parseRepoUrl(input: string): RepoInput | null {
  const trimmed = input.trim().replace(/\/+$/, '')

  // https://github.com/owner/repo or github.com/owner/repo
  const urlMatch = /(?:https?:\/\/)?github\.com\/([^/\s]+)\/([^/\s#?]+)/.exec(trimmed)
  if (urlMatch) {
    return validateRepoInput(urlMatch[1], urlMatch[2])
  }

  // owner/repo shorthand
  const shortMatch = /^([^/\s]+)\/([^/\s]+)$/.exec(trimmed)
  if (shortMatch) {
    return validateRepoInput(shortMatch[1], shortMatch[2])
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
  const encodedPath = path.split('/').map(encodeURIComponent).join('/')
  const url = `${GITHUB_API}/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/contents/${encodedPath}${ref}`

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
    const res = await fetch(
      `${GITHUB_API}/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`,
    )
    if (!res.ok) return { branch: 'main', exists: false }
    const data = await res.json()
    return { branch: data.default_branch || 'main', exists: true }
  } catch {
    return { branch: 'main', exists: false }
  }
}

/** One recursive trees call gives every path in the repo -- the backbone of deep detection. */
async function fetchTree(
  owner: string,
  repo: string,
  branch: string,
): Promise<string[]> {
  const safeBranch = sanitizeBranch(branch)
  if (!safeBranch) return []
  try {
    const res = await fetch(
      `${GITHUB_API}/repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/git/trees/${encodeURIComponent(safeBranch)}?recursive=1`,
    )
    if (!res.ok) return []
    const data = await res.json()
    if (!Array.isArray(data.tree)) return []
    return data.tree
      .filter((e: { type: string }) => e.type === 'blob')
      .map((e: { path: string }) => e.path)
  } catch {
    return []
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

function countHookEntries(hooks: unknown): number {
  if (!hooks || typeof hooks !== 'object') return 0
  let count = 0
  for (const value of Object.values(hooks as Record<string, unknown>)) {
    if (Array.isArray(value)) count += value.length
    else if (value) count += 1
  }
  return count
}

// Obvious credential shapes worth flagging in config files.
const API_KEY_PATTERN = /sk-ant-[a-zA-Z0-9-]{10,}|sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36}/

// -- Tree-based detection ----------------------------------------------------

interface TreeDetection {
  skills: string[]
  costModeInstalled: boolean
  commandCount: number
  agents: string[]
  hasPluginMetadata: boolean
  hookScripts: number
  hasMcpJson: boolean
  envTracked: boolean
  lockFilesPresent: string[]
}

// skills/<name>/SKILL.md or .claude/skills/<name>/SKILL.md
const SKILL_PATH = /^(?:\.claude\/)?skills\/([^/]+)\/SKILL\.md$/
// .claude/agents/<name>.md
const AGENT_PATH = /^\.claude\/agents\/([^/]+)\.md$/
const COMMAND_PATH = /^\.claude\/commands\/[^/]+\.md$/
// Only .claude/hooks/ counts -- a root hooks/ dir is usually distribution
// content (git hooks, examples), not installed Claude Code hooks.
const HOOK_SCRIPT_PATH = /^\.claude\/hooks\/[^/]+\.(sh|py|js|ts)$/
const TRACKED_ENV_PATH = /^\.env\.(?!example|sample|template)[^/]*$/
const PLUGIN_METADATA_PATHS = new Set([
  '.claude-plugin/marketplace.json',
  '.claude-plugin/plugin.json',
])
const LOCK_FILE_NAMES = new Set([
  'package-lock.json',
  'pnpm-lock.yaml',
  'yarn.lock',
  'poetry.lock',
  'Cargo.lock',
  'uv.lock',
])

function detectFromTree(paths: string[]): TreeDetection {
  const skills = new Set<string>()
  const agents = new Set<string>()

  for (const p of paths) {
    const skillMatch = SKILL_PATH.exec(p)
    if (skillMatch) skills.add(skillMatch[1])
    const agentMatch = AGENT_PATH.exec(p)
    if (agentMatch) agents.add(agentMatch[1])
  }

  return {
    skills: [...skills].sort((a, b) => a.localeCompare(b)),
    costModeInstalled: skills.has('cost-mode'),
    commandCount: paths.filter((p) => COMMAND_PATH.test(p)).length,
    agents: [...agents].sort((a, b) => a.localeCompare(b)),
    hasPluginMetadata: paths.some((p) => PLUGIN_METADATA_PATHS.has(p)),
    hookScripts: paths.filter((p) => HOOK_SCRIPT_PATH.test(p)).length,
    hasMcpJson: paths.includes('.mcp.json'),
    envTracked: paths.some((p) => p === '.env' || TRACKED_ENV_PATH.test(p)),
    lockFilesPresent: paths.filter((p) => LOCK_FILE_NAMES.has(p)),
  }
}

// -- Category scoring (mirrors tools/claude-rate rubric: 7 categories, 100 pts)

function scoreClaudeMd(primaryChars: number, totalChars: number, found: boolean): CategoryScore {
  let score = 0
  if (found) {
    if (primaryChars <= 2000) score += 12
    else if (primaryChars <= 3000) score += 10
    else if (primaryChars <= 4000) score += 7
    else if (primaryChars <= 6000) score += 3
    else if (primaryChars <= 8000) score += 1

    if (totalChars <= 6000) score += 8
    else if (totalChars <= 9000) score += 6
    else if (totalChars <= 12000) score += 4
    else if (totalChars <= 16000) score += 2
  }
  const detail = found
    ? `${primaryChars.toLocaleString()} chars (${totalChars.toLocaleString()} total)`
    : 'not found'
  return { name: 'CLAUDE.md', score, maxScore: 20, detail }
}

function scoreClaudeIgnore(
  found: boolean,
  entryCount: number,
  entries: string[],
  lockFilesPresent: string[],
): CategoryScore {
  let score = 0
  let detail = 'not found'
  if (found) {
    if (entryCount >= 10) score = 13
    else if (entryCount >= 5) score = 10
    else if (entryCount >= 1) score = 6

    // Coverage bonus: every lock file in the repo is ignored (vacuously true when none exist).
    const coversLocks = lockFilesPresent.every((lf) =>
      entries.some((e) => e.includes(lf) || e.includes('*.lock')),
    )
    if (coversLocks && entryCount >= 1) score += 2
    score = Math.min(score, 15)
    const lockNote = coversLocks
      ? ''
      : `; lock files not covered (${lockFilesPresent.join(', ')})`
    detail = `${entryCount} entries${lockNote}`
  }
  return { name: '.claudeignore', score, maxScore: 15, detail }
}

function scoreSettings(found: boolean, hasModel: boolean, hasBudget: boolean): CategoryScore {
  let score = 0
  if (found) score += 5
  if (hasModel) score += 5
  if (hasBudget) score += 5
  const parts = found
    ? [`model ${hasModel ? 'set' : 'not set'}`, `budget ${hasBudget ? 'set' : 'not set'}`]
    : ['not found']
  return { name: 'Settings', score, maxScore: 15, detail: parts.join(', ') }
}

function scoreMcp(count: number): CategoryScore {
  let score: number
  if (count <= 3) score = 15
  else if (count <= 5) score = 12
  else if (count <= 8) score = 8
  else if (count <= 12) score = 4
  else score = 0
  return {
    name: 'MCP servers',
    score,
    maxScore: 15,
    detail: `${count} configured (~${(count * TOKEN_ESTIMATES.tokensPerMcpServer).toLocaleString()} tokens/turn)`,
  }
}

function scoreHooks(hookCount: number, hookScripts: number): CategoryScore {
  const effective = Math.max(hookCount, hookScripts > 0 ? 1 : 0)
  let score = 0
  if (effective >= 3) score = 10
  else if (effective >= 1) score = 6
  const detail =
    effective > 0
      ? `${hookCount} settings entries, ${hookScripts} scripts`
      : 'none configured'
  return { name: 'Hooks', score, maxScore: 10, detail }
}

function scoreSecurity(envTracked: boolean, keyLeakFiles: string[]): CategoryScore {
  let score = 10
  const problems: string[] = []
  if (envTracked) {
    score -= 5
    problems.push('.env committed to the repo')
  }
  if (keyLeakFiles.length > 0) {
    score -= 5
    problems.push(`API key pattern in ${keyLeakFiles.join(', ')}`)
  }
  return {
    name: 'Security',
    score: Math.max(score, 0),
    maxScore: 10,
    detail: problems.length ? problems.join('; ') : 'no leaks detected',
  }
}

function scoreTooling(t: TreeDetection): CategoryScore {
  let score = 0
  const found: string[] = []
  if (t.costModeInstalled) {
    score += 5
    found.push('cost-mode skill')
  }
  if (t.commandCount >= 3) {
    score += 4
    found.push(`${t.commandCount} commands`)
  } else if (t.commandCount >= 1) {
    score += 2
    found.push(`${t.commandCount} command(s)`)
  }
  if (t.agents.length > 0) {
    score += 3
    found.push(`${t.agents.length} agent(s)`)
  }
  if (t.hasPluginMetadata) {
    score += 3
    found.push('plugin metadata')
  }
  return {
    name: 'Optimizer tooling',
    score: Math.min(score, 15),
    maxScore: 15,
    detail: found.length ? found.join(', ') : 'no skills, commands, agents, or plugin metadata',
  }
}

// -- Main analysis -----------------------------------------------------------

export async function analyzeRepo(
  input: RepoInput,
): Promise<AnalysisResult> {
  const { owner, repo } = input
  const requestedBranch = sanitizeBranch(input.branch)
  const repoInfo = requestedBranch
    ? { branch: requestedBranch, exists: true }
    : await fetchDefaultBranch(owner, repo)
  const branch = repoInfo.branch

  // One recursive tree call -> full file listing for deep detection.
  const treePaths = await fetchTree(owner, repo, branch)
  const treeSet = new Set(treePaths)
  const detection = detectFromTree(treePaths)

  // Fetch content only for files the tree says exist (saves rate limit).
  const contentTargets = [
    'CLAUDE.md',
    '.claude/CLAUDE.md',
    '.claude/settings.json',
    '.claude/settings.local.json',
    '.claudeignore',
    '.mcp.json',
  ]
  const files = await Promise.all(
    contentTargets.map((path) =>
      treeSet.size === 0 || treeSet.has(path)
        ? fetchFile(owner, repo, path, branch)
        : Promise.resolve({ path, content: '', size: 0, found: false }),
    ),
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
  let settingsRaw: Record<string, unknown> | null = null
  if (settingsFile?.found) settingsRaw = parseSettings(settingsFile.content)
  else if (localSettingsFile?.found) settingsRaw = parseSettings(localSettingsFile.content)

  const hasModel = settingsRaw
    ? !!(settingsRaw.model || settingsRaw.preferredModel)
    : false

  const hasBudget = settingsRaw
    ? !!(settingsRaw.maxCost || settingsRaw.costLimit || settingsRaw.maxMonthlyCost)
    : false

  // MCP servers: .mcp.json is the canonical location; settings.json is legacy.
  const mcpFile = fileMap.get('.mcp.json')
  const mcpRaw = mcpFile?.found ? parseSettings(mcpFile.content) : null
  const mcpFromFile =
    mcpRaw && typeof mcpRaw.mcpServers === 'object' && mcpRaw.mcpServers
      ? Object.keys(mcpRaw.mcpServers as Record<string, unknown>).length
      : 0
  const mcpFromSettings =
    settingsRaw && typeof settingsRaw.mcpServers === 'object' && settingsRaw.mcpServers
      ? Object.keys(settingsRaw.mcpServers as Record<string, unknown>).length
      : 0
  const mcpServerCount = mcpFromFile + mcpFromSettings

  const hookCount = settingsRaw ? countHookEntries(settingsRaw.hooks) : 0
  const hasHooks = hookCount > 0 || detection.hookScripts > 0

  const settings = {
    found: !!settingsRaw,
    hasModel,
    hasBudget,
    mcpServerCount,
    hasHooks,
    hookCount,
    raw: settingsRaw,
  }

  // Security: obvious key shapes in the config files we fetched.
  const keyLeakFiles = files
    .filter((f) => f.found && API_KEY_PATTERN.test(f.content))
    .map((f) => f.path)

  const security = {
    envTracked: detection.envTracked,
    keyLeakFiles,
  }

  const tooling = {
    costModeInstalled: detection.costModeInstalled,
    skills: detection.skills,
    commandCount: detection.commandCount,
    agentCount: detection.agents.length,
    agents: detection.agents,
    hasPluginMetadata: detection.hasPluginMetadata,
    hookScripts: detection.hookScripts,
  }

  // Scoring: 7 categories, 100 points -- same rubric as the claude-rate CLI.
  const categories: CategoryScore[] = [
    scoreClaudeMd(claudeMd.charCount, totalInstructionChars, claudeMd.found),
    scoreClaudeIgnore(
      claudeIgnore.found,
      claudeIgnore.entryCount,
      ignoreEntries,
      detection.lockFilesPresent,
    ),
    scoreSettings(settings.found, hasModel, hasBudget),
    scoreMcp(mcpServerCount),
    scoreHooks(hookCount, detection.hookScripts),
    scoreSecurity(detection.envTracked, keyLeakFiles),
    scoreTooling(detection),
  ]
  const totalScore = categories.reduce((sum, c) => sum + c.score, 0)
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

  const recommendations = buildRecommendations({
    claudeMd,
    claudeMdAll,
    claudeIgnore,
    settings,
    tooling,
    security,
    mcpServerCount,
  })

  return {
    repo: `${owner}/${repo}`,
    branch,
    files,
    claudeMd,
    claudeMdAll,
    claudeIgnore,
    settings,
    tooling,
    security,
    categories,
    repoExists: repoInfo.exists,
    grade: { ...grade, score: totalScore },
    tokenEstimate,
    costEstimate,
    recommendations,
  }
}

interface RecommendationInput {
  claudeMd: AnalysisResult['claudeMd']
  claudeMdAll: AnalysisResult['claudeMdAll']
  claudeIgnore: AnalysisResult['claudeIgnore']
  settings: AnalysisResult['settings']
  tooling: AnalysisResult['tooling']
  security: AnalysisResult['security']
  mcpServerCount: number
}

function securityRecommendations(r: RecommendationInput): string[] {
  const recs: string[] = []
  if (r.security.envTracked) {
    recs.push(
      'A .env file is committed to this repo. Remove it, rotate any credentials it contains, and add .env to .gitignore.',
    )
  }
  if (r.security.keyLeakFiles.length > 0) {
    recs.push(
      `An API-key-shaped string appears in ${r.security.keyLeakFiles.join(', ')}. Move secrets to environment variables and rotate the key.`,
    )
  }
  return recs
}

function contextRecommendations(r: RecommendationInput): string[] {
  const recs: string[] = []
  if (!r.claudeMd.found) {
    recs.push(
      'Create a CLAUDE.md file at your repo root. This gives Claude project context and reduces back-and-forth tokens.',
    )
  } else if (r.claudeMd.overLimit) {
    recs.push(
      `Your CLAUDE.md is ${r.claudeMd.charCount.toLocaleString()} characters -- over the 4,000 char hard limit. Content beyond 4K is silently truncated. Trim it down.`,
    )
  } else if (r.claudeMd.charCount > 3000) {
    recs.push(
      `CLAUDE.md is ${r.claudeMd.charCount.toLocaleString()} chars (limit: 4,000). Consider trimming to stay safely under the limit.`,
    )
  }
  if (r.claudeMdAll.overLimit) {
    recs.push(
      `Total instruction files are ${r.claudeMdAll.totalChars.toLocaleString()} chars -- over the 12,000 char total limit. Split into essentials only.`,
    )
  }
  if (!r.claudeIgnore.found) {
    recs.push(
      'Add a .claudeignore file. Exclude build outputs, node_modules, lock files, and generated code to reduce context loading.',
    )
  } else if (r.claudeIgnore.entryCount < 5) {
    recs.push(
      `Only ${r.claudeIgnore.entryCount} .claudeignore entries. Aim for 5+ patterns to exclude build artifacts, vendor dirs, and large generated files.`,
    )
  }
  return recs
}

function configRecommendations(r: RecommendationInput): string[] {
  const recs: string[] = []
  if (!r.settings.found) {
    recs.push('Create .claude/settings.json to configure default model and budget caps.')
  } else {
    if (!r.settings.hasModel) {
      recs.push(
        'Set a default model in settings to avoid accidentally using expensive models for simple tasks.',
      )
    }
    if (!r.settings.hasBudget) {
      recs.push(
        'Set a budget cap (maxCost or maxMonthlyCost) in settings to prevent runaway costs.',
      )
    }
  }
  if (r.mcpServerCount > 3) {
    recs.push(
      `${r.mcpServerCount} MCP servers configured -- each adds ~1,500 tokens/turn to the system prompt. Disable servers you don't use every session.`,
    )
  }
  if (!r.settings.hasHooks) {
    recs.push(
      'Consider adding hooks for budget tracking. PreToolUse hooks can warn when costs are high.',
    )
  }
  return recs
}

function toolingRecommendations(r: RecommendationInput): string[] {
  const recs: string[] = []
  if (!r.tooling.costModeInstalled) {
    recs.push(
      'Install the cost-mode skill for 30-60% savings: npx skills add Sagargupta16/claude-cost-optimizer',
    )
  }
  if (r.tooling.commandCount === 0) {
    recs.push(
      'Add reusable slash commands in .claude/commands/ (e.g. /cost-check, /quick-fix). Saves re-explaining workflows every session.',
    )
  }
  if (r.tooling.agentCount === 0) {
    recs.push(
      'Define custom subagents in .claude/agents/ to isolate expensive searches from your main context window.',
    )
  }
  return recs
}

function buildRecommendations(r: RecommendationInput): string[] {
  const recommendations = [
    ...securityRecommendations(r),
    ...contextRecommendations(r),
    ...configRecommendations(r),
    ...toolingRecommendations(r),
  ]
  if (recommendations.length === 0) {
    recommendations.push(
      'Your setup looks well-optimized. Keep CLAUDE.md concise and .claudeignore up to date as your project grows.',
    )
  }
  return recommendations
}
