(function () {
  "use strict";

  // ── Pricing (March 2026, per 1M tokens) ──────────────────────────
  var PRICING = {
    opus: {
      name: "Opus 4.6",
      input: 5.0,
      output: 25.0,
      cacheHit: 0.5,
      contextWindow: 1000000,
    },
    sonnet: {
      name: "Sonnet 4.6",
      input: 3.0,
      output: 15.0,
      cacheHit: 0.3,
      contextWindow: 1000000,
    },
    haiku: {
      name: "Haiku 4.5",
      input: 1.0,
      output: 5.0,
      cacheHit: 0.1,
      contextWindow: 200000,
    },
  };

  // ── Assumptions ──────────────────────────────────────────────────
  var TOKENS_PER_CLAUDEMD_LINE = 7;
  var SYSTEM_PROMPT_TOKENS = 3500;
  var MCP_SCHEMA_TOKENS = 1500;
  var FILE_READ_TOKENS = 2000;
  var OUTPUT_TOKENS_PER_TURN = 500;
  var HISTORY_GROWTH_PER_TURN = 1500;
  var CACHE_HIT_RATE = 0.7;
  var FAST_MODE_MULTIPLIER = 6;
  var OPTIMIZED_CLAUDEMD_LINES = 80;

  // ── DOM refs ─────────────────────────────────────────────────────
  var modelRadios = document.querySelectorAll('input[name="model"]');
  var turnsInput = document.getElementById("turns");
  var claudemdInput = document.getElementById("claudemd-lines");
  var sessionsInput = document.getElementById("sessions");
  var workdaysInput = document.getElementById("workdays");
  var mcpInput = document.getElementById("mcp-servers");
  var fileReadsInput = document.getElementById("file-reads");
  var fastModeCheck = document.getElementById("fast-mode");
  var copyBtn = document.getElementById("copy-btn");
  var copyFeedback = document.getElementById("copy-feedback");

  // ── Helpers ──────────────────────────────────────────────────────
  function getSelectedModel() {
    var checked = document.querySelector('input[name="model"]:checked');
    return checked ? checked.value : "opus";
  }

  function numVal(el, fallback) {
    var v = parseFloat(el.value);
    return isNaN(v) || v < 0 ? fallback : v;
  }

  function fmt(dollars) {
    return "$" + dollars.toFixed(2);
  }

  function pct(fraction) {
    return Math.round(fraction * 100) + "%";
  }

  function el(id) {
    return document.getElementById(id);
  }

  // ── Cost calculation for one scenario ────────────────────────────
  // Returns an object with per-component monthly costs.
  function computeCosts(params) {
    var pricing = PRICING[params.model];
    var inputRate = pricing.input / 1e6; // cost per token
    var outputRate = pricing.output / 1e6;
    var cacheRate = pricing.cacheHit / 1e6;
    var fastMult = params.fastMode && params.model === "opus" ? FAST_MODE_MULTIPLIER : 1;

    inputRate *= fastMult;
    outputRate *= fastMult;
    cacheRate *= fastMult;

    var totalSessions = params.sessions * params.workdays;
    var totalTurns = totalSessions * params.turns;

    // ── CLAUDE.md cost ──────────────────────────────────────────
    // Loaded every turn. Stable content -> high cache hit rate.
    var claudemdTokens = params.claudemdLines * TOKENS_PER_CLAUDEMD_LINE;
    var claudemdCostPerTurn =
      claudemdTokens * CACHE_HIT_RATE * cacheRate +
      claudemdTokens * (1 - CACHE_HIT_RATE) * inputRate;
    var claudemdMonthly = claudemdCostPerTurn * totalTurns;

    // ── System prompt cost ──────────────────────────────────────
    // Also stable, benefits from caching.
    var sysCostPerTurn =
      SYSTEM_PROMPT_TOKENS * CACHE_HIT_RATE * cacheRate +
      SYSTEM_PROMPT_TOKENS * (1 - CACHE_HIT_RATE) * inputRate;
    var sysMonthly = sysCostPerTurn * totalTurns;

    // ── MCP schema overhead ─────────────────────────────────────
    // Loaded every turn, stable -> cached.
    var mcpTokens = params.mcpServers * MCP_SCHEMA_TOKENS;
    var mcpCostPerTurn =
      mcpTokens * CACHE_HIT_RATE * cacheRate +
      mcpTokens * (1 - CACHE_HIT_RATE) * inputRate;
    var mcpMonthly = mcpCostPerTurn * totalTurns;

    // ── File read cost ──────────────────────────────────────────
    // Not cached (different files each time).
    var fileTokensPerTurn = params.fileReads * FILE_READ_TOKENS;
    var fileMonthly = fileTokensPerTurn * inputRate * totalTurns;

    // ── Conversation history growth ─────────────────────────────
    // Each turn re-sends the full conversation. Average context size
    // across the session is (turns / 2) * growth_per_turn.
    // Total input tokens for history across one session:
    //   sum(i=1..turns) of i * growth_per_turn = turns*(turns+1)/2 * growth
    // Simplified: average turn context = (turns + 1) / 2 * growth
    // Total input tokens from history across all turns in one session:
    // sum(i=1..turns) of i * HISTORY_GROWTH_PER_TURN = turns*(turns+1)/2 * growth
    var historyTotalTokensPerSession =
      (params.turns * (params.turns + 1)) / 2 * HISTORY_GROWTH_PER_TURN;
    var historyMonthly = historyTotalTokensPerSession * inputRate * totalSessions;

    // ── Output tokens ───────────────────────────────────────────
    var outputMonthly = OUTPUT_TOKENS_PER_TURN * outputRate * totalTurns;

    var total =
      claudemdMonthly +
      sysMonthly +
      mcpMonthly +
      fileMonthly +
      historyMonthly +
      outputMonthly;

    return {
      claudemd: claudemdMonthly,
      system: sysMonthly,
      mcp: mcpMonthly,
      file: fileMonthly,
      history: historyMonthly,
      output: outputMonthly,
      total: total,
    };
  }

  // ── Generate recommendations based on inputs ─────────────────────
  function getRecommendations(params, current, optimized) {
    var recs = [];
    var savings;

    // 1. Large CLAUDE.md
    if (params.claudemdLines > 80) {
      savings = current.claudemd - optimized.claudemd;
      recs.push({
        priority: savings,
        text:
          '<strong>Trim CLAUDE.md to ~80 lines.</strong> Your ' +
          params.claudemdLines +
          "-line file is loaded every turn. Trimming saves ~" +
          fmt(savings) +
          "/month.",
      });
    }

    // 2. Many MCP servers
    if (params.mcpServers > 2) {
      var reducedMcp = computeCosts(
        Object.assign({}, params, { mcpServers: 2 })
      );
      savings = current.mcp - reducedMcp.mcp;
      recs.push({
        priority: savings,
        text:
          "<strong>Reduce MCP servers from " +
          params.mcpServers +
          " to 2.</strong> Each server adds ~1,500 tokens of schema to every turn. Saves ~" +
          fmt(savings) +
          "/month.",
      });
    }

    // 3. Long sessions -> use compact mode or split sessions
    if (params.turns > 25) {
      var splitTurns = Math.min(params.turns, 20);
      var splitSessions = Math.ceil(
        (params.turns * params.sessions) / splitTurns
      );
      var splitCost = computeCosts(
        Object.assign({}, params, {
          turns: splitTurns,
          sessions: splitSessions / params.workdays, // daily
        })
      );
      // Recalc total sessions based on workdays
      var splitParams = Object.assign({}, params, {
        turns: splitTurns,
        sessions: Math.ceil(
          (params.turns / splitTurns) * params.sessions
        ),
      });
      var splitResult = computeCosts(splitParams);
      savings = current.history - splitResult.history;
      if (savings > 0) {
        recs.push({
          priority: savings,
          text:
            "<strong>Keep sessions under 20 turns.</strong> Conversation history grows quadratically. Splitting long sessions resets context and saves ~" +
            fmt(savings) +
            "/month on history costs.",
        });
      }
    }

    // 4. Switch to cheaper model for simple tasks
    if (params.model === "opus") {
      var haikuCost = computeCosts(Object.assign({}, params, { model: "haiku" }));
      savings = current.total - haikuCost.total;
      recs.push({
        priority: savings * 0.3, // only partial tasks would switch
        text:
          "<strong>Use Haiku for simple tasks.</strong> Routing refactors, docs, and boilerplate to Haiku 4.5 at $1/$5 instead of Opus at $5/$25 can save 70-80% on those tasks.",
      });
    } else if (params.model === "sonnet") {
      var haikuCostFromSonnet = computeCosts(
        Object.assign({}, params, { model: "haiku" })
      );
      savings = current.total - haikuCostFromSonnet.total;
      recs.push({
        priority: savings * 0.3,
        text:
          "<strong>Use Haiku for simple tasks.</strong> Routing docs and formatting to Haiku 4.5 at $1/$5 instead of Sonnet at $3/$15 saves on low-complexity work.",
      });
    }

    // 5. Fast mode warning
    if (params.fastMode && params.model === "opus") {
      recs.push({
        priority: current.total * 0.8,
        text:
          "<strong>Disable Fast Mode for non-urgent work.</strong> Fast Mode applies a 6x multiplier. Reserve it for time-sensitive debugging only.",
      });
    }

    // 6. High file reads
    if (params.fileReads > 2) {
      var reducedFiles = computeCosts(
        Object.assign({}, params, { fileReads: 1 })
      );
      savings = current.file - reducedFiles.file;
      recs.push({
        priority: savings,
        text:
          "<strong>Reduce file reads with .claudeignore.</strong> Excluding build artifacts, node_modules, and generated files saves ~" +
          fmt(savings) +
          "/month.",
      });
    }

    // 7. Use prompt caching effectively
    if (params.claudemdLines > 0 || params.mcpServers > 0) {
      var stableTokens =
        params.claudemdLines * TOKENS_PER_CLAUDEMD_LINE +
        SYSTEM_PROMPT_TOKENS +
        params.mcpServers * MCP_SCHEMA_TOKENS;
      if (stableTokens > 5000) {
        recs.push({
          priority: 1,
          text:
            "<strong>Keep CLAUDE.md content stable between turns.</strong> The ~70% cache hit rate depends on content not changing. Avoid dynamic content in CLAUDE.md to maximize cache savings.",
        });
      }
    }

    // Sort by priority (highest savings first) and take top 3
    recs.sort(function (a, b) {
      return b.priority - a.priority;
    });
    return recs.slice(0, 3);
  }

  // ── Main recalculation ───────────────────────────────────────────
  function recalculate() {
    var params = {
      model: getSelectedModel(),
      turns: numVal(turnsInput, 30),
      claudemdLines: numVal(claudemdInput, 100),
      sessions: numVal(sessionsInput, 3),
      workdays: numVal(workdaysInput, 22),
      mcpServers: numVal(mcpInput, 2),
      fileReads: numVal(fileReadsInput, 1),
      fastMode: fastModeCheck.checked,
    };

    // Current scenario
    var current = computeCosts(params);

    // Optimized scenario:
    // - CLAUDE.md trimmed to 80 lines (or current if already under)
    // - Use .claudeignore (reduce file reads by 30%)
    // - For Opus/Sonnet, assume 30% of turns switch to Haiku
    var optParams = Object.assign({}, params);
    optParams.claudemdLines = Math.min(params.claudemdLines, OPTIMIZED_CLAUDEMD_LINES);
    optParams.fileReads = Math.max(params.fileReads * 0.7, 0);
    optParams.fastMode = false;

    var optimized;
    if (params.model !== "haiku") {
      // Blend: 70% on current model (optimized), 30% on Haiku
      var mainCost = computeCosts(optParams);
      var haikuParams = Object.assign({}, optParams, { model: "haiku" });
      var haikuCost = computeCosts(haikuParams);
      optimized = {
        claudemd: mainCost.claudemd * 0.7 + haikuCost.claudemd * 0.3,
        system: mainCost.system * 0.7 + haikuCost.system * 0.3,
        mcp: mainCost.mcp * 0.7 + haikuCost.mcp * 0.3,
        file: mainCost.file * 0.7 + haikuCost.file * 0.3,
        history: mainCost.history * 0.7 + haikuCost.history * 0.3,
        output: mainCost.output * 0.7 + haikuCost.output * 0.3,
        total: mainCost.total * 0.7 + haikuCost.total * 0.3,
      };
    } else {
      optimized = computeCosts(optParams);
    }

    var savingsAmount = current.total - optimized.total;
    var savingsFraction = current.total > 0 ? savingsAmount / current.total : 0;

    // ── Update DOM ──────────────────────────────────────────────
    el("current-cost").textContent = fmt(current.total);
    el("optimized-cost").textContent = fmt(optimized.total);
    el("savings-amount").textContent = fmt(savingsAmount);
    el("savings-percent").textContent = "(" + pct(savingsFraction) + ")";

    el("bd-claudemd-current").textContent = fmt(current.claudemd);
    el("bd-claudemd-optimized").textContent = fmt(optimized.claudemd);
    el("bd-system-current").textContent = fmt(current.system);
    el("bd-system-optimized").textContent = fmt(optimized.system);
    el("bd-mcp-current").textContent = fmt(current.mcp);
    el("bd-mcp-optimized").textContent = fmt(optimized.mcp);
    el("bd-file-current").textContent = fmt(current.file);
    el("bd-file-optimized").textContent = fmt(optimized.file);
    el("bd-history-current").textContent = fmt(current.history);
    el("bd-history-optimized").textContent = fmt(optimized.history);
    el("bd-output-current").textContent = fmt(current.output);
    el("bd-output-optimized").textContent = fmt(optimized.output);
    el("bd-total-current").textContent = fmt(current.total);
    el("bd-total-optimized").textContent = fmt(optimized.total);

    // ── Recommendations ─────────────────────────────────────────
    var recs = getRecommendations(params, current, optimized);
    var recList = el("recommendations");
    recList.innerHTML = "";
    if (recs.length === 0) {
      var li = document.createElement("li");
      li.textContent = "Your configuration looks well-optimized already.";
      recList.appendChild(li);
    } else {
      recs.forEach(function (rec) {
        var li = document.createElement("li");
        li.innerHTML = rec.text;
        recList.appendChild(li);
      });
    }

    // Store for copy
    window._calcState = { params: params, current: current, optimized: optimized, savings: savingsAmount, savingsPct: savingsFraction, recs: recs };
  }

  // ── Copy as Markdown ─────────────────────────────────────────────
  function copyAsMarkdown() {
    var s = window._calcState;
    if (!s) return;

    var modelName = PRICING[s.params.model].name;
    var lines = [
      "## Claude Cost Estimate",
      "",
      "**Model:** " + modelName,
      "**Turns/session:** " + s.params.turns +
        " | **Sessions/day:** " + s.params.sessions +
        " | **Workdays/month:** " + s.params.workdays,
      "**CLAUDE.md:** " + s.params.claudemdLines + " lines" +
        " | **MCP servers:** " + s.params.mcpServers +
        " | **File reads/turn:** " + s.params.fileReads,
      s.params.fastMode && s.params.model === "opus" ? "**Fast Mode:** enabled" : "",
      "",
      "| Component | Current | Optimized |",
      "| --- | ---: | ---: |",
      "| CLAUDE.md tokens | " + fmt(s.current.claudemd) + " | " + fmt(s.optimized.claudemd) + " |",
      "| System prompt | " + fmt(s.current.system) + " | " + fmt(s.optimized.system) + " |",
      "| MCP schema overhead | " + fmt(s.current.mcp) + " | " + fmt(s.optimized.mcp) + " |",
      "| File reads | " + fmt(s.current.file) + " | " + fmt(s.optimized.file) + " |",
      "| Conversation history | " + fmt(s.current.history) + " | " + fmt(s.optimized.history) + " |",
      "| Output tokens | " + fmt(s.current.output) + " | " + fmt(s.optimized.output) + " |",
      "| **Total** | **" + fmt(s.current.total) + "** | **" + fmt(s.optimized.total) + "** |",
      "",
      "**Monthly savings:** " + fmt(s.savings) + " (" + pct(s.savingsPct) + ")",
      "",
    ];

    if (s.recs.length > 0) {
      lines.push("### Recommendations");
      s.recs.forEach(function (rec, i) {
        // Strip HTML tags for markdown
        var text = rec.text.replace(/<\/?strong>/g, "**");
        lines.push((i + 1) + ". " + text);
      });
      lines.push("");
    }

    lines.push("---");
    lines.push("*Generated by [Claude Cost Calculator](https://github.com/Sagargupta16/claude-cost-optimizer)*");

    var markdown = lines.filter(function (l) { return l !== undefined; }).join("\n");

    navigator.clipboard.writeText(markdown).then(function () {
      copyFeedback.textContent = "Copied!";
      copyFeedback.classList.add("visible");
      setTimeout(function () {
        copyFeedback.classList.remove("visible");
      }, 2000);
    }).catch(function () {
      // Fallback: select text in a textarea
      var ta = document.createElement("textarea");
      ta.value = markdown;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      copyFeedback.textContent = "Copied!";
      copyFeedback.classList.add("visible");
      setTimeout(function () {
        copyFeedback.classList.remove("visible");
      }, 2000);
    });
  }

  // ── Event Listeners ──────────────────────────────────────────────
  var allInputs = [turnsInput, claudemdInput, sessionsInput, workdaysInput, mcpInput, fileReadsInput];
  allInputs.forEach(function (input) {
    input.addEventListener("input", recalculate);
  });
  modelRadios.forEach(function (radio) {
    radio.addEventListener("change", recalculate);
  });
  fastModeCheck.addEventListener("change", recalculate);
  copyBtn.addEventListener("click", copyAsMarkdown);

  // ── Initial calculation ──────────────────────────────────────────
  recalculate();
})();
