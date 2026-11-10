# Guide 07: MCP Server and Agent Cost Impact

> MCP servers and subagents are powerful -- but each one adds tokens to your context. Understanding the overhead helps you keep costs under control.

---

## Table of Contents

- [MCP Server Token Overhead](#mcp-server-token-overhead)
- [Measuring Your MCP Cost](#measuring-your-mcp-cost)
- [Optimization Strategies](#optimization-strategies)
- [Code Search and Retrieval Servers](#code-search-and-retrieval-servers)
  - [Does a Retrieval Server Pay for Itself?](#does-a-retrieval-server-pay-for-itself)
- [Subagent Cost Patterns](#subagent-cost-patterns)
- [Agent SDK Cost Considerations](#agent-sdk-cost-considerations)
- [Key Takeaways](#key-takeaways)

---

## MCP Server Token Overhead

In Claude Code, **MCP tool search is on by default** ([MCP docs](https://code.claude.com/docs/en/mcp) and [costs page](https://code.claude.com/docs/en/costs), read 2026-11-01). Tool definitions are deferred: only **tool names and server instructions** enter context until Claude uses a specific tool, and then that tool's schema loads. Anthropic publishes no per-server token figure for deferred servers.

Full **tool schemas** load into the prompt up front, on every turn, only when tool search is off (or for a server you mark `alwaysLoad: true`):

- `ENABLE_TOOL_SEARCH=false`, `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`, or a HIPAA configuration
- `ENABLE_TOOL_SEARCH=auto` or `auto:N` while the deferred tools' definitions total under the threshold (10% of the context window for `auto`; see [Tool Search](#tool-search-deferred-tools))
- a gateway that rejects it: tool search is on by default behind a custom `ANTHROPIC_BASE_URL` since v2.1.304 (it was off before unless `ENABLE_TOOL_SEARCH` was `true`, `auto` or `auto:N`), and since v2.1.305 Claude Code can retry a request without it after a `400` or `422` whose cause it does not recognize, so tools load up front, and it tries tool search again later (set `ENABLE_TOOL_SEARCH=false` to skip the rejected requests)
- models older than the Claude 4.5 generation on Google Cloud (Google managed, formerly Vertex AI; Claude Code calls it Google Cloud's Agent Platform), and Microsoft Foundry deployments hosted on Azure, which reject it

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

On Opus 5.5:  750K tokens x $4.00/1M = $3.00 uncached; with caching (turn 1 written, 49 turns read)
              15K x $5/1M + 735K x $0.20/1M = $0.22 (about 30% more if the new tokenizer inflates the schema)
On Opus 5:    750K tokens x $5.00/1M = $3.75 uncached (legacy); cached 15K x $6.25/1M + 735K x $0.50/1M = $0.46
On Sonnet 5.5: 750K tokens x $2.00/1M = $1.50 uncached; cached 15K x $2.50/1M + 735K x $0.10/1M = $0.11
On Haiku 5.5:  750K tokens x $0.10/1M = $0.075 uncached while each request stays <= 100K prompt tokens
               (750K x $0.50/1M = $0.375 once the requests are over 100K)
```

Rates from [Anthropic's pricing page](https://platform.claude.com/docs/en/about-claude/pricing), read 2026-11-01 (5-minute cache write 1.25x input; cache hit 0.05x on Opus 5.5 and Sonnet 5.5, 0.1x on Opus 5).

With tool search on (the default), that per-turn schema load does not happen: only tool names and server instructions ride along until a tool is used. This is why the old advice that "adding a server breaks the cache" is out of date -- with tool search on, connecting or removing a server does **not** invalidate the prompt cache. It still does when tool search is off, and so does enabling or disabling a plugin that provides MCP servers.

Add the tool-use system prompt on top of the schemas themselves: **286 tokens** with `tool_choice: auto` or `none`, **406 tokens** with `any` or `tool` (Opus 5.5 and Sonnet 5.5 reject forced `any`/`tool`, so only 286 applies there; Haiku 5.5 supports forced tool use, so both apply). Individual built-in tools cost more (the bash tool adds 325 input tokens on Opus 5 / 4.8 / 4.7, 244 on Opus 4.6 and earlier; the text editor tool adds 700).

With prompt caching, the actual cost is much lower: cached schema tokens bill at 0.1x base input on most models (0.05x on Opus 5.5 and Sonnet 5.5, 0.025x on Fable 5.2 and Fable 5.1). But the first turn and any cache misses still pay full price. Note that the minimum cacheable prompt on Fable 5.2, Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5 is only **512 tokens** (Opus 4.8 and Sonnet 5 needed 1,024, Opus 4.7 needed 2,048, Opus 4.6 and Haiku 4.5 needed 4,096), so even a single small MCP server's schemas are now big enough to cache.

### Tool Search (Deferred Tools)

Tool search is **on by default** in Claude Code: schemas load only when Claude uses a tool, not all at once. What it removes is the full-schema load described above for every tool you do not call. Anthropic has measured it on the API: with all tools loaded, a run's cost rose from $0.55 to $1.02 at 502 tools, while with tool search it stayed at $0.56 (45% less) at the same accuracy, and deferring a GitHub MCP server's toolset cut a run 20% ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), "Defer unused tool definitions", read 2026-11-01). An earlier engineering post measured the Tool Search Tool cutting about 77K tokens of definitions to about 8.7K, 85% fewer ([advanced tool use, 2025-11-24](https://www.anthropic.com/research/advanced-tool-use), read 2026-11-01). There is no Claude Code-specific figure. Leave it on unless you have a reason to turn it off; a custom `ANTHROPIC_BASE_URL` no longer turns it off by itself (see the list above).

`ENABLE_TOOL_SEARCH` takes these values ([MCP docs](https://code.claude.com/docs/en/mcp), "Configure tool search", and [environment variables](https://code.claude.com/docs/en/env-vars), read 2026-11-03):

| Value | What loads |
|-------|------------|
| unset or `true` | MCP tools are deferred and load on demand, with the exceptions in the list above |
| `auto` | Threshold mode: tools load up front while their definitions total under 10% of the context window; at 10% or more tool search turns on, and once on it can stay on for the conversation even if the total later drops |
| `auto:N` | Threshold mode with your own percentage, `N` from 0 to 100 (`auto:5` is 5%) |
| `false` | Every MCP tool loads up front, no deferral |

Below its threshold, `auto` puts full schemas back in every request, and with them the old cache rule: a server connecting mid-session, or one you disable in `/mcp`, then invalidates the cache ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching), read 2026-11-03). To keep a few always-needed tools visible without giving up deferral for the rest, set `alwaysLoad: true` on that one server instead.

Descriptions are capped too. Claude Code cuts a tool description or server instructions that load up front at 4,096 characters (raised from 2,048 in v2.1.296) and a description loaded through tool search at 16,384 characters; `CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH` (v2.1.280+) changes both ([MCP docs](https://code.claude.com/docs/en/mcp), read 2026-11-01). The cap bounds what one verbose server can add to every request when its tools load up front.

### MCP Tool Output

What a tool **returns** costs tokens too, deferred or not. Claude Code warns when an MCP tool's output exceeds **10,000 tokens** and caps it at **25,000 tokens** by default; raise or lower the cap with `MAX_MCP_OUTPUT_TOKENS`. A lower cap is a cost backstop for servers that dump whole pages or tables.

---

## Measuring Your MCP Cost

Measure rather than estimate. Inside a session, `/context` shows what is consuming context space, and on a Pro, Max, Ultra, Team or Enterprise plan `/usage` attributes recent usage to individual MCP servers as a share of the total ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-01). That share counts only the requests that consumed one of the server's tool results ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-03).

For a longer window on any provider, `claude-rate --usage --by mcp,skill,plugin,agent` (claude-rate 0.4.0 or later) groups 30 days of your local transcripts by the attribution fields Claude Code writes on each request. Read each row as "requests Claude Code tagged with X", not as what X added: the fields are undocumented, a tag covers the whole request, cached prefix included, for as long as the server or skill is active, and one request can carry several tags, so the rows overlap and do not sum to your total. A row's dollars say where tagged spend sat, not what removing X would save.

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

A beta removes the penalty on the Claude API:

```
anthropic-beta: inline-tools-2026-09-15
```

With that header, tools can be added or removed between turns by appending a mid-conversation system message, and a tool can be defined inside a `tool_addition` block, while the `tools` array and the rest of the cached prefix stay exactly as sent. The older `mid-conversation-tool-changes-2026-07-01` header still works for changes that name a tool by reference, on the Claude API, Amazon Bedrock and Google Cloud (Google managed). This makes it affordable to load a narrow tool set by default and attach extra MCP servers only for the turns that need them, instead of carrying every schema for the whole session.

The beta covers Fable 5.2, Mythos 5.2, Fable 5.1, Mythos 5.1, Fable 5, Mythos 5, Opus 5.5, Opus 5, Opus 4.8, Sonnet 5.5 and Haiku 5.5 -- on the Sonnet tier **Sonnet 5.5 but not Sonnet 5**, so dynamic tool sets keep the cache only after you move to Sonnet 5.5 ([mid-conversation system messages and tool changes](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages), [Opus 5.5 migration guide](https://platform.claude.com/docs/en/models/opus-5-5/migration-guide), read 2026-11-01).

Those headers are for your own API calls. Inside Claude Code the question is tool search: with it on (the default), connecting or removing an MCP server keeps the cache; with it off, connecting or removing a server, or denying an entire tool, invalidates it.

---

## Code Search and Retrieval Servers

Several popular MCP servers promise cheaper code search: a symbol layer over a language server or IDE (Serena), a vector index (claude-context) and a graph index (codebase-memory-mcp). Compare them with what Claude Code already has. Its LSP tool jumps to definitions, finds references and reports type errors once you install a code intelligence plugin for your language (it stays inactive until then, and in cloud sessions) ([tools reference](https://code.claude.com/docs/en/tools-reference), read 2026-11-03), and Grep and Read cover the rest.

Some of these servers cost more than tokens. claude-context needs a vector database and an embedding API, so your code chunks go to that embedding provider unless you run both locally (its FAQ describes Milvus in Docker plus Ollama) ([claude-context README](https://github.com/zilliztech/claude-context), read 2026-11-03).

Each project's own figures, as it reports them. None is a Claude Code measurement of cost per task, and none converts into the `S` of the formula below: different models, tokenizers and units.

| Project | What it measured | Model and size | What it reports | Read |
|---------|------------------|----------------|-----------------|------|
| [claude-context](https://github.com/zilliztech/claude-context/blob/HEAD/evaluation/README.md) (vector index) | Code retrieval on 30 SWE-bench Verified instances (15 to 60 minutes, exactly 2 files modified), grep-only agent vs the same agent plus the server | GPT-4o-mini, each arm run 3 times, means only | Tokens per instance 73,373 vs 44,449 (39.4% fewer), summed input plus output over every call in the agent loop; retrieval F1 on the modified files 0.40 in both arms, which is not a task pass rate | 2026-11-03 |
| [codebase-memory-mcp](https://arxiv.org/abs/2603.27277) (graph index), the authors' preprint | 12 question categories on 31 repositories, graded by the first author against manually derived answers | Claude Opus 4.6, one backend; the paper's 14-tool version | About 1,000 vs about 10,000 tokens per question ("ten times fewer", rounded) and a graded quality score of 0.83 vs 0.92 for a file-exploration agent, not a pass rate | 2026-11-03 |
| [Serena](https://github.com/oraios/serena/blob/HEAD/docs/04-evaluation/030_results/010_cc_on_tianshou.md) (symbol layer) | A self-assessment written by Claude Code itself: 20 tasks on one codebase (Tianshou), with the paid JetBrains backend; the free LSP backend was not evaluated | Claude Opus 4.6 at `medium` | Call counts and edit payload sizes only, no token totals and no quality score; its verdict is one call instead of a chain for cross-file renames and moves, and comparable or slightly less efficient for small single-file edits | 2026-11-03 |

### Does a Retrieval Server Pay for Itself?

A server costs what it loads up front on every request, and saves what it keeps out of the conversation. The first half is the formula this repo already uses for CLAUDE.md: a fixed prefix of `D` tokens costs `D x (w + (T - 1) x h)` over `T` turns, with `w` the cache write rate and `h` the cache-hit rate ([Guide 01](01-understanding-costs.md#claudemd-cost-over-a-session)). The second half:

```
saving from one use at turn t of T  =  S x (w + (T - t) x h)
  S = net tokens kept out: what the plain read would have returned
      minus the server's own result tokens; sum it over every use in the task
pays for itself when  sum of savings  >=  D x (w + (T - 1) x h)  +  E
  E = dollars outside Claude tokens: embedding calls, a hosted index
cost per completed task  =  session cost / pass rate
```

The payback turn is the first `T` at which the savings cover the carry cost. Cost per completed task needs a pass rate you measure yourself on your own tasks: none of the three projects above publishes one.

With tool search on, `D` is only the server's tool names and instructions until Claude calls one of its tools. Anthropic publishes no per-server figure for that ([MCP Server Token Overhead](#mcp-server-token-overhead)); the only bound is the 4,096-character cap on an up-front description or server instructions. Measure your own with `/context`, and `/usage` on a plan, rather than assuming a size.

Worked examples, with `S` = 20,000 net tokens kept out at turn 20 of a 30-turn session (an illustrative round number, not a measurement):

```
Opus 5.5, 5-minute TTL:    20,000 x ($5.00 + 10 x $0.20) / 1M = $0.14
Sonnet 5.5, 5-minute TTL:  20,000 x ($2.50 + 10 x $0.10) / 1M = $0.07
Opus 5.5, 1-hour TTL:      20,000 x ($8.00 + 10 x $0.20) / 1M = $0.20
                           (a subscription's main conversation)
```

On the 5-minute rows, that one use covers an up-front load of up to about 12,960 tokens carried over all 30 turns (computed: $0.14 / (($5.00 + 29 x $0.20) / 1M) on Opus 5.5, the same on Sonnet 5.5, whose rates are half), before `E` and before any change in pass rate. A server that lowers your pass rate can cost more per completed task even when it saves tokens.

---

## Subagent Cost Patterns

Subagents (`Agent` tool) run in separate contexts. Each subagent is a full Claude session with its own input/output billing.

### Cost Formula

```
Subagent cost = (system prompt + task prompt + tool results) x model price
Main context savings = avoided context pollution from search results
```

Priced the way Claude Code caches, for one read of `F` tokens with `T` main-thread requests after it (`w` = 5-minute write, `h` = cache hit, `o` = output rate of the model that bills each request):

```
Read on the main thread:  F x (w_main + T x h_main)
Delegate:                 D x o_main + (D + S) x (w_main + T x h_main)      delegation prompt D, summary S
                        + O x (w_sub + h_sub) + F x w_sub + S x o_sub       subagent overhead O, two requests
```

[Delegation break-even](../benchmarks/delegation-breakeven.md) works this through for a Haiku 5.5 subagent and for one that inherits Opus 5.5, including Haiku 5.5's 100K price line, with the assumptions stated. It is a computed token-cost floor, not a measurement: on those assumptions a Haiku 5.5 subagent repays its overhead on reads of a few thousand tokens, while one that inherits Opus 5.5 rarely pays on tokens alone.

### When Subagents Save Money

| Pattern | Without Subagent | With Subagent | Savings |
|---------|:----------------:|:-------------:|:-------:|
| Large codebase search | Search results bloat main context for all remaining turns | Search results isolated, only summary returns | Not measured; depends on how much the subagent reads vs returns |
| Parallel research (3 agents) | Sequential searches, each adding to context | 3 small isolated contexts | Often more, not less: multi-agent research used ~15x chat tokens; agent teams ~7x a standard session |
| Background tasks | Block main context while waiting | Run in background, results on completion | Time saved |

The published subagent measurements are all outside Claude Code. In Anthropic's [cost-optimization cookbook](https://platform.claude.com/cookbook/cost-optimization-cost-optimization), moving the work into a subagent cut one agent loop's cost 78% ($1.7945 to $0.3978). In the [cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence) ("Orchestrator strategy"), delegation to Sonnet 5 workers saved money in only two measured situations, routine work with a long cost tail and work larger than one context window, and adding Haiku 5.5 subagents to Opus 5.5 at `medium` on Claude Managed Agents cut cost per attempt by 32% and the pass rate by about 4 percentage points, about what a mix of `low` and `medium` effort without subagents would give at that cost (read 2026-11-01). Subagents save when they read far more than they return and run on a cheaper model; for Haiku 5.5 subagents on coding tasks, Anthropic says to compare with lower effort first.

To see your own split, `claude-rate --usage` (claude-rate 0.4.0 or later) divides 30 days of local list-price spend between the main conversation and subagents, by agent type, from the transcripts on your machine. It tells you whether subagents are a large enough share of your spend for these choices to matter.

### When Subagents Cost More

- **Simple, one-off queries**: The overhead of spinning up a new context (system prompt, CLAUDE.md) costs more than just doing the search in the main context
- **Tasks requiring main context knowledge**: Subagents don't inherit conversation history, so you have to re-explain context (a fork does inherit it; see the cache note at the end of this section)
- **Haiku subagents for complex tasks**: If the subagent fails and you retry on a better model, you've paid twice
- **Multi-agent fan-out**: Anthropic's multi-agent research system used about 15x the tokens of a chat (a single agent about 4x), and token usage alone explained 80% of the variance in its BrowseComp results ([multi-agent research system, 2025-06-13](https://www.anthropic.com/research/multi-agent-research-system), read 2026-11-01). Claude Code's agent teams (experimental, off by default; enable with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) use about 7x the tokens of a standard session when teammates run in plan mode ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-01).
- **An Opus subagent for a small read**: a subagent that inherits Opus 5.5, as the built-in Explore does under an Opus 5.5 main conversation, writes its whole starting context at the same rate the main thread would pay for the read itself, so on tokens alone it pays only for large reads followed by many main-thread turns (computed in [Delegation break-even](../benchmarks/delegation-breakeven.md))
- **A Fable 5.2 session whose prompts invite delegation**: in Anthropic's testing Fable 5.2 delegates readily to subagents when a prompt invites it, and Anthropic warns that "subagents can account for a large part of what a session costs" ([what's new in Fable 5.2](https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2), read 2026-11-10). Invite subagents only for work that passes the fit test below, and pin a cheaper `model` on the subagents you define ([Model Selection for Subagents](#model-selection-for-subagents))

**A fit test before delegating** (adapted from [houtini-lm's delegation guide](https://github.com/houtini-ai/houtini-lm/blob/HEAD/manual/delegation.md), read 2026-11-03, which hands work to non-Claude models; its economics and figures are not Claude subagent numbers):

- **Can you brief it in one message, and check the result at a glance?** Bounded, self-contained work fits: searching, summarizing a log, reading many files to answer one question.
- **Is it bulky in tokens and shallow in reasoning?** Delegation pays when the subagent reads far more than it returns.
- **Does it need cross-file judgement you have not put in the prompt?** Keep it on the main thread; the subagent knows only what the delegation prompt and its own reads give it.
- **Is it faster to do than to brief?** A one-line change does not repay the subagent's starting context.

Cut that starting context where you can: a custom subagent with `omitClaudeMd: true` (v2.1.271+) starts without the user, project and local CLAUDE.md files, which suits a subagent that takes everything it needs from the delegation prompt ([sub-agents docs](https://code.claude.com/docs/en/sub-agents), read 2026-11-03).

### Model Selection for Subagents

```json
// Use haiku for simple searches, sonnet for analysis
{
  "model": "haiku"  // In agent frontmatter or via model parameter
}
```

Anthropic's costs page gives the same advice: set `model: haiku` in the subagent configuration for simple subagent tasks. Without it, a subagent can inherit your session's model, so a switch to Opus applies to it too. That includes the built-in **Explore** subagent: it runs on the main conversation's model, not Haiku. The one exception is a Fable main conversation: with a Claude subscription, a Console account or an LLM gateway reached through `ANTHROPIC_BASE_URL`, Explore runs on the Opus model the `opus` alias resolves to, and on Bedrock, Google Cloud's Agent Platform, Foundry, Claude Platform on AWS or a Claude apps gateway it stays on the Fable model. To explore on Haiku, define your own `Explore` subagent with `model: haiku`, or set `CLAUDE_CODE_SUBAGENT_MODEL=haiku` plus `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` (v2.1.257+; forks and skills that run in a subagent with `model: inherit` still use the main model). Explore and Plan start without your CLAUDE.md files and the git status snapshot, which keeps them cheap. Since v2.1.292 (2026-10-06) the Agent tool also takes an `effort` parameter, and `CLAUDE_CODE_SUBAGENT_EFFORT` (v2.1.316, 2026-10-31) sets the effort subagents run at when nothing else names one, instead of inheriting the session's (the changelog states this; the sub-agents docs do not list the variable yet) ([sub-agents docs](https://code.claude.com/docs/en/sub-agents), [changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01). The `sonnet` alias resolves by provider: on Bedrock, Google Cloud (Google managed) and Microsoft Foundry it means Sonnet 4.5 ($3/$15, 200K; deprecated, retirement scheduled for 2026-11-30), on Claude Platform on AWS Sonnet 4.6 ($3/$15), not Sonnet 5.5 ($2/$10), so pin `claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) there ([model-config alias table](https://code.claude.com/docs/en/model-config), read 2026-11-01) -- see [Guide 06](06-access-methods-pricing.md#anthropic-api-direct-pricing).

The `haiku` alias resolves by provider too. On the Anthropic API it means **Haiku 5.5** (Claude Code v2.1.293+): $0.10/$0.50 up to 100K prompt tokens, $0.50/$2.50 above, and the 100K counts cache reads and writes. That makes Haiku 5.5 the right subagent model for short search, classification, extraction and routing calls, and the wrong one for a subagent that reads half the repo: past 100K its rates rise 5x. On Claude Platform on AWS, Bedrock, Google Cloud (Google managed) and Foundry, `haiku` still means legacy Haiku 4.5 ($1/$5, 200K); pin `ANTHROPIC_DEFAULT_HAIKU_MODEL` to `claude-haiku-5-5` (Bedrock: `anthropic.claude-haiku-5-5`), which also sets the model for background functionality. Haiku 5.5 thinks by default too (effort `medium`, and Claude Code cannot turn it off), but its reasoning bills as output at $0.50/MTok up to 100K prompt tokens.

On Opus 5.5 subagents, adaptive thinking is **always on** -- `thinking: {type: "disabled"}` returns a 400 -- and reasoning tokens bill as **output** at $20/MTok. A fan-out of ten search subagents on Opus 5.5 pays for ten sets of reasoning tokens, so lower the effort level (default `medium`) or, better, route subagents that just grep and summarize to Haiku 5.5. On legacy Opus 5, thinking is on by default at $25/MTok and can be disabled only at effort `high` or below. Also note that `max_tokens` caps thinking plus visible text together, so a subagent with a tight `max_tokens` and high effort can burn its budget reasoning and return nothing usable.

Subagents also cache on a shorter clock: on a Claude subscription the main conversation gets a one-hour cache TTL, but subagents get five minutes (tunable with `subagentPromptCacheTtl` / `CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`). An ordinary subagent starts a fresh cache of its own, because its system prompt and tool set differ from the parent's. A fork (`subagent_type: "fork"`, on by default in `claude -p`, the Agent SDK, the desktop app and VS Code since v2.1.302; `CLAUDE_CODE_FORK_SUBAGENT=0` turns it off) inherits the parent's system prompt, tools and history exactly, so its first request reads the parent's cache; its requests still fall in the five-minute bucket ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching), "Subagents and the cache", [changelog](https://code.claude.com/docs/en/changelog), read 2026-11-01).

Three more frontmatter fields bound what one custom subagent can spend ([sub-agents docs](https://code.claude.com/docs/en/sub-agents), "Supported frontmatter fields", read 2026-11-03):

- **`maxTurns`**: the most agentic turns the subagent takes before it stops. Claude Code returns its output marked as partial (v2.1.246+), and Claude can resume it to continue, so a runaway search ends at a known size instead of running on.
- **`omitClaudeMd: true`** (v2.1.271+): the subagent starts without the user, project and local CLAUDE.md files; managed policy files still load, and so do a subdirectory's CLAUDE.md and path-scoped rules when it works with files there. Use it for subagents that take everything from the delegation prompt; Explore and Plan already skip CLAUDE.md.
- **`experimental: {cacheTtl: 1h}`** (v2.1.248+): this subagent's own prompt cache lifetime, `5m` or `1h`, written inside the `experimental` map, not at the top level. It is read only from subagent files (the `--agents` JSON ignores `experimental`), and `1h` is ignored while a subscription is drawing on usage credits. The 1-hour write costs 2x input against 1.25x, so it pays only when enough of the subagent's turns follow a pause of 5 to 60 minutes (breakeven in [Guide 08](08-prompt-caching.md#extended-ttl-economics)).

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

Claude Code's **agent teams** are the extreme case: Anthropic's costs page says they use about **7x the tokens** of a standard session when teammates run in plan mode, because each teammate keeps its own context window. Agent teams are experimental and off by default (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` enables them). Keep teams small and shut teammates down when their work is done ([costs page](https://code.claude.com/docs/en/costs), read 2026-11-01).

### Cost Controls

Use `--max-budget-usd` to cap spending. It works in print mode (`-p`) only, checks Claude Code's client-side cost estimate (which can differ from your bill), counts subagent spend, and can be passed by a little, so leave headroom ([CLI reference](https://code.claude.com/docs/en/cli-reference), read 2026-11-01):

```bash
claude -p --max-budget-usd 5 "analyze this codebase"
```

Use `--fallback-model` to auto-switch when the primary model is overloaded or unavailable (it accepts a comma-separated chain):

```bash
claude --model opus --fallback-model sonnet "complex refactoring task"
```

If you call the API directly, the server-side `fallbacks` parameter (beta, header `anthropic-beta: server-side-fallback-2026-07-01`, on the Claude API and Google Cloud (Anthropic managed)) covers a different case: Fable 5.1, Fable 5, Opus 5.5, Opus 5, Sonnet 5.5 and Haiku 5.5 ship safety classifiers, and with `fallbacks` set to `"default"` a declined request is re-run on the fallback model Anthropic recommends for its refusal category inside one API call, billed at the fallback model's rates, instead of failing and forcing you to build a client-side retry. Haiku 5.5 has no server-side fallback ([refusals and fallback](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback), read 2026-11-01). Fable 5.2's fallback targets are Opus 4.8 for cyber refusals and Opus 5 for bio, both $5/$25 against Fable 5.2's $8/$40 ([what's new in Fable 5.2](https://platform.claude.com/docs/en/models/fable-5-2/whats-new-fable-5-2), read 2026-11-10).

If you are billed for Managed Agents rather than raw tokens, budget the session runtime line too: **$0.08 per session-hour** while a session is `running`. That is on top of standard token rates, and it replaces Code Execution container-hour billing rather than stacking with it.

Max, Ultra (formerly Max 20x, $200 a month) and Team plans include monthly Claude API credits -- $100 on Max, $200 on Ultra, $20 per Standard seat and $100 per Premium seat on Team (pooled, capped at $500 a month). They cover the Claude API, Managed Agents and the Agent SDK when you use an API key from the linked Console organization, and they do not cover Claude Code ([API credits for subscribers](https://platform.claude.com/docs/en/about-claude/api-credits-for-subscribers), read 2026-11-01).

---

## Key Takeaways

1. **MCP tool search is on by default** -- only tool names and server instructions enter context until a tool is used; the ~500-3,000 tokens per server per turn in the table above applies only with tool search off
2. **Use project-level MCP configs** instead of global to avoid loading unnecessary servers, and disable unused ones with `/mcp`
3. **Prefer CLI tools** (`gh`, `aws`, `gcloud`, `sentry-cli`) over an MCP server when one exists -- they add no per-tool listing
4. **Cap tool output** -- warning above 10,000 tokens, default cap 25,000 (`MAX_MCP_OUTPUT_TOKENS`)
5. **Subagents can save money on large searches** (no Claude Code measurement; Anthropic's cookbook loop: 78%; its cost guide found delegation saved money in only two situations) but cost more for simple one-off queries; Anthropic's multi-agent research system used about 15x the tokens of a chat. Fable 5.2 delegates readily when a prompt invites it, so invite it only for work that passes the fit test
6. **Use `claude -p --max-budget-usd`** (print mode only) to prevent runaway costs in automated/SDK workflows
7. **Haiku 5.5 subagents** (`model: haiku` on the Anthropic API) are ideal for search/exploration tasks at 40x lower per-token cost than Opus 5.5 while the prompt stays at or under 100K tokens (8x above)
8. **Agent teams (experimental, off by default) use ~7x the tokens** of a standard session when teammates run in plan mode -- keep them small
9. **With tool search on, adding or removing a server keeps the cache** in Claude Code; on your own API calls, the `inline-tools-2026-09-15` beta (or the older `mid-conversation-tool-changes-2026-07-01` for changes by reference) does the same for changed tool definitions on Opus 5.5, Opus 5, Opus 4.8, Fable and Haiku 5.5, and on the Sonnet tier mid-conversation tool changes need Sonnet 5.5 (Sonnet 5 does not support them)
10. **Opus 5.5 always thinks** and reasoning tokens bill as output at $20/MTok -- lower the effort level, or route subagents that only search and summarize to Haiku 5.5
11. **A code search server pays only if the tokens it keeps out beat what it loads, plus any embedding or index cost** -- the published figures for these servers are each project's own, on other models or other units, so measure `S` and your pass rate on your own tasks
