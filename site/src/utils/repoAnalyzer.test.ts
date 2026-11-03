import { describe, expect, it } from 'vitest'
import { scoreBadge } from './badge'
import {
  computeCostControls,
  denyCovered,
  findHookProblems,
  findRepeatedLines,
  normalizedLine,
  settingsFindings,
  shellWords,
  suggestReadDenyRules,
} from './repoAnalyzer'

// Same cases, in the same order, as COST_CONTROL_CASES in tools/claude-rate/tests/test_b1.py,
// which checks rate.py, the badge generator and the audit Action against them. Keep them equal.
const COST_CONTROL_CASES: [Record<string, unknown>, boolean][] = [
  [{}, false],
  [{ autoCompactWindow: 200000 }, true],
  [{ autoCompactWindow: 1000000 }, false],
  [{ autoCompactWindow: 99999 }, false],
  [{ autoCompactWindow: '200000' }, false],
  [{ modelSettings: { 'claude-haiku-5-5': { autoCompactWindow: 100000 } } }, true],
  [{ modelSettings: { 'claude-opus-5-5': { autoCompactWindow: 'auto' } } }, false],
  [{ env: { CLAUDE_CODE_AUTO_COMPACT_WINDOW: '200k' } }, true],
  [{ env: { CLAUDE_CODE_AUTO_COMPACT_WINDOW: '1M' } }, false],
  [{ env: { CLAUDE_CODE_AUTO_COMPACT_WINDOW: '200' } }, false],
  [{ env: { MAX_MCP_OUTPUT_TOKENS: '10000' } }, true],
  [{ env: { MAX_MCP_OUTPUT_TOKENS: '25000' } }, false],
  [{ env: { MAX_MCP_OUTPUT_TOKENS: '10k' } }, false],
  [{ env: { CLAUDE_CODE_SUBAGENT_MODEL: 'haiku' } }, false],
  [{ env: { CLAUDE_CODE_SUBAGENT_MODEL: 'haiku', CLAUDE_CODE_SUBAGENT_MODEL_FORCE: '1' } }, true],
  [
    { model: 'claude-sonnet-5-5', env: { CLAUDE_CODE_SUBAGENT_MODEL: 'sonnet', CLAUDE_CODE_SUBAGENT_MODEL_FORCE: '1' } },
    false,
  ],
  [
    {
      model: 'claude-opus-5-5',
      env: { CLAUDE_CODE_SUBAGENT_MODEL: 'claude-sonnet-5-5', CLAUDE_CODE_SUBAGENT_MODEL_FORCE: '1' },
    },
    true,
  ],
  [{ env: { CLAUDE_CODE_SUBAGENT_MODEL: 'opus', CLAUDE_CODE_SUBAGENT_MODEL_FORCE: '1' } }, false],
  [{ bashOutputMaxChars: 10000 }, false],
  [{ env: { BASH_MAX_OUTPUT_LENGTH: '10000' } }, false],
  [{ effortLevel: 'medium' }, true],
  [{ fastMode: true }, false],
]

describe('computeCostControls', () => {
  it.each(COST_CONTROL_CASES)('scores %j as %s, like the Python graders', (settings, expected) => {
    expect(computeCostControls(settings)).toBe(expected)
  })
})

describe('badge checker text', () => {
  it('lists the same cost controls and the Read deny caveat', () => {
    const result = scoreBadge({
      claudeMdLines: 50,
      claudeMdTokens: 500,
      readDenyRules: 0,
      lockFilesCovered: true,
      hasIgnoreFile: false,
      hasModelConfigured: true,
      hasCostControls: false,
      mcpServers: 0,
    })
    const text = result.categories.map((c) => c.recommendation).join(' ')
    for (const key of ['autoCompactWindow', 'MAX_MCP_OUTPUT_TOKENS', 'CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1']) {
      expect(text).toContain(key)
    }
    expect(text).toContain('also blocks Edit and Write')
  })
})

describe('settingsFindings', () => {
  it('notes the price line for the haiku alias on the Anthropic API', () => {
    const findings = settingsFindings({ model: 'haiku' })
    expect(findings).toHaveLength(1)
    expect(findings[0]).toContain('$0.50/$2.50')
    expect(findings[0]).toContain('5x')
  })

  it('says nothing for the haiku alias on Bedrock, where it is Haiku 4.5', () => {
    expect(settingsFindings({ model: 'haiku', env: { CLAUDE_CODE_USE_BEDROCK: '1' } })).toEqual([])
  })

  it('says nothing once Haiku 5.5 has a window under 1M', () => {
    const settings = { model: 'claude-haiku-5-5', modelSettings: { 'claude-haiku-5-5': { autoCompactWindow: 100000 } } }
    expect(settingsFindings(settings)).toEqual([])
  })

  it('reports CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION as a no-op', () => {
    const findings = settingsFindings({ env: { CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION: '50' } })
    expect(findings).toHaveLength(1)
    expect(findings[0]).toContain('no-op')
  })
})

describe('shellWords', () => {
  it('keeps a quoted variable and the path after it as one word', () => {
    expect(shellWords('bash "$CLAUDE_PROJECT_DIR"/hooks/x.sh | jq .')).toEqual([
      'bash',
      '$CLAUDE_PROJECT_DIR/hooks/x.sh',
      'jq',
      '.',
    ])
  })

  it('keeps a quoted path with spaces together and turns backslashes into slashes', () => {
    expect(shellWords('node "C:\\Program Files\\hooks\\a.js"')).toEqual(['node', 'C:/Program Files/hooks/a.js'])
  })
})

describe('findHookProblems', () => {
  const secret = 'sk-test-not-a-real-key-1234567890'
  const hooks = {
    PreToolUse: [
      'bash hooks/bare.sh',
      { matcher: 'Bash', hooks: [{ command: 'echo hi' }] },
      { matcher: '.*', hooks: [{ type: 'command', command: 'bash hooks/guard.sh' }] },
      { matcher: '.*', hooks: [{ type: 'command', command: `TOKEN=${secret} bash "$CLAUDE_PROJECT_DIR"/hooks/ok.sh` }] },
    ],
    Stop: [{ hooks: [{ type: 'command', command: 'claude -p "summarize the session"' }] }],
    SessionStart: [{ hooks: [{ type: 'command', command: 'echo started' }] }],
  }
  const findings = findHookProblems([
    { file: 'settings.json', raw: { hooks } },
    { file: 'settings.local.json', raw: { hooks: { Stop: hooks.Stop } } },
  ])

  it('finds handlers that never run, a relative script, claude -p once, and an unscoped SessionStart', () => {
    expect(findings).toHaveLength(4)
    expect(findings[0]).toMatch(/^2 hook handler\(s\) never run: settings.json PreToolUse\[0\]; settings.json PreToolUse\[1\].hooks\[0\]\./)
    expect(findings[1]).toMatch(/^1 hook handler\(s\) use a relative script path: settings.json PreToolUse\[2\].hooks\[0\] \(hooks\/guard.sh\)\./)
    expect(findings[2]).toMatch(/^1 hook handler\(s\) run claude -p/)
    expect(findings[3]).toMatch(/^Note: SessionStart hook settings.json SessionStart\[0\].hooks\[0\] has no matcher/)
  })

  it('never prints a command', () => {
    expect(findings.join('\n')).not.toContain(secret)
    expect(findings.join('\n')).not.toContain('summarize the session')
  })

  it('passes this repo-style config: project-dir paths, SessionEnd summary', () => {
    const own = {
      hooks: {
        PreToolUse: [{ matcher: '.*', hooks: [{ type: 'command', command: 'bash "$CLAUDE_PROJECT_DIR"/hooks/budget-tracker.sh' }] }],
        SessionEnd: [{ matcher: '', hooks: [{ type: 'command', command: 'bash "$CLAUDE_PROJECT_DIR"/hooks/session-summary.sh' }] }],
      },
    }
    expect(findHookProblems([{ file: 'settings.json', raw: own }, { file: 'settings.local.json', raw: null }])).toEqual([])
  })
})

describe('findRepeatedLines', () => {
  // The same pair of files as DeadLoad in test_b1.py, minus the near-duplicate the CLI also reports.
  const claudeMd = [
    '# Project',
    '- See `docs/guide.md` and `docs/missing.md`.',
    'Always run the full test suite before you open a pull request.',
    '```',
    'Always run the full test suite before you open a pull request.',
    '```',
    '| Always run the full test suite before you open a pull request |',
    'short line',
    '',
  ].join('\r\n')
  const nested = [
    '---',
    'description: Always run the full test suite before you open a pull request',
    '---',
    '- **Always run the full test suite** before you open a pull request',
    '1. always   RUN the full test suite before you open a pull request!',
  ].join('\n')

  it('reports exact repeats after normalizing, skipping fences, tables, frontmatter and short lines', () => {
    const { repeats, chars } = findRepeatedLines([
      { path: 'CLAUDE.md', content: claudeMd },
      { path: '.claude/CLAUDE.md', content: nested },
    ])
    expect(repeats).toEqual(['.claude/CLAUDE.md:4 repeats CLAUDE.md:3', '.claude/CLAUDE.md:5 repeats CLAUDE.md:3'])
    expect(chars).toBe(
      '- **Always run the full test suite** before you open a pull request'.length +
        '1. always   RUN the full test suite before you open a pull request!'.length,
    )
  })

  it('normalizes list markers, emphasis, case, spacing and trailing punctuation', () => {
    expect(normalizedLine('  * **Keep** `CLAUDE.md`   under 200 lines.  ')).toBe('keep claude.md under 200 lines')
    expect(normalizedLine('## A heading that is long enough to count')).toBeNull()
  })
})

describe('suggestReadDenyRules', () => {
  const gitignore = 'dist/\n/node_modules\ncoverage\n'
  const tree = ['dist/app.js', 'web/app.min.js', 'src/index.ts', 'package-lock.json']

  it('never denies a folder with committed files, and adds globs only for committed matches', () => {
    expect(suggestReadDenyRules(tree, true, gitignore, ['package-lock.json'])).toEqual([
      'Read(./.env)',
      'Read(./.env.*)',
      'Read(node_modules/**)',
      'Read(coverage/**)',
      'Read(*.min.js)',
      'Read(./package-lock.json)',
    ])
  })

  it('names no folder when the tree is unknown or truncated', () => {
    expect(suggestReadDenyRules([], false, gitignore, [])).toEqual(['Read(./.env)', 'Read(./.env.*)'])
  })

  it('counts a rule as present by segment, and lock files by the scoring rule', () => {
    const rules = ['Read(.env)', 'Read(./node_modules/**)', 'Read(*.lock)', 'Read(*.js)']
    expect(denyCovered('Read(node_modules/**)', rules)).toBe(true)
    expect(denyCovered('Read(./.env)', rules)).toBe(true)
    expect(denyCovered('Read(./.env.*)', rules)).toBe(false)
    expect(denyCovered('Read(*.min.js)', rules)).toBe(true)
    expect(denyCovered('Read(./yarn.lock)', rules)).toBe(true)
    expect(denyCovered('Read(coverage/**)', rules)).toBe(false)
  })
})
