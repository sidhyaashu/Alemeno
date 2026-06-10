const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_URL = `${API_BASE_URL}/api/v1`;

export interface JobUploadResponse {
  job_id: string;
  status: string;
}

export interface JobSummary {
  total_spend_inr: number;
  total_spend_usd: number;
  top_merchants: Array<{ merchant: string; total: number }>;
  anomaly_count: number;
  category_breakdown: Record<string, number>;
  narrative?: string;
  risk_level?: string;
  llm_failed: boolean;
}

export interface Transaction {
  txn_id: string;
  date: string;
  merchant: string;
  amount: number;
  currency: string;
  status: string;
  category: string;
  account_id: string;
  is_anomaly: boolean;
  anomaly_reason?: string;
  llm_category?: string;
  llm_failed: boolean;
}

export interface JobDetails {
  id: string;
  filename: string;
  status: string;
  row_count_raw?: number;
  row_count_clean?: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
  summary?: JobSummary;
  transactions?: Transaction[];
  anomalies?: Transaction[];
}

export interface SuccessResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export const api = {
  async uploadCSV(file: File, geminiKey?: string): Promise<JobUploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const headers: Record<string, string> = {
      "ngrok-skip-browser-warning": "any",
    };
    if (geminiKey) {
      headers["X-Gemini-API-Key"] = geminiKey;
    }

    const response = await fetch(`${API_URL}/jobs/upload`, {
      method: "POST",
      body: formData,
      headers: headers,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Upload failed with status ${response.status}`);
    }

    const res: SuccessResponse<JobUploadResponse> = await response.json();
    return res.data;
  },

  async getJobStatus(jobId: string): Promise<JobDetails> {
    const response = await fetch(`${API_URL}/jobs/${jobId}/status`, {
      headers: { "ngrok-skip-browser-warning": "any" }
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Failed to fetch status: ${response.status}`);
    }

    const res: SuccessResponse<JobDetails> = await response.json();
    return res.data;
  },

  async getJobResults(jobId: string): Promise<JobDetails> {
    const response = await fetch(`${API_URL}/jobs/${jobId}/results`, {
      headers: { "ngrok-skip-browser-warning": "any" }
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Failed to fetch results: ${response.status}`);
    }

    const res: SuccessResponse<JobDetails> = await response.json();
    return res.data;
  },

  async listJobs(status?: string): Promise<JobDetails[]> {
    const url = status ? `${API_URL}/jobs?status=${status}` : `${API_URL}/jobs`;
    const response = await fetch(url, {
      headers: { "ngrok-skip-browser-warning": "any" }
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Failed to list jobs: ${response.status}`);
    }

    const res: SuccessResponse<JobDetails[]> = await response.json();
    return res.data;
  },
};
