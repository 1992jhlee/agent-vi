import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent-VI | 가치투자 기업 분석",
  description:
    "가치투자 철학 기반의 AI 기업 분석 보고서 - Deep Value & Quality 관점",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="border-b bg-white">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
            <a href="/" className="text-xl font-bold tracking-tight">
              Agent-VI
            </a>
            <div className="flex gap-6 text-sm">
              <a href="/reports" className="hover:text-blue-600">
                보고서
              </a>
              <a href="/companies" className="hover:text-blue-600">
                기업 목록
              </a>
              <a href="/admin" className="hover:text-blue-600">
                관리자
              </a>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="border-t bg-white py-6 text-center text-sm text-gray-500">
          Agent-VI &mdash; 가치투자 기업 분석 에이전트
        </footer>
      </body>
    </html>
  );
}
