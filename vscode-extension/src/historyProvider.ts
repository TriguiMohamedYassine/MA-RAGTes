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

    setApiClient(apiClient: ApiClient): void {
        this.apiClient = apiClient;
        void this.refresh();
    }

    async refresh(): Promise<void> {
        await this.loadHistory();
        this._onDidChangeTreeData.fire(undefined);
    }

    private startAutoRefresh(): void {
        const config = vscode.workspace.getConfiguration('maragtes');
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
            this.lastError = error instanceof Error ? error.message : 'API unreachable';
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
                    new RunItem('API unreachable', 'error', 0, undefined, undefined, undefined, undefined, this.lastError || undefined)
                ]);
            }

            // Show only groups that contain at least one run.
            const groups = [
                new RunItem('Running', 'running', this.runs.filter(r => r.status === 'running').length),
                new RunItem('Completed', 'done', this.runs.filter(r => r.status === 'done').length),
                new RunItem('Failed', 'error', this.runs.filter(r => r.status === 'error').length)
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
            this.tooltip = `Run ID: ${runId}\nContract: ${contractName || 'UnknownContract'}\nStatus: ${status}${error ? `\nError: ${error}` : ''}`;
            this.collapsibleState = vscode.TreeItemCollapsibleState.None;
            this.command = {
                command: 'maragtes.viewResults',
                title: 'View results',
                arguments: [this]
            };
        } else if (contextValue === 'error' && runId === undefined) {
            this.contextValue = 'error';
            this.description = error || 'Failed to load history';
            this.collapsibleState = vscode.TreeItemCollapsibleState.None;
        } else {
            this.collapsibleState = vscode.TreeItemCollapsibleState.Collapsed;
            this.description = `${count} test(s)`;
            this.iconPath = this.getIcon();
        }
    }

    private formatDate(value?: string): string {
        if (!value) {
            return 'Unknown date';
        }

        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) {
            return value;
        }

        return parsed.toLocaleString();
    }

    private getIcon(): vscode.ThemeIcon {
        switch (this.label) {
            case 'Running':   return new vscode.ThemeIcon('sync');
            case 'Completed': return new vscode.ThemeIcon('check');
            case 'Failed': return new vscode.ThemeIcon('error');
            case 'API unreachable': return new vscode.ThemeIcon('warning');
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


