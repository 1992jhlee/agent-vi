"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useSession, signIn } from "next-auth/react";
import { getWatchlist, removeFromWatchlist } from "@/lib/api";
import { CompanyListResponse } from "@/lib/types";
import CompanyCreateModal from "@/components/companies/CompanyCreateModal";

export default function CompaniesPage() {
  const { data: session, status: sessionStatus } = useSession();
  const [data, setData] = useState<CompanyListResponse | null>(null);
  const [search, setSearch] = useState("");
  const [market, setMarket] = useState("");
  const [page, setPage] = useState(1);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchWatchlist = useCallback(async () => {
    setLoading(true);
    try {
      const result = await getWatchlist({
        page,
        per_page: 20,
        market: market || undefined,
        q: search || undefined,
      });
      setData(result);
    } catch (e) {
      console.error("Failed to fetch watchlist:", e);
    } finally {
      setLoading(false);
    }
  }, [page, market, search]);

  useEffect(() => {
    if (session) {
      fetchWatchlist();
    }
  }, [session, fetchWatchlist]);

  const handleSearch = () => {
    setPage(1);
    fetchWatchlist();
  };

  const handleRemove = async (stockCode: string) => {
    try {
      await removeFromWatchlist(stockCode);
      fetchWatchlist();
    } catch (e) {
      console.error("Failed to remove from watchlist:", e);
    }
  };

  // 세션 로딩 중
  if (sessionStatus === "loading") {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center py-12">
          <p className="text-gray-500">로딩 중...</p>
        </div>
      </div>
    );
  }

  // 미로그인
  if (!session) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">종목 리서치</h1>
        <div className="p-12 bg-gray-50 border border-gray-200 rounded-lg text-center">
          <p className="text-gray-600 text-lg mb-2">관심종목을 관리하려면 로그인이 필요합니다.</p>
          <p className="text-gray-400 text-sm mb-6">로그인 후 관심종목을 추가하고 나만의 종목 리스트를 구성할 수 있습니다.</p>
          <button
            onClick={() => signIn("google")}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Google 로그인
          </button>
        </div>
      </div>
    );
  }

  // 로그인된 상태
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">종목 리서치</h1>
        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          + 종목 등록
        </button>
      </div>

      {/* 검색 & 필터 */}
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          placeholder="종목명 또는 종목코드 검색"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <select
          value={market}
          onChange={(e) => {
            setMarket(e.target.value);
            setPage(1);
          }}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">전체</option>
          <option value="KOSPI">KOSPI</option>
          <option value="KOSDAQ">KOSDAQ</option>
        </select>
        <button
          onClick={handleSearch}
          className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
        >
          검색
        </button>
      </div>

      {/* 테이블 */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">로딩 중...</p>
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="overflow-x-auto">
            <table className="min-w-full border border-gray-300">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold border-b">종목코드</th>
                  <th className="px-4 py-3 text-left font-semibold border-b">기업명</th>
                  <th className="px-4 py-3 text-left font-semibold border-b">시장</th>
                  <th className="px-4 py-3 text-left font-semibold border-b">섹터</th>
                  <th className="px-4 py-3 text-right font-semibold border-b">액션</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((company) => (
                  <tr key={company.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3">{company.stock_code}</td>
                    <td className="px-4 py-3 font-medium">{company.company_name}</td>
                    <td className="px-4 py-3">{company.market}</td>
                    <td className="px-4 py-3">{company.sector || "-"}</td>
                    <td className="px-4 py-3 text-right flex items-center justify-end gap-3">
                      <Link
                        href={`/research/${company.stock_code}`}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        상세 보기 →
                      </Link>
                      <button
                        onClick={() => handleRemove(company.stock_code)}
                        className="text-gray-400 hover:text-red-500 transition-colors"
                        title="관심종목 제거"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 페이지네이션 */}
          {data.total_pages > 1 && (
            <div className="flex justify-center gap-2 mt-6">
              {Array.from({ length: data.total_pages }, (_, i) => i + 1).map((p) => (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`px-3 py-1 border rounded ${
                    p === page
                      ? "bg-blue-600 text-white border-blue-600"
                      : "hover:bg-gray-100"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </>
      ) : (
        <div className="p-8 bg-gray-50 border border-gray-200 rounded-lg text-center">
          <p className="text-gray-500 mb-2">관심종목이 없습니다.</p>
          <p className="text-gray-400 text-sm">
            위의 &quot;+ 종목 등록&quot; 버튼으로 관심종목을 추가해보세요.
          </p>
        </div>
      )}

      {/* 모달 */}
      <CompanyCreateModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => {
          setIsModalOpen(false);
          fetchWatchlist();
        }}
      />
    </div>
  );
}
