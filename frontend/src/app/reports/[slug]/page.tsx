interface ReportPageProps {
  params: Promise<{ slug: string }>;
}

export default async function ReportDetailPage({ params }: ReportPageProps) {
  const { slug } = await params;

  return (
    <div>
      <h1 className="mb-6 text-3xl font-bold">보고서 상세</h1>
      <p className="text-gray-500">보고서 slug: {slug}</p>
      {/* TODO: Fetch and render full report */}
    </div>
  );
}
