// Shared logic behind scripts/create-user.ts (contracts/create-user-cli.md), kept here (under
// src) so it is unit-testable against a fake pool.
import bcrypt from "bcryptjs";
import type { Pool } from "pg";

export class UsernameAlreadyExists extends Error {
  constructor(username: string) {
    super(`username already exists: ${username}`);
  }
}

export async function ensureUsersTable(pool: Pool): Promise<void> {
  await pool.query(
    `CREATE TABLE IF NOT EXISTS users (
       id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
       username text UNIQUE NOT NULL,
       password_hash text NOT NULL,
       created_at timestamptz NOT NULL DEFAULT now(),
       disabled_at timestamptz
     )`,
  );
}

export async function createUser(
  pool: Pool,
  rawUsername: string,
  password: string,
): Promise<{ id: string; username: string }> {
  const username = rawUsername.toLowerCase();
  await ensureUsersTable(pool);
  const passwordHash = await bcrypt.hash(password, 12);
  const result = await pool.query<{ id: string; username: string }>(
    "INSERT INTO users (username, password_hash) VALUES ($1, $2) " +
      "ON CONFLICT (username) DO NOTHING RETURNING id, username",
    [username, passwordHash],
  );
  const row = result.rows[0];
  if (!row) {
    throw new UsernameAlreadyExists(username);
  }
  return row;
}
