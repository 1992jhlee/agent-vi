const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}/api/v1${endpoint}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
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
  return fetchAPI(`/companies${query ? `?${query}` : ""}`);
}

export async function getCompany(stockCode: string) {
  return fetchAPI(`/companies/${stockCode}`);
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
  return fetchAPI(`/reports${query ? `?${query}` : ""}`);
}

export async function getLatestReports(limit: number = 10) {
  return fetchAPI(`/reports/latest?limit=${limit}`);
}

export async function getReport(slug: string) {
  return fetchAPI(`/reports/${slug}`);
}

export async function getCompanyReports(stockCode: string) {
  return fetchAPI(`/reports/company/${stockCode}`);
}

// Analysis
export async function triggerAnalysis(data: {
  stock_code: string;
  llm_model?: string;
}) {
  return fetchAPI("/analysis/run", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getAnalysisRuns(params?: {
  status?: string;
  limit?: number;
}) {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));

  const query = searchParams.toString();
  return fetchAPI(`/analysis/runs${query ? `?${query}` : ""}`);
}

// Financials
export async function getFinancials(stockCode: string, years?: number) {
  const query = years ? `?years=${years}` : "";
  return fetchAPI(`/financials/${stockCode}${query}`);
}

export async function getValuationMetrics(stockCode: string) {
  return fetchAPI(`/financials/${stockCode}/metrics`);
}

export async function refreshFinancials(stockCode: string, force: boolean = false) {
  const query = force ? "?force=true" : "";
  return fetchAPI(`/financials/${stockCode}/refresh${query}`, {
    method: "POST",
  });
}

// Stocks
export async function searchStocks(query: string) {
  return fetchAPI(`/stocks/search?q=${encodeURIComponent(query)}`);
}
