import Link from "next/link";
import ServiceCard from "@/components/common/ServiceCard";
import { getLatestReports } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let reportCount = 0;

  try {
    const reports = await getLatestReports(100); // Get more to count
    reportCount = reports.length;
  } catch (e) {
    // Fail silently for homepage stats
    console.error("Failed to fetch reports for stats:", e);
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Hero Section */}
      <section className="mb-16 text-center">
        <h1 className="mb-4 text-5xl font-bold text-gray-900">Agent-VI</h1>
        <p className="text-xl text-gray-600 mb-2">
          가치투자 철학 기반 AI 기업 분석 플랫폼
        </p>
        <p className="text-sm text-gray-500">
          Deep Value & Quality 관점으로 한국 주식을 분석합니다
        </p>
      </section>

      {/* Service Grid */}
      <section className="mb-16">
        <div className="grid md:grid-cols-2 gap-8">
          <ServiceCard
            icon="📊"
            title="AI 종목 추천"
            description="Deep Value & Quality 관점의 AI 분석 보고서"
            highlights={[
              "최신 AI 분석 보고서",
              "가치투자 철학 기반 평가",
              "종합 점수 및 매수의견",
              "뉴스 센티먼트 분석",
            ]}
            href="/insights"
            ctaText="추천 보고서 보기"
          />

          <ServiceCard
            icon="🔍"
            title="종목 리서치 도구"
            description="관심 종목의 재무제표 및 실적 추적"
            highlights={[
              "6년 연간 실적 조회",
              "8분기 분기별 실적 조회",
              "관심 종목 관리",
              "PER/PBR 과거 추이",
            ]}
            href="/research"
            ctaText="리서치 시작하기"
            requiresLogin
          />
        </div>
      </section>

      {/* Quick Stats */}
      {reportCount > 0 && (
        <section className="mb-16 p-8 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl text-center">
          <p className="text-sm text-gray-600 mb-2">
            현재까지
          </p>
          <p className="text-4xl font-bold text-blue-600 mb-1">
            {reportCount}개
          </p>
          <p className="text-gray-700">
            의 AI 분석 보고서가 발행되었습니다
          </p>
        </section>
      )}

      {/* Philosophy Summary */}
      <section className="p-8 bg-gray-50 rounded-xl">
        <h2 className="text-2xl font-semibold mb-6 text-center text-gray-900">
          투자 철학
        </h2>
        <div className="grid md:grid-cols-2 gap-8">
          <div className="p-6 bg-white rounded-lg">
            <h3 className="font-bold text-lg text-blue-600 mb-3">
              Deep Value
            </h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              그레이엄, 버핏의 가치투자 원칙에 따라 내재가치 대비 저평가된 기업을
              발굴합니다. NCAV, PBR, 그레이엄 넘버 등 정량적 지표를 분석합니다.
            </p>
          </div>
          <div className="p-6 bg-white rounded-lg">
            <h3 className="font-bold text-lg text-green-600 mb-3">Quality</h3>
            <p className="text-sm text-gray-600 leading-relaxed">
              높은 ROE, 안정적인 현금흐름, 지속 가능한 경쟁우위를 가진 우량
              기업을 평가합니다. 정성적 분석과 뉴스 센티먼트도 함께 고려합니다.
            </p>
          </div>
        </div>
      </section>

      {/* CTA to Admin for Empty Reports */}
      {reportCount === 0 && (
        <section className="mt-8 p-6 bg-yellow-50 border border-yellow-200 rounded-lg text-center">
          <p className="text-yellow-800 mb-4">
            아직 발행된 보고서가 없습니다.
          </p>
          <Link
            href="/admin"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            관리자 페이지에서 분석 실행
          </Link>
        </section>
      )}
    </div>
  );
}
