# Changelog

## [1.12.1] - 2026-09-06

Propagation release. v1.12.0's pricing numbers were correct and are unchanged here -- Sonnet 5 stays $2/$10, Fable 5.1 / Mythos 5.1 keep the 0.025x cache read. What 1.12.0 got wrong was applying its own changelog: two entries ("Opus 4.1 moved to the retired list", "'verified' dates bumped from 2026-07-25") landed in a handful of files and were missed in the rest. This release finishes both, and adds automated checks so the next one cannot half-apply.

### Fixed
- **Opus 4.1 is described as retired everywhere, not as an upcoming migration.** It retired **2026-08-05** on the Claude API (still served on Bedrock and Google Cloud, which set their own schedules), but 8 places still called it "deprecated, retiring soon" or "still callable": the README's `Deprecated, retiring soon` table and its `Older snapshots still callable` row, `cheatsheet.md` (upcoming-retirements table, the `Deprecated (still working, retiring soon)` section, the historical-pricing note, and the still-active snapshots table), `guides/01`, and `guides/03` (twice) and `guides/06`. Opus 4.1 now sits in every "recently retired" table, and the retired-model rows that remain in pricing tables are annotated as such.
- **Mythos Preview is deprecated, not retired, and the 2026-06-30 date it carried is unsourced.** The deprecations page carries a Note reading "Claude Mythos Preview (`claude-mythos-preview`) is deprecated" and recommends Claude Mythos 5. The model has **no row in the model-status table and no published retirement date anywhere on that page**. This repo asserted "retired 2026-06-30" in 22 places across `README.md`, `cheatsheet.md`, `docs/pricing-data.md`, `guides/01`, `guides/03`, `guides/06`, `guides/08`, `guides/diagrams.md`, `site/src/utils/pricing.ts`, `tools/token-estimator/estimate.py` and `tools/usage-analyzer/README.md`; all 22 now say deprecated rather than retired, and the model is out of every "recently retired (requests will fail)" table. Earlier entries in this file (1.11.x and 1.12.0) assert that retirement date; they are wrong.
- **Mythos Preview is therefore the one model in Deprecated state.** `README.md` and `cheatsheet.md` name it explicitly instead of claiming nothing is deprecated, and the "no forced migration outstanding" line is scoped to *dated* migrations rather than stated absolutely.
- **Fable 5.1's release date is 2026-09-01, not 2026-09-04.** The [Fable 5.1 model page](https://platform.claude.com/docs/en/models/fable-5-1/overview) states "Released September 1, 2026"; 2026-09-04 appears on no Anthropic page. Corrected in `docs/pricing-data.md`, `site/src/utils/pricing.ts` and `tools/token-estimator/estimate.py`.
- **Sonnet 4.5's minimum cacheable prompt is 1,024, not 4,096.** The [prompt-caching page](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) lists it in the 1,024-token group; `docs/pricing-data.md` had it at 4,096 in two places while every table in the repo already said 1,024. Mythos Preview's 2,048 floor was also missing from that list.
- **Removed a rotting countdown.** `cheatsheet.md` read "Opus 4.1 is the only near-term forced migration left -- it retires August 5, 2026 (about 11 days out) ... Everything else on this list is a year or more away." Every clause had gone false: the date had passed, "11 days out" was frozen at the 2026-07-25 verification pass, and Sonnet 4.5 (2026-09-29) and Haiku 4.5 (2026-10-15) were both listed in the table directly above it. Replaced with absolute dates and no countdown.
- **Every pricing-provenance stamp now agrees at 2026-09-05** -- 23 stamps across 18 files, counted with the checker's own patterns. The drift ran both ways: files lagged at 2026-07-25 while `CLAUDE.md`, `README.md`, `site/src/utils/pricing.ts`, `tools/mcp-cost-server/src/index.ts`, `tools/token-estimator/estimate.py` and `tools/vscode-extension/src/costEstimator.ts` were already current, so `claude-rate` printed "Verified against Anthropic pricing as of: 2026-07-25" while listing Fable 5.1, released 2026-09-01.
- **Five date references were not stamps at all and survived the first pass.** `guides/03` (twice), `guides/06`, `guides/11` and `guides/diagrams.md` carried "Updated 2026-07-25", "As of 2026-07-25" and "at the time of writing (2026-07-25)", which the stamp patterns deliberately do not match, so the checker reported "all stamps agree" with all five still in the tree. Each one is gone -- the substantive content stays, and the file's own verified stamp carries the provenance -- and `check-pricing-sync.py` gained a fourth check for that phrasing.
- **Mythos 5.1 was missing from the README pricing table.** It is one of only two models with the 0.025x cache read, and README text pointed readers at that table to find it. Added at $10 / $50 / $0.25 cache hit / $12.50 5m-write / $20 1h-write.
- **Dead and broken links.** The Opus 5 migration guide URL cited in `README.md`, `cheatsheet.md`, and `site/src/utils/pricing.ts` returned 404; the live path is `/docs/en/models/opus-5/migration-guide`. `case-studies/README.md` linked `/CONTRIBUTING.md` and `/.github/ISSUE_TEMPLATE/case-study.md` root-relative, which resolve against github.com rather than the repo. `guides/06` pointed at a README anchor whose section no longer exists. The README's own `#pricing-reference-verified-2026-09-05` anchor did not match its `verified 2026-07-25` heading; the date is now a line beneath the heading so the anchor is stable across future verification passes.
- **The three web tools returned HTTP 404.** `/calculator`, `/badge`, and `/analyzer` rendered correctly for a human but answered 404, because `spa-404.mjs` only wrote `dist/404.html`. That de-indexes the repo's main public draw and trips every link checker. The build now also emits a real `index.html` per route, with the route list documented as needing to match `src/App.tsx`.
- **Sonnet 5 was missing from guide 01's 1M-context lists.** Both enumerations omitted the current Sonnet flagship (and Fable 5.1 / Mythos 5.1), so a reader of that guide alone would conclude the cheapest 1M-context option did not exist and reach for a 2.5x more expensive Opus tier.
- **Removed the one unsourced number in the section built to prove every number is sourced.** README claimed "measured real-world totals cluster around 70-73% ... e.g. a 6-person team cutting $2,400 -> $680/mo (72%)". That figure appears exactly once in the repo, has no citation, and cannot be sourced internally because `case-studies/` contains no case studies. Replaced with a statement of what the repo can actually back, and `case-studies/` is no longer advertised as containing stories until one exists.
- Corrected the cross-repo table's "50+ copy-paste recipes" to 47 (claude-code-recipes' own description), and set Fable 5.1's tentative retirement to 2027-09-01 per the deprecations page.
- **The README CLI Tools table now matches `tools/`.** It listed 8 rows, but the set mixed in Budget Hooks (which lives in `hooks/`) and omitted `tools/optimize-command`, so it disagreed with `tools/README.md` and with `CLAUDE.md`'s "8 CLI tools". Added the missing `claude-rate` and `/optimize` rows, and the count now says what it counts: the 8 tools in `tools/`, plus the hooks.
- **`.claude/settings.json`, `hooks/settings-example.json`, `hooks/README.md` and `guides/10` wired hooks in a shape Claude Code does not accept.** Each entry was a bare command string; the schema requires an object with `"type": "command"` and `"command"`, and a bare string means the hook silently never runs. All four are fixed and both JSON files now validate clean against the `claude-code-settings.json` schema they declare. `templates/settings/balanced.json` already used the correct shape.
- **Dropped `maxMonthlyCost` from `.claude/settings.json`.** It is not a Claude Code setting -- it appears nowhere in the settings schema, and Claude Code has no spend cap. `claude-rate` accepts it as one of six budget-cap keys, which is what awarded the repo 5 points for a key the product ignores; the settings category now scores 10/15 honestly. The rubric itself is fixed in the Changed entry below.
- Dropped two unused imports (`datetime`, `timezone`) from `tools/usage-analyzer/analyze.py`.

### Added
- **The repo now passes its own audit.** `claude-rate` scored this repo **35/100 (F)** and `.github/workflows/cost-audit.yml` published a **D (45/100)** grade to the Actions tab on every push to main -- the config grader failing its own rubric in public. Root causes, all fixed: no `.claudeignore` (0/15) though README Quick Start item #4 tells readers to add one; no tracked `.claude/settings.json` (0/15); no hooks wired (0/10) despite the repo shipping three budget hooks; and a `CLAUDE.md` of **14,224 chars** against the 4,000-char hard limit its own README tells readers to respect (2/20, "massively bloated"), meaning ~10,000 chars of its pricing detail were silently truncated and never reached the model. Now **86/100 (A)**, with the settings category at 10/15 rather than 15/15 because the repo does not ship a budget key Claude Code cannot read.
- `.claudeignore` at the repo root -- a working example from the project that recommends the practice, covering the site and both TypeScript tools' `node_modules`/build output, `__pycache__`, `*.tsbuildinfo`, and the lock files.
- `.claude/settings.json`, tracked, pinning a default model and permissions, and wiring `budget-tracker.sh`, `cost-logger.sh`, and `session-summary.sh` with repo-relative paths. It validates against the schema it declares. `hooks/README.md` points at it as a block you can copy instead of a placeholder template; whether the hooks fire in a live session is not something this PR demonstrates.
- `docs/pricing-data.md` -- the per-model pricing block moved out of `CLAUDE.md`, which is now **2,927 chars** and comfortably inside the limit. This is also the worked demonstration of the split-a-large-CLAUDE.md advice the guides give but never showed.
- `scripts/check-pricing-sync.py` -- four checks: verified-date drift between files, any model described as "retiring" on a date that has already passed, relative countdowns like "about 11 days out", and a doc-freshness date older than the canonical verified date. Run against the pre-fix tree it reports 14 problems: 7 stale "retires \<past date\>" occurrences, 1 countdown, and 6 verified-date mismatches. **Read what those 6 point at before trusting the check**: on that tree the canonical date is 2026-07-25, so the mismatches name the 6 files that were already correct at 2026-09-05 and the check is silent on the ones still lagging. Check 1 enforces *agreement* with `_PRICING_VERIFIED_DATE` in `rate.py`, not correctness -- bump that constant only after re-reading Anthropic's pages, and the check then names every file left behind. It reports 0 on this tree.
- `scripts/check-links.py` -- offline checker for relative links and heading anchors. Verified against the pre-fix tree: it reports exactly the 4 broken internal links with no false positives. It reproduces GitHub's anchor slug including the double-hyphen that `&` and `+` produce, which is what makes naive slugifiers report false positives on headings like "Legacy & Retired Models". External URLs are deliberately not checked: they rot for reasons outside this repo's control, which makes them a flaky gate.
- `.github/workflows/ci.yml` -- PR-time verification, which did not exist for a repo with a TypeScript SPA, 5 Python tools, and 63 markdown files. Typechecks and builds the site (paths-filtered so docs-only PRs stay fast), asserts every advertised route has a real entry point, byte-compiles the tools, lints them for genuine errors (`ruff --select E9,F`), smoke-tests both graders that CI and the README depend on, and runs the two consistency checkers. Previously the first build of a site change happened after merge, on main, where a failure meant a broken Pages deploy instead of a red PR.

### Changed
- **The settings rubric now scores cost controls Claude Code actually reads, instead of a spend cap that does not exist.** All four graders awarded points for the presence of `budgetCap` / `costLimit` / `maxCost` / `maxMonthlyCost` / `maxCostPerSession` / `budget`, and each one tested a *different subset*, so they already disagreed with each other. Checked on 2026-09-06 against [the settings schema](https://www.schemastore.org/claude-code-settings.json): **none of the six is among its 142 top-level properties.** Claude Code has no spend-cap setting -- the only budget-shaped key is `skillListingBudgetFraction`, a context fraction. So a third of the 15-point settings category went to a key the product ignores, and `claude-rate`'s fix text told users to add `"maxMonthlyCost": 100`. The 5 points now go to real settings, and the check is value-aware because presence is not enough: `"fastMode": true` doubles the bill and `"effortLevel": "max"` raises it. Credited: `effortLevel` at `low`/`medium` (reasoning tokens bill as output and effort defaults to `high`), `fastMode: false` (declines the flat 2x), `alwaysThinkingEnabled: false`, `autoCompactEnabled: true`, and `enforceAvailableModels: true` with a non-empty `availableModels` (the closest real analogue of a cap: it can keep Opus- and Fable-tier models out of a project entirely). All four graders plus the badge self-report UI were changed together and cross-checked over 24 shared inputs with 0 disagreements. Category maxima and the 100-point total are unchanged, so published grades stay comparable; this repo's own score is unaffected at 86/100 because it ships no budget key either way. For an actual spend ceiling, the advice now points at a `PreToolUse` hook, which is what `hooks/budget-tracker.sh` already does.
- `.github/workflows/cost-audit.yml` now grades with `claude-rate` instead of `badge-generator`. The two disagreed on identical input (35/F vs 45/D) because `badge-generator` scores 4 categories while `claude-rate` scores the 7 the README advertises, so the job was publishing a number the docs do not describe. `badge-generator` is unchanged and still documented as the 4-category precursor.

## [1.12.0] - 2026-09-05

### Added
- **Claude Fable 5.1 support** (`claude-fable-5-1`, GA 2026-09-04) across all pricing tables, guides, tools, templates, and the web calculator. Same posted rate as Fable 5 ($10/$50), 1M context (default and max), 128K max output, 512-token cache floor, Batch $5/$25, no Fast Mode, no Priority Tier, 30-day retention required. Adaptive thinking always on -- `thinking: {type: "disabled"}` and `budget_tokens` both return 400; depth comes from `effort` (`low` through `xhigh` and `max`). Documented the three breaking changes versus Fable 5: forced tool use (`tool_choice` `any`/`tool`) returns 400, thinking blocks are bound to the producing model, and editing earlier turns invalidates thinking blocks ("preserved thinking" -- accounts created on/after 2026-08-31 get a 400 on edited history). Also noted the new per-message `effort`, turn-scoped `clear_at` system messages, and `thinking.display: "updates"` betas.
- **Claude Mythos 5.1 entry** (`claude-mythos-5-1`): same specs, pricing, and cache rate as Fable 5.1, but under Project Glasswing and running access-program safeguards (so `refusal` can occur, unlike Mythos 5). Not offered on Claude Platform on AWS. Flagged `inviteOnly`.
- **The 0.025x cache-read tier is now modeled as a first-class exception.** `site/src/utils/pricing.ts` exports `CACHE_HIT_MULTIPLIER_DEFAULT` / `CACHE_HIT_MULTIPLIER_FABLE_5_1` plus a `cacheDiscountShare()` helper, and every tool table carries an explicit comment that the rate must be read, never derived as `input * 0.1`. The VS Code extension gained a `CACHE_HIT_PRICING` map it previously lacked entirely.

### Changed
- **Corrected a live pricing error: Sonnet 5 is $2/$10, not $3/$15.** Anthropic made the launch "introductory" rate permanent and **cancelled the increase to $3/$15** that was scheduled for 2026-09-01. Every tool in this repo was projecting Sonnet 5 at $3/$15 (cache hit $0.30, 5m-write $3.75, 1h-write $6.00), overstating Sonnet 5 cost by 50% -- fixed in the site calculator, MCP cost server, VS Code extension (+ its settings enum), token-estimator, usage-analyzer, and claude-rate, along with every guide, benchmark, cheatsheet, and tool README table. The Sonnet-vs-Opus gap is therefore a durable **2.5x (60% cheaper)**, not 1.67x/40%, and legacy Sonnet 4.6 at $3/$15 is now strictly more expensive than the current flagship.
- **Fable 5 and Mythos 5 moved to `legacy`.** Same posted price as 5.1 but 4x costlier cache reads ($1.00 vs $0.25), so migrating up is strictly cheaper on any cached workload; the calculator now emits that as a recommendation.
- **Opus 4.1 moved to the retired list** -- it retired **2026-08-05** on the Claude API (still served on Bedrock and Google Cloud). Sonnet 4.5 (2026-09-29) is now the next retirement due.
- Guide 08's framing corrected throughout: the "every model is 90% off" rule no longer holds, the per-model cache table gained a Fable 5.1 row at 97.5% off, and the TTL guidance now recommends a `max_tokens: 0` keep-alive on the 5-minute TTL over the 2x 1-hour write for Fable 5.1's 5-to-60-minute gaps.
- `usage-analyzer` model detection distinguishes Fable/Mythos 5.1 from 5.0 (they cannot share a pricing key now that cache rates diverge) and recognizes `sonnet-4.6` separately from the `sonnet` flagship alias.
- Removed the Bedrock-specific minimum-cacheable-prompt override note for Fable 5.1 -- Anthropic dropped it, so the 512-token floor applies on every platform.
- All pricing re-verified against Anthropic's pricing docs on 2026-09-05; "verified" dates bumped from 2026-07-25.

## [1.11.1] - 2026-08-15

### Security
- **Cleared all 10 open Dependabot alerts.** In `tools/mcp-cost-server` (all four are transitive dependencies of `@modelcontextprotocol/sdk`): `ip-address` 10.2.0 -> 10.5.0 (three SSRF / trust-boundary bypasses -- octal decoding of leading-zero octets, IPv4-mapped/NAT64 misclassification, and a CIDR suffix suppressing special-use classification), `hono` 4.12.31 -> 4.13.2 (CORS ReDoS, language-middleware algorithmic DoS, `memo()` retaining SSR output across requests, and the proxy helper leaking `Connection`-listed headers), `@hono/node-server` 1.19.14 -> 2.1.0 (`serve-static` path traversal on Windows via encoded backslash), and `fast-uri` 3.1.4 -> 4.1.2 (host confusion via backslash authority introducer). In `site`: `react-router` / `react-router-dom` 7.18.1 -> 7.18.2 (RSC-mode CSRF bypass executing actions before the 400 response), plus `nanoid` -> 3.3.18 from an `npm audit fix` in the same pass. `pnpm audit` and `npm audit` both report zero known vulnerabilities.
- **Fixed the root cause behind the mcp-cost-server drift: pnpm 11 silently ignores the `pnpm` field in `package.json`.** The `ip-address` and `hono` overrides added in 1.8.0 lived there, so once the toolchain reached pnpm 11 they stopped applying (pnpm only warns "the following keys were ignored") and the pinned transitive versions rolled back to vulnerable ranges. Moved them to `tools/mcp-cost-server/pnpm-workspace.yaml`, which is the supported home for the setting, raised each floor to the first patched version, and added `fast-uri` and `@hono/node-server`. Verified the overrides now take effect: pnpm rejected the old lockfile with `ERR_PNPM_LOCKFILE_CONFIG_MISMATCH` before regenerating it. Removed the dead `pnpm` block from `package.json` so it cannot mislead again.
- **Closed SonarCloud code-scanning alert #8** (`tssecurity:S8476`, high, "Client-side requests should not be vulnerable to forging attacks") in `site/src/utils/repoAnalyzer.ts`. Request URLs are no longer assembled by string concatenation: `buildApiUrl` now encodes each path segment individually, resolves them against a fixed base with the `URL` constructor, and **drops any request whose parsed `origin` is not `https://api.github.com`** -- a backstop that holds even if a segment smuggles in a scheme or a protocol-relative `//host`. Empty, `.`, and `..` segments are rejected outright. Verified by driving `analyzeRepo` directly with hostile input (`evil.test`, `..`, `a/../../evil`, and a `../../../other` branch): zero off-origin requests were issued, hostile owner/repo values produced no request at all, and the traversal branch fell back to `main`.

### Removed
- Deleted the stray untracked `site/pnpm-lock.yaml`. The site is an npm project -- it tracks `site/package-lock.json` and CI builds it with `npm ci` -- so a second pnpm lockfile would have drifted from the one actually used on the next dependency bump.

## [1.11.0] - 2026-07-25

### Added
- **Claude Opus 5 support** (`claude-opus-5`, GA 2026-07-24) across all pricing tables, guides, tools, templates, and the web calculator. Opus 5 is the new Opus-tier flagship at **$5/$25 per 1M input/output -- exactly what Opus 4.8 cost**, so posted rates do not move. What moves is the shape of the bill: adaptive thinking is **on by default**, reasoning tokens bill as output at $25/1M, and `max_tokens` caps thinking **plus** text. 1M context at standard rates, 128K max output (300K on Batch via beta), cache hit $0.50, 5m-write $6.25, 1h-write $10, Batch $2.50/$12.50. Knowledge cutoff May 2026. Earliest retirement 2027-07-24. Bedrock `anthropic.claude-opus-5` (legacy InvokeModel/Converse: `us.anthropic.claude-opus-5`), Vertex AI `claude-opus-5`.
- **Minimum cacheable prompt length is now first-class, not just prose.** A `cache_control` block on a prefix below the model's floor is silently ignored -- no error, no `cache_creation_input_tokens`, and full input price on every turn. Opus 5 halves the Opus 4.8 floor from 1,024 to **512 tokens**, so prefixes that never cached on 4.8 start caching on 5. Added a 13-model threshold table to guide 01, a 14-row table plus `usage`-field detection to guide 08, a new section to `guides/diagrams.md`, and rows to `CLAUDE.md` and the tool READMEs. The MCP cost server now carries a typed `minCacheTokens` field per model and emits a `cache_warning` when your prefix falls short; the VS Code extension exports `MIN_CACHE_TOKENS` and adds the same note to its CLAUDE.md per-turn report. Haiku 4.5's 4,096 floor is 8x Opus 5's, so a Haiku-first routing tier can quietly pay full price on a prefix that caches fine on Opus.
- **Opus 5 migration guidance** in README and guide 03: `output_config.effort` (defaults `high`) as the primary cost dial, `thinking: {type: "disabled"}` being legal only at effort `high` or below (`xhigh`/`max` + disabled returns 400), cybersecurity classifiers returning `stop_reason: "refusal"` with the server-side `fallbacks` param (beta `server-side-fallback-2026-07-01`) as the recovery path, and beta `mid-conversation-tool-changes-2026-07-01` for changing tool definitions between turns without busting the cache.
- New "The Opus 5 Default-Thinking Effect" (guide 09) and "Opus 5 and the Default-On Thinking Tax" (guide 11) sections: why an unchanged workload costs more on Opus 5 than Opus 4.8 despite identical per-token rates, and which levers claw it back.
- Tool-token overhead figures in guide 07, which previously omitted them entirely: tool-use system prompt 286 (`auto`/`none`) / 406 (`any`/`tool`) on Opus 5, plus the bash and text-editor per-tool costs.

### Changed
- **Fast Mode economics rewritten everywhere -- the 6x tier no longer exists.** Fast Mode is now **Opus 5 and Opus 4.8 only, both at a flat 2x ($10/$50)**. Opus 4.7 **errors** on `speed: "fast"`; Opus 4.6 **silently runs standard** and reports `usage.speed: "standard"` rather than failing, which is the dangerous case -- check that field instead of assuming you got what you paid for. Removed the `fast_mode_legacy` ($30/$150) entry from the token-estimator, deleted the `$5 x 6 = $30.00` row from the diagrams stacking table, and recomputed every figure that was derived from the dead rate (cache-hit floor $3.00 -> $1.00, cache rewrite $37.50 -> $12.50).
- `opus` alias now resolves to **Opus 5** in the site calculator, MCP cost server, VS Code extension, token-estimator, usage-analyzer, and claude-rate. Opus 4.8 is flagged `legacy` and gained its own explicit key (`opus-4.8` / `opus_4_8`) in every tool so a pinned 4.8 can still be priced. `claude-rate` positions Opus 5 as flagship directly after Fable 5.
- Opus 4.8 repositioned from flagship to "previous flagship" -- still the right pin if prompts are tuned to it or you need thinking off at `xhigh`/`max`, and the fallback target for Opus 5 refusals.
- **Corrected two stale figures in `CLAUDE.md`** that predate this release: the bash tool adds **325** tokens on Opus 5 / 4.8 / 4.7 and **244** on Opus 4.6 and earlier (was a flat "+245"), both verified live against Anthropic's bash-tool and tool-use pricing docs on 2026-07-25.
- Added **Sonnet 5** (`claude-sonnet-5`) rows alongside Opus 5: $3/$15 standard with an introductory **$2/$10 through 2026-08-31**, earliest retirement 2027-06-30. Tool tables use the standard rate so projections stay valid past the intro window.
- Mythos Preview moved to past tense (**retired 2026-06-30**); Sonnet 4 and Opus 4 moved to the retired list (2026-06-15). Opus 4.1 is now the next retirement due (2026-08-05) and the only $15/$75 model left.
- `guides/diagrams.md` Mermaid charts rebuilt: Opus 5 and Sonnet 5 nodes added, legacy snapshots restyled, the decision tree gained a cost-sensitive branch pointing at `effort`, and the pricing-modifier stack now shows all three Fast Mode outcomes (2x, error, silent standard).
- usage-analyzer `detect_model()` recognizes `opus-5` / `claude-opus-5` / the Bedrock-prefixed IDs, and distinguishes `opus-4-8` from the generic `opus` catch-all. Its README gained a "Models and Pricing" section -- it previously documented no pricing at all, so code and docs were silently out of sync.
- `CLAUDE.md` sync checklist expanded to name every file carrying a pricing table, including the per-tool sibling READMEs that were being missed.

## [1.10.0] - 2026-07-10

### Added
- **Guide 11: Speed vs Cost** (`guides/11-speed-vs-cost.md`) -- making Claude faster without burning money. Speed levers ranked by cost (cache warmth, shorter context, Haiku/Sonnet routing, `effort` control, then Fast Mode last), Fast Mode economics (2x on Opus 4.8 vs 6x on 4.7/4.6, the OTPS-vs-TTFT caveat, cache-pool invalidation on speed switch, compatibility matrix), deadline math for when the premium pays off, and the Batch API as the inverse lever. Every figure adversarially verified against the repo pricing block.
- **Interactive charts on the Cost Calculator** (`site/src/components/charts.tsx`): per-turn cost curve (line + area, crosshair hover), current-vs-optimized savings breakdown (paired bars with legend), and same-settings-on-other-models comparison (emphasis bars). Hand-rolled SVG, no new dependencies; palette validated for lightness band, chroma, CVD separation, and contrast against the site surface.
- **"How Far Can You Actually Go?" README section** -- per-lever savings table with primary sources (Anthropic prompt caching up to 90%, Batch flat 50%, RouteLLM routing, context management 84%, subscription economics) and the honest caveats separating typical results from stacked ceilings.
- SPA fallback for GitHub Pages (`site/scripts/spa-404.mjs` copies `index.html` to `404.html` at build) so deep links like `/calculator` load directly.

### Changed
- **Headline savings claim reframed from "30-60%" to the "30-90%" band** (30-60% typical for a mixed workload; up to 90% ceiling when every lever stacks against an unoptimized all-Opus baseline) across README, site title/meta/hero, and awesome-list submission entries. Backed by a deep-research pass: 103 agents, 20 sources, 25 claims adversarially verified (2 aggressive community claims refuted and excluded). The cost-mode skill's own claim stays 30-60% -- the skill alone does output reduction and routing hints, not batch/caching/subscription.
- **Calculator, Badge Checker, and Repo Analyzer pages are now routed and live** -- `App.tsx` previously routed every path to the landing page; added routes plus navbar links, and removed the README "Not live yet" notice.
- Guide counts updated to 12 across README, CLAUDE.md, site copy, cheatsheet links, awesome-list PR descriptions (which were stale at 7), and diagrams.md related-guides list.

## [1.9.0] - 2026-06-12

### Added
- **Claude Fable 5 support** (`claude-fable-5`) across all pricing tables, guides, tools, and the web calculator. Fable 5 is Anthropic's most capable widely released model -- a new Mythos-class tier above Opus at **$10/$50 per 1M input/output (2x Opus 4.8)**. 1M context at standard rates, 128K max output, cache hit $1, 5m-write $12.50, 1h-write $20, Batch $5/$25. Always-on adaptive thinking (`thinking: disabled` not supported; depth via `effort`). Safety classifiers can decline requests: HTTP 200 + `stop_reason: "refusal"`, pre-output refusals unbilled, beta `fallbacks` param + fallback credit for retries. No Fast Mode. Requires 30-day data retention. GA 2026-06-09 on Claude API, Claude Platform on AWS, Bedrock (`anthropic.claude-fable-5`), Vertex AI, and Microsoft Foundry.
- **Claude Mythos 5 entry** (`claude-mythos-5`): same specs and pricing as Fable 5 but without the safety classifiers; limited availability to approved Project Glasswing customers. Successor to Mythos Preview. Flagged `inviteOnly` in the site registry (reference tables only, hidden from calculator selection).
- `fable` model alias in token-estimator, usage-analyzer, mcp-cost-server (tool enums + compare output), VS Code extension, and claude-rate cost projections.
- Fable 5 routing guidance: cheatsheet decision tree, guide 03 quick-reference card, guide 10 "Tier 2+" block, cost-mode skill model-routing table (downshift suggestion when running routine work on Fable 5), calculator and usage-analyzer recommendations for Fable-heavy usage.

### Changed
- **Mythos Preview marked retiring 2026-06-30** (announced with the Mythos 5 launch) -- lifecycle flipped to `legacy`, pricing rows annotated, retirement tables updated across README, cheatsheet, and CLAUDE.md. The token-estimator `mythos` alias now prices Mythos 5 ($10/$50) instead of Mythos Preview ($25/$125).
- Opus 4.8 repositioned from "most capable model" to "Opus-tier flagship" in copy across README, cheatsheet, guides, and the site registry; "most capable" now refers to Fable 5.
- usage-analyzer model detection extended: recognizes `fable`/`mythos` and distinguishes `opus-4.7` / `opus-4.6` from the `opus` alias; the Opus-share hotspot check now matches all Opus variants.
- All pricing references re-verified against Anthropic docs on 2026-06-12; "verified" dates bumped from 2026-06-06.
- Plugin-identity versions bumped to 1.9.0; plugin distribution copy of the cost-mode skill re-synced.

## [1.8.0] - 2026-06-06

### Added
- **Claude Opus 4.8 support** (`claude-opus-4-8`) across all pricing tables, guides, tools, and the web calculator. Opus 4.8 is Anthropic's new flagship and most capable model at $5/$25 per 1M input/output (same posted price as Opus 4.7 / 4.6). 1M context at standard rates (200K on Microsoft Foundry), 128K max output, adaptive thinking only, `effort` defaults to `high` on all surfaces, knowledge cutoff Jan 2026. Earliest retirement 2027-05-28. Bedrock ID `anthropic.claude-opus-4-8`.
- **Per-model Fast Mode pricing.** Promoted the single `FAST_MODE_MULTIPLIER` constant to a per-model `fastModeMultiplier` field on `ModelPricing` (site) and per-model entries in the standalone tool tables. Opus 4.8 Fast Mode is **2x** ($10/$50); Opus 4.7 / 4.6 remain **6x** ($30/$150). Opus 4.6 Fast Mode is deprecated as of the 4.8 launch (removed ~30 days later, then falls back to standard speed). Opus 4.8 Fast Mode is Claude API + Managed Agents only.
- `opus-4-7` model entry in `site/src/utils/pricing.ts` and the standalone tool tables.

### Changed
- **Default `opus` alias now resolves to Opus 4.8** in the site calculator, MCP cost server, VS Code extension, token-estimator, usage-analyzer, and claude-rate. Opus 4.7 / 4.6 / 4.5 and Sonnet 4.5 are now flagged `legacy`.
- Renamed the site `ModelId` `opus-legacy` key to `opus-4-6` and added an explicit `opus-4-7` entry; the Fast Mode UI label and savings recommendation are now computed from the per-model multiplier instead of a hardcoded "6x / 83%".
- Per-model tool-use system-prompt overhead documented in CLAUDE.md (Opus 4.8 = 290/410, Opus 4.7 = 675/804, Opus 4.6 + Sonnet 4.6 = 497/589) -- replaces the stale flat "346 / 313 tokens".
- Batch API extended-output note added (up to 300K output on Opus 4.8/4.7/4.6 + Sonnet 4.6 via `output-300k-2026-03-24`).
- Opus 4.1 marked deprecated with a firm 2026-08-05 retirement date (announced 2026-06-05). Migration targets across README + cheatsheet updated to Opus 4.8.
- All pricing references re-verified against Anthropic docs on 2026-06-06; "verified" dates bumped from 2026-05-22.
- **Reconciled plugin-identity versions to 1.8.0.** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and `plugins/cost-mode/.codex-plugin/plugin.json` were stuck at 1.5.0 while the changelog had advanced to 1.7.0 -- bumped all three to match this release.

### Security
- **Updated `react-router-dom` to 7.17.0** in `site/` (was resolving to 7.14.0), clearing 3 Dependabot alerts: turbo-stream deserialization RCE (high), `__manifest` DoS (high), and protocol-relative open redirect (moderate).
- **Updated transitive `hono` to 4.12.23 and `qs` to 6.15.2** in `tools/mcp-cost-server/` (via `pnpm update`, both within existing semver ranges), clearing 5 Dependabot alerts: Set-Cookie injection, mount-prefix routing, IPv6 deny-rule bypass, JWT scheme acceptance (all moderate), and `qs.stringify` DoS (moderate). `npm audit` and `pnpm audit` both report 0 vulnerabilities.

## [1.7.0] - 2026-05-22

### Added
- **`claude-rate` CLI** at `tools/claude-rate/`. Local rater that scans a project directory and grades the Claude/AI setup across 7 categories (CLAUDE.md size discipline, .claudeignore coverage, settings.json model+budget+permissions, MCP server count, hooks, security/secrets hygiene, optimizer tooling). Returns 0-100 score, A+ to F letter grade, per-category breakdown with text bar charts, monthly-cost projection on every active model tier, copy-pasteable fix suggestions, and a shields.io badge URL.
  - **Three runners**: `npx -y @sagargupta16/claude-rate .`, `curl | sh` one-shot, persistent `curl | sh -- --install`. Plus direct `python rate.py`.
  - **Stdlib only** (Python 3.10+). No `pip install` needed for the rater itself.
  - **Flags**: `--fix` (copy-pasteable fix list), `--strict` (CI gate, exits 1 below grade B), `--json` (machine-readable output), `--version`.
  - **Why local?** Inspects things the deployed web analyzer can't see: real MCP server count from `.mcp.json`, hooks in settings.json, .claudeignore coverage gaps vs files actually on disk, accidentally-committed secrets (`sk-...`, `AKIA...`, `ghp_...`), missing `.env` entries in `.gitignore`, cost-mode skill installation status, custom slash command count.
  - Files: `tools/claude-rate/rate.py` (single-file Python CLI), `tools/claude-rate/bin/claude-rate.js` (npx shim that locates Python and forwards args), `tools/claude-rate/install.sh` (POSIX one-shot/persistent installer), `tools/claude-rate/package.json` (npm distribution metadata), `tools/claude-rate/README.md` (full docs with example output and CI snippet).
- **README "Rate your setup" section** -- new top-level entry point. Local `claude-rate` is the recommended path; web tools (analyzer, calculator, badge) remain available for browser-only / public-repo flows.
- **Legacy & Retired Models section** in README. Self-contained migration reference covering recently-retired models (Opus 3, Sonnet 3.7, Haiku 3 / 3.5, Sonnet 3.5 v1/v2, Sonnet 3, Claude 2.x, Claude 1.x, Instant 1.x), deprecated-soon models (Sonnet 4 / Opus 4 retiring 2026-06-15), still-callable older snapshots (Opus 4.5, Opus 4.1, Sonnet 4.5), and historical pricing patterns no longer in effect (the obsolete "2x over 200K" long-context premium, single-endpoint Bedrock, ARN-versioned-only model IDs). Cheatsheet got an expanded version of this in 1.6.0; this PR adds it to README too with last-known pricing for every retired tier.
- `tools/README.md` quick-reference table updated to lead with `claude-rate` as the recommended starting point.

## [1.5.0] - 2026-05-20

### Added
- Added repository-level `SECURITY.md` and `.github/pull_request_template.md` to align with community standard practices.

### Changed
- Resolved 3-way version drift across repository files, standardizing on version 1.5.0.

### Fixed
- Fixed uncommitted `CLAUDE.md` duplicate H1 header by merging headers and keeping the stacking blockquote intact.

## [1.4.0] - 2026-04-17

### Added
- **Claude Opus 4.7 support** across all tools, guides, pricing tables, and the web calculator. Opus 4.7 is Anthropic's current flagship (April 2026) at $5/$25 per 1M input/output -- same posted pricing as legacy Opus 4.6.
- **Claude Mythos Preview entry** in pricing tables, token-estimator, and the site's model registry. $25/$125 per MTok. Invite-only via [Project Glasswing](https://anthropic.com/glasswing) for defensive cybersecurity research. Added `inviteOnly` flag on ModelPricing so Mythos appears in reference tables but is filtered out of the calculator/analyzer selection UIs.
- `opus-legacy` model option in site/src/utils/pricing.ts (maps to Opus 4.6) to keep Fast Mode accessible for users who need it.
- `fastModeCapable` flag on ModelPricing type; calculator now scopes Fast Mode UI to the model that actually supports it (Opus 4.6) instead of hardcoding to `model === 'opus'`.
- Tokenizer overhead warning: Opus 4.7 introduced a new tokenizer that may use up to 35% more tokens for the same source text. Guides now recommend budgeting 20-35% higher for Opus 4.7 tasks vs Opus 4.6.
- Bedrock model ID reference table in guides/06 (includes `us.anthropic.claude-opus-4-7` cross-region profile + research-preview caveat).
- New Mermaid diagrams in guides/diagrams.md: "Claude Model Family (April 2026)" showing all GA + research-preview models with cost tiers, and "Pricing Modifier Stack" showing how cache/batch/regional/fast-mode multipliers compose.
- **Thinking modes table** in cheatsheet: clarifies Opus 4.7 uses adaptive thinking only (no extended thinking), Sonnet 4.6 supports both, Haiku 4.5 is extended-only.
- **Upcoming retirements table** in cheatsheet and README: Haiku 3 retires 2026-04-20 (corrected from April 19 in 1.6.0), Sonnet 4 / Opus 4 retire 2026-06-15.
- Published benchmark numbers (CyberGym, SWE-bench Verified/Pro, Terminal-Bench) in guides/03 comparing Opus 4.6 vs Mythos Preview.

### Changed
- **1M context pricing corrected**: Opus 4.7, Opus 4.6, and Sonnet 4.6 now bill the full 1M window at **standard per-token rates**. The earlier "2x input, 1.5x output over 200K" documentation was obsolete and applied only to Opus 4.1 and older. Removed the "Long Context Threshold Trap" anti-pattern section since it no longer applies.
- All pricing tables updated to April 2026 (was March 2026).
- `Max Output` column for Opus updated to 128K (was incorrectly listed as 32K).
- Default `opus` alias in the site calculator now refers to Opus 4.7; the calculator surface supports both.
- Regional endpoint +10% premium clarified to apply specifically to Sonnet 4.5+ and Haiku 4.5+ (global pricing structure changed with that generation).
- Data residency +10% multiplier clarified as `inference_geo: us-only` on Opus 4.7 and newer, not a blanket "Opus and above" rule.

### Fixed
- Token estimator Python CLI: removed obsolete `opus_4.6_1m` entry; added legacy `opus_4_6` explicitly.
- Cheatsheet: corrected max output per turn values and the historical Haiku-to-Opus cost ratio explanation.
- Benchmarks headers now include explicit "measured on Opus 4.6" note since Opus 4.7 benchmarks are not yet collected.
- **Comprehensive factual sweep**: updated every remaining "Opus 4.6" default-recommendation reference to "Opus 4.7" across guides/09-subscription-value.md (plan model lineup, allowance table, Batch API table), guides/08-prompt-caching.md (cache pricing table), guides/06-access-methods-pricing.md ("stay under 200K" tip rewritten for current standard-rate 1M context, March→April 2026 date), benchmarks/context-size-impact.md (file read budget table, context window reference), benchmarks/model-comparison.md (decision tree, recommendation labels), and benchmarks/leaderboard.md (pricing note).
- **Diagrams rewritten** (guides/diagrams.md): replaced `\n` line breaks with `<br/>` inside quoted labels (GitHub renders these correctly, `\n` showed as literal text), dropped inline `<b>` tags that GitHub's sanitizer strips, switched from inline `style` to `classDef` + `class` syntax, wrapped model groupings in `subgraph` blocks for proper boxed regions. All 5 diagrams validated via `@mermaid-js/mermaid-cli@11.12.0`.
- **Issue templates** (`.github/ISSUE_TEMPLATE/leaderboard-entry.md`, `case-study.md`): added Opus 4.7 option.
- **Case study template** (`case-studies/TEMPLATE.md`): added Opus 4.7 to example model list.
- **Context size benchmark**: corrected the "200K token context window" claim to reflect that Opus 4.7/4.6/Sonnet 4.6 are 1M and Haiku 4.5 is 200K.

## [1.3.0] - 2026-04-06

### Added
- **Installable cost-mode skill**: `npx skills add Sagargupta16/claude-cost-optimizer` then `/cost-mode`
- Plugin structure (.claude-plugin/, plugins/, skills/, .agents/) for Claude Code marketplace
- Three intensity levels for cost-mode: lite (20-40% output reduction), standard (40-60%), strict (60-70%)
- Guide 00: Getting Started in 5 Minutes -- zero to optimized in 5 steps
- Guide 10: Three-Tier Task Routing -- skip LLM for Tier 0, Haiku for Tier 1, Opus for Tier 2
- Repo Analyzer page -- paste a GitHub URL to get full cost audit, grade, and recommendations
- "Try it on our repo" prefilled demo on Analyzer page
- cost-logger.sh hook -- logs estimated tokens and cost per tool call
- Output Token Optimization section in cheatsheet (5 strategies + arXiv reference)
- Community Tools section in README referencing caveman project
- Before/after cost comparison example in README (61% savings)
- Star History chart in README with dark/light mode support
- SEO meta tags (Open Graph, Twitter Card, canonical URL, keywords)
- tools/README.md with quick reference table
- GitHub Discussions enabled on the repository

### Changed
- Repo transformed from docs-only to installable skill + docs
- README install command featured at the top
- Home page hero links to Repo Analyzer
- Repo Analyzer shows results for repos with no config files (was showing error)
- Cheatsheet links table updated with all new guides and tools
- CLAUDE.md updated with new file structure and skill directories
- Home page guide count updated to 10

## [1.2.0] - 2026-04-03

### Added
- Guide 08: Prompt Caching Deep Dive - cache mechanics, TTL economics, ROI math
- Guide 09: Maximizing Subscription Value - plan comparison, upgrade/downgrade signals
- Visual decision tree diagrams (Mermaid) for model selection, session optimization, cost tiers
- React site (Vite + React 19 + TypeScript) with cost calculator and badge checker for GitHub Pages
- MCP cost estimation server with estimate_cost, session_estimate, compare_models tools
- Claude Code budget enforcement hooks (budget-tracker, session-summary)
- Efficiency badge generator (A+ to F grading, shields.io badge output)
- VS Code extension for token count and cost estimation in status bar
- GitHub Action for automated cost auditing on PRs
- /optimize custom command for project cost-efficiency analysis
- Case studies directory with submission template and issue template
- Community benchmark leaderboard with seed data
- 5 new stack-specific CLAUDE.md templates: Go, Rust, Django, Rails, Java Spring Boot
- Leaderboard entry issue template
- Case study issue template
- Awesome-list submission preparation guide
- GitHub Pages deployment workflow (deploy-site.yml)
- Issue template config with quick-link cards

### Changed
- Simplified CONTRIBUTING.md with contribution ladder (Level 1-6) and "Your First PR in 5 Steps"
- Updated CLAUDE.md file size guidance with precise limits (4K chars/file, 12K total) based on community research
- Updated compaction docs with thresholds (10K tokens trigger, 4 messages preserved)
- Updated prompt caching guide with static/dynamic boundary explanation
- Updated hooks with correct JSON payload format and exit code semantics
- Updated cheatsheet with 7 new entries (character limits, compaction, output caps, token estimation)
- Cleaned up duplicate calculator files (replaced vanilla JS with React site)

## [1.1.0] - 2026-03-16

- Add regional pricing, PPP note, and cloud discount info
- Add off-peak 2x usage documentation
- Update 1M context from beta to native, add README badges

## [1.0.0] - 2026-03-08

- Add 1M context pricing, Fast Mode, and access methods guide
- Update all pricing to March 2026 (Opus 4.6, Haiku 4.5)
- Initial release: Claude Cost Optimizer
