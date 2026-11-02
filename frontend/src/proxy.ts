// Redirects unauthenticated requests to /login (FR-005/FR-006). callbackUrl is accepted only as a
// same-site relative path (never an absolute/external URL), per the spec's edge cases. An
// unauthenticated API request gets a JSON 401 (the chat UI expects that shape, not an HTML
// redirect it would otherwise have to follow and reparse).
//
// Next.js 16 renamed "middleware" to "proxy"; with a src/ layout this file must live at
// src/proxy.ts (next to app/), not at the project root, or it is silently never loaded.
import { NextResponse } from "next/server";

import { isPublic, safeCallbackPath } from "@/lib/auth/request-guards";
import { isPublicPage } from "@/lib/routes";
import { auth } from "../auth";

const UNAUTHORIZED_BODY = {
  error: {
    code: "unauthorized",
    message: "Sua sessão expirou. Entre novamente para continuar.",
  },
};

export default auth((request) => {
  const { pathname, search, origin } = request.nextUrl;

  if (pathname === "/login") {
    if (request.auth) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  // The store home is public (spec 009); its chat widget asks for sign-in itself.
  if (isPublic(pathname) || isPublicPage(pathname)) {
    return NextResponse.next();
  }

  if (!request.auth) {
    if (pathname.startsWith("/api/")) {
      return NextResponse.json(UNAUTHORIZED_BODY, { status: 401 });
    }
    const callbackUrl = safeCallbackPath(`${pathname}${search}`, origin);
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("callbackUrl", callbackUrl);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  // Excludes Next internals and any file with an extension (favicon, public SVGs/images, etc.) —
  // those are static assets, never pages or API routes that need a session.
  matcher: ["/((?!_next/static|_next/image|.*\\..*).*)"],
};
