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
    pool = new Pool({ connectionString });
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

export async function findUserByUsername(username: string): Promise<UserRecord | null> {
  const pool = getPool();
  await ensureUsersTable(pool);
  const result = await pool.query<{
    id: string;
    username: string;
    password_hash: string;
    disabled_at: Date | null;
  }>(
    "SELECT id, username, password_hash, disabled_at FROM users WHERE username = $1",
    [username.toLowerCase()],
  );
  const row = result.rows[0];
  if (!row) return null;
  return {
    id: row.id,
    username: row.username,
    passwordHash: row.password_hash,
    disabledAt: row.disabled_at,
  };
}
