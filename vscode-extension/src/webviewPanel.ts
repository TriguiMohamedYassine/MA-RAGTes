import * as vscode from 'vscode';
import * as path from 'path';
import { ApiClient, RunRecord } from './apiClient';

export interface ContractInfo {
    name: string;
    path: string;
    size: string;
    modified: string;
}

export interface DashboardSnapshot {
    contract: ContractInfo | null;
    latestRun: RunRecord | null;
    history: RunRecord[];
    apiUrl: string;
    frontendUrl: string;
    apiHealthy: boolean;
    frontendHealthy: boolean;
    lastEnvironment: string;
    selectedRunId?: string;
}

export class maragtesPanel {
    public static currentPanel: maragtesPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private readonly _extensionUri: vscode.Uri;
    private _disposables: vscode.Disposable[] = [];
    private _rendered = false;

    private constructor(
        panel: vscode.WebviewPanel,
        extensionUri: vscode.Uri,
        private apiClient: ApiClient,
        private runId?: string,
        private isDashboard: boolean = false
    ) {
        this._panel = panel;
        this._extensionUri = extensionUri;

        this._panel.webview.onDidReceiveMessage(
            message => {
                void this.handleMessage(message);
            },
            null,
            this._disposables
        );

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    public static createOrShow(
        extensionUri: vscode.Uri,
        apiClient: ApiClient,
        runId?: string,
        isDashboard: boolean = false
    ): maragtesPanel {
        const column = vscode.ViewColumn.Two;

        if (maragtesPanel.currentPanel) {
            maragtesPanel.currentPanel._panel.reveal(column);
            return maragtesPanel.currentPanel;
        }

        const panel = vscode.window.createWebviewPanel(
            'maragtes',
            isDashboard ? 'MA-RAGTes Dashboard' : runId ? `Run: ${runId.substring(0, 8)}...` : 'MA-RAGTes',
            column,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'webview')]
            }
        );

        maragtesPanel.currentPanel = new maragtesPanel(panel, extensionUri, apiClient, runId, isDashboard);
        return maragtesPanel.currentPanel;
    }

    public show() {
        this._panel.reveal(vscode.ViewColumn.Two);
        if (!this._rendered) {
            this._panel.webview.html = this.getWebviewContent();
            this._rendered = true;
        }
    }

    public focusSection(section: 'status' | 'results' | 'history' | 'settings') {
        this.postMessage({
            type: 'focus-section',
            section
        });
    }

    public setDashboardSnapshot(snapshot: DashboardSnapshot) {
        this.postMessage({
            type: 'dashboard-state',
            snapshot
        });
    }

    public setActiveContract(contract: ContractInfo | null) {
        this.postMessage({
            type: 'contract-selected',
            contract
        });
    }

    public setSelectedEnvironment(environment: string) {
        this.postMessage({
            type: 'environment-selected',
            environment
        });
    }

    public setRunFocus(runId: string) {
        this.runId = runId;
        this.postMessage({
            type: 'focus-run',
            runId
        });
    }

    public setRunProgress(status: RunRecord) {
        this.postMessage({
            type: 'run-progress',
            status
        });
    }

    public setRunDetails(runId: string, details: any) {
        this.postMessage({
            type: 'run-details',
            runId,
            details
        });
    }

    public setApiClient(apiClient: ApiClient) {
        this.apiClient = apiClient;
    }

    public setError(message: string) {
        this.postMessage({
            type: 'error',
            message
        });
    }

    private postMessage(message: any) {
        void this._panel.webview.postMessage(message);
    }

    private async handleMessage(message: any) {
        switch (message.type) {
            case 'request-initial-data':
                await this.handleInitialData();
                break;
            case 'select-contract':
                await this.handleSelectContract();
                break;
            case 'select-user-story':
                await this.handleSelectUserStory();
                break;
            case 'submit-contract':
                await vscode.commands.executeCommand('maragtes.submitFromPanel', message);
                break;
            case 'open-dashboard':
                await vscode.commands.executeCommand('maragtes.openDashboard');
                break;
            case 'open-latest-result':
                await vscode.commands.executeCommand('maragtes.openLatestResult');
                break;
            case 'refresh-history':
                await vscode.commands.executeCommand('maragtes.refresh');
                break;
            case 'view-history':
                await vscode.commands.executeCommand('maragtes.viewHistory');
                break;
            case 'select-run':
                if (message.runId) {
                    await vscode.commands.executeCommand('maragtes.viewResults', { runId: message.runId });
                }
                break;
            case 'open-generated-test':
                await this.handleOpenGeneratedTest();
                break;
            case 'download-report':
                await this.handleDownloadReport(message.runId);
                break;
            case 'copy-test-code':
                await this.handleCopyTestCode(message.text);
                break;
            case 'open-contract-file':
                if (message.path) {
                    await this.handleOpenContractFile(message.path);
                }
                break;
            case 'save-settings':
                await this.handleSaveSettings(message.apiUrl, message.frontendUrl);
                break;
            case 'get-settings':
                await this.handleGetSettings();
                break;
            case 'save-llm-key':
                await this.handleSaveLlmKey(message.apiKey);
                break;
        }
    }

    private async handleInitialData() {
        const [contract, history, latestRun, apiHealthy] = await Promise.all([
            this.getContractInfo(),
            this.safeHistory(),
            this.safeLatestRun(),
            this.apiClient.checkApiHealth()
        ]);

        const config = vscode.workspace.getConfiguration('maragtes');
        const apiUrl = config.get('apiUrl', 'http://localhost:8000');
        const frontendUrl = config.get('frontendUrl', 'http://localhost:5173');
        const lastEnvironment = config.get('defaultEnvironment', 'simulation');
        const frontendHealthy = (await this.apiClient.checkFrontendReachable(frontendUrl)).reachable;

        const snapshot: DashboardSnapshot = {
            contract,
            latestRun,
            history,
            apiUrl,
            frontendUrl,
            apiHealthy,
            frontendHealthy,
            lastEnvironment,
            selectedRunId: this.runId
        };

        this.postMessage({
            type: 'dashboard-state',
            snapshot
        });

        await this.handleGetSettings();
    }

    private async handleSelectContract() {
        const picked = await vscode.window.showOpenDialog({
            canSelectMany: false,
            canSelectFiles: true,
            canSelectFolders: false,
            openLabel: 'Select contract',
            filters: {
                Solidity: ['sol']
            }
        });

        if (!picked || picked.length === 0) {
            return;
        }

        const contract = await this.readContractInfo(picked[0]);
        this.postMessage({
            type: 'contract-selected',
            contract
        });
    }

    private async handleSelectUserStory() {
        const picked = await vscode.window.showOpenDialog({
            canSelectMany: false,
            canSelectFiles: true,
            canSelectFolders: false,
            openLabel: 'Select user story file',
            filters: {
                Text: ['md', 'txt', 'json']
            }
        });

        if (!picked || picked.length === 0) {
            return;
        }

        const content = await vscode.workspace.fs.readFile(picked[0]);
        this.postMessage({
            type: 'user-story-selected',
            filePath: picked[0].fsPath,
            text: Buffer.from(content).toString('utf-8')
        });
    }

    private async handleOpenGeneratedTest() {
        const candidates = await vscode.workspace.findFiles('**/generated_test.js', '**/{node_modules,.git}/**', 20);
        if (candidates.length === 0) {
            vscode.window.showInformationMessage('generated_test.js not found in the workspace.');
            return;
        }

        const preferred = candidates.find(file => /[\\/]outputs[\\/]/i.test(file.fsPath)) ?? candidates[0];
        const document = await vscode.workspace.openTextDocument(preferred);
        await vscode.window.showTextDocument(document, { preview: false });
    }

    private async handleDownloadReport(runId?: string) {
        const targetRunId = runId || this.runId;
        if (!targetRunId) {
            vscode.window.showInformationMessage('No run is available to generate a report.');
            return;
        }

        const [results, status] = await Promise.all([
            this.apiClient.getResults(targetRunId).catch(() => null),
            this.apiClient.getRunStatus(targetRunId).catch(() => null)
        ]);

        const reportText = this.buildReportMarkdown(targetRunId, results, status);
        const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri;
        if (!workspaceRoot) {
            vscode.window.showWarningMessage('Cannot create a report without an open workspace.');
            return;
        }

        const outputUri = vscode.Uri.joinPath(workspaceRoot, 'outputs', `maragtes-report-${targetRunId}.md`);
        await vscode.workspace.fs.createDirectory(vscode.Uri.joinPath(workspaceRoot, 'outputs'));
        await vscode.workspace.fs.writeFile(outputUri, Buffer.from(reportText, 'utf-8'));

        const document = await vscode.workspace.openTextDocument(outputUri);
        await vscode.window.showTextDocument(document, { preview: false });
        vscode.window.showInformationMessage(`Report exported to ${vscode.workspace.asRelativePath(outputUri)}`);
    }

    private async handleOpenContractFile(filePath: string) {
        const fileUri = vscode.Uri.file(filePath);
        const document = await vscode.workspace.openTextDocument(fileUri);
        await vscode.window.showTextDocument(document, { preview: false });
    }

    private async handleCopyTestCode(text: string) {
        const normalized = typeof text === 'string' ? text.trim() : '';
        if (!normalized) {
            vscode.window.showWarningMessage('No test code to copy.');
            return;
        }

        await vscode.env.clipboard.writeText(text);
        vscode.window.showInformationMessage('Test code copied to clipboard.');
    }

    private async handleSaveSettings(apiUrl?: string, frontendUrl?: string) {
        const config = vscode.workspace.getConfiguration('maragtes');

        if (typeof apiUrl === 'string' && apiUrl.trim()) {
            await config.update('apiUrl', apiUrl.trim(), vscode.ConfigurationTarget.Global);
        }

        if (typeof frontendUrl === 'string' && frontendUrl.trim()) {
            await config.update('frontendUrl', frontendUrl.trim(), vscode.ConfigurationTarget.Global);
        }

        await this.handleGetSettings();
    }

    private async handleGetSettings() {
        const config = vscode.workspace.getConfiguration('maragtes');
        const apiUrl = config.get('apiUrl', 'http://localhost:8000');
        const frontendUrl = config.get('frontendUrl', 'http://localhost:3000');
        const defaultEnvironment = config.get('defaultEnvironment', 'simulation');

        this.postMessage({
            type: 'settings-loaded',
            apiUrl,
            frontendUrl,
            defaultEnvironment
        });
    }

    private async handleSaveLlmKey(apiKey?: string) {
        const normalized = typeof apiKey === 'string' ? apiKey.trim() : '';
        if (!normalized) {
            this.postMessage({
                type: 'llm-key-save-result',
                ok: false,
                message: 'Please enter a valid API key.'
            });
            return;
        }

        try {
            await this.apiClient.saveLlmApiKey(normalized);
            this.postMessage({
                type: 'llm-key-save-result',
                ok: true,
                message: 'LLM API key saved successfully.'
            });
        } catch (error: any) {
            this.postMessage({
                type: 'llm-key-save-result',
                ok: false,
                message: error?.message || 'Failed to save API key.'
            });
        }
    }

    private async safeHistory(): Promise<RunRecord[]> {
        try {
            return await this.apiClient.getHistory();
        } catch {
            return [];
        }
    }

    private async safeLatestRun(): Promise<RunRecord | null> {
        try {
            return await this.apiClient.getLatestRun();
        } catch {
            return null;
        }
    }

    private async getContractInfo(): Promise<ContractInfo | null> {
        const editor = vscode.window.activeTextEditor;

        if (!editor || !editor.document.fileName.toLowerCase().endsWith('.sol')) {
            return null;
        }

        return this.readContractInfo(editor.document.uri);
    }

    private buildReportMarkdown(runId: string, results: any, status: RunRecord | null): string {
        const summary = results?.summary || status?.summary || {};
        const coverage = summary?.coverage || {};
        const testCode = results?.test_code || '';
        const error = results?.error || status?.error || '';
        const contractName = results?.contract_name || status?.contract_name || 'UnknownContract';

        return [
            `# MA-RAGTes Report`,
            '',
            `- Run ID: ${runId}`,
            `- Contract: ${contractName}`,
            `- Status: ${status?.status || results?.status || 'unknown'}`,
            `- Started: ${status?.started_at || '-'}`,
            `- Finished: ${status?.finished_at || '-'}`,
            '',
            `## Quick Summary`,
            `- Tests total: ${summary?.total ?? 0}`,
            `- Passed: ${summary?.passed ?? 0}`,
            `- Failed: ${summary?.failed ?? 0}`,
            `- Coverage statements: ${Number(coverage?.statements ?? 0).toFixed(1)}%`,
            `- Coverage branches: ${Number(coverage?.branches ?? 0).toFixed(1)}%`,
            `- Coverage functions: ${Number(coverage?.functions ?? 0).toFixed(1)}%`,
            '',
            `## Error`,
            error || 'None',
            '',
            `## Generated Test`,
            '```javascript',
            testCode || '// No generated test code available',
            '```',
            ''
        ].join('\n');
    }

    private async readContractInfo(uri: vscode.Uri): Promise<ContractInfo> {
        const fileName = path.basename(uri.fsPath);

        try {
            const stat = await vscode.workspace.fs.stat(uri);
            return {
                name: fileName,
                path: uri.fsPath,
                size: `${(stat.size / 1024).toFixed(1)} KB`,
                modified: new Date(stat.mtime).toLocaleString()
            };
        } catch {
            return {
                name: fileName,
                path: uri.fsPath,
                size: 'Unknown',
                modified: 'Unknown'
            };
        }
    }

    private getWebviewContent(): string {
        const nonce = this.getNonce();
        const cssPath = vscode.Uri.joinPath(this._extensionUri, 'webview', 'styles.css');
        const jsPath = vscode.Uri.joinPath(this._extensionUri, 'webview', 'script.js');

        const cssUri = this._panel.webview.asWebviewUri(cssPath);
        const jsUri = this._panel.webview.asWebviewUri(jsPath);

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${this._panel.webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}'; img-src ${this._panel.webview.cspSource} https: data:;">
    <link rel="stylesheet" href="${cssUri}">
    <title>MA-RAGTes</title>
</head>
<body>
    <div class="app-shell">
        <header class="hero">
            <div>
                <div class="eyebrow">MA-RAGTes</div>
                <h1>Smart contract testing dashboard</h1>
                <p class="hero-copy">Submit a contract, track the pipeline live, and review results without leaving VS Code.</p>
            </div>
            <div class="hero-actions">
                <button id="selectContractBtn" class="btn btn-secondary">Select contract</button>
                <button id="submitBtn" class="btn btn-primary">Submit</button>
                <button id="openDashboardBtn" class="btn btn-secondary" type="button">Open Browser</button>
            </div>
        </header>

        <section id="inputsSection" class="grid-two">
            <article class="card">
                <div class="card-header">
                    <div>
                        <div class="card-kicker">Inputs</div>
                        <h2>User story</h2>
                    </div>
                </div>
                <div class="form-row">
                    <label for="userStoryInput">User story (optional)</label>
                    <textarea id="userStoryInput" rows="5" placeholder="Paste your user story here, or load it from a file."></textarea>
                    <div class="user-story-actions">
                        <button id="selectUserStoryBtn" class="btn btn-secondary" type="button">Load user story file</button>
                        <button id="latestResultBtn" class="btn btn-secondary" type="button">Open latest result</button>
                    </div>
                </div>
            </article>

            <article class="card" id="settingsSection">
                <div class="card-header">
                    <div>
                        <div class="card-kicker">Inputs</div>
                        <h2>LLM API key</h2>
                    </div>
                </div>
                <div class="form-row">
                    <label for="llmApiKeyInput">Mistral API key</label>
                    <input id="llmApiKeyInput" type="password" placeholder="mistral_api_key..." />
                </div>
                <div class="inline-actions">
                    <button id="saveLlmKeyBtn" class="btn btn-primary" type="button">Save API key</button>
                </div>
                <p id="llmKeyMessage" class="muted"></p>
            </article>
        </section>

        <section class="grid-two">
            <article id="statusSection" class="card">
                <div class="card-header">
                    <div>
                        <div class="card-kicker">Status</div>
                        <h2>Pipeline live</h2>
                    </div>
                    <span id="statusBadge" class="status-pill">idle</span>
                </div>
                <p id="statusMessage" class="muted"></p>
                <div id="progressBar" class="progress-track">
                    <div id="progressFill" class="progress-fill"></div>
                </div>
                <div id="pipelineTimeline" class="timeline"></div>
                <div id="runMeta" class="run-meta"></div>
            </article>

            <article class="card">
                <div class="card-header">
                    <div>
                        <div class="card-kicker">Summary</div>
                        <h2>Quick result</h2>
                    </div>
                    <button id="refreshHistoryBtn" class="text-button" type="button">Refresh</button>
                </div>
                <div id="quickSummary" class="summary-grid"></div>
                <div id="resultError" class="error-box hidden"></div>
            </article>
        </section>

        <section>
            <article class="card">
                <div class="card-header">
                    <div>
                        <div class="card-kicker">Current contract</div>
                        <h2>Selected file</h2>
                    </div>
                    <button id="openContractBtn" class="text-button" type="button">Open file</button>
                </div>
                <div id="contractInfo" class="stacked-data"></div>
                <div class="form-row">
                    <label for="environmentSelect">Environment</label>
                    <select id="environmentSelect">
                        <option value="simulation">simulation</option>
                        <option value="testnet">testnet</option>
                        <option value="mainnet">mainnet</option>
                    </select>
                </div>
            </article>
        </section>

        <section id="historySection" class="card">
            <div class="card-header">
                <div>
                    <div class="card-kicker">History</div>
                    <h2>Latest runs</h2>
                </div>
                <div class="history-controls">
                    <input id="historySearch" type="search" placeholder="Search by contract name" />
                    <select id="historyStatusFilter">
                        <option value="all">All statuses</option>
                        <option value="running">running</option>
                        <option value="completed">completed</option>
                        <option value="failed">failed</option>
                    </select>
                    <select id="historySort">
                        <option value="newest">Newest first</option>
                        <option value="oldest">Oldest first</option>
                    </select>
                    <button id="historyRefreshBtn" class="btn btn-secondary" type="button">Refresh</button>
                </div>
            </div>
            <div id="historyList" class="history-list"></div>
        </section>

        <section id="resultsSection" class="card">
            <div class="card-header">
                <div>
                    <div class="card-kicker">Run details</div>
                    <h2>Selected run</h2>
                </div>
                <div class="inline-actions">
                    <button id="rerunBtn" class="btn btn-secondary" type="button">Rerun</button>
                    <button id="copyCodeBtn" class="btn btn-secondary" type="button">Copy test code</button>
                    <button id="downloadReportBtn" class="btn btn-secondary" type="button">Download report</button>
                </div>
            </div>
            <div id="runDetailsMeta" class="summary-grid"></div>
            <pre id="runDetailsError" class="log-block hidden"></pre>
            <div class="code-block-wrap">
                <button id="copyCodeInlineBtn" class="copy-inline-btn" type="button">Copy</button>
                <pre id="runDetailsCode" class="code-block"></pre>
            </div>
            <pre id="runDetailsLogs" class="log-block"></pre>
        </section>

    </div>

    <script nonce="${nonce}" src="${jsUri}"></script>
</body>
</html>`;
    }

    private getNonce() {
        let text = '';
        const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        for (let i = 0; i < 32; i++) {
            text += possible.charAt(Math.floor(Math.random() * possible.length));
        }
        return text;
    }

    public dispose() {
        maragtesPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
}


