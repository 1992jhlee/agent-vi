"use client";

import { useState } from "react";
import { FinancialStatement } from "@/lib/types";
import FinancialTable from "@/components/companies/FinancialTable";

interface Props {
  annualData: FinancialStatement[];
  quarterlyData: FinancialStatement[];
}

export default function FinancialTabView({ annualData, quarterlyData }: Props) {
  const [tab, setTab] = useState<"annual" | "quarterly">("annual");

  return (
    <div>
      {/* 탭 토글 */}
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        <button
          onClick={() => setTab("annual")}
          className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
            tab === "annual"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          연간 (최근 6년)
        </button>
        <button
          onClick={() => setTab("quarterly")}
          className={`px-4 py-1.5 text-sm font-medium rounded-md transition-colors ${
            tab === "quarterly"
              ? "bg-white text-gray-900 shadow-sm"
              : "text-gray-600 hover:text-gray-900"
          }`}
        >
          분기 (최근 8분기)
        </button>
      </div>

      {/* 테이블 */}
      {tab === "annual" ? (
        annualData.length > 0 ? (
          <FinancialTable type="annual" data={annualData} />
        ) : (
          <div className="p-8 bg-gray-50 border border-gray-200 rounded-lg text-center">
            <p className="text-gray-500">
              데이터 수집 중입니다. 잠시 후 새로고침해주세요.
            </p>
          </div>
        )
      ) : (
        quarterlyData.length > 0 ? (
          <FinancialTable type="quarterly" data={quarterlyData} />
        ) : (
          <div className="p-8 bg-gray-50 border border-gray-200 rounded-lg text-center">
            <p className="text-gray-500">
              데이터 수집 중입니다. 잠시 후 새로고침해주세요.
            </p>
          </div>
        )
      )}
    </div>
  );
}
