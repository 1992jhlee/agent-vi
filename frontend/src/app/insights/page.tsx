import Link from "next/link";
import type { Metadata } from "next";
import { getReports } from "@/lib/api";
import {
  ReportListResponse,
  ReportSummary,
  VERDICT_LABELS,
  VERDICT_COLORS,
} from "@/lib/types";

export const metadata: Metadata = {
  title: "AI 투자 추천 | Agent-VI",
  description: "Deep Value & Quality 관점의 AI 기업 분석 보고서",
};

interface SearchParams {
  page?: string;
  verdict?: string;
  market?: string;
}

function getScoreColor(score: number | null): string {
  if (score === null) return "text-gray-400";
  if (score >= 80) return "text-red-600";
  if (score >= 65) return "text-orange-500";
  if (score >= 50) return "text-gray-600";
  if (score >= 35) return "text-blue-500";
  return "text-blue-700";
}

function VerdictBadge({ verdict }: { verdict: string | null }) {
  if (!verdict) return null;
  const label = VERDICT_LABELS[verdict] || verdict;
  const colorClass = VERDICT_COLORS[verdict] || "text-gray-600 bg-gray-50";

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded ${colorClass}`}>
      {label}
    </span>
  );
}

function ReportRow({ report }: { report: ReportSummary }) {
  return (
    <Link
      href={`/insights/${report.slug}`}
      className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-400 hover:shadow-sm transition-all"
    >
      <div className="flex items-center gap-4">
        <div
          className={`w-12 h-12 flex items-center justify-center rounded-lg ${getScoreColor(
            report.overall_score
          )} bg-gray-50 font-bold text-lg`}
        >
          {report.overall_score !== null
            ? report.overall_score.toFixed(0)
            : "-"}
        </div>
        <div>
          <h3 className="font-semibold">{report.company_name}</h3>
          <p className="text-sm text-gray-500">
            {report.stock_code} ·{" "}
            {new Date(report.report_date).toLocaleDateString("ko-KR")}
          </p>
        </div>
      </div>
      <VerdictBadge verdict={report.overall_verdict} />
    </Link>
  );
}

function FilterButton({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={`px-3 py-1 text-sm rounded-full transition-colors ${
        active
          ? "bg-blue-600 text-white"
          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
      }`}
    >
      {children}
    </Link>
  );
}

function Pagination({
  currentPage,
  totalPages,
  baseUrl,
}: {
  currentPage: number;
  totalPages: number;
  baseUrl: string;
}) {
  if (totalPages <= 1) return null;

  const pages = [];
  const maxVisible = 5;
  let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
  const end = Math.min(totalPages, start + maxVisible - 1);

  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1);
  }

  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  return (
    <div className="flex items-center justify-center gap-2 mt-8">
      {currentPage > 1 && (
        <Link
          href={`${baseUrl}&page=${currentPage - 1}`}
          className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
        >
          이전
        </Link>
      )}
      {pages.map((page) => (
        <Link
          key={page}
          href={`${baseUrl}&page=${page}`}
          className={`px-3 py-1 text-sm rounded ${
            page === currentPage
              ? "bg-blue-600 text-white"
              : "bg-gray-100 hover:bg-gray-200"
          }`}
        >
          {page}
        </Link>
      ))}
      {currentPage < totalPages && (
        <Link
          href={`${baseUrl}&page=${currentPage + 1}`}
          className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200"
        >
          다음
        </Link>
      )}
    </div>
  );
}

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const page = parseInt(params.page || "1", 10);
  const verdict = params.verdict || "";
  const market = params.market || "";

  let data: ReportListResponse | null = null;
  let error: string | null = null;

  try {
    data = (await getReports({
      page,
      per_page: 20,
      verdict: verdict || undefined,
      market: market || undefined,
    })) as ReportListResponse;
  } catch (e) {
    error = e instanceof Error ? e.message : "데이터를 불러올 수 없습니다.";
  }

  const baseUrl = `/insights?verdict=${verdict}&market=${market}`;

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">AI 투자 추천</h1>
      <p className="mb-6 text-gray-600">
        AI가 Deep Value & Quality 관점에서 분석한 종목 추천 보고서입니다.
        마음에 드는 종목은 <strong>관심 종목</strong>에 추가하여 리서치를
        이어가세요.
      </p>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap gap-2">
        <span className="text-sm text-gray-500 mr-2">투자 의견:</span>
        <FilterButton href="/insights" active={!verdict}>
          전체
        </FilterButton>
        <FilterButton
          href={`/insights?verdict=strong_buy&market=${market}`}
          active={verdict === "strong_buy"}
        >
          강력매수
        </FilterButton>
        <FilterButton
          href={`/insights?verdict=buy&market=${market}`}
          active={verdict === "buy"}
        >
          매수
        </FilterButton>
        <FilterButton
          href={`/insights?verdict=hold&market=${market}`}
          active={verdict === "hold"}
        >
          보유
        </FilterButton>
        <FilterButton
          href={`/insights?verdict=sell&market=${market}`}
          active={verdict === "sell"}
        >
          매도
        </FilterButton>
        <FilterButton
          href={`/insights?verdict=strong_sell&market=${market}`}
          active={verdict === "strong_sell"}
        >
          강력매도
        </FilterButton>
      </div>

      {error ? (
        <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-center">
          <p className="text-red-600">{error}</p>
          <p className="text-sm text-gray-500 mt-2">
            백엔드 서버가 실행 중인지 확인해주세요.
          </p>
        </div>
      ) : !data || data.items.length === 0 ? (
        <div className="p-8 bg-gray-50 border border-gray-200 rounded-lg text-center">
          <p className="text-gray-500 mb-4">
            {verdict
              ? `'${VERDICT_LABELS[verdict] || verdict}' 의견의 보고서가 없습니다.`
              : "아직 발행된 보고서가 없습니다."}
          </p>
          {verdict && (
            <Link
              href="/insights"
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              전체 보고서 보기
            </Link>
          )}
        </div>
      ) : (
        <>
          <p className="text-sm text-gray-500 mb-4">
            총 {data.total}개의 보고서
          </p>
          <div className="space-y-3">
            {data.items.map((report) => (
              <ReportRow key={report.id} report={report} />
            ))}
          </div>
          <Pagination
            currentPage={data.page}
            totalPages={data.total_pages}
            baseUrl={baseUrl}
          />
        </>
      )}
    </div>
  );
}
