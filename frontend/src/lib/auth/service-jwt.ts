// Mints the short-lived HS256 proof the BFF attaches to every backend /api/chat request.
// Contract: specs/004-auth-limits-deploy/contracts/service-jwt.md.
import { SignJWT } from "jose";

const ALGORITHM = "HS256";
const LIFETIME_SECONDS = 120;

export async function mintServiceJwt(
  userId: string,
  username: string,
  secret: string,
): Promise<string> {
  const key = new TextEncoder().encode(secret);
  const now = Math.floor(Date.now() / 1000);
  return new SignJWT({ username })
    .setProtectedHeader({ alg: ALGORITHM })
    .setSubject(userId)
    .setIssuedAt(now)
    .setExpirationTime(now + LIFETIME_SECONDS)
    .sign(key);
}
