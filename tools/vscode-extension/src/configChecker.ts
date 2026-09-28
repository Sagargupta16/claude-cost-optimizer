/**
 * Project configuration analysis for Claude Code optimization.
 *
 * Checks CLAUDE.md size, file-read exclusions (Read rules in
 * permissions.deny), and .claude/settings.json in the current workspace,
 * then reports findings and suggestions. CLAUDE.md and file-read exclusions
 * are scored on the same rubric as tools/claude-rate/rate.py.
 */

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { formatTokens } from "./costEstimator";

interface ConfigFinding {
  label: string;
  status: "ok" | "warning" | "missing";
  detail: string;
}

/**
 * Run a configuration check on the current workspace and display results.
 */
export async function checkProjectConfig(): Promise<void> {
  const workspaceFolders = vscode.workspace.workspaceFolders;
  if (!workspaceFolders || workspaceFolders.length === 0) {
    vscode.window.showWarningMessage("No workspace folder open.");
    return;
  }

  const rootPath = workspaceFolders[0].uri.fsPath;
  const findings: ConfigFinding[] = [];

  // Check CLAUDE.md
  findings.push(checkClaudeMd(rootPath));

  // Check Read deny rules in permissions.deny
  findings.push(checkFileReadExclusions(rootPath));

  // Check .claude/settings.json
  findings.push(checkClaudeSettings(rootPath));

  // Show summary as information message
  const summary = findings
    .map((f) => `${statusIcon(f.status)} ${f.label}: ${f.detail}`)
    .join("\n");

  const warningCount = findings.filter(
    (f) => f.status === "warning" || f.status === "missing"
  ).length;

  if (warningCount > 0) {
    const action = await vscode.window.showWarningMessage(
      `Claude Config: ${warningCount} issue(s) found.\n\n${summary}`,
      "Show Suggestions"
    );
    if (action === "Show Suggestions") {
      showSuggestions(findings);
    }
  } else {
    vscode.window.showInformationMessage(
      `Claude Config: All checks passed.\n\n${summary}`
    );
  }
}

const CLAUDE_MD_LINE_GUIDANCE = 200;

/** Line count matching Python's str.splitlines(), so scores agree with claude-rate. */
function countLines(text: string): number {
  if (!text) {
    return 0;
  }
  const lines = text.split("\n");
  return lines[lines.length - 1] === "" ? lines.length - 1 : lines.length;
}

/** Shared rubric, 20 points: primary line count (12) + estimated tokens across files (8). */
function claudeMdScore(lines: number, tokens: number): number {
  let score = 1;
  if (lines <= 100) score = 12;
  else if (lines <= CLAUDE_MD_LINE_GUIDANCE) score = 10;
  else if (lines <= 300) score = 6;
  else if (lines <= 500) score = 3;

  if (tokens <= 2000) score += 8;
  else if (tokens <= 4000) score += 6;
  else if (tokens <= 8000) score += 4;
  else if (tokens <= 16000) score += 2;
  return score;
}

function checkClaudeMd(rootPath: string): ConfigFinding {
  // Primary is the root CLAUDE.md, or .claude/CLAUDE.md when the root has none.
  // Newlines are normalized the way Python's text mode reads them.
  const texts = [
    path.join(rootPath, "CLAUDE.md"),
    path.join(rootPath, ".claude", "CLAUDE.md"),
  ]
    .filter((p) => fs.existsSync(p))
    .map((p) => fs.readFileSync(p, "utf-8").replace(/\r\n?/g, "\n"));

  if (texts.length === 0) {
    return {
      label: "CLAUDE.md",
      status: "missing",
      detail: "Not found. Add one to give Claude project context.",
    };
  }

  const lines = countLines(texts[0]);
  const tokens = Math.ceil(texts.reduce((sum, t) => sum + t.length, 0) / 4);
  const summary = `~${formatTokens(tokens)} tokens across ${texts.length} file(s); scores ${claudeMdScore(lines, tokens)}/20.`;
  const config = vscode.workspace.getConfiguration("claudeCost");
  const threshold = config.get<number>("claudeMdWarningThreshold", 150);

  if (lines > CLAUDE_MD_LINE_GUIDANCE) {
    return {
      label: "CLAUDE.md",
      status: "warning",
      detail: `${lines} lines -- over Anthropic's 200-line guidance for CLAUDE.md. Longer files consume more context and reduce adherence. Move workflow-specific instructions into skills or path-scoped .claude/rules/ so they load on demand. ${summary}`,
    };
  }

  if (lines > threshold) {
    return {
      label: "CLAUDE.md",
      status: "warning",
      detail: `${lines} lines, ${summary} Consider trimming -- it loads in full at the start of every session.`,
    };
  }

  return {
    label: "CLAUDE.md",
    status: "ok",
    detail: `${lines} lines, ${summary}`,
  };
}

const FILE_READ_LABEL = "File-read exclusions";
const SHOW_READ_RULES = "Show Read deny rules to add";
const READ_RULE = /^Read\(.+\)$/;
const LOCK_FILES = [
  "package-lock.json",
  "pnpm-lock.yaml",
  "yarn.lock",
  "poetry.lock",
  "Cargo.lock",
  "uv.lock",
];
// Claude Code does not read this file; it is detected only to flag it and convert its patterns.
const IGNORE_FILE = ".claudeignore";
const IGNORE_FILE_FINDING =
  "`.claudeignore` is not read by Claude Code -- it appears nowhere in Claude Code's documentation. Move its patterns into permissions.deny as Read(...) rules.";
// Suggested when a project has no Read deny rules at all.
const DEFAULT_READ_DENY = [
  "Read(./node_modules/**)",
  "Read(./dist/**)",
  "Read(./build/**)",
  "Read(./coverage/**)",
  "Read(./.env)",
  "Read(./.env.*)",
  "Read(*.min.js)",
  "Read(./package-lock.json)",
];

/** First of .claude/settings.json, .claude/settings.local.json that parses as a JSON object. */
function loadSettings(rootPath: string): Record<string, unknown> | null {
  for (const name of ["settings.json", "settings.local.json"]) {
    const settingsPath = path.join(rootPath, ".claude", name);
    if (!fs.existsSync(settingsPath)) {
      continue;
    }
    try {
      const data = JSON.parse(fs.readFileSync(settingsPath, "utf-8"));
      if (data && typeof data === "object" && !Array.isArray(data)) {
        return data as Record<string, unknown>;
      }
    } catch {
      // Invalid JSON: fall through to the next file, as claude-rate does.
    }
  }
  return null;
}

function readDenyRules(rootPath: string): string[] {
  const perms = loadSettings(rootPath)?.permissions;
  const deny =
    perms && typeof perms === "object"
      ? (perms as Record<string, unknown>).deny
      : undefined;
  if (!Array.isArray(deny)) {
    return [];
  }
  return deny.filter(
    (r): r is string => typeof r === "string" && READ_RULE.test(r)
  );
}

function uncoveredLockFiles(rootPath: string, rules: string[]): string[] {
  return LOCK_FILES.filter(
    (lf) =>
      fs.existsSync(path.join(rootPath, lf)) &&
      !rules.some(
        (r) => r.includes(lf) || r.includes("*.lock") || r.includes("*lock*")
      )
  );
}

/**
 * Converts ignore-file patterns to Read deny rules: `dir/` -> Read(./dir/**);
 * a pattern containing `/` elsewhere -> Read(./pattern) with any leading `/`
 * stripped; a bare name or glob -> Read(pattern). Blank lines, comments and
 * `!` negations are skipped.
 */
function ignorePatternsAsReadRules(content: string): string[] {
  const rules: string[] = [];
  for (const line of content.replace(/\r\n?/g, "\n").split("\n")) {
    const s = line.trim();
    if (!s || s.startsWith("#") || s.startsWith("!")) {
      continue;
    }
    if (s.endsWith("/")) {
      rules.push(`Read(./${s.slice(0, -1).replace(/^\//, "")}/**)`);
    } else if (s.includes("/")) {
      rules.push(`Read(./${s.replace(/^\//, "")})`);
    } else {
      rules.push(`Read(${s})`);
    }
  }
  return rules;
}

function checkFileReadExclusions(rootPath: string): ConfigFinding {
  const rules = readDenyRules(rootPath);
  const lockFiles = LOCK_FILES.filter((lf) =>
    fs.existsSync(path.join(rootPath, lf))
  );
  const uncovered = uncoveredLockFiles(rootPath, rules);

  // Shared rubric, 15 points: >=10 rules -> 13, >=5 -> 10, >=1 -> 6, plus 2
  // when every lock file at the root is covered.
  let score = 0;
  if (rules.length >= 10) score = 13;
  else if (rules.length >= 5) score = 10;
  else if (rules.length >= 1) score = 6;
  if (rules.length >= 1 && uncovered.length === 0) score += 2;
  score = Math.min(score, 15);

  let summary = "no Read deny rules in permissions.deny";
  if (rules.length > 0) {
    let lockNote = "lock files covered";
    if (lockFiles.length === 0) lockNote = "no lock files at root";
    else if (uncovered.length > 0) {
      lockNote = `lock files not covered: ${uncovered.join(", ")}`;
    }
    summary = `${rules.length} Read deny rule(s); ${lockNote}`;
  }

  if (fs.existsSync(path.join(rootPath, IGNORE_FILE))) {
    return {
      label: FILE_READ_LABEL,
      status: "warning",
      detail: `${IGNORE_FILE_FINDING} Scores ${score}/15 (${summary}).`,
    };
  }
  if (rules.length === 0) {
    return {
      label: FILE_READ_LABEL,
      status: "missing",
      detail: `Scores 0/15 (${summary}). Add Read(...) rules to keep Claude's file tools out of dependency, build and generated paths.`,
    };
  }
  return {
    label: FILE_READ_LABEL,
    status: uncovered.length > 0 ? "warning" : "ok",
    detail: `Scores ${score}/15 (${summary}).`,
  };
}

/** Read deny rules to suggest: the ignore file converted, uncovered lock files, or a default block. */
function suggestedReadRules(rootPath: string): string[] {
  const ignorePath = path.join(rootPath, IGNORE_FILE);
  if (fs.existsSync(ignorePath)) {
    return ignorePatternsAsReadRules(fs.readFileSync(ignorePath, "utf-8"));
  }
  const rules = readDenyRules(rootPath);
  if (rules.length === 0) {
    return DEFAULT_READ_DENY;
  }
  return uncoveredLockFiles(rootPath, rules).map((lf) => `Read(./${lf})`);
}

function checkClaudeSettings(rootPath: string): ConfigFinding {
  const settingsPath = path.join(rootPath, ".claude", "settings.json");

  if (!fs.existsSync(settingsPath)) {
    return {
      label: ".claude/settings.json",
      status: "missing",
      detail: "Not found. Optional, but useful for permission rules and hooks.",
    };
  }

  try {
    const content = fs.readFileSync(settingsPath, "utf-8");
    JSON.parse(content);
    return {
      label: ".claude/settings.json",
      status: "ok",
      detail: "Found and valid JSON.",
    };
  } catch {
    return {
      label: ".claude/settings.json",
      status: "warning",
      detail: "Found but contains invalid JSON.",
    };
  }
}

function statusIcon(status: "ok" | "warning" | "missing"): string {
  switch (status) {
    case "ok":
      return "[OK]";
    case "warning":
      return "[WARN]";
    case "missing":
      return "[MISSING]";
  }
}

async function showSuggestions(findings: ConfigFinding[]): Promise<void> {
  const items: vscode.QuickPickItem[] = [];

  for (const f of findings) {
    if (f.status === "missing" && f.label === "CLAUDE.md") {
      items.push({
        label: "Create CLAUDE.md",
        description: "Add a project instructions file for Claude Code",
      });
    }
    if (f.status !== "ok" && f.label === FILE_READ_LABEL) {
      items.push({
        label: SHOW_READ_RULES,
        description: "Open a permissions.deny block to merge into .claude/settings.json",
      });
    }
    if (f.status === "warning" && f.label === "CLAUDE.md") {
      items.push({
        label: "Open CLAUDE.md for editing",
        description: "Trim it down to reduce per-turn token costs",
      });
    }
    if (f.status === "warning" && f.label === ".claude/settings.json") {
      items.push({
        label: "Open .claude/settings.json",
        description: "Fix the invalid JSON",
      });
    }
  }

  if (items.length === 0) {
    return;
  }

  const selected = await vscode.window.showQuickPick(items, {
    placeHolder: "Select an action",
  });

  if (!selected) {
    return;
  }

  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!workspaceRoot) {
    return;
  }

  switch (selected.label) {
    case "Create CLAUDE.md": {
      const doc = await vscode.workspace.openTextDocument(
        vscode.Uri.file(path.join(workspaceRoot, "CLAUDE.md")).with({
          scheme: "untitled",
        })
      );
      await vscode.window.showTextDocument(doc);
      break;
    }
    case SHOW_READ_RULES: {
      const content = JSON.stringify(
        { permissions: { deny: suggestedReadRules(workspaceRoot) } },
        null,
        2
      );
      const doc = await vscode.workspace.openTextDocument({
        language: "json",
        content,
      });
      await vscode.window.showTextDocument(doc);
      break;
    }
    case "Open CLAUDE.md for editing": {
      // The primary file: root CLAUDE.md, or .claude/CLAUDE.md when the root has none.
      const rootFile = path.join(workspaceRoot, "CLAUDE.md");
      const filePath = fs.existsSync(rootFile)
        ? rootFile
        : path.join(workspaceRoot, ".claude", "CLAUDE.md");
      const doc = await vscode.workspace.openTextDocument(filePath);
      await vscode.window.showTextDocument(doc);
      break;
    }
    case "Open .claude/settings.json": {
      const filePath = path.join(workspaceRoot, ".claude", "settings.json");
      const doc = await vscode.workspace.openTextDocument(filePath);
      await vscode.window.showTextDocument(doc);
      break;
    }
  }
}
