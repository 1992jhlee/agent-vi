export default function KnowledgePage() {
  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">투자 철학 관리</h1>
      <p className="mb-4 text-gray-600">
        에이전트가 기업 분석 시 참고하는 투자 철학 문서를 편집합니다.
      </p>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="mb-2 text-xl font-semibold">Deep Value</h2>
          <p className="mb-4 text-sm text-gray-500">
            자산가치 대비 저평가 기업 발굴 원칙
          </p>
          {/* TODO: Markdown editor */}
          <p className="text-gray-400">마크다운 에디터 구현 예정</p>
        </div>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="mb-2 text-xl font-semibold">Quality</h2>
          <p className="mb-4 text-sm text-gray-500">
            우수 기업을 합리적 가격에 매수하는 원칙
          </p>
          {/* TODO: Markdown editor */}
          <p className="text-gray-400">마크다운 에디터 구현 예정</p>
        </div>
      </div>
    </div>
  );
}
