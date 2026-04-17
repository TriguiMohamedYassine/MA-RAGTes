import * as vscode from 'vscode';

export type SolidTestStatusState = 'idle' | 'submitting' | 'running' | 'done' | 'error';

export class StatusBar {
    private statusBar: vscode.StatusBarItem;

    constructor() {
        this.statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.showState('idle', 'SolidTest prêt');
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

    showState(state: SolidTestStatusState, message?: string): void {
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

    private getDefaultMessage(state: SolidTestStatusState): string {
        switch (state) {
            case 'submitting': return 'Soumission du contrat';
            case 'running': return 'Pipeline en cours';
            case 'done': return 'Dernier run terminé';
            case 'error': return 'Erreur SolidTest';
            case 'idle':
            default:
                return 'SolidTest prêt';
        }
    }

    private getIcon(state: SolidTestStatusState): string {
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

    private getTooltip(state: SolidTestStatusState, message: string): string {
        return `SolidTest - ${state}\n${message}`;
    }

    private getForegroundColor(state: SolidTestStatusState): vscode.ThemeColor | undefined {
        if (state === 'error') {
            return new vscode.ThemeColor('statusBarItem.errorForeground');
        }

        if (state === 'submitting' || state === 'running') {
            return new vscode.ThemeColor('statusBarItem.prominentForeground');
        }

        return undefined;
    }

    private getBackgroundColor(state: SolidTestStatusState): vscode.ThemeColor | undefined {
        if (state === 'error') {
            return new vscode.ThemeColor('statusBarItem.errorBackground');
        }

        if (state === 'submitting' || state === 'running') {
            return new vscode.ThemeColor('statusBarItem.prominentBackground');
        }

        return undefined;
    }
}
