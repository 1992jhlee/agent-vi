import Link from "next/link";
import { notFound } from "next/navigation";
import { getReport, getCompany } from "@/lib/api";
import { ReportDetail, VERDICT_LABELS, VERDICT_COLORS } from "@/lib/types";
import AddToWatchlistButton from "@/components/insights/AddToWatchlistButton";

interface ReportPageProps {
  params: Promise<{ slug: string }>;
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
    <span
      className={`inline-block px-3 py-1.5 text-sm font-medium rounded ${colorClass}`}
    >
      {label}
    </span>
  );
}

function ScoreGauge({
  score,
  label,
  color,
}: {
  score: number;
  label: string;
  color: string;
}) {
  return (
    <div className="flex flex-col items-center">
      <div
        className={`w-20 h-20 rounded-full border-4 flex items-center justify-center ${color}`}
      >
        <span className="text-2xl font-bold">{score}</span>
      </div>
      <p className="mt-2 text-sm text-gray-600">{label}</p>
    </div>
  );
}

function Section({
  title,
  content,
}: {
  title: string;
  content: string | null;
}) {
  if (!content) return null;

  return (
    <section className="mb-8">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">{title}</h2>
      <div className="prose prose-sm max-w-none text-gray-600 whitespace-pre-line">
        {content}
      </div>
    </section>
  );
}

function EvaluationSection({
  title,
  evaluation,
  scoreColor,
}: {
  title: string;
  evaluation: { score: number; analysis: string; signals?: string[] } | null;
  scoreColor: string;
}) {
  if (!evaluation) return null;

  return (
    <section className="mb-8 p-6 bg-gray-50 rounded-lg">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-800">{title}</h2>
        <span className={`text-3xl font-bold ${scoreColor}`}>
          {evaluation.score}/100
        </span>
      </div>
      <div className="prose prose-sm max-w-none text-gray-600 whitespace-pre-line">
        {evaluation.analysis}
      </div>
      {evaluation.signals && evaluation.signals.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-medium text-gray-700 mb-2">주요 신호:</p>
          <ul className="list-disc list-inside text-sm text-gray-600">
            {evaluation.signals.map((signal, index) => (
              <li key={index}>{signal}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export default async function ReportDetailPage({ params }: ReportPageProps) {
  const { slug } = await params;

  let report: ReportDetail | null = null;
  let companyMarket = "KOSPI"; // fallback
  let error: string | null = null;

  try {
    report = (await getReport(slug)) as ReportDetail;

    // Fetch company to get market info
    if (report) {
      try {
        const company = await getCompany(report.stock_code);
        companyMarket = company.market;
      } catch (e) {
        // Fail silently, use fallback market
        console.error("Failed to fetch company market:", e);
      }
    }
  } catch (e) {
    if (e instanceof Error && e.message.includes("404")) {
      notFound();
    }
    error = e instanceof Error ? e.message : "보고서를 불러올 수 없습니다.";
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-center">
        <p className="text-red-600">{error}</p>
        <Link
          href="/insights"
          className="text-blue-600 hover:text-blue-800 text-sm mt-4 inline-block"
        >
          &larr; 보고서 목록으로
        </Link>
      </div>
    );
  }

  if (!report) {
    notFound();
  }

  const deepValueScore =
    typeof report.deep_value_evaluation === "object" &&
    report.deep_value_evaluation !== null
      ? (report.deep_value_evaluation as { score: number; analysis: string })
          .score
      : 0;

  const qualityScore =
    typeof report.quality_evaluation === "object" &&
    report.quality_evaluation !== null
      ? (report.quality_evaluation as { score: number; analysis: string }).score
      : 0;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back link */}
      <Link
        href="/insights"
        className="text-blue-600 hover:text-blue-800 text-sm mb-6 inline-block"
      >
        &larr; 보고서 목록
      </Link>

      {/* Header */}
      <header className="mb-8 pb-6 border-b">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h1 className="text-3xl font-bold mb-2">{report.company_name}</h1>
            <p className="text-gray-500">
              {report.stock_code} ·{" "}
              {new Date(report.report_date).toLocaleDateString("ko-KR")}
            </p>
          </div>
          <VerdictBadge verdict={report.overall_verdict} />
        </div>

        {/* Score Summary */}
        <div className="flex items-center justify-center gap-12 mt-8 py-6 bg-gray-50 rounded-lg">
          <ScoreGauge
            score={deepValueScore}
            label="Deep Value"
            color="border-blue-500 text-blue-600"
          />
          <div className="text-center">
            <div
              className={`text-5xl font-bold ${getScoreColor(
                report.overall_score
              )}`}
            >
              {report.overall_score?.toFixed(0) || "-"}
            </div>
            <p className="text-sm text-gray-500 mt-2">종합 점수</p>
          </div>
          <ScoreGauge
            score={qualityScore}
            label="Quality"
            color="border-green-500 text-green-600"
          />
        </div>
      </header>

      {/* Action Bar */}
      <div className="mb-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-gray-700 mb-4">
          이 종목에 관심이 있으신가요? 관심 종목에 추가하여 재무제표를
          지속적으로 추적할 수 있습니다.
        </p>
        <div className="flex flex-wrap gap-4">
          <AddToWatchlistButton
            stockCode={report.stock_code}
            companyName={report.company_name}
            market={companyMarket}
          />
          <Link
            href={`/research/${report.stock_code}`}
            className="flex items-center justify-center px-6 py-3 bg-white border-2 border-blue-600 text-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors"
          >
            재무제표 보기 →
          </Link>
        </div>
      </div>

      {/* Executive Summary */}
      <Section title="요약" content={report.executive_summary} />

      {/* Company Overview */}
      <Section title="기업 개요" content={report.company_overview} />

      {/* Financial Analysis */}
      <Section title="재무 분석" content={report.financial_analysis} />

      {/* Deep Value Evaluation */}
      <EvaluationSection
        title="Deep Value 평가"
        evaluation={
          report.deep_value_evaluation as {
            score: number;
            analysis: string;
            signals?: string[];
          } | null
        }
        scoreColor="text-blue-600"
      />

      {/* Quality Evaluation */}
      <EvaluationSection
        title="Quality 평가"
        evaluation={
          report.quality_evaluation as {
            score: number;
            analysis: string;
            signals?: string[];
          } | null
        }
        scoreColor="text-green-600"
      />

      {/* News Sentiment */}
      <Section title="뉴스 센티먼트" content={report.news_sentiment_summary} />

      {/* Earnings Outlook */}
      <Section title="실적 전망" content={report.earnings_outlook} />

      {/* Footer */}
      <footer className="mt-12 pt-6 border-t text-sm text-gray-500">
        <p>
          보고서 생성일:{" "}
          {new Date(report.created_at).toLocaleDateString("ko-KR")}
        </p>
        <p className="mt-2 text-xs">
          본 보고서는 AI가 자동 생성한 것으로, 투자 권유가 아닙니다. 투자 결정은
          본인의 판단과 책임 하에 이루어져야 합니다.
        </p>
      </footer>
    </div>
  );
}
