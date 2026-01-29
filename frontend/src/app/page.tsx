export default function HomePage() {
  return (
    <div>
      <section className="mb-12 text-center">
        <h1 className="mb-4 text-4xl font-bold">Agent-VI</h1>
        <p className="text-lg text-gray-600">
          가치투자 철학 기반 AI 기업 분석 보고서
        </p>
        <p className="mt-2 text-sm text-gray-500">
          Deep Value &amp; Quality 관점에서 한국 주식을 분석합니다
        </p>
      </section>

      <section>
        <h2 className="mb-6 text-2xl font-semibold">최근 보고서</h2>
        <p className="text-gray-500">
          아직 발행된 보고서가 없습니다. 관리자 페이지에서 분석을 실행해주세요.
        </p>
      </section>
    </div>
  );
}
