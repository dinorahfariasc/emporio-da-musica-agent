// Sign-in lockout (FR-005, research.md R11): 5 failed attempts within 15 minutes locks further
// attempts for that username for 15 minutes. Keyed by username, not a `users` foreign key, so the
// lockout also applies to a username that does not exist (data-model.md "login_attempts").
import type { Pool } from "pg";

const MAX_ATTEMPTS = 5;
const WINDOW_MS = 15 * 60 * 1000;

export type Clock = () => Date;

const systemClock: Clock = () => new Date();

async function ensureTable(pool: Pool): Promise<void> {
  await pool.query(
    `CREATE TABLE IF NOT EXISTS login_attempts (
       username text PRIMARY KEY,
       failed_count int NOT NULL DEFAULT 0,
       window_start timestamptz NOT NULL DEFAULT now()
     )`,
  );
}

export async function isLockedOut(
  pool: Pool,
  username: string,
  now: Clock = systemClock,
): Promise<boolean> {
  await ensureTable(pool);
  const result = await pool.query<{ failed_count: number; window_start: Date }>(
    "SELECT failed_count, window_start FROM login_attempts WHERE username = $1",
    [username.toLowerCase()],
  );
  const row = result.rows[0];
  if (!row) return false;
  const withinWindow = now().getTime() - new Date(row.window_start).getTime() < WINDOW_MS;
  return withinWindow && row.failed_count >= MAX_ATTEMPTS;
}

export async function recordFailedAttempt(
  pool: Pool,
  username: string,
  now: Clock = systemClock,
): Promise<void> {
  await ensureTable(pool);
  const key = username.toLowerCase();
  const result = await pool.query<{ failed_count: number; window_start: Date }>(
    "SELECT failed_count, window_start FROM login_attempts WHERE username = $1",
    [key],
  );
  const row = result.rows[0];
  const expired = row && now().getTime() - new Date(row.window_start).getTime() >= WINDOW_MS;
  if (!row || expired) {
    await pool.query(
      "INSERT INTO login_attempts (username, failed_count, window_start) VALUES ($1, 1, $2) " +
        "ON CONFLICT (username) DO UPDATE SET failed_count = 1, window_start = $2",
      [key, now()],
    );
    return;
  }
  await pool.query(
    "UPDATE login_attempts SET failed_count = failed_count + 1 WHERE username = $1",
    [key],
  );
}

export async function clearAttempts(pool: Pool, username: string): Promise<void> {
  await ensureTable(pool);
  await pool.query("DELETE FROM login_attempts WHERE username = $1", [username.toLowerCase()]);
}
