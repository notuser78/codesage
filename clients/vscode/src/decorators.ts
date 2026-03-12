import * as vscode from 'vscode';

interface Finding {
    severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
    line_start: number;
    line_end: number;
    message: string;
    rule_name: string;
}

export class Decorators {
    private decorationTypes: Map<string, vscode.TextEditorDecorationType> = new Map();

    constructor() {
        // Initialize decoration types for each severity
        this.decorationTypes.set('critical', this.createDecorationType('critical'));
        this.decorationTypes.set('high', this.createDecorationType('high'));
        this.decorationTypes.set('medium', this.createDecorationType('medium'));
        this.decorationTypes.set('low', this.createDecorationType('low'));
        this.decorationTypes.set('info', this.createDecorationType('info'));
    }

    private createDecorationType(severity: string): vscode.TextEditorDecorationType {
        const colors: Record<string, string> = {
            critical: 'rgba(255, 0, 0, 0.3)',
            high: 'rgba(255, 107, 107, 0.3)',
            medium: 'rgba(255, 165, 0, 0.3)',
            low: 'rgba(255, 217, 61, 0.3)',
            info: 'rgba(100, 149, 237, 0.2)'
        };

        const overviewColors: Record<string, string> = {
            critical: '#FF0000',
            high: '#FF6B6B',
            medium: '#FFA500',
            low: '#FFD93D',
            info: '#6495ED'
        };

        return vscode.window.createTextEditorDecorationType({
            backgroundColor: colors[severity],
            overviewRulerColor: overviewColors[severity],
            overviewRulerLane: vscode.OverviewRulerLane.Right,
            isWholeLine: true,
            after: {
                contentText: ` ${severity.toUpperCase()}`,
                color: overviewColors[severity],
                fontWeight: 'bold'
            }
        });
    }

    decorateFindings(editor: vscode.TextEditor, findings: Finding[]): void {
        // Clear existing decorations
        this.clearDecorations(editor);

        // Group findings by severity
        const findingsBySeverity: Map<string, Finding[]> = new Map();
        
        for (const finding of findings) {
            const list = findingsBySeverity.get(finding.severity) || [];
            list.push(finding);
            findingsBySeverity.set(finding.severity, list);
        }

        // Apply decorations for each severity
        for (const [severity, severityFindings] of findingsBySeverity) {
            const decorationType = this.decorationTypes.get(severity);
            if (!decorationType) continue;

            const decorations: vscode.DecorationOptions[] = severityFindings.map(finding => {
                const range = new vscode.Range(
                    finding.line_start - 1,
                    0,
                    finding.line_end - 1,
                    editor.document.lineAt(finding.line_end - 1).text.length
                );

                return {
                    range,
                    hoverMessage: this.createHoverMessage(finding)
                };
            });

            editor.setDecorations(decorationType, decorations);
        }
    }

    clearDecorations(editor: vscode.TextEditor): void {
        for (const decorationType of this.decorationTypes.values()) {
            editor.setDecorations(decorationType, []);
        }
    }

    private createHoverMessage(finding: Finding): vscode.MarkdownString {
        const message = new vscode.MarkdownString();
        message.appendMarkdown(`### ${finding.rule_name}\n\n`);
        message.appendMarkdown(`**Severity:** ${finding.severity.toUpperCase()}\n\n`);
        message.appendMarkdown(finding.message);
        message.isTrusted = true;
        return message;
    }

    dispose(): void {
        for (const decorationType of this.decorationTypes.values()) {
            decorationType.dispose();
        }
        this.decorationTypes.clear();
    }
}
