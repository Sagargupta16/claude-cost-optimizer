export interface BadgeInputs {
  /** Lines in the root CLAUDE.md (or .claude/CLAUDE.md if the root has none). 0 = no CLAUDE.md. */
  claudeMdLines: number
  /** Estimated tokens (chars / 4) across CLAUDE.md and .claude/CLAUDE.md. */
  claudeMdTokens: number
  /** Read(...) entries in permissions.deny. */
  readDenyRules: number
  /** Every lock file at the repo root is covered by a Read rule (true when there are none). */
  lockFilesCovered: boolean
  /** A .claudeignore exists. Claude Code does not read it, so it scores nothing. */
  hasIgnoreFile: boolean
  hasModelConfigured: boolean
  hasCostControls: boolean
  mcpServers: number
}

export interface CategoryScore {
  name: string
  score: number
  maxScore: number
  recommendation: string
}

export interface BadgeResult {
  totalScore: number
  grade: string
  gradeColor: string
  categories: CategoryScore[]
  badgeUrl: string
  badgeMarkdown: string
}

/**
 * Rescales a shared-rubric score (CLAUDE.md out of 20, File-read exclusions out
 * of 15, as in tools/claude-rate/rate.py) to this badge's 25-point categories,
 * rounding half up. Same arithmetic as `_scale_to_25` in
 * tools/badge-generator/generate.py.
 */
function scaleTo25(points: number, rubricMax: number): number {
  return Math.floor((points * 50 + rubricMax) / (rubricMax * 2))
}

function scoreClaudeMd(lines: number, tokens: number): CategoryScore {
  let points = 0
  if (lines > 0) {
    if (lines <= 100) points += 12
    else if (lines <= 200) points += 10
    else if (lines <= 300) points += 6
    else if (lines <= 500) points += 3
    else points += 1

    if (tokens <= 2000) points += 8
    else if (tokens <= 4000) points += 6
    else if (tokens <= 8000) points += 4
    else if (tokens <= 16000) points += 2
  }
  const score = scaleTo25(points, 20)

  let recommendation = ''
  if (lines <= 0) {
    recommendation =
      "Create a CLAUDE.md at the repo root with your project conventions. Keep it under 200 lines (Anthropic's guidance)."
  } else if (lines > 200) {
    recommendation = `${lines} lines -- over Anthropic's 200-line guidance for CLAUDE.md. Longer files consume more context and reduce adherence. Move workflow-specific instructions into skills or path-scoped .claude/rules/ so they load on demand.`
  } else if (score < 25) {
    recommendation = `Full marks need 100 lines or fewer and 2,000 estimated tokens or fewer across CLAUDE.md and .claude/CLAUDE.md (currently ${lines} lines, ~${tokens.toLocaleString()} tokens).`
  }

  return { name: 'CLAUDE.md', score, maxScore: 25, recommendation }
}

const IGNORE_FILE_FINDING =
  "`.claudeignore` is not read by Claude Code -- it appears nowhere in Claude Code's documentation. Move its patterns into permissions.deny as Read(...) rules."

function scoreFileReadExclusions(
  rules: number,
  lockFilesCovered: boolean,
  hasIgnoreFile: boolean,
): CategoryScore {
  let points = 0
  if (rules >= 10) points = 13
  else if (rules >= 5) points = 10
  else if (rules >= 1) points = 6
  if (rules >= 1 && lockFilesCovered) points = Math.min(points + 2, 15)
  const score = scaleTo25(points, 15)

  const notes: string[] = []
  if (hasIgnoreFile) notes.push(IGNORE_FILE_FINDING)
  if (rules === 0) {
    notes.push(
      "Add Read(...) rules to permissions.deny in .claude/settings.json, e.g. Read(./node_modules/**), Read(./dist/**), Read(*.min.js), Read(./package-lock.json). No published measurement exists for what they save; the effect depends on how often Claude would otherwise open those files.",
    )
  } else if (!lockFilesCovered) {
    notes.push('Add a Read deny rule for each lock file at the repo root, e.g. Read(./package-lock.json).')
  } else if (score < 25) {
    notes.push(`Full marks need 10 or more Read deny rules (currently ${rules}).`)
  }

  return { name: 'File-read exclusions', score, maxScore: 25, recommendation: notes.join(' ') }
}

function scoreSettings(hasModel: boolean, hasCostControls: boolean): CategoryScore {
  let score: number
  if (hasModel && hasCostControls) score = 25
  else if (hasModel) score = 15
  else score = 0

  let recommendation = ''
  if (!hasModel) {
    recommendation = 'Configure a default model in .claude/settings.json to avoid accidentally using expensive models.'
  } else if (!hasCostControls) {
    recommendation =
      'Add a cost control Claude Code actually reads: "effortLevel": "medium", "fastMode": false, "autoCompactEnabled": true, or "enforceAvailableModels" with "availableModels". There is no spend-cap setting, so maxMonthlyCost and budgetCap are silently ignored.'
  }

  return { name: 'Settings', score, maxScore: 25, recommendation }
}

function scoreMcp(servers: number): CategoryScore {
  let score: number
  if (servers <= 3) score = 25
  else if (servers <= 5) score = 20
  else if (servers <= 8) score = 15
  else if (servers <= 12) score = 10
  else score = 0

  let recommendation = ''
  if (score < 25) {
    recommendation = `Reduce MCP servers from ${servers} to 3 or fewer. With tool search on (the default), each server adds its tool names and server instructions to context; full schemas load up front only when tool search is off. Prefer CLI tools (gh, aws, gcloud) where they exist, and disable unused servers with /mcp.`
  }

  return { name: 'MCP Servers', score, maxScore: 25, recommendation }
}

function getGrade(score: number): { grade: string; color: string } {
  if (score >= 95) return { grade: 'A+', color: '#3fb950' }
  if (score >= 85) return { grade: 'A', color: '#3fb950' }
  if (score >= 70) return { grade: 'B', color: '#d29922' }
  if (score >= 55) return { grade: 'C', color: '#d29922' }
  if (score >= 40) return { grade: 'D', color: '#f85149' }
  return { grade: 'F', color: '#f85149' }
}

export function scoreBadge(inputs: BadgeInputs): BadgeResult {
  const categories = [
    scoreClaudeMd(inputs.claudeMdLines, inputs.claudeMdTokens),
    scoreFileReadExclusions(inputs.readDenyRules, inputs.lockFilesCovered, inputs.hasIgnoreFile),
    scoreSettings(inputs.hasModelConfigured, inputs.hasCostControls),
    scoreMcp(inputs.mcpServers),
  ]

  const totalScore = categories.reduce((sum, c) => sum + c.score, 0)
  const { grade, color } = getGrade(totalScore)

  const encodedGrade = encodeURIComponent(grade)
  const encodedColor = color.replace('#', '')
  const badgeUrl = `https://img.shields.io/badge/claude_cost_optimizer-${encodedGrade}-${encodedColor}?style=for-the-badge`
  const badgeMarkdown = `[![Claude Cost Optimizer Grade](${badgeUrl})](https://sagargupta16.github.io/claude-cost-optimizer/badge)`

  return {
    totalScore,
    grade,
    gradeColor: color,
    categories,
    badgeUrl,
    badgeMarkdown,
  }
}
