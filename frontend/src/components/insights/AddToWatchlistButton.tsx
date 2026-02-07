"use client";

import { useState } from "react";
import { useSession, signIn } from "next-auth/react";
import { useRouter } from "next/navigation";
import { addToWatchlist } from "@/lib/api";

interface AddToWatchlistButtonProps {
  stockCode: string;
  companyName: string;
  market?: string;
}

export default function AddToWatchlistButton({
  stockCode,
  companyName,
  market = "KOSPI", // default fallback
}: AddToWatchlistButtonProps) {
  const { data: session } = useSession();
  const router = useRouter();
  const [added, setAdded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  const handleAdd = async () => {
    if (!session) {
      // Redirect to login with return URL
      signIn("google", {
        callbackUrl: window.location.href,
      });
      return;
    }

    setLoading(true);
    try {
      await addToWatchlist({
        stock_code: stockCode,
        company_name: companyName,
        market: market,
      });
      setAdded(true);
      setShowSuccess(true);

      // Hide success message after 3 seconds
      setTimeout(() => {
        setShowSuccess(false);
      }, 3000);
    } catch (e) {
      console.error("Failed to add to watchlist:", e);
      alert("관심 종목 추가에 실패했습니다. 이미 추가된 종목일 수 있습니다.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoToResearch = () => {
    router.push("/research");
  };

  if (added) {
    return (
      <div className="flex flex-col gap-3">
        <button
          disabled
          className="flex items-center justify-center px-6 py-3 bg-green-100 text-green-700 rounded-lg font-medium cursor-not-allowed"
        >
          ✓ 관심 종목에 추가됨
        </button>
        {showSuccess && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800 mb-2">
              관심 종목에 추가되었습니다!
            </p>
            <button
              onClick={handleGoToResearch}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              리서치 페이지로 이동 →
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <button
      onClick={handleAdd}
      disabled={loading}
      className="flex items-center justify-center px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
    >
      {loading ? "추가 중..." : "⭐ 관심 종목 추가"}
    </button>
  );
}
