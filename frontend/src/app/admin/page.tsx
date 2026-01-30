"use client";

import Link from "next/link";
import { useState, useEffect } from "react";

interface AnalysisRun {
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
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-700",
    running: "bg-blue-100 text-blue-700",
    completed: "bg-green-100 text-green-700",
    failed: "bg-red-100 text-red-700",
  };

  return (
    <span
      className={`px-2 py-1 text-xs font-medium rounded ${
        colors[status] || "bg-gray-100 text-gray-700"
      }`}
    >
      {status}
    </span>
  );
}

export default function AdminPage() {
  const [stockCode, setStockCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [pollingIds, setPollingIds] = useState<number[]>([]);

  // 분석 실행 목록 조회
  const fetchRuns = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/analysis/runs?limit=10`);
      if (res.ok) {
        const data = await res.json();
        // Get detailed status for each run
        const detailedRuns = await Promise.all(
          data.map(async (run: { id: number }) => {
            const statusRes = await fetch(
              `${API_BASE_URL}/api/v1/analysis/status/${run.id}`
            );
            if (statusRes.ok) {
              return statusRes.json();
            }
            return run;
          })
        );
        setRuns(detailedRuns);

        // Update polling IDs for running tasks
        const runningIds = detailedRuns
          .filter(
            (r: AnalysisRun) =>
              r.status === "pending" || r.status === "running"
          )
          .map((r: AnalysisRun) => r.id);
        setPollingIds(runningIds);
      }
    } catch (e) {
      console.error("Failed to fetch runs:", e);
    }
  };

  // 분석 실행 시작
  const triggerAnalysis = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stockCode.trim()) return;

    setLoading(true);
    setMessage(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/analysis/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stock_code: stockCode.trim() }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessage({
          type: "success",
          text: `분석이 시작되었습니다. (Run ID: ${data.id})`,
        });
        setStockCode("");
        fetchRuns();
      } else {
        const error = await res.json();
        setMessage({
          type: "error",
          text: error.detail || "분석 시작에 실패했습니다.",
        });
      }
    } catch (e) {
      setMessage({
        type: "error",
        text: e instanceof Error ? e.message : "네트워크 오류가 발생했습니다.",
      });
    } finally {
      setLoading(false);
    }
  };

  // Initial fetch and polling
  useEffect(() => {
    fetchRuns();
  }, []);

  // Polling for running tasks
  useEffect(() => {
    if (pollingIds.length === 0) return;

    const interval = setInterval(() => {
      fetchRuns();
    }, 3000);

    return () => clearInterval(interval);
  }, [pollingIds]);

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">관리자 대시보드</h1>

      {/* Quick Links */}
      <div className="grid gap-4 md:grid-cols-2 mb-8">
        <Link
          href="/admin/knowledge"
          className="rounded-lg border bg-white p-6 shadow-sm hover:shadow-md transition-shadow"
        >
          <h2 className="mb-2 text-xl font-semibold">투자 철학 관리</h2>
          <p className="text-gray-600">
            Deep Value / Quality 투자 철학 마크다운 파일 편집
          </p>
        </Link>
        <Link
          href="/companies"
          className="rounded-lg border bg-white p-6 shadow-sm hover:shadow-md transition-shadow"
        >
          <h2 className="mb-2 text-xl font-semibold">기업 관리</h2>
          <p className="text-gray-600">분석 대상 기업 목록 관리</p>
        </Link>
      </div>

      {/* Analysis Trigger */}
      <div className="rounded-lg border bg-white p-6 shadow-sm mb-8">
        <h2 className="mb-4 text-xl font-semibold">분석 실행</h2>
        <form onSubmit={triggerAnalysis} className="flex gap-4 mb-4">
          <input
            type="text"
            value={stockCode}
            onChange={(e) => setStockCode(e.target.value)}
            placeholder="종목코드 (예: 005930)"
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={loading || !stockCode.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? "실행 중..." : "분석 시작"}
          </button>
        </form>
        {message && (
          <p
            className={`text-sm ${
              message.type === "success" ? "text-green-600" : "text-red-600"
            }`}
          >
            {message.text}
          </p>
        )}
        <p className="text-sm text-gray-500 mt-2">
          분석에는 수 분이 소요될 수 있습니다. 진행 상태를 아래에서 확인하세요.
        </p>
      </div>

      {/* Analysis Runs */}
      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">최근 분석 실행</h2>
          <button
            onClick={fetchRuns}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            새로고침
          </button>
        </div>

        {runs.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            아직 실행된 분석이 없습니다.
          </p>
        ) : (
          <div className="space-y-3">
            {runs.map((run) => (
              <div
                key={run.id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
              >
                <div className="flex items-center gap-4">
                  <StatusBadge status={run.status} />
                  <div>
                    <p className="font-medium">
                      {run.company_name || "알 수 없음"} ({run.stock_code})
                    </p>
                    <p className="text-sm text-gray-500">
                      {run.started_at
                        ? new Date(run.started_at).toLocaleString("ko-KR")
                        : "-"}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  {run.status === "completed" && run.report && (
                    <Link
                      href={`/reports/${run.report.slug}`}
                      className="text-blue-600 hover:text-blue-800 text-sm"
                    >
                      보고서 보기 &rarr;
                    </Link>
                  )}
                  {run.status === "failed" && run.error_message && (
                    <p
                      className="text-red-600 text-sm max-w-xs truncate"
                      title={run.error_message}
                    >
                      {run.error_message}
                    </p>
                  )}
                  {(run.status === "pending" || run.status === "running") && (
                    <span className="text-sm text-gray-500 animate-pulse">
                      진행 중...
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
