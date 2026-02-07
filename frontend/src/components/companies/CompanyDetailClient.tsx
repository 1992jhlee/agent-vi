"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getFinancials } from "@/lib/api";
import { FinancialStatement } from "@/lib/types";
import FinancialTabView from "@/components/companies/FinancialTabView";
import RefreshFinancialButton from "@/components/companies/RefreshFinancialButton";

interface Company {
  stock_code: string;
  company_name: string;
  market: string;
  sector?: string;
}

interface Props {
  company: Company;
  stockCode: string;
  initialData: {
    stock_code: string;
    company_name: string;
    statements: FinancialStatement[];
  };
}

export default function CompanyDetailClient({ company, stockCode, initialData }: Props) {
  const [financialData, setFinancialData] = useState(initialData);
  const [isLoading, setIsLoading] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // 연간 실적 (report_type === 'annual')
  const annualData = financialData.statements
    .filter((s: any) => s.report_type === 'annual')
    .sort((a: any, b: any) => b.fiscal_year - a.fiscal_year)
    .slice(0, 6);

  // 분기 실적 (report_type === 'quarterly')
  const quarterlyData = financialData.statements
    .filter((s: any) => s.report_type === 'quarterly')
    .sort((a: any, b: any) => {
      if (a.fiscal_year !== b.fiscal_year) {
        return b.fiscal_year - a.fiscal_year;
      }
      return b.fiscal_quarter - a.fiscal_quarter;
    })
    .slice(0, 8);

  // PER/PBR 데이터가 있는지 확인
  const hasPerPbrData = (data: FinancialStatement[]) => {
    // 데이터가 하나라도 있고, PER 또는 PBR이 null이 아닌 항목이 있으면 true
    if (data.length === 0) return false;
    return data.some(s => s.per !== null || s.pbr !== null);
  };

  const annualHasData = hasPerPbrData(annualData);
  const quarterlyHasData = hasPerPbrData(quarterlyData);

  // 데이터가 있고, PER/PBR이 없으면 로딩 상태
  const needsLoading = (annualData.length > 0 || quarterlyData.length > 0) &&
                       (!annualHasData || !quarterlyHasData);

  // 폴링: PER/PBR 데이터가 없으면 주기적으로 재조회
  useEffect(() => {
    if (!needsLoading || retryCount >= 20) {
      // 데이터가 준비되었거나 최대 재시도 횟수 초과
      setIsLoading(false);
      return;
    }

    setIsLoading(true);

    // 3초마다 재조회 (최대 20번 = 1분)
    const timer = setTimeout(async () => {
      try {
        const updatedData = await getFinancials(stockCode, 6);
        setFinancialData(updatedData);
        setRetryCount(prev => prev + 1);
      } catch (error) {
        console.error("재무 데이터 재조회 실패:", error);
        setRetryCount(prev => prev + 1);
      }
    }, 3000);

    return () => clearTimeout(timer);
  }, [stockCode, needsLoading, retryCount]);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* 뒤로 가기 버튼 */}
      <div className="mb-6">
        <Link
          href="/companies"
          className="inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors"
        >
          <svg
            className="w-5 h-5 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 19l-7-7m0 0l7-7m-7 7h18"
            />
          </svg>
          목록으로 돌아가기
        </Link>
      </div>

      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">{company.company_name}</h1>
        <p className="text-gray-600">
          {stockCode} · {company.market}
          {company.sector && ` · ${company.sector}`}
        </p>
      </div>

      {/* 재무 데이터 갱신 버튼 */}
      {(annualData.length === 0 || quarterlyData.length === 0) && (
        <div className="mb-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800 mb-3">
            재무 데이터가 없거나 부족합니다. 아래 버튼을 눌러 데이터를 수집해주세요.
          </p>
          <RefreshFinancialButton stockCode={stockCode} />
        </div>
      )}

      {/* 로딩 상태 표시 */}
      {isLoading && needsLoading && (
        <div className="mb-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-4"></div>
            <div>
              <p className="text-blue-900 font-medium">재무 지표 계산 중...</p>
              <p className="text-sm text-blue-700 mt-1">
                PER/PBR 등의 투자 지표를 계산하고 있습니다. 잠시만 기다려주세요.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 재무 실적 (연간/분기 토글) */}
      {!isLoading && (
        <FinancialTabView annualData={annualData} quarterlyData={quarterlyData} />
      )}
    </div>
  );
}
