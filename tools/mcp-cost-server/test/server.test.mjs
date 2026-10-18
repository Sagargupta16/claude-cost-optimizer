// End-to-end tests: spawn the built server over stdio with the MCP SDK client
// and check its tools return the cache-aware numbers worked out by hand below.
// Run after `pnpm run build`: `pnpm test`.

import { after, before, describe, it } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const SERVER = fileURLToPath(new URL("../dist/index.js", import.meta.url));
const perM = (tokens, rate) => (tokens / 1_000_000) * rate;
const usd = (n) => `$${n.toFixed(4)}`;

let client;

before(async () => {
  client = new Client({ name: "cost-server-test", version: "0.0.0" });
  await client.connect(new StdioClientTransport({ command: process.execPath, args: [SERVER] }));
});

after(async () => {
  await client?.close();
});

async function call(name, args) {
  const res = await client.callTool({ name, arguments: args });
  assert.notEqual(res.isError, true, JSON.stringify(res.content));
  return JSON.parse(res.content[0].text);
}

describe("tools/list", () => {
  it("exposes the three cost tools", async () => {
    const { tools } = await client.listTools();
    assert.deepEqual(tools.map((t) => t.name).sort(), ["compare_models", "estimate_cost", "session_estimate"]);
  });
});

describe("session_estimate", () => {
  it("bills a 30-turn Opus 5.5 session the way Claude Code caches it", async () => {
    // Turn t (1-based) sends 3,500 + 1,500(t-1) tokens. Turn 1 writes it all at
    // $5 (1.25 x $4); later turns read the previous prompt at $0.20 and write
    // 1,500 at $5; 500 output tokens a turn at $20.
    const prompts = Array.from({ length: 30 }, (_, i) => 3_500 + 1_500 * i);
    let expected = perM(prompts[0], 5) + perM(30 * 500, 20);
    for (let t = 1; t < 30; t++) expected += perM(prompts[t - 1], 0.2) + perM(1_500, 5);

    const result = await call("session_estimate", { turns: 30, model: "opus" });
    assert.equal(result.totals.total_cost, usd(expected));
    assert.equal(result.totals.total_cost, "$0.6771");
  });

  it("rejects an unknown model with the list of valid ids", async () => {
    const result = await call("session_estimate", { turns: 5, model: "gpt-5" });
    assert.match(result.error, /Unknown model "gpt-5"/);
  });
});

describe("compare_models", () => {
  it("prices one 100,001-token Haiku 5.5 request at the high tier", async () => {
    const result = await call("compare_models", { input_tokens: 100_001, output_tokens: 1_000 });
    // $0.50 input and $2.50 output on the whole request once the prompt is over 100,000.
    assert.equal(result.comparison.haiku.total, usd(perM(100_001, 0.5) + perM(1_000, 2.5)));
    assert.equal(result.comparison.haiku.input_cost, usd(perM(100_001, 0.5)));
  });
});

describe("estimate_cost", () => {
  it("warns when the text is below the model's minimum cacheable prompt", async () => {
    const result = await call("estimate_cost", { text: "x".repeat(400), model: "haiku-4.5" });
    assert.equal(result.estimated_tokens, 100); // ~4 characters per token
    assert.match(result.cache_warning, /4096-token minimum/);
  });
});
