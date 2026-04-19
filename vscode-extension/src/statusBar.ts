import * as vscode from 'vscode';

export type maragtesStatusState = 'idle' | 'submitting' | 'running' | 'done' | 'error';

export class StatusBar {
    private statusBar: vscode.StatusBarItem;

    constructor() {
        this.statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.showState('idle', 'MA-RAGTes ready');
    }

    show(message: string, color?: string): void {
        if (color === 'green') {
            this.showState('done', message);
            return;
        }

        if (color === 'red') {
            this.showState('error', message);
            return;
        }

        if (color === 'blue') {
            this.showState('running', message);
            return;
        }

        this.statusBar.text = `$(beaker) ${message}`;
        this.statusBar.backgroundColor = undefined;
        this.statusBar.color = undefined;
        this.statusBar.show();
    }

    showState(state: maragtesStatusState, message?: string): void {
        const label = message || this.getDefaultMessage(state);
        const icon = this.getIcon(state);

        this.statusBar.text = `${icon} ${label}`;
        this.statusBar.tooltip = this.getTooltip(state, label);
        this.statusBar.color = this.getForegroundColor(state);
        this.statusBar.backgroundColor = this.getBackgroundColor(state);
        this.statusBar.show();
    }

    hide(): void {
        this.statusBar.hide();
    }

    dispose(): void {
        this.statusBar.dispose();
    }

    private getDefaultMessage(state: maragtesStatusState): string {
        switch (state) {
            case 'submitting': return 'Submitting contract';
            case 'running': return 'Pipeline running';
            case 'done': return 'Last run completed';
            case 'error': return 'MA-RAGTes error';
            case 'idle':
            default:
                return 'MA-RAGTes ready';
        }
    }

    private getIcon(state: maragtesStatusState): string {
        switch (state) {
            case 'submitting': return '$(cloud-upload)';
            case 'running': return '$(sync~spin)';
            case 'done': return '$(check)';
            case 'error': return '$(error)';
            case 'idle':
            default:
                return '$(beaker)';
        }
    }

    private getTooltip(state: maragtesStatusState, message: string): string {
        return `MA-RAGTes - ${state}\n${message}`;
    }

    private getForegroundColor(state: maragtesStatusState): vscode.ThemeColor | undefined {
        if (state === 'error') {
            return new vscode.ThemeColor('statusBarItem.errorForeground');
        }

        if (state === 'submitting' || state === 'running') {
            return new vscode.ThemeColor('statusBarItem.prominentForeground');
        }

        return undefined;
    }

    private getBackgroundColor(state: maragtesStatusState): vscode.ThemeColor | undefined {
        if (state === 'error') {
            return new vscode.ThemeColor('statusBarItem.errorBackground');
        }

        if (state === 'submitting' || state === 'running') {
            return new vscode.ThemeColor('statusBarItem.prominentBackground');
        }

        return undefined;
    }
}


