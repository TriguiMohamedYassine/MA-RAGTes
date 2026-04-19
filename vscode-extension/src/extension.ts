import * as vscode from 'vscode';
import * as path from 'path';
import { maragtesPanel } from './webviewPanel';
import { HistoryProvider, RunItem } from './historyProvider';
import { ApiClient, ContractSubmission, RunRecord } from './apiClient';
import { StatusBar } from './statusBar';

const DEFAULT_API_URL = 'http://localhost:8000';
const DEFAULT_FRONTEND_URL = 'http://localhost:3000';
const LAST_ENVIRONMENT_KEY = 'maragtes.lastEnvironment';
const HISTORY_REFRESH_DELAY_MS = 1000;

let apiClient: ApiClient;
let historyProvider: HistoryProvider;
let statusBar: StatusBar;
let pollTimer: ReturnType<typeof setInterval> | undefined;

interface ContractContext {
    contractCode: string;
    contractName: string;
    contractPath: string;
    uri: vscode.Uri;
}

interface DashboardSnapshot {
    contract: {
        name: string;
        path: string;
        size: string;
        modified: string;
    } | null;
    latestRun: RunRecord | null;
    history: RunRecord[];
    apiUrl: string;
    frontendUrl: string;
    apiHealthy: boolean;
    frontendHealthy: boolean;
    lastEnvironment: string;
    selectedRunId?: string;
}

interface SubmissionPayload {
    uri?: string;
    contractPath?: string;
    environment?: string;
    userStory?: string;
}

export async function activate(context: vscode.ExtensionContext) {
    console.log('maragtes extension is now active!');

    const config = vscode.workspace.getConfiguration('maragtes');
    apiClient = new ApiClient(config.get('apiUrl', DEFAULT_API_URL));
    statusBar = new StatusBar();
    historyProvider = new HistoryProvider(apiClient);

    context.subscriptions.push(historyProvider);
    vscode.window.registerTreeDataProvider('maragtesExplorer', historyProvider);

    const submitCommand = vscode.commands.registerCommand('maragtes.submitContract', async (payload?: vscode.Uri | SubmissionPayload) => {
        await handleOpenSubmitPanel(context, payload);
    });

    const submitCurrentContractCommand = vscode.commands.registerCommand('maragtes.submitCurrentContract', async () => {
        await handleOpenSubmitPanel(context);
    });

    const submitFromPanelCommand = vscode.commands.registerCommand('maragtes.submitFromPanel', async (payload?: vscode.Uri | SubmissionPayload) => {
        await handleSubmitContract(context, payload);
    });

    const viewHistoryCommand = vscode.commands.registerCommand('maragtes.viewHistory', async () => {
        await handleViewHistory(context);
    });

    const openDashboardCommand = vscode.commands.registerCommand('maragtes.openDashboard', async () => {
        await handleOpenDashboard();
    });

    const openLatestResultCommand = vscode.commands.registerCommand('maragtes.openLatestResult', async () => {
        await handleOpenLatestResult(context);
    });

    const settingsCommand = vscode.commands.registerCommand('maragtes.settings', async () => {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'maragtes');
    });

    const viewResultsCommand = vscode.commands.registerCommand('maragtes.viewResults', async (item: RunItem) => {
        if (item?.runId) {
            await handleViewResults(context, item.runId);
        }
    });

    const refreshCommand = vscode.commands.registerCommand('maragtes.refresh', async () => {
        await historyProvider.refresh();
    });

    const runNowCommand = vscode.commands.registerCommand('maragtes.runTestNow', async (item?: RunItem) => {
        await handleRunNow(context, item);
    });

    context.subscriptions.push(
        submitCommand,
        submitCurrentContractCommand,
        submitFromPanelCommand,
        viewHistoryCommand,
        openDashboardCommand,
        openLatestResultCommand,
        settingsCommand,
        viewResultsCommand,
        refreshCommand,
        runNowCommand
    );

    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration(async event => {
        if (!event.affectsConfiguration('maragtes.apiUrl')) {
            return;
        }

        const updatedConfig = vscode.workspace.getConfiguration('maragtes');
        apiClient = new ApiClient(updatedConfig.get('apiUrl', DEFAULT_API_URL));
        historyProvider.setApiClient(apiClient);

        if (maragtesPanel.currentPanel) {
            maragtesPanel.currentPanel.setApiClient(apiClient);
        }

        await refreshDashboardSnapshot(context);
    }));

    statusBar.showState('idle', 'MA-RAGTes ready');
    void refreshDashboardSnapshot(context);
    vscode.window.showInformationMessage('MA-RAGTes ready. Open a .sol file to start a run.');
}

async function handleOpenSubmitPanel(
    context: vscode.ExtensionContext,
    payload?: vscode.Uri | SubmissionPayload
) {
    const panel = maragtesPanel.createOrShow(context.extensionUri, apiClient);
    panel.show();
    panel.focusSection('status');

    const uri = payload instanceof vscode.Uri
        ? payload
        : payload?.uri
            ? vscode.Uri.file(payload.uri)
            : payload?.contractPath
                ? vscode.Uri.file(payload.contractPath)
            : undefined;

    const contract = await resolveContractContext(context, uri);
    if (!contract) {
        panel.setError('No Solidity contract selected.');
        return;
    }

    const preferredEnvironment = getPreferredEnvironment(context);
    panel.setSelectedEnvironment(preferredEnvironment);
    panel.setActiveContract({
        name: contract.contractName,
        path: contract.contractPath,
        size: '-',
        modified: '-'
    });

    statusBar.showState('idle', `Ready to submit ${contract.contractName}`);
    await refreshDashboardSnapshot(context);
}

async function handleSubmitContract(
    context: vscode.ExtensionContext,
    payload?: vscode.Uri | SubmissionPayload
) {
    const panel = maragtesPanel.createOrShow(context.extensionUri, apiClient);
    panel.show();
    panel.focusSection('status');

    try {
        const uri = payload instanceof vscode.Uri
            ? payload
            : payload?.uri
                ? vscode.Uri.file(payload.uri)
                : payload?.contractPath
                    ? vscode.Uri.file(payload.contractPath)
                : undefined;
        const contract = await resolveContractContext(context, uri);
        if (!contract) {
            panel.setError('No Solidity contract selected.');
            return;
        }

        const explicitEnvironment = payload && !(payload instanceof vscode.Uri)
            ? payload.environment
            : undefined;
        const userStory = payload && !(payload instanceof vscode.Uri)
            ? (payload.userStory || '').trim()
            : '';
        const environment = explicitEnvironment || await resolveEnvironment(context);
        if (!environment) {
            statusBar.showState('idle', 'Submission cancelled');
            panel.setError('Submission cancelled. No environment selected.');
            return;
        }

        panel.setSelectedEnvironment(environment);
        panel.setActiveContract({
            name: contract.contractName,
            path: contract.contractPath,
            size: '-',
            modified: '-'
        });

        statusBar.showState('submitting', `Submitting ${contract.contractName}...`);

        const submission: ContractSubmission = {
            contractCode: contract.contractCode,
            contractName: contract.contractName,
            environment,
            userStory
        };

        const response = await apiClient.submitContract(submission);
        if (response.status === 'error' || !response.run_id) {
            const message = response.message || 'Submission failed';
            vscode.window.showErrorMessage(message);
            statusBar.showState('error', message);
            panel.setError(message);
            await refreshDashboardSnapshot(context);
            return;
        }

        await context.workspaceState.update(LAST_ENVIRONMENT_KEY, environment);
        statusBar.showState('running', `Run ${shortRunId(response.run_id)} running`);

        panel.setRunFocus(response.run_id);

        vscode.window.showInformationMessage(`Run lancé: ${response.run_id}`);
        void historyProvider.refresh();
        void refreshDashboardSnapshot(context, response.run_id);
        void watchRun(context, response.run_id, panel);
    } catch (error) {
        const message = formatError(error, DEFAULT_API_URL, 'Failed to submit contract');
        vscode.window.showErrorMessage(message);
        statusBar.showState('error', message);
        panel.setError(message);
        await refreshDashboardSnapshot(context);
    }
}

async function handleViewHistory(context: vscode.ExtensionContext) {
    const panel = maragtesPanel.createOrShow(context.extensionUri, apiClient);
    panel.show();
    panel.focusSection('history');
    await refreshDashboardSnapshot(context);
}

async function handleOpenDashboard() {
    const config = vscode.workspace.getConfiguration('maragtes');
    const frontendUrl = config.get('frontendUrl', DEFAULT_FRONTEND_URL);
    const reachability = await apiClient.checkFrontendReachable(frontendUrl);
    if (reachability.reachable) {
        await vscode.env.openExternal(vscode.Uri.parse(frontendUrl));
        return;
    }

    const fallbackUrl = frontendUrl.includes('5173')
        ? frontendUrl.replace('5173', '3000')
        : frontendUrl.replace('3000', '5173');

    const fallbackReachability = await apiClient.checkFrontendReachable(fallbackUrl);
    if (fallbackReachability.reachable) {
        await config.update('frontendUrl', fallbackUrl, vscode.ConfigurationTarget.Global);
        await vscode.env.openExternal(vscode.Uri.parse(fallbackUrl));
        vscode.window.showInformationMessage(`Dashboard opened at ${fallbackUrl}.`);
        return;
    }

    vscode.window.showWarningMessage(`Dashboard unavailable, start frontend on ${frontendUrl} ou ${fallbackUrl}.`);
}

async function handleOpenLatestResult(context: vscode.ExtensionContext) {
    const latestRun = await safeLatestRun();
    if (!latestRun) {
        vscode.window.showInformationMessage('No run available at the moment.');
        return;
    }

    const panel = maragtesPanel.createOrShow(context.extensionUri, apiClient, latestRun.run_id);
    panel.show();
    panel.focusSection('results');
    panel.setRunFocus(latestRun.run_id);
    await renderRunDetails(panel, latestRun.run_id, latestRun);
}

async function handleViewResults(context: vscode.ExtensionContext, runId: string) {
    const panel = maragtesPanel.createOrShow(context.extensionUri, apiClient, runId);
    panel.show();
    panel.focusSection('results');
    panel.setRunFocus(runId);

    try {
        const details = await apiClient.getResults(runId);
        panel.setRunDetails(runId, details);
    } catch (error) {
        const run = await safeRunStatus(runId);
        const fallback = run ?? { run_id: runId, status: 'error', error: formatError(error, DEFAULT_API_URL, 'Failed to load results') };
        panel.setRunDetails(runId, fallback);
        vscode.window.showWarningMessage(fallback.error || 'Failed to load results.');
    }
}

async function handleRunNow(context: vscode.ExtensionContext, item?: RunItem) {
    if (item?.contractName) {
        const located = await findContractByName(item.contractName);
        if (located) {
            await handleSubmitContract(context, located);
            return;
        }
    }

    await handleSubmitContract(context);
}

async function resolveContractContext(context: vscode.ExtensionContext, uri?: vscode.Uri): Promise<ContractContext | null> {
    const resolvedUri = uri ?? vscode.window.activeTextEditor?.document.uri ?? null;

    if (resolvedUri && resolvedUri.fsPath.toLowerCase().endsWith('.sol')) {
        return buildContractContext(resolvedUri);
    }

    const activeEditor = vscode.window.activeTextEditor;
    if (activeEditor?.document.fileName.toLowerCase().endsWith('.sol')) {
        return buildContractContext(activeEditor.document.uri);
    }

    const picked = await pickContractFile();
    if (!picked) {
        vscode.window.showInformationMessage('No Solidity contract selected. Open a .sol file then retry MA-RAGTes.');
        return null;
    }

    return buildContractContext(picked);
}

async function buildContractContext(uri: vscode.Uri): Promise<ContractContext> {
    const content = await vscode.workspace.fs.readFile(uri);
    const contractCode = Buffer.from(content).toString('utf-8');
    const contractName = path.basename(uri.fsPath).replace(/\.sol$/i, '');

    return {
        contractCode,
        contractName,
        contractPath: uri.fsPath,
        uri
    };
}

async function pickContractFile(): Promise<vscode.Uri | undefined> {
    const files = await vscode.workspace.findFiles('**/*.sol', '**/{node_modules,.git,artifacts,cache}/**', 50);
    if (files.length === 0) {
        return undefined;
    }

    if (files.length === 1) {
        return files[0];
    }

    const selection = await vscode.window.showQuickPick(
        files.map(file => ({
            label: path.basename(file.fsPath),
            description: vscode.workspace.asRelativePath(file.fsPath),
            uri: file
        })),
        {
            title: 'Choose a Solidity contract',
            placeHolder: 'Select the .sol file to submit'
        }
    );

    return selection?.uri;
}

async function resolveEnvironment(context: vscode.ExtensionContext): Promise<string | undefined> {
    const config = vscode.workspace.getConfiguration('maragtes');
    const lastEnvironment = context.workspaceState.get<string>(LAST_ENVIRONMENT_KEY);
    const defaultEnvironment = config.get('defaultEnvironment', 'simulation');

    if (lastEnvironment) {
        return lastEnvironment;
    }

    const picked = await vscode.window.showQuickPick(
        ['simulation', 'testnet', 'mainnet', 'custom...'],
        {
            title: 'Select execution environment',
            placeHolder: 'Environment used to run the pipeline',
            ignoreFocusOut: true,
            canPickMany: false
        }
    );

    if (!picked) {
        return undefined;
    }

    if (picked === 'custom...') {
        const custom = await vscode.window.showInputBox({
            title: 'Custom environment',
            prompt: 'Enter environment name',
            value: defaultEnvironment,
            ignoreFocusOut: true
        });
        return custom?.trim() || undefined;
    }

    return picked;
}

function getPreferredEnvironment(context: vscode.ExtensionContext): string {
    const config = vscode.workspace.getConfiguration('maragtes');
    return context.workspaceState.get<string>(LAST_ENVIRONMENT_KEY) || config.get('defaultEnvironment', 'simulation');
}

async function buildDashboardSnapshot(context: vscode.ExtensionContext, selectedRunId?: string): Promise<DashboardSnapshot> {
    const config = vscode.workspace.getConfiguration('maragtes');
    const apiUrl = config.get('apiUrl', DEFAULT_API_URL);
    const frontendUrl = config.get('frontendUrl', DEFAULT_FRONTEND_URL);
    const lastEnvironment = context.workspaceState.get<string>(LAST_ENVIRONMENT_KEY) || config.get('defaultEnvironment', 'simulation');

    const [contract, latestRun, history, apiHealthy] = await Promise.all([
        getActiveContractInfo(),
        safeLatestRun(),
        safeHistory(),
        safeApiHealth()
    ]);
    let effectiveFrontendUrl = frontendUrl;
    let frontendHealthy = (await apiClient.checkFrontendReachable(frontendUrl)).reachable;

    if (!frontendHealthy) {
        const fallbackUrl = frontendUrl.includes('5173')
            ? frontendUrl.replace('5173', '3000')
            : frontendUrl.replace('3000', '5173');
        const fallbackHealthy = (await apiClient.checkFrontendReachable(fallbackUrl)).reachable;
        if (fallbackHealthy) {
            effectiveFrontendUrl = fallbackUrl;
            frontendHealthy = true;
        }
    }

    return {
        contract,
        latestRun,
        history,
        apiUrl,
        frontendUrl: effectiveFrontendUrl,
        apiHealthy,
        frontendHealthy,
        lastEnvironment,
        selectedRunId
    };
}

async function refreshDashboardSnapshot(context: vscode.ExtensionContext, selectedRunId?: string): Promise<void> {
    const panel = maragtesPanel.currentPanel;
    if (!panel) {
        return;
    }

    const snapshot = await buildDashboardSnapshot(context, selectedRunId);
    panel.setDashboardSnapshot(snapshot);
}

async function getActiveContractInfo(): Promise<DashboardSnapshot['contract']> {
    const editor = vscode.window.activeTextEditor;
    if (!editor || !editor.document.fileName.toLowerCase().endsWith('.sol')) {
        return null;
    }

    try {
        const stat = await vscode.workspace.fs.stat(editor.document.uri);
        return {
            name: path.basename(editor.document.fileName),
            path: editor.document.fileName,
            size: `${(stat.size / 1024).toFixed(1)} KB`,
            modified: new Date(stat.mtime).toLocaleString()
        };
    } catch {
        return {
            name: path.basename(editor.document.fileName),
            path: editor.document.fileName,
            size: 'Unknown',
            modified: 'Unknown'
        };
    }
}

async function safeHistory(): Promise<RunRecord[]> {
    try {
        return await apiClient.getHistory();
    } catch {
        return [];
    }
}

async function safeLatestRun(): Promise<RunRecord | null> {
    try {
        return await apiClient.getLatestRun();
    } catch {
        return null;
    }
}

async function safeRunStatus(runId: string): Promise<RunRecord | null> {
    try {
        return await apiClient.getRunStatus(runId);
    } catch {
        return null;
    }
}

async function safeApiHealth(): Promise<boolean> {
    try {
        return await apiClient.checkApiHealth();
    } catch {
        return false;
    }
}

async function renderRunDetails(panel: maragtesPanel, runId: string, fallback?: RunRecord | null): Promise<void> {
    try {
        const details = await apiClient.getResults(runId);
        panel.setRunDetails(runId, details);
    } catch {
        if (fallback) {
            panel.setRunDetails(runId, fallback);
        } else {
            panel.setRunDetails(runId, {
                run_id: runId,
                status: 'error',
                error: 'Failed to load run details'
            });
        }
    }
}

async function watchRun(context: vscode.ExtensionContext, runId: string, panel: maragtesPanel): Promise<void> {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = undefined;
    }

    const poll = async () => {
        try {
            const status = await apiClient.getRunStatus(runId);
            panel.setRunProgress(status);
            statusBar.showState('running', buildRunStatusLabel(status));

            if (status.status !== 'running') {
                if (pollTimer) {
                    clearInterval(pollTimer);
                    pollTimer = undefined;
                }

                if (status.status === 'error') {
                    statusBar.showState('error', status.error || `Run ${shortRunId(runId)} failed`);
                } else {
                    statusBar.showState('done', `Run ${shortRunId(runId)} completed`);
                }

                const details = await apiClient.getResults(runId).catch(() => null);
                if (details) {
                    panel.setRunDetails(runId, details);
                } else {
                    panel.setRunDetails(runId, status);
                }

                void historyProvider.refresh();
                void refreshDashboardSnapshot(context, runId);
            }
        } catch (error) {
            if (pollTimer) {
                clearInterval(pollTimer);
                pollTimer = undefined;
            }

            const message = formatError(error, DEFAULT_API_URL, 'Error réseau pendant le suivi du run');
            statusBar.showState('error', message);
            panel.setError(message);
            vscode.window.showWarningMessage(message);
        }
    };

    await poll();
    pollTimer = setInterval(() => {
        void poll();
    }, HISTORY_REFRESH_DELAY_MS);
}

async function findContractByName(contractName: string): Promise<vscode.Uri | undefined> {
    const files = await vscode.workspace.findFiles(`**/${contractName}.sol`, '**/{node_modules,.git,artifacts,cache}/**', 20);
    return files[0];
}

function shortRunId(runId: string): string {
    return runId.length > 8 ? `${runId.slice(0, 8)}...` : runId;
}

function buildRunStatusLabel(run: RunRecord): string {
    const statusPart = run.status === 'running'
        ? 'running'
        : run.status === 'done'
            ? 'completed'
            : 'failed';

    const currentNode = run.current_node ? ` · ${run.current_node}` : '';
    return `Run ${shortRunId(run.run_id)} ${statusPart}${currentNode}`;
}

function formatError(error: unknown, apiUrl: string, fallback: string): string {
    if (error instanceof Error) {
        if (error.message.includes('API unreachable')) {
            return `API unreachable at ${apiUrl}.`;
        }
        return `${fallback}: ${error.message}`;
    }

    return fallback;
}

export function deactivate() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = undefined;
    }

    statusBar.dispose();
    historyProvider.dispose();
}


