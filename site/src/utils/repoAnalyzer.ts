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
    /** Primary file is over Anthropic's 200-line guidance. */
    overGuidance: boolean
  }
  claudeMdAll: {
    totalChars: number
    /** Estimated as ceil(totalChars / 4). */
    totalTokens: number
    fileCount: number
    files: { path: string; chars: number }[]
  }
  fileReadExclusions: {
    /** Read(...) entries in permissions.deny. */
    readDenyRules: string[]
    lockFilesPresent: string[]
    lockFilesUncovered: string[]
    /** A .claudeignore is committed. Claude Code does not read it. */
    ignoreFileFound: boolean
    /** Its patterns converted to Read deny rules, for migration. */
    ignoreFileRules: string[]
  }
  settings: {
    found: boolean
    hasModel: boolean
    hasCostControls: boolean
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
// The only origin this module is ever allowed to call. Every request is checked
// against it after URL parsing, so no combination of user input can retarget a
// fetch at another host.
const GITHUB_ORIGIN = new URL(GITHUB_API).origin

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

/**
 * Builds a GitHub API URL, or returns null if any part fails validation.
 *
 * `analyzeRepo` is exported and takes plain strings, so validating only inside
 * `parseRepoUrl` leaves a path where unchecked input reaches the request URL.
 * Re-checking here puts the gate on the URL itself: every request in this
 * module goes through this function, and callers treat null as "not found".
 *
 * Three layers, because string concatenation alone is easy to get wrong:
 *   1. owner/repo must match the GitHub character rules, and no segment may be
 *      ".." -- REPO_PATTERN permits dots, and `new URL` resolves ".." by walking
 *      up a path segment, so a repo of ".." would otherwise escape /repos/.
 *   2. Each segment is encoded individually, then resolved against a fixed base
 *      so the caller supplies only a path, never a scheme or host.
 *   3. The resulting origin must equal GITHUB_ORIGIN. This is the backstop: even
 *      if a segment smuggled in "//evil.test" or a scheme, the parsed origin
 *      would differ and the request is dropped before it is made.
 */
function buildApiUrl(
  owner: string,
  repo: string,
  segments: string[] = [],
  query: Record<string, string> = {},
): URL | null {
  if (!OWNER_PATTERN.test(owner) || !REPO_PATTERN.test(repo)) return null

  const allSegments = ['repos', owner, repo, ...segments]
  if (allSegments.some((s) => s === '..' || s === '.' || s === '')) return null

  const path = allSegments.map(encodeURIComponent).join('/')

  let url: URL
  try {
    url = new URL(path, `${GITHUB_API}/`)
  } catch {
    return null
  }
  if (url.origin !== GITHUB_ORIGIN) return null

  for (const [key, value] of Object.entries(query)) {
    url.searchParams.set(key, value)
  }
  return url
}

function validateRepoInput(owner: string, repo: string): RepoInput | null {
  const cleanRepo = repo.replace(/\.git$/, '')
  if (!OWNER_PATTERN.test(owner) || !REPO_PATTERN.test(cleanRepo)) {
    return null
  }
  if (cleanRepo.includes('..')) {
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
  const safeBranch = sanitizeBranch(branch)
  const url = buildApiUrl(
    owner,
    repo,
    ['contents', ...path.split('/')],
    safeBranch ? { ref: safeBranch } : {},
  )
  if (!url) {
    return { path, content: '', size: 0, found: false }
  }

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
  const url = buildApiUrl(owner, repo)
  if (!url) return { branch: 'main', exists: false }
  try {
    const res = await fetch(url)
    if (!res.ok) return { branch: 'main', exists: false }
    const data = await res.json()
    // The response is remote data, so it is a taint source in its own right --
    // it flows straight back into the tree and contents URLs. Run it through
    // the same ref check as user input and fall back to 'main' if it fails.
    return { branch: sanitizeBranch(String(data.default_branch ?? '')) || 'main', exists: true }
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
  const url = buildApiUrl(
    owner,
    repo,
    ['git', 'trees', safeBranch],
    { recursive: '1' },
  )
  if (!url) return []
  try {
    const res = await fetch(url)
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

/** Line endings normalized the way Python's text mode reads them, so counts match the CLI graders. */
function normalizeNewlines(text: string): string {
  return text.replace(/\r\n?/g, '\n')
}

/** Line count matching Python's str.splitlines(): a trailing newline does not start a new line. */
function countLines(text: string): number {
  if (!text) return 0
  const lines = normalizeNewlines(text).split('\n')
  return lines[lines.length - 1] === '' ? lines.length - 1 : lines.length
}

const READ_RULE = /^Read\(.+\)$/

/** Read(...) entries of permissions.deny in a parsed settings object. */
function readDenyRules(settings: Record<string, unknown> | null): string[] {
  const perms = settings?.permissions
  const deny = perms && typeof perms === 'object' ? (perms as Record<string, unknown>).deny : undefined
  if (!Array.isArray(deny)) return []
  return deny.filter((r): r is string => typeof r === 'string' && READ_RULE.test(r))
}

/**
 * Converts ignore-file patterns to Read deny rules: `dir/` -> Read(./dir/**);
 * a pattern containing `/` elsewhere -> Read(./pattern) with any leading `/`
 * stripped; a bare name or glob -> Read(pattern), which matches at any depth.
 * Blank lines, comments and `!` negations are skipped.
 */
function ignorePatternsAsReadRules(content: string): string[] {
  const rules: string[] = []
  for (const line of normalizeNewlines(content).split('\n')) {
    const s = line.trim()
    if (!s || s.startsWith('#') || s.startsWith('!')) continue
    if (s.endsWith('/')) rules.push(`Read(./${s.slice(0, -1).replace(/^\//, '')}/**)`)
    else if (s.includes('/')) rules.push(`Read(./${s.replace(/^\//, '')})`)
    else rules.push(`Read(${s})`)
  }
  return rules
}

// Claude Code does not read this file. It is fetched only to flag it and convert its patterns.
const IGNORE_FILE = '.claudeignore'
const IGNORE_FILE_FINDING =
  "`.claudeignore` is not read by Claude Code -- it appears nowhere in Claude Code's documentation. Move its patterns into permissions.deny as Read(...) rules."

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

const CLAUDE_MD_LINE_GUIDANCE = 200

function scoreClaudeMd(primaryLines: number, totalTokens: number, found: boolean): CategoryScore {
  let score = 0
  if (found) {
    if (primaryLines <= 100) score += 12
    else if (primaryLines <= CLAUDE_MD_LINE_GUIDANCE) score += 10
    else if (primaryLines <= 300) score += 6
    else if (primaryLines <= 500) score += 3
    else score += 1

    if (totalTokens <= 2000) score += 8
    else if (totalTokens <= 4000) score += 6
    else if (totalTokens <= 8000) score += 4
    else if (totalTokens <= 16000) score += 2
  }
  const detail = found
    ? `${primaryLines.toLocaleString()} lines (~${totalTokens.toLocaleString()} tokens total)`
    : 'not found'
  return { name: 'CLAUDE.md', score, maxScore: 20, detail }
}

function scoreFileReadExclusions(f: AnalysisResult['fileReadExclusions']): CategoryScore {
  const count = f.readDenyRules.length
  let score = 0
  if (count >= 10) score = 13
  else if (count >= 5) score = 10
  else if (count >= 1) score = 6
  // Lock-file bonus: every lock file at the root is covered (vacuously true when none exist).
  if (count >= 1 && f.lockFilesUncovered.length === 0) score += 2
  score = Math.min(score, 15)

  let detail = 'no Read deny rules in permissions.deny'
  if (count > 0) {
    let lockNote = 'lock files covered'
    if (f.lockFilesPresent.length === 0) lockNote = 'no lock files at root'
    else if (f.lockFilesUncovered.length > 0) {
      lockNote = `lock files not covered: ${f.lockFilesUncovered.join(', ')}`
    }
    detail = `${count} Read deny rule(s); ${lockNote}`
  }
  return { name: 'File-read exclusions', score, maxScore: 15, detail }
}

/**
 * Whether settings.json configures a real spend-bounding setting.
 *
 * Mirrors `_cost_control_signals` in tools/claude-rate/rate.py and
 * `has_cost_controls` in tools/badge-generator/generate.py. Change all three
 * together or the CLI, the badge and the web analyzer will disagree.
 */
export function computeCostControls(s: Record<string, unknown>): boolean {
  // Reasoning tokens bill at the output rate and effort defaults to "high", so
  // pinning below that is the biggest lever here after model choice.
  const effort = s.effortLevel
  if (typeof effort === 'string' && ['low', 'medium'].includes(effort.trim().toLowerCase())) {
    return true
  }
  // Fast Mode is a flat 2x on input and output.
  if (s.fastMode === false) return true
  if (s.alwaysThinkingEnabled === false) return true
  // The closest real analogue of a spend cap: an enforced allowlist can keep
  // Opus- and Fable-tier models out of a project entirely.
  if (s.enforceAvailableModels === true && Array.isArray(s.availableModels) && s.availableModels.length > 0) {
    return true
  }
  // Bounds the context growth that drives per-turn input cost.
  if (s.autoCompactEnabled === true) return true
  return false
}

function scoreSettings(
  found: boolean,
  hasModel: boolean,
  hasCostControls: boolean,
): CategoryScore {
  let score = 0
  if (found) score += 5
  if (hasModel) score += 5
  if (hasCostControls) score += 5
  const parts = found
    ? [
        `model ${hasModel ? 'set' : 'not set'}`,
        `cost controls ${hasCostControls ? 'set' : 'not set'}`,
      ]
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
    detail: `${count} configured`,
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
  // An explicit branch skips the repo lookup, so without this check a rejected
  // owner/repo would report exists: true and render an empty analysis as if the
  // repo were real. Surface it as not-found instead.
  const inputIsValid = buildApiUrl(owner, repo) !== null
  const repoInfo =
    requestedBranch && inputIsValid
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
    IGNORE_FILE,
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

  // Chars and lines are counted on newline-normalized text, as the Python graders read it.
  const claudeMdFiles: { path: string; chars: number }[] = []
  if (rootClaudeMd?.found) {
    claudeMdFiles.push({ path: 'CLAUDE.md', chars: normalizeNewlines(rootClaudeMd.content).length })
  }
  if (nestedClaudeMd?.found) {
    claudeMdFiles.push({
      path: '.claude/CLAUDE.md',
      chars: normalizeNewlines(nestedClaudeMd.content).length,
    })
  }

  const primaryClaudeMd = rootClaudeMd?.found ? rootClaudeMd : nestedClaudeMd
  const totalInstructionChars = claudeMdFiles.reduce((sum, f) => sum + f.chars, 0)
  const primaryText = primaryClaudeMd?.found ? normalizeNewlines(primaryClaudeMd.content) : ''
  const primaryLines = countLines(primaryText)

  const claudeMd = {
    found: !!primaryClaudeMd?.found,
    charCount: primaryText.length,
    lineCount: primaryLines,
    overGuidance: primaryLines > CLAUDE_MD_LINE_GUIDANCE,
  }

  const claudeMdAll = {
    totalChars: totalInstructionChars,
    totalTokens: estimateTokens(totalInstructionChars),
    fileCount: claudeMdFiles.length,
    files: claudeMdFiles,
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

  // Kept in step with `_cost_control_signals` in tools/claude-rate/rate.py and
  // `has_cost_controls` in tools/badge-generator/generate.py. This used to test
  // maxCost / costLimit / maxMonthlyCost; none of those is in the Claude Code
  // settings schema (checked 2026-09-06 against schemastore, 142 top-level
  // properties, no spend cap among them), so it scored a key the product
  // ignores. Value-aware on purpose: fastMode true doubles the bill and
  // effortLevel "max" raises it, so the key being present is not enough.
  const hasCostControls = settingsRaw ? computeCostControls(settingsRaw) : false

  // File-read exclusions: Read(...) rules in permissions.deny. A committed
  // .claudeignore scores nothing (Claude Code does not read it); its patterns
  // are only converted so the page can show the rules to migrate to.
  const denyRules = readDenyRules(settingsRaw)
  const ignoreFile = fileMap.get(IGNORE_FILE)
  const fileReadExclusions = {
    readDenyRules: denyRules,
    lockFilesPresent: detection.lockFilesPresent,
    lockFilesUncovered: detection.lockFilesPresent.filter(
      (lf) => !denyRules.some((r) => r.includes(lf) || r.includes('*.lock') || r.includes('*lock*')),
    ),
    ignoreFileFound: !!ignoreFile?.found,
    ignoreFileRules: ignoreFile?.found ? ignorePatternsAsReadRules(ignoreFile.content) : [],
  }

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
    hasCostControls,
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
    scoreClaudeMd(claudeMd.lineCount, claudeMdAll.totalTokens, claudeMd.found),
    scoreFileReadExclusions(fileReadExclusions),
    scoreSettings(settings.found, hasModel, hasCostControls),
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
    fileReadExclusions,
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
    fileReadExclusions,
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
  fileReadExclusions: AnalysisResult['fileReadExclusions']
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
  } else if (r.claudeMd.overGuidance) {
    recs.push(
      `${r.claudeMd.lineCount} lines -- over Anthropic's 200-line guidance for CLAUDE.md. Longer files consume more context and reduce adherence. Move workflow-specific instructions into skills or path-scoped .claude/rules/ so they load on demand.`,
    )
  }
  if (r.claudeMd.found && r.claudeMdAll.totalTokens > 2000) {
    recs.push(
      `Your CLAUDE.md files total ~${r.claudeMdAll.totalTokens.toLocaleString()} tokens and load in full at the start of every session. Delete duplication and drop low-value rules; 2,000 tokens or fewer scores full marks.`,
    )
  }
  const f = r.fileReadExclusions
  if (f.ignoreFileFound) {
    recs.push(
      `${IGNORE_FILE_FINDING} The File-read exclusions panel lists its patterns converted to Read rules.`,
    )
  } else if (f.readDenyRules.length === 0) {
    recs.push(
      'Add Read(...) rules to permissions.deny in .claude/settings.json to keep Claude\'s file tools out of dependency, build and generated paths, e.g. Read(./node_modules/**), Read(./dist/**), Read(*.min.js). No published measurement exists for what they save; the effect depends on how often Claude would otherwise open those files.',
    )
  }
  if (f.readDenyRules.length > 0 && f.lockFilesUncovered.length > 0) {
    const lockRules = f.lockFilesUncovered.map((lf) => 'Read(./' + lf + ')').join(', ')
    recs.push(`Add a Read deny rule for each lock file at the repo root: ${lockRules}.`)
  }
  return recs
}

function configRecommendations(r: RecommendationInput): string[] {
  const recs: string[] = []
  if (!r.settings.found) {
    recs.push('Create .claude/settings.json to pin a default model and set cost controls.')
  } else {
    if (!r.settings.hasModel) {
      recs.push(
        'Set a default model in settings to avoid accidentally using expensive models for simple tasks.',
      )
    }
    if (!r.settings.hasCostControls) {
      recs.push(
        'Add cost controls Claude Code actually reads. There is no spend-cap setting, so maxMonthlyCost and budgetCap are silently ignored: use "effortLevel": "medium" (reasoning tokens bill as output), "fastMode": false (declines the flat 2x), "autoCompactEnabled": true, or "enforceAvailableModels" with "availableModels" to keep Opus- and Fable-tier models out. A real spend ceiling needs a PreToolUse hook, not a setting.',
      )
    }
  }
  if (r.mcpServerCount > 3) {
    recs.push(
      `${r.mcpServerCount} MCP servers configured. With tool search on (the default), each adds its tool names and server instructions to context; full tool schemas load up front only when tool search is off. Prefer CLI tools (gh, aws, gcloud, sentry-cli) where they exist, and disable servers you don't use every session with /mcp.`,
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
      'Your setup looks well-optimized. Keep CLAUDE.md under 200 lines and your Read deny rules up to date as your project grows.',
    )
  }
  return recommendations
}
