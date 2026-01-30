"use client";

import { useState, useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface StockSearchResult {
  stock_code: string;
  company_name: string;
  market: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CompanyCreateModal({ isOpen, onClose, onSuccess }: Props) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<StockSearchResult[]>([]);
  const [selected, setSelected] = useState<StockSearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 종목 검색 (디바운싱)
  useEffect(() => {
    if (query.length < 1) {
      setSuggestions([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/stocks/search?q=${encodeURIComponent(query)}`);
        if (res.ok) {
          const data = await res.json();
          setSuggestions(data);
        }
      } catch (e) {
        console.error("검색 실패:", e);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/v1/companies`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          stock_code: selected.stock_code,
          company_name: selected.company_name,
          market: selected.market,
        }),
      });

      if (res.ok) {
        onSuccess();
        onClose();
        setQuery("");
        setSelected(null);
      } else {
        const data = await res.json();
        setError(data.detail || "등록 실패");
      }
    } catch (e) {
      setError("네트워크 오류");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h2 className="text-xl font-semibold mb-4">종목 등록</h2>

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              종목명 또는 종목코드 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelected(null);
              }}
              placeholder="예: 삼성전자, 005930"
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            {/* 자동완성 드롭다운 */}
            {suggestions.length > 0 && !selected && (
              <ul className="mt-2 border rounded-lg max-h-60 overflow-y-auto">
                {suggestions.map((item) => (
                  <li
                    key={item.stock_code}
                    onClick={() => {
                      setSelected(item);
                      setQuery(`${item.company_name} (${item.stock_code})`);
                      setSuggestions([]);
                    }}
                    className="px-4 py-2 hover:bg-gray-100 cursor-pointer"
                  >
                    <div className="font-medium">{item.company_name}</div>
                    <div className="text-sm text-gray-500">
                      {item.stock_code} · {item.market}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* 선택된 종목 표시 */}
          {selected && (
            <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-gray-700">선택된 종목:</p>
              <p className="font-semibold">
                {selected.company_name} ({selected.stock_code})
              </p>
            </div>
          )}

          {error && <p className="text-sm text-red-600 mb-4">{error}</p>}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded-lg hover:bg-gray-100"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={!selected || loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
            >
              {loading ? "등록 중..." : "등록"}
            </button>
          </div>
        </form>

        <p className="text-xs text-gray-500 mt-4">
          등록 후 재무데이터가 자동으로 수집됩니다.
        </p>
      </div>
    </div>
  );
}
