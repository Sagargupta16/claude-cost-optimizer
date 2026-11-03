import { MODELS, TOKEN_ESTIMATES, type ModelId, ratesForPrompt, turnInputCost } from './pricing'

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
    /** `file:line repeats file:line` for each exact repeat after normalizing (findings only). */
    repeatedLines: string[]
    /** Estimated tokens (chars / 4) of the repeated lines. */
    repeatedTokens: number
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
    /** Read deny rules detected for this repo (.env, gated generated paths, root lock files). */
    suggestedRules: string[]
    /** The suggested rules the existing ones do not cover yet. */
    missingRules: string[]
  }
  settings: {
    found: boolean
    hasModel: boolean
    hasCostControls: boolean
    mcpServerCount: number
    hasHooks: boolean
    hookCount: number
    raw: Record<string, unknown> | null
    /** A dead env key and the Haiku 5.5 price line (findings only). */
    findings: string[]
    /** Hook handlers that never run, use a relative script path, run claude -p, or an unscoped SessionStart. */
    hookFindings: string[]
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

function stripTrailingSlashes(value: string): string {
  let end = value.length
  while (end > 0 && value[end - 1] === '/') end--
  return value.slice(0, end)
}

export function parseRepoUrl(input: string): RepoInput | null {
  const trimmed = stripTrailingSlashes(input.trim())

  // https://github.com/owner/repo or github.com/owner/repo
  const urlMatch = /github\.com\/([^/\s]+)\/([^/\s#?]+)/.exec(trimmed)
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

interface TreeListing {
  /** Blob paths only: a gitignored directory never appears here. */
  paths: string[]
  /** GitHub cut the listing short, so a missing path may still exist. */
  truncated: boolean
}

/** One recursive trees call gives every path in the repo -- the backbone of deep detection. */
async function fetchTree(
  owner: string,
  repo: string,
  branch: string,
): Promise<TreeListing> {
  const empty = { paths: [], truncated: false }
  const safeBranch = sanitizeBranch(branch)
  if (!safeBranch) return empty
  const url = buildApiUrl(
    owner,
    repo,
    ['git', 'trees', safeBranch],
    { recursive: '1' },
  )
  if (!url) return empty
  try {
    const res = await fetch(url)
    if (!res.ok) return empty
    const data = await res.json()
    if (!Array.isArray(data.tree)) return empty
    return {
      paths: data.tree
        .filter((e: { type: string }) => e.type === 'blob')
        .map((e: { path: string }) => e.path),
      truncated: data.truncated === true,
    }
  } catch {
    return empty
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
const GITIGNORE_FILE = '.gitignore'
const IGNORE_FILE_FINDING =
  "`.claudeignore` is not read by Claude Code -- its permissions docs say the file has no effect. Move its patterns into permissions.deny as Read(...) rules."

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

const LISTED_REFS = 5

function listed(items: string[]): string {
  const shown = items.slice(0, LISTED_REFS).join('; ')
  const more = items.length - LISTED_REFS
  return more > 0 ? `${shown}; and ${more} more` : shown
}

// -- Detected Read deny rules (mirrors _detected_read_deny in tools/claude-rate/rate.py)
//
// A Read deny rule also blocks Edit and Write on the same path (code.claude.com/docs/en/permissions,
// read 2026-11-03), so a folder is suggested only when it is safe to block. The CLI asks git; the
// tree here lists blobs only, so a gitignored folder never shows in it. The site therefore names a
// folder only when the root .gitignore has an exact line for it and no committed file sits under a
// folder of that name. A single-segment rule such as Read(dist/**) matches that name at any depth.

const ENV_DENY = ['Read(./.env)', 'Read(./.env.*)']
const GENERATED_DIRS = [
  'node_modules',
  'dist',
  'build',
  'coverage',
  '.next',
  '.turbo',
  '.venv',
  '__pycache__',
  '.pytest_cache',
  'htmlcov',
  'target',
  'vendor',
  '.dart_tool',
  '.terraform',
  '.gradle',
]
const GENERATED_GLOBS = ['*.min.js', '*.min.css', '*.map', '*.pb.go', '*_pb2.py', '*.g.dart']
const LOCK_ORDER = ['package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'poetry.lock', 'Cargo.lock', 'uv.lock']

/** Shell-style match with * and ? only, the same rule as `_glob_match` in rate.py. */
function globMatch(pattern: string, name: string): boolean {
  const source = pattern.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\?/g, '.')
  return new RegExp(`^${source}$`).test(name)
}

function ignoreLineForms(name: string): string[] {
  return [name, `/${name}`, `${name}/`, `/${name}/`, `**/${name}`, `**/${name}/`]
}

/**
 * Read deny rules that fit a repo: .env, generated folders .gitignore names with nothing
 * committed under them, generated-file globs a committed file matches, and root lock files.
 * Folders are skipped when the tree is unknown or truncated.
 */
export function suggestReadDenyRules(
  treePaths: string[],
  treeComplete: boolean,
  gitignore: string,
  lockFilesPresent: string[],
): string[] {
  const lines = new Set(normalizeNewlines(gitignore).split('\n').map((l) => l.trim()).filter(Boolean))
  const committedDirs = new Set(treePaths.flatMap((p) => p.split('/').slice(0, -1)))
  const dirs = treeComplete
    ? GENERATED_DIRS.filter((d) => ignoreLineForms(d).some((f) => lines.has(f)) && !committedDirs.has(d))
    : []
  const names = treePaths.map((p) => p.slice(p.lastIndexOf('/') + 1))
  const globs = GENERATED_GLOBS.filter((g) => names.some((n) => globMatch(g, n)))
  const locks = LOCK_ORDER.filter((l) => lockFilesPresent.includes(l))
  return [...ENV_DENY, ...dirs.map((d) => `Read(${d}/**)`), ...globs.map((g) => `Read(${g})`), ...locks.map((l) => `Read(./${l})`)]
}

/** Path segments of a Read(...) rule, without the ./, / and ** parts. */
function ruleSegments(rule: string): string[] {
  const inner = rule.slice(rule.indexOf('(') + 1, rule.lastIndexOf(')'))
  return inner.split('/').filter((s) => s !== '' && s !== '.' && s !== '**')
}

/** A suggested rule is already there when an existing rule names or globs its first segment. */
export function denyCovered(candidate: string, rules: string[]): boolean {
  const key = ruleSegments(candidate)[0]
  if (LOCK_FILE_NAMES.has(key)) {
    return rules.some((r) => r.includes(key) || r.includes('*.lock') || r.includes('*lock*'))
  }
  return rules.some((rule) => ruleSegments(rule).some((seg) => globMatch(seg, key)))
}

// -- Repeated lines in the CLAUDE.md files (mirrors _repeated_lines in rate.py, exact repeats only)

const FENCE = /^\s*(```|~~~)/
const LIST_MARKER = /^(?:[-*+]|\d+[.)])\s+/
const DUP_MIN_CHARS = 25

/** Lines as Python's str.splitlines() gives them. */
function splitLines(text: string): string[] {
  if (!text) return []
  const lines = normalizeNewlines(text).split('\n')
  return lines[lines.length - 1] === '' ? lines.slice(0, -1) : lines
}

/** [1-based line number, line] outside frontmatter and fenced code blocks. */
function proseLines(text: string): [number, string][] {
  const lines = splitLines(text)
  let start = 0
  if (lines.length > 0 && lines[0].trim() === '---') {
    const end = lines.findIndex((l, i) => i > 0 && l.trim() === '---')
    start = end === -1 ? 0 : end + 1
  }
  const out: [number, string][] = []
  let fenced = false
  lines.slice(start).forEach((line, i) => {
    if (FENCE.test(line)) fenced = !fenced
    else if (!fenced) out.push([start + i + 1, line])
  })
  return out
}

/** A line as the duplicate check compares it, or null for headings, tables and short lines. */
export function normalizedLine(line: string): string | null {
  let text = line.trim()
  if (text.startsWith('#') || text.startsWith('|') || text.startsWith('<!--')) return null
  text = text.replace(LIST_MARKER, '')
  for (const mark of ['**', '__', '`']) text = text.split(mark).join('')
  text = text.replace(/\s+/g, ' ').trim().toLowerCase().replace(/[.:;,!]+$/, '')
  return text.length >= DUP_MIN_CHARS ? text : null
}

/** `later:line repeats first:line` for each exact repeat, plus the repeated lines' chars. */
export function findRepeatedLines(files: { path: string; content: string }[]): { repeats: string[]; chars: number } {
  const first = new Map<string, string>()
  const repeats: string[] = []
  let chars = 0
  for (const { path, content } of files) {
    for (const [number, line] of proseLines(content)) {
      const norm = normalizedLine(line)
      if (norm === null) continue
      const match = first.get(norm)
      if (match) {
        repeats.push(`${path}:${number} repeats ${match}`)
        chars += line.trim().length
      } else {
        first.set(norm, `${path}:${number}`)
      }
    }
  }
  return { repeats, chars }
}

// -- Hook hygiene (mirrors checks 1, 3, 6 and 7 of _hook_problems in rate.py) --------
//
// From code.claude.com/docs/en/hooks, read 2026-11-03: each handler is an object with a
// "type" inside a matcher group's "hooks" array, and the same handler in more than one
// settings file runs once. Findings name the file, event and index, never the command.

const HOOK_SCRIPT = /^[^\s]+\.(?:sh|bash|py|js|mjs|cjs|ts|ps1|rb|pl)$/i
const PROJECT_DIR_VAR = /^(?:\$\{CLAUDE_PROJECT_DIR\}|\$CLAUDE_PROJECT_DIR|\$env:CLAUDE_PROJECT_DIR)(?=\/|$)/
const HOME_VAR = /^(?:\$\{HOME\}|\$HOME|\$env:USERPROFILE|~)(?=\/|$)/
const HEADLESS_RUN = /(?<![\w-])claude(?:\.exe)?(?![\w-])[^\n|;&]*?\s(?:-p|--print)\b/

export interface HookSource {
  /** settings.json or settings.local.json */
  file: string
  raw: JsonObject | null
}

interface HookHandler {
  where: string
  event: string
  matcher: unknown
  handler: JsonObject
}

/** Split a shell command into words: quotes group and are dropped; | ; & < > ( ) separate. */
export function shellWords(command: string): string[] {
  const words: string[] = []
  let word = ''
  let quote = ''
  for (const ch of command.replace(/\\/g, '/')) {
    if (quote && ch === quote) quote = ''
    else if (quote || (!`"'`.includes(ch) && !/\s/.test(ch) && !'|;&<>()'.includes(ch))) word += ch
    else if (`"'`.includes(ch)) quote = ch
    else if (word) {
      words.push(word)
      word = ''
    }
  }
  return word ? [...words, word] : words
}

function hookWords(handler: JsonObject): string[] {
  const command = handler.command
  if (typeof command !== 'string') return []
  if (Array.isArray(handler.args)) return [command, ...handler.args.map(String)].map((p) => p.replace(/\\/g, '/'))
  return shellWords(command)
}

function isRelativeScript(word: string): boolean {
  if (PROJECT_DIR_VAR.test(word) || HOME_VAR.test(word)) return false
  if (word.includes('$') || word.includes('%')) return false
  return !word.startsWith('/') && !/^[A-Za-z]:\//.test(word)
}

function hookHandlers(sources: HookSource[]): { handlers: HookHandler[]; malformed: string[] } {
  const handlers: HookHandler[] = []
  const malformed: string[] = []
  const seen = new Set<string>()
  for (const { file, raw } of sources) {
    for (const [event, entries] of Object.entries(asObject(raw?.hooks))) {
      const groups: unknown[] = Array.isArray(entries) ? entries : [entries]
      groups.forEach((group, g) => {
        const where = `${file} ${event}[${g}]`
        const inner = asObject(group).hooks
        if (!Array.isArray(inner)) {
          malformed.push(where)
          return
        }
        const matcher = asObject(group).matcher
        inner.forEach((handler: unknown, h: number) => {
          const obj = asObject(handler)
          if (!obj.type) {
            malformed.push(`${where}.hooks[${h}]`)
            return
          }
          const key = JSON.stringify([event, matcher ?? null, obj])
          if (seen.has(key)) return
          seen.add(key)
          handlers.push({ where: `${where}.hooks[${h}]`, event, matcher, handler: obj })
        })
      })
    }
  }
  return { handlers, malformed }
}

/** Hook findings the site can see from the settings text alone. */
export function findHookProblems(sources: HookSource[]): string[] {
  const { handlers, malformed } = hookHandlers(sources)
  const relative: string[] = []
  const headless: string[] = []
  const sessionStart: string[] = []
  for (const { where, event, matcher, handler } of handlers) {
    if (event === 'SessionStart' && [undefined, null, '', '*', '.*'].includes(matcher as string)) sessionStart.push(where)
    if (handler.type !== 'command') continue
    const words = hookWords(handler)
    const script = words.find((w) => HOOK_SCRIPT.test(w) && !w.startsWith('-') && !w.includes('://'))
    if (script && isRelativeScript(script)) relative.push(`${where} (${script})`)
    const args = Array.isArray(handler.args) ? handler.args.map(String) : []
    if (HEADLESS_RUN.test([String(handler.command ?? ''), ...args].join(' '))) headless.push(where)
  }
  const findings: string[] = []
  if (malformed.length > 0) {
    findings.push(
      `${malformed.length} hook handler(s) never run: ${listed(malformed)}. Each handler must be an object with a "type" (such as "command") inside a matcher group's "hooks" array; a bare command string or a handler without a type does not run (hooks reference, read 2026-11-03).`,
    )
  }
  if (relative.length > 0) {
    findings.push(
      `${relative.length} hook handler(s) use a relative script path: ${listed(relative)}. A hook runs in the session's current directory, so it fails once Claude cds into a subfolder. Start the path with "$CLAUDE_PROJECT_DIR"/ in a shell-form command, or \${CLAUDE_PROJECT_DIR}/ in args.`,
    )
  }
  if (headless.length > 0) {
    findings.push(
      `${headless.length} hook handler(s) run claude -p (or --print): ${listed(headless)}. Each run is its own Claude Code session on your plan limits or API credits, started every time the hook fires; keep it on events that fire rarely, such as SessionEnd.`,
    )
  }
  for (const where of sessionStart) {
    findings.push(
      `Note: SessionStart hook ${where} has no matcher, so it also runs on resume, clear, compact and fork. That is intended if it re-injects context after compacting; Claude's first response waits for SessionStart hooks to finish (hooks reference, read 2026-11-03).`,
    )
  }
  return findings
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

type JsonObject = Record<string, unknown>

function asObject(value: unknown): JsonObject {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as JsonObject) : {}
}

// Auto-compact windows are token counts from 100,000 to 1,000,000, and only one under
// the 1M default bounds context growth. MCP tool results are capped at 25,000 tokens by
// default. On these providers the `haiku` alias is Haiku 4.5, not Haiku 5.5. (Settings,
// env-vars and model-config references, read 2026-11-03.)
const WINDOW_MIN = 100_000
const WINDOW_DEFAULT = 1_000_000
const MCP_OUTPUT_DEFAULT = 25_000
const TOKEN_COUNT = /^\s*([0-9]+)\s*([kKmM]?)\s*$/
const TOKEN_SCALE: Record<string, number> = { '': 1, k: 1_000, m: 1_000_000 }
const PROVIDER_FLAGS = [
  'CLAUDE_CODE_USE_BEDROCK',
  'CLAUDE_CODE_USE_VERTEX',
  'CLAUDE_CODE_USE_FOUNDRY',
  'CLAUDE_CODE_USE_ANTHROPIC_AWS',
  'CLAUDE_CODE_USE_MANTLE',
]
const MODEL_FAMILIES = ['haiku', 'sonnet', 'opus', 'fable', 'mythos']

/** A token count from a settings key, which takes a JSON number. */
function settingTokens(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? Math.trunc(value) : null
}

/** A token count from an env value: 200000 or "200000", plus "200k" or "1M" when `suffixes`. */
function envTokens(value: unknown, suffixes = true): number | null {
  if (typeof value !== 'string') return settingTokens(value)
  const match = TOKEN_COUNT.exec(value)
  if (!match || (match[2] && !suffixes)) return null
  return Number(match[1]) * TOKEN_SCALE[match[2].toLowerCase()]
}

function modelFamily(model: unknown): string | null {
  const text = typeof model === 'string' ? model.toLowerCase() : ''
  return MODEL_FAMILIES.find((family) => text.includes(family)) ?? null
}

/** An auto-compact window under the 1M default: top-level, per model, or the env variable. */
function windowSet(s: JsonObject): boolean {
  const values = [settingTokens(s.autoCompactWindow)]
  for (const conf of Object.values(asObject(s.modelSettings))) {
    values.push(settingTokens(asObject(conf).autoCompactWindow))
  }
  values.push(envTokens(asObject(s.env).CLAUDE_CODE_AUTO_COMPACT_WINDOW))
  return values.some((v) => v !== null && v >= WINDOW_MIN && v < WINDOW_DEFAULT)
}

/**
 * A lower MCP output cap, or a forced subagent model cheaper than the main one. The
 * subagent model alone is a default that a subagent's own model field overrides, so it
 * counts only with CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1.
 */
function envControls(s: JsonObject): boolean {
  const env = asObject(s.env)
  const mcpCap = envTokens(env.MAX_MCP_OUTPUT_TOKENS, false)
  if (mcpCap !== null && mcpCap > 0 && mcpCap < MCP_OUTPUT_DEFAULT) return true
  const forced = String(env.CLAUDE_CODE_SUBAGENT_MODEL_FORCE ?? '').trim() === '1'
  const family = modelFamily(env.CLAUDE_CODE_SUBAGENT_MODEL)
  return forced && (family === 'haiku' || family === 'sonnet') && family !== modelFamily(s.model)
}

const DEAD_SUBAGENT_KEY_FINDING =
  'env CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION does nothing: it was removed in v2.1.224 and is now a no-op (code.claude.com/docs/en/env-vars, read 2026-11-03). CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS limits how many subagents run at once.'

function haikuWindowFinding(): string {
  const base = MODELS['haiku-5-5']
  const tier = base.longPrompt
  if (!tier) return ''
  const usd = (n: number) => `$${n.toFixed(2)}`
  return `The pinned model is Haiku 5.5 with no auto-compact window. It auto-compacts at about 967K tokens by default (code.claude.com/docs/en/model-config, read 2026-11-03), but a request whose prompt is over ${tier.threshold.toLocaleString('en-US')} tokens pays ${usd(tier.inputPer1M)}/${usd(tier.outputPer1M)} per 1M on the whole request instead of ${usd(base.inputPer1M)}/${usd(base.outputPer1M)}, ${Math.round(tier.inputPer1M / base.inputPer1M)}x. Run /autocompact 100k in a Haiku 5.5 session, or set "modelSettings": {"claude-haiku-5-5": {"autoCompactWindow": 100000}}; the docs do not say how far below a 100K window compaction starts.`
}

/**
 * A dead env key and the Haiku 5.5 price line; neither changes the score. Mirrors
 * `_add_settings_findings` in tools/claude-rate/rate.py.
 */
export function settingsFindings(s: JsonObject): string[] {
  const env = asObject(s.env)
  const findings = Object.keys(env).includes('CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION') ? [DEAD_SUBAGENT_KEY_FINDING] : []
  const name = typeof s.model === 'string' ? s.model.trim().toLowerCase() : ''
  const onProvider = PROVIDER_FLAGS.some(
    (flag) => !['', '0', 'false', 'none'].includes(String(env[flag] ?? '').trim().toLowerCase()),
  )
  const onHaiku55 = name.includes('haiku-5-5') || (name === 'haiku' && !onProvider)
  const haikuSettings = Object.fromEntries(
    Object.entries(asObject(s.modelSettings)).filter(([model]) => model.toLowerCase().includes('haiku')),
  )
  if (onHaiku55 && !windowSet({ autoCompactWindow: s.autoCompactWindow, env, modelSettings: haikuSettings })) {
    findings.push(haikuWindowFinding())
  }
  return findings
}

/**
 * Whether settings.json configures a real spend-bounding setting.
 *
 * Mirrors `_cost_control_signals` in tools/claude-rate/rate.py and
 * `has_cost_controls` in tools/badge-generator/generate.py and
 * tools/actions/claude-cost-audit/audit.py. Change all four together or the
 * CLI, the badge, the Action and the web analyzer will disagree.
 * bashOutputMaxChars is not counted: the settings reference documents it as a
 * way to raise the Bash output limit.
 */
export function computeCostControls(s: Record<string, unknown>): boolean {
  // Reasoning tokens bill at the output rate. Claude Code defaults to "medium"
  // on Opus 5.5, Sonnet 5.5 and Haiku 5.5 and "high" on most other models, so
  // pinning low or medium is the biggest lever here after model choice.
  const effort = s.effortLevel
  if (typeof effort === 'string' && ['low', 'medium'].includes(effort.trim().toLowerCase())) {
    return true
  }
  // maxEffortLevel caps effort on every provider; "max" sets no cap.
  const cap = s.maxEffortLevel
  if (typeof cap === 'string' && ['low', 'medium', 'high', 'xhigh'].includes(cap.trim().toLowerCase())) {
    return true
  }
  // Fast Mode is a flat 2x on input and output. alwaysThinkingEnabled: false is
  // not counted: it has no effect on the always-thinking 5.5 and Fable models.
  if (s.fastMode === false || s.fastModePerSessionOptIn === true) return true
  // The closest real analogue of a spend cap: an enforced allowlist can keep
  // Opus- and Fable-tier models out of a project entirely.
  if (s.enforceAvailableModels === true && Array.isArray(s.availableModels) && s.availableModels.length > 0) {
    return true
  }
  // Bounds the context growth that drives per-turn input cost.
  if (s.autoCompactEnabled === true) return true
  // An auto-compact window under 1M, a lower MCP output cap, or a forced cheaper subagent model.
  return windowSet(s) || envControls(s)
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

/** CLAUDE.md size, counted on newline-normalized text as the Python graders read it. */
function analyzeClaudeMd(fileMap: Map<string, FetchedFile>) {
  const rootClaudeMd = fileMap.get('CLAUDE.md')
  const nestedClaudeMd = fileMap.get('.claude/CLAUDE.md')
  const files = [
    { path: 'CLAUDE.md', file: rootClaudeMd },
    { path: '.claude/CLAUDE.md', file: nestedClaudeMd },
  ]
    .filter(({ file }) => file?.found)
    .map(({ path, file }) => ({ path, chars: normalizeNewlines(file?.content ?? '').length }))

  const primary = rootClaudeMd?.found ? rootClaudeMd : nestedClaudeMd
  const primaryText = primary?.found ? normalizeNewlines(primary.content) : ''
  const primaryLines = countLines(primaryText)
  const totalChars = files.reduce((sum, f) => sum + f.chars, 0)
  // Exact repeats only, within the two fetched files; the CLI also reads rules files and
  // near-duplicates. No extra API calls.
  const { repeats, chars: repeatedChars } = findRepeatedLines(
    files.map(({ path }) => ({ path, content: fileMap.get(path)?.content ?? '' })),
  )

  return {
    totalChars,
    claudeMd: {
      found: !!primary?.found,
      charCount: primaryText.length,
      lineCount: primaryLines,
      overGuidance: primaryLines > CLAUDE_MD_LINE_GUIDANCE,
    },
    claudeMdAll: {
      totalChars,
      totalTokens: estimateTokens(totalChars),
      fileCount: files.length,
      files,
      repeatedLines: repeats,
      repeatedTokens: estimateTokens(repeatedChars),
    },
  }
}

/** Number of servers under `mcpServers` in a parsed config, or 0. */
function serverCount(config: Record<string, unknown> | null): number {
  const servers = config?.mcpServers
  return servers && typeof servers === 'object' ? Object.keys(servers as Record<string, unknown>).length : 0
}

/** 30-turn session and monthly cost per model at 3 sessions/day, 22 days/month. */
function estimateModelCosts(systemPromptTokens: number, turns: number) {
  const costEstimate = {} as Record<ModelId, { perSession: number; perMonth: number }>
  for (const modelId of Object.keys(MODELS) as ModelId[]) {
    const model = MODELS[modelId]
    // Billed per turn the way Claude Code caches (turnInputCost): the previous request is a
    // cache read, the new exchange a cache write. Per turn also lets a tiered model (Haiku 5.5)
    // price each request by its own prompt length.
    let perSession = 0
    let previousPrompt = 0
    for (let turn = 0; turn < turns; turn++) {
      const prompt =
        systemPromptTokens + turn * TOKEN_ESTIMATES.historyGrowthPerTurn + TOKEN_ESTIMATES.tokensPerFileRead
      const { readDollars, writeDollars } = turnInputCost(model, prompt, previousPrompt)
      previousPrompt = prompt
      perSession +=
        readDollars + writeDollars + (TOKEN_ESTIMATES.outputTokensPerTurn / 1_000_000) * ratesForPrompt(model, prompt).outputPer1M
    }
    costEstimate[modelId] = {
      perSession: Math.round(perSession * 100) / 100,
      perMonth: Math.round(perSession * 3 * 22 * 100) / 100,
    }
  }
  return costEstimate
}

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
  const tree = await fetchTree(owner, repo, branch)
  const treePaths = tree.paths
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
    // Read only for the detected Read deny rules; it does not change the score.
    GITIGNORE_FILE,
  ]
  const files = await Promise.all(
    contentTargets.map((path) =>
      treeSet.size === 0 || treeSet.has(path)
        ? fetchFile(owner, repo, path, branch)
        : Promise.resolve({ path, content: '', size: 0, found: false }),
    ),
  )

  const fileMap = new Map(files.map((f) => [f.path, f]))

  const { claudeMd, claudeMdAll, totalChars: totalInstructionChars } = analyzeClaudeMd(fileMap)

  // Settings
  const settingsFile = fileMap.get('.claude/settings.json')
  const localSettingsFile = fileMap.get('.claude/settings.local.json')
  const projectRaw = settingsFile?.found ? parseSettings(settingsFile.content) : null
  const localRaw = localSettingsFile?.found ? parseSettings(localSettingsFile.content) : null
  let settingsRaw: Record<string, unknown> | null = null
  if (settingsFile?.found) settingsRaw = projectRaw
  else if (localSettingsFile?.found) settingsRaw = localRaw

  const hasModel = settingsRaw
    ? !!(settingsRaw.model || settingsRaw.preferredModel)
    : false

  // Kept in step with `_cost_control_signals` in tools/claude-rate/rate.py and
  // `has_cost_controls` in tools/badge-generator/generate.py. This used to test
  // maxCost / costLimit / maxMonthlyCost; none of those is in the Claude Code
  // settings schema (checked 2026-09-06 against schemastore, 142 top-level
  // properties, no spend cap among them), so it scored a key the product
  // ignores. Value-aware on purpose: fastMode true doubles the bill and a
  // high effortLevel raises it, so the key being present is not enough.
  const hasCostControls = settingsRaw ? computeCostControls(settingsRaw) : false

  // File-read exclusions: Read(...) rules in permissions.deny. A committed
  // .claudeignore scores nothing (Claude Code does not read it); its patterns
  // are only converted so the page can show the rules to migrate to.
  const denyRules = readDenyRules(settingsRaw)
  const ignoreFile = fileMap.get(IGNORE_FILE)
  const suggestedRules = suggestReadDenyRules(
    treePaths,
    treePaths.length > 0 && !tree.truncated,
    fileMap.get(GITIGNORE_FILE)?.content ?? '',
    detection.lockFilesPresent,
  )
  const fileReadExclusions = {
    readDenyRules: denyRules,
    lockFilesPresent: detection.lockFilesPresent,
    lockFilesUncovered: detection.lockFilesPresent.filter(
      (lf) => !denyRules.some((r) => r.includes(lf) || r.includes('*.lock') || r.includes('*lock*')),
    ),
    ignoreFileFound: !!ignoreFile?.found,
    ignoreFileRules: ignoreFile?.found ? ignorePatternsAsReadRules(ignoreFile.content) : [],
    suggestedRules,
    missingRules: denyRules.length > 0 ? suggestedRules.filter((r) => !denyCovered(r, denyRules)) : [],
  }

  // MCP servers: .mcp.json is the canonical location; settings.json is legacy.
  const mcpFile = fileMap.get('.mcp.json')
  const mcpRaw = mcpFile?.found ? parseSettings(mcpFile.content) : null
  const mcpServerCount = serverCount(mcpRaw) + serverCount(settingsRaw)

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
    findings: settingsRaw ? settingsFindings(settingsRaw) : [],
    // Both files, because Claude Code merges their hooks; the score still counts settings.json only.
    hookFindings: findHookProblems([
      { file: 'settings.json', raw: projectRaw },
      { file: 'settings.local.json', raw: localRaw },
    ]),
  }

  // Security: obvious key shapes in the config files we fetched (.gitignore is not a config file).
  const keyLeakFiles = files
    .filter((f) => f.found && f.path !== GITIGNORE_FILE && API_KEY_PATTERN.test(f.content))
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

  const tokenEstimate = {
    systemPromptTokens,
    perTurnTokens,
    sessionTokens30Turns: inputTokensSession + outputTokensSession,
  }

  const costEstimate = estimateModelCosts(systemPromptTokens, turns)

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
  const repeated = r.claudeMdAll.repeatedLines
  if (repeated.length > 0) {
    recs.push(
      `${repeated.length} line(s) repeat an earlier line in your CLAUDE.md files (~${r.claudeMdAll.repeatedTokens.toLocaleString()} tokens in every session): ${listed(repeated)}. Keep one copy of each, in the file named after "repeats".`,
    )
  }
  const f = r.fileReadExclusions
  if (f.ignoreFileFound) {
    recs.push(
      `${IGNORE_FILE_FINDING} The File-read exclusions panel lists its patterns converted to Read rules.`,
    )
  } else if (f.readDenyRules.length === 0) {
    recs.push(
      `Add Read(...) rules to permissions.deny in .claude/settings.json to keep Claude's file tools out of dependency, build and generated paths. Detected for this repo: ${f.suggestedRules.join(', ')}. A folder is listed only when .gitignore names it and nothing under it is committed, because a Read deny also blocks Edit and Write on that path. No published measurement exists for what they save; the effect depends on how often Claude would otherwise open those files.`,
    )
  }
  // Uncovered lock files are part of the detected list, so they print once, here.
  if (f.readDenyRules.length > 0 && f.missingRules.length > 0) {
    recs.push(`Add these Read deny rules detected for this repo: ${f.missingRules.join(', ')}.`)
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
        'Add cost controls Claude Code actually reads. There is no spend-cap setting, so maxMonthlyCost and budgetCap are silently ignored: use "effortLevel": "medium" (reasoning tokens bill as output), "maxEffortLevel": "high" (caps effort on every provider), "fastMode": false (declines the flat 2x) or "fastModePerSessionOptIn": true, "autoCompactEnabled": true, "autoCompactWindow" under 1000000 (compacts sooner than the ~967K default), "enforceAvailableModels" with "availableModels" to keep Opus- and Fable-tier models out, or in "env": MAX_MCP_OUTPUT_TOKENS under 25000, or CLAUDE_CODE_SUBAGENT_MODEL with CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1. A real spend ceiling needs a PreToolUse hook, not a setting.',
      )
    }
    recs.push(...r.settings.findings)
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
  recs.push(...r.settings.hookFindings)
  return recs
}

function toolingRecommendations(r: RecommendationInput): string[] {
  const recs: string[] = []
  if (!r.tooling.costModeInstalled) {
    recs.push(
      'Install the cost-mode skill for concise responses and model-routing hints: npx skills add Sagargupta16/claude-cost-optimizer',
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
