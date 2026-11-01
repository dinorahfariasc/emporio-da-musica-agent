// Auth.js v5 config (research.md R1): Credentials provider, JWT session strategy, no OAuth/sign-up.
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

import { authorizeCredentials } from "@/lib/auth/authorize";
import { getPool } from "@/lib/auth/db";

const SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60; // 30 days (research.md R8)

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt", maxAge: SESSION_MAX_AGE_SECONDS },
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      credentials: { username: {}, password: {} },
      async authorize(credentials) {
        return authorizeCredentials(
          getPool(),
          String(credentials?.username ?? ""),
          String(credentials?.password ?? ""),
        );
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user?.id) token.sub = user.id;
      return token;
    },
    async session({ session, token }) {
      if (session.user && token.sub) session.user.id = token.sub;
      return session;
    },
  },
});
