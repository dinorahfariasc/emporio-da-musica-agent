// The Credentials provider's authorize logic, factored out of auth.ts so it is directly
// unit-testable (including the lockout path) without exercising NextAuth's own machinery.
import bcrypt from "bcryptjs";
import type { Pool } from "pg";

import { findUserByUsername } from "@/lib/auth/db";
import { clearAttempts, type Clock, reserveLoginAttempt } from "@/lib/auth/lockout";

// A precomputed bcrypt hash of an arbitrary password, compared against for an unknown/disabled/
// locked-out account so bcrypt always runs once per attempt regardless of whether the username
// exists (senior review #44): otherwise a real account takes measurably longer to reject (one
// bcrypt compare) than an unknown one (none), which is exactly the "does this username exist"
// oracle FR-005's generic error message is meant to deny.
const DUMMY_HASH = "$2b$12$NAwCx.2Sr.errW4qaE6Ie.nLznSue5p6My.RJpKHci1Il0n85TpQq";

export type AuthorizedUser = { id: string; name: string };

export async function authorizeCredentials(
  pool: Pool,
  rawUsername: string,
  password: string,
  now?: Clock,
): Promise<AuthorizedUser | null> {
  const username = rawUsername.trim().toLowerCase();
  if (!username || !password) return null;

  const reservation = await reserveLoginAttempt(pool, username, now);
  if (!reservation.allowed) {
    // Still run bcrypt against the dummy hash: a locked-out existing account must not respond
    // faster than a locked-out unknown one either.
    await bcrypt.compare(password, DUMMY_HASH);
    return null;
  }

  const user = await findUserByUsername(username);
  const hashToCompare = user && !user.disabledAt ? user.passwordHash : DUMMY_HASH;
  const passwordMatches = await bcrypt.compare(password, hashToCompare);
  if (!user || user.disabledAt || !passwordMatches) return null;

  await clearAttempts(pool, username);
  return { id: user.id, name: user.username };
}
