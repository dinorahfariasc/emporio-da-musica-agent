// Pure helpers for middleware.ts, kept here (under src) so they are unit-testable without
// exercising Auth.js's cookie/JWT machinery.
const PUBLIC_PATHS = ["/login", "/api/auth", "/api/health"];

export function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

// A callbackUrl must be a same-site relative path: never an absolute/external URL
// (open-redirect guard, spec FR-005).
export function isSameSitePath(value: string | null): value is string {
  return !!value && value.startsWith("/") && !value.startsWith("//");
}
