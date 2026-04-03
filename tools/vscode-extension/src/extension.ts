/**
 * Claude Cost Estimator - VS Code Extension
 *
 * Shows estimated token count and Claude API cost for the active file
 * in the status bar. Provides commands for detailed file estimation,
 * CLAUDE.md per-turn cost analysis, and project config checks.
 */

import * as vscode from "vscode";
import {
  estimateTokens,
  calculateCost,
  estimatePerTurnCost,
  formatCost,
  formatTokens,
  MODEL_LABELS,
  PRICING,
} from "./costEstimator";
import { StatusBarManager } from "./statusBar";
import { checkProjectConfig } from "./configChecker";

let statusBarManager: StatusBarManager | undefined;

export function activate(context: vscode.ExtensionContext): void {
  // Status bar
  statusBarManager = new StatusBarManager();
  statusBarManager.activate();
  context.subscriptions.push({ dispose: () => statusBarManager?.dispose() });

  // Command: Estimate current file
  context.subscriptions.push(
    vscode.commands.registerCommand("claudeCost.estimateFile", () => {
      estimateCurrentFile();
    })
  );

  // Command: Estimate CLAUDE.md per-turn cost
  context.subscriptions.push(
    vscode.commands.registerCommand("claudeCost.estimateClaudeMd", () => {
      estimateClaudeMdCost();
    })
  );

  // Command: Check project configuration
  context.subscriptions.push(
    vscode.commands.registerCommand("claudeCost.checkConfig", () => {
      checkProjectConfig();
    })
  );
}

export function deactivate(): void {
  statusBarManager?.dispose();
  statusBarManager = undefined;
}

/**
 * Show a detailed cost estimate for the currently active file.
 */
function estimateCurrentFile(): void {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active file to estimate.");
    return;
  }

  const text = editor.document.getText();
  const tokens = estimateTokens(text);
  const fileName = editor.document.fileName.split(/[/\\]/).pop() ?? "file";
  const lines = editor.document.lineCount;
  const chars = text.length;

  const rows = Object.keys(PRICING).map((model) => {
    const inputCost = calculateCost(tokens, model, "input");
    const outputCost = calculateCost(tokens, model, "output");
    return `${MODEL_LABELS[model]}: input ${formatCost(inputCost)}, output ${formatCost(outputCost)}`;
  });

  const message = [
    `File: ${fileName}`,
    `Lines: ${lines.toLocaleString("en-US")} | Characters: ${chars.toLocaleString("en-US")} | Tokens: ~${formatTokens(tokens)}`,
    "",
    "Estimated cost if this file is sent as context:",
    ...rows.map((r) => `  ${r}`),
  ].join("\n");

  vscode.window.showInformationMessage(message, { modal: true });
}

/**
 * Find and estimate the per-turn cost of CLAUDE.md files in the workspace.
 */
async function estimateClaudeMdCost(): Promise<void> {
  const files = await vscode.workspace.findFiles("**/CLAUDE.md", null, 10);

  if (files.length === 0) {
    vscode.window.showWarningMessage("No CLAUDE.md found in the workspace.");
    return;
  }

  const config = vscode.workspace.getConfiguration("claudeCost");
  const model = config.get<string>("defaultModel", "sonnet");

  const results: string[] = [];

  for (const file of files) {
    const doc = await vscode.workspace.openTextDocument(file);
    const text = doc.getText();
    const relativePath = vscode.workspace.asRelativePath(file);
    const breakdown = estimatePerTurnCost(text, 20, model);

    results.push(
      [
        `--- ${relativePath} ---`,
        `Tokens: ~${formatTokens(breakdown.tokens)}`,
        `Model: ${MODEL_LABELS[model]}`,
        `Input cost per turn: ${formatCost(breakdown.inputCostPerTurn)}`,
        `Est. output per turn (500 tokens): ${formatCost(breakdown.outputEstimatePerTurn)}`,
        `Total per turn: ${formatCost(breakdown.totalPerTurn)}`,
        `20-turn session cost (this file only): ${formatCost(breakdown.totalForSession)}`,
      ].join("\n")
    );
  }

  vscode.window.showInformationMessage(results.join("\n\n"), { modal: true });
}
