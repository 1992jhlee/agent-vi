interface FinancialStatement {
  fiscal_year: number;
  fiscal_quarter: number;
  revenue: number | null;
  operating_income: number | null;
  net_income: number | null;
  metadata?: {
    revenue_estimated?: boolean;
    revenue_source?: string;
    [key: string]: any;
  };
}

interface Props {
  type: "annual" | "quarterly";
  data: FinancialStatement[];
}

export default function FinancialTable({ type, data }: Props) {
  // 억 원 단위 포맷팅
  const formatAmount = (amount: number | null, fiscalYear: number, fiscalQuarter: number) => {
    if (amount === null || amount === undefined) {
      // 현재 연도 또는 미래 분기는 "발표 전"으로 표시
      const currentYear = new Date().getFullYear();
      const currentMonth = new Date().getMonth() + 1;
      const currentQuarter = Math.floor((currentMonth - 1) / 3) + 1;

      // 연간 실적: 현재 연도 이후거나, 현재 연도 3월 이전이면 발표 전
      if (fiscalQuarter === 4) {
        if (fiscalYear >= currentYear) {
          return "(발표 전)";
        }
      } else {
        // 분기 실적: 현재 분기 이후면 발표 전
        if (
          fiscalYear > currentYear ||
          (fiscalYear === currentYear && fiscalQuarter >= currentQuarter)
        ) {
          return "(발표 전)";
        }
      }
      return "-";
    }
    const billions = amount / 100_000_000; // 원 → 억 원
    return billions.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
  };

  // 전년 대비 증감률 (역순이므로 이전 데이터는 idx - 1)
  const calculateGrowth = (current: number | null, previous: number | null) => {
    if (!current || !previous) return null;
    const growth = ((current - previous) / previous) * 100;
    return growth.toFixed(1);
  };

  // 항목별 데이터 구성
  const rows = [
    {
      label: "매출액",
      key: "revenue" as keyof FinancialStatement,
      showGrowth: true,
    },
    {
      label: "영업이익",
      key: "operating_income" as keyof FinancialStatement,
      showGrowth: false,
    },
    {
      label: "순이익",
      key: "net_income" as keyof FinancialStatement,
      showGrowth: false,
    },
  ];

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border border-gray-300">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-4 py-3 text-left font-semibold border-b sticky left-0 bg-gray-100">
              항목 (억 원)
            </th>
            {data.map((col) => (
              <th
                key={`${col.fiscal_year}-${col.fiscal_quarter}`}
                className="px-4 py-3 text-right font-semibold border-b min-w-[120px]"
              >
                {type === "annual"
                  ? `${col.fiscal_year}년`
                  : `${col.fiscal_year}년 ${col.fiscal_quarter}Q`}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-b hover:bg-gray-50">
              <td className="px-4 py-3 font-medium sticky left-0 bg-white">
                {row.label}
              </td>
              {data.map((col, idx) => {
                const value = col[row.key] as number | null;
                const prevValue =
                  idx > 0 ? (data[idx - 1][row.key] as number | null) : null;
                const growth =
                  row.showGrowth && prevValue
                    ? calculateGrowth(value, prevValue)
                    : null;

                const isEstimated =
                  row.key === "revenue" &&
                  col.metadata?.revenue_estimated === true;
                const estimatedSource = col.metadata?.revenue_source;

                return (
                  <td
                    key={`${col.fiscal_year}-${col.fiscal_quarter}-${row.key}`}
                    className="px-4 py-3 text-right relative group"
                  >
                    <div className="flex items-center justify-end">
                      {formatAmount(value, col.fiscal_year, col.fiscal_quarter)}
                      {isEstimated && (
                        <span
                          className="ml-1 text-orange-500 cursor-help"
                          title={`추정값: '${estimatedSource}' 항목을 매출액으로 판단했습니다`}
                        >
                          *
                        </span>
                      )}
                    </div>
                    {growth && (
                      <div
                        className={`text-xs mt-1 ${
                          parseFloat(growth) >= 0
                            ? "text-red-600"
                            : "text-blue-600"
                        }`}
                      >
                        ({growth > "0" ? "+" : ""}
                        {growth}%)
                      </div>
                    )}
                    {isEstimated && (
                      <div className="hidden group-hover:block absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-800 text-white text-xs rounded whitespace-nowrap z-10">
                        추정값: &apos;{estimatedSource}&apos; 항목을 매출액으로 판단
                        <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-800"></div>
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
