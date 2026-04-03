# Contributing

Every contribution helps developers save money on Claude Code. Whether you star the repo, file an issue, or submit a PR -- it all counts.

## Contribution Ladder

Pick your comfort level and jump in.

| Level | What to do | Time needed |
|-------|-----------|-------------|
| 1 | Star the repo, share it with your team | 10 seconds |
| 2 | Open an issue with a tip, bug report, or question | 5 minutes |
| 3 | Submit a benchmark or case study via issue template | 15 minutes |
| 4 | Fix a typo or improve wording in a guide (PR) | 10 minutes |
| 5 | Add a CLAUDE.md template for a new stack (PR) | 30 minutes |
| 6 | Build a tool or write a new guide (PR) | 1+ hours |

Most contributions start at Level 2. You don't need to write code to help.

## Open an Issue (No Code Required)

The fastest way to contribute:

- **Share a tip** -- Found a way to cut costs? [Open a tip submission](https://github.com/Sagargupta16/claude-cost-optimizer/issues/new?template=tip-submission.md). Even one sentence is useful.
- **Report a bug or error** -- Spot wrong pricing, a broken link, or bad advice? Open an issue. No template needed.
- **Submit benchmarks** -- Ran a cost comparison? [Submit your numbers](https://github.com/Sagargupta16/claude-cost-optimizer/issues/new?template=benchmark-result.md) so others can learn from your data.
- **Share your story** -- Reduced your Claude costs on a real project? [Tell us how](https://github.com/Sagargupta16/claude-cost-optimizer/issues/new?template=case-study.md).
- **Ask a question** -- Not sure about something? Open an issue with the "question" label.

## Your First PR in 5 Steps

Never submitted a PR before? Follow these exact commands:

```bash
# 1. Fork the repo on GitHub (click the Fork button), then clone your fork
git clone https://github.com/YOUR-USERNAME/claude-cost-optimizer.git
cd claude-cost-optimizer

# 2. Create a branch
git checkout -b my-fix

# 3. Make your changes (edit files, fix typos, add content)

# 4. Commit your changes
git add the-file-you-changed.md
git commit -m "fix: correct pricing in caching guide"

# 5. Push and open a PR
git push origin my-fix
# Then go to your fork on GitHub and click "Compare & pull request"
```

That's it. We'll review it and help you get it merged.

## What We're Looking For Right Now

If you want to help but don't know where to start, here are specific things we need:

- **CLAUDE.md templates** for: Django, Rails, Spring Boot, Go, Rust, Flutter, Svelte, Vue, Angular
- **Benchmark data** comparing costs between Opus, Sonnet, and Haiku for real tasks
- **Case studies** from teams that reduced costs by 30%+ on production projects
- **Pricing corrections** if any numbers in the guides are outdated
- **Tool improvements** to the token estimator or usage analyzer in `tools/`
- **Typo fixes and wording improvements** in any guide -- always welcome

## PR Guidelines

1. Create your branch from `main`.
2. One PR per topic. Don't bundle unrelated changes.
3. Write a short description of what you changed and why.
4. If you change pricing data, update it everywhere (README, guides, cheatsheet, benchmarks).
5. For tools, verify they run without errors before submitting.

## Style Quick Reference

### Markdown

| Rule | Example |
|------|---------|
| Headings | `##` for sections, `###` for subsections, don't skip levels |
| Data | Use tables over bullet lists for comparisons |
| Code blocks | Always tag the language: ` ```bash `, ` ```python `, ` ```json ` |
| Links | Relative paths for internal links: `guides/02-context-optimization.md` |
| Numbers | Be specific: "saves 30-50%" not "saves a lot" |
| Tone | Direct and practical, not marketing copy |

### Python (for tools)

| Rule | Detail |
|------|--------|
| Version | Python 3.10+ |
| Style | PEP 8, type hints on function signatures |
| Docs | Docstrings on modules and public functions |
| Deps | Standard library preferred, minimize external packages |
| CLI | Use argparse with help text |
| Errors | Handle gracefully with clear user-facing messages |

## Code of Conduct

Be kind, be constructive, assume good intentions. This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## Questions?

Open an issue. There are no bad questions when it comes to understanding Claude costs.
