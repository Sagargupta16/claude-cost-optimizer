#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// -------------------------------------------------------------------
// Pricing tables -- verified 2026-07-25
// -------------------------------------------------------------------

interface ModelPricing {
  inputPerMillion: number;
  outputPerMillion: number;
  cacheHitPerMillion: number;
  /** Prefixes shorter than this are silently not cached (no error, full input price). */
  minCacheTokens: number;
}

const PRICING: Record<string, ModelPricing> = {
  // "fable" = Fable 5, the most capable widely released model (2x Opus 5 rates)
  fable: { inputPerMillion: 10, outputPerMillion: 50, cacheHitPerMillion: 1, minCacheTokens: 512 },
  // "opus" alias maps to the Opus-tier flagship (Opus 5, GA 2026-07-24)
  opus: { inputPerMillion: 5, outputPerMillion: 25, cacheHitPerMillion: 0.5, minCacheTokens: 512 },
  "opus-4.8": { inputPerMillion: 5, outputPerMillion: 25, cacheHitPerMillion: 0.5, minCacheTokens: 1024 },
  "opus-4.7": { inputPerMillion: 5, outputPerMillion: 25, cacheHitPerMillion: 0.5, minCacheTokens: 2048 },
  "opus-4.6": { inputPerMillion: 5, outputPerMillion: 25, cacheHitPerMillion: 0.5, minCacheTokens: 4096 },
  // "sonnet" alias maps to the current Sonnet-tier flagship (Sonnet 5); same $3/$15 tier as Sonnet 4.6
  sonnet: { inputPerMillion: 3, outputPerMillion: 15, cacheHitPerMillion: 0.3, minCacheTokens: 1024 },
  haiku: { inputPerMillion: 1, outputPerMillion: 5, cacheHitPerMillion: 0.1, minCacheTokens: 4096 },
};

const MODEL_IDS = Object.keys(PRICING);
const UNKNOWN_MODEL_HINT = `Use one of: ${MODEL_IDS.join(", ")} ("opus" is Opus 5, "sonnet" is Sonnet 5).`;

// -------------------------------------------------------------------
// Helpers
// -------------------------------------------------------------------

/** Rough token estimate: ~4 characters per token. */
function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

function costForTokens(tokens: number, ratePerMillion: number): number {
  return (tokens / 1_000_000) * ratePerMillion;
}

function formatUsd(amount: number): string {
  return `$${amount.toFixed(4)}`;
}

function pctSaving(base: number, other: number): string {
  if (base === 0) return "0%";
  return `${(((base - other) / base) * 100).toFixed(1)}%`;
}

// -------------------------------------------------------------------
// Tool implementations
// -------------------------------------------------------------------

function estimateCost(args: {
  text: string;
  model?: string;
  turns?: number;
}): object {
  const model = (args.model ?? "sonnet").toLowerCase();
  const pricing = PRICING[model];
  if (!pricing) {
    return { error: `Unknown model "${args.model}". ${UNKNOWN_MODEL_HINT}` };
  }

  const tokens = estimateTokens(args.text);
  const inputCost = costForTokens(tokens, pricing.inputPerMillion);
  const outputEstimate = Math.ceil(tokens * 0.3); // rough output assumption
  const outputCost = costForTokens(outputEstimate, pricing.outputPerMillion);
  const singlePassCost = inputCost + outputCost;

  const result: Record<string, unknown> = {
    model,
    estimated_tokens: tokens,
    input_cost: formatUsd(inputCost),
    estimated_output_tokens: outputEstimate,
    output_cost: formatUsd(outputCost),
    single_pass_total: formatUsd(singlePassCost),
  };

  if (tokens < pricing.minCacheTokens) {
    result.cache_warning = `~${tokens} tokens is below the ${pricing.minCacheTokens}-token minimum cacheable prompt for "${model}". A cache_control block on a prefix this short is silently ignored: no error, no cache_creation_input_tokens, and full input price on every turn.`;
  }

  if (args.turns && args.turns > 1) {
    // Each turn re-sends conversation history, which grows cumulatively.
    // Assume ~70% cache hit rate on stable content.
    let totalCost = 0;
    for (let t = 1; t <= args.turns; t++) {
      const historyTokens = tokens + (t - 1) * 1500;
      const cachedTokens = Math.floor(historyTokens * 0.7);
      const freshTokens = historyTokens - cachedTokens;
      const turnInputCost =
        costForTokens(freshTokens, pricing.inputPerMillion) +
        costForTokens(cachedTokens, pricing.cacheHitPerMillion);
      const turnOutputCost = costForTokens(500, pricing.outputPerMillion);
      totalCost += turnInputCost + turnOutputCost;
    }
    result.projected_turns = args.turns;
    result.projected_total_cost = formatUsd(totalCost);
  }

  return result;
}

function sessionEstimate(args: {
  turns: number;
  model?: string;
  claude_md_lines?: number;
  mcp_servers?: number;
}): object {
  const model = (args.model ?? "sonnet").toLowerCase();
  const pricing = PRICING[model];
  if (!pricing) {
    return { error: `Unknown model "${args.model}". ${UNKNOWN_MODEL_HINT}` };
  }

  const turns = args.turns;
  const claudeMdTokens = (args.claude_md_lines ?? 0) * 7;
  const mcpSchemaTokens = (args.mcp_servers ?? 0) * 1500;
  const systemPromptTokens = 3500;

  // Stable tokens (loaded every turn, eligible for caching)
  const stableTokens = systemPromptTokens + claudeMdTokens + mcpSchemaTokens;

  const cacheHitRate = 0.7;
  let totalInputCost = 0;
  let totalOutputCost = 0;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;

  for (let t = 1; t <= turns; t++) {
    const historyTokens = (t - 1) * 1500; // cumulative conversation growth
    const turnInputTokens = stableTokens + historyTokens;

    const cachedTokens = Math.floor(stableTokens * cacheHitRate);
    const freshTokens = turnInputTokens - cachedTokens;

    const turnInputCost =
      costForTokens(freshTokens, pricing.inputPerMillion) +
      costForTokens(cachedTokens, pricing.cacheHitPerMillion);
    const turnOutputTokens = 500;
    const turnOutputCost = costForTokens(turnOutputTokens, pricing.outputPerMillion);

    totalInputCost += turnInputCost;
    totalOutputCost += turnOutputCost;
    totalInputTokens += turnInputTokens;
    totalOutputTokens += turnOutputTokens;
  }

  const totalCost = totalInputCost + totalOutputCost;

  const recommendations: string[] = [];
  if (claudeMdTokens > 2000) {
    recommendations.push(
      `CLAUDE.md contributes ~${claudeMdTokens} tokens/turn. Consider trimming to reduce per-turn cost.`
    );
  }
  if ((args.mcp_servers ?? 0) > 3) {
    recommendations.push(
      `${args.mcp_servers} MCP servers add ~${mcpSchemaTokens} tokens/turn in schema overhead. Disable unused servers.`
    );
  }
  if (turns > 20) {
    recommendations.push(
      "Sessions over 20 turns accumulate significant history cost. Consider starting a fresh session for new tasks."
    );
  }
  if (stableTokens < pricing.minCacheTokens) {
    recommendations.push(
      `The stable prefix is only ~${stableTokens} tokens, below the ${pricing.minCacheTokens}-token minimum cacheable prompt for "${model}". Caching is silently skipped at that size, so these figures assume no cache discount is actually applied.`
    );
  }
  if (model === "fable") {
    recommendations.push(
      "Fable 5 costs 2x Opus 5 ($10/$50 vs $5/$25). Reserve it for the hardest reasoning; route routine work to Opus or Sonnet."
    );
  }
  if (model === "opus") {
    recommendations.push(
      "Opus 5 has adaptive thinking on by default, and reasoning tokens bill as output. Lower output_config.effort for routine turns, or set thinking to disabled (legal only at effort high or below)."
    );
    recommendations.push(
      "Switching to Sonnet for routine tasks saves ~40% with comparable quality for most coding work."
    );
  }

  return {
    model,
    turns,
    breakdown: {
      system_prompt_tokens: systemPromptTokens,
      claude_md_tokens_per_turn: claudeMdTokens,
      mcp_schema_tokens_per_turn: mcpSchemaTokens,
      avg_history_tokens_per_turn: Math.round(((turns - 1) * 1500) / 2),
      output_tokens_per_turn: 500,
    },
    totals: {
      total_input_tokens: totalInputTokens,
      total_output_tokens: totalOutputTokens,
      input_cost: formatUsd(totalInputCost),
      output_cost: formatUsd(totalOutputCost),
      total_cost: formatUsd(totalCost),
    },
    recommendations,
  };
}

function compareModels(args: {
  input_tokens: number;
  output_tokens: number;
}): object {
  const { input_tokens, output_tokens } = args;

  const results: Record<
    string,
    { input_cost: string; output_cost: string; total: string; total_raw: number }
  > = {};

  for (const [name, pricing] of Object.entries(PRICING)) {
    const ic = costForTokens(input_tokens, pricing.inputPerMillion);
    const oc = costForTokens(output_tokens, pricing.outputPerMillion);
    results[name] = {
      input_cost: formatUsd(ic),
      output_cost: formatUsd(oc),
      total: formatUsd(ic + oc),
      total_raw: ic + oc,
    };
  }

  // Determine cheapest
  const sorted = Object.entries(results).sort(
    ([, a], [, b]) => a.total_raw - b.total_raw
  );
  const cheapest = sorted[0][0];
  const mostExpensive = sorted[sorted.length - 1];

  const comparison = Object.fromEntries(
    Object.entries(results).map(([name, data]) => [
      name,
      {
        input_cost: data.input_cost,
        output_cost: data.output_cost,
        total: data.total,
      },
    ])
  );

  return {
    input_tokens,
    output_tokens,
    comparison,
    cheapest_model: cheapest,
    savings_vs_most_expensive: pctSaving(
      mostExpensive[1].total_raw,
      sorted[0][1].total_raw
    ),
  };
}

// -------------------------------------------------------------------
// MCP Server setup
// -------------------------------------------------------------------

const server = new Server(
  { name: "cost-estimator", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "estimate_cost",
      description:
        "Estimate token count and cost for a given text. Optionally project cost over multiple turns.",
      inputSchema: {
        type: "object" as const,
        properties: {
          text: {
            type: "string",
            description: "The text to estimate tokens for",
          },
          model: {
            type: "string",
            enum: MODEL_IDS,
            description:
              'Claude model (default: sonnet). "opus" is Opus 5, "sonnet" is Sonnet 5.',
          },
          turns: {
            type: "number",
            description:
              "Number of conversation turns to project cost over (optional)",
          },
        },
        required: ["text"],
      },
    },
    {
      name: "session_estimate",
      description:
        "Estimate total cost for a Claude Code session based on turn count, CLAUDE.md size, and MCP server count.",
      inputSchema: {
        type: "object" as const,
        properties: {
          turns: {
            type: "number",
            description: "Number of conversation turns",
          },
          model: {
            type: "string",
            enum: MODEL_IDS,
            description:
              'Claude model (default: sonnet). "opus" is Opus 5, "sonnet" is Sonnet 5.',
          },
          claude_md_lines: {
            type: "number",
            description: "Number of lines in your CLAUDE.md file (default: 0)",
          },
          mcp_servers: {
            type: "number",
            description: "Number of configured MCP servers (default: 0)",
          },
        },
        required: ["turns"],
      },
    },
    {
      name: "compare_models",
      description:
        "Compare cost across Fable 5, Opus 5, legacy Opus snapshots, Sonnet 5, and Haiku 4.5 for a given token count. Shows which model is cheapest and savings percentages.",
      inputSchema: {
        type: "object" as const,
        properties: {
          input_tokens: {
            type: "number",
            description: "Number of input tokens",
          },
          output_tokens: {
            type: "number",
            description: "Number of output tokens",
          },
        },
        required: ["input_tokens", "output_tokens"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let result: object;

    switch (name) {
      case "estimate_cost":
        result = estimateCost(args as Parameters<typeof estimateCost>[0]);
        break;
      case "session_estimate":
        result = sessionEstimate(args as Parameters<typeof sessionEstimate>[0]);
        break;
      case "compare_models":
        result = compareModels(args as Parameters<typeof compareModels>[0]);
        break;
      default:
        return {
          content: [
            { type: "text" as const, text: `Unknown tool: ${name}` },
          ],
          isError: true,
        };
    }

    return {
      content: [
        { type: "text" as const, text: JSON.stringify(result, null, 2) },
      ],
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return {
      content: [{ type: "text" as const, text: `Error: ${message}` }],
      isError: true,
    };
  }
});

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
