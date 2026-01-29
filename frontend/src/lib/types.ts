// Company types
export interface Company {
  id: number;
  stock_code: string;
  company_name: string;
  company_name_en: string | null;
  corp_code: string | null;
  market: string;
  sector: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CompanyListResponse {
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  items: Company[];
}

// Report types
export interface ReportSummary {
  id: number;
  slug: string;
  title: string;
  report_date: string;
  company_name: string;
  stock_code: string;
  overall_score: number | null;
  overall_verdict: string | null;
  is_published: boolean;
  published_at: string | null;
  created_at: string;
}

export interface ReportDetail extends ReportSummary {
  executive_summary: string | null;
  company_overview: string | null;
  financial_analysis: string | null;
  news_sentiment_summary: string | null;
  earnings_outlook: string | null;
  deep_value_evaluation: ValuationEvaluation | null;
  quality_evaluation: ValuationEvaluation | null;
  updated_at: string;
}

export interface ValuationEvaluation {
  score: number;
  analysis: string;
  signals: string[];
}

export interface ReportListResponse {
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
  items: ReportSummary[];
}

// Analysis types
export interface AnalysisRun {
  id: number;
  company_id: number;
  status: string;
  trigger_type: string;
  llm_model: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

// Verdict display helper
export const VERDICT_LABELS: Record<string, string> = {
  strong_buy: "강력매수",
  buy: "매수",
  hold: "보유",
  sell: "매도",
  strong_sell: "강력매도",
};

export const VERDICT_COLORS: Record<string, string> = {
  strong_buy: "text-red-600 bg-red-50",
  buy: "text-orange-600 bg-orange-50",
  hold: "text-gray-600 bg-gray-50",
  sell: "text-blue-600 bg-blue-50",
  strong_sell: "text-blue-800 bg-blue-100",
};
