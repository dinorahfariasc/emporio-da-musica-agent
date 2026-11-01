// Tiny pg client for the login path (specs/004-auth-limits-deploy/research.md R3): no ORM, same
// spirit as the backend's direct psycopg use. One lazy process-wide pool over DATABASE_URL.
import { Pool } from "pg";

let pool: Pool | null = null;

export function getPool(): Pool {
  if (!pool) {
    const connectionString = process.env.DATABASE_URL;
    if (!connectionString) {
      throw new Error("DATABASE_URL is not configured");
    }
    // Serverless: each function instance should hold very few connections (senior review #44).
    pool = new Pool({ connectionString, max: 2 });
  }
  return pool;
}

export type UserRecord = {
  id: string;
  username: string;
  passwordHash: string;
  disabledAt: Date | null;
};

let tableEnsured = false;

async function ensureUsersTable(pool: Pool): Promise<void> {
  if (tableEnsured) return;
  await pool.query(
    `CREATE TABLE IF NOT EXISTS users (
       id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
       username text UNIQUE NOT NULL,
       password_hash text NOT NULL,
       created_at timestamptz NOT NULL DEFAULT now(),
       disabled_at timestamptz
     )`,
  );
  tableEnsured = true;
}

function toUserRecord(row: {
  id: string;
  username: string;
  password_hash: string;
  disabled_at: Date | null;
}): UserRecord {
  return {
    id: row.id,
    username: row.username,
    passwordHash: row.password_hash,
    disabledAt: row.disabled_at,
  };
}

export async function findUserByUsername(username: string): Promise<UserRecord | null> {
  const pool = getPool();
  await ensureUsersTable(pool);
  const result = await pool.query<{
    id: string;
    username: string;
    password_hash: string;
    disabled_at: Date | null;
  }>("SELECT id, username, password_hash, disabled_at FROM users WHERE username = $1", [
    username.toLowerCase(),
  ]);
  const row = result.rows[0];
  return row ? toUserRecord(row) : null;
}

export async function findUserById(id: string): Promise<UserRecord | null> {
  const pool = getPool();
  await ensureUsersTable(pool);
  try {
    const result = await pool.query<{
      id: string;
      username: string;
      password_hash: string;
      disabled_at: Date | null;
    }>("SELECT id, username, password_hash, disabled_at FROM users WHERE id = $1", [id]);
    const row = result.rows[0];
    return row ? toUserRecord(row) : null;
  } catch {
    // A malformed uuid (should never happen for a value we minted ourselves) is "not found",
    // not a 500 — same posture as the backend's service-JWT sub validation.
    return null;
  }
}
