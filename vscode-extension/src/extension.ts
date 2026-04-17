import * as vscode from 'vscode';
import * as path from 'path';
import { SolidTestPanel } from './webviewPanel';
import { HistoryProvider, RunItem } from './historyProvider';
import { ApiClient, ContractSubmission, RunRecord } from './apiClient';
import { StatusBar } from './statusBar';

const DEFAULT_API_URL = 'http://localhost:8000';
const DEFAULT_FRONTEND_URL = 'http://localhost:3000';
const LAST_ENVIRONMENT_KEY = 'solidtest.lastEnvironment';
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

export async function activate(context: vscode.ExtensionContext) {
    console.log('SolidTest extension is now active!');

    const config = vscode.workspace.getConfiguration('solidtest');
    apiClient = new ApiClient(config.get('apiUrl', DEFAULT_API_URL));
    statusBar = new StatusBar();
    historyProvider = new HistoryProvider(apiClient);

    context.subscriptions.push(historyProvider);
    vscode.window.registerTreeDataProvider('solidtestExplorer', historyProvider);

    const submitCommand = vscode.commands.registerCommand('solidtest.submitContract', async (payload?: vscode.Uri | { uri?: string; contractPath?: string; environment?: string }) => {
        await handleSubmitContract(context, payload);
    });

    const submitCurrentContractCommand = vscode.commands.registerCommand('solidtest.submitCurrentContract', async () => {
        await handleSubmitContract(context);
    });

    const viewHistoryCommand = vscode.commands.registerCommand('solidtest.viewHistory', async () => {
        await handleViewHistory(context);
    });

    const openDashboardCommand = vscode.commands.registerCommand('solidtest.openDashboard', async () => {
        await handleOpenDashboard();
    });

    const openLatestResultCommand = vscode.commands.registerCommand('solidtest.openLatestResult', async () => {
        await handleOpenLatestResult(context);
    });

    const settingsCommand = vscode.commands.registerCommand('solidtest.settings', async () => {
        await vscode.commands.executeCommand('workbench.action.openSettings', 'solidtest');
    });

    const viewResultsCommand = vscode.commands.registerCommand('solidtest.viewResults', async (item: RunItem) => {
        if (item?.runId) {
            await handleViewResults(context, item.runId);
        }
    });

    const refreshCommand = vscode.commands.registerCommand('solidtest.refresh', async () => {
        await historyProvider.refresh();
    });

    const runNowCommand = vscode.commands.registerCommand('solidtest.runTestNow', async (item?: RunItem) => {
        await handleRunNow(context, item);
    });

    context.subscriptions.push(
        submitCommand,
        submitCurrentContractCommand,
        viewHistoryCommand,
        openDashboardCommand,
        openLatestResultCommand,
        settingsCommand,
        viewResultsCommand,
        refreshCommand,
        runNowCommand
    );

    statusBar.showState('idle', 'SolidTest prêt');
    void refreshDashboardSnapshot(context);
    vscode.window.showInformationMessage('SolidTest prêt. Ouvrez un fichier .sol pour lancer un run.');
}

async function handleSubmitContract(
    context: vscode.ExtensionContext,
    payload?: vscode.Uri | { uri?: string; contractPath?: string; environment?: string }
) {
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
            return;
        }

        const explicitEnvironment = payload && !(payload instanceof vscode.Uri)
            ? payload.environment
            : undefined;
        const environment = explicitEnvironment || await resolveEnvironment(context);
        if (!environment) {
            statusBar.showState('idle', 'Soumission annulée');
            return;
        }

        statusBar.showState('submitting', `Soumission de ${contract.contractName}...`);

        const submission: ContractSubmission = {
            contractCode: contract.contractCode,
            contractName: contract.contractName,
            environment
        };

        const response = await apiClient.submitContract(submission);
        if (response.status === 'error' || !response.run_id) {
            const message = response.message || 'Soumission impossible';
            vscode.window.showErrorMessage(message);
            statusBar.showState('error', message);
            await refreshDashboardSnapshot(context);
            return;
        }

        await context.workspaceState.update(LAST_ENVIRONMENT_KEY, environment);
        statusBar.showState('running', `Run ${shortRunId(response.run_id)} en cours`);

        const panel = SolidTestPanel.createOrShow(context.extensionUri, apiClient, response.run_id);
        panel.show();
        panel.focusSection('status');
        panel.setSelectedEnvironment(environment);
        panel.setActiveContract({
            name: contract.contractName,
            path: contract.contractPath,
            size: '-',
            modified: '-'
        });
        panel.setRunFocus(response.run_id);

        vscode.window.showInformationMessage(`Run lancé: ${response.run_id}`);
        void historyProvider.refresh();
        void refreshDashboardSnapshot(context, response.run_id);
        void watchRun(context, response.run_id, panel);
    } catch (error) {
        const message = formatError(error, DEFAULT_API_URL, 'Impossible de soumettre le contrat');
        vscode.window.showErrorMessage(message);
        statusBar.showState('error', message);
        await refreshDashboardSnapshot(context);
    }
}

async function handleViewHistory(context: vscode.ExtensionContext) {
    const panel = SolidTestPanel.createOrShow(context.extensionUri, apiClient);
    panel.show();
    panel.focusSection('history');
    await refreshDashboardSnapshot(context);
}

async function handleOpenDashboard() {
    const config = vscode.workspace.getConfiguration('solidtest');
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
        vscode.window.showInformationMessage(`Dashboard ouvert sur ${fallbackUrl}.`);
        return;
    }

    vscode.window.showWarningMessage(`Dashboard indisponible, lance frontend/ sur ${frontendUrl} ou ${fallbackUrl}.`);
}

async function handleOpenLatestResult(context: vscode.ExtensionContext) {
    const latestRun = await safeLatestRun();
    if (!latestRun) {
        vscode.window.showInformationMessage('Aucun run disponible pour le moment.');
        return;
    }

    const panel = SolidTestPanel.createOrShow(context.extensionUri, apiClient, latestRun.run_id);
    panel.show();
    panel.focusSection('results');
    panel.setRunFocus(latestRun.run_id);
    await renderRunDetails(panel, latestRun.run_id, latestRun);
}

async function handleViewResults(context: vscode.ExtensionContext, runId: string) {
    const panel = SolidTestPanel.createOrShow(context.extensionUri, apiClient, runId);
    panel.show();
    panel.focusSection('results');
    panel.setRunFocus(runId);

    try {
        const details = await apiClient.getResults(runId);
        panel.setRunDetails(runId, details);
    } catch (error) {
        const run = await safeRunStatus(runId);
        const fallback = run ?? { run_id: runId, status: 'error', error: formatError(error, DEFAULT_API_URL, 'Impossible de charger les résultats') };
        panel.setRunDetails(runId, fallback);
        vscode.window.showWarningMessage(fallback.error || 'Impossible de charger les résultats.');
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
        vscode.window.showInformationMessage('Aucun contrat Solidity sélectionné. Ouvrez un fichier .sol puis relancez SolidTest.');
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
            title: 'Choisir un contrat Solidity',
            placeHolder: 'Sélectionnez le fichier .sol à soumettre'
        }
    );

    return selection?.uri;
}

async function resolveEnvironment(context: vscode.ExtensionContext): Promise<string | undefined> {
    const config = vscode.workspace.getConfiguration('solidtest');
    const lastEnvironment = context.workspaceState.get<string>(LAST_ENVIRONMENT_KEY);
    const defaultEnvironment = config.get('defaultEnvironment', 'simulation');

    if (lastEnvironment) {
        return lastEnvironment;
    }

    const picked = await vscode.window.showQuickPick(
        ['simulation', 'testnet', 'mainnet', 'custom...'],
        {
            title: 'Sélectionnez l’environnement d’exécution',
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
            title: 'Environnement personnalisé',
            prompt: 'Entrez le nom de l’environnement',
            value: defaultEnvironment,
            ignoreFocusOut: true
        });
        return custom?.trim() || undefined;
    }

    return picked;
}

async function buildDashboardSnapshot(context: vscode.ExtensionContext, selectedRunId?: string): Promise<DashboardSnapshot> {
    const config = vscode.workspace.getConfiguration('solidtest');
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
    const panel = SolidTestPanel.currentPanel;
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

async function renderRunDetails(panel: SolidTestPanel, runId: string, fallback?: RunRecord | null): Promise<void> {
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
                error: 'Impossible de charger les détails du run'
            });
        }
    }
}

async function watchRun(context: vscode.ExtensionContext, runId: string, panel: SolidTestPanel): Promise<void> {
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
                    statusBar.showState('error', status.error || `Run ${shortRunId(runId)} en erreur`);
                } else {
                    statusBar.showState('done', `Run ${shortRunId(runId)} terminé`);
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

            const message = formatError(error, DEFAULT_API_URL, 'Erreur réseau pendant le suivi du run');
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
        ? 'en cours'
        : run.status === 'done'
            ? 'terminé'
            : 'en erreur';

    const currentNode = run.current_node ? ` · ${run.current_node}` : '';
    return `Run ${shortRunId(run.run_id)} ${statusPart}${currentNode}`;
}

function formatError(error: unknown, apiUrl: string, fallback: string): string {
    if (error instanceof Error) {
        if (error.message.includes('API inaccessible')) {
            return `API inaccessible sur ${apiUrl}.`;
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
