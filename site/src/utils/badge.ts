export interface BadgeInputs {
  claudeMdLines: number
  claudeIgnoreEntries: number
  hasModelConfigured: boolean
  hasBudgetCap: boolean
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

function scoreClaudeMd(lines: number): CategoryScore {
  let score: number
  if (lines <= 80) score = 25
  else if (lines <= 100) score = 20
  else if (lines <= 150) score = 15
  else if (lines <= 200) score = 10
  else if (lines <= 300) score = 5
  else score = 0

  let recommendation = ''
  if (score < 25) {
    recommendation = `Trim CLAUDE.md from ${lines} to 80 lines or fewer. Remove verbose explanations, use references to external docs instead.`
  }

  return { name: 'CLAUDE.md', score, maxScore: 25, recommendation }
}

function scoreClaudeIgnore(entries: number): CategoryScore {
  let score: number
  if (entries >= 5) score = 25
  else if (entries >= 1) score = 15
  else score = 0

  let recommendation = ''
  if (score < 25) {
    recommendation = entries === 0
      ? 'Create a .claudeignore file. Add build outputs, node_modules, lock files, and generated code.'
      : `Add more entries to .claudeignore (currently ${entries}). Aim for 5+ patterns covering build artifacts, vendor dirs, and generated files.`
  }

  return { name: '.claudeignore', score, maxScore: 25, recommendation }
}

function scoreSettings(hasModel: boolean, hasBudget: boolean): CategoryScore {
  let score: number
  if (hasModel && hasBudget) score = 25
  else if (hasModel) score = 15
  else score = 0

  let recommendation = ''
  if (!hasModel) {
    recommendation = 'Configure a default model in .claude/settings.json to avoid accidentally using expensive models.'
  } else if (!hasBudget) {
    recommendation = 'Set a monthly budget cap to prevent runaway costs. Use --max-cost or configure in settings.'
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
    recommendation = `Reduce MCP servers from ${servers} to 3 or fewer. Each server adds ~1,500 tokens per turn. Disable servers you do not use every session.`
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
    scoreClaudeMd(inputs.claudeMdLines),
    scoreClaudeIgnore(inputs.claudeIgnoreEntries),
    scoreSettings(inputs.hasModelConfigured, inputs.hasBudgetCap),
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
