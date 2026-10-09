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

In Claude Code, **MCP tool search is on by default** (code.claude.com/docs/en/mcp and /costs, read 2026-09-28). Tool definitions are deferred: only **tool names and server instructions** enter context until Claude uses a specific tool, and then that tool's schema loads. Anthropic publishes no per-server token figure for deferred servers.

Full **tool schemas** load into the prompt up front, on every turn, only when tool search is off:

- `ENABLE_TOOL_SEARCH=false`, or `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`
- an `ANTHROPIC_BASE_URL` pointing at a non-first-party host (set `ENABLE_TOOL_SEARCH=true` if your proxy forwards `tool_reference` blocks)
- models older than the Claude 4.5 generation on Google Cloud, and Microsoft Foundry deployments hosted on Azure

The sizes and the worked example below are that **tool-search-off** case.

### Typical Tool Schema Sizes (tool search off)

| MCP Server | Tools | Approx. Tokens Added |
|------------|:-----:|:--------------------:|
| Playwright (browser) | 20+ | ~2,000-3,000 |
| GitHub | 15+ | ~1,500-2,500 |
| Memory | 5 | ~500-800 |
| Sequential Thinking | 1 | ~200-400 |
| Context7 | 2 | ~300-500 |
| Brave Search | 3 | ~400-600 |
| 21st (Magic) | 3 | ~400-600 |

### The Multiplication Effect (tool search off)

With tool search off, if you have 10 MCP servers connected with ~1,500 tokens of full schemas each (an estimate from the table above, not an Anthropic figure):

```
15,000 tokens of MCP schemas x 50 turns = 750,000 input tokens

On Opus 5.5:  750K tokens x $4.00/1M = $3.00 just for MCP schemas (+~35% if new tokenizer inflates schema)
On Opus 5:    750K tokens x $5.00/1M = $3.75 (legacy)
On Sonnet 5.5: 750K tokens x $2.00/1M = $1.50 just for MCP schemas
On Haiku 5.5:  750K tokens x $0.10/1M = $0.075 while each request stays <= 100K prompt tokens
               (750K x $0.50/1M = $0.375 once the requests are over 100K)
```

With tool search on (the default), that per-turn schema load does not happen: only tool names and server instructions ride along until a tool is used. This is why the old advice that "adding a server breaks the cache" is out of date -- with tool search on, connecting or removing a server does **not** invalidate the prompt cache. It still does when tool search is off, and so does enabling or disabling a plugin that provides MCP servers.

Add the tool-use system prompt on top of the schemas themselves: **286 tokens** with `tool_choice: auto` or `none`, **406 tokens** with `any` or `tool` (Opus 5.5 and Sonnet 5.5 reject forced `any`/`tool`, so only 286 applies there; Haiku 5.5 supports forced tool use, so both apply). Individual built-in tools cost more (the bash tool adds 325 input tokens on Opus 5 / 4.8 / 4.7, 244 on Opus 4.6 and earlier; the text editor tool adds 700).

With prompt caching, the actual cost is much lower: cached schema tokens bill at 0.1x base input on most models (0.05x on Opus 5.5 and Sonnet 5.5, 0.025x on Fable 5.1). But the first turn and any cache misses still pay full price. Note that the minimum cacheable prompt on Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5 is only **512 tokens** (Opus 4.8 and Sonnet 5 needed 1,024, Opus 4.7 needed 2,048, Opus 4.6 and Haiku 4.5 needed 4,096), so even a single small MCP server's schemas are now big enough to cache.

### Tool Search (Deferred Tools)

Tool search is **on by default** in Claude Code: schemas load only when Claude uses a tool, not all at once. Anthropic publishes no percentage saving for it; what it removes is the full-schema load described above for every tool you do not call. Leave it on unless you have a reason to turn it off, and remember that pointing Claude Code at a custom `ANTHROPIC_BASE_URL` also turns it off.

### MCP Tool Output

What a tool **returns** costs tokens too, deferred or not. Claude Code warns when an MCP tool's output exceeds **10,000 tokens** and caps it at **25,000 tokens** by default; raise or lower the cap with `MAX_MCP_OUTPUT_TOKENS`. A lower cap is a cost backstop for servers that dump whole pages or tables.

---

## Measuring Your MCP Cost

Measure rather than estimate. Inside a session, `/context` shows what is consuming context space, and on a Pro, Max, Team or Enterprise plan `/usage` attributes recent usage to individual MCP servers as a share of the total.

If tool search is off, a rough estimate is still possible:

```bash
# Count connected MCP servers
claude mcp list 2>&1 | grep "Connected" | wc -l

# Tool search OFF only: multiply connected servers x their full-schema size x turns per session
# Example: 10 servers x ~1,500 tokens x 30 turns = 450,000 extra input tokens
# Tool search ON (default): only tool names and server instructions load; use /context instead
```

---

## Optimization Strategies

### 1. Only Connect What You Need

Don't connect 12 MCP servers if you only use 3 regularly. Tool search keeps idle servers cheap, but each still adds its tool names and server instructions, and each one Claude does call loads its schema and returns output. Run `/mcp` to see configured servers and disable the ones you are not using. Add servers to **project-level** config (not global) so they only load for relevant projects. Project-scoped servers live in `.mcp.json` at the project root (`claude mcp add --scope project` writes it), not in `settings.json`:

```json
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
| **Project** (`.mcp.json`) | Stack-specific: playwright (web projects), context7 (library work) |

### 3. Disable Unused Built-in MCPs

Built-in MCPs like `plugin:github:github` or `plugin:playwright:playwright` load even if you don't use them. Check `claude mcp list` (or `/mcp` inside a session) and disable any that show as connected but you never invoke.

### 3b. Prefer a CLI When One Exists

Anthropic's costs page still recommends CLI tools such as `gh`, `aws`, `gcloud` and `sentry-cli` over the equivalent MCP server when available, because they add no per-tool listing at all: Claude runs the command directly. A GitHub MCP server is worth it only for what `gh` cannot do.

### 4. Add or Remove Tools Mid-Conversation Without Busting the Cache

Historically, changing your `tools` array between turns invalidated the entire prompt cache -- tool definitions sit at the very front of the prompt, so connecting one more MCP server mid-session meant paying a full cache write on everything after it. That made dynamic tool sets expensive.

Opus 5 ships a beta that removes the penalty:

```
anthropic-beta: mid-conversation-tool-changes-2026-07-01
```

With that header, tool definitions can change between turns while the rest of the cached prefix stays valid. This makes it affordable to load a narrow tool set by default and attach extra MCP servers only for the turns that need them, instead of carrying every schema for the whole session.

On the Sonnet tier, mid-conversation tool changes (beta) are supported on **Sonnet 5.5 but not Sonnet 5**, so dynamic tool sets keep the cache only after you move to Sonnet 5.5.

That header is for your own API calls. Inside Claude Code the question is tool search: with it on (the default), connecting or removing an MCP server keeps the cache; with it off, connecting or removing a server, or denying an entire tool, invalidates it.

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

Anthropic's costs page gives the same advice: set `model: haiku` in the subagent configuration for simple subagent tasks. Without it, a subagent can inherit your session's model, so a switch to Opus applies to it too. The `sonnet` alias resolves by provider: on Bedrock, Google Cloud and Microsoft Foundry it means Sonnet 4.5 ($3/$15, 200K; deprecated, retirement scheduled for 2026-11-30), not Sonnet 5.5 ($2/$10), so pin `claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) there -- see [Guide 06](06-access-methods-pricing.md#anthropic-api-direct-pricing).

The `haiku` alias resolves by provider too. On the Anthropic API it means **Haiku 5.5** (Claude Code v2.1.293+): $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above, and the 100K counts cache reads and writes. That makes Haiku 5.5 the right subagent model for short search, classification, extraction and routing calls, and the wrong one for a subagent that reads half the repo: past 100K its rates rise 5x. On Claude Platform on AWS, Bedrock, Google Cloud and Foundry, `haiku` still means legacy Haiku 4.5 ($1/$5, 200K); pin `ANTHROPIC_DEFAULT_HAIKU_MODEL` to `claude-haiku-5-5` (Bedrock: `anthropic.claude-haiku-5-5`), which also sets the model for background functionality. Haiku 5.5 thinks by default too (effort `medium`, and Claude Code cannot turn it off), but its reasoning bills as output at $0.50/MTok up to 100K prompt tokens.

On Opus 5.5 subagents, adaptive thinking is **always on** -- `thinking: {type: "disabled"}` returns a 400 -- and reasoning tokens bill as **output** at $20/MTok. A fan-out of ten search subagents on Opus 5.5 pays for ten sets of reasoning tokens, so lower the effort level (default `medium`) or, better, route subagents that just grep and summarize to Haiku 5.5. On legacy Opus 5, thinking is on by default at $25/MTok and can be disabled only at effort `high` or below. Also note that `max_tokens` caps thinking plus visible text together, so a subagent with a tight `max_tokens` and high effort can burn its budget reasoning and return nothing usable.

Subagents also cache on a shorter clock: on a Claude subscription the main conversation gets a one-hour cache TTL, but subagents get five minutes (tunable with `subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`).

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

Claude Code's **agent teams** are the extreme case: Anthropic's costs page says they use about **7x the tokens** of a standard session when teammates run in plan mode, because each teammate keeps its own context window. Keep teams small and shut teammates down when their work is done.

### Cost Controls

Use `--max-budget-usd` to cap spending. It works in print mode (`-p`) only:

```bash
claude -p --max-budget-usd 5 "analyze this codebase"
```

Use `--fallback-model` to auto-switch when the primary model is overloaded:

```bash
claude --model opus --fallback-model sonnet "complex refactoring task"
```

If you call the API directly, Opus 5's server-side `fallbacks` parameter (header `anthropic-beta: server-side-fallback-2026-07-01`) covers a different case: Opus 5 ships cybersecurity safety classifiers, and a cyber refusal can auto-fall-back to Opus 4.8 server-side instead of failing the request and forcing you to pay for a client-side retry.

If you are billed for Managed Agents rather than raw tokens, budget the session runtime line too: **$0.08 per session-hour** while a session is `running`. That is on top of standard token rates, and it replaces Code Execution container-hour billing rather than stacking with it.

---

## Key Takeaways

1. **MCP tool search is on by default** -- only tool names and server instructions enter context until a tool is used; the ~500-3,000 tokens per server per turn in the table above applies only with tool search off
2. **Use project-level MCP configs** instead of global to avoid loading unnecessary servers, and disable unused ones with `/mcp`
3. **Prefer CLI tools** (`gh`, `aws`, `gcloud`, `sentry-cli`) over an MCP server when one exists -- they add no per-tool listing
4. **Cap tool output** -- warning above 10,000 tokens, default cap 25,000 (`MAX_MCP_OUTPUT_TOKENS`)
5. **Subagents save money on large searches** but cost more for simple one-off queries
6. **Use `claude -p --max-budget-usd`** (print mode only) to prevent runaway costs in automated/SDK workflows
7. **Haiku 5.5 subagents** (`model: haiku` on the Anthropic API) are ideal for search/exploration tasks at 40x lower per-token cost than Opus 5.5 while the prompt stays at or under 100K tokens (8x above)
8. **Agent teams use ~7x the tokens** of a standard session when teammates run in plan mode -- keep them small
9. **With tool search on, adding or removing a server keeps the cache** in Claude Code; on your own API calls, the `mid-conversation-tool-changes-2026-07-01` beta on Opus 5 does the same for changed tool definitions, and on the Sonnet tier mid-conversation tool changes need Sonnet 5.5 (Sonnet 5 does not support them)
10. **Opus 5.5 always thinks** and reasoning tokens bill as output at $20/MTok -- lower the effort level, or route subagents that only search and summarize to Haiku 5.5
