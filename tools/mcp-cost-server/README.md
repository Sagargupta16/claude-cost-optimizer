# MCP Cost Server

A lightweight Model Context Protocol (MCP) server that provides token cost estimation tools for Claude Code. Query it mid-session to estimate costs, compare models, or project session-level spend.

## Installation

```bash
cd tools/mcp-cost-server
npm install
npm run build
```

## Configuration

Register it with the CLI (user scope, so it is available in every project):

```bash
claude mcp add --scope user cost-estimator -- node /path/to/claude-cost-optimizer/tools/mcp-cost-server/dist/index.js
```

Or add it to `.mcp.json` at a project root to share it with that project. Claude Code reads MCP servers from `.mcp.json` and `~/.claude.json`, not from `settings.json`:

```json
{
  "mcpServers": {
    "cost-estimator": {
      "command": "node",
      "args": ["/path/to/claude-cost-optimizer/tools/mcp-cost-server/dist/index.js"]
    }
  }
}
```

Replace `/path/to/` with the actual absolute path to this repository on your machine.

## Tools

### estimate_cost

Estimate token count and cost for a given text input.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `text` | string | yes | The text to estimate tokens for |
| `model` | string | no | `fable` (Fable 5.1), `fable-5`, `opus` (Opus 5.5), `opus-5`, `opus-4.8`, `opus-4.7`, `opus-4.6`, `sonnet` (Sonnet 5), `sonnet-4.6`, or `haiku` (default: `sonnet`) |
| `turns` | number | no | Project cost over this many conversation turns |

**Example usage:**

> "Estimate the cost of sending this 500-line file to Opus over 10 turns."

Returns token count, single-pass input/output cost, and (if `turns` specified) a projected multi-turn total that accounts for cumulative history growth and a 70% cache hit rate.

### session_estimate

Estimate total cost for an entire Claude Code session.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `turns` | number | yes | Number of conversation turns |
| `model` | string | no | `fable` (Fable 5.1), `fable-5`, `opus` (Opus 5.5), `opus-5`, `opus-4.8`, `opus-4.7`, `opus-4.6`, `sonnet` (Sonnet 5), `sonnet-4.6`, or `haiku` (default: `sonnet`) |
| `claude_md_lines` | number | no | Lines in your CLAUDE.md (default: 0) |
| `mcp_servers` | number | no | Number of configured MCP servers (default: 0) |

**Example usage:**

> "Estimate a 30-turn Sonnet session with a 200-line CLAUDE.md and 5 MCP servers."

Returns a breakdown of cost by component (system prompt, CLAUDE.md, MCP schemas, conversation history, output) plus actionable recommendations for reducing cost.

**Assumptions used in the estimate:**

- System prompt: ~3,500 tokens (fixed, loaded every turn)
- CLAUDE.md: ~7 tokens per line (loaded every turn)
- MCP servers: ~1,500 tokens per server, this tool's own assumption rather than a published figure. It models full schemas, which load up front only when tool search is off (`ENABLE_TOOL_SEARCH=false`, a custom `ANTHROPIC_BASE_URL`, or models older than the Claude 4.5 generation on Google Cloud). Tool search is on by default, and then only tool names and server instructions enter context until Claude uses a tool
- Conversation history: ~1,500 tokens per turn (cumulative)
- Output: ~500 tokens per turn
- Cache hit rate: 70% on stable content (system prompt, CLAUDE.md, schemas)

### compare_models

Compare cost across every model in the pricing table for a given workload.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `input_tokens` | number | yes | Number of input tokens |
| `output_tokens` | number | yes | Number of output tokens |

**Example usage:**

> "Compare model costs for 100K input tokens and 5K output tokens."

Returns cost for each model, identifies the cheapest option, and shows the percentage saved versus the most expensive model.

## Pricing Reference

All estimates use current API pricing (verified 2026-09-28, per 1M tokens):

| Model | Input | Output | Cache Hit | Min cacheable prompt |
|-------|-------|--------|-----------|---------------------:|
| Fable 5.1 (alias: `fable`) | $10.00 | $50.00 | **$0.25** | 512 |
| Fable 5 (alias: `fable-5`) | $10.00 | $50.00 | $1.00 | 512 |
| Opus 5.5 (alias: `opus`) | $4.00 | $20.00 | **$0.20** | 512 |
| Opus 5 (alias: `opus-5`, legacy) | $5.00 | $25.00 | $0.50 | 512 |
| Opus 4.8 (alias: `opus-4.8`, legacy) | $5.00 | $25.00 | $0.50 | 1,024 |
| Opus 4.7 (alias: `opus-4.7`, legacy) | $5.00 | $25.00 | $0.50 | 2,048 |
| Opus 4.6 (alias: `opus-4.6`, legacy) | $5.00 | $25.00 | $0.50 | 4,096 |
| Sonnet 5 (alias: `sonnet`) | $2.00 | $10.00 | $0.20 | 1,024 |
| Haiku 4.5 (alias: `haiku`) | $1.00 | $5.00 | $0.10 | 4,096 |

Cache hits have three multipliers: 0.1x base input by default, 0.025x on Fable 5.1 and Mythos 5.1, and 0.05x on Opus 5.5.

Token estimation uses a ~4 characters per token approximation. This is a reasonable average for English text and code but will vary with content type.

**Minimum cacheable prompt.** A `cache_control` block on a prefix shorter than the model's floor is silently ignored: no error, no `cache_creation_input_tokens`, and full input price on every turn. Both `estimate_cost` and `session_estimate` emit a warning when your prefix falls below the floor for the selected model.

**Opus 5.5 note.** Opus 5.5 (released 2026-09-22) costs 20% less per token than Opus 5, but adaptive thinking is always on and reasoning tokens bill as output, so the ~500 output tokens per turn assumed above is a floor, not an average. Effort is the only control: it defaults to `medium` (Opus 5 defaulted to `high`), and `thinking: {type: "disabled"}` or a `budget_tokens` setting returns a 400. On legacy Opus 5 (`opus-5`), setting `thinking` to disabled is legal only at effort `high` or below; pairing it with `xhigh` or `max` returns a 400.

Fast Mode is 2x each model's own base rate -- $8/$40 on Opus 5.5 and $10/$50 on Opus 5 and Opus 4.8, the only models that support it -- and this server does not model it. The old 6x tier on Opus 4.7 / 4.6 no longer exists: Opus 4.7 errors on `speed: "fast"`, and Opus 4.6 silently runs at standard speed and standard rates.

## Development

The server is written in TypeScript and uses the `@modelcontextprotocol/sdk` package with `StdioServerTransport` for communication.

```
src/index.ts    -- server implementation (tools, pricing, handlers)
dist/           -- compiled output (generated by npm run build)
```

To rebuild after changes:

```bash
npm run build
```
