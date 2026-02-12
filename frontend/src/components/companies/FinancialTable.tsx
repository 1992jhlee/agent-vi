import { FinancialStatement } from "@/lib/types";

interface Props {
  type: "annual" | "quarterly";
  data: FinancialStatement[];
  isCalculatingMetrics?: boolean;
}

export default function FinancialTable({ type, data, isCalculatingMetrics = false }: Props) {
  const formatAmount = (amount: number | null, fiscalYear: number, fiscalQuarter: number) => {
    if (amount === null || amount === undefined) {
      const currentYear = new Date().getFullYear();
      const currentMonth = new Date().getMonth() + 1;
      const currentQuarter = Math.floor((currentMonth - 1) / 3) + 1;

      if (fiscalQuarter === 4) {
        if (fiscalYear >= currentYear) return "(발표 전)";
      } else {
        if (
          fiscalYear > currentYear ||
          (fiscalYear === currentYear && fiscalQuarter >= currentQuarter)
        )
          return "(발표 전)";
      }
      return "-";
    }
    const billions = amount / 100_000_000;
    return billions.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
  };

  const formatPercent = (value: number | null) => {
    if (value === null) return "-";
    return value.toLocaleString("ko-KR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
  };

  const calcDebtRatio = (col: FinancialStatement): number | null => {
    if (col.total_liabilities === null || col.total_equity === null || col.total_equity === 0) return null;
    return (col.total_liabilities / col.total_equity) * 100;
  };

  const calcQuickRatio = (col: FinancialStatement): number | null => {
    if (col.current_assets === null || col.current_liabilities === null || col.current_liabilities === 0) return null;
    return ((col.current_assets - (col.inventories ?? 0)) / col.current_liabilities) * 100;
  };

  const calcFCF = (col: FinancialStatement): number | null => {
    if (col.operating_cash_flow === null || col.capex === null) return null;
    return col.operating_cash_flow - col.capex;
  };

  const calculateGrowth = (current: number | null, previous: number | null) => {
    if (!current || !previous) return null;
    return (((current - previous) / previous) * 100).toFixed(1);
  };

  type AmountRow = {
    label: string;
    key: keyof FinancialStatement;
    showGrowth: boolean;
  };

  type CalcRow = {
    label: string;
    calc: (col: FinancialStatement) => number | null;
    format: "percent" | "amount" | "ratio";
    decimals?: number;
  };

  const incomeRows: AmountRow[] = [
    { label: "매출액", key: "revenue", showGrowth: true },
    { label: "영업이익", key: "operating_income", showGrowth: false },
    { label: "순이익", key: "net_income", showGrowth: false },
  ];

  const balanceRows: CalcRow[] = [
    { label: "부채비율", calc: calcDebtRatio, format: "percent" },
    { label: "당좌비율", calc: calcQuickRatio, format: "percent" },
  ];

  const cashFlowRows: AmountRow[] = [
    { label: "영업활동현금흐름", key: "operating_cash_flow", showGrowth: false },
    { label: "투자활동현금흐름", key: "investing_cash_flow", showGrowth: false },
    { label: "재무활동현금흐름", key: "financing_cash_flow", showGrowth: false },
    { label: "CAPEX", key: "capex", showGrowth: false },
  ];

  const fcfRow: CalcRow = { label: "잉여현금흐름", calc: calcFCF, format: "amount" };

  const formatRatio = (value: number | null, decimals: number = 1) => {
    if (value === null) return "-";
    return value.toFixed(decimals) + "배";
  };

  const calcROE = (col: FinancialStatement): number | null => {
    if (col.net_income === null || col.total_equity === null || col.total_equity === 0) return null;
    return (col.net_income / col.total_equity) * 100;
  };

  const calcROA = (col: FinancialStatement): number | null => {
    if (col.net_income === null || col.total_assets === null || col.total_assets === 0) return null;
    return (col.net_income / col.total_assets) * 100;
  };

  const calcOperatingMargin = (col: FinancialStatement): number | null => {
    if (col.operating_income === null || col.revenue === null || col.revenue === 0) return null;
    return (col.operating_income / col.revenue) * 100;
  };

  const calcNetMargin = (col: FinancialStatement): number | null => {
    if (col.net_income === null || col.revenue === null || col.revenue === 0) return null;
    return (col.net_income / col.revenue) * 100;
  };

  const investmentRows: CalcRow[] = [
    { label: "ROE", calc: calcROE, format: "percent" },
    { label: "ROA", calc: calcROA, format: "percent" },
    { label: "영업이익률", calc: calcOperatingMargin, format: "percent" },
    { label: "순이익률", calc: calcNetMargin, format: "percent" },
    { label: "PER", calc: (col) => col.per, format: "ratio", decimals: 1 },
    { label: "PBR", calc: (col) => col.pbr, format: "ratio", decimals: 2 },
  ];

  const renderSectionHeader = (label: string) => (
    <tr key={`section-${label}`}>
      <td
        colSpan={1 + data.length}
        className="px-4 py-2 bg-gray-100 text-xs font-semibold text-gray-600 border-b"
      >
        {label}
      </td>
    </tr>
  );

  const renderAmountRow = (row: AmountRow) => (
    <tr key={row.key} className="border-b hover:bg-gray-50">
      <td className="px-4 py-3 font-medium sticky left-0 bg-white">
        {row.label}
      </td>
      {data.map((col, idx) => {
        const value = col[row.key] as number | null;
        const prevValue = idx > 0 ? (data[idx - 1][row.key] as number | null) : null;
        const growth = row.showGrowth ? calculateGrowth(value, prevValue) : null;

        return (
          <td
            key={`${col.fiscal_year}-${col.fiscal_quarter}-${row.key}`}
            className="px-4 py-3 text-right"
          >
            {formatAmount(value, col.fiscal_year, col.fiscal_quarter)}
            {growth && (
              <div
                className={`text-xs mt-1 ${
                  parseFloat(growth) >= 0 ? "text-red-600" : "text-blue-600"
                }`}
              >
                ({parseFloat(growth) >= 0 ? "+" : ""}{growth}%)
              </div>
            )}
          </td>
        );
      })}
    </tr>
  );

  const renderCalcRow = (row: CalcRow) => {
    const isPerOrPbr = row.label === "PER" || row.label === "PBR";

    return (
      <tr key={row.label} className="border-b hover:bg-gray-50">
        <td className="px-4 py-3 font-medium sticky left-0 bg-white">
          {row.label}
        </td>
        {data.map((col) => {
          const value = row.calc(col);
          const showLoadingIndicator = isCalculatingMetrics && isPerOrPbr && value === null;

          return (
            <td
              key={`${col.fiscal_year}-${col.fiscal_quarter}-${row.label}`}
              className="px-4 py-3 text-right"
            >
              {showLoadingIndicator ? (
                <div className="flex items-center justify-end gap-2">
                  <div className="animate-spin rounded-full h-3 w-3 border border-gray-300 border-t-blue-500" />
                  <span className="text-xs text-gray-400">계산 중...</span>
                </div>
              ) : (
                <>
                  {row.format === "percent"
                    ? formatPercent(value)
                    : row.format === "ratio"
                    ? formatRatio(value, row.decimals)
                    : formatAmount(value, col.fiscal_year, col.fiscal_quarter)}
                </>
              )}
            </td>
          );
        })}
      </tr>
    );
  };

  return (
    <div>
      <p className="text-xs text-gray-500 text-right mb-1">(단위: 억원 / 비율: % · 배)</p>
      <div className="overflow-x-auto">
        <table className="min-w-full border border-gray-300">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-3 text-left font-semibold border-b sticky left-0 bg-gray-100">
                항목
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
            {renderSectionHeader("손익계산서")}
            {incomeRows.map(renderAmountRow)}
            {renderSectionHeader("재무상태표")}
            {balanceRows.map(renderCalcRow)}
            {renderSectionHeader("현금흐름표")}
            {cashFlowRows.map(renderAmountRow)}
            {renderCalcRow(fcfRow)}
            {renderSectionHeader("투자지표")}
            {investmentRows.map(renderCalcRow)}
          </tbody>
        </table>
      </div>
    </div>
  );
}
