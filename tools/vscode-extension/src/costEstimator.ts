/**
 * Cost estimation logic for Claude API token counts and pricing.
 *
 * Token estimation uses character-based heuristics rather than a real
 * tokenizer. This keeps the extension dependency-free and fast, at the
 * cost of ~10-15% accuracy variance compared to the actual BPE tokenizer.
 */

export interface CostBreakdown {
  tokens: number;
  inputCostPerTurn: number;
  outputEstimatePerTurn: number;
  totalPerTurn: number;
  totalForSession: number;
  turns: number;
  model: string;
}

/** Per-1M-token pricing as of April 2026. */
export const PRICING: Record<string, { input: number; output: number }> = {
  opus: { input: 5, output: 25 },
  "opus-4.6": { input: 5, output: 25 },
  sonnet: { input: 3, output: 15 },
  haiku: { input: 1, output: 5 },
};

/** Friendly display names for each model tier. */
export const MODEL_LABELS: Record<string, string> = {
  opus: "Opus 4.7",
  "opus-4.6": "Opus 4.6 (legacy)",
  sonnet: "Sonnet 4.6",
  haiku: "Haiku 4.5",
};

/**
 * Estimate token count from raw text.
 *
 * Heuristic: code averages ~4 characters per token, prose averages ~3.5.
 * We detect "code-like" content by checking for common syntax characters
 * and adjust the ratio accordingly.
 */
export function estimateTokens(text: string): number {
  if (text.length === 0) {
    return 0;
  }

  const codeIndicators = /[{}();=<>\[\]|&^%$#@!~`]/g;
  const matches = text.match(codeIndicators);
  const codeRatio = matches ? matches.length / text.length : 0;

  // Blend between prose (3.5 chars/token) and code (4.0 chars/token)
  const charsPerToken = 3.5 + codeRatio * 2.5; // caps at ~4.5 for very dense code
  const clampedCharsPerToken = Math.min(Math.max(charsPerToken, 3.5), 4.5);

  return Math.ceil(text.length / clampedCharsPerToken);
}

/**
 * Calculate cost in USD for a given token count, model, and direction.
 */
export function calculateCost(
  tokens: number,
  model: string,
  direction: "input" | "output"
): number {
  const pricing = PRICING[model];
  if (!pricing) {
    return 0;
  }
  const ratePerMillion = direction === "input" ? pricing.input : pricing.output;
  return (tokens / 1_000_000) * ratePerMillion;
}

/**
 * Estimate the per-turn cost of including a CLAUDE.md file in context.
 *
 * CLAUDE.md is sent as input on every turn. This function estimates how
 * much that adds to a session of N turns, plus a rough output estimate
 * (assuming ~500 output tokens per turn on average).
 */
export function estimatePerTurnCost(
  claudeMdText: string,
  turns: number,
  model: string
): CostBreakdown {
  const tokens = estimateTokens(claudeMdText);
  const inputCostPerTurn = calculateCost(tokens, model, "input");

  // Rough average output per turn -- 500 tokens covers a typical response
  const avgOutputTokens = 500;
  const outputEstimatePerTurn = calculateCost(avgOutputTokens, model, "output");

  const totalPerTurn = inputCostPerTurn + outputEstimatePerTurn;
  const totalForSession = inputCostPerTurn * turns + outputEstimatePerTurn * turns;

  return {
    tokens,
    inputCostPerTurn,
    outputEstimatePerTurn,
    totalPerTurn,
    totalForSession,
    turns,
    model,
  };
}

/**
 * Format a USD cost for display.
 * Shows 4 decimal places for sub-cent values, 2 otherwise.
 */
export function formatCost(cost: number): string {
  if (cost < 0.01) {
    return `$${cost.toFixed(4)}`;
  }
  return `$${cost.toFixed(2)}`;
}

/**
 * Format a token count with thousands separators.
 */
export function formatTokens(tokens: number): string {
  return tokens.toLocaleString("en-US");
}
