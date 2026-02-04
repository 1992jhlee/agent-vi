import Link from "next/link";
import { getLatestReports } from "@/lib/api";
import { ReportSummary, VERDICT_LABELS, VERDICT_COLORS } from "@/lib/types";

export const dynamic = "force-dynamic";

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

function ReportCard({ report }: { report: ReportSummary }) {
  return (
    <Link
      href={`/reports/${report.slug}`}
      className="block p-4 bg-white border border-gray-200 rounded-lg hover:border-blue-400 hover:shadow-md transition-all"
    >
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="font-semibold text-lg">{report.company_name}</h3>
          <p className="text-sm text-gray-500">{report.stock_code}</p>
        </div>
        <VerdictBadge verdict={report.overall_verdict} />
      </div>
      <div className="flex justify-between items-end mt-4">
        <div>
          <p className="text-xs text-gray-400">종합 점수</p>
          <p className={`text-2xl font-bold ${getScoreColor(report.overall_score)}`}>
            {report.overall_score !== null ? report.overall_score.toFixed(0) : "-"}
          </p>
        </div>
        <p className="text-xs text-gray-400">
          {new Date(report.report_date).toLocaleDateString("ko-KR")}
        </p>
      </div>
    </Link>
  );
}

export default async function HomePage() {
  let reports: ReportSummary[] = [];
  let error: string | null = null;

  try {
    reports = await getLatestReports(8);
  } catch (e) {
    error = e instanceof Error ? e.message : "데이터를 불러올 수 없습니다.";
  }

  // 통계 계산
  const stats = {
    total: reports.length,
    buyCount: reports.filter(
      (r) => r.overall_verdict === "buy" || r.overall_verdict === "strong_buy"
    ).length,
    avgScore:
      reports.length > 0
        ? reports.reduce((sum, r) => sum + (r.overall_score || 0), 0) /
          reports.length
        : 0,
  };

  return (
    <div>
      {/* Hero Section */}
      <section className="mb-12 text-center">
        <h1 className="mb-4 text-4xl font-bold">Agent-VI</h1>
        <p className="text-lg text-gray-600">
          가치투자 철학 기반 AI 기업 분석 보고서
        </p>
        <p className="mt-2 text-sm text-gray-500">
          Deep Value &amp; Quality 관점에서 한국 주식을 분석합니다
        </p>
      </section>

      {/* Stats Section */}
      {reports.length > 0 && (
        <section className="grid grid-cols-3 gap-4 mb-12">
          <div className="p-6 bg-white border border-gray-200 rounded-lg text-center">
            <p className="text-3xl font-bold text-blue-600">{stats.total}</p>
            <p className="text-sm text-gray-500">발행 보고서</p>
          </div>
          <div className="p-6 bg-white border border-gray-200 rounded-lg text-center">
            <p className="text-3xl font-bold text-green-600">{stats.buyCount}</p>
            <p className="text-sm text-gray-500">매수 의견</p>
          </div>
          <div className="p-6 bg-white border border-gray-200 rounded-lg text-center">
            <p className={`text-3xl font-bold ${getScoreColor(stats.avgScore)}`}>
              {stats.avgScore.toFixed(1)}
            </p>
            <p className="text-sm text-gray-500">평균 점수</p>
          </div>
        </section>
      )}

      {/* Recent Reports Section */}
      <section>
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-semibold">최근 보고서</h2>
          {reports.length > 0 && (
            <Link
              href="/reports"
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              전체 보기 &rarr;
            </Link>
          )}
        </div>

        {error ? (
          <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-center">
            <p className="text-red-600">{error}</p>
            <p className="text-sm text-gray-500 mt-2">
              백엔드 서버가 실행 중인지 확인해주세요.
            </p>
          </div>
        ) : reports.length === 0 ? (
          <div className="p-8 bg-gray-50 border border-gray-200 rounded-lg text-center">
            <p className="text-gray-500 mb-4">
              아직 발행된 보고서가 없습니다.
            </p>
            <Link
              href="/admin"
              className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              관리자 페이지에서 분석 실행
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {reports.map((report) => (
              <ReportCard key={report.id} report={report} />
            ))}
          </div>
        )}
      </section>

      {/* About Section */}
      <section className="mt-16 p-8 bg-gray-50 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">투자 철학</h2>
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <h3 className="font-medium text-blue-600 mb-2">Deep Value</h3>
            <p className="text-sm text-gray-600">
              그레이엄, 버핏의 가치투자 원칙에 따라 내재가치 대비 저평가된 기업을 발굴합니다.
              NCAV, PBR, 그레이엄 넘버 등 정량적 지표를 분석합니다.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-green-600 mb-2">Quality</h3>
            <p className="text-sm text-gray-600">
              높은 ROE, 안정적인 현금흐름, 지속 가능한 경쟁우위를 가진 우량 기업을 평가합니다.
              정성적 분석과 뉴스 센티먼트도 함께 고려합니다.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
