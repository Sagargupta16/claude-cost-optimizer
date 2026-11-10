# claude-rate

> **Rate your Claude / AI setup -- locally, in 5 seconds, no signup.**

`claude-rate` scans your project directory and grades your Claude Code (and adjacent AI tooling) configuration for cost-efficiency. Get a 0-100 score, an A+ to F letter grade, a per-category breakdown, copy-pasteable fix suggestions, and an estimated monthly spend on every active model tier.

Unlike the [web analyzer](https://sagargupta.online/claude-cost-optimizer/analyzer/) (which only sees what's on GitHub), `claude-rate` runs on the actual filesystem and inspects things the web tool can't:

- Real MCP server count from `.mcp.json`
- Hook configuration in `.claude/settings.json`
- `Read(...)` deny rules in a gitignored `.claude/settings.local.json`, checked against the lock files actually on disk
- Accidentally-committed secrets in `CLAUDE.md`, `.mcp.json`, or settings
- Untracked `.env` / credential files missing from `.gitignore`
- cost-mode skill installation, custom slash commands, subagents
- With `--user` and `--usage`: your user-level setup in `~/.claude` and your measured usage from local transcripts ([below](#your-whole-setup-and-your-real-usage)), with reports on cache breaks and where the spend went ([usage reports](#usage-reports))
- With `--statusline`, `--transcript` and `--hook cache-guard`: live views inside a running session, for Claude Code's status line and hooks ([live modes](#live-modes-inside-a-session))

## Quick start

### One command, nothing installed

The only requirement is Python 3.10 or later (preinstalled on most Linux distributions; on macOS it comes with the Xcode Command Line Tools). The script is streamed straight into Python, so nothing is installed or written to disk. Run it in your project directory:

Windows PowerShell:

```powershell
irm https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/rate.py | python - . --user --usage --fix
```

macOS, Linux, Git Bash, or Windows cmd (on Windows, `python` instead of `python3`):

```bash
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/rate.py | python3 - . --user --usage --fix
```

Drop `--user --usage` to grade only the project.

### Persistent install (macOS, Linux, Git Bash)

```bash
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh | sh -s -- --install
# then anywhere:
claude-rate .
```

### From PyPI or npm (after the first release)

`pyproject.toml` packages `rate.py` as the `claude_rate` module with a `claude-rate` console script, and `package.json` wraps it for npx. Neither is published yet ([Releasing](../README.md#releasing)); once they are:

```bash
uvx claude-rate . --fix          # or: pipx run claude-rate . --fix
npx @sagargupta16/claude-rate . --fix
```

### Direct Python (cloned repo)

```bash
python tools/claude-rate/rate.py /path/to/project
```

No external dependencies. Pure Python 3.10+ stdlib.

Tests: `python -m unittest discover -s tools/claude-rate/tests -v` from the repo root, six files. `test_rate.py` pins the per-request billing, the Haiku 5.5 100,000-token boundary, the session estimate, model-id matching and the `--user` checks to values worked out by hand from the posted rates. `test_a1.py`, `test_a2.py` and `test_a3.py` run the `--usage` reports, the `--by`, `--what-if`, pace, plan and history reports, and `--tools` on synthetic transcripts. `test_b1.py` covers the project findings, the detected Read deny block and `--max-context-tokens`, and `test_c.py` the live modes.

## Your whole setup and your real usage

The project grade only sees one directory. Two flags grade the rest, all from local files:

```bash
claude-rate . --user --usage --fix
# no install (PowerShell: irm https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/rate.py | python - . --user --usage --fix):
curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/rate.py | python3 - . --user --usage --fix
```

- **`--user`** grades `~/.claude` (or `$CLAUDE_CONFIG_DIR`), which loads in every project: always-loaded instructions (`CLAUDE.md` plus `rules/` files without `paths:` frontmatter, which load at launch), the skill listing, user and local MCP servers from `~/.claude.json`, cost controls in user settings, and user-level `Read(...)` deny rules. It reads counts and setting names only, never values. From claude-rate 0.4.0:
  - **Skill listing.** Every skill's description is in context each turn unless it sets `disable-model-invocation: true`. The whole listing is capped at `skillListingBudgetFraction` (default 0.01) of the context window of the model your settings pin, Opus 5.5's 1,000,000 tokens when none is pinned; over the cap Claude Code keeps every name and drops the descriptions of the least-used skills ([settings reference](https://code.claude.com/docs/en/settings-reference), read 2026-11-03). `skillOverrides` (`off`, `user-invocable-only`, `name-only`) and `skillListingMaxDescChars` are honoured, project settings over user settings.
  - **Subagent descriptions** from `~/.claude/agents`, the project's `.claude/agents` and enabled plugins are counted on the same row, and flagged above 15,000 tokens, where Claude Code warns at startup ([subagents](https://code.claude.com/docs/en/sub-agents), read 2026-11-03).
  - **Subagent findings** for `~/.claude/agents` (the project grade checks `.claude/agents` the same way): no `model` (it runs on the main conversation's model unless `CLAUDE_CODE_SUBAGENT_MODEL` is set), `model: haiku` on Bedrock, Google Cloud, Foundry or Claude Platform on AWS without `ANTHROPIC_DEFAULT_HAIKU_MODEL` (there the alias is Haiku 4.5 at $1/$5, not Haiku 5.5), a legacy model id with its current successor, and, as info, an agent that sets neither `tools` nor `disallowedTools` and so inherits every tool.
  - **Startup tokens**: one line estimating (chars / 4) what loads at the start of every session from user-level files, instructions in full plus the listing entries, against the context window, with the five largest items.
- **`--usage [DAYS]`** reads your Claude Code transcripts (`~/.claude/projects/**/*.jsonl`, last 30 days by default) and grades what actually happened: the share of prompt tokens read from cache, median and p90 prompt size, and the share of list-price spend on legacy models. It prices each request the way Anthropic bills it (5-minute and 1-hour cache writes, the Haiku 5.5 prompt-length tier, Fast Mode at 2x), then prints the [usage reports](#usage-reports) below the grade. The dollar total is list price: on a subscription plan you pay the plan price, so use it to compare models and habits.
  - **What counts, from claude-rate 0.4.0.** Each request is windowed by its own record timestamp (a file written today can hold requests from weeks ago), a session is one distinct `sessionId`, and each message id is counted once, at its final usage snapshot, across main and subagent files. 0.3.0 windowed by file modification time, kept the first snapshot and counted transcript files as sessions, so the same history can give different totals and session counts. A model id is matched whole: a release the rate table does not carry yet is counted but not priced, and listed by id, instead of taking an older model's rate.
  - **Privacy.** It reads token counts, model names, timestamps, session, agent and request ids, project folder names from paths, the `isSidechain` flag, the `speed`, `effort`, `version`, `cwd`, `gitBranch`, `entrypoint` and attribution-tag fields of each record, `diagnostics.cache_miss_reason` when Claude Code records one, compaction records, `agentType` from each subagent's `agent-<id>.meta.json`, and the kind and first 300 characters of Claude Code's own API error messages, which name the limit you hit; never message content. With `--tools` it also reads tool names, inputs and result text locally and prints aggregates only, labelled by a command's first word (and subcommand), a file's last two path segments or a URL's host; no result text or command argument is printed. `--state` writes only the file you name, and `--history` writes only aggregate snapshots in the folder you name.

Example against a synthetic `~/.claude` (8 skills, 3 subagents, 5 user MCP servers, Bedrock on in settings, and synthetic transcripts: 4 sessions in 6 files), with the project grade trimmed off:

```
Your Claude Code setup (user scope)
------------------------------------------------------------
  Global instructions      [####################]  25/25  ~1,819 tokens in 2 always-loaded file(s)
  Skill listing            [####################]  20/20  8 skill(s) in ~/.claude/skills and 0 enabled plugin(s), ~591 listing tokens; cap ~10,000 tokens = 1% of 1,000,000 (Sonnet 5.5, the pinned model); 3 subagent(s), ~19 description tokens
  MCP servers (user)       [###############-----]  15/20  5 user, 0 local (this project)
  Settings (user)          [####################]  20/20  model=opus; cost controls: claude-opus-5-5 effortLevel=medium
    ! 1 subagent(s) name no `model` and run on the main conversation's model: helper.md. Add `model: haiku` to read-only search roles and a named model to the rest.
    ! 1 subagent(s) use `model: haiku`: scout.md. On Bedrock that alias is Haiku 4.5 ($1/$5 per 1M), not Haiku 5.5 ($0.1/$0.5 up to 100K prompt tokens); set ANTHROPIC_DEFAULT_HAIKU_MODEL to a Haiku 5.5 id.
    ! 1 subagent(s) pin a legacy model: old-reviewer.md (claude-opus-4-7 $5/$25 -> Opus 5.5 $4/$20). Unless an eval needs the old one, pin the current model of that family.
    ! info: 1 subagent(s) set neither `tools` nor `disallowedTools`, so each inherits every tool available to subagents: helper.md.
  Read deny rules (user)   [--------------------]   0/15  0 Read(...) rule(s) in user permissions.deny
  Score: 80/100  (B)
  Startup tokens (estimate, chars/4): ~2,429 of a 1,000,000-token window (Sonnet 5.5, the pinned model), 0.2%. Largest: CLAUDE.md ~1,294 (always-on, pays in full), rules/style.md ~525 (always-on, pays in full), db-migrate ~139 (listing entry), release ~119 (listing entry), review ~119 (listing entry). The 4.7+ tokenizer makes about 30% more tokens for the same text.
  2 suggestion(s) -- add --fix to see them.

Your measured usage (last 30 days)
------------------------------------------------------------
  Cache hit rate           [--------------------]   0/50  29.6% of prompt tokens were cache reads
  Context size             [####################]  30/30  median prompt 25,000 tokens, p90 100,050; 12% of requests over 100K
  Model mix                [#################---]  17/20  16% of list-price spend on legacy models
    ! 1 request(s) ran in Fast Mode, billed at 2x the model's base rate.
  Score: 47/100  (D)
  5 suggestion(s) -- add --fix to see them.
  19 requests in 4 session(s) (6 transcript files); list-price total $1.68, 5% of it output
    Opus 5.5             6 requests  $      1.15   68%
    Opus 4.7             4 requests  $      0.26   16%
    Sonnet 5.5           4 requests  $      0.20   12%
    Haiku 5.5            3 requests  $      0.07    4%
  List price = what these tokens cost on the API. On a Pro, Max or Ultra plan you pay the plan price; use this to compare models and habits, not as a bill.
  2 request(s) on models without a price row were counted but not priced: claude-mystery-9 (2).
  Transcripts on disk start 2026-11-01, so this covers less than 30 days (Claude Code deletes transcripts after cleanupPeriodDays, 30 by default).
  By token class: 5m write 93.5%, output 4.7%, cache read 1.0%, 1h write 0.7%, fresh input 0.0%
    Caching saved $0.28 vs uncached input, write premium $0.32, net -$0.04 (saved = reads x (input - read rate); premium = writes x (write rate - input))
    Output is 4.7% of list spend: halving billed output saves 2.4% at most (thinking is billed inside output_tokens)
  Main thread $1.61 (96%), subagents $0.07 (4%); agent type known for 1 of 2 subagent files
    Explore                        $0.07   4%  hit 50%  Haiku 5.5 100%
    unknown                        $0.00   0%  hit 0%  Haiku 5.5 100%
  Top sessions (full ids in --json; resume with claude --resume <id> from that project folder)
    S1  2026-11-01  proj-a                               $0.97  57%  writes 92%
    S2  2026-11-01  proj-b                               $0.46  27%  writes 99%
    S3  2026-11-01  proj-b                               $0.26  15%  writes 96%
  cost-mode break-even (hypothetical): if its SKILL.md (4,000 chars) sat in every main-thread request, its $0.03 context cost needs a 34.3% cut of main-thread output ($0.08) (chars / 4 x tokenizer factor at the read rate per request + one 5m write per session; brevity only, routing and cache advice not counted)
  Cache breaks: 9 re-wrote 202,000 tokens, $0.97 above warm reads (57.9% of list spend)
    fast mode toggle             main           1        $0.29  17.1%
    idle 5-60 min                main           1        $0.25  14.8%
    compaction                   main           1        $0.10   5.7%
    Costliest sessions: S1 $0.51, S2 $0.29, S3 $0.17
    break = cached prefix >= 4,096 tokens, read back < 50%, >= 2,000 re-written; extra = re-written x (write rate - read rate); gaps include response time
  1h TTL what-if, main: 1% of writes already 1h; saves $0.25, costs $0.75, net -$0.50 per 30 days at list price; idle rebuilds 17.4% of 5m writes vs 38.5% break-even on Opus 5.5: skip
  1h TTL what-if, subagents: 0% of writes already 1h; saves $0.00, costs $0.04, net -$0.04 per 30 days at list price; idle rebuilds 0.0% of 5m writes vs 39.5% break-even on Haiku 5.5: skip
    net = idle 5-60 min rebuilds x (write rate - read rate) - (5m write tokens - those rebuilds) x (1h write rate - 5m write rate); break-even rebuild share = (1h - 5m) / (1h - read)
  Compactions: 1 auto; the first request after one averaged 20,005 prompt tokens (triggers as recorded; manual can include idle compactions)
  Haiku 5.5 over 100,000 prompt tokens: 2 of 3 requests paid $0.06 above the base-tier rates (long-tier price - the same tokens at base rates)
  Limit hits: 3 (2026-W44 3; other 429 1, spend limit 1, weekly 1) (rate_limit and billing_error messages; transcripts past cleanupPeriodDays are gone)
  Pace: $0.77 per active hour over 2.2 h (gaps under 60 min between requests, all sessions merged); $0.86 per calendar day over 1.97 days
  Month to date (2026-11): $1.68 in 2.38 days; the window or the transcripts on disk begin after the 1st, so month to date is incomplete
  Startup floor (prompt tokens of each session's first main-thread request):
    unknown                   4 sessions  min     1,000  p10     1,000  median    30,000
  The first request in the window of each main session: it carries the first message, a resumed session carries its restored context, and a session begun before the window counts from its first request inside it, so min and p10 are the floor. The floor minus what --user counts is built-in prompt and tools, MCP tool names and instructions, project CLAUDE.md and skills, auto memory, git status and the harness.
```

The skill listing above reads Sonnet 5.5's window because the project's own settings pin `claude-sonnet-5-5`; project settings win over user settings.

| Scope | Category | Max | Full marks when |
|-------|----------|----:|-----------------|
| `--user` | Global instructions | 25 | Always-loaded user instructions stay small (they load in every session of every project) |
| `--user` | Skill listing | 20 | The skill and plugin descriptions in context each turn stay small (1,000 listing tokens or fewer, counted up to the cap) |
| `--user` | MCP servers (user) | 20 | Few servers at user and local scope |
| `--user` | Settings (user) | 20 | A default model is pinned and a cost control Claude Code reads is set: `/effort` low or medium per model under `modelSettings`, `maxEffortLevel`, `fastMode: false`, `fastModePerSessionOptIn: true`, `availableModels` with `enforceAvailableModels`, `autoCompactEnabled: true`, or, from claude-rate 0.4.0, an auto-compact window of at least 100,000 and under the 1,000,000 default (`autoCompactWindow`, per model under `modelSettings`, or `CLAUDE_CODE_AUTO_COMPACT_WINDOW` in `env`), `MAX_MCP_OUTPUT_TOKENS` under its 25,000 default in `env`, or `CLAUDE_CODE_SUBAGENT_MODEL` on Haiku or Sonnet with `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` when it differs from the main model's family. A top-level `effortLevel` in user settings does not count: Opus 5.5 and later ignore it there. `bashOutputMaxChars` does not count: the settings reference documents it as a way to raise the Bash limit |
| `--user` | Read deny rules (user) | 15 | Deny rules for `.env`, dependencies and build output apply in every project |
| `--usage` | Cache hit rate | 50 | 95% or more of prompt tokens are cache reads |
| `--usage` | Context size | 30 | Median prompt under 50,000 tokens |
| `--usage` | Model mix | 20 | No list-price spend on legacy models |

## Usage reports

Below the `--usage` grade (claude-rate 0.4.0 or later), claude-rate prints where the list-price spend went, from the same pass over the transcripts. With `--json` each block sits under `usage.facts`:

| Block | What it shows | `usage.facts` key |
|-------|---------------|-------------------|
| Model rows, unpriced ids | Requests and list-price spend per model; requests on a model id the rate table lacks are counted and listed by id | `by_model`, `unpriced` |
| By token class | Spend in fresh input, cache reads, 5-minute and 1-hour writes and output, and the caching net: reads x (input - read rate) saved, minus writes x (write rate - input) | `by_class`, `caching_net` |
| Output share ceiling | The most that halving billed output could save; thinking is billed inside `output_tokens` | `ceilings` |
| Main thread vs subagents | Main-thread and subagent spend, subagents by `agentType` | `by_agent_type` |
| Top sessions | Up to five costliest sessions, with the id for `claude --resume` (full ids in `--json`) | `top_sessions` |
| cost-mode break-even | Only when a cost-mode `SKILL.md` is installed (this project, `~/.claude/skills` or an enabled plugin): the cut of main-thread output its own context cost needs. A hypothetical that counts brevity only | `cost_mode_break_even` |
| Cache breaks | Requests that re-wrote a cached prefix instead of reading it, by cause (a reason Claude Code recorded, compaction, model switch, fast mode toggle, idle 5-60 min, idle 1-4 h, idle over 4 h, effort change, version change, unknown) and scope, with the extra list price over warm reads; for idle breaks, model switches and fast mode toggles `--fix` adds the fix with a verdict: do at 5% of list spend or more, not yet at 1% to 5% | `cache_breaks` |
| 1h TTL what-if | Per scope (main, subagents): what the 1-hour cache TTL would save on idle rebuilds against what its dearer writes cost. Break-even rebuild share = (1h write - 5m write) / (1h write - cache read), so (8.00 - 5.00) / (8.00 - 0.20) = 38.5% on Opus 5.5 (computed from the posted rates) | `ttl_what_if` |
| Compactions | Auto and manual compactions, and the prompt size of the first request after one | `compactions` |
| Haiku 5.5 over 100K | Requests over the 100,000-token price line and what the long tier added | `haiku_long_prompt` |
| Limit hits | Claude Code's own `rate_limit` and `billing_error` messages by ISO week and kind (session, weekly, model-specific, spend limit, other) | `limit_hits` |
| Pace | List price per active hour (gaps under 60 minutes) and per calendar day, and month to date, projected once three days of the month have spend | `pace` |
| Startup floor | Prompt tokens of each session's first main-thread request, by entrypoint: the floor every session starts from | `startup_floor` |

### Report flags

Each adds to `--usage`:

| Flag | What it adds | `usage.facts` key |
|------|--------------|-------------------|
| `--by KEYS` | List-price spend grouped by any of `project`, `branch`, `session`, `day`, `week`, `version`, `skill`, `mcp`, `plugin`, `agent` (a comma list); every view's rows sum to the total. `session` rolls subagent requests into the session that started them, with active minutes (gaps under 5 minutes), output share and p90 prompt. `project` folds worktree folders into their repo. `skill`, `mcp`, `plugin` and `agent` group by the attribution tags Claude Code writes on the requests made while one was active, whole cached prefix included, so a row is not what that skill or server added | `by.sessions`, `by.projects`, `by.branches`, `by.days`, `by.weeks`, `by.versions`, `by.skills`, `by.mcp_servers`, `by.plugins`, `by.agents` |
| `--what-if MODEL[,MODEL]` | Your recorded tokens repriced on other models: token counts are scaled by the tokenizer ratio (target / source), while output length, thinking and the cache hit pattern stay as recorded. Modeled, quality not tested | `what_if` |
| `--scope all\|main\|subagents` | Which requests the `--what-if` table covers (default `all`); the grade always uses every request | `what_if` |
| `--budget USD` | The date this month's list-price spend crosses USD at the current pace | `pace.budget` |
| `--plan pro\|max\|ultra` | List-price spend per 30 days divided by the plan's monthly price ($20, $100 or $200). Above 1 the plan costs less than these tokens at list price; it says nothing about fitting the plan's usage limits | `plan_fit` |
| `--history DIR` | Saves an aggregates-only snapshot in DIR and compares it with the newest earlier one | `history` |
| `--tools` | The [tool-output audit](#tool-output-audit) | `tool_output` |

On synthetic transcripts (3 sessions, 6 requests, one of them on a model id the table does not carry), trimmed to the blocks these flags add:

```bash
claude-rate . --usage --by session,project,day --what-if sonnet,haiku --budget 50 --plan max
```

```
  Pace: $1.37 per active hour over 0.1 h (gaps under 60 min between requests, all sessions merged); $0.03 per calendar day over 4.88 days
  Month to date (2026-11): $0.11 in 2.38 days; a projection needs spend on 3 or more days this month
  Budget $50.00 for 2026-11: a projection needs spend on 3 or more days this month
  Plan fit (Max, $100/month): $0.99 list price per 30 days / $100 = 0.01. Above 1, the plan costs less than these tokens at list price; it says nothing about fitting the plan's usage limits.
  ratio = list-price spend x 30 / days covered / plan price per month, over 4.88 days. Claude Code transcripts on this machine only. The plan's usage pool is shared with Claude and Cowork too, and API, Bedrock or Google Cloud users have no plan.
  What-if repricing (all requests; modeled from your recorded tokens, quality not tested):
    scope            actual    Sonnet 5.5     Haiku 5.5
    main              $0.12         $0.08         $0.00
    subagents         $0.04         $0.02         $0.01
    all               $0.16         $0.10         $0.01
    general-purpose subagents would cost $0.02 on Sonnet 5.5 or $0.01 on Haiku 5.5 instead of $0.04; built-in: set CLAUDE_CODE_SUBAGENT_MODEL plus CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1, or define a same-named agent with model:
  Modeled from your own recorded tokens; quality not tested, and a cheaper model that needs retries or more turns raises the cost per completed task. Each request keeps its recorded text: token counts are scaled by tokenizer overhead (target / source), while output length, thinking and the cache hit pattern stay as recorded, though thinking and the minimum cacheable prompt differ by model. A request whose scaled prompt exceeds the target's context window is not priced.
  By session (subagents rolled into their session; active = gaps under 5 min summed):
    s1  code/alpha               2026-11-02     2 min       $0.11   69%  out 41%  p90 61,100
    s3  code/beta                2026-10-29     0 min       $0.04   24%  out 8%  p90 15,000
    s2  code/alpha               2026-10-31     0 min       $0.01    7%  out 33%  p90 2,000
  By project:
    code/alpha                                4 req        $0.12   76%  hit 97%
    code/beta                                 2 req        $0.04   24%  hit 0%
  By day (local time): mean $0.03/day over 6 days; outliers are marked on 14+ day windows only. Costliest:
    2026-11-02          3 req        $0.11   69%
    2026-10-29          2 req        $0.04   24%
    2026-10-31          1 req        $0.01    7%
```

### Live spend in a terminal

`--burn [MINUTES]` skips the project grade and prints the list-price spend of the last MINUTES (default 60) from local transcripts, windowed by each request's own time, per model and with the costliest session. `--watch SECONDS` (15 or more) redraws it until Ctrl+C. On the same synthetic transcripts:

```
$ claude-rate --burn 10080
claude-rate --burn last 10080 min, list price from local transcripts
  $0.16 in 10080 min = $0.00/hour; 6 requests; cache hit 89.6%
    Opus 5.5             3 requests       $0.08
    Sonnet 4.6           1 requests       $0.04
    Sonnet 5.5           1 requests       $0.04
    unpriced             1 requests       $0.00
  Costliest session: s1 $0.11
  List price = API rates for these tokens; on a plan you pay the plan price.
```

### Tool-output audit

`--usage --tools` is opt-in because it reads more than token counts: tool names, inputs and result text, locally (see the privacy note above). It estimates how much each tool's results add to context (characters / 4 x the model's tokenizer factor; images by their pixel size) and an upper-bound carry cost: one cache write of the result, then a cache read on every later request until the next compaction, capped at what the file was billed for cache reads and writes. It also counts identical re-reads, whole-file Reads of files over 500 lines, failures, empty searches, and what a lower `bashOutputMaxChars` would move out of context. On a synthetic transcript:

```
  Tool output (--tools: tokens are estimates from result text; reads tool names, inputs and result text locally, prints aggregates only)
    18 results, ~19K tokens; carry cost <= $0.10 (upper bound, cache-aware)
    From 1 main and 1 subagent transcript file(s), each its own chain; carry resets at every compaction and is capped at each file's billed cache reads and writes (0 file(s) hit the cap).
    By tool (results, ~tokens, share of all result tokens, carry)
      Bash                                                 8  ~   12K tok   65%  carry <= $0.06
      Read                                                 5  ~ 5,196 tok   28%  carry <= $0.02
      mcp__srv                                             2  ~ 1,300 tok    7%  carry <= $0.01
      Grep                                                 1  ~     5 tok    0%  carry <= $0.00
      Glob                                                 1  ~     5 tok    0%  carry <= $0.00
    Top Bash commands
      pytest                                               1  ~ 6,500 tok   35%  carry <= $0.03
      cat                                                  1  ~ 3,900 tok   21%  carry <= $0.02
      git diff                                             1  ~ 1,300 tok    7%  carry <= $0.01
      ls                                                   1  ~   390 tok    2%  carry <= $0.00
      npm run                                              3  ~    39 tok    0%  carry <= $0.00
    Identical re-reads: 2 of 4 reads (50.0%) repeated an earlier read of the same range with the same text and no edit between
      1 in one context, 1 after a compaction; ~1,950 tokens, carry <= $0.01
    Whole-file Reads of files over 500 lines: 4 results, ~3,900 tokens, carry <= $0.02
    If bashOutputMaxChars were lower, a result over it would arrive as a file path plus a 2,000-character preview (upper bound: assumes the file is never read):
      10,000 chars: 2 of 5 Bash results over, ~9,100 tokens (75.3% of Bash result tokens), carry <= $0.05
      15,000 chars: 1 of 5 Bash results over, ~5,850 tokens (48.4% of Bash result tokens), carry <= $0.03
    Failures: 3 results (16.7% of all)
      command not found       3  carry <= $0.00 + retry output <= $0.00
      1 run(s) of 3+ identical failing calls in a row (3 calls)
    Empty searches: 2 of 2 (100.0%): Glob 1 of 1, Grep 1 of 1
  7 tool-output suggestion(s) -- add --fix to see them.
```

## Live modes (inside a session)

Three modes run inside a live Claude Code session (claude-rate 0.4.0 or later). Each returns before the project scan and is written never to raise, because a status line command that exits non-zero goes blank and a hook's stdout must be one JSON object; a hook prints that object or nothing. Every dollar is a list-price estimate from claude-rate's rate table; on a Pro, Max or Ultra plan it is API-equivalent value, not your bill.

**`--statusline`** reads Claude Code's statusLine JSON on stdin and prints at most two rows. Row 1: model, effort, fast tag, context fill, Claude Code's own session cost estimate (`cost.total_cost_usd`), then the 5-hour and 7-day limit windows: used %, pace against an even burn (`+40` is 40 points ahead), the run-out time when it comes before the reset, and the reset countdown. Row 2, once the payload has `prompt_cache` (Claude Code v2.1.251 or later): warm or cold, the countdown to cold, `if cold +$X` (the list price of re-writing the cached prompt instead of reading it: tokens x (write rate - cache read rate)), hit ratio and misses with the last cause. Setup, install forms and refresh timing: [`templates/settings/statusline.json`](../../templates/settings/statusline.json). With the [statusline docs](https://code.claude.com/docs/en/statusline) sample payload (45,000 tokens on Opus 5.5 at the 1-hour TTL, so 45,000 x ($8.00 - $0.20) / 1M = $0.35) plus synthetic 5-hour and 7-day windows, and `NO_COLOR=1`:

```
Opus high | ctx 8% | $0.01 est | 5h 80% (+40, out 29m) resets 3h00m | 7d 41% (-2) resets 4d0h
cache warm (1h), cold in 42m | if cold +$0.35 | hit 91% | misses 2 (last: tools_changed)
```

**`--transcript PATH [--state FILE]`** prices one session transcript plus its subagent transcripts at list price, each message id once, and prints JSON: the session total and its split by model, the current prompt's turn and today's total. With `--state FILE` it keeps byte offsets, totals and seen message ids in FILE so each call reads only the lines added since, and sessions that share FILE share one day total. [`hooks/budget-tracker.sh`](../../hooks/budget-tracker.sh) (the `BUDGET_SESSION_USD`, `BUDGET_DAY_USD` and `BUDGET_TURN_USD` caps) and [`hooks/session-summary.sh`](../../hooks/session-summary.sh) call it. On a synthetic session, piped through `python -m json.tool`:

```
$ claude-rate --transcript .claude/projects/proj-a/S1.jsonl --state state.json | python -m json.tool
{
    "transcript": ".claude/projects/proj-a/S1.jsonl",
    "session_id": "S1",
    "basis": "list-price estimate",
    "found": true,
    "files": 3,
    "dollars": 0.9663,
    "requests": 11,
    "unpriced": 0,
    "prompts": 0,
    "first": "2026-11-01T10:00:00.000Z",
    "last": "2026-11-01T10:51:00.000Z",
    "by_model": {
        "Opus 5.5": 0.6961,
        "Sonnet 5.5": 0.1982,
        "Haiku 5.5": 0.072
    },
    "turn": {
        "prompt_id": null,
        "dollars": 0.0
    },
    "day": {
        "date": "2026-11-03",
        "dollars": 0.0,
        "covers": "every transcript this state file read in the last 3 days"
    },
    "state": "saved"
}
```

**`--hook cache-guard`** runs as a Claude Code hook ([`hooks/cache-guard.sh`](../../hooks/cache-guard.sh), opt-in). On `PreModelSwitch` it compares Claude Code's own estimate of writing the prompt to the new model's cache with staying (a warm read, or a re-write once the cache is cold); for a cheaper target it adds how many requests like your last 10 the switch takes to pay back. On `SessionStart` with `resume` or `fork`, when the cache has likely expired and the context is at least `CACHE_GUARD_MIN_TOKENS` (default 50,000), it prices the re-write. It returns only a `systemMessage`, never a permission decision, and gives up after 3 seconds. With the payloads in `tests/test_c.py`:

```
$ claude-rate --hook cache-guard < switch.json
{"systemMessage": "[cache-guard] Switching Sonnet 5 to Opus 5 re-sends 182K tokens: ~$1.14 to write them to the new model's cache (Claude Code's list-price estimate). Staying would read the warm cache for ~$0.04, so the switch adds ~$1.10. Dollars are list price unless noted; on a Pro, Max or Ultra plan it is API-equivalent value, not your bill."}
$ claude-rate --hook cache-guard < resume.json
{"systemMessage": "[cache-guard] Resuming after 1h30m: the prompt cache has likely expired, so the first request re-writes 182K tokens, ~$1.14 (Claude Code's estimate). If you do not need the old context, /rename this session to find it later, then /clear or start a fresh session. List price; on a Pro, Max or Ultra plan it is API-equivalent value, not your bill."}
```

## Example output (project)

Against a synthetic project: a 250-line `CLAUDE.md` with two stale path references and one repeated line, a `.claudeignore`, six Read deny rules, a `package-lock.json`, git-ignored `node_modules/` and `dist/` folders, and a `.claude/settings.json` with `autoCompactWindow`, a dead env key and two broken hooks (the `Project:` path line is trimmed):

```
claude-rate -- Claude / AI setup audit
============================================================
Verified against Anthropic pricing as of: 2026-11-10

  CLAUDE.md                [##########----------]  10/20  250 lines primary (over the 200-line guidance); ~5,232 tokens total across 1 file(s)
    ! 250 lines -- over Anthropic's 200-line guidance for CLAUDE.md. Longer files consume more context and reduce adherence. Move workflow-specific instructions into skills or path-scoped .claude/rules/ so they load on demand.
    ! 2 path reference(s) in CLAUDE.md files point at nothing: CLAUDE.md:3 docs/setup.md; CLAUDE.md:3 src/old_module/main.py. Claude may try to open them and get an error.
    ! 1 line(s) repeat an earlier line in the always-loaded instruction files (~20 tokens in every session): CLAUDE.md:250 repeats CLAUDE.md:124 (near).
  File-read exclusions     [################----]  12/15  6 Read deny rule(s); lock files covered
    ! `.claudeignore` is not read by Claude Code -- its permissions docs say the file has no effect. Move its patterns into permissions.deny as Read(...) rules.
  .claude/settings.json    [####################]  15/15  found at .claude/settings.json; model=claude-sonnet-5-5, cost controls: autoCompactWindow=200000, permissions defined
    ! env CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION does nothing: it was removed in v2.1.224 and is now a no-op (code.claude.com/docs/en/env-vars, read 2026-11-03). CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS limits how many subagents run at once.
  MCP servers              [####################]  15/15  no MCP servers configured (lowest overhead)
  Hooks                    [############--------]   6/10  2 hook(s) configured
    ! 1 hook handler(s) never run: settings.json Stop[0]. Each handler must be an object with a "type" (such as "command") inside a matcher group's "hooks" array; a bare command string or a handler without a type does not run (hooks reference, read 2026-11-03).
    ! 1 hook handler(s) point at a script that does not exist: settings.json PreToolUse[0].hooks[0] (hooks/budget-tracker.sh). A mistyped path means the hook never runs (hooks reference, read 2026-11-03).
    ! 1 hook handler(s) use a relative script path: settings.json PreToolUse[0].hooks[0] (hooks/budget-tracker.sh). A hook runs in the session's current directory, so it fails once Claude cds into a subfolder.
  Security & hygiene       [##############------]   7/10  minor gaps
    ! No .gitignore at all -- secrets and build artifacts will be tracked.
  Optimizer tooling        [--------------------]   0/15  none of: cost-mode skill, custom commands, subagents, plugin metadata

Total: 65/100  (C)

Estimated monthly cost (30 turns/session, 3 sessions/day, 22 days; each turn reads the last one from cache)
  Fable 5.2      $ 1.72/session  ->  $ 113.80/month
  Fable 5.1      $ 2.16/session  ->  $ 142.25/month
  Fable 5        $ 3.05/session  ->  $ 201.47/month
  Opus 5.5       $ 0.98/session  ->  $  64.80/month
  Opus 5         $ 1.53/session  ->  $ 100.73/month
  Opus 4.8       $ 1.53/session  ->  $ 100.73/month
  Opus 4.7       $ 1.53/session  ->  $ 100.73/month
  Opus 4.6       $ 1.17/session  ->  $  77.49/month
  Opus 4.1       $ 3.52/session  ->  $ 232.46/month
  Sonnet 5.5     $ 0.49/session  ->  $  32.40/month
  Sonnet 5       $ 0.61/session  ->  $  40.29/month
  Sonnet 4.6     $ 0.70/session  ->  $  46.49/month
  Haiku 5.5      $ 0.03/session  ->  $   2.01/month
  Haiku 4.5      $ 0.23/session  ->  $  15.50/month

Badge URL:  https://img.shields.io/badge/Claude%20Cost%20Grade-C-yellow
Markdown:  ![Claude Cost Grade](https://img.shields.io/badge/Claude%20Cost%20Grade-C-yellow)

Run with --fix to see 13 copy-pasteable fix suggestion(s).
```

With `--fix`, the File-read exclusions entries print the `.claudeignore` patterns converted to rules you can paste, then the Read deny rules detected for this project that the existing rules do not cover. A folder is listed only when it exists within two levels of the root, git ignores it and it holds no tracked file, because a Read deny also blocks Edit and Write on that path; the `.env` rules and root lock files are always kept. With no Read rules at all, the same detected list prints as one `permissions.deny` block. The `node_modules` rule is missing below because `Read(./node_modules/**)` already covers it, and `package-lock.json` because `Read(./package-lock.json)` does:

```
  * [File-read exclusions] Merge its patterns into permissions.deny in .claude/settings.json, then delete .claudeignore:
    {
      "permissions": {
        "deny": [
          "Read(./node_modules/**)",
          "Read(*.min.js)",
          "Read(./docs/generated/x.md)"
        ]
      }
    }

  * [File-read exclusions] Add these Read deny rules detected for this project (a folder is listed only when git ignores it and it holds no tracked file, since a Read deny also blocks Edit and Write):
    "Read(./.env)"
    "Read(./.env.*)"
    "Read(dist/**)"
```

## What gets scored

| Category | Max | What's checked |
|----------|----:|----------------|
| **CLAUDE.md** | 20 | Primary file (root `CLAUDE.md`, else `.claude/CLAUDE.md`) line count: up to 100 lines 12, up to 200 10, up to 300 6, up to 500 3, more 1. Plus estimated tokens (chars / 4) across both files: up to 2,000 8, up to 4,000 6, up to 8,000 4, up to 16,000 2, more 0. CLAUDE.md loads in full at launch, so over 200 lines is flagged against Anthropic's 200-line guidance. From claude-rate 0.4.0, findings with no score change: path references in `CLAUDE.md`, `.claude/CLAUDE.md` and `CLAUDE.local.md` (links, backticked paths, `@imports`) that point at nothing, and lines repeated, exactly or 90% alike, across the always-loaded instruction files (those three plus `.claude/rules/` files without `paths:` frontmatter) |
| **File-read exclusions** | 15 | `Read(...)` rules in `permissions.deny` (`.claude/settings.json`, else `.claude/settings.local.json`): 10+ rules 13, 5-9 10, 1-4 6, none 0. +2 when every lock file at the root (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `Cargo.lock`, `uv.lock`) is covered by a rule containing its name, `*.lock` or `*lock*`. A `.claudeignore` scores nothing -- Claude Code does not read it -- and `--fix` converts its patterns to Read rules. `--fix` also prints the Read deny rules detected for the project ([above](#example-output-project)): `.env`, root lock files, git-ignored generated folders that hold no tracked file, and generated-file globs git tracks; with rules present, only the ones not yet covered |
| **.claude/settings.json** | 15 | Default model pinned (6); a cost control Claude Code reads (5): `effortLevel` low/medium, `maxEffortLevel`, `fastMode: false`, `fastModePerSessionOptIn: true`, `enforceAvailableModels` with `availableModels`, `autoCompactEnabled: true`, or, from claude-rate 0.4.0, an auto-compact window of at least 100,000 and under the 1,000,000 default (`autoCompactWindow`, per model under `modelSettings`, or `CLAUDE_CODE_AUTO_COMPACT_WINDOW` in `env`), `MAX_MCP_OUTPUT_TOKENS` under 25000 in `env`, or `CLAUDE_CODE_SUBAGENT_MODEL` on Haiku or Sonnet with `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` when it differs from the main model's family; permissions defined (4). `alwaysThinkingEnabled: false` is not counted: it has no effect on Opus 5.5, Sonnet 5.5, Haiku 5.5 or the Fable models, which always think ([settings reference](https://code.claude.com/docs/en/settings-reference#alwaysthinkingenabled), read 2026-11-01). `bashOutputMaxChars` is not counted: the settings reference documents it as a way to raise the Bash limit. Findings with no score change: `CLAUDE_CODE_MAX_SUBAGENTS_PER_SESSION` in `env` does nothing since v2.1.224 ([env vars](https://code.claude.com/docs/en/env-vars), read 2026-11-03), and a pinned Haiku 5.5 with no auto-compact window under 1,000,000 gets a note that a request over 100,000 prompt tokens pays $0.50/$2.50 on the whole request |
| **MCP servers** | 15 | Total count across `.mcp.json` and `settings.json`: none 15, 1-3 13, 4-5 10, 6-8 6, 9-12 3, more 0. With tool search on (the default) each server adds its tool names and server instructions to context; full tool schemas load up front only when tool search is off |
| **Hooks** | 10 | Hook entries in `.claude/settings.json`: 3 or more 10, 1-2 6, none 0, for budget tracking and cost logging. From claude-rate 0.4.0, hygiene findings with no score change, across `settings.json` and `settings.local.json`: handlers that never run (not an object with a `type` inside a matcher group's `hooks` array), missing or relative script paths, `claude -p` in a hook, and a shell-form PreToolUse or PermissionRequest hook that would run in PowerShell on Windows without Git Bash; plus notes for a SessionStart hook with no matcher, several Bash PreToolUse hooks returning `updatedInput`, and an interpreter that is not on PATH. Findings name the settings file, event, index and script path, never the command text |
| **Security & hygiene** | 10 | `.env` / credentials presence vs `.gitignore` coverage, plus a regex scan for leaked API keys (`sk-...`, `AKIA...`, `ghp_...`) in tracked files |
| **Optimizer tooling** | 15 | Bonus: cost-mode skill installed, custom slash commands, subagents, plugin marketplace metadata. The subagent findings described under `--user` also run on `.claude/agents` |
| **Total** | **100** | |

| Grade | Score | Color |
|:-----:|:-----:|:-----:|
| A+ | 95-100 | brightgreen |
| A | 85-94 | green |
| B | 70-84 | yellowgreen |
| C | 55-69 | yellow |
| D | 40-54 | orange |
| F | 0-39 | red |

## Flags

From `claude-rate --help` (claude-rate 0.4.1):

```
positional arguments:
  path                  Project directory (default: current dir)

options:
  -h, --help            show this help message and exit
  --json                Emit machine-readable JSON
  --fix                 Show copy-pasteable fix suggestions
  --strict              Exit with status 1 if grade is below B
  --user                Also grade your user-level setup (~/.claude): global
                        instructions, skill listing, user MCP servers, user
                        settings and Read deny rules
  --usage [DAYS]        Also grade your measured usage from local Claude Code
                        transcripts (default: last 30 days): cache hit rate,
                        context size, model mix and list-price spend per model
  --by KEYS             With --usage: list-price spend grouped by any of
                        project, branch, session, day, week, version, skill,
                        mcp, plugin, agent (a comma list)
  --what-if MODEL[,MODEL]
                        With --usage: reprice your recorded tokens on other
                        models (modeled, quality not tested)
  --scope {all,main,subagents}
                        Requests the --what-if table covers (default: all);
                        the grade always uses every request
  --budget USD          With --usage: the date this month's list-price spend
                        crosses USD at the current pace
  --plan {pro,max,ultra}
                        With --usage: list-price spend per 30 days divided by
                        the plan's monthly price
  --history DIR         With --usage: save an aggregates-only snapshot in DIR
                        and compare it with the newest earlier one
  --burn [MINUTES]      Live view of list-price spend in the last MINUTES
                        (default 60); skips the project grade
  --watch SECONDS       With --burn: redraw every SECONDS (15 or more) until
                        Ctrl+C
  --tools               With --usage, also audit tool output: which tool
                        results fill context and what carrying them costs
                        (cache-aware, an upper bound). Reads tool names,
                        inputs and result text locally and prints aggregates
                        only
  --max-context-tokens N
                        Exit with status 1 when the always-loaded instructions
                        are estimated over N tokens: chars / 4 over CLAUDE.md,
                        .claude/CLAUDE.md, CLAUDE.local.md, .claude/rules
                        files without paths frontmatter and the files they
                        @import, plus ~/.claude/CLAUDE.md and its unscoped
                        rules with --user. Ignores the 1.3x tokenizer overhead
                        of 4.7+ models
  --statusline          Read Claude Code's statusLine JSON on stdin and print
                        at most two status rows: context, rate limits, cache
                        countdown and the list price of a cold re-cache
  --transcript PATH     Price one session transcript plus its subagent
                        transcripts at list price; prints JSON
  --state FILE          With --transcript: keep byte offsets, totals and seen
                        message ids in FILE so each call reads only new lines;
                        sessions that share FILE share one day total
  --hook {cache-guard}  Run as a Claude Code hook: cache-guard prices a
                        PreModelSwitch, or a stale SessionStart resume or
                        fork, from the payload on stdin
  --version             show program's version number and exit
```

### CI usage

Add a quality gate to your CI:

```yaml
# .github/workflows/claude-rate.yml
name: claude-rate
on: [pull_request]
jobs:
  rate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          curl -sSL https://raw.githubusercontent.com/Sagargupta16/claude-cost-optimizer/main/tools/claude-rate/install.sh \
            | sh -s -- . --strict --fix
```

`--strict` exits with status 1 if your grade drops below B, breaking the build until the configuration is fixed.

`--max-context-tokens N` (claude-rate 0.4.0 or later) is a size gate on its own, whatever the grade: it exits with status 1 when the always-loaded instructions (`CLAUDE.md`, `.claude/CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules/` files without `paths:` frontmatter and the files they `@import`) are estimated over N tokens at chars / 4, and prints the reason on stderr before the report. On the example project above:

```
$ claude-rate . --max-context-tokens 2000
claude-rate: always-loaded instructions are ~5,232 tokens, over --max-context-tokens 2,000. Largest: CLAUDE.md ~5,232.
...
$ echo $?
1
```

### Programmatic / JSON

On the example project above:

```bash
claude-rate . --json | jq '.grade, .cost_estimate."sonnet-5-5".per_month'
# "C"
# 32.4
```

With `--user` the JSON adds `user` (its startup-tokens estimate is `user.facts.startup`), and with `--usage` it adds `usage`, whose `facts` hold every key in the [usage reports](#usage-reports) tables.

## Why a separate tool from the web analyzer?

The [web analyzer](https://sagargupta.online/claude-cost-optimizer/analyzer/) is aimed at **public repos** -- paste a GitHub URL, get a grade. But it can only see what's exposed via the GitHub Contents API. It can't:

- See your local `.claude/settings.local.json` (gitignored)
- Detect untracked secrets that haven't been pushed yet
- Check your Read deny rules against the lock files actually on disk
- Check whether you've installed the cost-mode skill locally

`claude-rate` runs where your code actually is. It's also faster (no network round-trip), works on private repos, and integrates with CI.

## Pricing data

All cost estimates use Anthropic's published rates **verified 2026-11-10**:

- Fable 5.2: $8/$40 per 1M tokens (1M context, released 2026-11-09) -- the most capable widely released model, 2x Opus 5.5 and 20% below Fable 5.1 on every rate ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing), read 2026-11-10)
- Fable 5.1 and Fable 5: $10/$50 per 1M tokens (1M context, both legacy)
- Opus 5.5: $4/$20 per 1M tokens (1M context, released 2026-09-22) -- Anthropic's recommended starting model for most workloads, and 20% below Opus 5
- Opus 5 / 4.8 / 4.7 / 4.6: $5/$25 per 1M tokens (1M context, all legacy)
- Sonnet 5.5: $2/$10 per 1M tokens (1M context, released 2026-09-28) -- the current Sonnet flagship, same rate and tokenizer as Sonnet 5, but its cache read is $0.10 (cut on 2026-10-07), half Sonnet 5's $0.20
- Sonnet 5: $2/$10 per 1M tokens (1M context, legacy) -- the permanent standard rate; the increase to $3/$15 was cancelled
- Sonnet 4.6: $3/$15 per 1M tokens (1M context, legacy)
- Haiku 5.5 (`haiku-5-5`): $0.10/$0.50 per 1M tokens up to 100K prompt tokens, $0.50/$2.50 above (1M context, released 2026-10-07) -- the current Haiku and the first model priced by prompt length
- Haiku 4.5 (`haiku-4-5`): $1/$5 per 1M tokens (200K context, legacy)
- Opus 4.1: $15/$75 per 1M tokens (200K context; retired on the Claude API on 2026-08-05, still served on Bedrock and Google Cloud), so transcripts and bills that still use it are priced ([pricing page](https://platform.claude.com/docs/en/about-claude/pricing), read 2026-11-03)
- Model ids are matched whole (claude-rate 0.4.0 or later): a plain, Bedrock (`anthropic.claude-...`) or dated id maps to its row, and an id the table does not carry, such as a point release newer than this file, is counted but not priced and listed by id. Mythos 5.2, Mythos 5.1 and Mythos 5 are priced as Fable 5.2, Fable 5.1 and Fable 5, Opus 4.5 as Opus 4.6, Opus 4 as Opus 4.1, and Sonnet 4.5 and Sonnet 4 as Sonnet 4.6, the rows with the same rates
- Cache hit: three multipliers -- 0.1x base input on most models (Haiku 5.5: $0.01/1M, or $0.05 over 100K), 0.05x on Opus 5.5 ($0.20/1M) and Sonnet 5.5 ($0.10/1M), 0.025x on Fable 5.2 ($0.20/1M) and Fable 5.1 ($0.25/1M); 5m write: 1.25x; 1h write: 2x
- Every model on the Claude 4.7+ tokenizer (Opus 4.7 and later, Fable, Sonnet 5 and 5.5, Haiku 5.5) includes a +30% tokenizer overhead: Anthropic's [pricing page](https://platform.claude.com/docs/en/about-claude/pricing) puts it at approximately 30% more tokens for the same text. Opus 4.6, Sonnet 4.6 and Haiku 4.5 use the previous tokenizer
- Each turn is billed the way Claude Code caches a conversation ([prompt caching docs](https://code.claude.com/docs/en/prompt-caching)): turn 1 writes the whole prompt at the 5-minute write rate (1.25x input), and every later turn reads the previous request from cache and writes only the new ~1,500-token exchange
- Haiku 5.5 is priced turn by turn, the way Anthropic bills each request on its own: a turn whose estimated prompt (after the tokenizer overhead) is over 100,000 tokens is priced at $0.50/$2.50 for input, cache and output alike. The example above stays under 100K on every turn

### Opus 5.5 cost gotchas

Opus 5.5 is 20% cheaper per token than Opus 5 ($4/$20 vs $5/$25), but re-baseline your costs after migrating:

- **Adaptive thinking is always on.** `thinking: {type: "disabled"}` and `budget_tokens` both return a 400, so effort is the only control. Code that disabled thinking on Opus 5 now pays for thinking tokens, billed as output at $20/1M.
- **`effort` defaults to `medium`** (Opus 5 defaulted to `high`; all five levels are supported). A request that omits effort now thinks less than it did on Opus 5.
- **Forced `tool_choice` (`any` / `tool`) returns a 400**, as do non-default sampling params and assistant prefill. Use `auto` with strict tool use or structured outputs.
- **`max_tokens` is a backstop, not a knob.** On Anthropic's repository-task benchmark a 16,384 cap ended about a quarter of Opus 5.5's attempts and 43% of Fable 5.1's ([cost guide](https://platform.claude.com/docs/en/about-claude/models/optimizing-for-cost-and-intelligence)); use 64,000 for agentic work.
- **Prompts written for an older model make the new one over-work.** In Anthropic's published runs, prompts written for Opus 4.8 cost 36% more per ticket on Opus 5 for no accuracy gain; audited, they were 14% cheaper and more accurate. Prune inherited instructions.
- **Minimum cacheable prompt is 512 tokens** on Opus 5.5 and Opus 5 (1,024 on Opus 4.8, 2,048 on Opus 4.7, 4,096 on Opus 4.6). A `cache_control` block below the floor is silently ignored: no error, no `cache_creation_input_tokens`, full input price.

### Sonnet 5.5 cost gotchas

Sonnet 5.5 costs the same as Sonnet 5 ($2/$10) and uses the same tokenizer, so migrating is free at the posted rate, and since 2026-10-07 cached reads cost half as much ($0.10 vs $0.20 per 1M, 0.05x base input). What still moves the bill:

- **Adaptive thinking is on by default** (effort `high`) and reasoning bills as output at $10/1M. `thinking: {type: "disabled"}` and `budget_tokens` return a 400; send `thinking: {type: "between_tools"}` at `high` effort or below to stop up-front thinking on routine turns.
- **Effort levels are recalibrated.** The same level does not produce the same amount of thinking as on Sonnet 5, so re-run your effort sweep. Anthropic's starting points: `high` in general, `medium` for well-specified agentic coding.
- **Forced `tool_choice` (`any` / `tool`) returns a 400**, as do non-default `temperature` / `top_p` / `top_k`. Use `auto` with strict tool use or structured outputs.
- **Minimum cacheable prompt is 512 tokens** (1,024 on Sonnet 5), so short system prompts that never cached on Sonnet 5 now do.
- **In Claude Code, `sonnet` is Sonnet 5.5 only on the Anthropic API.** On Bedrock, Google Cloud (Google managed, formerly Vertex AI) and Foundry it is Sonnet 4.5 ($3/$15, 200K context; deprecated, retirement scheduled for 2026-11-30), and on Claude Platform on AWS it is Sonnet 4.6 ($3/$15). Pin `claude-sonnet-5-5` (Bedrock: `anthropic.claude-sonnet-5-5`) or set `ANTHROPIC_DEFAULT_SONNET_MODEL`. Needs Claude Code v2.1.284 or later.

### Haiku 5.5 cost gotchas

Haiku 5.5 is 10x cheaper per token than Haiku 4.5 up to 100K prompt tokens and 2x above, but:

- **The 100K line is a cliff.** A request's prompt length counts all of its input tokens, including cache reads and writes, and a request over 100,000 tokens pays the higher prices for all of it, output included. A 100,000-token prompt costs $0.010 of input; a 100,001-token prompt costs $0.050 (5x). Short subagent and classification calls are where it wins.
- **~30% more tokens for the same text** than Haiku 4.5 (newer tokenizer), so per task it is roughly 7.7x cheaper at <=100K (10 / 1.3) and ~1.5x above (2 / 1.3).
- **Adaptive thinking is on by default** (effort `medium`). In Claude Code you cannot turn it off on Haiku 5.5.
- **Code carried over from Haiku 4.5 can return 400**: `budget_tokens`, non-default `temperature` / `top_p` / `top_k`, and assistant prefill are all rejected.
- **Minimum cacheable prompt is 512 tokens** (Haiku 4.5: 4,096).
- **In Claude Code, `haiku` is Haiku 5.5 only on the Anthropic API** (v2.1.293 or later). On Claude Platform on AWS, Bedrock, Google Cloud and Foundry it is Haiku 4.5 ($1/$5, 200K context). Set `ANTHROPIC_DEFAULT_HAIKU_MODEL` to pin it; that also sets the model for background functionality.

### Fast Mode

`speed: "fast"` is **Fable 5.2, Mythos 5.2, Opus 5.5, Opus 5 and Opus 4.8 only**, at a flat **2x** of each model's base: $16/$80 on Fable 5.2 and Mythos 5.2, $8/$40 on Opus 5.5, $10/$50 on Opus 5 and Opus 4.8. Fable 5.2 has it with no beta header on the Claude API, both Claude Models on Google Cloud offerings (Google sets the price on the Google-managed one) and Microsoft Foundry hosted on Anthropic, where it is a separate model, `claude-fable-5-2-fast`; in Claude Code, `/fast` on Fable 5.2 needs v2.1.321 or later. Cache multipliers stack on the fast rate, so Fable 5.2 fast reads cache at $0.40 and writes at $20 (5m) or $32 (1h) (computed: 0.025x, 1.25x and 2x of $16). Opus 5.5 has it generally available (out of research preview since 2026-10-15) with no beta header, on the Claude API, Claude Models on Google Cloud (Anthropic managed) and Microsoft Foundry. Opus 5 and Opus 4.8 are a research preview on the Claude API only and need the `fast-mode-2026-02-01` beta header; Opus 4.8's fast mode is deprecated (2026-10-30) and removed on 2026-11-30, after which `speed: "fast"` on `claude-opus-4-8` returns an error with no fallback. The older 6x tier no longer exists. Opus 4.7 returns an error on `speed: "fast"` with no fallback, and Opus 4.6 accepts the field but silently runs at standard speed and standard rates (`usage.speed` comes back `"standard"`). Managed Agents support it on the Claude API only. It cannot combine with Batch or Priority Tier, and fast and standard speed keep separate prompt caches, so switching speeds invalidates the cache. In Claude Code, subscription users pay for fast mode with usage credits only ([fast mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode) and [Claude Code fast mode](https://code.claude.com/docs/en/fast-mode), read 2026-11-10).

Sources:
- [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)
- [platform.claude.com/docs/en/models/overview](https://platform.claude.com/docs/en/models/overview)
- [platform.claude.com/docs/en/build-with-claude/fast-mode](https://platform.claude.com/docs/en/build-with-claude/fast-mode)
- [platform.claude.com/docs/en/models/opus-5-5/overview](https://platform.claude.com/docs/en/models/opus-5-5/overview)
- [platform.claude.com/docs/en/models/sonnet-5-5/overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview)
- [platform.claude.com/docs/en/models/haiku-5-5/overview](https://platform.claude.com/docs/en/models/haiku-5-5/overview)

## Limitations

- **Heuristic scoring.** Token estimates assume 30 turns/session, 3 sessions/day, 22 working days/month, ~1,500 new tokens and 500 output tokens per turn, with each turn reading the previous request from cache. Your actual usage may differ; treat the dollar numbers as order-of-magnitude.
- **The project grade is static.** It reads files and does not trace API calls. `--usage` prices what your transcripts recorded (`--usage --by session` for measured per-session costs), and the [live modes](#live-modes-inside-a-session) read Claude Code's status line and hook payloads during a session. Every dollar any of them prints is a list-price estimate, not a bill.
- **Stdlib only.** Intentional -- no `tiktoken`, no `requests`, runs anywhere Python 3.10+ runs. Token counts are estimated as characters / 4, then multiplied by the tokenizer overhead. Anthropic's [models overview](https://platform.claude.com/docs/en/models/overview) puts the current tokenizer at about 2.5 characters per token (1M tokens is roughly 2.5M characters), so these counts can run low: treat them as a floor.

## License

MIT. Source: [github.com/Sagargupta16/claude-cost-optimizer](https://github.com/Sagargupta16/claude-cost-optimizer)
