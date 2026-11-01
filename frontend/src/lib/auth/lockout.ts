// Sign-in lockout (FR-005, research.md R11): 5 failed attempts within 15 minutes locks further
// attempts for that username for 15 minutes. Keyed by username, not a `users` foreign key, so the
// lockout also applies to a username that does not exist (data-model.md "login_attempts").
//
// The attempt is reserved atomically BEFORE the password is ever compared (senior review #44),
// mirroring the backend's reserve_attempt/confirm_success pattern in app/agent/state.py: a burst
// of parallel guesses increments the same counter one row-lock at a time, so none of them can
// read "not locked yet" and all slip through before any of them observes the 5th failure.
import type { Pool } from "pg";

const MAX_ATTEMPTS = 5;
const WINDOW_MINUTES = 15;

export type Clock = () => Date;

const systemClock: Clock = () => new Date();

let tableEnsured = false;

async function ensureTable(pool: Pool): Promise<void> {
  if (tableEnsured) return;
  await pool.query(
    `CREATE TABLE IF NOT EXISTS login_attempts (
       username text PRIMARY KEY,
       failed_count int NOT NULL DEFAULT 0,
       window_start timestamptz NOT NULL DEFAULT now()
     )`,
  );
  tableEnsured = true;
}

export type Reservation = { allowed: boolean };

// Atomically increments failed_count (starting a new 15-minute window if the previous one
// expired) and reports whether the account is now over the limit. Call this BEFORE comparing a
// password; on a correct password, call `clearAttempts` to give the attempt back.
export async function reserveLoginAttempt(
  pool: Pool,
  username: string,
  now: Clock = systemClock,
): Promise<Reservation> {
  await ensureTable(pool);
  const key = username.toLowerCase();
  const moment = now();
  const result = await pool.query<{ failed_count: number }>(
    `INSERT INTO login_attempts (username, failed_count, window_start)
     VALUES ($1, 1, $2)
     ON CONFLICT (username) DO UPDATE SET
       failed_count = CASE
         WHEN $2::timestamptz - login_attempts.window_start >= make_interval(mins => $3)
           THEN 1
         ELSE login_attempts.failed_count + 1
       END,
       window_start = CASE
         WHEN $2::timestamptz - login_attempts.window_start >= make_interval(mins => $3)
           THEN $2
         ELSE login_attempts.window_start
       END
     RETURNING failed_count`,
    [key, moment, WINDOW_MINUTES],
  );
  const failedCount = result.rows[0].failed_count;
  return { allowed: failedCount <= MAX_ATTEMPTS };
}

export async function clearAttempts(pool: Pool, username: string): Promise<void> {
  await ensureTable(pool);
  await pool.query("DELETE FROM login_attempts WHERE username = $1", [username.toLowerCase()]);
}
