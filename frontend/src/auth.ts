import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    jwt({ token, account }) {
      // 첫 로그인 시 Google sub만 유지 — name/email/image는 세션에 저장하지 않음
      if (account) {
        return { sub: account.providerAccountId };
      }
      return token;
    },
    session({ session, token }) {
      return {
        ...session,
        user: { id: token.sub as string },
      };
    },
  },
});
