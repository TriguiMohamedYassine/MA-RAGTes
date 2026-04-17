import * as vscode from 'vscode';
import { ApiClient, RunRecord } from './apiClient';

export class HistoryProvider implements vscode.TreeDataProvider<RunItem>, vscode.Disposable {
    private _onDidChangeTreeData: vscode.EventEmitter<RunItem | undefined | null | void> =
        new vscode.EventEmitter<RunItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<RunItem | undefined | null | void> =
        this._onDidChangeTreeData.event;

    private runs: RunRecord[] = [];
    private lastError: string | null = null;
    private refreshInterval: ReturnType<typeof setInterval> | null = null;

    constructor(private apiClient: ApiClient) {
        this.loadHistory();
        this.startAutoRefresh();
    }

    async refresh(): Promise<void> {
        await this.loadHistory();
        this._onDidChangeTreeData.fire(undefined);
    }

    private startAutoRefresh(): void {
        const config = vscode.workspace.getConfiguration('solidtest');
        if (config.get('autoRefresh', true)) {
            const interval = config.get('refreshInterval', 5000);
            this.refreshInterval = setInterval(() => {
                this.refresh();
            }, interval as number);
        }
    }

    private async loadHistory(): Promise<void> {
        try {
            this.runs = await this.apiClient.getHistory();
            this.lastError = null;
        } catch (error) {
            this.lastError = error instanceof Error ? error.message : 'API inaccessible';
            this.runs = [];
        }
    }

    getTreeItem(element: RunItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: RunItem): Thenable<RunItem[]> {
        if (!element) {
            if (this.lastError) {
                return Promise.resolve([
                    new RunItem('API inaccessible', 'error', 0, undefined, undefined, undefined, undefined, this.lastError || undefined)
                ]);
            }

            // N'afficher que les groupes avec au moins 1 run
            const groups = [
                new RunItem('En cours', 'running', this.runs.filter(r => r.status === 'running').length),
                new RunItem('Terminés', 'done', this.runs.filter(r => r.status === 'done').length),
                new RunItem('Échoués', 'error', this.runs.filter(r => r.status === 'error').length)
            ].filter(item => item.count > 0);

            return Promise.resolve(groups);
        }

        if (
            element.collapsibleState === vscode.TreeItemCollapsibleState.Collapsed ||
            element.collapsibleState === vscode.TreeItemCollapsibleState.Expanded
        ) {
            const filtered = this.runs.filter(r => r.status === element.statusKey);

            return Promise.resolve(
                filtered.map(run => new RunItem(
                    `${run.status === 'running' ? '⏳' : run.status === 'done' ? '✓' : '✕'} ${run.contract_name || 'UnknownContract'} · ${run.run_id.substring(0, 8)}...`,
                    'run',
                    0,
                    run.run_id,
                    run.status,
                    run.contract_name,
                    run.started_at,
                    run.error || undefined
                ))
            );
        }

        return Promise.resolve([]);
    }

    dispose(): void {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
}

export class RunItem extends vscode.TreeItem {
    public readonly statusKey: string;

    constructor(
        public readonly label: string,
        public readonly contextValue: string,
        public readonly count: number,
        public readonly runId?: string,
        public readonly status?: string,
        public readonly contractName?: string,
        public readonly startedAt?: string,
        public readonly error?: string
    ) {
        super(label);
        this.statusKey = status || contextValue;

        if (contextValue === 'run') {
            this.contextValue = status || 'run';
            this.description = `${contractName || 'UnknownContract'} · ${this.formatDate(startedAt)}`;
            this.tooltip = `Run ID: ${runId}\nContrat: ${contractName || 'UnknownContract'}\nStatus: ${status}${error ? `\nErreur: ${error}` : ''}`;
            this.collapsibleState = vscode.TreeItemCollapsibleState.None;
            this.command = {
                command: 'solidtest.viewResults',
                title: 'Voir les résultats',
                arguments: [this]
            };
        } else if (contextValue === 'error' && runId === undefined) {
            this.contextValue = 'error';
            this.description = error || 'Impossible de charger l’historique';
            this.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else {
            this.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
            this.description = `${count} test(s)`;
            this.iconPath = this.getIcon();
        }
    }

    private formatDate(value?: string): string {
        if (!value) {
            return 'Date inconnue';
        }

        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) {
            return value;
        }

        return parsed.toLocaleString();
    }

    private getIcon(): vscode.ThemeIcon {
        switch (this.label) {
            case 'En cours':   return new vscode.ThemeIcon('sync');
            case 'Terminés':   return new vscode.ThemeIcon('check');
            case 'Échoués':    return new vscode.ThemeIcon('error');
            case 'API inaccessible': return new vscode.ThemeIcon('warning');
            default:           return new vscode.ThemeIcon('file');
        }
    }

    private getRunIcon(status?: string): string {
        switch (status) {
            case 'running': return '⏳';
            case 'done': return '✓';
            case 'error': return '✕';
            default: return '•';
        }
    }
}