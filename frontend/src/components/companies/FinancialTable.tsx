interface FinancialStatement {
  fiscal_year: number;
  fiscal_quarter: number;
  revenue: number | null;
  operating_income: number | null;
  net_income: number | null;
}

interface Props {
  type: "annual" | "quarterly";
  data: FinancialStatement[];
}

export default function FinancialTable({ type, data }: Props) {
  // 억 원 단위 포맷팅
  const formatAmount = (amount: number | null) => {
    if (amount === null || amount === undefined) return "-";
    const billions = amount / 100_000_000; // 원 → 억 원
    return billions.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
  };

  // 전년 대비 증감률
  const calculateGrowth = (current: number | null, previous: number | null) => {
    if (!current || !previous) return null;
    const growth = ((current - previous) / previous) * 100;
    return growth.toFixed(1);
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border border-gray-300">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-4 py-3 text-left font-semibold border-b">
              {type === "annual" ? "연도" : "분기"}
            </th>
            <th className="px-4 py-3 text-right font-semibold border-b">
              매출액 (억 원)
            </th>
            <th className="px-4 py-3 text-right font-semibold border-b">
              영업이익 (억 원)
            </th>
            <th className="px-4 py-3 text-right font-semibold border-b">
              순이익 (억 원)
            </th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => {
            const prevRow = data[idx + 1];
            const revenueGrowth = prevRow
              ? calculateGrowth(row.revenue, prevRow.revenue)
              : null;

            return (
              <tr
                key={`${row.fiscal_year}-${row.fiscal_quarter}`}
                className="border-b hover:bg-gray-50"
              >
                <td className="px-4 py-3 font-medium">
                  {type === "annual"
                    ? `${row.fiscal_year}년`
                    : `${row.fiscal_year}년 ${row.fiscal_quarter}Q`}
                </td>
                <td className="px-4 py-3 text-right">
                  {formatAmount(row.revenue)}
                  {revenueGrowth && (
                    <span
                      className={`ml-2 text-xs ${
                        parseFloat(revenueGrowth) >= 0
                          ? "text-red-600"
                          : "text-blue-600"
                      }`}
                    >
                      ({revenueGrowth > 0 ? "+" : ""}
                      {revenueGrowth}%)
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  {formatAmount(row.operating_income)}
                </td>
                <td className="px-4 py-3 text-right">
                  {formatAmount(row.net_income)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
