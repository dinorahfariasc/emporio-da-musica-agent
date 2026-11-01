import type { Pool } from "pg";
import { describe, expect, it } from "vitest";

import { clearAttempts, reserveLoginAttempt } from "./lockout";

// A minimal in-memory stand-in for `pg.Pool` so lockout logic is tested without a real database.
// The real atomicity guarantee comes from Postgres's single-statement upsert (tested against the
// real SQL in lockout.postgres.test.ts); this fake only has to reproduce its observable behavior
// for sequential calls.
class FakePool {
  rows = new Map<string, { failed_count: number; window_start: Date }>();

  async query(sql: string, params: unknown[] = []) {
    const text = sql.trim();
    if (text.startsWith("CREATE TABLE")) return { rows: [] };
    if (text.startsWith("INSERT")) {
      const [username, moment, windowMinutes] = params as [string, Date, number];
      const existing = this.rows.get(username);
      const windowMs = windowMinutes * 60_000;
      const expired = existing && moment.getTime() - existing.window_start.getTime() >= windowMs;
      if (!existing || expired) {
        const row = { failed_count: 1, window_start: moment };
        this.rows.set(username, row);
        return { rows: [{ failed_count: 1 }] };
      }
      existing.failed_count += 1;
      return { rows: [{ failed_count: existing.failed_count }] };
    }
    if (text.startsWith("DELETE")) {
      const [username] = params as [string];
      this.rows.delete(username);
      return { rows: [] };
    }
    throw new Error(`unexpected query: ${text}`);
  }
}

function fakeClock(ms: number) {
  return () => new Date(ms);
}

describe("sign-in lockout", () => {
  it("allows the first 5 attempts and locks out the 6th", async () => {
    const pool = new FakePool() as unknown as Pool;
    const now = fakeClock(0);
    for (let i = 0; i < 5; i++) {
      expect((await reserveLoginAttempt(pool, "demo", now)).allowed).toBe(true);
    }
    expect((await reserveLoginAttempt(pool, "demo", now)).allowed).toBe(false);
  });

  it("clears the lock after a successful login", async () => {
    const pool = new FakePool() as unknown as Pool;
    const now = fakeClock(0);
    for (let i = 0; i < 5; i++) await reserveLoginAttempt(pool, "demo", now);
    expect((await reserveLoginAttempt(pool, "demo", now)).allowed).toBe(false);

    await clearAttempts(pool, "demo");
    expect((await reserveLoginAttempt(pool, "demo", now)).allowed).toBe(true);
  });

  it("resets the window after 15 minutes", async () => {
    const pool = new FakePool() as unknown as Pool;
    const start = fakeClock(0);
    for (let i = 0; i < 5; i++) await reserveLoginAttempt(pool, "demo", start);
    expect((await reserveLoginAttempt(pool, "demo", start)).allowed).toBe(false);

    const later = fakeClock(16 * 60 * 1000);
    expect((await reserveLoginAttempt(pool, "demo", later)).allowed).toBe(true);
  });

  it("username lookup is case-insensitive", async () => {
    const pool = new FakePool() as unknown as Pool;
    const now = fakeClock(0);
    for (let i = 0; i < 5; i++) await reserveLoginAttempt(pool, "Demo", now);
    expect((await reserveLoginAttempt(pool, "demo", now)).allowed).toBe(false);
  });
});
