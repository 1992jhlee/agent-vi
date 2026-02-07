"use client";

import Link from "next/link";
import NavTab from "./NavTab";
import { useActiveService } from "./useActiveService";
import AuthButton from "../AuthButton";

export default function MainNav() {
  const { isInsightsActive, isResearchActive } = useActiveService();

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      <nav className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link
            href="/"
            className="text-2xl font-bold text-gray-900 hover:text-blue-600 transition-colors"
          >
            Agent-VI
          </Link>

          {/* Main Service Tabs */}
          <div className="flex items-center gap-3">
            <NavTab href="/insights" active={isInsightsActive}>
              📊 추천
            </NavTab>
            <NavTab href="/research" active={isResearchActive}>
              🔍 리서치
            </NavTab>
          </div>

          {/* Right utilities */}
          <div className="flex items-center gap-4">
            <Link
              href="/admin"
              className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
            >
              관리자
            </Link>
            <AuthButton />
          </div>
        </div>
      </nav>
    </header>
  );
}
