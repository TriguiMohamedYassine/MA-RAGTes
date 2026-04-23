import axios, { AxiosError, AxiosInstance } from 'axios';

export interface ContractSubmission {
    contractCode: string;
    contractName: string;
    environment: string;
    userStory: string;
}

export interface RunResponse {
    run_id: string;
    status: 'running' | 'success' | 'error';
    message?: string;
}

export interface RunSummary {
    total?: number;
    passed?: number;
    failed?: number;
    coverage?: {
        statements?: number;
        branches?: number;
        functions?: number;
    };
    evaluation_decision?: string;
    evaluation_reason?: string;
    iterations?: number;
    failures_count?: number;
    detected_ercs?: string[];
}

export interface RunRecord {
    run_id: string;
    status: 'running' | 'done' | 'error' | string;
    contract_name?: string;
    started_at?: string;
    finished_at?: string;
    current_node?: string;
    iterations?: number;
    summary?: RunSummary | null;
    error?: string | null;
    test_report?: any;
    coverage_report?: any;
    analyzer_report?: any;
    test_code?: string;
    test_design?: any;
    llm_stats?: any;
}

export interface RunStatus extends RunRecord {
    progress?: number;
    message?: string;
}

export interface DashboardReachability {
    url: string;
    reachable: boolean;
}

export class ApiClient {
    private client: AxiosInstance;
    private baseUrl: string;

    constructor(baseUrl: string) {
        this.baseUrl = baseUrl;
        this.client = axios.create({
            baseURL: baseUrl,
            timeout: 30000,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    async submitContract(submission: ContractSubmission): Promise<RunResponse> {
        try {
            const response = await this.client.post('/api/run', {
                contract_code: submission.contractCode,
                contract_name: submission.contractName,
                environment: submission.environment,
                user_story: submission.userStory
            });
            return {
                run_id: response.data.run_id,
                status: 'success',
                message: response.data.message
            };
        } catch (error: any) {
            return {
                run_id: '',
                status: 'error',
                message: this.formatError(error, 'Failed to submit contract')
            };
        }
    }

    async getRunStatus(runId: string): Promise<RunStatus> {
        try {
            const response = await this.client.get(`/api/run/${runId}`);
            return response.data;
        } catch (error: any) {
            throw new Error(this.formatError(error, 'Failed to fetch run status'));
        }
    }

    async getHistory(): Promise<RunRecord[]> {
        try {
            const response = await this.client.get('/api/history');
            return response.data || [];
        } catch (error: any) {
            throw new Error(this.formatError(error, 'Failed to fetch history'));
        }
    }

    async getResults(runId: string): Promise<any> {
        try {
            const response = await this.client.get(`/api/results/${runId}`);
            return response.data;
        } catch (error: any) {
            throw new Error(this.formatError(error, 'Failed to fetch results'));
        }
    }

    async getLatestRun(): Promise<RunRecord | null> {
        const history = await this.getHistory();
        return history.length > 0 ? history[0] : null;
    }

    async deleteHistory(): Promise<boolean> {
        try {
            await this.client.delete('/api/history');
            return true;
        } catch (error: any) {
            throw new Error(this.formatError(error, 'Failed to clear history'));
        }
    }

    async checkApiHealth(): Promise<boolean> {
        try {
            const response = await this.client.get('/api/health');
            return response.status === 200;
        } catch (error) {
            return false;
        }
    }

    async checkFrontendReachable(url: string): Promise<DashboardReachability> {
        try {
            const response = await axios.get(url, { timeout: 2500 });
            return {
                url,
                reachable: response.status >= 200 && response.status < 500
            };
        } catch {
            return {
                url,
                reachable: false
            };
        }
    }

    async saveLlmApiKey(apiKey: string): Promise<void> {
        const normalized = String(apiKey || '').trim();
        if (!normalized) {
            throw new Error('API key is required.');
        }

        try {
            await this.client.post('/api/settings/llm-key', {
                api_key: normalized
            });
        } catch (error: any) {
            throw new Error(this.formatError(error, 'Failed to save API key'));
        }
    }

    private formatError(error: unknown, fallback: string): string {
        if (axios.isAxiosError(error)) {
            const axiosError = error as AxiosError<any>;
            const detail = axiosError.response?.data?.detail;
            const responseMessage = typeof detail === 'string'
                ? detail
                : axiosError.response?.statusText;

            if (axiosError.code === 'ECONNREFUSED' || axiosError.code === 'ERR_NETWORK') {
                return `${fallback} - API unreachable at ${this.baseUrl}`;
            }

            if (responseMessage) {
                return `${fallback}: ${responseMessage}`;
            }

            return `${fallback}: ${axiosError.message}`;
        }

        if (error instanceof Error) {
            return `${fallback}: ${error.message}`;
        }

        return fallback;
    }
}


