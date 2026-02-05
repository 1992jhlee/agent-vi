import {
  Company,
  CompanyListResponse,
  FinancialDataResponse,
  ReportSummary,
  ReportListResponse,
  ReportDetail,
  AnalysisRun,
  StockSearchResult,
} from "@/lib/types";

const API_BASE_URL =
  process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Auth token cache — 서버 측 /api/auth/token에서 받은 JWT를 메모리에 캐시
// ---------------------------------------------------------------------------
let tokenCache: { token: string; expiresAt: number } | null = null;

export async function getAuthToken(): Promise<string> {
  const now = Date.now();
  if (tokenCache && now < tokenCache.expiresAt) {
    return tokenCache.token;
  }

  const res = await fetch("/api/auth/token");
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || "토큰 가져오기 실패");
  }

  const { token } = await res.json();
  tokenCache = {
    token,
    expiresAt: now + 55 * 60 * 1000, // 55분 (백엔드 JWT는 1h)
  };
  return token;
}

export function clearAuthToken(): void {
  tokenCache = null;
}

// ---------------------------------------------------------------------------
// Core fetch helper
// ---------------------------------------------------------------------------
interface FetchOptions extends RequestInit {
  /** true이면 Bearer token을 자동으로 첨부 */
  auth?: boolean;
}

async function fetchAPI<T>(endpoint: string, options?: FetchOptions): Promise<T> {
  const { auth: needsAuth, ...restOptions } = options ?? {};

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(restOptions.headers as Record<string, string>),
  };

  if (needsAuth) {
    const token = await getAuthToken();
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}/api/v1${endpoint}`;
  const res = await fetch(url, {
    ...restOptions,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// Companies
export async function getCompanies(params?: {
  page?: number;
  per_page?: number;
  market?: string;
  is_active?: boolean;
  q?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.market) searchParams.set("market", params.market);
  if (params?.is_active !== undefined)
    searchParams.set("is_active", String(params.is_active));
  if (params?.q) searchParams.set("q", params.q);

  const query = searchParams.toString();
  return fetchAPI<CompanyListResponse>(`/companies${query ? `?${query}` : ""}`);
}

export async function getCompany(stockCode: string) {
  return fetchAPI<Company>(`/companies/${stockCode}`);
}

export async function createCompany(data: {
  stock_code: string;
  company_name: string;
  market: string;
}) {
  return fetchAPI<Company>("/companies", {
    method: "POST",
    body: JSON.stringify(data),
    auth: true,
  });
}

// Reports
export async function getReports(params?: {
  page?: number;
  per_page?: number;
  market?: string;
  verdict?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.per_page) searchParams.set("per_page", String(params.per_page));
  if (params?.market) searchParams.set("market", params.market);
  if (params?.verdict) searchParams.set("verdict", params.verdict);

  const query = searchParams.toString();
  return fetchAPI<ReportListResponse>(`/reports${query ? `?${query}` : ""}`);
}

export async function getLatestReports(limit: number = 10) {
  return fetchAPI<ReportSummary[]>(`/reports/latest?limit=${limit}`);
}

export async function getReport(slug: string) {
  return fetchAPI<ReportDetail>(`/reports/${slug}`);
}

export async function getCompanyReports(stockCode: string) {
  return fetchAPI<ReportSummary[]>(`/reports/company/${stockCode}`);
}

// Analysis
export async function triggerAnalysis(data: {
  stock_code: string;
  llm_model?: string;
}) {
  return fetchAPI("/analysis/run", {
    method: "POST",
    body: JSON.stringify(data),
    auth: true,
  });
}

export async function getAnalysisStatus(runId: number) {
  return fetchAPI<{
    id: number;
    company_name: string | null;
    stock_code: string | null;
    status: string;
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
    report: {
      id: number;
      slug: string;
      overall_score: number;
      overall_verdict: string;
    } | null;
  }>(`/analysis/status/${runId}`);
}

export async function getAnalysisRuns(params?: {
  status?: string;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));

  const query = searchParams.toString();
  return fetchAPI<AnalysisRun[]>(`/analysis/runs${query ? `?${query}` : ""}`);
}

// Financials
export async function getFinancials(stockCode: string, years?: number) {
  const query = years ? `?years=${years}` : "";
  return fetchAPI<FinancialDataResponse>(`/financials/${stockCode}${query}`);
}

export async function getValuationMetrics(stockCode: string) {
  return fetchAPI(`/financials/${stockCode}/metrics`);
}

export async function refreshFinancials(stockCode: string, force: boolean = false) {
  const query = force ? "?force=true" : "";
  return fetchAPI(`/financials/${stockCode}/refresh${query}`, {
    method: "POST",
    auth: true,
  });
}

// Stocks
export async function searchStocks(query: string) {
  return fetchAPI<StockSearchResult[]>(`/stocks/search?q=${encodeURIComponent(query)}`);
}
