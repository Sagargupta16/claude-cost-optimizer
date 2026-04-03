# Badge Generator

A Python CLI tool that audits your project's Claude Code configuration for cost efficiency and generates a shields.io badge with a letter grade.

## What It Does

Scans your project directory for Claude Code configuration files and scores each on how well it controls context size, token usage, and cost:

| Category | File Checked | What It Measures | Max Points |
|----------|-------------|------------------|------------|
| CLAUDE.md | `CLAUDE.md` | Exists and is concise (fewer lines = less context per turn) | 25 |
| .claudeignore | `.claudeignore` | Exists with entries to exclude bulky files from indexing | 25 |
| Settings | `.claude/settings.json` | Has a model configured and a budget cap set | 25 |
| MCP Servers | `.claude/settings.json` | Fewer MCP servers = less overhead per turn | 25 |

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

| Lines | Points |
|-------|--------|
| 0-80 | 25 |
| 81-100 | 20 |
| 101-150 | 15 |
| 151-200 | 10 |
| 201-300 | 5 |
| 301+ or missing | 0 |

### .claudeignore Scoring

| Condition | Points |
|-----------|--------|
| 5+ entries | 25 |
| 1-4 entries | 15 |
| Missing | 0 |

### Settings Scoring

| Condition | Points |
|-----------|--------|
| Model + budget cap | 25 |
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

  CLAUDE.md        20/25  95 lines
  .claudeignore    25/25  7 entries
  Settings         15/25  model configured
  MCP Servers      25/25  2 MCP servers

Total: 85/100
Grade: A

Badge URL:
  https://img.shields.io/badge/Claude_Cost_Grade-A-green

Markdown:
  ![Claude Cost Grade](https://img.shields.io/badge/Claude_Cost_Grade-A-green)
```

### JSON Output

```json
{
  "project": "/home/user/my-project",
  "score": 85,
  "grade": "A",
  "badge_url": "https://img.shields.io/badge/Claude_Cost_Grade-A-green",
  "badge_markdown": "![Claude Cost Grade](https://img.shields.io/badge/Claude_Cost_Grade-A-green)",
  "breakdown": {
    "claude_md": {"score": 20, "detail": "95 lines", "lines": 95},
    "claudeignore": {"score": 25, "detail": "7 entries", "entries": 7},
    "settings": {"score": 15, "detail": "model configured", "has_model": true, "has_budget": false},
    "mcp_servers": {"score": 25, "detail": "2 MCP servers", "count": 2}
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
