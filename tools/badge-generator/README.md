# Badge Generator

A Python CLI tool that audits your project's Claude Code configuration for cost efficiency and generates a shields.io badge with a letter grade.

## What It Does

Scans your project directory for Claude Code configuration files and scores each on how well it controls context size, token usage, and cost:

| Category | File Checked | What It Measures | Max Points |
|----------|-------------|------------------|------------|
| CLAUDE.md | `CLAUDE.md`, `.claude/CLAUDE.md` | Primary file line count plus estimated tokens across both (Anthropic's guidance: under 200 lines) | 25 |
| File-read exclusions | `.claude/settings.json` (else `.claude/settings.local.json`) | `Read(...)` rules in `permissions.deny`, plus lock-file coverage | 25 |
| Settings | `.claude/settings.json` | Has a model configured and a real cost control set | 25 |
| MCP Servers | `.claude/settings.json` | Fewer MCP servers = less overhead per turn | 25 |

CLAUDE.md and File-read exclusions use the same rubric as [claude-rate](../claude-rate/), where they are worth 20 and 15 points. This tool rescales each to 25 (rubric points x 25 / rubric max, rounded half up), and the JSON output keeps the unscaled `rubric_score` so the two tools can be compared directly.

Total score maps to a letter grade:

| Grade | Score Range |
|-------|------------|
| A+ | 95-100 |
| A | 85-94 |
| B | 70-84 |
| C | 55-69 |
| D | 40-54 |
| F | 0-39 |

### CLAUDE.md Scoring

The primary file is the root `CLAUDE.md`, or `.claude/CLAUDE.md` when the root has none. Rubric points are the sum of two parts:

| Primary file lines | Rubric points |
|-------|--------|
| 0-100 | 12 |
| 101-200 | 10 |
| 201-300 | 6 |
| 301-500 | 3 |
| 501+ | 1 |

| Estimated tokens, both files (chars / 4) | Rubric points |
|-------|--------|
| 0-2,000 | 8 |
| 2,001-4,000 | 6 |
| 4,001-8,000 | 4 |
| 8,001-16,000 | 2 |
| 16,001+ | 0 |

No CLAUDE.md in either place scores 0. The 20 rubric points rescale to 25 (for example 20 -> 25, 18 -> 23, 12 -> 15). Over 200 lines adds a finding: CLAUDE.md loads in full at launch, and Anthropic's guidance is to target under 200 lines per file.

### File-read exclusions Scoring

Counts `Read(...)` entries in `permissions.deny`:

| Read deny rules | Rubric points |
|-----------|--------|
| 10+ | 13 |
| 5-9 | 10 |
| 1-4 | 6 |
| 0 | 0 |

+2 when there is at least one rule and every lock file at the root (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock`, `uv.lock`) is covered by a rule containing its name, `*.lock` or `*lock*` (true when there are none); capped at 15. The 15 rubric points rescale to 25 (15 -> 25, 13 -> 22, 12 -> 20, 10 -> 17, 8 -> 13, 6 -> 10).

A `.claudeignore` scores nothing: Claude Code does not read it. When one exists the tool adds a finding telling you to move its patterns into `permissions.deny` as `Read(...)` rules.

### Settings Scoring

| Condition | Points |
|-----------|--------|
| Model + a real cost control (`effortLevel` low/medium, `fastMode: false`, `alwaysThinkingEnabled: false`, `enforceAvailableModels` with `availableModels`, or `autoCompactEnabled: true`) | 25 |
| Model only | 15 |
| Exists, no model | 5 |
| Missing | 0 |

### MCP Servers Scoring

| Server Count | Points |
|-------------|--------|
| 0-3 | 25 |
| 4-5 | 20 |
| 6-8 | 15 |
| 9-12 | 10 |
| 13+ | 0 |

## Usage

```bash
# Audit a project directory
python tools/badge-generator/generate.py /path/to/project

# Audit the current directory
python tools/badge-generator/generate.py .

# JSON output (for CI or scripting)
python tools/badge-generator/generate.py . --json
```

### Terminal Output

```
Claude Cost Efficiency Audit
========================================
Project: /home/user/my-project

  CLAUDE.md              15/25  250 lines, ~3,223 tokens across 1 file(s)
    ! 250 lines -- over Anthropic's 200-line guidance for CLAUDE.md. Longer files consume more context and reduce adherence. Move workflow-specific instructions into skills or path-scoped .claude/rules/ so they load on demand.
  File-read exclusions   20/25  6 Read deny rule(s); lock files covered
    ! `.claudeignore` is not read by Claude Code -- it appears nowhere in Claude Code's documentation. Move its patterns into permissions.deny as Read(...) rules.
  Settings                5/25  no model pin or cost controls
  MCP Servers            25/25  0 MCP servers

Total: 65/100
Grade: C

Badge URL:
  https://img.shields.io/badge/Claude_Cost_Grade-C-yellow

Markdown:
  ![Claude Cost Grade](https://img.shields.io/badge/Claude_Cost_Grade-C-yellow)
```

### JSON Output

```json
{
  "project": "/home/user/my-project",
  "score": 65,
  "grade": "C",
  "badge_url": "https://img.shields.io/badge/Claude_Cost_Grade-C-yellow",
  "badge_markdown": "![Claude Cost Grade](https://img.shields.io/badge/Claude_Cost_Grade-C-yellow)",
  "breakdown": {
    "claude_md": {
      "score": 15,
      "detail": "250 lines, ~3,223 tokens across 1 file(s)",
      "lines": 250,
      "tokens": 3223,
      "rubric_score": 12,
      "rubric_max": 20,
      "findings": [
        "250 lines -- over Anthropic's 200-line guidance for CLAUDE.md. Longer files consume more context and reduce adherence. Move workflow-specific instructions into skills or path-scoped .claude/rules/ so they load on demand."
      ]
    },
    "file_read_exclusions": {
      "score": 20,
      "detail": "6 Read deny rule(s); lock files covered",
      "rules": 6,
      "lock_files_uncovered": [],
      "rubric_score": 12,
      "rubric_max": 15,
      "findings": [
        "`.claudeignore` is not read by Claude Code -- it appears nowhere in Claude Code's documentation. Move its patterns into permissions.deny as Read(...) rules."
      ]
    },
    "settings": {"score": 5, "detail": "no model pin or cost controls", "has_model": false, "has_cost_controls": false},
    "mcp_servers": {"score": 25, "detail": "0 MCP servers", "count": 0}
  }
}
```

## Adding the Badge to Your README

Copy the markdown snippet from the output and paste it at the top of your README:

```markdown
![Claude Cost Grade](https://img.shields.io/badge/Claude_Cost_Grade-A-green)
```

This renders as a static badge. Re-run the tool after configuration changes to get an updated URL.

For automated badge updates on every push, see the [GitHub Action](../../.github/workflows/cost-audit.yml) or the [reusable composite action](../actions/claude-cost-audit/).

## Requirements

- Python 3.10+
- Standard library only (no external dependencies)
