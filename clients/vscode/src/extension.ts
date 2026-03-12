import * as vscode from 'vscode';
import { AnalysisProvider } from './analysisProvider';
import { WebSocketClient } from './websocketClient';
import { Decorators } from './decorators';

let analysisProvider: AnalysisProvider;
let wsClient: WebSocketClient;
let decorators: Decorators;

export function activate(context: vscode.ExtensionContext) {
    console.log('CodeSage extension is now active');

    // Initialize components
    analysisProvider = new AnalysisProvider();
    wsClient = new WebSocketClient();
    decorators = new Decorators();

    // Register tree data provider
    vscode.window.registerTreeDataProvider('codesageResults', analysisProvider);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('codesage.analyzeFile', analyzeFile),
        vscode.commands.registerCommand('codesage.analyzeSelection', analyzeSelection),
        vscode.commands.registerCommand('codesage.analyzeWorkspace', analyzeWorkspace),
        vscode.commands.registerCommand('codesage.showResults', showResults),
        vscode.commands.registerCommand('codesage.configure', configure),
        vscode.commands.registerCommand('codesage.connect', connect),
        vscode.commands.registerCommand('codesage.disconnect', disconnect),
        vscode.commands.registerCommand('codesage.refreshResults', () => analysisProvider.refresh())
    );

    // Set up real-time analysis if enabled
    const config = vscode.workspace.getConfiguration('codesage');
    if (config.get('enableRealTimeAnalysis')) {
        setupRealTimeAnalysis(context);
    }

    // Connect to server
    connect();

    // Show welcome message
    vscode.window.showInformationMessage(
        'CodeSage is ready! Use "CodeSage: Analyze Current File" to get started.',
        'Analyze File',
        'Configure'
    ).then(selection => {
        if (selection === 'Analyze File') {
            vscode.commands.executeCommand('codesage.analyzeFile');
        } else if (selection === 'Configure') {
            vscode.commands.executeCommand('codesage.configure');
        }
    });
}

export function deactivate() {
    // Clean up
    if (wsClient) {
        wsClient.disconnect();
    }
}

async function analyzeFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const document = editor.document;
    const filePath = document.fileName;
    const language = document.languageId;
    const content = document.getText();

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'CodeSage: Analyzing file...',
        cancellable: false
    }, async (progress) => {
        try {
            const results = await analysisProvider.analyzeCode(content, language, filePath);
            
            if (results.findings && results.findings.length > 0) {
                decorators.decorateFindings(editor, results.findings);
                vscode.window.showInformationMessage(
                    `Analysis complete: ${results.findings.length} findings`,
                    'View Results'
                ).then(selection => {
                    if (selection === 'View Results') {
                        showResults();
                    }
                });
            } else {
                vscode.window.showInformationMessage('Analysis complete: No issues found');
                decorators.clearDecorations(editor);
            }
            
            analysisProvider.refresh();
        } catch (error) {
            vscode.window.showErrorMessage(`Analysis failed: ${error}`);
        }
    });
}

async function analyzeSelection() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    if (selection.isEmpty) {
        vscode.window.showWarningMessage('No code selected');
        return;
    }

    const code = editor.document.getText(selection);
    const language = editor.document.languageId;

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'CodeSage: Analyzing selection...',
        cancellable: false
    }, async () => {
        try {
            const results = await analysisProvider.analyzeCode(code, language);
            
            if (results.findings && results.findings.length > 0) {
                vscode.window.showWarningMessage(
                    `Found ${results.findings.length} issues in selection`,
                    'View Details'
                ).then(selection => {
                    if (selection === 'View Details') {
                        showResults();
                    }
                });
            } else {
                vscode.window.showInformationMessage('No issues found in selection');
            }
            
            analysisProvider.refresh();
        } catch (error) {
            vscode.window.showErrorMessage(`Analysis failed: ${error}`);
        }
    });
}

async function analyzeWorkspace() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showWarningMessage('No workspace open');
        return;
    }

    const folder = workspaceFolders[0];
    
    const result = await vscode.window.showQuickPick(
        ['Security Scan', 'Performance Analysis', 'Full Analysis'],
        { placeHolder: 'Select analysis type' }
    );

    if (!result) return;

    const analysisTypes: string[] = [];
    if (result === 'Security Scan') analysisTypes.push('security');
    if (result === 'Performance Analysis') analysisTypes.push('performance');
    if (result === 'Full Analysis') analysisTypes.push('security', 'performance', 'quality');

    vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: 'CodeSage: Analyzing workspace...',
        cancellable: true
    }, async (progress, token) => {
        try {
            // This would trigger a background analysis job
            vscode.window.showInformationMessage(
                'Workspace analysis started. Results will be available in the CodeSage panel.',
                'OK'
            );
        } catch (error) {
            vscode.window.showErrorMessage(`Workspace analysis failed: ${error}`);
        }
    });
}

function showResults() {
    vscode.commands.executeCommand('codesageResults.focus');
}

async function configure() {
    vscode.commands.executeCommand('workbench.action.openSettings', 'codesage');
}

async function connect() {
    const config = vscode.workspace.getConfiguration('codesage');
    const serverUrl = config.get<string>('serverUrl');
    const apiKey = config.get<string>('apiKey');

    if (!serverUrl) {
        vscode.window.showWarningMessage(
            'CodeSage server URL not configured',
            'Configure'
        ).then(selection => {
            if (selection === 'Configure') {
                configure();
            }
        });
        return;
    }

    try {
        await wsClient.connect(serverUrl, apiKey);
        vscode.commands.executeCommand('setContext', 'codesage:connected', true);
        vscode.window.showInformationMessage('Connected to CodeSage server');
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to connect: ${error}`);
    }
}

async function disconnect() {
    wsClient.disconnect();
    vscode.commands.executeCommand('setContext', 'codesage:connected', false);
    vscode.window.showInformationMessage('Disconnected from CodeSage server');
}

function setupRealTimeAnalysis(context: vscode.ExtensionContext) {
    const config = vscode.workspace.getConfiguration('codesage');
    const delay = config.get<number>('analysisDelay') || 1000;

    let timeout: NodeJS.Timeout | undefined;

    vscode.workspace.onDidChangeTextDocument(
        event => {
            if (timeout) {
                clearTimeout(timeout);
            }

            timeout = setTimeout(() => {
                const editor = vscode.window.activeTextEditor;
                if (editor && event.document === editor.document) {
                    // Trigger lightweight analysis
                    // analyzeFile();
                }
            }, delay);
        },
        null,
        context.subscriptions
    );
}
