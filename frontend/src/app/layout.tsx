import type { Metadata } from "next";
import "./globals.css";
import SessionProvider from "@/components/SessionProvider";
import MainNav from "@/components/navigation/MainNav";

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
        <SessionProvider>
        <MainNav />
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="border-t bg-white py-6 text-center text-sm text-gray-500">
          Agent-VI &mdash; 가치투자 기업 분석 에이전트
        </footer>
        </SessionProvider>
      </body>
    </html>
  );
}
