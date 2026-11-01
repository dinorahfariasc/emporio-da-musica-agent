// Fail-closed production config check for the frontend BFF, mirroring the backend's
// check_fail_closed_config (app/config.py, specs/004-auth-limits-deploy FR-015/research.md R7).
export const MIN_SECRET_LENGTH = 32;

type Env = Record<string, string | undefined>;

function isProduction(env: Env): boolean {
  // Vercel sets VERCEL_ENV=production on the real deployment; NODE_ENV alone can also be
  // "production" for a local production build, so either signal is treated as production.
  return env.NODE_ENV === "production" || env.VERCEL_ENV === "production";
}

export function checkFailClosedConfig(env: Env): void {
  if (!isProduction(env)) return;

  const missing: string[] = [];
  if (!env.DATABASE_URL) missing.push("DATABASE_URL");
  if (!env.BACKEND_URL) missing.push("BACKEND_URL");
  if (missing.length > 0) {
    throw new Error(`Refusing to start in production with missing required config: ${missing.join(", ")}`);
  }

  for (const [name, value] of [
    ["AUTH_SECRET", env.AUTH_SECRET],
    ["SERVICE_JWT_SECRET", env.SERVICE_JWT_SECRET],
  ] as const) {
    if (!value) {
      throw new Error(`Refusing to start in production with missing required config: ${name}`);
    }
    if (value.length < MIN_SECRET_LENGTH) {
      throw new Error(`${name} must be at least ${MIN_SECRET_LENGTH} characters in production`);
    }
  }
}
