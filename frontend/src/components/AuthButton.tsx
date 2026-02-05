"use client";

import { signIn, signOut, useSession } from "next-auth/react";
import { clearAuthToken } from "@/lib/api";

export default function AuthButton() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <span className="text-sm text-gray-400">...</span>;
  }

  if (session) {
    return (
      <button
        onClick={async () => {
          clearAuthToken();
          await signOut({ redirect: true, redirectTo: "/" });
        }}
        className="text-sm text-gray-600 hover:text-red-600 transition-colors"
      >
        로그아웃
      </button>
    );
  }

  return (
    <button
      onClick={() => signIn("google")}
      className="px-3 py-1 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
    >
      Google 로그인
    </button>
  );
}
