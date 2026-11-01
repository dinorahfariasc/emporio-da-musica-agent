// Redirects unauthenticated requests to /login (FR-005/FR-006). callbackUrl is accepted only as a
// same-site relative path (never an absolute/external URL), per the spec's edge cases.
//
// Next.js 16 renamed "middleware" to "proxy"; with a src/ layout this file must live at
// src/proxy.ts (next to app/), not at the project root, or it is silently never loaded.
import { NextResponse } from "next/server";

import { isPublic, isSameSitePath } from "@/lib/auth/request-guards";
import { auth } from "../auth";

export default auth((request) => {
  const { pathname, search } = request.nextUrl;

  if (pathname === "/login") {
    if (request.auth) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  if (isPublic(pathname)) {
    return NextResponse.next();
  }

  if (!request.auth) {
    const callbackUrl = `${pathname}${search}`;
    const loginUrl = new URL("/login", request.url);
    if (isSameSitePath(callbackUrl)) {
      loginUrl.searchParams.set("callbackUrl", callbackUrl);
    }
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
