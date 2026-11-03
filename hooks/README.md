# Claude Code Budget Enforcement Hooks

Hooks that track tool calls per session, price the session from its transcript when you set a dollar cap (warn, then ask, optionally deny), show what a model switch or a stale resume costs in cache re-writes, and log session summaries for historical analysis. Two more are opt-in: one loads a handoff note after `/clear`, and one trims the output of green build and test runs before Claude reads it.

## What Are Claude Code Hooks?

Claude Code hooks are shell commands that run automatically in response to specific events during a Claude Code session. They are configured in `settings.json` and execute as subprocesses -- they receive JSON on stdin with event data and can output JSON to stdout to surface messages to the user.

Claude Code has about 30 hook events ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03). The ones that matter for cost tracking:

| Event | When It Fires |
|-------|---------------|
| `PreToolUse` | Before a tool call is executed |
| `PostToolUse` | After a tool call completes |
| `Stop` | When Claude finishes responding -- every turn, not once per session |
| `SubagentStop` | When a subagent finishes |
| `PreCompact` / `PostCompact` | Before and after a compaction |
| `SessionStart` | When a session starts (`startup`), resumes (`resume`), forks (`fork`), or restarts after `/clear` (`clear`) or a compaction (`compact`); the matcher picks which |
| `PreModelSwitch` | Before a model switch you request (`/model`, the model picker, `/config`); Claude Code v2.1.251 or later |
| `SessionEnd` | When a session terminates (`/clear`, `/resume`, logout, exit) |

Each hook entry has a `matcher` and a list of handlers. For tool events the `matcher` is matched against the tool name -- `".*"` matches all tools; `""` matches every occurrence of events that have no tool. On macOS, Linux and WSL, Claude Code leaves the Glob and Grep tools out of the default tool set and searches with `find` and `grep` through Bash, so a matcher on `Glob|Grep` only fires on Windows or when those tools are turned back on ([tools reference](https://code.claude.com/docs/en/tools-reference), read 2026-11-01).

## What These Hooks Do

### budget-tracker.sh (PreToolUse)

Counts every tool invocation in the session and warns when approaching a configurable limit. With a dollar cap set, it also prices the session before each tool call.

- Maintains a per-session counter in a temp file
- At 80% of the limit (configurable): prints a warning with remaining count
- At 100% of the limit: prints a "limit reached" message. The tool-call counter only ever warns.
- Dollar caps are opt-in: nothing below happens until you set `BUDGET_SESSION_USD`, `BUDGET_DAY_USD`, `BUDGET_TURN_USD` or `BUDGET_SESSION_USD_WARN`

With a cap set, the script has claude-rate (`tools/claude-rate/rate.py --transcript`, claude-rate 0.4.0 or later) price the payload's `transcript_path` at list price: the main transcript plus every subagent transcript under `<session>/subagents/`, each message id once at its final usage snapshot, cache reads and writes at their own rates. A state file in `BUDGET_LOG_DIR` keeps a byte offset per transcript, so each call reads only what was written since the last one, and claude-rate runs only when the session's transcripts changed size. The session cap covers subagents; the day cap covers every session this tracker priced today (local calendar day), and history a resumed session copies counts once; the turn cap covers the current prompt (`prompt_id`), subagents included.

Each cap has a ladder. Every warning step fires once per session, day or prompt (marker files created with `O_EXCL`, the same create-only-if-absent rule as bash `noclobber`, so parallel tool calls cannot double-fire a step):

| Share of the cap | What happens |
|------------------|--------------|
| 70% | Warning: at the next task boundary, one model tier down (Opus to Sonnet, Sonnet to Haiku) slows the climb |
| 80% | Warning with the spend and the cap |
| 90% | Warning: `/compact`, or hand searches to a Haiku subagent |
| 100%, then 125%, 150%, ... | `permissionDecision: "ask"`: you approve the call to keep going, and it asks again at the next +25%, so one approval does not end the cap |
| 120% with `BUDGET_HARD_DENY=1` | `permissionDecision: "deny"` on every tool call, the hard limit [guides/05-team-budgeting.md](../guides/05-team-budgeting.md#budget-enforcement-philosophy) recommends instead of 100% |

These percentages are starting points to tune, not measurements. Every message says the figure is a list-price estimate: the transcript is written asynchronously and may lag the conversation ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03), so it can trail by a request or two, and on a Pro, Max or Ultra plan it is API-equivalent value, not your bill.

- **Unattended runs**: in `claude -p`, an `ask` nobody can answer is denied, and Claude reads the reason ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03); in `dontAsk` mode the script returns `deny` itself. Either way that is one denied call per step, so set `BUDGET_HARD_DENY=1` in CI to keep denying. For print mode, `claude -p --max-budget-usd` is Claude Code's own cap.
- **Auto mode**: the hooks reference says a PreToolUse `ask` sends the call to the permission prompt rather than the classifier. Under `bypassPermissions` the ask is not verified here.
- **Never gated**: `SubagentHandback` (a subagent delivering its report) is warned, never asked or denied, so a cap does not throw away work already paid for.
- **Overshoot**: the cap is checked before tool calls, so a long reply with no tool calls, or several tool calls started at once, can pass it before the ask appears.
- **Finding claude-rate**: `CLAUDE_RATE_PY` if set, else `../tools/claude-rate/rate.py` next to the script, else an installed claude-rate (the `claude_rate` module or `claude-rate` on PATH). If a cap is set and none is found, it warns once per session and counts tool calls only.
- **Cost per call**: one Python process (it used to start two), plus the import of rate.py when the transcripts grew.

### cost-logger.sh (PreToolUse)

Logs estimated token count and cost for each tool call to a daily log file. Helps you understand where tokens go and which operations are expensive.

- Estimates input/output tokens by tool type (Read, Edit, Bash, Agent, etc.)
- Reads `tool_name` and `session_id` from the JSON on stdin (Claude Code sets no per-tool environment variables)
- Logs each call with timestamp, tool name, token estimate, and cost; prices by `COST_LOGGER_MODEL`, then `ANTHROPIC_MODEL`, then Opus 5.5 (hook input carries no model)
- Warns at 50 and 100 tool calls in a session to suggest a refresh
- Never blocks -- informational only
- Review logs at `${TMPDIR:-/tmp}/claude-cost-log/session-YYYYMMDD-<session_id>.log`

### session-summary.sh (SessionEnd)

Runs when the session ends. Produces a summary and appends it to a persistent log file. Register it on `SessionEnd`, not `Stop`: `Stop` fires after every response, so the counter cleanup below would reset the budget tracker every turn (this repo had it on `Stop` until 1.18.0).

- The SessionEnd payload carries `session_id`, `transcript_path`, `cwd` and `reason`, no model, turns or duration; the summary gets those from the transcript through claude-rate (`--transcript`): models with their list-price dollars, requests, prompts, the time from the first to the last request, and the total list-price estimate, subagents included. Without claude-rate it logs the tool call count only.
- Writes a timestamped entry to `sessions.log` for historical tracking
- Cleans up the per-session counter file, the spend cache and the session's warning markers
- SessionEnd hooks share a 1.5-second budget by default, and a per-hook `timeout` raises it, up to 60 seconds ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03). Pricing a long session from scratch can take longer, so [settings-example.json](settings-example.json) gives this hook `"timeout": 10`; when budget-tracker.sh has been pricing the session, the summary reuses its state and reads only the new bytes.

### cache-guard.sh (PreModelSwitch, SessionStart resume|fork)

Shows, as a `systemMessage`, what a cache break costs before the request that pays it. It runs `rate.py --hook cache-guard` (claude-rate 0.4.0 or later) and needs Claude Code v2.1.251 or later, which added these payload fields ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03).

- **Model switch** (`PreModelSwitch`): the payload carries `context_tokens`, `prompt_cache_warm`, `cache_ttl`, and Claude Code's own `estimated_cache_write_usd` for writing the prompt to the new model's cache, with `pricing` saying how it priced it (`default` means it had no price for the model and guessed; the message says so). The hook compares that with staying: a cache read on the current model while the cache is warm, a re-write at the same TTL once it is cold. For the hooks reference's example (182,340 tokens, Sonnet 5 to Opus 5, warm, 5-minute TTL, estimate $1.1396), staying reads 182,340 x $0.20 / 1M = $0.036, so the switch adds about $1.10. When the transcript is readable it prices your last 10 main-thread requests on both models (same tokens assumed): for a cheaper target it says after how many such requests the switch pays back, for a dearer one only how much more each costs.
- **Stale resume or fork** (`SessionStart`, matcher `resume|fork`): when `prompt_cache_likely_expired` is true and `context_tokens` is at least `CACHE_GUARD_MIN_TOKENS` (default 50,000, a starting point to tune, not a measurement), it prints the re-write cost (Claude Code's estimate) and suggests `/rename` to find the session later, then `/clear` or a fresh session if the old context is not needed. On Pro and Max, Claude Code already warns when a resume would use a noticeable share of the 5-hour limit (v2.1.304); this one adds the list-price figure, and covers API keys and cloud providers too.
- **Never blocks**: it returns no `permissionDecision`. `"allow"` would skip the confirmation Claude Code already shows when you `/model` with a warm cache, and `"ask"` would repeat it. Claude Code shows a `systemMessage` whatever the decision.
- **Fails open**: claude-rate abandons its own work after 3 seconds and prints nothing, and the script always exits 0. Do not give the PreModelSwitch entry a short `timeout`: a PreModelSwitch hook that reaches its timeout blocks the switch (default 30 seconds).

### handoff-loader.sh (SessionStart clear, opt-in) and /handoff

[templates/commands/handoff.md](../templates/commands/handoff.md) is a `/handoff` command: it overwrites `.claude/handoff.md` with at most 40 lines (Goal, Done, Next, Files touched, Open questions, Commands to re-run) and prints the same notes in chat, so they work with no hook at all. Run it while the cache is warm, before a break or a `/clear`.

handoff-loader.sh loads those notes into the next session after `/clear`, once. It is opt-in: [settings-example.json](settings-example.json) keeps its entry under `_opt_in_hooks`, which Claude Code does not read; move it into `hooks` to turn it on. It loads `.claude/handoff.md` only when:

- the matcher is `clear` (and the payload says so), so a new session, a resume, a fork or a compaction never loads anything
- the file is untracked and git-ignored, so notes committed to a repository you cloned are never injected; outside a git repository it never loads (add `.claude/handoff.md` to `.gitignore`)
- it is younger than `HANDOFF_MAX_AGE_HOURS` (default 24) and has not been loaded before: after one load the script sets the file's modification time to 1970, and the next `/handoff` rewrites it

The notes arrive as `additionalContext`, framed as an earlier session's notes that may be stale and are not instructions, cut to 8,000 characters; Claude Code caps a hook's `additionalContext` at 10,000 characters and saves anything longer to a file Claude is not asked to read ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03).

### Trim noisy build and test output (opt-in)

`output-trim.sh` shortens the output of green build, install and test runs before Claude reads it. It is a PostToolUse hook on Bash that returns `updatedToolOutput`. It is off until you add it (see `settings-example.json`).

Scope: PostToolUse only fires for a Bash command that exited 0, so this covers builds, installs and passing suites. A failed run goes to PostToolUseFailure, which can only add context and cannot rewrite output, so failed runs are never trimmed. The tool has already run and OpenTelemetry records the original output; only what Claude reads changes. Cutting detail can mislead Claude, which is why the hook is narrow. Needs Claude Code 2.1.121 or later (the changelog entry that lets PostToolUse replace the output of every tool; read 2026-11-03).

What it does:
- Acts only when the first real command (after cd, env assignments, time, npx, uv run, pnpm exec) is a known runner: pytest, python -m pytest or unittest, vitest, jest, mocha, node --test, npm/pnpm/yarn/bun test, install, ci, add, build or run test|build|typecheck|check, tsc, go test|build|vet, cargo test|build|check|clippy, dotnet test|build, mvn, gradle, uv sync, pip install. The list is at the top of `output_trim.py`.
- Leaves alone any chain that contains a read-like command (cat, sed, head, tail, grep, rg, ls, find, git diff/show/log), any pipeline, interrupted runs, images, background runs, and output under 2,000 characters (`CLAUDE_TRIM_MIN_CHARS`).
- Strips ANSI codes and carriage-return redraws, folds repeated lines (identical, or different only in digits) into a count, keeps the first 30 and last 40 lines, every error/warn/fail/deprecated line with 2 lines of context (first 40 matches), and runner result lines such as "13 passed" or "Ran 13 tests".
- Writes the full output to `${TMPDIR:-/tmp}/claude-trim/<session>/<tool_use_id>.txt` (.txt on purpose: `.claude/settings.json` denies Read(*.log)) and ends the output with a footer naming kept lines, total lines and that path.
- Never-worse guard: unless the result is non-empty and at least 20% shorter, the original output goes through. Any error inside the hook also leaves the output unchanged.
- The replacement is a copy of the incoming tool_response with only stdout and stderr changed. Kill switch: `CLAUDE_TRIM_OFF=1`. Per-session numbers: `stats.tsv` in the spill folder.

Measured here: `python scripts/eval-output-filter.py` (read 2026-11-03) trimmed 3 of 9 captured fixtures (4948 to 3706, 7600 to 5724 and 7544 to 5684 bytes), left the other 6 alone (5 are under 2,000 characters, 1 saves under 20%), dropped 0 of 27 needed strings and grew nothing. This repo's single suites print 215 to 1,839 characters, so the hook only acts on long chained runs, colored runs and bigger projects' output. Token figures in that script are an estimate (chars / 4 x 1.3). Anthropic's costs page example is a PreToolUse hook that filters test output; its tens-of-thousands-to-hundreds claim is its own, not measured here. Claude Code's own `bashOutputMaxChars` cap already bounds very large output.

### Status line: claude-rate --statusline

Not a hook, but the same live data. [templates/settings/statusline.json](../templates/settings/statusline.json) wires `claude-rate --statusline` (claude-rate 0.4.0 or later) into the status line: context fill, Claude Code's own session cost estimate, the 5-hour and 7-day limit windows with pace and run-out time, and the cache countdown with the list price of letting it go cold.

### Going further: hooks that cut tokens

The other hooks here count, price and warn; only [output-trim.sh](#trim-noisy-build-and-test-output-opt-in) shrinks what Claude reads, and only for green runs. Anthropic's [costs page](https://code.claude.com/docs/en/costs) calls preprocessing output the bigger lever; its example is a PreToolUse hook that filters test output down to the failures, and the tens-of-thousands-to-hundreds figure is its claim, not measured here. [rtk](https://github.com/rtk-ai/rtk) packages the same idea as a CLI proxy that compresses common dev-command output; its GitHub description claims 60-90% on those commands (its README now says "up to 90% smaller", read 2026-11-01), not measured by this repo, and its README adds that this is not the same as cutting your bill by the same amount.

## Installation

### 1. Copy the hook scripts

Clone or download this repo, then note the path to the `hooks/` directory. Keep the scripts next to `tools/claude-rate/rate.py` (they find it at `../tools/claude-rate/rate.py`), or set `CLAUDE_RATE_PY` to its full path.

### 2. Make scripts executable

```bash
chmod +x hooks/budget-tracker.sh hooks/session-summary.sh hooks/cost-logger.sh hooks/cache-guard.sh hooks/handoff-loader.sh hooks/output-trim.sh
```

### 3. Configure settings.json

Copy the hooks configuration into your Claude Code settings file. You have two options:

**Global** (all projects): `~/.claude/settings.json`

**Per-project**: `.claude/settings.json` in your project root

Edit `settings-example.json` in this directory -- replace `/path/to/claude-cost-optimizer` with the actual path -- then merge the `hooks` block into your existing settings file. It wires budget-tracker.sh, session-summary.sh and cache-guard.sh; the handoff loader and the output trimmer wait under `_opt_in_hooks`. The schemastore schema the file declares does not list `PreModelSwitch` yet (read 2026-11-03), so an editor that validates against it flags that key; Claude Code accepts it.

This repo's own [`.claude/settings.json`](../.claude/settings.json) wires budget-tracker.sh, cost-logger.sh and session-summary.sh through `"$CLAUDE_PROJECT_DIR"/hooks/...`, so you can copy its `hooks` block into a project that keeps the scripts in its own `hooks/` folder; cache-guard.sh, handoff-loader.sh and output-trim.sh are not wired there. It validates against the `claude-code-settings.json` schema it declares. Do not use a bare relative path such as `bash hooks/cost-logger.sh`: a hook runs in the session's current directory, so it fails with "No such file or directory" as soon as Claude `cd`s into a subfolder. Claude Code sets `CLAUDE_PROJECT_DIR` to the project root for every hook ([hooks reference](https://code.claude.com/docs/en/hooks)). For a global install in `~/.claude/settings.json`, use absolute paths.

Each entry must be an object with `"type": "command"` and a `"command"` string. A bare command string in the `hooks` array is invalid and the hook silently never runs.

Example (using the provided `settings-example.json` as a reference):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "bash /home/you/claude-cost-optimizer/hooks/budget-tracker.sh"
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash /home/you/claude-cost-optimizer/hooks/session-summary.sh",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "matcher": "resume|fork",
        "hooks": [
          {
            "type": "command",
            "command": "bash /home/you/claude-cost-optimizer/hooks/cache-guard.sh"
          }
        ]
      }
    ],
    "PreModelSwitch": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "bash /home/you/claude-cost-optimizer/hooks/cache-guard.sh"
          }
        ]
      }
    ]
  }
}
```

To turn on the handoff loader, add a second `SessionStart` entry with `"matcher": "clear"` running `bash /home/you/claude-cost-optimizer/hooks/handoff-loader.sh`, and copy [templates/commands/handoff.md](../templates/commands/handoff.md) to `.claude/commands/` (project) or `~/.claude/commands/` (user).

To turn on the output trimmer, add a `PostToolUse` entry with `"matcher": "Bash"` running `bash /home/you/claude-cost-optimizer/hooks/output-trim.sh`, and keep `output_trim.py` in the same folder (the script runs it from there).

### 4. Verify

Start a new Claude Code session and make a few tool calls. You should see budget warnings as you approach the limit. When you end the session, the summary will be logged.

Check the log:

```bash
cat /tmp/claude-budget/sessions.log
```

To try a hook without a session, pipe a payload into it. For example, the hooks reference's PreModelSwitch example:

```bash
echo '{"hook_event_name":"PreModelSwitch","from_model":"claude-sonnet-5","to_model":"claude-opus-5","context_tokens":182340,"prompt_cache_warm":true,"cache_ttl":"5m","estimated_cache_write_usd":1.1396,"pricing":"catalog"}' | bash hooks/cache-guard.sh
```

## Configuration

All configuration is through environment variables. Set them in your shell profile or in the `env` block of your Claude Code settings.

| Variable | Default | Description |
|----------|---------|-------------|
| `BUDGET_TOOL_LIMIT` | `50` | Total tool calls before the "limit reached" warning |
| `BUDGET_WARN_AT` | `80` | Percentage of the limit at which warnings begin |
| `BUDGET_LOG_DIR` | `/tmp/claude-budget` (`%TEMP%\claude-budget` on Windows) | Directory for counter, marker and state files and session logs |
| `SESSION_LOG_FILE` | `$BUDGET_LOG_DIR/sessions.log` | Path to the persistent session log |
| `BUDGET_SESSION_USD_WARN` | unset | One warning when session spend passes this many dollars |
| `BUDGET_SESSION_USD` | unset | Session cap in dollars, subagents included: the ladder above |
| `BUDGET_DAY_USD` | unset | Cap on today's spend across every session the tracker priced |
| `BUDGET_TURN_USD` | unset | Cap on one prompt's spend, subagents included |
| `BUDGET_HARD_DENY` | unset | `1` = deny every tool call once a cap is 120% spent |
| `CLAUDE_RATE_PY` | `../tools/claude-rate/rate.py` next to the script | Full path to rate.py for budget-tracker, session-summary and cache-guard |
| `CACHE_GUARD_MIN_TOKENS` | `50000` | Smallest resumed context cache-guard warns about |
| `HANDOFF_MAX_AGE_HOURS` | `24` | The handoff loader ignores older notes |
| `CLAUDE_TRIM_OFF` | unset | `1` = output-trim.sh leaves every output unchanged |
| `CLAUDE_TRIM_MIN_CHARS` | `2000` | output-trim.sh leaves shorter output alone |

### Setting via Claude Code settings.json

```json
{
  "env": {
    "BUDGET_TOOL_LIMIT": "75",
    "BUDGET_WARN_AT": "70",
    "BUDGET_SESSION_USD": "5",
    "BUDGET_LOG_DIR": "/home/you/.claude/budget-logs"
  }
}
```

### Adjusting the Limit

The default of 50 tool calls is a reasonable starting point for cost-conscious usage. Adjust based on your workflow:

These are starting points to tune, not measurements:

| Workflow | Suggested Limit |
|----------|:--------------:|
| Quick bug fixes, simple edits | 25 |
| Moderate feature work | 60 |
| Large refactors, multi-file changes | 125 |
| Exploration and research | 200 |

## How It Works

### Data Flow

```
Claude Code PreToolUse event
    |
    v
stdin (JSON) --> budget-tracker.sh --> stdout ({"systemMessage": ...}, and at a cap
                     |                           hookSpecificOutput.permissionDecision)
                     |-- /tmp/claude-budget/session-{id}.count       (tool call counter)
                     '-- with a cap: rate.py --transcript {transcript_path}
                            --state /tmp/claude-budget/spend-state.json  (offsets, totals, seen ids)

Claude Code PreModelSwitch, or SessionStart resume|fork
    |
    v
stdin (JSON) --> cache-guard.sh --> rate.py --hook cache-guard --> stdout ({"systemMessage": ...} or nothing)

Claude Code SessionStart clear (opt-in)
    |
    v
stdin (JSON) --> handoff-loader.sh --> stdout (additionalContext from .claude/handoff.md, or nothing)

Claude Code PostToolUse on Bash, after a command that exited 0 (opt-in)
    |
    v
stdin (JSON) --> output-trim.sh --> output_trim.py --> stdout (updatedToolOutput, or nothing)
                                         |
                                         '-- ${TMPDIR:-/tmp}/claude-trim/<session>/<tool_use_id>.txt (full output), stats.tsv

Claude Code SessionEnd event
    |
    v
stdin (JSON) --> session-summary.sh --> stdout (discarded by Claude Code on SessionEnd)
                     |
                     v
              /tmp/claude-budget/sessions.log  (persistent log)
              /tmp/claude-budget/session-{id}.count  (cleaned up)
```

### Hook Input Format

Hooks receive a JSON payload on stdin ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03). Every event carries `session_id`, `transcript_path`, `cwd` and `hook_event_name`; tool events add `tool_name`, `tool_input` and `tool_use_id`, `prompt_id` identifies the current prompt, and `effort.level` appears where the model has effort. A PreToolUse example:

```json
{
  "session_id": "abc123",
  "transcript_path": "/home/you/.claude/projects/my-project/abc123.jsonl",
  "hook_event_name": "PreToolUse",
  "tool_name": "Read",
  "tool_input": {"file_path": "/path/to/file"},
  "tool_use_id": "toolu_01"
}
```

Claude Code sets no per-tool environment variables such as `HOOK_TOOL_NAME`; read the tool name from stdin. It does set `CLAUDE_PROJECT_DIR`. A tool event's payload has no token counts or dollars, but `transcript_path` points at the session transcript, which records every request's usage; the dollars have to be computed from it, which is what budget-tracker.sh and session-summary.sh have claude-rate do. Only `SessionStart` can carry a `model`; `PreModelSwitch` carries `from_model`, `to_model` and the cache fields above, and `SessionStart` on `resume` or `fork` adds `context_tokens`, `seconds_since_last_response`, `prompt_cache_likely_expired` and `estimated_cache_write_usd` (v2.1.251 or later).

### Hook Exit Code Semantics

The exit code from a hook script controls whether the tool call proceeds:

| Exit Code | Meaning | Behavior |
|:---------:|---------|----------|
| **0** | Success | Tool call proceeds. Claude Code applies any JSON output fields the hook printed. |
| **2** | Blocking error | Tool call is blocked. Stderr is the reason. |
| **Any other** | Non-blocking error | Tool call proceeds, with a hook error notice. |

Every script here always exits 0. budget-tracker.sh never blocks through the exit code: without a dollar cap it only warns, and at a cap it returns its `ask` or `deny` as JSON (`hookSpecificOutput.permissionDecision`), which Claude Code applies on exit 0.

### Hook Output Format

- **Exit 0 with JSON**: the fields apply. `systemMessage` is a warning shown to the user, which is what these scripts print. A `message` or `result` field is not a hook output field; JSON that fails validation shows as a hook error (these scripts printed those until 1.18.0, so their warnings never appeared).
- **PreToolUse decisions**: `hookSpecificOutput` with `permissionDecision` (`allow`, `deny`, `ask` or `defer`) and `permissionDecisionReason`. For `ask` the reason is shown in the permission prompt; for `deny` it is shown to Claude, so budget-tracker.sh also puts it in `systemMessage` for you.
- **Context and replaced output**: `hookSpecificOutput.additionalContext` on `SessionStart` adds text Claude reads (handoff-loader.sh); `hookSpecificOutput.updatedToolOutput` on `PostToolUse` replaces the tool result Claude reads (output-trim.sh).
- **Exit 0 with plain text or nothing**: success; the text is not shown in the transcript. On `SessionStart`, `UserPromptSubmit` and a few other events, plain stdout becomes context Claude reads, so these scripts print one JSON object or nothing.
- **Exit 2**: blocks the action; stderr is the reason.
- **SessionEnd**: Claude Code discards the output fields, so a summary hook has to write to a file.

## Troubleshooting

**Hooks not running**: Verify the path in settings.json is absolute and correct. Check that the scripts are executable (`chmod +x`).

**Python not found**: The scripts run `python3`, or `python` when there is no `python3`; output-trim.sh also tries `py` and takes the first one that is Python 3.10 or later. Without one they print nothing and exit 0. On Windows, a `python3` that is only the Microsoft Store stub (in `WindowsApps`) does the same: install Python, or turn the stub off under App execution aliases.

**Dollar cap never fires**: a cap with no claude-rate found warns once per session ("claude-rate was not found"). Set `CLAUDE_RATE_PY` to the full path of `tools/claude-rate/rate.py`, or install claude-rate 0.4.0 or later.

**Permission errors on /tmp**: Set `BUDGET_LOG_DIR` to a directory you have write access to.

**Hooks blocking Claude Code**: These scripts catch their own errors and always exit 0. If a hook hangs, check for filesystem issues. A command hook's default timeout is 600 seconds (30 on `UserPromptSubmit` and `PreModelSwitch`), and on `PreToolUse` a hook that times out does not block the tool call: the call continues through the normal permission flow. Two exceptions: a hook with `"onFailure": "block"`, and Windows without Git Bash (below). On `PreModelSwitch`, a hook that reaches its timeout does block the switch ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03).

**Windows: every tool call blocked**: These are bash scripts. On Windows, Claude Code runs a shell-form hook in Git Bash when Git Bash is installed and in PowerShell when it is not, and without Git Bash a shell-form `PreToolUse` or `PermissionRequest` hook that fails, with `onFailure` unset, blocks the tool call; the error says `blocking because Git Bash wasn't found` ([hooks reference](https://code.claude.com/docs/en/hooks), read 2026-11-03). The documented fixes:

- Install [Git for Windows](https://git-scm.com/downloads/win), or set `CLAUDE_CODE_GIT_BASH_PATH` if Git Bash is installed where Claude Code does not find it, then start a new session.
- Or add `"onFailure": "continue"` next to `"type": "command"` on the entry, so the call goes ahead when the hook fails. It needs Claude Code v2.1.295 or later. Elsewhere `continue` is already what a failure does, so the key changes nothing there. The schemastore schema does not list `onFailure` yet (read 2026-11-03), so an editor that validates against it flags the key.

Write script paths in `command` with forward slashes: Git Bash drops unquoted backslashes.

## Limitations

- Tool call counting is a proxy for cost, not an exact measure. A single Read of a large file costs more tokens than a Glob call, but both count as one tool call. The dollar caps measure cost directly.
- The counter file is session-scoped. If Claude Code does not provide a session ID in the hook payload, all calls fall back to a shared "default" counter.
- Hook payloads carry no billing data: the dollars are computed from the transcript at list price from claude-rate's rate table, so they ignore any negotiated or `modelPricing` rates, and on a subscription they are API-equivalent value, not the bill. Claude Code writes the transcript asynchronously, so the figure can trail by a request or two. An installed claude-rate keeps the rates it shipped with; upgrade it after a price change.
- A resumed session that copies earlier messages counts them once while the tracker's state holds them (two days back); a copy of older history counts again in the new session.
- The scripts handle missing payload fields gracefully, falling back to `default` and `n/a`.
- Whether each hook's message renders in a live session is checked here by piping sample payloads into the scripts, not in a running Claude Code session.
