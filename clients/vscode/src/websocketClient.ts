import * as vscode from 'vscode';
import WebSocket from 'ws';

export class WebSocketClient {
    private ws: WebSocket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 5000;
    private pingInterval: NodeJS.Timeout | null = null;

    async connect(url: string, apiKey?: string): Promise<void> {
        return new Promise((resolve, reject) => {
            try {
                // Convert http to ws
                const wsUrl = url.replace(/^http/, 'ws') + '/ws';
                
                const headers: Record<string, string> = {};
                if (apiKey) {
                    headers['Authorization'] = `Bearer ${apiKey}`;
                }

                this.ws = new WebSocket(wsUrl, { headers });

                this.ws.on('open', () => {
                    console.log('WebSocket connected');
                    this.reconnectAttempts = 0;
                    this.startPingInterval();
                    resolve();
                });

                this.ws.on('message', (data: WebSocket.Data) => {
                    this.handleMessage(data.toString());
                });

                this.ws.on('error', (error: Error) => {
                    console.error('WebSocket error:', error);
                    reject(error);
                });

                this.ws.on('close', () => {
                    console.log('WebSocket closed');
                    this.stopPingInterval();
                    this.attemptReconnect(url, apiKey);
                });

            } catch (error) {
                reject(error);
            }
        });
    }

    disconnect(): void {
        this.stopPingInterval();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    private handleMessage(data: string): void {
        try {
            const message = JSON.parse(data);
            
            switch (message.type) {
                case 'analysis_update':
                    this.handleAnalysisUpdate(message);
                    break;
                case 'notification':
                    this.handleNotification(message);
                    break;
                case 'pong':
                    // Ping response, do nothing
                    break;
                default:
                    console.log('Unknown message type:', message.type);
            }
        } catch (error) {
            console.error('Failed to parse message:', error);
        }
    }

    private handleAnalysisUpdate(message: any): void {
        const { analysis_id, status, progress } = message;
        
        if (status === 'completed') {
            vscode.window.showInformationMessage(
                `Analysis ${analysis_id} completed`,
                'View Results'
            ).then(selection => {
                if (selection === 'View Results') {
                    vscode.commands.executeCommand('codesage.showResults');
                }
            });
        } else if (status === 'failed') {
            vscode.window.showErrorMessage(`Analysis ${analysis_id} failed: ${message.error}`);
        }
    }

    private handleNotification(message: any): void {
        const { level, text } = message;
        
        switch (level) {
            case 'info':
                vscode.window.showInformationMessage(text);
                break;
            case 'warning':
                vscode.window.showWarningMessage(text);
                break;
            case 'error':
                vscode.window.showErrorMessage(text);
                break;
        }
    }

    private startPingInterval(): void {
        this.pingInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);
    }

    private stopPingInterval(): void {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    private attemptReconnect(url: string, apiKey?: string): void {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            vscode.window.showErrorMessage(
                'Lost connection to CodeSage server. Please check your connection and try again.',
                'Reconnect'
            ).then(selection => {
                if (selection === 'Reconnect') {
                    this.reconnectAttempts = 0;
                    this.connect(url, apiKey);
                }
            });
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * this.reconnectAttempts;
        
        console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
        
        setTimeout(() => {
            this.connect(url, apiKey).catch(() => {
                // Reconnection failed, will try again
            });
        }, delay);
    }

    subscribeToAnalysis(analysisId: string): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                type: 'subscribe',
                analysis_id: analysisId
            }));
        }
    }
}
