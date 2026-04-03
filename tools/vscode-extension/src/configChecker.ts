/**
 * Project configuration analysis for Claude Code optimization.
 *
 * Checks for the presence and quality of CLAUDE.md, .claudeignore,
 * and .claude/settings.json in the current workspace, then reports
 * findings and suggestions.
 */

import * as vscode from "vscode";
import * as path from "path";
import * as fs from "fs";
import { estimateTokens, formatTokens } from "./costEstimator";

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

  // Check .claudeignore
  findings.push(checkClaudeignore(rootPath));

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

function checkClaudeMd(rootPath: string): ConfigFinding {
  const claudeMdPath = path.join(rootPath, "CLAUDE.md");

  if (!fs.existsSync(claudeMdPath)) {
    return {
      label: "CLAUDE.md",
      status: "missing",
      detail: "Not found. Add one to give Claude project context.",
    };
  }

  const content = fs.readFileSync(claudeMdPath, "utf-8");
  const lines = content.split("\n").length;
  const tokens = estimateTokens(content);
  const config = vscode.workspace.getConfiguration("claudeCost");
  const threshold = config.get<number>("claudeMdWarningThreshold", 150);

  if (lines > threshold) {
    return {
      label: "CLAUDE.md",
      status: "warning",
      detail: `${lines} lines (~${formatTokens(tokens)} tokens). Consider trimming -- this is sent on every turn.`,
    };
  }

  return {
    label: "CLAUDE.md",
    status: "ok",
    detail: `${lines} lines (~${formatTokens(tokens)} tokens).`,
  };
}

function checkClaudeignore(rootPath: string): ConfigFinding {
  const ignorePath = path.join(rootPath, ".claudeignore");

  if (!fs.existsSync(ignorePath)) {
    return {
      label: ".claudeignore",
      status: "missing",
      detail: "Not found. Add one to exclude large/irrelevant files from context.",
    };
  }

  const content = fs.readFileSync(ignorePath, "utf-8");
  const rules = content
    .split("\n")
    .filter((line) => line.trim() && !line.startsWith("#")).length;

  return {
    label: ".claudeignore",
    status: "ok",
    detail: `Found with ${rules} rule(s).`,
  };
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
    if (f.status === "missing" && f.label === ".claudeignore") {
      items.push({
        label: "Create .claudeignore",
        description: "Exclude node_modules, dist, build artifacts, etc.",
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
    case "Create .claudeignore": {
      const defaultContent = [
        "# Directories",
        "node_modules/",
        "dist/",
        "build/",
        ".git/",
        "",
        "# Large files",
        "*.min.js",
        "*.map",
        "package-lock.json",
        "pnpm-lock.yaml",
        "",
        "# Binary files",
        "*.png",
        "*.jpg",
        "*.gif",
        "*.pdf",
        "*.zip",
        "",
      ].join("\n");
      const filePath = path.join(workspaceRoot, ".claudeignore");
      fs.writeFileSync(filePath, defaultContent, "utf-8");
      const doc = await vscode.workspace.openTextDocument(filePath);
      await vscode.window.showTextDocument(doc);
      break;
    }
    case "Open CLAUDE.md for editing": {
      const filePath = path.join(workspaceRoot, "CLAUDE.md");
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
