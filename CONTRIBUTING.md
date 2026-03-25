# Contributing to Claude Cost Optimizer

Thank you for your interest in helping others save money on Claude Code. Contributions of all kinds are welcome, from quick tips to detailed benchmarks.

## Ways to Contribute

### Share a Cost-Saving Tip
Found a technique that reduced your Claude costs? Open an issue using the [Tip Submission](/.github/ISSUE_TEMPLATE/tip-submission.md) template. Include expected savings, effort level, and any evidence you have.

### Submit Benchmark Results
Ran a cost comparison test? Submit your findings using the [Benchmark Result](/.github/ISSUE_TEMPLATE/benchmark-result.md) template. Reproducible benchmarks with clear methodology are especially valuable.

### Add or Improve Templates
- Submit a CLAUDE.md template for a stack or framework not yet covered.
- Improve existing templates based on real-world testing.
- Add new Claude Code command templates for common workflows.

### Build a Tool
The `tools/` directory contains Python utilities for cost estimation and analysis. Contributions that extend or improve these tools are welcome. New tool ideas are also encouraged - open an issue to discuss before building.

### Improve the Guides
- Fix errors, typos, or outdated information.
- Add examples, diagrams, or clarifications.
- Expand sections that are too brief.
- Update pricing data when Anthropic changes rates.

## Pull Request Guidelines

1. **Fork the repository** and create your branch from `main`.
2. **Keep changes focused.** One PR per topic. Don't bundle unrelated changes.
3. **Test your contributions.** For tools, verify they run without errors. For templates, test them in a real project if possible.
4. **Update related files.** If your change affects the README, cheatsheet, or other docs, update them too.
5. **Write a clear PR description.** Explain what you changed and why.

## Markdown Style Guide

This project is primarily documentation. Consistent formatting matters.

- **Headings**: Use `##` for major sections, `###` for subsections. Don't skip levels.
- **Tables**: Preferred over bullet lists for comparisons and structured data.
- **Code blocks**: Always specify the language (```bash, ```python, ```json).
- **Links**: Use relative paths for internal links (`guides/02-context-optimization.md`, not full URLs).
- **Line length**: No strict limit, but aim for readability. One sentence per line is fine.
- **Numbers**: Use specific numbers and percentages, not vague claims. "Saves 30-50%" is better than "saves a lot."
- **Tone**: Direct and practical. Write for developers who want to save money, not for marketing.

## Python Code Style

For tools in the `tools/` directory:

- Target Python 3.10+.
- Follow PEP 8.
- Use type hints for function signatures.
- Include docstrings for modules and public functions.
- Minimize dependencies. Prefer the standard library.
- Handle errors gracefully with clear, user-facing messages.
- Include argparse with help text and usage examples.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you agree to uphold a respectful and inclusive environment for everyone.

In short: be kind, be constructive, and assume good intentions.

## Questions?

Open an issue with the question label. There are no bad questions when it comes to understanding Claude costs.
