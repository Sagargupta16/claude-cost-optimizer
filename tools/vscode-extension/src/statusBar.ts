/**
 * Status bar management for the Claude Cost Estimator extension.
 *
 * Displays token count and estimated input cost for the active file
 * in the VS Code status bar. Updates automatically when the active
 * editor changes or document text is modified.
 */

import * as vscode from "vscode";
import { estimateTokens, calculateCost, formatCost, formatTokens } from "./costEstimator";

const WARNING_COLOR = new vscode.ThemeColor("statusBarItem.warningBackground");

export class StatusBarManager {
  private statusBarItem: vscode.StatusBarItem;
  private disposables: vscode.Disposable[] = [];

  constructor() {
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.statusBarItem.command = "claudeCost.estimateFile";
    this.statusBarItem.tooltip = "Click for detailed Claude cost estimate";
  }

  /**
   * Start listening for editor changes and show the status bar item.
   */
  activate(): void {
    const config = vscode.workspace.getConfiguration("claudeCost");
    if (!config.get<boolean>("showInStatusBar", true)) {
      return;
    }

    this.disposables.push(
      vscode.window.onDidChangeActiveTextEditor(() => this.update()),
      vscode.workspace.onDidChangeTextDocument((e) => {
        if (e.document === vscode.window.activeTextEditor?.document) {
          this.update();
        }
      }),
      vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration("claudeCost")) {
          this.update();
        }
      })
    );

    this.update();
    this.statusBarItem.show();
  }

  /**
   * Recalculate and display the token estimate for the active file.
   */
  update(): void {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      this.statusBarItem.hide();
      return;
    }

    const config = vscode.workspace.getConfiguration("claudeCost");
    if (!config.get<boolean>("showInStatusBar", true)) {
      this.statusBarItem.hide();
      return;
    }

    const text = editor.document.getText();
    const tokens = estimateTokens(text);
    const model = config.get<string>("defaultModel", "sonnet");
    const cost = calculateCost(tokens, model, "input");

    this.statusBarItem.text = `$(file) ~${formatTokens(tokens)} tokens | ${formatCost(cost)}`;

    // Warn if this looks like a CLAUDE.md that exceeds the threshold
    const fileName = editor.document.fileName;
    const lineCount = editor.document.lineCount;
    const threshold = config.get<number>("claudeMdWarningThreshold", 150);

    if (fileName.endsWith("CLAUDE.md") && lineCount > threshold) {
      this.statusBarItem.backgroundColor = WARNING_COLOR;
      this.statusBarItem.tooltip =
        `CLAUDE.md is ${lineCount} lines (threshold: ${threshold}). ` +
        `Large CLAUDE.md files increase per-turn costs. Click for details.`;
    } else {
      this.statusBarItem.backgroundColor = undefined;
      this.statusBarItem.tooltip = "Click for detailed Claude cost estimate";
    }

    this.statusBarItem.show();
  }

  /**
   * Dispose of the status bar item and event listeners.
   */
  dispose(): void {
    this.statusBarItem.dispose();
    for (const d of this.disposables) {
      d.dispose();
    }
    this.disposables = [];
  }
}
