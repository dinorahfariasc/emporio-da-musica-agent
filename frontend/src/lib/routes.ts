// Pages anyone can open without a session (the proxy lets them through). The store home is
// public; its chat widget asks for sign-in on its own, and /api/chat stays protected.
const PUBLIC_PAGES = ["/"];

export function isPublicPage(pathname: string): boolean {
  return PUBLIC_PAGES.includes(pathname);
}
