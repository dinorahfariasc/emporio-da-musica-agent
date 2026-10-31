// BACKEND_URL is injected by the Vercel Services binding in production
// and set in .env.local for local development.
export function backendUrl(path: string): URL {
  const base = process.env.BACKEND_URL;
  if (!base) {
    throw new Error("BACKEND_URL is not configured");
  }
  return new URL(path, base);
}
