import { notFound } from "next/navigation";
import { getCompany, getFinancials } from "@/lib/api";
import FinancialTable from "@/components/companies/FinancialTable";

interface Props {
  params: Promise<{ stock_code: string }>;
}

export default async function CompanyDetailPage({ params }: Props) {
  const { stock_code } = await params;

  try {
    const company = await getCompany(stock_code);
    const financialData = await getFinancials(stock_code, 6);

    // 연간 실적 (fiscal_quarter === 4)
    const annualData = financialData.statements
      .filter((s: any) => s.fiscal_quarter === 4)
      .sort((a: any, b: any) => b.fiscal_year - a.fiscal_year)
      .slice(0, 6);

    // 분기 실적 (fiscal_quarter !== 4)
    const quarterlyData = financialData.statements
      .filter((s: any) => s.fiscal_quarter !== 4)
      .sort((a: any, b: any) => {
        if (a.fiscal_year !== b.fiscal_year) {
          return b.fiscal_year - a.fiscal_year;
        }
        return b.fiscal_quarter - a.fiscal_quarter;
      })
      .slice(0, 8);

    return (
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">{company.company_name}</h1>
          <p className="text-gray-600">
            {stock_code} · {company.market}
            {company.sector && ` · ${company.sector}`}
          </p>
        </div>

        {/* 연간 실적 */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">연간 실적 (최근 6년)</h2>
          {annualData.length > 0 ? (
            <FinancialTable type="annual" data={annualData} />
          ) : (
            <div className="p-8 bg-gray-50 border border-gray-200 rounded-lg text-center">
              <p className="text-gray-500">
                데이터 수집 중입니다. 잠시 후 새로고침해주세요.
              </p>
            </div>
          )}
        </section>

        {/* 분기 실적 */}
        <section>
          <h2 className="text-2xl font-semibold mb-4">분기 실적 (최근 8분기)</h2>
          {quarterlyData.length > 0 ? (
            <FinancialTable type="quarterly" data={quarterlyData} />
          ) : (
            <div className="p-8 bg-gray-50 border border-gray-200 rounded-lg text-center">
              <p className="text-gray-500">
                데이터 수집 중입니다. 잠시 후 새로고침해주세요.
              </p>
            </div>
          )}
        </section>
      </div>
    );
  } catch (e) {
    notFound();
  }
}
