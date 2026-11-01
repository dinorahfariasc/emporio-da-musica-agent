// Mints the short-lived HS256 proof the BFF attaches to every backend /api/chat request.
// Contract: specs/004-auth-limits-deploy/contracts/service-jwt.md. Claims (iss/aud/exp-iat cap,
// UUID sub) must match what app/auth/service_jwt.py verifies exactly.
import { SignJWT } from "jose";

const ALGORITHM = "HS256";
const LIFETIME_SECONDS = 120;
export const ISSUER = "emporio-da-musica-bff";
export const AUDIENCE = "emporio-da-musica-backend";
export const MIN_SECRET_LENGTH = 32;

export async function mintServiceJwt(
  userId: string,
  username: string,
  secret: string,
): Promise<string> {
  if (secret.length < MIN_SECRET_LENGTH) {
    throw new Error(`SERVICE_JWT_SECRET must be at least ${MIN_SECRET_LENGTH} characters`);
  }
  const key = new TextEncoder().encode(secret);
  const now = Math.floor(Date.now() / 1000);
  return new SignJWT({ username })
    .setProtectedHeader({ alg: ALGORITHM })
    .setSubject(userId)
    .setIssuer(ISSUER)
    .setAudience(AUDIENCE)
    .setIssuedAt(now)
    .setExpirationTime(now + LIFETIME_SECONDS)
    .sign(key);
}
