import { SignJWT } from "jose";
import { NextResponse } from "next/server";
import { auth } from "@/auth";

/**
 * GET /api/auth/token
 *
 * 서버 전용 엔드포인트. NextAuth 세션을 읽고 백엔드용 HS256 JWT를 생성합니다.
 * JWT payload는 { sub: google_user_id }만 포함합니다.
 * AUTH_SECRET은 서버에서만 접근 — 클라이언트에 노출되지 않습니다.
 */
export const GET = auth(async (req) => {
  const session = req.auth;

  if (!session?.user?.id) {
    return NextResponse.json({ error: "로그인 필요" }, { status: 401 });
  }

  const secret = process.env.AUTH_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "AUTH_SECRET not configured" },
      { status: 500 }
    );
  }

  const token = await new SignJWT({ sub: session.user.id })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("1h")
    .sign(new TextEncoder().encode(secret));

  return NextResponse.json({ token });
});
