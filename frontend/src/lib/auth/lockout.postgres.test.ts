// Exercises reserveLoginAttempt against a real Postgres (the atomicity claim only means something
// against the real single-statement upsert, not the in-memory FakePool in lockout.test.ts).
// Skipped when no local DATABASE_URL is configured (same posture as the backend's `database_url`
// pytest fixture): `docker compose up -d` then set DATABASE_URL to run it.
import { randomUUID } from "node:crypto";

import { Pool } from "pg";
import { afterAll, describe, expect, it } from "vitest";

import { clearAttempts, reserveLoginAttempt } from "./lockout";

const DATABASE_URL = process.env.DATABASE_URL;

describe.skipIf(!DATABASE_URL)("reserveLoginAttempt (real Postgres)", () => {
  const pool = new Pool({ connectionString: DATABASE_URL });

  afterAll(async () => {
    await pool.end();
  });

  it("allows exactly 5 of 20 fully concurrent attempts for one username", async () => {
    // The real regression this guards against: a TOCTOU race where every parallel request reads
    // "not locked yet" before any of them has recorded its own failure, letting far more than 5
    // guesses through a burst. The single-statement upsert serializes on the row, so only the
    // first 5 increments (in whatever order Postgres picks) see failed_count <= 5.
    const username = `concurrency-${randomUUID()}`;
    const results = await Promise.all(
      Array.from({ length: 20 }, () => reserveLoginAttempt(pool, username)),
    );
    expect(results.filter((r) => r.allowed)).toHaveLength(5);
    await clearAttempts(pool, username);
  });

  it("allows 5 sequential attempts then locks the 6th", async () => {
    const username = `sequential-${randomUUID()}`;
    for (let i = 0; i < 5; i++) {
      expect((await reserveLoginAttempt(pool, username)).allowed).toBe(true);
    }
    expect((await reserveLoginAttempt(pool, username)).allowed).toBe(false);
    await clearAttempts(pool, username);
  });

  it("clearAttempts lets a fresh window start immediately", async () => {
    const username = `clear-${randomUUID()}`;
    for (let i = 0; i < 5; i++) await reserveLoginAttempt(pool, username);
    expect((await reserveLoginAttempt(pool, username)).allowed).toBe(false);

    await clearAttempts(pool, username);
    expect((await reserveLoginAttempt(pool, username)).allowed).toBe(true);
    await clearAttempts(pool, username);
  });
});
