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

On Opus 5:    750K tokens x $5.00/1M = $3.75 just for MCP schemas (+~35% if new tokenizer inflates schema)
On Sonnet 5:  750K tokens x $3.00/1M = $2.25 just for MCP schemas
```

Add the tool-use system prompt on top of the schemas themselves: **286 tokens** with `tool_choice: auto` or `none`, **406 tokens** with `any` or `tool`. Individual built-in tools cost more (the bash tool adds 325 input tokens on Opus 5 / 4.8 / 4.7, 244 on Opus 4.6 and earlier; the text editor tool adds 700).

With prompt caching, the actual cost is much lower (~90% of those tokens get cached). But the first turn and any cache misses still pay full price. Note that Opus 5's minimum cacheable prompt is only **512 tokens** (Opus 4.8 needed 1,024, Opus 4.7 needed 2,048, Opus 4.6 needed 4,096), so even a single small MCP server's schemas are now big enough to cache.

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

### 4. Add or Remove Tools Mid-Conversation Without Busting the Cache

Historically, changing your `tools` array between turns invalidated the entire prompt cache -- tool definitions sit at the very front of the prompt, so connecting one more MCP server mid-session meant paying a full cache write on everything after it. That made dynamic tool sets expensive.

Opus 5 ships a beta that removes the penalty:

```
anthropic-beta: mid-conversation-tool-changes-2026-07-01
```

With that header, tool definitions can change between turns while the rest of the cached prefix stays valid. This makes it affordable to load a narrow tool set by default and attach extra MCP servers only for the turns that need them, instead of carrying every schema for the whole session.

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

On Opus 5 subagents, remember that adaptive thinking is on by default when you omit the `thinking` parameter, and reasoning tokens bill as **output** at $25/MTok. A fan-out of ten search subagents on Opus 5 pays for ten sets of reasoning tokens. Drop the effort level, or set `thinking: {type: "disabled"}` (allowed only at effort `high` or below), for subagents that just grep and summarize. Also note that `max_tokens` caps thinking plus visible text together, so a subagent with a tight `max_tokens` and high effort can burn its budget reasoning and return nothing usable.

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

If you call the API directly, Opus 5's server-side `fallbacks` parameter (header `anthropic-beta: server-side-fallback-2026-07-01`) covers a different case: Opus 5 ships cybersecurity safety classifiers, and a cyber refusal can auto-fall-back to Opus 4.8 server-side instead of failing the request and forcing you to pay for a client-side retry.

If you are billed for Managed Agents rather than raw tokens, budget the session runtime line too: **$0.08 per session-hour** while a session is `running`. That is on top of standard token rates, and it replaces Code Execution container-hour billing rather than stacking with it.

---

## Key Takeaways

1. **Each MCP server adds ~500-3,000 tokens per turn** to your context -- connect only what you need
2. **Use project-level MCP configs** instead of global to avoid loading unnecessary servers
3. **Subagents save money on large searches** but cost more for simple one-off queries
4. **Use `--max-budget-usd`** to prevent runaway costs in automated/SDK workflows
5. **Deferred tool loading** (when available) reduces MCP schema overhead significantly
6. **Haiku subagents** are ideal for search/exploration tasks at 5x lower cost
7. **Changing tools mid-conversation no longer busts the cache** on Opus 5 with the `mid-conversation-tool-changes-2026-07-01` beta -- attach MCP servers per-turn instead of carrying every schema all session
8. **Opus 5 thinks by default** and reasoning tokens bill as output at $25/MTok -- lower the effort level or disable thinking on subagents that only search and summarize
