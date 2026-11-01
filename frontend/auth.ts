// Auth.js v5 config (research.md R1): Credentials provider, JWT session strategy, no OAuth/sign-up.
import bcrypt from "bcryptjs";
import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";

import { findUserByUsername, getPool } from "@/lib/auth/db";
import { clearAttempts, isLockedOut, recordFailedAttempt } from "@/lib/auth/lockout";

const SESSION_MAX_AGE_SECONDS = 30 * 24 * 60 * 60; // 30 days (research.md R8)

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt", maxAge: SESSION_MAX_AGE_SECONDS },
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      credentials: { username: {}, password: {} },
      async authorize(credentials) {
        const username = String(credentials?.username ?? "").trim().toLowerCase();
        const password = String(credentials?.password ?? "");
        if (!username || !password) return null;

        const pool = getPool();
        if (await isLockedOut(pool, username)) return null;

        const user = await findUserByUsername(username);
        const valid =
          user && !user.disabledAt && (await bcrypt.compare(password, user.passwordHash));
        if (!valid) {
          await recordFailedAttempt(pool, username);
          return null;
        }
        await clearAttempts(pool, username);
        return { id: user.id, name: user.username };
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
