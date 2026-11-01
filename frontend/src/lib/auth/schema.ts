// Idempotent DDL helper, same spirit as the backend's advisory-locked schema setup
// (app/agent/state.py: ensure_agent_tables). A module-level flag alone is not enough here: a
// serverless function instance's module state does not persist across cold starts, so concurrent
// cold starts could otherwise race on CREATE TABLE (senior review #44); the advisory lock makes
// that race safe even though it cannot be avoided entirely.
import type { Pool } from "pg";

const ensured = new Set<number>();

export async function ensureTableOnce(pool: Pool, lockKey: number, ddl: string): Promise<void> {
  if (ensured.has(lockKey)) return;
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query("SELECT pg_advisory_xact_lock($1)", [lockKey]);
    await client.query(ddl);
    await client.query("COMMIT");
    ensured.add(lockKey);
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}
