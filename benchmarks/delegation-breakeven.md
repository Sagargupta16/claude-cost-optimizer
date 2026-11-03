# Delegation Break-Even: Read on the Main Thread or in a Subagent

> **Evidence: computed, not measured.** Every dollar figure below comes from the formula on this page and the posted rates in [docs/pricing-data.md](../docs/pricing-data.md). It is a token-cost floor for one read, not cost per solved task: it ignores quality, retries and reasoning tokens. The overhead `O`, the delegation prompt `D` and the summary `S` are round illustrative values, not measurements of any setup; measure your own `O` with the [method below](#measure-your-own-overhead-o).

Claude needs to read `F` tokens: a large search result, a log, a file. Either the main conversation reads it, or a subagent reads it and hands back a summary. This page prices both paths the way Claude Code caches a conversation: the request that receives new content writes it to cache at the 5-minute rate (1.25x input), and every later request reads it at the cache-hit rate.

## The Formula

| Symbol | Meaning |
|--------|---------|
| `F` | Tokens the read returns |
| `T` | Main-thread requests after the read that carry its result (or the summary) in their prefix |
| `O` | The subagent's first-request prompt: its system prompt, tool definitions, CLAUDE.md files (unless the definition sets `omitClaudeMd`) and the delegation prompt |
| `D` | The delegation prompt the main thread writes as the Agent tool's input, billed as main-model output |
| `S` | The summary the subagent returns, billed as subagent output |
| `w`, `h`, `o` | 5-minute cache write, cache hit and output rate per 1M tokens, of the model that bills that request |

```
Read on the main thread:
  F x (w_main + T x h_main)

Delegate to a subagent:
  D x o_main + (D + S) x (w_main + T x h_main)     main thread: writes the prompt, then carries prompt and summary
+ O x w_sub                                        subagent request 1: writes its own prefix
+ O x h_sub + F x w_sub + S x o_sub                subagent request 2: reads that prefix, writes the result, writes the summary
```

Assumptions, each of which you can change in the formula:

- **One tool call reads `F` in both paths**, so the main thread sends the same number of requests either way and the cost of its existing context cancels out. A read spread over many calls makes the main-thread path dearer, because each call is another main-thread request that re-reads the whole prefix.
- **The subagent makes two requests**: one to call the tool, one to write the summary. Tool-call arguments other than `D` are left out.
- **Reasoning tokens are left out.** Opus 5.5 always thinks and Haiku 5.5 thinks by default; both bill reasoning as output, so add a subagent's reasoning to `S` and the main thread's extra reasoning to `D`.
- **Every request uses the 5-minute TTL**, the case on an API key. Subagents use five minutes on every plan; a subscription's main conversation writes at the 1-hour rate ($8.00 on Opus 5.5), which raises the main-thread path and the `(D + S)` term alike ([prompt caching](https://code.claude.com/docs/en/prompt-caching), read 2026-11-03).
- **Forks are left out.** A fork inherits the parent's system prompt, tools and history, so its first request reads the parent's cache instead of writing a fresh `O`.

**Haiku 5.5's 100K line.** Each request is priced on its own prompt length, cache reads and writes included. Request 2's prompt is `O + F`; when that is over 100,000 tokens, the whole request pays $0.625 write, $0.05 hit and $2.50 output instead of $0.125, $0.01 and $0.50.

**Rates** ([docs/pricing-data.md](../docs/pricing-data.md), the same values as `MODELS` in [tools/claude-rate/rate.py](../tools/claude-rate/rate.py)):

| Model | `w` (5-minute write) | `h` (cache hit) | `o` (output) |
|-------|:--------------------:|:---------------:|:------------:|
| Opus 5.5 | $5.00 ($4 base x 1.25) | $0.20 | $20.00 |
| Haiku 5.5, prompt <= 100K | $0.125 | $0.01 | $0.50 |
| Haiku 5.5, prompt > 100K | $0.625 | $0.05 | $2.50 |

Two subagents are priced: one pinned to Haiku 5.5 (`model: haiku` on the Anthropic API), and one that inherits the main conversation's Opus 5.5, which is what the built-in Explore subagent does when the main conversation runs on Opus 5.5 ([Guide 07](../guides/07-mcp-agent-costs.md#model-selection-for-subagents)).

## Results

Main thread on Opus 5.5. `D` = 300 tokens, `S` = 500 tokens, `O` = 20,000 or 60,000 tokens (illustrative). The cheapest path in each row is in bold.

| `F` | `T` | Read on main | Haiku 5.5 sub, `O` 20K | Haiku 5.5 sub, `O` 60K | Opus 5.5 sub, `O` 20K | Opus 5.5 sub, `O` 60K |
|----:|----:|:------------:|:----------------------:|:----------------------:|:---------------------:|:---------------------:|
| 2,000 | 5 | **$0.0120** | $0.0140 | $0.0194 | $0.1348 | $0.3428 |
| 2,000 | 20 | $0.0180 | **$0.0164** | $0.0218 | $0.1372 | $0.3452 |
| 2,000 | 50 | $0.0300 | **$0.0212** | $0.0266 | $0.1420 | $0.3500 |
| 10,000 | 5 | $0.0600 | **$0.0150** | $0.0204 | $0.1748 | $0.3828 |
| 10,000 | 20 | $0.0900 | **$0.0174** | $0.0228 | $0.1772 | $0.3852 |
| 10,000 | 50 | $0.1500 | **$0.0222** | $0.0276 | $0.1820 | $0.3900 |
| 50,000 | 5 | $0.3000 | **$0.0200** | $0.0538 (over 100K) | $0.3748 | $0.5828 |
| 50,000 | 20 | $0.4500 | **$0.0224** | $0.0562 (over 100K) | $0.3772 | $0.5852 |
| 50,000 | 50 | $0.7500 | **$0.0272** | $0.0610 (over 100K) | $0.3820 | $0.5900 |

"Over 100K": request 2's prompt is 60,000 + 50,000 = 110,000 tokens, so it bills at Haiku 5.5's upper tier.

**Break-even read size**: the smallest `F` (searched in steps of 100 tokens) at which delegating costs less than reading on the main thread.

| Subagent | `O` | `T` = 5 | `T` = 20 | `T` = 50 |
|----------|----:|--------:|---------:|---------:|
| Haiku 5.5 | 20,000 | 2,400 | 1,900 | 1,500 |
| Haiku 5.5 | 60,000 | 3,300 | 2,500 | 1,800 |
| Opus 5.5 (inherited) | 20,000 | 124,900 | 31,900 | 13,200 |
| Opus 5.5 (inherited) | 60,000 | 332,900 | 83,900 | 34,100 |

What the tables say, on these assumptions:

- **A Haiku 5.5 subagent repays its overhead on reads of a few thousand tokens.** Its whole prefix costs about a fortieth of Opus 5.5's per token, so the main thread's write of `D + S` dominates its cost.
- **A subagent that inherits Opus 5.5 rarely pays on tokens alone.** It writes `O` at the same $5.00 the main thread would pay for `F`, so it wins only when `F` is large and many main-thread requests follow. That is the Explore default; pin a cheaper model to change it.
- **Crossing the 100K line costs Haiku 5.5 more than it saves.** At `O` = 60,000 and `F` = 50,000 the subagent's own share is $0.0430 instead of $0.0146 below the line, 2.9x (computed: 0.0430 / 0.0146). Keep `O + F` under 100,000 tokens, or let `omitClaudeMd` and a smaller tool set shrink `O`.

## Worked Example

`O` = 20,000, `F` = 10,000, `T` = 20, Haiku 5.5 subagent:

```
Read on main:   10,000 x ($5.00 + 20 x $0.20) / 1M                       = $0.0900
Main side:      (300 x $20 + 800 x ($5.00 + 20 x $0.20)) / 1M
                = (6,000 + 7,200) / 1M                                    = $0.0132
Subagent:       (20,000 x $0.125 + 20,000 x $0.01 + 10,000 x $0.125 + 500 x $0.50) / 1M
                = (2,500 + 200 + 1,250 + 250) / 1M                       = $0.0042
Delegated:      $0.0132 + $0.0042                                         = $0.0174
```

## Measure Your Own Overhead (O)

`O` depends on your CLAUDE.md files, MCP servers, the subagent's tool list and its delegation prompt, so no single figure fits every setup. To read your own:

1. Find subagent transcripts under `~/.claude/projects/<project folder>/<session id>/subagents/`: each `agent-<id>.jsonl` is one subagent run (some sit one level deeper, under `subagents/workflows/`), and its `agent-<id>.meta.json` names the `agentType`.
2. In each transcript, take the first assistant record's `message.usage` and add `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. That is the subagent's first-request prompt, `O`.
3. Group by `agentType` and model, and skip forks, whose first request reads the parent's prefix.

This reads one machine's history only. `claude-rate --usage` (claude-rate 0.4.0 or later) shows how much of your list-price spend went to subagents, by agent type, which tells you whether the decision matters for you at all.

## Quality Caveat

A cheaper read is not a cheaper task if the subagent's answer needs a retry. Anthropic measured Haiku 5.5 subagents added to Opus 5.5 at `medium` effort, with a short delegation prompt, on an internal coding benchmark on Claude Managed Agents: cost per attempt fell 32% and the pass rate about 4 percentage points (95% interval 1.3 to 7.1), about what a mix of `low` and `medium` effort without subagents gives at that cost. Its advice for Haiku 5.5 subagents on coding tasks is to compare them with lower effort first ([cost-optimization guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence), read 2026-11-03). See [Guide 07](../guides/07-mcp-agent-costs.md#when-subagents-cost-more) for when delegation fits at all.
