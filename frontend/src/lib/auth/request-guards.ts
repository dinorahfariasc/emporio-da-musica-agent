// Pure helpers for proxy.ts (and the login form), kept here (under src) so they are unit-testable
// without exercising Auth.js's cookie/JWT machinery.
const PUBLIC_PATHS = ["/login", "/api/auth", "/api/health"];

export function isPublic(pathname: string): boolean {
  return PUBLIC_PATHS.some((path) => pathname === path || pathname.startsWith(`${path}/`));
}

// A callbackUrl must resolve to the same origin as a real relative path: never an absolute/
// external URL, a protocol-relative one, or something a browser would normalize into one.
// `value.startsWith("/") && !value.startsWith("//")` is NOT enough: a browser normalizes a
// backslash to a forward slash before parsing a URL, so "/\evil.com" becomes "//evil.com" (a
// protocol-relative URL to "evil.com") even though the raw string looks like a same-site path.
// Parsing with `new URL(value, origin)` and comparing origins catches that (and any other
// normalization quirk) by construction, instead of trying to enumerate every bypass by hand.
export function safeCallbackPath(value: string | null, origin: string): string {
  const fallback = "/";
  if (!value) return fallback;
  // Reject backslashes and control characters outright: both are legitimate browser-level
  // normalization triggers before a URL is ever parsed, so rejecting the raw string is safer
  // than trusting the parser alone.
  if (/[\\\x00-\x1f]/.test(value)) return fallback;
  if (!value.startsWith("/")) return fallback;
  let url: URL;
  try {
    url = new URL(value, origin);
  } catch {
    return fallback;
  }
  if (url.origin !== origin) return fallback;
  return `${url.pathname}${url.search}${url.hash}`;
}

// Kept for call sites that only need a yes/no (not the resolved path).
export function isSameSitePath(value: string | null, origin: string): boolean {
  return value !== null && safeCallbackPath(value, origin) === value;
}
