# Guide 07: MCP Server and Agent Cost Impact

> MCP servers and subagents are powerful -- but each one adds tokens to your context. Understanding the overhead helps you keep costs under control.

---

## Table of Contents

- [MCP Server Token Overhead](#mcp-server-token-overhead)
- [Measuring Your MCP Cost](#measuring-your-mcp-cost)
- [Optimization Strategies](#optimization-strategies)
- [Subagent Cost Patterns](#subagent-cost-patterns)
- [Agent SDK Cost Considerations](#agent-sdk-cost-considerations)
- [Key Takeaways](#key-takeaways)

---

## MCP Server Token Overhead

Every connected MCP server injects its **tool schemas** into the system prompt. This happens on every turn, regardless of whether you use that server.

### Typical Tool Schema Sizes

| MCP Server | Tools | Approx. Tokens Added |
|------------|:-----:|:--------------------:|
| Playwright (browser) | 20+ | ~2,000-3,000 |
| GitHub | 15+ | ~1,500-2,500 |
| Memory | 5 | ~500-800 |
| Sequential Thinking | 1 | ~200-400 |
| Context7 | 2 | ~300-500 |
| Brave Search | 3 | ~400-600 |
| 21st (Magic) | 3 | ~400-600 |

### The Multiplication Effect

If you have 10 MCP servers connected with ~1,500 tokens average each:

```
15,000 tokens of MCP schemas x 50 turns = 750,000 input tokens

On Opus 4.7:  750K tokens x $5.00/1M = $3.75 just for MCP schemas (+~35% if new tokenizer inflates schema)
On Sonnet 4.6: 750K tokens x $3.00/1M = $2.25 just for MCP schemas
```

With prompt caching, the actual cost is much lower (~90% of those tokens get cached). But the first turn and any cache misses still pay full price.

### Tool Search (Deferred Tools)

Claude Code 2.1+ supports **deferred tool loading** -- tool schemas are only loaded when needed, not all at once. This can significantly reduce per-turn token overhead if most MCP tools go unused in a session.

If your MCP servers support it, deferred tools can save 5-15% on input tokens.

---

## Measuring Your MCP Cost

Run this to estimate your MCP overhead:

```bash
# Count connected MCP servers
claude mcp list 2>&1 | grep "Connected" | wc -l

# Rough estimate: multiply connected servers x 1,500 tokens x turns per session
# Example: 10 servers x 1,500 tokens x 30 turns = 450,000 extra input tokens
```

---

## Optimization Strategies

### 1. Only Connect What You Need

Don't connect 12 MCP servers if you only use 3 regularly. Add servers to **project-level** config (not global) so they only load for relevant projects.

```json
// .claude/settings.json (project-level) -- only loads for this project
{
  "mcpServers": {
    "context7": { "command": "npx", "args": ["-y", "@upstash/context7-mcp"] }
  }
}
```

### 2. Use Project-Level vs Global MCPs

| Scope | When to Use |
|-------|-------------|
| **Global** (`~/.claude.json`) | Daily drivers: memory, sequential-thinking |
| **Project** (`.claude/settings.json`) | Stack-specific: playwright (web projects), context7 (library work) |

### 3. Disable Unused Built-in MCPs

Built-in MCPs like `plugin:github:github` or `plugin:playwright:playwright` load even if you don't use them. Check `claude mcp list` and disable any that show as connected but you never invoke.

---

## Subagent Cost Patterns

Subagents (`Agent` tool) run in separate contexts. Each subagent is a full Claude session with its own input/output billing.

### Cost Formula

```
Subagent cost = (system prompt + task prompt + tool results) x model price
Main context savings = avoided context pollution from search results
```

### When Subagents Save Money

| Pattern | Without Subagent | With Subagent | Savings |
|---------|:----------------:|:-------------:|:-------:|
| Large codebase search | Search results bloat main context for all remaining turns | Search results isolated, only summary returns | 20-40% |
| Parallel research (3 agents) | Sequential searches, each adding to context | 3 small isolated contexts | 15-30% |
| Background tasks | Block main context while waiting | Run in background, results on completion | Time saved |

### When Subagents Cost More

- **Simple, one-off queries**: The overhead of spinning up a new context (system prompt, CLAUDE.md) costs more than just doing the search in the main context
- **Tasks requiring main context knowledge**: Subagents don't inherit conversation history, so you have to re-explain context
- **Haiku subagents for complex tasks**: If the subagent fails and you retry on a better model, you've paid twice

### Model Selection for Subagents

```json
// Use haiku for simple searches, sonnet for analysis
{
  "model": "haiku"  // In agent frontmatter or via model parameter
}
```

---

## Agent SDK Cost Considerations

If you're building custom agents with the Claude Agent SDK:

### Multi-Agent Systems Multiply Costs

Each agent in a multi-agent system has its own context window and billing:

```
Orchestrator agent: $X per session
+ Worker agent 1:   $Y per task
+ Worker agent 2:   $Y per task
+ Worker agent N:   $Y per task
= Total: $X + (N x $Y)
```

### Cost Controls

Use `--max-budget-usd` in CLI mode to cap spending:

```bash
claude -p "analyze this codebase" --max-budget-usd 5.00
```

Use `--fallback-model` to auto-switch when the primary model is overloaded:

```bash
claude --model opus --fallback-model sonnet "complex refactoring task"
```

---

## Key Takeaways

1. **Each MCP server adds ~500-3,000 tokens per turn** to your context -- connect only what you need
2. **Use project-level MCP configs** instead of global to avoid loading unnecessary servers
3. **Subagents save money on large searches** but cost more for simple one-off queries
4. **Use `--max-budget-usd`** to prevent runaway costs in automated/SDK workflows
5. **Deferred tool loading** (when available) reduces MCP schema overhead significantly
6. **Haiku subagents** are ideal for search/exploration tasks at 5x lower cost
