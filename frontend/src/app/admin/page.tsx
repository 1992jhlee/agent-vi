export default function AdminPage() {
  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">관리자 대시보드</h1>
      <div className="grid gap-6 md:grid-cols-2">
        <a
          href="/admin/knowledge"
          className="rounded-lg border bg-white p-6 shadow-sm hover:shadow-md"
        >
          <h2 className="mb-2 text-xl font-semibold">투자 철학 관리</h2>
          <p className="text-gray-600">
            Deep Value / Quality 투자 철학 마크다운 파일 편집
          </p>
        </a>
        <div className="rounded-lg border bg-white p-6 shadow-sm">
          <h2 className="mb-2 text-xl font-semibold">분석 실행</h2>
          <p className="text-gray-600">기업 분석 파이프라인 실행 및 모니터링</p>
        </div>
      </div>
    </div>
  );
}
