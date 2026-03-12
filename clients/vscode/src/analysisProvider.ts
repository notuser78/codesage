import * as vscode from 'vscode';
import axios from 'axios';

interface Finding {
    id: string;
    rule_id: string;
    rule_name: string;
    severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
    message: string;
    file_path: string;
    line_start: number;
    line_end: number;
    code_snippet?: string;
    suggestion?: string;
}

interface AnalysisResult {
    id: string;
    status: string;
    findings: Finding[];
    metrics?: {
        complexity_score?: number;
        maintainability_index?: number;
        lines_of_code: number;
    };
    summary?: {
        total_findings: number;
        severity_counts: Record<string, number>;
    };
}

export class AnalysisProvider implements vscode.TreeDataProvider<AnalysisItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<AnalysisItem | undefined | null | void> = new vscode.EventEmitter<AnalysisItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<AnalysisItem | undefined | null | void> = this._onDidChangeTreeData.event;

    private findings: Finding[] = [];
    private currentFile: string | undefined;

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: AnalysisItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: AnalysisItem): Thenable<AnalysisItem[]> {
        if (!element) {
            // Root level - group by severity
            const severities = ['critical', 'high', 'medium', 'low', 'info'] as const;
            return Promise.resolve(
                severities
                    .filter(sev => this.findings.some(f => f.severity === sev))
                    .map(sev => new SeverityItem(
                        sev,
                        this.findings.filter(f => f.severity === sev).length,
                        vscode.TreeItemCollapsibleState.Collapsed
                    ))
            );
        } else if (element instanceof SeverityItem) {
            // Severity level - show findings
            return Promise.resolve(
                this.findings
                    .filter(f => f.severity === element.severity)
                    .map(f => new FindingItem(f))
            );
        }
        return Promise.resolve([]);
    }

    async analyzeCode(code: string, language: string, filePath?: string): Promise<AnalysisResult> {
        const config = vscode.workspace.getConfiguration('codesage');
        const serverUrl = config.get<string>('serverUrl');
        const apiKey = config.get<string>('apiKey');
        const analysisTypes = config.get<string[]>('analysisTypes') || ['security', 'performance'];

        if (!serverUrl) {
            throw new Error('CodeSage server URL not configured');
        }

        const headers: Record<string, string> = {
            'Content-Type': 'application/json'
        };
        if (apiKey) {
            headers['Authorization'] = `Bearer ${apiKey}`;
        }

        const response = await axios.post<AnalysisResult>(
            `${serverUrl}/api/v1/analyze`,
            {
                snippet: {
                    code,
                    language,
                    filename: filePath ? filePath.split('/').pop() : undefined
                },
                analysis_types: analysisTypes,
                options: {
                    include_suggestions: true,
                    include_explanations: true
                }
            },
            { headers }
        );

        this.findings = response.data.findings || [];
        this.currentFile = filePath;
        this.refresh();

        return response.data;
    }

    getFindings(): Finding[] {
        return this.findings;
    }

    clearFindings(): void {
        this.findings = [];
        this.refresh();
    }
}

class AnalysisItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(label, collapsibleState);
    }
}

class SeverityItem extends AnalysisItem {
    constructor(
        public readonly severity: 'critical' | 'high' | 'medium' | 'low' | 'info',
        public readonly count: number,
        collapsibleState: vscode.TreeItemCollapsibleState
    ) {
        super(`${severity.toUpperCase()} (${count})`, collapsibleState);
        
        this.iconPath = new vscode.ThemeIcon(
            'warning',
            new vscode.ThemeColor(`codesage.${severity}`)
        );
        
        this.contextValue = 'severity';
    }
}

class FindingItem extends AnalysisItem {
    constructor(public readonly finding: Finding) {
        super(finding.rule_name, vscode.TreeItemCollapsibleState.None);
        
        this.description = `Line ${finding.line_start}: ${finding.message.substring(0, 50)}...`;
        this.tooltip = finding.message;
        
        this.iconPath = new vscode.ThemeIcon(
            'circle-filled',
            new vscode.ThemeColor(`codesage.${finding.severity}`)
        );
        
        this.command = {
            command: 'vscode.open',
            title: 'Open File',
            arguments: [
                vscode.Uri.file(finding.file_path),
                {
                    selection: new vscode.Range(
                        finding.line_start - 1,
                        0,
                        finding.line_end - 1,
                        0
                    )
                }
            ]
        };
        
        this.contextValue = 'finding';
    }
}
